import { useMemo } from 'react'
import { GROUPS, HEART_EMOJIS, detectFanOf, getUserSearchText } from '../constants'

function formatCreatedAt(str) {
  if (!str) return ''
  try {
    const d = new Date(str)
    if (isNaN(d.getTime())) return str
    return `${d.getFullYear()}/${d.getMonth() + 1}/${d.getDate()}`
  } catch {
    return str
  }
}

function needsTruncation(text) {
  if (!text) return false
  return text.length > 80 || (text.match(/\n/g) || []).length >= 3
}

export default function UserCard({ user, showSources, visibleFields = {}, selectedGroup, compact = false, expanded = false, onToggleExpand }) {
  const toggleExpand = () => onToggleExpand?.(user.username)
  const officialAccounts = useMemo(() => GROUPS[selectedGroup]?.members || {}, [selectedGroup])

  // _fanCache があればキャッシュから取得（computeStatsOnePassで事前計算済み）
  const mentionedAccounts = useMemo(() => {
    if (user._fanCache && user._fanCache[selectedGroup]) {
      return user._fanCache[selectedGroup]
    }
    return detectFanOf(user, officialAccounts)
  }, [user, officialAccounts, selectedGroup])

  const usedHearts = useMemo(() => {
    const text = getUserSearchText(user)
    return Object.keys(HEART_EMOJIS).filter(emoji => text.includes(emoji))
  }, [user])

  // コンパクトモード
  if (compact) {
    return (
      <div className="px-3 py-2 bg-gray-800 rounded-lg hover:bg-gray-750 transition flex items-center gap-3">
        {user.profile_image_url && (
          <img src={user.profile_image_url} alt="" className="w-8 h-8 rounded-full flex-shrink-0" />
        )}
        <div className="flex-1 min-w-0 flex items-center gap-3">
          <div className="min-w-0">
            <span className="font-semibold text-sm">{user.name || '名前なし'}</span>
            <a
              href={`https://x.com/${user.username}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-gray-400 hover:text-blue-400 ml-2"
            >
              @{user.username}
            </a>
          </div>
          <div className="flex flex-wrap gap-1 flex-shrink-0">
            {user.can_dm === true && (
              <span className="px-1.5 py-0.5 text-[10px] font-semibold bg-green-600 text-white rounded">DM可</span>
            )}
            {user.can_dm === false && (
              <span className="px-1.5 py-0.5 text-[10px] bg-red-900 text-red-300 rounded">DM不可</span>
            )}
            {mentionedAccounts.map(name => {
              const member = officialAccounts[name]
              return (
                <span key={name} className="px-1.5 py-0.5 text-[10px] bg-blue-600 rounded">
                  {member?.fanMark || ''}{name}
                </span>
              )
            })}
            {usedHearts.length > 0 && (
              <span className="text-[10px]">{usedHearts.join('')}</span>
            )}
          </div>
        </div>
        {user.followers_count != null && (
          <span className="text-xs text-gray-500 flex-shrink-0">{user.followers_count.toLocaleString()} フォロワー</span>
        )}
      </div>
    )
  }

  // 通常モード
  return (
    <div className="p-3 bg-gray-800 rounded-xl hover:bg-gray-750 transition">
      <div className="flex items-start gap-3">
        {user.profile_image_url && (
          <img src={user.profile_image_url} alt="" className="w-12 h-12 rounded-full flex-shrink-0" />
        )}
        <div className="flex-1 min-w-0">
          {/* 名前 */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-bold text-base">{user.name || '名前なし'}</span>
            {user.verified && <span className="text-blue-400 text-sm">✓</span>}
            {user.is_blue_verified && (
              <span className="px-1.5 py-0.5 text-[10px] bg-blue-500/20 text-blue-400 rounded">Premium</span>
            )}
          </div>

          {/* ユーザー名 */}
          <a
            href={`https://x.com/${user.username}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-gray-400 hover:text-blue-400 block mt-0.5"
          >
            @{user.username}
          </a>

          {/* バッジ */}
          <div className="flex flex-wrap gap-1 mt-1.5">
            {user.can_dm === true && (
              <span className="px-2 py-0.5 text-xs font-semibold bg-green-600 text-white rounded-md">✉ DM開放</span>
            )}
            {user.can_dm === false && (
              <span className="px-2 py-0.5 text-xs bg-red-900/80 text-red-300 rounded-md">✗ DM閉鎖</span>
            )}
            {user.can_dm == null && (
              <span className="px-2 py-0.5 text-xs bg-gray-700 text-gray-500 rounded-md">DM不明</span>
            )}
            {mentionedAccounts.map(name => {
              const member = officialAccounts[name]
              const mark = member?.fanMark || ''
              return (
                <span key={name} className="px-2 py-0.5 text-xs bg-blue-600/80 rounded-md">
                  {mark && <span className="mr-1">{mark}</span>}{name}ファン
                </span>
              )
            })}
            {usedHearts.length > 0 && (
              <span className="px-2 py-0.5 text-xs bg-pink-600/80 rounded-md">{usedHearts.join('')}</span>
            )}
            {user.protected && visibleFields.protected !== false && (
              <span className="px-2 py-0.5 text-xs bg-yellow-600/80 rounded-md">🔒 鍵垢</span>
            )}
            {user.default_profile_image && (
              <span className="px-2 py-0.5 text-xs bg-gray-600 rounded-md">デフォアイコン</span>
            )}
            {showSources && (user._sources || []).length > 1 && (
              <span className="px-2 py-0.5 text-xs bg-yellow-600/80 rounded-md">
                {(user._sources || []).length}ソース
              </span>
            )}
          </div>

          {/* 数値データ */}
          {(visibleFields.followers !== false || visibleFields.following !== false ||
            visibleFields.statuses !== false || visibleFields.favourites !== false) && (
            <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-gray-400 mt-1.5">
              {visibleFields.followers !== false && user.followers_count != null && (
                <span>フォロワー: <span className="text-gray-300">{user.followers_count.toLocaleString()}</span></span>
              )}
              {visibleFields.following !== false && user.following_count != null && (
                <span>フォロー: <span className="text-gray-300">{user.following_count.toLocaleString()}</span></span>
              )}
              {visibleFields.statuses !== false && user.statuses_count != null && (
                <span>ツイート: <span className="text-gray-300">{user.statuses_count.toLocaleString()}</span></span>
              )}
              {visibleFields.favourites !== false && user.favourites_count != null && (
                <span>いいね: <span className="text-gray-300">{user.favourites_count.toLocaleString()}</span></span>
              )}
              {visibleFields.media !== false && user.media_count != null && user.media_count > 0 && (
                <span>メディア: <span className="text-gray-300">{user.media_count.toLocaleString()}</span></span>
              )}
              {visibleFields.listed !== false && user.listed_count != null && user.listed_count > 0 && (
                <span>リスト: <span className="text-gray-300">{user.listed_count.toLocaleString()}</span></span>
              )}
            </div>
          )}

          {/* 作成日 */}
          {visibleFields.created_at !== false && user.created_at && (
            <div className="text-xs text-gray-500 mt-1">
              作成: {formatCreatedAt(user.created_at)}
            </div>
          )}

          {/* プロフィール文 */}
          {visibleFields.bio !== false && user.bio && (
            <div className="mt-2 p-2.5 bg-gray-700/50 rounded-lg border-l-2 border-gray-600">
              <p
                className={`text-sm text-gray-300 whitespace-pre-wrap ${!expanded && 'line-clamp-3'}`}
              >
                {user.bio}
              </p>
              {needsTruncation(user.bio) && (
                <button
                  onClick={toggleExpand}
                  className="text-[11px] text-blue-400 hover:underline mt-1"
                >
                  {expanded ? '折りたたむ' : 'もっと見る'}
                </button>
              )}
            </div>
          )}

          {/* 引用ツイート */}
          {visibleFields.quote !== false && user.quote_text && (
            <div className="mt-2 p-2.5 bg-blue-900/20 rounded-lg border-l-2 border-blue-500">
              <p className="text-[11px] text-blue-400 mb-1 font-medium">💬 引用ツイート</p>
              <p
                className={`text-sm text-gray-200 whitespace-pre-wrap ${!expanded && 'line-clamp-3'}`}
              >
                {user.quote_text}
              </p>
              {needsTruncation(user.quote_text) && (
                <button
                  onClick={toggleExpand}
                  className="text-[11px] text-blue-400 hover:underline mt-1"
                >
                  {expanded ? '折りたたむ' : 'もっと見る'}
                </button>
              )}
            </div>
          )}

          {visibleFields.location !== false && (user.location || user.url) && (
            <div className="text-xs text-gray-400 mt-1.5">
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
