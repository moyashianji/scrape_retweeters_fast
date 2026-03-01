import { useState } from 'react'
import HelpTip from './HelpTip'

const SCRAPER_TYPES = [
  {
    value: 'retweeters_fast',
    label: 'リポスト取得（高速）',
    icon: '⚡',
    desc: 'リポストしたユーザーを素早く取得します。基本的なプロフィール情報を取得します。',
  },
  {
    value: 'retweeters_hover',
    label: 'リポスト取得（詳細）',
    icon: '🔍',
    desc: 'リポストしたユーザーの詳細情報（DM開放状態など）まで取得します。時間がかかります。',
  },
  {
    value: 'quotes',
    label: '引用ツイート取得',
    icon: '💬',
    desc: '引用ツイートしたユーザーと引用内容を取得します。',
  },
]

export default function ScrapeForm({ onSubmit, disabled }) {
  const [url, setUrl] = useState('')
  const [scraperType, setScraperType] = useState('retweeters_fast')
  const [maxUsers, setMaxUsers] = useState(500)
  const [useCache, setUseCache] = useState(true)

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!url.trim()) return
    onSubmit({ scraperType, url: url.trim(), maxUsers, useCache })
  }

  const selectedType = SCRAPER_TYPES.find(t => t.value === scraperType)

  return (
    <form onSubmit={handleSubmit} className="p-4 border-b border-gray-700 space-y-3">
      <h3 className="font-semibold text-sm text-gray-200 flex items-center gap-2">
        <span className="w-5 h-5 flex items-center justify-center rounded-full bg-blue-600 text-[10px] font-bold">1</span>
        データ取得
        <HelpTip text="XのツイートURLを入力して、リポスト・引用したユーザーの情報を自動で取得します。" />
      </h3>

      <div>
        <label className="block text-xs text-gray-400 mb-1">ツイートのURL</label>
        <input
          type="text"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://x.com/ユーザー/status/..."
          className="w-full p-2.5 bg-gray-700 rounded-lg border border-gray-600 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/30 placeholder:text-gray-500"
          disabled={disabled}
        />
      </div>

      <div>
        <label className="block text-xs text-gray-400 mb-1">
          取得モード
          <HelpTip text="高速: 基本情報のみ素早く取得\n詳細: DM状態なども含めた完全なデータを取得（時間かかる）\n引用: 引用ツイートの内容も含めて取得" />
        </label>
        <div className="space-y-1.5">
          {SCRAPER_TYPES.map(t => (
            <label
              key={t.value}
              className={`flex items-center gap-2.5 p-2 rounded-lg cursor-pointer transition border ${
                scraperType === t.value
                  ? 'bg-blue-600/20 border-blue-500/50'
                  : 'bg-gray-700/50 border-transparent hover:bg-gray-700'
              } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <input
                type="radio"
                name="scraperType"
                value={t.value}
                checked={scraperType === t.value}
                onChange={(e) => setScraperType(e.target.value)}
                disabled={disabled}
                className="sr-only"
              />
              <span className="text-base">{t.icon}</span>
              <span className="text-xs">{t.label}</span>
            </label>
          ))}
        </div>
        {selectedType && (
          <p className="text-[11px] text-gray-500 mt-1.5 pl-1">{selectedType.desc}</p>
        )}
      </div>

      <div>
        <label className="block text-xs text-gray-400 mb-1">
          最大取得数
          <HelpTip text="取得するユーザーの最大数です。多いほど時間がかかります。" />
        </label>
        <input
          type="number"
          value={maxUsers}
          onChange={(e) => setMaxUsers(parseInt(e.target.value) || 500)}
          min={1}
          max={10000}
          className="w-full p-2.5 bg-gray-700 rounded-lg border border-gray-600 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/30"
          disabled={disabled}
        />
      </div>

      <label className={`flex items-center gap-2.5 p-2 rounded-lg cursor-pointer transition hover:bg-gray-700/50 ${disabled ? 'opacity-50' : ''}`}>
        <div className={`relative w-9 h-5 rounded-full transition-colors ${useCache ? 'bg-blue-600' : 'bg-gray-600'}`}>
          <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${useCache ? 'translate-x-4' : 'translate-x-0.5'}`} />
          <input
            type="checkbox"
            checked={useCache}
            onChange={(e) => setUseCache(e.target.checked)}
            disabled={disabled}
            className="sr-only"
          />
        </div>
        <span className="text-xs text-gray-300">過去のデータで補完する</span>
        <HelpTip text="以前取得したユーザーの情報がデータベースにある場合、それを利用して不足データを補完します。" />
      </label>

      <button
        type="submit"
        disabled={disabled || !url.trim()}
        className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg text-sm font-semibold transition flex items-center justify-center gap-2"
      >
        {disabled ? (
          <>
            <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            取得中...
          </>
        ) : (
          '取得を開始'
        )}
      </button>
    </form>
  )
}
