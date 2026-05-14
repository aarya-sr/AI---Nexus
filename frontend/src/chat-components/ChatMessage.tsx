import type { ChatEntry } from "../types/pipeline"

interface Props {
  entry: ChatEntry
}

export function ChatMessage({ entry }: Props) {
  const isUser = entry.variant === "user"
  const text = (entry.payload as { text?: string }).text ?? ""

  return (
    <div
      className={`
        animate-[fadeUp_250ms_ease-out]
        ${isUser ? "ml-12 bg-transparent" : "bg-surface rounded-xl px-5 py-4"}
      `}
    >
      <p className="text-[15px] leading-[1.6] text-text-primary whitespace-pre-wrap">
        {text}
      </p>
    </div>
  )
}
