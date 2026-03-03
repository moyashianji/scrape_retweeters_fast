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

// レスポンスチェック付きfetch
async function safeFetch(url, options) {
  const res = await fetch(url, options)
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.error || `サーバーエラー (${res.status})`)
  }
  return res.json()
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
  return safeFetch(`${getApiBase()}/api/scrape`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      scraper_type: scraperType,
      url,
      max_users: maxUsers,
      use_cache: useCache,
    }),
  })
}

export async function listJobs() {
  return safeFetch(`${getApiBase()}/api/jobs`)
}

export async function getJobResults(jobId) {
  return safeFetch(`${getApiBase()}/api/jobs/${jobId}/results`)
}

export async function getJobLogs(jobId) {
  return safeFetch(`${getApiBase()}/api/jobs/${jobId}/logs`)
}

export async function cancelJob(jobId) {
  return safeFetch(`${getApiBase()}/api/jobs/${jobId}/cancel`, { method: 'POST' })
}

export function getCsvDownloadUrl(jobId) {
  return `${getApiBase()}/api/jobs/${jobId}/csv`
}

export function createWebSocket() {
  return new WebSocket(`${getWsBase()}/ws/logs`)
}

// --- 履歴 API ---

export async function listHistory(limit = 100, offset = 0) {
  return safeFetch(`${getApiBase()}/api/history?limit=${limit}&offset=${offset}`)
}

export async function getHistoryResults(jobId) {
  return safeFetch(`${getApiBase()}/api/history/${jobId}/results`)
}

export function getHistoryCsvUrl(jobId) {
  return `${getApiBase()}/api/history/${jobId}/csv`
}

export async function deleteHistory(jobId) {
  return safeFetch(`${getApiBase()}/api/history/${jobId}`, { method: 'DELETE' })
}

export async function getCacheStats() {
  return safeFetch(`${getApiBase()}/api/cache/stats`)
}
