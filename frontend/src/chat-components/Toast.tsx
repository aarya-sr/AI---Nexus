import { useEffect, useState } from "react"

interface Props {
  message: string
  onDismiss: () => void
  duration?: number
}

export function Toast({ message, onDismiss, duration = 3000 }: Props) {
  const [visible, setVisible] = useState(true)

  useEffect(() => {
    const timer = setTimeout(() => {
      setVisible(false)
      setTimeout(onDismiss, 200) // wait for fade-out
    }, duration)
    return () => clearTimeout(timer)
  }, [duration, onDismiss])

  return (
    <div
      className={`fixed top-6 right-6 z-50 bg-surface-elevated border border-border rounded-xl px-5 py-3 shadow-lg transition-opacity duration-200 ${
        visible ? "opacity-100" : "opacity-0"
      }`}
    >
      <span className="text-[13px] text-text-primary font-medium">{message}</span>
    </div>
  )
}
