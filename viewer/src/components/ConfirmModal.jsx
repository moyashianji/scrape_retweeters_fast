export default function ConfirmModal({ open, title, message, onConfirm, onCancel, confirmLabel = '実行', cancelLabel = 'キャンセル', danger = false }) {
  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onCancel} />
      <div className="relative bg-gray-800 border border-gray-600 rounded-xl shadow-2xl p-6 max-w-sm w-full mx-4">
        <h3 className="text-lg font-bold mb-2">{title}</h3>
        <p className="text-sm text-gray-300 mb-6">{message}</p>
        <div className="flex gap-3 justify-end">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm bg-gray-700 hover:bg-gray-600 rounded-lg transition"
          >
            {cancelLabel}
          </button>
          <button
            onClick={onConfirm}
            className={`px-4 py-2 text-sm font-semibold rounded-lg transition ${
              danger
                ? 'bg-red-600 hover:bg-red-700'
                : 'bg-blue-600 hover:bg-blue-700'
            }`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
