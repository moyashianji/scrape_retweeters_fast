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

// --- パス ---
function getProjectRoot() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'backend-bundle')
  }
  return path.resolve(__dirname, '..')
}

// --- バンドル済み実行ファイルを探す ---
function findBundledBackend() {
  const root = getProjectRoot()
  // PyInstaller でビルドしたバイナリを探す
  const candidates = [
    path.join(root, 'backend-server'),         // macOS / Linux
    path.join(root, 'backend-server.exe'),      // Windows
  ]
  for (const p of candidates) {
    if (fs.existsSync(p)) {
      // 実行権限があるか確認 (macOS/Linux)
      try { fs.accessSync(p, fs.constants.X_OK) } catch {
        try { fs.chmodSync(p, 0o755) } catch { /* ignore */ }
      }
      return p
    }
  }
  return null
}

// --- Python フォールバック (dev モード用) ---
function findPython() {
  if (process.platform === 'win32') return 'python'
  const candidates = [
    '/opt/homebrew/bin/python3',
    '/usr/local/bin/python3',
    '/usr/bin/python3',
  ]
  try {
    const shellPath = execSync('/bin/bash -lc "which python3"', { timeout: 3000 }).toString().trim()
    if (shellPath && !candidates.includes(shellPath)) candidates.unshift(shellPath)
  } catch { /* ignore */ }
  for (const p of candidates) {
    try { if (fs.existsSync(p)) return p } catch { /* ignore */ }
  }
  return 'python3'
}

function getMacShellEnv() {
  try {
    const env = execSync('/bin/bash -lc "env"', { timeout: 5000 }).toString()
    const result = {}
    for (const line of env.split('\n')) {
      const idx = line.indexOf('=')
      if (idx > 0) result[line.substring(0, idx)] = line.substring(idx + 1)
    }
    return result
  } catch { return null }
}

// --- バックエンド起動 ---
async function startBackend() {
  backendPort = await findFreePort()
  const projectRoot = getProjectRoot()

  // 1. バンドル済み実行ファイルを試す (ユーザーはPython不要)
  const bundledPath = findBundledBackend()

  let cmd, args, spawnEnv

  if (bundledPath) {
    console.log(`Using bundled backend: ${bundledPath}`)
    cmd = bundledPath
    args = [String(backendPort)]
    spawnEnv = { ...process.env }
  } else {
    // 2. フォールバック: システムの Python を使う (dev モード)
    console.log('No bundled backend found, falling back to Python')
    const pythonCmd = findPython()
    cmd = pythonCmd
    args = [
      '-u', '-c',
      `import sys; sys.path.insert(0, r"${projectRoot}"); import uvicorn; uvicorn.run("backend.app:app", host="127.0.0.1", port=${backendPort}, log_level="warning")`
    ]
    spawnEnv = { ...process.env, PYTHONIOENCODING: 'utf-8' }

    // macOS .app ではシェルの環境変数を取得
    if (process.platform === 'darwin' && app.isPackaged) {
      const shellEnv = getMacShellEnv()
      if (shellEnv) spawnEnv = { ...shellEnv, PYTHONIOENCODING: 'utf-8' }
    }
  }

  console.log(`Starting backend on port ${backendPort}...`)
  console.log(`Command: ${cmd}`)
  console.log(`Project root: ${projectRoot}`)

  let stderrOutput = ''

  pythonProcess = spawn(cmd, args, {
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
    console.error('Failed to start backend:', err.message)
    backendError = `バックエンド起動失敗: ${err.message}`
  })

  pythonProcess.on('exit', (code) => {
    console.log(`Backend exited with code ${code}`)
    if (code !== 0 && code !== null) {
      backendError = `バックエンド異常終了 (code ${code}):\n${stderrOutput.slice(-500)}`
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
    const indexPath = path.join(__dirname, '..', 'viewer', 'dist', 'index.html')
    mainWindow.loadFile(indexPath)
  }

  mainWindow.on('closed', () => { mainWindow = null })
  mainWindow.setMenuBarVisibility(false)
}

// --- IPC ---
ipcMain.handle('get-backend-info', () => ({
  port: backendPort,
  error: backendError,
}))

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
  if (pythonProcess) { pythonProcess.kill(); pythonProcess = null }
  app.quit()
})

app.on('before-quit', () => {
  if (pythonProcess) { pythonProcess.kill(); pythonProcess = null }
})

app.on('activate', () => {
  if (app.isReady() && BrowserWindow.getAllWindows().length === 0) {
    createWindow()
  }
})
