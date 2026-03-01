import { getCsvDownloadUrl } from '../api'

const STATUS_INFO = {
  pending: { icon: '⏳', label: '待機中', color: 'text-yellow-400' },
  running: { icon: '🔄', label: '実行中', color: 'text-blue-400' },
  completed: { icon: '✅', label: '完了', color: 'text-green-400' },
  failed: { icon: '❌', label: 'エラー', color: 'text-red-400' },
  cancelled: { icon: '🚫', label: '中止', color: 'text-gray-500' },
}

const TYPE_LABELS = {
  retweeters_fast: '⚡ リポスト(高速)',
  retweeters_hover: '🔍 リポスト(詳細)',
  quotes: '💬 引用ツイート',
}

export default function JobList({ jobs, selectedJobId, onSelect, onLoadResults }) {
  if (jobs.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500 text-sm">
        <p className="text-2xl mb-2">📋</p>
        <p>まだジョブがありません</p>
        <p className="text-xs mt-1">上のフォームからデータ取得を開始してください</p>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <h3 className="px-4 py-2 font-semibold text-sm text-gray-200 border-b border-gray-700 flex items-center gap-2">
        <span className="w-5 h-5 flex items-center justify-center rounded-full bg-blue-600 text-[10px] font-bold">2</span>
        実行状況
        <span className="text-xs text-gray-500 font-normal">({jobs.length}件)</span>
      </h3>
      <div className="divide-y divide-gray-700">
        {jobs.map(job => {
          const status = STATUS_INFO[job.status] || STATUS_INFO.pending
          return (
            <div
              key={job.id}
              className={`p-3 cursor-pointer transition hover:bg-gray-700 ${
                selectedJobId === job.id ? 'bg-gray-700 border-l-2 border-blue-500' : 'border-l-2 border-transparent'
              }`}
              onClick={() => onSelect(job.id)}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 min-w-0">
                  <span>{status.icon}</span>
                  <span className="text-xs text-gray-400">
                    {TYPE_LABELS[job.scraper_type] || job.scraper_type}
                  </span>
                </div>
                <span className={`text-xs font-medium ${status.color}`}>
                  {status.label}
                </span>
              </div>

              <p className="text-[11px] text-gray-500 mt-1 truncate" title={job.url}>
                {job.url}
              </p>

              {job.status === 'completed' && job.result_count > 0 && (
                <div className="flex gap-2 mt-2">
                  <button
                    onClick={(e) => { e.stopPropagation(); onLoadResults(job.id) }}
                    className="px-3 py-1 text-xs bg-green-600 hover:bg-green-700 rounded-lg transition font-medium flex items-center gap-1"
                  >
                    📊 結果を見る ({job.result_count}人)
                  </button>
                  <a
                    href={getCsvDownloadUrl(job.id)}
                    download
                    onClick={(e) => e.stopPropagation()}
                    className="px-3 py-1 text-xs bg-purple-600 hover:bg-purple-700 rounded-lg transition font-medium"
                  >
                    CSV保存
                  </a>
                </div>
              )}

              {job.status === 'running' && (
                <div className="mt-2">
                  <div className="w-full h-1.5 bg-gray-600 rounded-full overflow-hidden">
                    <div className="h-full bg-blue-500 rounded-full animate-pulse" style={{ width: '100%' }} />
                  </div>
                  <p className="text-[10px] text-blue-400 mt-1">処理中です...ログで進捗を確認できます</p>
                </div>
              )}

              {job.error && (
                <p className="text-xs text-red-400 mt-1 truncate">{job.error}</p>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
