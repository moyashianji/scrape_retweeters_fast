import { useState, useMemo, useEffect } from 'react'
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, BarElement, ArcElement, PointElement, LineElement, Filler,
  RadialLinearScale, Tooltip, Legend, Title,
} from 'chart.js'
import { Bar, Doughnut, Line, Radar } from 'react-chartjs-2'
import { GROUPS, HEART_EMOJIS, parseFollowerCount, detectFanOf, getUserSearchText } from '../constants'

ChartJS.register(
  CategoryScale, LinearScale, BarElement, ArcElement, PointElement, LineElement, Filler,
  RadialLinearScale, Tooltip, Legend, Title
)

// --- グループ定義 ---
const GROUP_DEFS = [
  { id: 'amptakcolors', key: 'amp', color: 'rgba(59, 130, 246, 0.8)', bg: 'rgba(59, 130, 246, 0.15)', textClass: 'text-blue-400', bgClass: 'bg-blue-900/30', solidColor: '#3b82f6' },
  { id: 'sneakerstep',  key: 'snk', color: 'rgba(16, 185, 129, 0.8)', bg: 'rgba(16, 185, 129, 0.15)', textClass: 'text-emerald-400', bgClass: 'bg-emerald-900/30', solidColor: '#10b981' },
  { id: 'knightx',      key: 'knx', color: 'rgba(168, 85, 247, 0.8)', bg: 'rgba(168, 85, 247, 0.15)', textClass: 'text-purple-400', bgClass: 'bg-purple-900/30', solidColor: '#a855f7' },
  { id: 'meteora',      key: 'mtor', color: 'rgba(251, 191, 36, 0.8)', bg: 'rgba(251, 191, 36, 0.15)', textClass: 'text-amber-400', bgClass: 'bg-amber-900/30', solidColor: '#fbbf24' },
]

function getGroupLabel(gdef) {
  const g = GROUPS[gdef.id]
  return g ? `${g.fanMark} ${g.name}` : gdef.id
}

function getGroupShortLabel(gdef) {
  const g = GROUPS[gdef.id]
  return g ? `${g.fanMark} ${g.name.split(' ')[0]}` : gdef.id
}

// --- ユーティリティ ---

function groupUsers(users, groupId) {
  const members = GROUPS[groupId]?.members || {}
  const result = {}
  Object.keys(members).forEach(name => { result[name] = [] })
  users.forEach(user => {
    // _fanCache があれば再計算を回避
    const fans = (user._fanCache && user._fanCache[groupId])
      ? user._fanCache[groupId]
      : detectFanOf(user, members)
    fans.forEach(name => { result[name].push(user.username) })
  })
  return result
}

const CHART_TEXT = '#d1d5db'
const GRID_COLOR = 'rgba(75, 85, 99, 0.4)'

const commonScaleOpts = {
  ticks: { color: CHART_TEXT, font: { size: 11 } },
  grid: { color: GRID_COLOR },
}

// ============================================================
// Group Selector
// ============================================================
function GroupSelector({ allGroupData, selectedIds, setSelectedIds, crossMode }) {
  const toggle = (id) => {
    setSelectedIds(prev => {
      if (prev.includes(id)) {
        if (prev.length <= 1) return prev // 最低1つ
        return prev.filter(x => x !== id)
      }
      return [...prev, id]
    })
  }

  const selectAll = () => setSelectedIds(allGroupData.map(gd => gd.def.id))

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <span className="text-xs text-gray-500">{crossMode ? '分析対象:' : '比較対象:'}</span>
      {allGroupData.map(gd => {
        const active = selectedIds.includes(gd.def.id)
        const hasData = crossMode || gd.users.length > 0
        return (
          <button
            key={gd.def.id}
            onClick={() => toggle(gd.def.id)}
            disabled={!hasData}
            className={`px-3 py-1.5 text-xs rounded-lg transition font-medium flex items-center gap-1.5 border ${
              !hasData
                ? 'border-gray-700 text-gray-600 cursor-not-allowed'
                : active
                  ? `border-transparent text-white`
                  : 'border-gray-600 text-gray-400 hover:text-white hover:border-gray-500'
            }`}
            style={active && hasData ? { backgroundColor: gd.def.color } : {}}
          >
            {getGroupShortLabel(gd.def)}
            {!crossMode && (
              <span className={`px-1.5 py-0.5 text-[10px] rounded-full font-bold ${
                active ? 'bg-white/20' : 'bg-gray-700'
              }`}>
                {gd.users.length}
              </span>
            )}
          </button>
        )
      })}
      {allGroupData.filter(gd => crossMode || gd.users.length > 0).length >= 3 && (
        <button
          onClick={selectAll}
          className="px-2 py-1 text-[10px] text-gray-500 hover:text-gray-300 transition"
        >
          全選択
        </button>
      )}
    </div>
  )
}

