import { useMemo, useState, useRef, useEffect } from 'react'
import { List } from 'react-window'
import { GROUPS, HEART_EMOJIS, parseFollowerCount, computeStatsOnePass, getUserSearchText } from '../constants'
import UserCard from './UserCard'
import HelpTip from './HelpTip'

const FIELD_OPTIONS = [
  { key: 'followers', label: 'フォロワー数' },
  { key: 'following', label: 'フォロー数' },
  { key: 'statuses', label: 'ツイート数' },
  { key: 'favourites', label: 'いいね数' },
  { key: 'media', label: 'メディア数' },
  { key: 'listed', label: 'リスト数' },
  { key: 'created_at', label: '作成日' },
  { key: 'protected', label: '鍵垢/属性' },
  { key: 'bio', label: 'プロフィール' },
  { key: 'quote', label: '引用ツイート' },
  { key: 'location', label: '場所/URL' },
]

function EmptyState({ onFileImport }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="text-6xl mb-6">📊</div>
      <h2 className="text-xl font-bold mb-2">ようこそ！X Campaign Picker へ</h2>
      <p className="text-gray-400 max-w-md mb-8">
        Xのツイートからリポスト・引用したユーザーを分析できるツールです。
        以下の方法でデータを読み込んでください。
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-lg w-full">
        <div className="p-4 bg-gray-800 rounded-xl border border-gray-700 text-left">
          <div className="text-2xl mb-2">⬅️</div>
          <h3 className="font-semibold text-sm mb-1">方法1: 自動取得</h3>
          <p className="text-xs text-gray-400">
            左のパネルにツイートURLを入力して「取得を開始」をクリック。完了後「結果を見る」ボタンを押してください。
          </p>
        </div>
        <label className="p-4 bg-gray-800 rounded-xl border border-gray-700 border-dashed text-left cursor-pointer hover:border-blue-500 hover:bg-gray-750 transition">
          <div className="text-2xl mb-2">📁</div>
          <h3 className="font-semibold text-sm mb-1">方法2: ファイル読込</h3>
          <p className="text-xs text-gray-400">
            JSONファイルをここにドロップ、またはクリックして選択してください。
          </p>
          <input
            type="file"
            accept=".json"
            multiple
            onChange={onFileImport}
            className="hidden"
          />
        </label>
      </div>
    </div>
  )
}

function ActiveFilters({ filterMention, filterHeart, filterDm, filterSource, searchQuery, setFilterMention, setFilterHeart, setFilterDm, setFilterSource, setSearchQuery }) {
  const chips = []
  if (searchQuery) chips.push({ label: `検索: "${searchQuery}"`, clear: () => setSearchQuery('') })
  if (filterMention) chips.push({ label: `ファン: ${filterMention}`, clear: () => setFilterMention('') })
  if (filterHeart) chips.push({ label: `ハート: ${filterHeart}`, clear: () => setFilterHeart('') })
  if (filterDm) chips.push({ label: `DM: ${filterDm === 'open' ? '開放' : '閉鎖'}`, clear: () => setFilterDm('') })
  if (filterSource) chips.push({ label: `ソース: ${filterSource}`, clear: () => setFilterSource('') })

  if (chips.length === 0) return null

  return (
    <div className="flex flex-wrap gap-2 mb-4">
      {chips.map((chip, i) => (
        <span key={i} className="inline-flex items-center gap-1.5 px-3 py-1 bg-blue-600/20 border border-blue-500/30 rounded-full text-xs text-blue-300">
          {chip.label}
          <button
            onClick={chip.clear}
            className="w-4 h-4 flex items-center justify-center rounded-full hover:bg-blue-500/30 text-blue-400 hover:text-white transition"
          >
            ×
          </button>
        </span>
      ))}
      {chips.length > 1 && (
        <button
          onClick={() => { setFilterMention(''); setFilterHeart(''); setFilterDm(''); setSearchQuery(''); setFilterSource('') }}
          className="px-3 py-1 text-xs text-red-400 hover:text-red-300 hover:bg-red-600/10 rounded-full transition"
        >
          全てクリア
        </button>
      )}
    </div>
  )
}

