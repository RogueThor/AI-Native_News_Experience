import { useState } from 'react'

export interface ToastItem { id: number; msg: string }

export function useToast() {
  const [toasts, setToasts] = useState<ToastItem[]>([])
  function addToast(msg: string) {
    const id = Date.now()
    setToasts(prev => [...prev, { id, msg }])
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 3200)
  }
  function removeToast(id: number) {
    setToasts(prev => prev.filter(t => t.id !== id))
  }
  return { toasts, addToast, removeToast }
}

interface ToastProps { toasts: ToastItem[]; onRemove: (id: number) => void }

export default function Toast({ toasts }: ToastProps) {
  return (
    <div className="toast-container">
      {toasts.map(t => (
        <div key={t.id} className="toast-item">{t.msg}</div>
      ))}
    </div>
  )
}
