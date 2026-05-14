import type { ChatEntry } from "../types/pipeline"

interface Props {
  entry: ChatEntry
}

function UserAvatar() {
  return (
    <div className="w-7 h-7 rounded-full bg-accent/20 border border-accent/30 flex items-center justify-center shrink-0">
      <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
        <circle cx="8" cy="5.5" r="2.5" stroke="currentColor" strokeWidth="1.5" className="text-accent" />
        <path d="M3 14c0-2.76 2.24-5 5-5s5 2.24 5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" className="text-accent" />
      </svg>
    </div>
  )
}

function SystemAvatar() {
  return (
    <div className="w-7 h-7 rounded-full bg-surface-elevated border border-border flex items-center justify-center shrink-0">
      <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
        <path d="M8 1L10 5.5L15 6.5L11.5 10L12.5 15L8 12.5L3.5 15L4.5 10L1 6.5L6 5.5L8 1Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" className="text-text-secondary" />
      </svg>
    </div>
  )
}

export { SystemAvatar }

export function ChatMessage({ entry }: Props) {
  const isUser = entry.variant === "user"
  const text = (entry.payload as { text?: string }).text ?? ""

  if (isUser) {
    return (
      <div className="flex items-start gap-3 justify-end animate-[fadeUp_200ms_ease-out]">
        <div className="max-w-[80%] bg-accent/15 border border-accent/20 rounded-2xl rounded-br-md px-4 py-3">
          <p className="text-[14px] leading-[1.6] text-text-primary whitespace-pre-wrap">
            {text}
          </p>
        </div>
        <UserAvatar />
      </div>
    )
  }

  return (
    <div className="flex items-start gap-3 animate-[fadeUp_200ms_ease-out]">
      <SystemAvatar />
      <div className="max-w-[80%] bg-surface rounded-2xl rounded-bl-md px-4 py-3">
        <p className="text-[14px] leading-[1.6] text-text-primary whitespace-pre-wrap">
          {text}
        </p>
      </div>
    </div>
  )
}
