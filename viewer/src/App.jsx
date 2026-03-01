import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { startScrape, listJobs, getJobResults, getJobLogs, createWebSocket, listHistory, getHistoryResults, deleteHistory } from './api'
import { mergeUser, GROUPS, DEFAULT_GROUP } from './constants'
import Sidebar from './components/Sidebar'
import AnalysisPanel from './components/AnalysisPanel'
import ComparisonPanel from './components/ComparisonPanel'
import { ToastContainer, useToast } from './components/Toast'
import ConfirmModal from './components/ConfirmModal'

const TABS = [
  { id: 'analysis', label: '📋 分析', desc: 'ユーザー一覧・統計' },
  { id: 'comparison', label: '📊 比較', desc: 'グループ間比較チャート' },
]

function App() {
  // トースト通知
  const { toasts, addToast, removeToast } = useToast()

  // 確認モーダル
  const [confirmState, setConfirmState] = useState({ open: false })
  const showConfirm = useCallback(({ title, message, confirmLabel, danger }) => {
    return new Promise((resolve) => {
      setConfirmState({
        open: true,
        title,
        message,
        confirmLabel,
        danger,
        onConfirm: () => { setConfirmState({ open: false }); resolve(true) },
        onCancel: () => { setConfirmState({ open: false }); resolve(false) },
      })
    })
  }, [])

  // タブ
  const [activeTab, setActiveTab] = useState('analysis')

  // グループ選択
  const [selectedGroup, setSelectedGroup] = useState(DEFAULT_GROUP)

  // ユーザーデータ（共通: 分析パネル用）
  const [userMap, setUserMap] = useState({})
  const [importedFiles, setImportedFiles] = useState([])

  // グループ別ユーザーデータ（比較パネル用）
  const [groupUserMaps, setGroupUserMaps] = useState({ amptakcolors: {}, sneakerstep: {}, knightx: {}, meteora: {} })

  // フィルター
  const [searchQuery, setSearchQuery] = useState('')
  const [filterMention, setFilterMention] = useState('')
  const [filterHeart, setFilterHeart] = useState('')
  const [filterDm, setFilterDm] = useState('')
  const [filterSource, setFilterSource] = useState('')
  const [sortBy, setSortBy] = useState('index')

  // ジョブ管理
  const [jobs, setJobs] = useState([])
  const [selectedJobId, setSelectedJobId] = useState(null)

  // 履歴
  const [history, setHistory] = useState([])

  // WebSocket
  const [logs, setLogs] = useState({})
  const [connected, setConnected] = useState(false)
  const wsRef = useRef(null)
  const reconnectRef = useRef(null)

  const users = useMemo(() => Object.values(userMap), [userMap])

  const allFileNames = useMemo(() =>
    [...new Set(importedFiles.map(f => f.name))],
    [importedFiles]
  )

  const hasRunningJob = useMemo(() =>
    jobs.some(j => j.status === 'running'),
    [jobs]
  )

  // 比較用のユーザーリスト
  const ampUsers = useMemo(() => Object.values(groupUserMaps.amptakcolors), [groupUserMaps.amptakcolors])
  const snkUsers = useMemo(() => Object.values(groupUserMaps.sneakerstep), [groupUserMaps.sneakerstep])
  const knxUsers = useMemo(() => Object.values(groupUserMaps.knightx), [groupUserMaps.knightx])
  const mtorUsers = useMemo(() => Object.values(groupUserMaps.meteora), [groupUserMaps.meteora])

  // グループ別にユーザーを追加するヘルパー
  const addUsersToGroup = useCallback((group, results, sourceName) => {
    setGroupUserMaps(prev => {
      const groupMap = { ...prev[group] }
      for (const user of results) {
        const key = user.username
        if (!key) continue
        if (groupMap[key]) {
          groupMap[key] = mergeUser(groupMap[key], user, sourceName)
        } else {
          groupMap[key] = { ...user, _sources: [sourceName] }
        }
      }
      return { ...prev, [group]: groupMap }
    })
  }, [])

  // --- WebSocket 接続 ---
  const connectWs = useCallback(() => {
    try {
      const ws = createWebSocket()
      wsRef.current = ws

      ws.onopen = () => {
        setConnected(true)
        ws.send('ping')
      }

      ws.onclose = () => {
        setConnected(false)
        wsRef.current = null
        reconnectRef.current = setTimeout(connectWs, 2000)
      }

      ws.onerror = () => {
        ws.close()
      }

      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data)
        if (msg.type === 'log') {
          setLogs(prev => ({
            ...prev,
            [msg.job_id]: [...(prev[msg.job_id] || []), msg.line],
          }))
        } else if (msg.type === 'status') {
          fetchJobs()
        }
      }
    } catch {
      reconnectRef.current = setTimeout(connectWs, 2000)
    }
  }, [])

  useEffect(() => {
    connectWs()
    return () => {
      if (wsRef.current) wsRef.current.close()
      if (reconnectRef.current) clearTimeout(reconnectRef.current)
    }
  }, [connectWs])

  // --- 履歴取得 ---
  const fetchHistory = useCallback(async () => {
    try {
      const data = await listHistory()
      setHistory(data)
    } catch {
      // ignore
    }
  }, [])

  useEffect(() => {
    fetchHistory()
  }, [fetchHistory])

  // --- ジョブ一覧のポーリング ---
  const fetchJobs = useCallback(async () => {
    try {
      const data = await listJobs()
      setJobs(prev => {
        for (const job of data) {
          const old = prev.find(j => j.id === job.id)
          if (old && old.status === 'running' && job.status === 'completed') {
            addToast(`取得完了: ${job.result_count}人のデータを取得しました`, 'success')
            fetchHistory()
            break
          }
          if (old && old.status === 'running' && job.status === 'failed') {
            addToast(`取得失敗: ${job.error || 'エラーが発生しました'}`, 'error', 6000)
            fetchHistory()
            break
          }
        }
        return data
      })
    } catch {
      // サーバー未起動時は無視
    }
  }, [fetchHistory, addToast])

  useEffect(() => {
    fetchJobs()
    const interval = setInterval(fetchJobs, 2000)
    return () => clearInterval(interval)
  }, [fetchJobs])

  // --- REST API ログポーリング ---
  useEffect(() => {
    if (!selectedJobId) return
    const runningJob = jobs.find(j => j.id === selectedJobId && (j.status === 'running' || j.status === 'completed'))
    if (!runningJob) return

    const pollLogs = async () => {
      try {
        const data = await getJobLogs(selectedJobId)
        if (data.lines && data.lines.length > 0) {
          setLogs(prev => {
            const currentLines = prev[selectedJobId] || []
            if (data.lines.length > currentLines.length) {
              return { ...prev, [selectedJobId]: data.lines }
            }
            return prev
          })
        }
      } catch {
        // ignore
      }
    }

    pollLogs()
    const interval = setInterval(pollLogs, 1000)
    return () => clearInterval(interval)
  }, [selectedJobId, jobs])

  // --- スクレイプ開始 ---
  const handleStartScrape = useCallback(async ({ scraperType, url, maxUsers }) => {
    try {
      const result = await startScrape({ scraperType, url, maxUsers })
      if (result.error) {
        addToast(result.error, 'error', 6000)
        return
      }
      setSelectedJobId(result.job_id)
      addToast('データ取得を開始しました', 'info')
      fetchJobs()
    } catch (err) {
      addToast('サーバーに接続できません。バックエンドが起動しているか確認してください。', 'error', 8000)
    }
  }, [fetchJobs, addToast])

  // --- 結果をViewerに読込 ---
  const handleLoadResults = useCallback(async (jobId) => {
    try {
      const results = await getJobResults(jobId)
      if (!Array.isArray(results)) return

      const job = jobs.find(j => j.id === jobId)
      const sourceName = job
        ? `${job.scraper_type}_${job.id}`
        : `job_${jobId}`

      setUserMap(prev => {
        const next = { ...prev }
        for (const user of results) {
          const key = user.username
          if (!key) continue
          if (next[key]) {
            next[key] = mergeUser(next[key], user, sourceName)
          } else {
            next[key] = { ...user, _sources: [sourceName] }
          }
        }
        return next
      })

      setImportedFiles(prev => [
        ...prev,
        { name: sourceName, count: results.length }
      ])

      // 比較用にも現在のグループに追加
      addUsersToGroup(selectedGroup, results, sourceName)

      addToast(`${results.length}人のデータを読み込みました（${GROUPS[selectedGroup]?.fanMark || ''} ${GROUPS[selectedGroup]?.name || selectedGroup}）`, 'success')
    } catch {
      addToast('結果の読み込みに失敗しました', 'error')
    }
  }, [jobs, addToast, selectedGroup, addUsersToGroup])

  // --- JSONファイル手動インポート ---
  const handleFileImport = useCallback((e) => {
    const files = Array.from(e.target.files)
    if (files.length === 0) return

    files.forEach(file => {
      const reader = new FileReader()
      reader.onload = (event) => {
        try {
          const data = JSON.parse(event.target.result)
          const arr = Array.isArray(data) ? data : []

          setUserMap(prev => {
            const next = { ...prev }
            for (const user of arr) {
              const key = user.username
              if (!key) continue
              if (next[key]) {
                next[key] = mergeUser(next[key], user, file.name)
              } else {
                next[key] = { ...user, _sources: [file.name] }
              }
            }
            return next
          })

          setImportedFiles(prev => [...prev, { name: file.name, count: arr.length }])

          // 比較用にも現在のグループに追加
          addUsersToGroup(selectedGroup, arr, file.name)

          addToast(`${file.name} を読み込みました (${arr.length}人 → ${GROUPS[selectedGroup]?.fanMark || ''} ${GROUPS[selectedGroup]?.name || ''})`, 'success')
        } catch {
          addToast(`${file.name} の読み込みに失敗しました。JSONファイルか確認してください。`, 'error')
        }
      }
      reader.readAsText(file)
    })

    e.target.value = ''
  }, [addToast, selectedGroup, addUsersToGroup])

  // --- 履歴から読込 ---
  const handleLoadHistory = useCallback(async (jobId) => {
    try {
      const results = await getHistoryResults(jobId)
      if (!Array.isArray(results)) return

      const historyJob = history.find(j => j.id === jobId)
      const sourceName = historyJob
        ? `${historyJob.scraper_type}_${historyJob.id}`
        : `history_${jobId}`

      setUserMap(prev => {
        const next = { ...prev }
        for (const user of results) {
          const key = user.username
          if (!key) continue
          if (next[key]) {
            next[key] = mergeUser(next[key], user, sourceName)
          } else {
            next[key] = { ...user, _sources: [sourceName] }
          }
        }
        return next
      })

      setImportedFiles(prev => [
        ...prev,
        { name: sourceName, count: results.length }
      ])

      // 比較用にも現在のグループに追加
      addUsersToGroup(selectedGroup, results, sourceName)

      addToast(`履歴から${results.length}人のデータを読み込みました（${GROUPS[selectedGroup]?.fanMark || ''} ${GROUPS[selectedGroup]?.name || ''}）`, 'success')
    } catch {
      addToast('履歴データの読み込みに失敗しました', 'error')
    }
  }, [history, addToast, selectedGroup, addUsersToGroup])

  // --- 履歴削除 ---
  const handleDeleteHistory = useCallback(async (jobId) => {
    const confirmed = await showConfirm({
      title: '履歴の削除',
      message: 'この履歴を削除しますか？この操作は取り消せません。',
      confirmLabel: '削除する',
      danger: true,
    })
    if (!confirmed) return
    try {
      await deleteHistory(jobId)
      fetchHistory()
      addToast('履歴を削除しました', 'info')
    } catch {
      addToast('削除に失敗しました', 'error')
    }
  }, [fetchHistory, showConfirm, addToast])

  // --- 全データクリア ---
  const handleClear = useCallback(async () => {
    const confirmed = await showConfirm({
      title: 'データのクリア',
      message: '読み込んだ全てのユーザーデータをクリアしますか？（比較データも含む）',
      confirmLabel: 'クリアする',
      danger: true,
    })
    if (!confirmed) return
    setUserMap({})
    setImportedFiles([])
    setGroupUserMaps({ amptakcolors: {}, sneakerstep: {}, knightx: {}, meteora: {} })
    setSearchQuery('')
    setFilterMention('')
    setFilterHeart('')
    setFilterDm('')
    setFilterSource('')
    setSortBy('index')
    addToast('データをクリアしました', 'info')
  }, [showConfirm, addToast])

  return (
    <div className="h-screen bg-gray-900 text-white flex flex-col overflow-hidden">
      {/* トースト通知 */}
      <ToastContainer toasts={toasts} removeToast={removeToast} />

      {/* 確認モーダル */}
      <ConfirmModal
        open={confirmState.open}
        title={confirmState.title}
        message={confirmState.message}
        confirmLabel={confirmState.confirmLabel}
        danger={confirmState.danger}
        onConfirm={confirmState.onConfirm}
        onCancel={confirmState.onCancel}
      />

      {/* ヘッダー */}
      <header className="bg-gray-800 border-b border-gray-700 px-6 py-2.5 flex-shrink-0 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h1 className="text-lg font-bold tracking-tight">X Campaign Picker</h1>
          <span className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`} title={connected ? '接続中' : 'オフライン'} />

          {/* メインタブ */}
          <div className="flex bg-gray-700/50 rounded-lg p-0.5 ml-2">
            {TABS.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-3 py-1.5 text-sm rounded-md transition font-medium ${
                  activeTab === tab.id
                    ? 'bg-gray-600 text-white shadow'
                    : 'text-gray-400 hover:text-white'
                }`}
                title={tab.desc}
              >
                {tab.label}
                {tab.id === 'comparison' && (ampUsers.length > 0 || snkUsers.length > 0 || knxUsers.length > 0 || mtorUsers.length > 0) && (
                  <span className="ml-1.5 px-1.5 py-0.5 text-[10px] bg-yellow-600 text-white rounded-full">
                    {ampUsers.length + snkUsers.length + knxUsers.length + mtorUsers.length}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">分析グループ:</span>
          <div className="flex bg-gray-700 rounded-lg p-0.5">
            {Object.entries(GROUPS).map(([id, group]) => {
              const groupCount = Object.keys(groupUserMaps[id] || {}).length
              return (
                <button
                  key={id}
                  onClick={() => { setSelectedGroup(id); setFilterMention('') }}
                  className={`px-3 py-1.5 text-sm rounded-md transition font-medium flex items-center gap-1.5 ${
                    selectedGroup === id
                      ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/20'
                      : 'text-gray-400 hover:text-white hover:bg-gray-600'
                  }`}
                >
                  {group.fanMark} {group.name}
                  {groupCount > 0 && (
                    <span className={`px-1.5 py-0.5 text-[10px] rounded-full font-bold ${
                      selectedGroup === id ? 'bg-white/20' : 'bg-gray-600'
                    }`}>
                      {groupCount}
                    </span>
                  )}
                </button>
              )
            })}
          </div>
        </div>
      </header>

      {/* メインレイアウト */}
      <div className="flex flex-1 overflow-hidden">
        {/* サイドバー */}
        <Sidebar
          jobs={jobs}
          logs={logs}
          connected={connected}
          onStartScrape={handleStartScrape}
          onSelectJob={setSelectedJobId}
          onLoadResults={handleLoadResults}
          selectedJobId={selectedJobId}
          hasRunningJob={hasRunningJob}
          history={history}
          onLoadHistory={handleLoadHistory}
          onDeleteHistory={handleDeleteHistory}
        />

        {/* メインエリア */}
        <main className="flex-1 overflow-y-auto p-6">
          {activeTab === 'analysis' && (
            <AnalysisPanel
              users={users}
              userMap={userMap}
              searchQuery={searchQuery}
              setSearchQuery={setSearchQuery}
              filterMention={filterMention}
              setFilterMention={setFilterMention}
              filterHeart={filterHeart}
              setFilterHeart={setFilterHeart}
              filterDm={filterDm}
              setFilterDm={setFilterDm}
              filterSource={filterSource}
              setFilterSource={setFilterSource}
              sortBy={sortBy}
              setSortBy={setSortBy}
              allFileNames={allFileNames}
              onFileImport={handleFileImport}
              onClear={handleClear}
              importedFiles={importedFiles}
              selectedGroup={selectedGroup}
            />
          )}

          {activeTab === 'comparison' && (
            <ComparisonPanel ampUsers={ampUsers} snkUsers={snkUsers} knxUsers={knxUsers} mtorUsers={mtorUsers} />
          )}
        </main>
      </div>
    </div>
  )
}

export default App
