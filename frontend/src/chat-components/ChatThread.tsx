import { useEffect, useRef, useState } from "react"
import { usePipelineState } from "../context/PipelineContext"
import { ChatMessage } from "./ChatMessage"
import { TypingIndicator } from "./TypingIndicator"

export function ChatThread() {
  const { messages, isWorking } = usePipelineState()
  const bottomRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [userScrolledUp, setUserScrolledUp] = useState(false)

  useEffect(() => {
    if (!userScrolledUp) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" })
    }
  }, [messages, isWorking, userScrolledUp])

  function handleScroll() {
    const el = containerRef.current
    if (!el) return
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 100
    setUserScrolledUp(!atBottom)
  }

  function scrollToBottom() {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
    setUserScrolledUp(false)
  }

  return (
    <div
      ref={containerRef}
      onScroll={handleScroll}
      className="flex-1 overflow-y-auto px-4 pb-28"
    >
      <div className="max-w-[720px] mx-auto flex flex-col pt-6">
        {messages.map((entry, i) => {
          const prev = messages[i - 1]
          const gapClass =
            prev?.variant === entry.variant ? "mt-2" : "mt-4"

          return (
            <div key={entry.id} className={i === 0 ? "" : gapClass}>
              <ChatMessage entry={entry} />
            </div>
          )
        })}

        {isWorking && (
          <div className="mt-4">
            <TypingIndicator />
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {userScrolledUp && messages.length > 0 && (
        <button
          onClick={scrollToBottom}
          className="fixed bottom-24 left-1/2 -translate-x-1/2 bg-surface-elevated border border-border rounded-full px-4 py-2 text-xs text-text-secondary hover:text-text-primary transition-colors z-20"
        >
          New messages ↓
        </button>
      )}
    </div>
  )
}
