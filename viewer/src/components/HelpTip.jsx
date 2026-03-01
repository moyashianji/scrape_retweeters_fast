import { useState } from 'react'

export default function HelpTip({ text }) {
  const [show, setShow] = useState(false)

  return (
    <span className="relative inline-flex ml-1.5">
      <span
        className="w-4 h-4 flex items-center justify-center rounded-full bg-gray-600 text-gray-300 text-[10px] cursor-help hover:bg-gray-500 transition"
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
      >
        ?
      </span>
      {show && (
        <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-gray-700 border border-gray-600 text-xs text-gray-200 rounded-lg shadow-xl whitespace-pre-line w-56 z-50 pointer-events-none">
          {text}
          <span className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-700" />
        </span>
      )}
    </span>
  )
}
