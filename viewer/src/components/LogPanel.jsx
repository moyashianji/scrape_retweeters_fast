import { useEffect, useRef, useState } from 'react'

export default function LogPanel({ logs, selectedJobId, connected }) {
  const logLines = selectedJobId ? (logs[selectedJobId] || []) : []
  const bottomRef = useRef(null)
  const containerRef = useRef(null)
  const [collapsed, setCollapsed] = useState(true)

  useEffect(() => {
    if (logLines.length > 0 && collapsed) {
      setCollapsed(false)
    }
  }, [logLines.length > 0])

  useEffect(() => {
    if (containerRef.current) {
      const el = containerRef.current
      const isNearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 100
      if (isNearBottom) {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
      }
    }
  }, [logLines.length])

  return (
    <div className={`border-t border-gray-700 flex flex-col flex-shrink-0 transition-all ${collapsed ? '' : 'h-48'}`}>
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="px-4 py-2 text-xs font-semibold text-gray-400 border-b border-gray-700 flex items-center justify-between hover:bg-gray-700/50 transition"
      >
        <span className="flex items-center gap-2">
          ログ
          {selectedJobId && <span className="text-gray-500">#{selectedJobId}</span>}
          {logLines.length > 0 && (
            <span className="px-1.5 py-0.5 bg-gray-600 rounded text-[10px]">{logLines.length}行</span>
          )}
        </span>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1">
            <div className={`w-1.5 h-1.5 rounded-full ${connected ? 'bg-green-400' : 'bg-red-400'}`} />
            <span className="text-gray-500">{connected ? '接続中' : 'オフライン'}</span>
          </div>
          <span>{collapsed ? '▶' : '▼'}</span>
        </div>
      </button>
      {!collapsed && (
        <div
          ref={containerRef}
          className="flex-1 overflow-y-auto p-2 font-mono text-xs leading-relaxed bg-gray-950"
        >
          {logLines.length === 0 ? (
            <p className="text-gray-600 text-center mt-4">
              {selectedJobId ? 'ログを待機中...' : 'ジョブを選択するとログが表示されます'}
            </p>
          ) : (
            logLines.map((line, i) => (
              <div key={i} className="text-green-400 whitespace-pre-wrap hover:bg-gray-900 px-1">
                {line}
              </div>
            ))
          )}
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  )
}
