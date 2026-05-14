import { useCallback, useEffect, useRef, useState } from "react"
import { usePipelineState, usePipelineDispatch } from "../context/PipelineContext"
import { useWebSocket } from "../hooks/useWebSocket"
import { approveCheckpoint } from "../api/sessions"
import { ChatMessage } from "./ChatMessage"
import { PhaseDivider } from "./PhaseDivider"
import { RequirementsCard } from "./RequirementsCard"
import { TypingIndicator } from "./TypingIndicator"
import type { RequirementsDoc } from "../types/models"

export function ChatThread() {
  const { messages, isWorking, sessionId } = usePipelineState()
  const dispatch = usePipelineDispatch()
  const { sendMessage } = useWebSocket(sessionId)
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

  const handleApprove = useCallback(async () => {
    if (!sessionId) return
    await approveCheckpoint(sessionId, "requirements", true)
    dispatch({ type: "SET_WORKING", payload: true })
  }, [sessionId, dispatch])

  const handleEdit = useCallback(
    (corrections: string) => {
      if (!sessionId) return
      dispatch({ type: "SET_WORKING", payload: true })
      sendMessage({
        type: "control.user_input",
        payload: { text: corrections },
        session_id: sessionId,
      })
    },
    [sessionId, dispatch, sendMessage]
  )

  // Track if PhaseDivider for "Requirements Summary" was already rendered
  let requirementsDividerShown = false

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

          // Render checkpoint messages as RequirementsCard with PhaseDivider
          if (entry.type === "chat.checkpoint") {
            const cp = entry.payload as { checkpoint_type?: string; requirements?: RequirementsDoc }
            if (cp.checkpoint_type === "requirements" && cp.requirements) {
              const showDivider = !requirementsDividerShown
              requirementsDividerShown = true
              return (
                <div key={entry.id} className={i === 0 ? "" : "mt-4"}>
                  {showDivider && <PhaseDivider label="Requirements Summary" />}
                  <RequirementsCard
                    requirements={cp.requirements}
                    onApprove={handleApprove}
                    onEdit={handleEdit}
                  />
                </div>
              )
            }
          }

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
