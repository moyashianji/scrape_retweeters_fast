import { useState, useMemo } from 'react'

// 公式アカウント定義（メンション + キーワード）
const OFFICIAL_ACCOUNTS = {
  'ぷりっつ': {
    mentions: ['ampxtak', 'umasugi_human', 'hinekureo_dayo', 'puri_dao'],
    keywords: ['ぷりっつ', 'プリッツ', 'ぷり民', 'priっつ']
  },
  'あっきぃ': {
    mentions: ['akkkkiy', 'akkkkiysab', 'akkiydaaa'],
    keywords: ['あっきぃ', 'アッキー', 'あっきー', 'akkiy', 'あきぃ']
  },
  'あっとくん': {
    mentions: ['_AtToKun', 'AtToKun_info'],
    keywords: ['あっとくん', 'あっと君', 'アットくん', 'あっと民', 'atto']
  },
  'ちぐさくん': {
    mentions: ['Tigusa_voice', 'Tigusa_sub'],
    keywords: ['ちぐさ', 'チグサ', 'tigusa', '千草']
  },
  'まぜ太': {
    mentions: ['mazeta_666', 'mazeta_sub'],
    keywords: ['まぜ太', 'まぜた', 'マゼタ', 'mazeta']
  },
  'けちゃ': {
    mentions: ['ketchup_N1', 'ketchup_N2'],
    keywords: ['けちゃ', 'ケチャ', 'ketchup', 'けちゃっぷ']
  },
}

// ハートの絵文字と色名
const HEART_EMOJIS = {
  '❤️': { name: '赤', color: '#ef4444' },
  '🧡': { name: 'オレンジ', color: '#f97316' },
  '💛': { name: '黄色', color: '#eab308' },
  '💚': { name: '緑', color: '#22c55e' },
  '💙': { name: '青', color: '#3b82f6' },
  '💜': { name: '紫', color: '#a855f7' },
  '🖤': { name: '黒', color: '#1f2937' },
  '🤍': { name: '白', color: '#e5e7eb' },
  '🤎': { name: '茶', color: '#a16207' },
  '💗': { name: 'ピンク(成長)', color: '#ec4899' },
  '💖': { name: 'ピンク(輝)', color: '#f472b6' },
  '💕': { name: 'ダブルハート', color: '#f9a8d4' },
  '💞': { name: '回転ハート', color: '#fb7185' },
  '💓': { name: '鼓動', color: '#f43f5e' },
  '💘': { name: '矢ハート', color: '#be123c' },
  '💝': { name: 'リボンハート', color: '#fbbf24' },
}

