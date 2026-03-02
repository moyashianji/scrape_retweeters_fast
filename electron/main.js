const { app, BrowserWindow, shell, ipcMain } = require('electron')
const path = require('path')
const { spawn, execSync } = require('child_process')
const net = require('net')
const fs = require('fs')

let mainWindow = null
let pythonProcess = null
let backendPort = null
let backendError = null

// --- ポート検出 ---
function findFreePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer()
    server.listen(0, '127.0.0.1', () => {
      const port = server.address().port
      server.close(() => resolve(port))
    })
    server.on('error', reject)
  })
}

// --- Python バックエンド起動 ---
function getProjectRoot() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'backend-bundle')
  }
  // dev: electron/main.js → プロジェクトルートは1つ上
  return path.resolve(__dirname, '..')
}

function getMacShellEnv() {
  // macOS の .app はシェルの PATH を継承しない。ログインシェルから取得する
  try {
    const env = execSync('/bin/bash -lc "env"', { timeout: 5000 }).toString()
    const result = {}
    for (const line of env.split('\n')) {
      const idx = line.indexOf('=')
      if (idx > 0) {
        result[line.substring(0, idx)] = line.substring(idx + 1)
      }
    }
    return result
  } catch {
    return null
  }
}

function findPython() {
  if (process.platform === 'win32') {
    return 'python'
  }
  // macOS の .app はシェルの PATH を継承しないため、よくあるパスを直接探す
  const candidates = [
    '/opt/homebrew/bin/python3',   // Apple Silicon Homebrew
    '/usr/local/bin/python3',      // Intel Homebrew / 公式インストーラ
    '/usr/bin/python3',            // macOS 標準
  ]
  // シェルから PATH を取得して追加候補を探す
  try {
    const shellPath = execSync('/bin/bash -lc "which python3"', { timeout: 3000 }).toString().trim()
    if (shellPath && !candidates.includes(shellPath)) {
      candidates.unshift(shellPath)
    }
  } catch { /* ignore */ }

  for (const p of candidates) {
    try {
      if (fs.existsSync(p)) return p
    } catch { /* ignore */ }
  }
  return 'python3' // フォールバック
}

async function startBackend() {
  backendPort = await findFreePort()
  const projectRoot = getProjectRoot()
  const pythonCmd = findPython()

  const args = [
    '-u',
    '-c',
    `import sys; sys.path.insert(0, r"${projectRoot}"); import uvicorn; uvicorn.run("backend.app:app", host="127.0.0.1", port=${backendPort}, log_level="warning")`
  ]

  console.log(`Starting backend on port ${backendPort}...`)
  console.log(`Python: ${pythonCmd}`)
  console.log(`Project root: ${projectRoot}`)

  // macOS .app ではシェルの環境変数を取得して spawn に渡す
  let spawnEnv = { ...process.env, PYTHONIOENCODING: 'utf-8' }
  if (process.platform === 'darwin' && app.isPackaged) {
    const shellEnv = getMacShellEnv()
    if (shellEnv) {
      spawnEnv = { ...shellEnv, PYTHONIOENCODING: 'utf-8' }
      console.log(`Using shell PATH: ${shellEnv.PATH?.substring(0, 200)}`)
    }
  }

  // Python に必要なパスを確実に含める
  const extraPaths = ['/opt/homebrew/bin', '/usr/local/bin', '/usr/bin', '/bin']
  if (spawnEnv.PATH) {
    const existing = spawnEnv.PATH.split(':')
    for (const p of extraPaths) {
      if (!existing.includes(p)) existing.push(p)
    }
    spawnEnv.PATH = existing.join(':')
  }

  let stderrOutput = ''

  pythonProcess = spawn(pythonCmd, args, {
    cwd: projectRoot,
    env: spawnEnv,
    stdio: ['pipe', 'pipe', 'pipe'],
  })

  pythonProcess.stdout.on('data', (data) => {
    console.log(`[Backend] ${data.toString().trim()}`)
  })

  pythonProcess.stderr.on('data', (data) => {
    const msg = data.toString().trim()
    console.error(`[Backend] ${msg}`)
    stderrOutput += msg + '\n'
  })

  pythonProcess.on('error', (err) => {
    console.error('Failed to start Python backend:', err.message)
    backendError = `Python起動失敗: ${err.message}`
  })

  pythonProcess.on('exit', (code) => {
    console.log(`Python backend exited with code ${code}`)
    if (code !== 0 && code !== null) {
      backendError = `Python異常終了 (code ${code}):\n${stderrOutput.slice(-500)}`
    }
    pythonProcess = null
  })

  await waitForBackend(backendPort)
  return backendPort
}

function waitForBackend(port, maxRetries = 30) {
  return new Promise((resolve, reject) => {
    let attempts = 0
    const check = () => {
      attempts++
      const client = net.createConnection({ port, host: '127.0.0.1' }, () => {
        client.end()
        resolve()
      })
      client.on('error', () => {
        if (attempts >= maxRetries) {
          reject(new Error(`Backend did not start in time (${maxRetries} attempts).\n${backendError || ''}`))
        } else {
          setTimeout(check, 500)
        }
      })
    }
    check()
  })
}

// --- ウィンドウ作成 ---
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1000,
    minHeight: 600,
    title: 'X Campaign Picker',
    backgroundColor: '#111827',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
  })

  if (process.env.VITE_DEV_SERVER_URL) {
    mainWindow.loadURL(process.env.VITE_DEV_SERVER_URL)
  } else {
    // ビルド済みReactアプリを読み込む
    const indexPath = path.join(__dirname, '..', 'viewer', 'dist', 'index.html')
    mainWindow.loadFile(indexPath)
  }

  mainWindow.on('closed', () => {
    mainWindow = null
  })

  mainWindow.setMenuBarVisibility(false)
}

// --- IPC ハンドラ ---
ipcMain.handle('get-backend-info', () => {
  return {
    port: backendPort,
    error: backendError,
  }
})

// --- アプリ起動 ---
app.whenReady().then(async () => {
  try {
    const port = await startBackend()
    process.env.BACKEND_PORT = port.toString()
    backendError = null
  } catch (err) {
    console.error('Backend startup failed:', err)
    backendError = err.message || 'Unknown error'
  }
  createWindow()
})

app.on('window-all-closed', () => {
  if (pythonProcess) {
    pythonProcess.kill()
    pythonProcess = null
  }
  app.quit()
})

app.on('before-quit', () => {
  if (pythonProcess) {
    pythonProcess.kill()
    pythonProcess = null
  }
})

app.on('activate', () => {
  if (app.isReady() && BrowserWindow.getAllWindows().length === 0) {
    createWindow()
  }
})
