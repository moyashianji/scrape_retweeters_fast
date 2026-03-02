// Electronからバックエンドポートを取得、Vite devモード時は空（proxyに委譲）
function getApiBase() {
  if (window.electronAPI?.getBackendPort) {
    const port = window.electronAPI.getBackendPort()
    if (port) return `http://127.0.0.1:${port}`
  }
  return ''
}

function getWsBase() {
  if (window.electronAPI?.getBackendPort) {
    const port = window.electronAPI.getBackendPort()
    if (port) return `ws://127.0.0.1:${port}`
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}`
}

// バックエンド接続チェック（エラー詳細をユーザーに表示）
async function checkBackendOrThrow() {
  const base = getApiBase()
  if (base) return // ポートが設定されていればOK

  // Electron 環境でポートがない = バックエンド起動失敗
  if (window.electronAPI?.getBackendInfo) {
    try {
      const info = await window.electronAPI.getBackendInfo()
      if (info.error) {
        throw new Error(
          `バックエンドの起動に失敗しました。\n\n` +
          `原因: ${info.error}\n\n` +
          `対処法:\n` +
          `1. Python3がインストールされているか確認\n` +
          `2. ターミナルで以下を実行:\n` +
          `   pip3 install fastapi uvicorn selenium webdriver-manager pydantic`
        )
      }
    } catch (e) {
      if (e.message.includes('バックエンド')) throw e
    }
  }
  throw new Error(
    'サーバーに接続できません。バックエンドが起動しているか確認してください。'
  )
}

export async function startScrape({ scraperType, url, maxUsers, useCache = true }) {
  await checkBackendOrThrow()
  const res = await fetch(`${getApiBase()}/api/scrape`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      scraper_type: scraperType,
      url,
      max_users: maxUsers,
      use_cache: useCache,
    }),
  })
  return res.json()
}

export async function listJobs() {
  const res = await fetch(`${getApiBase()}/api/jobs`)
  return res.json()
}

export async function getJobResults(jobId) {
  const res = await fetch(`${getApiBase()}/api/jobs/${jobId}/results`)
  return res.json()
}

export async function getJobLogs(jobId) {
  const res = await fetch(`${getApiBase()}/api/jobs/${jobId}/logs`)
  return res.json()
}

export async function cancelJob(jobId) {
  const res = await fetch(`${getApiBase()}/api/jobs/${jobId}/cancel`, { method: 'POST' })
  return res.json()
}

export function getCsvDownloadUrl(jobId) {
  return `${getApiBase()}/api/jobs/${jobId}/csv`
}

export function createWebSocket() {
  return new WebSocket(`${getWsBase()}/ws/logs`)
}

// --- 履歴 API ---

export async function listHistory(limit = 100, offset = 0) {
  const res = await fetch(`${getApiBase()}/api/history?limit=${limit}&offset=${offset}`)
  return res.json()
}

export async function getHistoryResults(jobId) {
  const res = await fetch(`${getApiBase()}/api/history/${jobId}/results`)
  return res.json()
}

export function getHistoryCsvUrl(jobId) {
  return `${getApiBase()}/api/history/${jobId}/csv`
}

export async function deleteHistory(jobId) {
  const res = await fetch(`${getApiBase()}/api/history/${jobId}`, { method: 'DELETE' })
  return res.json()
}

export async function getCacheStats() {
  const res = await fetch(`${getApiBase()}/api/cache/stats`)
  return res.json()
}
