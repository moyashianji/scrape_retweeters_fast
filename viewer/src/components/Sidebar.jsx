import { useState } from 'react'
import ScrapeForm from './ScrapeForm'
import JobList from './JobList'
import HistoryPanel from './HistoryPanel'
import LogPanel from './LogPanel'

export default function Sidebar({
  jobs, logs, connected,
  onStartScrape, onSelectJob, onLoadResults,
  selectedJobId, hasRunningJob,
  history, onLoadHistory, onDeleteHistory,
  importedFiles,
}) {
  const [collapsed, setCollapsed] = useState(false)

  if (collapsed) {
    return (
      <aside className="w-12 bg-gray-800 border-r border-gray-700 flex flex-col items-center py-3 flex-shrink-0">
        <button
          onClick={() => setCollapsed(false)}
          className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-700 transition text-gray-400 hover:text-white"
          title="サイドバーを開く"
        >
          ▶
        </button>
      </aside>
    )
  }

  return (
    <aside className="w-80 bg-gray-800 border-r border-gray-700 flex flex-col overflow-hidden flex-shrink-0">
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-700">
        <span className="text-xs text-gray-500">操作パネル</span>
        <button
          onClick={() => setCollapsed(true)}
          className="w-6 h-6 flex items-center justify-center rounded hover:bg-gray-700 transition text-gray-500 hover:text-white text-xs"
          title="サイドバーを閉じる"
        >
          ◀
        </button>
      </div>
      <div className="flex-1 overflow-y-auto">
        <ScrapeForm onSubmit={onStartScrape} disabled={hasRunningJob} />
        <JobList
          jobs={jobs}
          selectedJobId={selectedJobId}
          onSelect={onSelectJob}
          onLoadResults={onLoadResults}
        />
        <HistoryPanel
          history={history}
          onLoadHistory={onLoadHistory}
          onDeleteHistory={onDeleteHistory}
        />
        {/* 読み込み済みファイル一覧 */}
        {importedFiles && importedFiles.length > 0 && (
          <div className="border-t border-gray-700">
            <div className="px-4 py-2 text-sm font-semibold text-gray-200 flex items-center gap-2">
              <span className="w-5 h-5 flex items-center justify-center rounded-full bg-purple-600 text-[10px] font-bold">📁</span>
              読込済みデータ
              <span className="text-xs text-gray-500 font-normal">({importedFiles.length}件)</span>
            </div>
            <div className="max-h-40 overflow-y-auto divide-y divide-gray-700/50">
              {importedFiles.map((f, i) => (
                <div key={i} className="px-4 py-2 text-xs text-gray-400 flex items-center justify-between">
                  <span className="truncate mr-2" title={f.name}>{f.name}</span>
                  <span className="text-gray-500 flex-shrink-0">{f.count}人</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
      <LogPanel
        logs={logs}
        selectedJobId={selectedJobId}
        connected={connected}
      />
    </aside>
  )
}
