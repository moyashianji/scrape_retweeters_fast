import { useState, useEffect, useCallback } from 'react'

const ICONS = {
  success: '✓',
  error: '✗',
  info: 'i',
  warning: '!',
}

const COLORS = {
  success: 'bg-green-600 border-green-500',
  error: 'bg-red-600 border-red-500',
  info: 'bg-blue-600 border-blue-500',
  warning: 'bg-yellow-600 border-yellow-500',
}

function ToastItem({ toast, onRemove }) {
  useEffect(() => {
    const timer = setTimeout(() => onRemove(toast.id), toast.duration || 4000)
    return () => clearTimeout(timer)
  }, [toast, onRemove])

  return (
    <div
      className={`flex items-center gap-3 px-4 py-3 rounded-lg border shadow-lg text-white text-sm animate-slide-in ${COLORS[toast.type] || COLORS.info}`}
    >
      <span className="w-6 h-6 flex items-center justify-center rounded-full bg-white/20 text-xs font-bold flex-shrink-0">
        {ICONS[toast.type] || ICONS.info}
      </span>
      <span className="flex-1">{toast.message}</span>
      <button
        onClick={() => onRemove(toast.id)}
        className="text-white/60 hover:text-white text-lg leading-none ml-2"
      >
        ×
      </button>
    </div>
  )
}

export function ToastContainer({ toasts, removeToast }) {
  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
      {toasts.map(t => (
        <ToastItem key={t.id} toast={t} onRemove={removeToast} />
      ))}
    </div>
  )
}

let _nextId = 0

export function useToast() {
  const [toasts, setToasts] = useState([])

  const addToast = useCallback((message, type = 'info', duration = 4000) => {
    const id = ++_nextId
    setToasts(prev => [...prev, { id, message, type, duration }])
  }, [])

  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  return { toasts, addToast, removeToast }
}