// ============================================================
// Chart 1: Venn Diagram
// ============================================================
function VennDiagram({ groupData }) {
  const active = groupData.filter(gd => gd.users.length > 0)
  const sets = active.map(gd => new Set(gd.users.map(u => u.username)))
  const overlap = (a, b) => [...a].filter(u => b.has(u)).length

  return (
    <div className="p-5 bg-gray-800 rounded-xl">
      <h3 className="text-sm font-bold mb-4">1. ユーザー重複</h3>
      <div className={`grid gap-3 ${active.length >= 3 ? 'grid-cols-3' : 'grid-cols-2'}`}>
        {active.map((gd, i) => (
          <div key={gd.def.id} className={`text-center p-3 ${gd.def.bgClass} rounded-lg`}>
            <div className={`text-2xl font-bold ${gd.def.textClass}`}>{sets[i].size}</div>
            <div className="text-[11px] text-gray-400">{getGroupShortLabel(gd.def)}</div>
          </div>
        ))}
      </div>
      {active.length >= 2 && (
        <div className="mt-3 space-y-1">
          {active.map((gdA, i) =>
            active.slice(i + 1).map((gdB, j) => {
              const ov = overlap(sets[i], sets[i + 1 + j])
              return (
                <div key={`${i}-${i+1+j}`} className="flex items-center justify-between text-xs px-3 py-1.5 bg-gray-700/40 rounded">
                  <span className="text-gray-400">{getGroupShortLabel(gdA.def)} ∩ {getGroupShortLabel(gdB.def)}</span>
                  <span className="font-bold text-yellow-400">{ov}人</span>
                </div>
              )
            })
          )}
          {active.length >= 3 && (() => {
            const allOverlap = [...sets[0]].filter(u => sets[1].has(u) && sets[2].has(u)).length
            return (
              <div className="flex items-center justify-between text-xs px-3 py-1.5 bg-yellow-900/30 rounded">
                <span className="text-gray-400">全グループ共通</span>
                <span className="font-bold text-yellow-300">{allOverlap}人</span>
              </div>
            )
          })()}
        </div>
      )}
    </div>
  )
}

