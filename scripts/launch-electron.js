/**
 * Electron起動ラッパー
 * VSCode等のElectronベースIDEから起動する場合、
 * ELECTRON_RUN_AS_NODE=1 が設定されてElectronが通常のNode.jsとして動作してしまう。
 * この環境変数を削除してからElectronを起動する。
 */
const { spawn } = require('child_process')
const path = require('path')

// ELECTRON_RUN_AS_NODE を削除
const env = { ...process.env }
delete env.ELECTRON_RUN_AS_NODE

// electron バイナリのパスを取得
const electronPath = require('electron')

// Electronを起動
const child = spawn(electronPath, ['.'], {
  cwd: path.resolve(__dirname, '..'),
  env,
  stdio: 'inherit',
  windowsHide: false,
})

child.on('close', (code) => {
  process.exit(code)
})
