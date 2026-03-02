import HelpTip from './HelpTip'

export default function StatsFilterPanel({
  stats,
  officialAccounts,
  filterMention, setFilterMention,
  filterHeart, setFilterHeart,
  filterDm, setFilterDm,
  isOpen, onToggle,
}) {
  if (!isOpen) {
    return (
      <aside className="w-12 bg-gray-800 border-l border-gray-700 flex flex-col items-center py-3 flex-shrink-0">
        <button
          onClick={onToggle}
          className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-700 transition text-gray-400 hover:text-white"
          title="統計パネルを開く"
        >
          ◀
        </button>
      </aside>
    )
  }

  return (
    <aside className="w-80 bg-gray-800 border-l border-gray-700 flex flex-col overflow-hidden flex-shrink-0">
      {/* ヘッダー */}
      <div className="p-3 border-b border-gray-700 flex items-center justify-between flex-shrink-0">
        <h3 className="text-sm font-semibold flex items-center gap-1.5">
          📊 統計・フィルター
          <HelpTip text="各項目をクリックすると、その条件でユーザーを絞り込めます。もう一度クリックで解除します。" />
        </h3>
        <button
          onClick={onToggle}
          className="w-7 h-7 flex items-center justify-center rounded-lg hover:bg-gray-700 transition text-gray-400 hover:text-white text-xs"
          title="統計パネルを閉じる"
        >
          ✕
        </button>
      </div>

      {/* スクロール可能なコンテンツ */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {!stats ? (
          <p className="text-sm text-gray-500 text-center py-8">データを読み込むと統計が表示されます</p>
        ) : (
          <>
            {/* DM統計 */}
            {(stats.dmStats.open > 0 || stats.dmStats.closed > 0) && (
              <div className="p-3 bg-gray-700/50 rounded-xl">
                <h3 className="text-sm font-semibold mb-2 flex items-center gap-1.5">
                  ✉ DM開放状態
                  <HelpTip text="DM開放: ダイレクトメッセージを送れるユーザー\nDM閉鎖: DMを受け付けていないユーザー" />
                </h3>
                <div className="space-y-1.5">
                  <div
                    className={`flex items-center justify-between p-2.5 rounded-lg cursor-pointer transition ${
                      filterDm === 'open' ? 'bg-green-600 shadow-lg shadow-green-600/20' : 'bg-gray-700 hover:bg-gray-600'
                    }`}
                    onClick={() => setFilterDm(filterDm === 'open' ? '' : 'open')}
                  >
                    <span className="text-sm">開放</span>
                    <span className="font-bold text-lg">{stats.dmStats.open}</span>
                  </div>
                  <div
                    className={`flex items-center justify-between p-2.5 rounded-lg cursor-pointer transition ${
                      filterDm === 'closed' ? 'bg-red-600 shadow-lg shadow-red-600/20' : 'bg-gray-700 hover:bg-gray-600'
                    }`}
                    onClick={() => setFilterDm(filterDm === 'closed' ? '' : 'closed')}
                  >
                    <span className="text-sm">閉鎖</span>
                    <span className="font-bold text-lg">{stats.dmStats.closed}</span>
                  </div>
                  <div className="flex items-center justify-between p-2.5 rounded-lg bg-gray-700/30">
                    <span className="text-sm text-gray-500">不明</span>
                    <span className="font-bold text-lg text-gray-500">{stats.dmStats.unknown}</span>
                  </div>
                </div>
              </div>
            )}

            {/* ファンマーク */}
            <div className="p-3 bg-gray-700/50 rounded-xl">
              <h3 className="text-sm font-semibold mb-2 flex items-center gap-1.5">
                📌 ファンマーク
                <HelpTip text="ユーザーのプロフィールや名前にメンバーの情報が含まれている人数です。クリックで絞り込みできます。" />
              </h3>
              <div className="space-y-1.5">
                {Object.entries(stats.mentionCounts)
                  .sort((a, b) => b[1].count - a[1].count)
                  .map(([name, data]) => (
                    <div
                      key={name}
                      className={`flex items-center justify-between p-2 rounded-lg cursor-pointer transition ${
                        filterMention === name ? 'bg-blue-600 shadow-lg shadow-blue-600/20' : 'bg-gray-700 hover:bg-gray-600'
                      }`}
                      onClick={() => setFilterMention(filterMention === name ? '' : name)}
                    >
                      <span className="text-sm truncate mr-2">
                        {officialAccounts[name]?.fanMark && (
                          <span className="mr-1">{officialAccounts[name].fanMark}</span>
                        )}
                        {name}
                      </span>
                      <span className="font-bold text-lg flex-shrink-0">{data.count}</span>
                    </div>
                  ))}
              </div>
            </div>

            {/* 絵文字・ハート */}
            <div className="p-3 bg-gray-700/50 rounded-xl">
              <h3 className="text-sm font-semibold mb-2 flex items-center gap-1.5">
                🎯 絵文字・ハート
                <HelpTip text="プロフィールに含まれる絵文字の統計です。グループ絵文字とハート絵文字で絞り込みできます。" />
              </h3>

              {/* グループ絵文字 */}
              {Object.keys(stats.groupEmojiCounts).length > 0 && (
                <>
                  <p className="text-[11px] text-gray-500 mb-1.5 font-medium">グループ絵文字</p>
                  <div className="grid grid-cols-2 gap-1.5 mb-3">
                    {Object.entries(stats.groupEmojiCounts)
                      .sort((a, b) => b[1].count - a[1].count)
                      .map(([emoji, data]) => (
                        <div
                          key={emoji}
                          className={`flex items-center justify-between p-2 rounded-lg cursor-pointer transition ${
                            filterHeart === emoji ? 'bg-blue-600 shadow-lg shadow-blue-600/20' : 'bg-gray-700 hover:bg-gray-600'
                          }`}
                          onClick={() => setFilterHeart(filterHeart === emoji ? '' : emoji)}
                        >
                          <span>
                            <span className="text-lg mr-1">{emoji}</span>
                            <span className="text-[11px] text-gray-300">{data.name}</span>
                          </span>
                          <span className={`font-bold text-sm ${data.count > 0 ? '' : 'text-gray-600'}`}>{data.count}</span>
                        </div>
                      ))}
                  </div>
                </>
              )}

              {/* ハート絵文字 */}
              <p className="text-[11px] text-gray-500 mb-1.5 font-medium">ハート絵文字</p>
              <div className="grid grid-cols-2 gap-1.5">
                {Object.entries(stats.heartCounts)
                  .filter(([, data]) => data.count > 0)
                  .sort((a, b) => b[1].count - a[1].count)
                  .map(([emoji, data]) => (
                    <div
                      key={emoji}
                      className={`flex items-center justify-between p-2 rounded-lg cursor-pointer transition ${
                        filterHeart === emoji ? 'bg-blue-600 shadow-lg shadow-blue-600/20' : 'bg-gray-700 hover:bg-gray-600'
                      }`}
                      onClick={() => setFilterHeart(filterHeart === emoji ? '' : emoji)}
                    >
                      <span>
                        <span className="text-lg mr-1">{emoji}</span>
                        <span className="text-[11px] text-gray-300">{data.name}</span>
                      </span>
                      <span className="font-bold text-sm">{data.count}</span>
                    </div>
                  ))}
              </div>
            </div>
          </>
        )}
      </div>
    </aside>
  )
}