function App() {
  const [users, setUsers] = useState([])
  const [searchQuery, setSearchQuery] = useState('')
  const [filterMention, setFilterMention] = useState('')
  const [filterHeart, setFilterHeart] = useState('')
  const [sortBy, setSortBy] = useState('index')

  // JSONファイルインポート
  const handleFileImport = (e) => {
    const file = e.target.files[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (event) => {
      try {
        const data = JSON.parse(event.target.result)
        setUsers(Array.isArray(data) ? data : [])
      } catch (err) {
        alert('JSONファイルの読み込みに失敗しました')
      }
    }
    reader.readAsText(file)
  }

  // 統計計算
  const stats = useMemo(() => {
    if (users.length === 0) return null

    // ファンマーク（メンション）カウント
    const mentionCounts = {}
    Object.entries(OFFICIAL_ACCOUNTS).forEach(([name, accounts]) => {
      mentionCounts[name] = {
        accounts,
        count: 0,
        users: []
      }
    })

    // ハートカウント
    const heartCounts = {}
    Object.entries(HEART_EMOJIS).forEach(([emoji, info]) => {
      heartCounts[emoji] = {
        ...info,
        emoji,
        count: 0,
        users: []
      }
    })

    // 各ユーザーを分析
    users.forEach(user => {
      const bio = (user.bio || '') + ' ' + (user.name || '')

      // メンション・キーワードチェック
      Object.entries(OFFICIAL_ACCOUNTS).forEach(([name, data]) => {
        const bioLower = bio.toLowerCase()

        // @メンションチェック
        const hasMention = data.mentions.some(acc =>
          bioLower.includes(`@${acc.toLowerCase()}`)
        )

        // キーワードチェック
        const hasKeyword = data.keywords.some(kw =>
          bioLower.includes(kw.toLowerCase())
        )

        if (hasMention || hasKeyword) {
          mentionCounts[name].count++
          mentionCounts[name].users.push(user.username)
        }
      })

      // ハートチェック
      Object.keys(HEART_EMOJIS).forEach(emoji => {
        if (bio.includes(emoji)) {
          heartCounts[emoji].count++
          heartCounts[emoji].users.push(user.username)
        }
      })
    })

    return { mentionCounts, heartCounts }
  }, [users])

  // フィルタリング
  const filteredUsers = useMemo(() => {
    let result = [...users]

    // テキスト検索
    if (searchQuery) {
      const q = searchQuery.toLowerCase()
      result = result.filter(user =>
        (user.username || '').toLowerCase().includes(q) ||
        (user.name || '').toLowerCase().includes(q) ||
        (user.bio || '').toLowerCase().includes(q)
      )
    }

    // メンション・キーワードフィルター
    if (filterMention && OFFICIAL_ACCOUNTS[filterMention]) {
      const data = OFFICIAL_ACCOUNTS[filterMention]
      result = result.filter(user => {
        const bio = (user.bio || '') + ' ' + (user.name || '')
        const bioLower = bio.toLowerCase()

        const hasMention = data.mentions.some(acc =>
          bioLower.includes(`@${acc.toLowerCase()}`)
        )
        const hasKeyword = data.keywords.some(kw =>
          bioLower.includes(kw.toLowerCase())
        )

        return hasMention || hasKeyword
      })
    }

    // ハートフィルター
    if (filterHeart) {
      result = result.filter(user => {
        const bio = (user.bio || '') + ' ' + (user.name || '')
        return bio.includes(filterHeart)
      })
    }

    // ソート
    if (sortBy === 'username') {
      result.sort((a, b) => (a.username || '').localeCompare(b.username || ''))
    } else if (sortBy === 'name') {
      result.sort((a, b) => (a.name || '').localeCompare(b.name || ''))
    } else if (sortBy === 'followers') {
      result.sort((a, b) => {
        const aCount = parseFollowerCount(a.followers_count)
        const bCount = parseFollowerCount(b.followers_count)
        return bCount - aCount
      })
    }

    return result
  }, [users, searchQuery, filterMention, filterHeart, sortBy])

  // フォロワー数をパース
  function parseFollowerCount(str) {
    if (!str) return 0
    const num = parseFloat(str.replace(/,/g, ''))
    if (str.includes('K')) return num * 1000
    if (str.includes('M')) return num * 1000000
    return num || 0
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* ヘッダー */}
      <header className="bg-gray-800 border-b border-gray-700 p-4">
        <h1 className="text-2xl font-bold text-center">X ユーザー分析ツール</h1>
      </header>

      <div className="container mx-auto p-4">
        {/* インポート */}
        <div className="mb-6 p-4 bg-gray-800 rounded-lg">
          <label className="block mb-2 font-semibold">JSONファイルをインポート</label>
          <input
            type="file"
            accept=".json"
            onChange={handleFileImport}
            className="block w-full text-sm text-gray-300 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:bg-blue-600 file:text-white hover:file:bg-blue-700 cursor-pointer"
          />
          {users.length > 0 && (
            <p className="mt-2 text-green-400">✓ {users.length}人のユーザーを読み込みました</p>
          )}
        </div>

        {users.length > 0 && (
          <>
            {/* 統計 */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
              {/* ファンマークカウント */}
              <div className="p-4 bg-gray-800 rounded-lg">
                <h2 className="text-lg font-semibold mb-3">📌 ファンマーク（メンション）カウント</h2>
                <div className="space-y-2">
                  {stats && Object.entries(stats.mentionCounts)
                    .sort((a, b) => b[1].count - a[1].count)
                    .map(([name, data]) => (
                      <div
                        key={name}
                        className={`flex items-center justify-between p-2 rounded cursor-pointer transition ${filterMention === name ? 'bg-blue-600' : 'bg-gray-700 hover:bg-gray-600'}`}
                        onClick={() => setFilterMention(filterMention === name ? '' : name)}
                      >
                        <span>{name}</span>
                        <span className="font-bold text-xl">{data.count}</span>
                      </div>
                    ))}
                </div>
              </div>

              {/* ハートカウント */}
              <div className="p-4 bg-gray-800 rounded-lg">
                <h2 className="text-lg font-semibold mb-3">💖 ハート絵文字カウント</h2>
                <div className="grid grid-cols-2 gap-2">
                  {stats && Object.entries(stats.heartCounts)
                    .filter(([, data]) => data.count > 0)
                    .sort((a, b) => b[1].count - a[1].count)
                    .map(([emoji, data]) => (
                      <div
                        key={emoji}
                        className={`flex items-center justify-between p-2 rounded cursor-pointer transition ${filterHeart === emoji ? 'bg-blue-600' : 'bg-gray-700 hover:bg-gray-600'}`}
                        onClick={() => setFilterHeart(filterHeart === emoji ? '' : emoji)}
                      >
                        <span>
                          <span className="text-xl mr-2">{emoji}</span>
                          <span className="text-sm text-gray-300">{data.name}</span>
                        </span>
                        <span className="font-bold">{data.count}</span>
                      </div>
                    ))}
                </div>
              </div>
            </div>

            {/* 検索・フィルター */}
            <div className="mb-4 p-4 bg-gray-800 rounded-lg">
              <div className="flex flex-wrap gap-4">
                <div className="flex-1 min-w-64">
                  <label className="block text-sm mb-1">検索（ユーザー名・名前・プロフ）</label>
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="検索..."
                    className="w-full p-2 bg-gray-700 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm mb-1">ソート</label>
                  <select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value)}
                    className="p-2 bg-gray-700 rounded border border-gray-600"
                  >
                    <option value="index">取得順</option>
                    <option value="username">ユーザー名</option>
                    <option value="name">表示名</option>
                    <option value="followers">フォロワー数</option>
                  </select>
                </div>
                {(filterMention || filterHeart || searchQuery) && (
                  <button
                    onClick={() => {
                      setFilterMention('')
                      setFilterHeart('')
                      setSearchQuery('')
                    }}
                    className="self-end p-2 bg-red-600 hover:bg-red-700 rounded"
                  >
                    フィルタークリア
                  </button>
                )}
              </div>
              <div className="mt-2 text-sm text-gray-400">
                表示中: {filteredUsers.length} / {users.length}人
                {filterMention && <span className="ml-2 text-blue-400">| {filterMention}のファン</span>}
                {filterHeart && <span className="ml-2 text-pink-400">| {filterHeart}を含む</span>}
              </div>
            </div>

            {/* ユーザー一覧 */}
            <div className="space-y-2">
              {filteredUsers.map((user, index) => (
                <UserCard key={user.username || index} user={user} />
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

// ユーザーカード
function UserCard({ user }) {
  const [expanded, setExpanded] = useState(false)

  // このユーザーがファンとして検出されるアカウント
  const mentionedAccounts = useMemo(() => {
    const bio = (user.bio || '') + ' ' + (user.name || '')
    const bioLower = bio.toLowerCase()
    const mentioned = []

    Object.entries(OFFICIAL_ACCOUNTS).forEach(([name, data]) => {
      const hasMention = data.mentions.some(acc =>
        bioLower.includes(`@${acc.toLowerCase()}`)
      )
      const hasKeyword = data.keywords.some(kw =>
        bioLower.includes(kw.toLowerCase())
      )

      if (hasMention || hasKeyword) {
        mentioned.push(name)
      }
    })
    return mentioned
  }, [user])

  // このユーザーが使っているハート
  const usedHearts = useMemo(() => {
    const bio = (user.bio || '') + ' ' + (user.name || '')
    return Object.keys(HEART_EMOJIS).filter(emoji => bio.includes(emoji))
  }, [user])

  return (
    <div className="p-3 bg-gray-800 rounded-lg hover:bg-gray-750 transition">
      <div className="flex items-start gap-3">
        {/* アバター */}
        {user.profile_image_url && (
          <img
            src={user.profile_image_url}
            alt=""
            className="w-12 h-12 rounded-full"
          />
        )}

        <div className="flex-1 min-w-0">
          {/* 名前・ユーザー名 */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-bold">{user.name || '名前なし'}</span>
            {user.verified && <span className="text-blue-400">✓</span>}
            <a
              href={`https://x.com/${user.username}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-400 hover:text-blue-400"
            >
              @{user.username}
            </a>
          </div>

          {/* バッジ */}
          <div className="flex flex-wrap gap-1 mt-1">
            {mentionedAccounts.map(name => (
              <span key={name} className="px-2 py-0.5 text-xs bg-blue-600 rounded">
                {name}ファン
              </span>
            ))}
            {usedHearts.length > 0 && (
              <span className="px-2 py-0.5 text-xs bg-pink-600 rounded">
                {usedHearts.join('')}
              </span>
            )}
          </div>

          {/* フォロワー数 */}
          {(user.followers_count || user.following_count) && (
            <div className="text-xs text-gray-400 mt-1">
              {user.followers_count && <span className="mr-3">フォロワー: {user.followers_count}</span>}
              {user.following_count && <span>フォロー中: {user.following_count}</span>}
            </div>
          )}

          {/* プロフィール */}
          {user.bio && (
            <p
              className={`text-sm text-gray-300 mt-2 whitespace-pre-wrap ${!expanded && 'line-clamp-2'}`}
              onClick={() => setExpanded(!expanded)}
            >
              {user.bio}
            </p>
          )}

          {/* 場所・URL */}
          {(user.location || user.url) && (
            <div className="text-xs text-gray-400 mt-1">
              {user.location && <span className="mr-3">📍 {user.location}</span>}
              {user.url && (
                <a href={user.url} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">
                  🔗 {user.url}
                </a>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default App
