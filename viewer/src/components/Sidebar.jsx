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
      </div>
      <LogPanel
        logs={logs}
        selectedJobId={selectedJobId}
        connected={connected}
      />
    </aside>
  )
}
