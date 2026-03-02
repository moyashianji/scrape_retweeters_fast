import { useMemo, useState, useCallback, useRef, useEffect } from 'react'
import { VariableSizeList } from 'react-window'
import { GROUPS, parseFollowerCount, getUserSearchText } from '../constants'
import UserCard from './UserCard'

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
    <div className="flex flex-wrap gap-2 mb-3">
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
  users, userMap, stats,
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
  const [compactCards, setCompactCards] = useState(false)

  // 仮想スクロール用
  const listRef = useRef(null)
  const outerRef = useRef(null)
  const controlsRef = useRef(null)
  const [listHeight, setListHeight] = useState(400)

  // リスト高さを算出（outer全体 - controls部分 = リスト領域）
  useEffect(() => {
    const outer = outerRef.current
    const controls = controlsRef.current
    if (!outer || !controls) return

    const updateHeight = () => {
      let parentH = outer.clientHeight
      if (parentH < 50) {
        parentH = window.innerHeight - outer.getBoundingClientRect().top
      }
      const controlsH = controls.offsetHeight
      const h = parentH - controlsH
      if (h > 100) setListHeight(Math.floor(h))
    }

    updateHeight()
    const timer = setTimeout(updateHeight, 100)

    const obs = new ResizeObserver(updateHeight)
    obs.observe(outer)
    obs.observe(controls)
    window.addEventListener('resize', updateHeight)

    return () => {
      obs.disconnect()
      window.removeEventListener('resize', updateHeight)
      clearTimeout(timer)
    }
  }, [users.length > 0])

  // フィルター/ソート変更時にリストを先頭に戻す
  useEffect(() => {
    listRef.current?.scrollTo(0)
  }, [searchQuery, filterMention, filterHeart, filterDm, filterSource, sortBy])

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

  // 行の高さ推定
  const getItemSize = useCallback((index) => {
    if (compactCards) return 56
    const user = filteredUsers[index]
    let h = 110
    if (visibleFields.bio !== false && user?.bio) h += 60
    if (visibleFields.quote !== false && user?.quote_text) h += 60
    return h
  }, [compactCards, filteredUsers, visibleFields])

  // サイズ変更時にリストをリセット
  useEffect(() => {
    listRef.current?.resetAfterIndex(0)
  }, [compactCards, visibleFields, filteredUsers])

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
    <div ref={outerRef} className="flex flex-col h-full overflow-hidden">
      {/* コントロール部分 */}
      <div ref={controlsRef} className="flex-shrink-0">
        {/* ヘッダーバー */}
        <div className="mb-3 p-4 bg-gray-800 rounded-xl flex items-center justify-between">
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

        {/* 検索・ソート・表示設定 */}
        <div className="mb-3 p-4 bg-gray-800 rounded-xl">
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
      </div>

      {/* ユーザー一覧（仮想スクロール） */}
      {filteredUsers.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <div className="text-4xl mb-3">🔍</div>
          <p className="text-sm">条件に一致するユーザーが見つかりません</p>
          <p className="text-xs mt-1">フィルター条件を変更してみてください</p>
        </div>
      ) : (
        <div className="flex-1 min-h-0">
          <VariableSizeList
            ref={listRef}
            height={listHeight}
            itemCount={filteredUsers.length}
            itemSize={getItemSize}
            itemData={itemData}
            overscanCount={10}
            className="scrollbar-thin"
          >
            {UserRow}
          </VariableSizeList>
        </div>
      )}
    </div>
  )
}
