import { useState, useRef, useEffect, type KeyboardEvent } from "react"
import { usePipelineState } from "../context/PipelineContext"

interface Props {
  onSubmit: (text: string) => void
}

export function PromptInput({ onSubmit }: Props) {
  const [value, setValue] = useState("")
  const { isWorking, messages } = usePipelineState()
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-focus when input becomes enabled (e.g. after questions arrive)
  useEffect(() => {
    if (!isWorking) {
      textareaRef.current?.focus()
    }
  }, [isWorking])

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = "auto"
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`
  }, [value])

  const lastMessage = messages[messages.length - 1]
  const isAwaitingAnswer = lastMessage?.type === "chat.question_group"

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  function submit() {
    const trimmed = value.trim()
    if (!trimmed || isWorking) return
    onSubmit(trimmed)
    setValue("")
  }

  const placeholder = isWorking
    ? "Frankenstein is working..."
    : isAwaitingAnswer
      ? "Answer the questions above..."
      : "Type a message..."

  return (
    <div className="fixed bottom-0 left-0 right-0 min-[1024px]:right-[240px] bg-surface-elevated/80 backdrop-blur-xl border-t border-border z-10">
      <div className="max-w-[720px] mx-auto px-4 py-3">
        <div className="flex gap-2 items-end">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isWorking}
            placeholder={placeholder}
            rows={1}
            className="flex-1 resize-none bg-bg border border-border rounded-xl px-4 py-3 text-[14px] leading-[1.5] text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-accent/50 focus:ring-1 focus:ring-accent/30 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          />
          <button
            onClick={submit}
            disabled={isWorking || !value.trim()}
            className="h-[44px] px-5 bg-accent text-bg font-medium text-[13px] rounded-xl hover:brightness-110 active:scale-[0.97] transition-all duration-100 disabled:opacity-30 disabled:cursor-not-allowed shrink-0"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  )
}