// --- 仮想スクロール用の行コンポーネント ---
const UserRow = ({ index, style, data }) => {
  const { filteredUsers, allFileNames, visibleFields, selectedGroup, compactCards } = data
  const user = filteredUsers[index]
  return (
    <div style={{ ...style, paddingBottom: '8px' }}>
      <UserCard
        user={user}
        showSources={allFileNames.length > 1}
        visibleFields={visibleFields}
        selectedGroup={selectedGroup}
        compact={compactCards}
      />
    </div>
  )
}

export default function AnalysisPanel({
  users, userMap,
  searchQuery, setSearchQuery,
  filterMention, setFilterMention,
  filterHeart, setFilterHeart,
  filterDm, setFilterDm,
  filterSource, setFilterSource,
  sortBy, setSortBy,
  allFileNames,
  onFileImport, onClear,
  importedFiles,
  selectedGroup,
}) {
  const officialAccounts = useMemo(() => GROUPS[selectedGroup]?.members || {}, [selectedGroup])
  const [visibleFields, setVisibleFields] = useState(() => {
    const defaults = {}
    FIELD_OPTIONS.forEach(f => { defaults[f.key] = true })
    return defaults
  })
  const [showFieldSettings, setShowFieldSettings] = useState(false)
  const [statsCollapsed, setStatsCollapsed] = useState(false)
  const [compactCards, setCompactCards] = useState(false)

  // 仮想スクロール用
  const listRef = useRef(null)
  const containerRef = useRef(null)
  const [listHeight, setListHeight] = useState(600)

  // コンテナの高さを測定
  useEffect(() => {
    if (!containerRef.current) return
    const obs = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setListHeight(entry.contentRect.height)
      }
    })
    obs.observe(containerRef.current)
    return () => obs.disconnect()
  }, [users.length > 0])

  // フィルター/ソート変更時にリストを先頭に戻す
  useEffect(() => {
    listRef.current?.scrollTo(0)
  }, [searchQuery, filterMention, filterHeart, filterDm, filterSource, sortBy])

  // === 統計: 1パスで全集計 ===
  const stats = useMemo(() => {
    if (users.length === 0) return null
    return computeStatsOnePass(users, officialAccounts, selectedGroup)
  }, [users, officialAccounts, selectedGroup])

  // === フィルタリング（fanMapキャッシュを利用） ===
  const filteredUsers = useMemo(() => {
    let result = [...users]

    if (searchQuery) {
      const q = searchQuery.toLowerCase()
      result = result.filter(user => {
        const text = getUserSearchText(user)
        return text.toLowerCase().includes(q) ||
          (user.username || '').toLowerCase().includes(q)
      })
    }

    if (filterMention && officialAccounts[filterMention] && stats) {
      // fanMap からキャッシュ利用（detectFanOf再計算不要）
      result = result.filter(user => {
        const fans = stats.fanMap.get(user.username)
        return fans && fans.includes(filterMention)
      })
    }

    if (filterHeart) {
      result = result.filter(user => {
        const text = getUserSearchText(user)
        return text.includes(filterHeart)
      })
    }

    if (filterDm === 'open') {
      result = result.filter(user => user.can_dm === true)
    } else if (filterDm === 'closed') {
      result = result.filter(user => user.can_dm === false)
    }

    if (filterSource) {
      result = result.filter(user => (user._sources || []).includes(filterSource))
    }

    if (sortBy === 'username') {
      result.sort((a, b) => (a.username || '').localeCompare(b.username || ''))
    } else if (sortBy === 'name') {
      result.sort((a, b) => (a.name || '').localeCompare(b.name || ''))
    } else if (sortBy === 'followers') {
      result.sort((a, b) => parseFollowerCount(b.followers_count) - parseFollowerCount(a.followers_count))
    } else if (sortBy === 'following') {
      result.sort((a, b) => parseFollowerCount(b.following_count) - parseFollowerCount(a.following_count))
    } else if (sortBy === 'statuses') {
      result.sort((a, b) => (b.statuses_count || 0) - (a.statuses_count || 0))
    } else if (sortBy === 'favourites') {
      result.sort((a, b) => (b.favourites_count || 0) - (a.favourites_count || 0))
    } else if (sortBy === 'created') {
      result.sort((a, b) => {
        const da = a.created_at ? new Date(a.created_at).getTime() : 0
        const db = b.created_at ? new Date(b.created_at).getTime() : 0
        return db - da
      })
    } else if (sortBy === 'dm') {
      result.sort((a, b) => {
        const dmVal = (v) => v === true ? 2 : v === false ? 1 : 0
        return dmVal(b.can_dm) - dmVal(a.can_dm)
      })
    }

    return result
  }, [users, searchQuery, filterMention, filterHeart, filterDm, filterSource, sortBy, officialAccounts, stats])

  // 行の高さ（固定サイズ）
  const itemSize = compactCards ? 48 : 180

  // List に渡すデータ
  const itemData = useMemo(() => ({
    filteredUsers,
    allFileNames,
    visibleFields,
    selectedGroup,
    compactCards,
  }), [filteredUsers, allFileNames, visibleFields, selectedGroup, compactCards])

  // 空状態
  if (users.length === 0) {
    return <EmptyState onFileImport={onFileImport} />
  }

  return (
    <div className="flex flex-col h-full">
      {/* ヘッダーバー */}
      <div className="mb-4 p-4 bg-gray-800 rounded-xl flex items-center justify-between flex-shrink-0">
        <div>
          <h2 className="text-lg font-bold flex items-center gap-2">
            📊 分析結果
            <span className="text-sm font-normal text-gray-400">
              {users.length.toLocaleString()}人のデータ
            </span>
          </h2>
          {importedFiles.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1">
              {importedFiles.map((f, i) => (
                <span key={i} className="px-2 py-0.5 text-[11px] bg-gray-700 rounded">{f.name} ({f.count})</span>
              ))}
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          <label className="cursor-pointer">
            <span className="px-3 py-1.5 text-xs bg-blue-600 hover:bg-blue-700 rounded-lg transition font-medium inline-block">
              + ファイル追加
            </span>
            <input type="file" accept=".json" multiple onChange={onFileImport} className="hidden" />
          </label>
          <button onClick={onClear} className="px-3 py-1.5 text-xs bg-gray-700 hover:bg-red-600 rounded-lg transition">
            クリア
          </button>
        </div>
      </div>

      {/* アクティブフィルターチップ */}
      <ActiveFilters
        filterMention={filterMention} filterHeart={filterHeart} filterDm={filterDm}
        filterSource={filterSource} searchQuery={searchQuery}
        setFilterMention={setFilterMention} setFilterHeart={setFilterHeart} setFilterDm={setFilterDm}
        setFilterSource={setFilterSource} setSearchQuery={setSearchQuery}
      />

      {/* 統計セクション（折りたたみ可能） */}
      <div className="mb-4 flex-shrink-0">
        <button
          onClick={() => setStatsCollapsed(!statsCollapsed)}
          className="flex items-center gap-2 text-sm font-semibold text-gray-300 mb-3 hover:text-white transition"
        >
          <span>{statsCollapsed ? '▶' : '▼'}</span>
          統計・フィルター
          <HelpTip text="各項目をクリックすると、その条件でユーザーを絞り込めます。もう一度クリックで解除します。" />
        </button>

        {!statsCollapsed && (
          <>
            {/* DM統計 */}
            {stats && (stats.dmStats.open > 0 || stats.dmStats.closed > 0) && (
              <div className="mb-4 p-4 bg-gray-800 rounded-xl">
                <h3 className="text-sm font-semibold mb-2 flex items-center gap-1.5">
                  ✉ DM開放状態
                  <HelpTip text="DM開放: ダイレクトメッセージを送れるユーザー\nDM閉鎖: DMを受け付けていないユーザー" />
                </h3>
                <div className="flex gap-3">
                  <div
                    className={`flex-1 flex items-center justify-between p-2.5 rounded-lg cursor-pointer transition ${
                      filterDm === 'open' ? 'bg-green-600 shadow-lg shadow-green-600/20' : 'bg-gray-700 hover:bg-gray-600'
                    }`}
                    onClick={() => setFilterDm(filterDm === 'open' ? '' : 'open')}
                  >
                    <span className="text-sm">開放</span>
                    <span className="font-bold text-xl">{stats.dmStats.open}</span>
                  </div>
                  <div
                    className={`flex-1 flex items-center justify-between p-2.5 rounded-lg cursor-pointer transition ${
                      filterDm === 'closed' ? 'bg-red-600 shadow-lg shadow-red-600/20' : 'bg-gray-700 hover:bg-gray-600'
                    }`}
                    onClick={() => setFilterDm(filterDm === 'closed' ? '' : 'closed')}
                  >
                    <span className="text-sm">閉鎖</span>
                    <span className="font-bold text-xl">{stats.dmStats.closed}</span>
                  </div>
                  <div className="flex-1 flex items-center justify-between p-2.5 rounded-lg bg-gray-700/50">
                    <span className="text-sm text-gray-500">不明</span>
                    <span className="font-bold text-xl text-gray-500">{stats.dmStats.unknown}</span>
                  </div>
                </div>
              </div>
            )}

            {/* ファンマーク + ハート */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
              <div className="p-4 bg-gray-800 rounded-xl">
                <h3 className="text-sm font-semibold mb-2 flex items-center gap-1.5">
                  📌 ファンマーク
                  <HelpTip text="ユーザーのプロフィールや名前にメンバーの情報が含まれている人数です。クリックで絞り込みできます。" />
                </h3>
                <div className="space-y-1.5">
                  {stats && Object.entries(stats.mentionCounts)
                    .sort((a, b) => b[1].count - a[1].count)
                    .map(([name, data]) => (
                      <div
                        key={name}
                        className={`flex items-center justify-between p-2 rounded-lg cursor-pointer transition ${
                          filterMention === name ? 'bg-blue-600 shadow-lg shadow-blue-600/20' : 'bg-gray-700 hover:bg-gray-600'
                        }`}
                        onClick={() => setFilterMention(filterMention === name ? '' : name)}
                      >
                        <span className="text-sm">
                          {officialAccounts[name]?.fanMark && (
                            <span className="mr-1.5">{officialAccounts[name].fanMark}</span>
                          )}
                          {name}
                        </span>
                        <span className="font-bold text-lg">{data.count}</span>
                      </div>
                    ))}
                </div>
              </div>

              <div className="p-4 bg-gray-800 rounded-xl">
                <h3 className="text-sm font-semibold mb-2 flex items-center gap-1.5">
                  🎯 絵文字・ハート
                  <HelpTip text="プロフィールに含まれる絵文字の統計です。グループ絵文字とハート絵文字で絞り込みできます。" />
                </h3>

                {/* グループ絵文字 */}
                {stats && Object.keys(stats.groupEmojiCounts).length > 0 && (
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
                              <span className="text-lg mr-1.5">{emoji}</span>
                              <span className="text-xs text-gray-300">{data.name}</span>
                            </span>
                            <span className={`font-bold ${data.count > 0 ? '' : 'text-gray-600'}`}>{data.count}</span>
                          </div>
                        ))}
                    </div>
                  </>
                )}

                {/* ハート絵文字 */}
                <p className="text-[11px] text-gray-500 mb-1.5 font-medium">ハート絵文字</p>
                <div className="grid grid-cols-2 gap-1.5">
                  {stats && Object.entries(stats.heartCounts)
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
                          <span className="text-lg mr-1.5">{emoji}</span>
                          <span className="text-xs text-gray-300">{data.name}</span>
                        </span>
                        <span className="font-bold">{data.count}</span>
                      </div>
                    ))}
                </div>
              </div>
            </div>
          </>
        )}
      </div>

      {/* 検索・ソート・表示設定 */}
      <div className="mb-4 p-4 bg-gray-800 rounded-xl flex-shrink-0">
        <div className="flex flex-wrap gap-3 items-end">
          <div className="flex-1 min-w-56">
            <label className="block text-xs text-gray-400 mb-1">検索</label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 text-sm">🔍</span>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="ユーザー名・名前・プロフ・引用..."
                className="w-full p-2.5 pl-9 bg-gray-700 rounded-lg border border-gray-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/30 text-sm"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-2 top-1/2 -translate-y-1/2 w-5 h-5 flex items-center justify-center rounded-full hover:bg-gray-600 text-gray-400 text-xs"
                >
                  ×
                </button>
              )}
            </div>
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">並び替え</label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="p-2.5 bg-gray-700 rounded-lg border border-gray-600 text-sm"
            >
              <option value="index">取得順</option>
              <option value="username">ユーザー名</option>
              <option value="name">表示名</option>
              <option value="followers">フォロワー数</option>
              <option value="following">フォロー中</option>
              <option value="statuses">ツイート数</option>
              <option value="favourites">いいね数</option>
              <option value="created">作成日(新しい順)</option>
              <option value="dm">DM開放順</option>
            </select>
          </div>
          {allFileNames.length > 1 && (
            <div>
              <label className="block text-xs text-gray-400 mb-1">データソース</label>
              <select
                value={filterSource}
                onChange={(e) => setFilterSource(e.target.value)}
                className="p-2.5 bg-gray-700 rounded-lg border border-gray-600 text-sm"
              >
                <option value="">全て</option>
                {allFileNames.map(name => (
                  <option key={name} value={name}>{name}</option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* 表示設定 */}
        <div className="mt-3 pt-3 border-t border-gray-700 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowFieldSettings(!showFieldSettings)}
              className="text-xs text-gray-400 hover:text-gray-200 transition flex items-center gap-1"
            >
              ⚙ 表示項目 {showFieldSettings ? '▼' : '▶'}
            </button>
            <button
              onClick={() => setCompactCards(!compactCards)}
              className={`text-xs px-2 py-0.5 rounded transition ${compactCards ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-400 hover:text-gray-200'}`}
            >
              {compactCards ? '📋 コンパクト' : '📄 詳細'}
            </button>
          </div>
          <span className="text-sm text-gray-400">
            {filteredUsers.length.toLocaleString()} / {users.length.toLocaleString()}人
          </span>
        </div>

        {showFieldSettings && (
          <div className="flex flex-wrap gap-x-4 gap-y-1.5 mt-3 p-3 bg-gray-700/50 rounded-lg">
            {FIELD_OPTIONS.map(f => (
              <label key={f.key} className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={visibleFields[f.key] !== false}
                  onChange={(e) => setVisibleFields(prev => ({ ...prev, [f.key]: e.target.checked }))}
                  className="w-3.5 h-3.5 rounded bg-gray-600 border-gray-500 text-blue-500 accent-blue-500"
                />
                <span className="text-xs text-gray-300">{f.label}</span>
              </label>
            ))}
            <span className="flex gap-2 ml-auto">
              <button
                onClick={() => {
                  const all = {}
                  FIELD_OPTIONS.forEach(f => { all[f.key] = true })
                  setVisibleFields(all)
                }}
                className="text-xs text-blue-400 hover:underline"
              >
                全ON
              </button>
              <button
                onClick={() => {
                  const none = {}
                  FIELD_OPTIONS.forEach(f => { none[f.key] = false })
                  setVisibleFields(none)
                }}
                className="text-xs text-red-400 hover:underline"
              >
                全OFF
              </button>
            </span>
          </div>
        )}
      </div>

      {/* ユーザー一覧（仮想スクロール） */}
      {filteredUsers.length === 0 ? (
        <div className="text-center py-12 text-gray-500 flex-shrink-0">
          <div className="text-4xl mb-3">🔍</div>
          <p className="text-sm">条件に一致するユーザーが見つかりません</p>
          <p className="text-xs mt-1">フィルター条件を変更してみてください</p>
        </div>
      ) : (
        <div ref={containerRef} className="flex-1 min-h-0">
          <List
            ref={listRef}
            height={listHeight}
            itemCount={filteredUsers.length}
            itemSize={itemSize}
            itemData={itemData}
            overscanCount={10}
            className="scrollbar-thin"
          >
            {UserRow}
          </List>
        </div>
      )}
    </div>
  )
}
