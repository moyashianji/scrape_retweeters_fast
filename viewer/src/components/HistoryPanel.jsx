import { useState } from 'react'
import { getHistoryCsvUrl } from '../api'

const TYPE_LABELS = {
  retweeters_fast: '⚡ 高速',
  retweeters_hover: '🔍 詳細',
  quotes: '💬 引用',
}

function formatDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  const hh = String(d.getHours()).padStart(2, '0')
  const mi = String(d.getMinutes()).padStart(2, '0')
  return `${mm}/${dd} ${hh}:${mi}`
}

export default function HistoryPanel({ history, onLoadHistory, onDeleteHistory }) {
  const [expanded, setExpanded] = useState(true)

  if (!history || history.length === 0) {
    return null
  }

  return (
    <div className="border-t border-gray-700">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-2 flex items-center justify-between text-sm font-semibold text-gray-200 hover:bg-gray-700/50 transition"
      >
        <span className="flex items-center gap-2">
          <span className="w-5 h-5 flex items-center justify-center rounded-full bg-blue-600 text-[10px] font-bold">3</span>
          過去の履歴
          <span className="text-xs text-gray-500 font-normal">({history.length}件)</span>
        </span>
        <span className="text-xs text-gray-500">{expanded ? '▼' : '▶'}</span>
      </button>

      {expanded && (
        <div className="max-h-56 overflow-y-auto divide-y divide-gray-700/50">
          {history.map(job => (
            <div key={job.id} className="p-3 hover:bg-gray-700/30 transition">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-400">{formatDate(job.created_at)}</span>
                  <span className="text-[11px] px-1.5 py-0.5 bg-gray-600 rounded">
                    {TYPE_LABELS[job.scraper_type] || job.scraper_type}
                  </span>
                </div>
                <span className={`text-xs font-medium ${job.status === 'completed' ? 'text-green-400' : 'text-red-400'}`}>
                  {job.result_count}人
                </span>
              </div>

              <p className="text-[11px] text-gray-500 mt-1 truncate" title={job.url}>
                {job.url}
              </p>

              <div className="flex gap-2 mt-2">
                {job.status === 'completed' && job.result_count > 0 && (
                  <>
                    <button
                      onClick={() => onLoadHistory(job.id)}
                      className="px-2.5 py-1 text-xs bg-green-600 hover:bg-green-700 rounded-lg transition font-medium"
                    >
                      📊 結果を見る
                    </button>
                    <a
                      href={getHistoryCsvUrl(job.id)}
                      download
                      className="px-2.5 py-1 text-xs bg-purple-600 hover:bg-purple-700 rounded-lg transition font-medium"
                    >
                      CSV保存
                    </a>
                  </>
                )}
                <button
                  onClick={() => onDeleteHistory(job.id)}
                  className="px-2.5 py-1 text-xs bg-gray-700 hover:bg-red-700 text-gray-400 hover:text-white rounded-lg transition"
                >
                  削除
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