// ============================================================
// Chart 2: Cross Heatmap (all pairs)
// ============================================================
function CrossHeatmap({ groupData }) {
  const active = groupData.filter(gd => gd.users.length > 0)
  if (active.length < 2) return null  // クロス分析モードでは全グループにデータがあるので常に表示

  const allUsers = useMemo(() => {
    const map = {}
    groupData.forEach(gd => gd.users.forEach(u => { if (u.username) map[u.username] = u }))
    return Object.values(map)
  }, [groupData])

  // 全ペアのヒートマップを生成
  const pairs = []
  for (let i = 0; i < active.length; i++) {
    for (let j = i + 1; j < active.length; j++) {
      pairs.push([active[i], active[j]])
    }
  }

  return (
    <div className="p-5 bg-gray-800 rounded-xl">
      <h3 className="text-sm font-bold mb-1">2. 推しクロス集計ヒートマップ</h3>
      <p className="text-xs text-gray-500 mb-4">メンバーのファン重複人数</p>
      <div className="space-y-6">
        {pairs.map(([gdA, gdB], pi) => {
          const membersA = GROUPS[gdA.def.id]?.members || {}
          const membersB = GROUPS[gdB.def.id]?.members || {}
          const namesA = Object.keys(membersA)
          const namesB = Object.keys(membersB)
          const matrix = {}
          namesA.forEach(a => {
            matrix[a] = {}
            namesB.forEach(b => { matrix[a][b] = 0 })
          })
          allUsers.forEach(user => {
            const fansA = (user._fanCache && user._fanCache[gdA.def.id])
              ? user._fanCache[gdA.def.id]
              : detectFanOf(user, membersA)
            const fansB = (user._fanCache && user._fanCache[gdB.def.id])
              ? user._fanCache[gdB.def.id]
              : detectFanOf(user, membersB)
            fansA.forEach(a => { fansB.forEach(b => { matrix[a][b]++ }) })
          })
          const maxVal = Math.max(1, ...namesA.flatMap(a => namesB.map(b => matrix[a][b])))

          return (
            <div key={pi}>
              <p className="text-xs text-gray-400 mb-2 font-medium">
                {getGroupShortLabel(gdA.def)} × {getGroupShortLabel(gdB.def)}
              </p>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr>
                      <th className="p-1.5 text-left text-gray-500"></th>
                      {namesB.map(b => (
                        <th key={b} className={`p-1.5 text-center ${gdB.def.textClass} font-medium`}>
                          {membersB[b]?.fanMark || ''}{b}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {namesA.map(a => (
                      <tr key={a}>
                        <td className={`p-1.5 ${gdA.def.textClass} font-medium whitespace-nowrap`}>{membersA[a]?.fanMark || ''}{a}</td>
                        {namesB.map(b => {
                          const val = matrix[a][b]
                          const intensity = val / maxVal
                          return (
                            <td key={b} className="p-1 text-center">
                              <div
                                className="rounded-md py-1.5 px-1 font-bold"
                                style={{
                                  backgroundColor: val > 0 ? `rgba(251, 191, 36, ${0.15 + intensity * 0.6})` : 'rgba(55,65,81,0.3)',
                                  color: val > 0 ? '#fef3c7' : '#6b7280',
                                }}
                              >
                                {val}
                              </div>
                            </td>
                          )
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ============================================================
// Chart 3: Fan Count Bar Chart
// ============================================================
function FanCountBar({ groupData }) {
  const active = groupData.filter(gd => gd.users.length > 0)
  const labels = []
  const values = []
  const colors = []

  active.forEach(gd => {
    const fanCounts = groupUsers(gd.users, gd.def.id)
    const mark = GROUPS[gd.def.id]?.fanMark || ''
    Object.entries(fanCounts).forEach(([name, arr]) => {
      labels.push(`${mark}${name}`)
      values.push(arr.length)
      colors.push(gd.def.color)
    })
  })

  const data = {
    labels,
    datasets: [{ data: values, backgroundColor: colors, borderRadius: 4, barThickness: 20 }],
  }

  const options = {
    indexAxis: 'y',
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: { callbacks: { label: (ctx) => `${ctx.raw}人` } },
    },
    scales: {
      x: { ...commonScaleOpts, title: { display: true, text: 'ファン数', color: CHART_TEXT } },
      y: { ...commonScaleOpts, ticks: { ...commonScaleOpts.ticks, font: { size: 12 } } },
    },
  }

  return (
    <div className="p-5 bg-gray-800 rounded-xl">
      <h3 className="text-sm font-bold mb-1">3. ファン数 横棒グラフ</h3>
      <p className="text-xs text-gray-500 mb-4">全メンバーのファン検出数を比較</p>
      <div style={{ height: `${labels.length * 32 + 40}px` }}>
        <Bar data={data} options={options} />
      </div>
    </div>
  )
}

// ============================================================
// Chart 4: Group Share Doughnuts
// ============================================================
function GroupShareDoughnuts({ groupData }) {
  const active = groupData.filter(gd => gd.users.length > 0)
  const palettes = [
    ['rgba(59,130,246,0.9)', 'rgba(99,102,241,0.9)', 'rgba(139,92,246,0.9)', 'rgba(168,85,247,0.9)', 'rgba(79,70,229,0.9)', 'rgba(37,99,235,0.9)'],
    ['rgba(16,185,129,0.9)', 'rgba(20,184,166,0.9)', 'rgba(6,182,212,0.9)', 'rgba(34,197,94,0.9)', 'rgba(132,204,22,0.9)', 'rgba(245,158,11,0.9)', 'rgba(236,72,153,0.9)'],
    ['rgba(168,85,247,0.9)', 'rgba(192,132,252,0.9)', 'rgba(139,92,246,0.9)', 'rgba(124,58,237,0.9)'],
    ['rgba(251,191,36,0.9)', 'rgba(245,158,11,0.9)', 'rgba(234,179,8,0.9)', 'rgba(252,211,77,0.9)', 'rgba(253,224,71,0.9)', 'rgba(250,204,21,0.9)'],
  ]

  const opts = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: '55%',
    plugins: {
      legend: { position: 'bottom', labels: { color: CHART_TEXT, font: { size: 11 }, padding: 10, usePointStyle: true, pointStyleWidth: 8 } },
      tooltip: { callbacks: { label: (ctx) => `${ctx.label}: ${ctx.raw}人` } },
    },
  }

  const cols = active.length >= 3 ? 'grid-cols-3' : 'grid-cols-2'

  return (
    <div className="p-5 bg-gray-800 rounded-xl">
      <h3 className="text-sm font-bold mb-4">4. グループ内 ファンシェア</h3>
      <div className={`grid ${cols} gap-6`}>
        {active.map((gd, i) => {
          const fanCounts = groupUsers(gd.users, gd.def.id)
          const palette = palettes[i % palettes.length]
          const data = {
            labels: Object.keys(fanCounts),
            datasets: [{
              data: Object.values(fanCounts).map(arr => arr.length),
              backgroundColor: palette.slice(0, Object.keys(fanCounts).length),
              borderWidth: 0,
            }],
          }
          return (
            <div key={gd.def.id}>
              <p className={`text-xs ${gd.def.textClass} font-semibold text-center mb-2`}>{getGroupLabel(gd.def)}</p>
              <div style={{ height: '250px' }}>
                <Doughnut data={data} options={opts} />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ============================================================
// Chart 5: DM Open Rate
// ============================================================
function DmComparisonBar({ groupData }) {
  const active = groupData.filter(gd => gd.users.length > 0)

  const calcDm = (users) => {
    let open = 0, closed = 0, unknown = 0
    users.forEach(u => {
      if (u.can_dm === true) open++
      else if (u.can_dm === false) closed++
      else unknown++
    })
    const total = users.length || 1
    return { open, closed, unknown, openPct: ((open / total) * 100).toFixed(1) }
  }

  const dmData = active.map(gd => ({ ...calcDm(gd.users), label: getGroupShortLabel(gd.def) }))

  const data = {
    labels: dmData.map(d => d.label),
    datasets: [
      { label: 'DM開放', data: dmData.map(d => d.open), backgroundColor: 'rgba(34,197,94,0.8)', borderRadius: 4 },
      { label: 'DM閉鎖', data: dmData.map(d => d.closed), backgroundColor: 'rgba(239,68,68,0.8)', borderRadius: 4 },
      { label: '不明', data: dmData.map(d => d.unknown), backgroundColor: 'rgba(107,114,128,0.5)', borderRadius: 4 },
    ],
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'top', labels: { color: CHART_TEXT, font: { size: 11 }, usePointStyle: true, pointStyleWidth: 8 } },
      tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label}: ${ctx.raw}人` } },
    },
    scales: {
      x: { ...commonScaleOpts, stacked: true },
      y: { ...commonScaleOpts, stacked: true, title: { display: true, text: '人数', color: CHART_TEXT } },
    },
  }

  return (
    <div className="p-5 bg-gray-800 rounded-xl">
      <h3 className="text-sm font-bold mb-1">5. DM開放率 比較</h3>
      <p className="text-xs text-gray-500 mb-4">
        {dmData.map((d, i) => (
          <span key={i}>{i > 0 && ' / '}{d.label}: <span className="text-green-400 font-bold">{d.openPct}%</span></span>
        ))}
      </p>
      <div style={{ height: '220px' }}>
        <Bar data={data} options={options} />
      </div>
    </div>
  )
}

// ============================================================
// Chart 6: Follower Distribution Histogram
// ============================================================
function FollowerHistogram({ groupData }) {
  const active = groupData.filter(gd => gd.users.length > 0)
  const buckets = [
    { label: '0-100', min: 0, max: 100 },
    { label: '100-500', min: 100, max: 500 },
    { label: '500-1K', min: 500, max: 1000 },
    { label: '1K-5K', min: 1000, max: 5000 },
    { label: '5K-10K', min: 5000, max: 10000 },
    { label: '10K-50K', min: 10000, max: 50000 },
    { label: '50K+', min: 50000, max: Infinity },
  ]

  const countBuckets = (users) => {
    const counts = buckets.map(() => 0)
    users.forEach(u => {
      const fc = parseFollowerCount(u.followers_count)
      for (let i = 0; i < buckets.length; i++) {
        if (fc >= buckets[i].min && fc < buckets[i].max) { counts[i]++; break }
      }
    })
    return counts
  }

  const data = {
    labels: buckets.map(b => b.label),
    datasets: active.map(gd => ({
      label: getGroupShortLabel(gd.def),
      data: countBuckets(gd.users),
      backgroundColor: gd.def.bg,
      borderColor: gd.def.color,
      borderWidth: 2,
      tension: 0.3,
      fill: true,
      pointRadius: 4,
      pointBackgroundColor: gd.def.color,
    })),
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'top', labels: { color: CHART_TEXT, font: { size: 11 }, usePointStyle: true, pointStyleWidth: 8 } },
      tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label}: ${ctx.raw}人` } },
    },
    scales: {
      x: { ...commonScaleOpts, title: { display: true, text: 'フォロワー数', color: CHART_TEXT } },
      y: { ...commonScaleOpts, title: { display: true, text: '人数', color: CHART_TEXT }, beginAtZero: true },
    },
  }

  return (
    <div className="p-5 bg-gray-800 rounded-xl">
      <h3 className="text-sm font-bold mb-1">6. フォロワー数 分布</h3>
      <p className="text-xs text-gray-500 mb-4">各グループのユーザーのフォロワー数帯ごとの人数</p>
      <div style={{ height: '280px' }}>
        <Line data={data} options={options} />
      </div>
    </div>
  )
}

// ============================================================
// Chart 7: Account Creation Year
// ============================================================
function AccountAgeChart({ groupData }) {
  const active = groupData.filter(gd => gd.users.length > 0)

  const countByYear = (users) => {
    const counts = {}
    users.forEach(u => {
      if (!u.created_at) return
      try {
        const y = new Date(u.created_at).getFullYear()
        if (y >= 2006 && y <= 2026) counts[y] = (counts[y] || 0) + 1
      } catch { /* ignore */ }
    })
    return counts
  }

  const yearCounts = active.map(gd => countByYear(gd.users))
  const allYears = [...new Set(yearCounts.flatMap(c => Object.keys(c)))]
    .map(Number).sort((a, b) => a - b)

  if (allYears.length === 0) {
    return (
      <div className="p-5 bg-gray-800 rounded-xl">
        <h3 className="text-sm font-bold mb-2">7. アカウント作成年 分布</h3>
        <p className="text-sm text-gray-500 text-center py-8">作成日データがありません</p>
      </div>
    )
  }

  const data = {
    labels: allYears.map(String),
    datasets: active.map((gd, i) => ({
      label: getGroupShortLabel(gd.def),
      data: allYears.map(y => yearCounts[i][y] || 0),
      borderColor: gd.def.color,
      backgroundColor: gd.def.bg,
      borderWidth: 2,
      tension: 0.3,
      fill: true,
      pointRadius: 4,
      pointBackgroundColor: gd.def.color,
    })),
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'top', labels: { color: CHART_TEXT, font: { size: 11 }, usePointStyle: true, pointStyleWidth: 8 } },
      tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label}: ${ctx.raw}人` } },
    },
    scales: {
      x: { ...commonScaleOpts, title: { display: true, text: '作成年', color: CHART_TEXT } },
      y: { ...commonScaleOpts, title: { display: true, text: '人数', color: CHART_TEXT }, beginAtZero: true },
    },
  }

  return (
    <div className="p-5 bg-gray-800 rounded-xl">
      <h3 className="text-sm font-bold mb-1">7. アカウント作成年 分布</h3>
      <p className="text-xs text-gray-500 mb-4">新規ファンが多いグループはどちらか</p>
      <div style={{ height: '280px' }}>
        <Line data={data} options={options} />
      </div>
    </div>
  )
}

// ============================================================
// Chart 8: Heart Emoji Radar
// ============================================================
function HeartRadar({ groupData }) {
  const active = groupData.filter(gd => gd.users.length > 0)

  const countHearts = (users) => {
    const counts = {}
    Object.keys(HEART_EMOJIS).forEach(e => { counts[e] = 0 })
    users.forEach(u => {
      const text = getUserSearchText(u)
      Object.keys(HEART_EMOJIS).forEach(e => { if (text.includes(e)) counts[e]++ })
    })
    return counts
  }

  const heartCounts = active.map(gd => countHearts(gd.users))
  const usedEmojis = Object.keys(HEART_EMOJIS).filter(e => heartCounts.some(hc => hc[e] > 0))

  if (usedEmojis.length === 0) {
    return (
      <div className="p-5 bg-gray-800 rounded-xl">
        <h3 className="text-sm font-bold mb-2">8. ハート絵文字 レーダーチャート</h3>
        <p className="text-sm text-gray-500 text-center py-8">ハート絵文字のデータがありません</p>
      </div>
    )
  }

  const data = {
    labels: usedEmojis.map(e => `${e} ${HEART_EMOJIS[e].name}`),
    datasets: active.map(gd => ({
      label: getGroupShortLabel(gd.def),
      data: usedEmojis.map(e => heartCounts[active.indexOf(gd)][e]),
      borderColor: gd.def.color,
      backgroundColor: gd.def.bg,
      borderWidth: 2,
      pointRadius: 4,
      pointBackgroundColor: gd.def.color,
    })),
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'top', labels: { color: CHART_TEXT, font: { size: 11 }, usePointStyle: true, pointStyleWidth: 8 } },
      tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label}: ${ctx.raw}人` } },
    },
    scales: {
      r: {
        grid: { color: GRID_COLOR },
        angleLines: { color: GRID_COLOR },
        pointLabels: { color: CHART_TEXT, font: { size: 11 } },
        ticks: { color: CHART_TEXT, backdropColor: 'transparent', font: { size: 9 } },
        beginAtZero: true,
      },
    },
  }

  return (
    <div className="p-5 bg-gray-800 rounded-xl">
      <h3 className="text-sm font-bold mb-1">8. ハート絵文字 レーダーチャート</h3>
      <p className="text-xs text-gray-500 mb-4">各色ハートの使用率をグループ間で比較</p>
      <div style={{ height: '350px' }}>
        <Radar data={data} options={options} />
      </div>
    </div>
  )
}

// ============================================================
// Chart 9: 3-Group Triangle Map (SVG ternary)
// ============================================================
function TriangleMap({ groupData }) {
  const active = groupData.filter(gd => gd.users.length > 0)
  if (active.length < 3) return null

  const [gA, gB, gC] = active
  const membersA = GROUPS[gA.def.id]?.members || {}
  const membersB = GROUPS[gB.def.id]?.members || {}
  const membersC = GROUPS[gC.def.id]?.members || {}

  // 全ユーザーの集約
  const allUsersMap = useMemo(() => {
    const map = {}
    groupData.forEach(gd => gd.users.forEach(u => { if (u.username) map[u.username] = u }))
    return map
  }, [groupData])
  const allUsernames = Object.keys(allUsersMap)

  // 各ユーザーのグループ所属を計算
  const userData = useMemo(() => {
    // Set を一度だけ作成（ループ外）
    const setA = new Set(gA.users.map(u => u.username))
    const setB = new Set(gB.users.map(u => u.username))
    const setC = new Set(gC.users.map(u => u.username))

    return allUsernames.map(username => {
      const user = allUsersMap[username]
      const inA = setA.has(username)
      const inB = setB.has(username)
      const inC = setC.has(username)

      // _fanCache があれば再計算を回避
      const fanA = ((user._fanCache && user._fanCache[gA.def.id]) || detectFanOf(user, membersA)).length
      const fanB = ((user._fanCache && user._fanCache[gB.def.id]) || detectFanOf(user, membersB)).length
      const fanC = ((user._fanCache && user._fanCache[gC.def.id]) || detectFanOf(user, membersC)).length

      return { username, inA, inB, inC, fanA, fanB, fanC }
    }).filter(d => d.inA || d.inB || d.inC)
  }, [allUsersMap, allUsernames])

  // 三角形の頂点座標 (SVG座標)
  const W = 500, H = 450
  const pad = 50
  const triTop = { x: W / 2, y: pad }
  const triLeft = { x: pad, y: H - pad }
  const triRight = { x: W - pad, y: H - pad }

  // 3カテゴリの分布
  const onlyA = userData.filter(d => d.inA && !d.inB && !d.inC).length
  const onlyB = userData.filter(d => d.inB && !d.inA && !d.inC).length
  const onlyC = userData.filter(d => d.inC && !d.inA && !d.inB).length
  const abOnly = userData.filter(d => d.inA && d.inB && !d.inC).length
  const acOnly = userData.filter(d => d.inA && d.inC && !d.inB).length
  const bcOnly = userData.filter(d => d.inB && d.inC && !d.inA).length
  const abc = userData.filter(d => d.inA && d.inB && d.inC).length

  // 各ゾーンの位置
  const zones = [
    { label: `${onlyA}`, x: triTop.x, y: triTop.y + 70, color: gA.def.solidColor, desc: getGroupShortLabel(gA.def) + 'のみ' },
    { label: `${onlyB}`, x: triLeft.x + 60, y: triLeft.y - 50, color: gB.def.solidColor, desc: getGroupShortLabel(gB.def) + 'のみ' },
    { label: `${onlyC}`, x: triRight.x - 60, y: triRight.y - 50, color: gC.def.solidColor, desc: getGroupShortLabel(gC.def) + 'のみ' },
    { label: `${abOnly}`, x: (triTop.x + triLeft.x) / 2 + 10, y: (triTop.y + triLeft.y) / 2, color: '#eab308', desc: 'A∩B' },
    { label: `${acOnly}`, x: (triTop.x + triRight.x) / 2 - 10, y: (triTop.y + triRight.y) / 2, color: '#eab308', desc: 'A∩C' },
    { label: `${bcOnly}`, x: (triLeft.x + triRight.x) / 2, y: (triLeft.y + triRight.y) / 2 - 20, color: '#eab308', desc: 'B∩C' },
    { label: `${abc}`, x: W / 2, y: H / 2 + 10, color: '#f97316', desc: '全共通' },
  ]

  return (
    <div className="p-5 bg-gray-800 rounded-xl">
      <h3 className="text-sm font-bold mb-1">9. 3グループ トライアングルマップ</h3>
      <p className="text-xs text-gray-500 mb-4">3グループの所属分布を三角形で表示（{userData.length}ユーザー）</p>
      <div className="flex justify-center">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full max-w-lg">
          {/* 三角形の背景 */}
          <polygon
            points={`${triTop.x},${triTop.y} ${triLeft.x},${triLeft.y} ${triRight.x},${triRight.y}`}
            fill="rgba(55,65,81,0.2)"
            stroke="rgba(75,85,99,0.6)"
            strokeWidth="2"
          />

          {/* 内部分割線 */}
          <line x1={W / 2} y1={triTop.y} x2={W / 2} y2={H - pad} stroke="rgba(75,85,99,0.3)" strokeWidth="1" strokeDasharray="4,4" />
          <line x1={(triTop.x + triLeft.x) / 2} y1={(triTop.y + triLeft.y) / 2} x2={(triRight.x + (triLeft.x + triRight.x) / 2) / 2 + 30} y2={(triRight.y + (triLeft.y + triRight.y) / 2) / 2 - 10} stroke="rgba(75,85,99,0.3)" strokeWidth="1" strokeDasharray="4,4" />
          <line x1={(triTop.x + triRight.x) / 2} y1={(triTop.y + triRight.y) / 2} x2={(triLeft.x + (triLeft.x + triRight.x) / 2) / 2 - 30} y2={(triLeft.y + (triLeft.y + triRight.y) / 2) / 2 - 10} stroke="rgba(75,85,99,0.3)" strokeWidth="1" strokeDasharray="4,4" />

          {/* 頂点ラベル */}
          <text x={triTop.x} y={triTop.y - 15} fill={gA.def.solidColor} fontSize="14" fontWeight="bold" textAnchor="middle">
            {getGroupShortLabel(gA.def)}
          </text>
          <text x={triLeft.x - 10} y={triLeft.y + 20} fill={gB.def.solidColor} fontSize="14" fontWeight="bold" textAnchor="middle">
            {getGroupShortLabel(gB.def)}
          </text>
          <text x={triRight.x + 10} y={triRight.y + 20} fill={gC.def.solidColor} fontSize="14" fontWeight="bold" textAnchor="middle">
            {getGroupShortLabel(gC.def)}
          </text>

          {/* 各ゾーンの数値 */}
          {zones.map((z, i) => (
            <g key={i}>
              <circle cx={z.x} cy={z.y} r={Math.max(16, Math.min(30, parseInt(z.label) * 0.8 + 14))} fill={z.color} opacity="0.25" />
              <text x={z.x} y={z.y + 5} fill={z.color} fontSize="16" fontWeight="bold" textAnchor="middle">
                {z.label}
              </text>
            </g>
          ))}

          {/* 中央の「全共通」ラベル */}
          {abc > 0 && (
            <text x={W / 2} y={H / 2 + 35} fill="#9ca3af" fontSize="10" textAnchor="middle">全共通</text>
          )}
        </svg>
      </div>

      {/* 凡例テーブル */}
      <div className="grid grid-cols-4 gap-2 mt-4 text-xs">
        <div className={`text-center p-2 ${gA.def.bgClass} rounded`}>
          <div className={`font-bold text-lg ${gA.def.textClass}`}>{onlyA}</div>
          <div className="text-gray-500">{getGroupShortLabel(gA.def)}のみ</div>
        </div>
        <div className={`text-center p-2 ${gB.def.bgClass} rounded`}>
          <div className={`font-bold text-lg ${gB.def.textClass}`}>{onlyB}</div>
          <div className="text-gray-500">{getGroupShortLabel(gB.def)}のみ</div>
        </div>
        <div className={`text-center p-2 ${gC.def.bgClass} rounded`}>
          <div className={`font-bold text-lg ${gC.def.textClass}`}>{onlyC}</div>
          <div className="text-gray-500">{getGroupShortLabel(gC.def)}のみ</div>
        </div>
        <div className="text-center p-2 bg-orange-900/30 rounded">
          <div className="font-bold text-lg text-orange-400">{abc}</div>
          <div className="text-gray-500">全共通</div>
        </div>
      </div>
    </div>
  )
}

// ============================================================
// Summary Stats
// ============================================================
function SummaryStats({ groupData }) {
  const active = groupData.filter(gd => gd.users.length > 0)

  const avgFollowers = (users) => {
    const vals = users.map(u => parseFollowerCount(u.followers_count)).filter(v => v > 0)
    if (vals.length === 0) return 0
    return Math.round(vals.reduce((a, b) => a + b, 0) / vals.length)
  }

  const medianFollowers = (users) => {
    const vals = users.map(u => parseFollowerCount(u.followers_count)).filter(v => v > 0).sort((a, b) => a - b)
    if (vals.length === 0) return 0
    const mid = Math.floor(vals.length / 2)
    return vals.length % 2 ? vals[mid] : Math.round((vals[mid - 1] + vals[mid]) / 2)
  }

  const statRows = [
    { label: 'ファン検出数', values: active.map(gd => gd.users.length) },
    { label: '平均フォロワー', values: active.map(gd => avgFollowers(gd.users)) },
    { label: '中央値フォロワー', values: active.map(gd => medianFollowers(gd.users)) },
    {
      label: 'DM開放率',
      values: active.map(gd =>
        gd.users.length ? `${((gd.users.filter(u => u.can_dm === true).length / gd.users.length) * 100).toFixed(1)}%` : '-'
      ),
      isText: true,
    },
  ]

  return (
    <div className="p-5 bg-gray-800 rounded-xl">
      <h3 className="text-sm font-bold mb-4">サマリー</h3>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-gray-500 text-xs">
            <th className="text-left py-1.5"></th>
            {active.map(gd => (
              <th key={gd.def.id} className={`text-right py-1.5 ${gd.def.textClass}`}>
                {getGroupShortLabel(gd.def)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {statRows.map(s => (
            <tr key={s.label} className="border-t border-gray-700/50">
              <td className="py-2 text-gray-300">{s.label}</td>
              {active.map((gd, i) => (
                <td key={gd.def.id} className={`py-2 text-right font-bold ${gd.def.textClass}`}>
                  {s.isText ? s.values[i] : (typeof s.values[i] === 'number' ? s.values[i].toLocaleString() : s.values[i])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ============================================================
// Main ComparisonPanel
// ============================================================
export default function ComparisonPanel({ ampUsers, snkUsers, knxUsers, mtorUsers }) {
  const allGroupData = useMemo(() => [
    { def: GROUP_DEFS[0], users: ampUsers },
    { def: GROUP_DEFS[1], users: snkUsers },
    { def: GROUP_DEFS[2], users: knxUsers },
    { def: GROUP_DEFS[3], users: mtorUsers },
  ], [ampUsers, snkUsers, knxUsers, mtorUsers])

  // 全グループ分析モード（1つのデータでも全グループのメンバーで分析）
  const [crossAnalysis, setCrossAnalysis] = useState(false)

  // 全ユーザーの統合マップ（重複排除）
  const mergedUsers = useMemo(() => {
    const map = {}
    allGroupData.forEach(gd => gd.users.forEach(u => { if (u.username) map[u.username] = u }))
    return Object.values(map)
  }, [allGroupData])

  // クロス分析モード時: 全グループに同じユーザーセットを割り当て
  const crossGroupData = useMemo(() =>
    GROUP_DEFS.map(def => ({ def, users: mergedUsers })),
    [mergedUsers]
  )

  // データのあるグループIDをデフォルトで選択
  const defaultSelected = useMemo(() =>
    allGroupData.filter(gd => gd.users.length > 0).map(gd => gd.def.id),
    [allGroupData]
  )
  const [selectedIds, setSelectedIds] = useState(defaultSelected)

  // 新しいグループデータが追加されたら選択に反映
  useEffect(() => {
    setSelectedIds(prev => {
      const withData = allGroupData.filter(gd => gd.users.length > 0).map(gd => gd.def.id)
      const newIds = withData.filter(id => !prev.includes(id))
      if (newIds.length > 0) return [...prev, ...newIds]
      return prev
    })
  }, [allGroupData])

  // クロス分析ON時の選択ID
  const [crossSelectedIds, setCrossSelectedIds] = useState(GROUP_DEFS.map(d => d.id))

  // 現在のモードに応じたデータとセレクター
  const activeGroupData = crossAnalysis ? crossGroupData : allGroupData
  const activeSelectedIds = crossAnalysis ? crossSelectedIds : selectedIds
  const activeSetSelectedIds = crossAnalysis ? setCrossSelectedIds : setSelectedIds

  // 選択変更時にデータのあるグループを自動追加
  const effectiveSelected = useMemo(() => {
    if (crossAnalysis) {
      return crossSelectedIds.length > 0 ? crossSelectedIds : GROUP_DEFS.map(d => d.id)
    }
    const withData = allGroupData.filter(gd => gd.users.length > 0).map(gd => gd.def.id)
    const valid = selectedIds.filter(id => withData.includes(id))
    if (valid.length === 0) return withData
    return valid
  }, [crossAnalysis, crossSelectedIds, selectedIds, allGroupData])

  const filteredGroupData = useMemo(() =>
    activeGroupData.filter(gd => effectiveSelected.includes(gd.def.id)),
    [activeGroupData, effectiveSelected]
  )

  // クロス分析モード: 各グループのファンだけに絞ったデータ（サマリー/DM/フォロワー/年齢/ハート用）
  const fanFilteredGroupData = useMemo(() => {
    if (!crossAnalysis) return filteredGroupData
    return filteredGroupData.map(gd => {
      const members = GROUPS[gd.def.id]?.members || {}
      const fans = gd.users.filter(user => {
        const f = (user._fanCache && user._fanCache[gd.def.id])
          ? user._fanCache[gd.def.id]
          : detectFanOf(user, members)
        return f.length > 0
      })
      return { ...gd, users: fans }
    })
  }, [crossAnalysis, filteredGroupData])

  const totalUsers = ampUsers.length + snkUsers.length + knxUsers.length + mtorUsers.length
  const loadedCount = allGroupData.filter(gd => gd.users.length > 0).length
  const is3GroupMode = filteredGroupData.filter(gd => gd.users.length > 0).length >= 3

  if (totalUsers === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="text-6xl mb-6">📊</div>
        <h2 className="text-xl font-bold mb-2">分析データがありません</h2>
        <p className="text-gray-400 max-w-md mb-4">
          データを読み込むとグループ分析・比較ができます。
        </p>
        <div className="text-sm text-gray-500 space-y-1">
          <p>1. ヘッダーでグループを選択してスクレイプまたはファイル追加</p>
          <p>2. 完了後「結果を見る」でデータを読み込み</p>
          <p>3. このタブでチャートが表示されます</p>
        </div>
      </div>
    )
  }


  return (
    <div className="space-y-4">
      {/* ヘッダー + グループセレクター */}
      <div className="p-4 bg-gray-800 rounded-xl space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold flex items-center gap-2">
              📊 {crossAnalysis ? 'クロスグループ分析' : loadedCount >= 2 ? 'グループ比較' : 'グループ分析'}
            </h2>
            <p className="text-xs text-gray-400 mt-0.5">
              {crossAnalysis
                ? `全${mergedUsers.length}人を全グループのメンバーで分析`
                : filteredGroupData.filter(gd => gd.users.length > 0).map(gd =>
                    `${getGroupShortLabel(gd.def)}: ${gd.users.length}人`
                  ).join(' / ')
              }
            </p>
          </div>
          <div className="flex items-center gap-2">
            {is3GroupMode && !crossAnalysis && (
              <span className="px-2.5 py-1 text-[10px] font-bold bg-gradient-to-r from-blue-600 via-emerald-600 to-purple-600 rounded-full text-white">
                3グループ比較
              </span>
            )}
            <button
              onClick={() => setCrossAnalysis(prev => !prev)}
              className={`px-3 py-1.5 text-[11px] rounded-lg transition font-medium border ${
                crossAnalysis
                  ? 'bg-amber-600 border-amber-500 text-white'
                  : 'border-gray-600 text-gray-400 hover:text-white hover:border-gray-500'
              }`}
            >
              {crossAnalysis ? '🔀 クロス分析 ON' : '🔀 クロス分析'}
            </button>
          </div>
        </div>
        <GroupSelector
          allGroupData={activeGroupData}
          selectedIds={effectiveSelected}
          setSelectedIds={activeSetSelectedIds}
          crossMode={crossAnalysis}
        />
      </div>

      <SummaryStats groupData={fanFilteredGroupData} />
      {!crossAnalysis && <VennDiagram groupData={filteredGroupData} />}

      {/* 3グループ選択時のトライアングルマップ */}
      {is3GroupMode && !crossAnalysis && <TriangleMap groupData={filteredGroupData} />}

      <CrossHeatmap groupData={filteredGroupData} />
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <FanCountBar groupData={filteredGroupData} />
        <GroupShareDoughnuts groupData={filteredGroupData} />
      </div>
      <DmComparisonBar groupData={fanFilteredGroupData} />
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <FollowerHistogram groupData={fanFilteredGroupData} />
        <AccountAgeChart groupData={fanFilteredGroupData} />
      </div>
      <HeartRadar groupData={fanFilteredGroupData} />
    </div>
  )
}
