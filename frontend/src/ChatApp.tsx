import { useCallback, useRef, useState } from "react"
import { useLocation } from "react-router-dom"
import { createSession } from "./api/sessions"
import { PipelineProvider, usePipelineState, usePipelineDispatch } from "./context/PipelineContext"
import { useWebSocket } from "./hooks/useWebSocket"
import { ChatThread } from "./chat-components/ChatThread"
import { PipelineSidebar } from "./chat-components/PipelineSidebar"
import { PromptInput } from "./chat-components/PromptInput"
import { Toast } from "./chat-components/Toast"

function EntryScreen({ onSubmit, initialPrompt }: { onSubmit: (text: string) => void; initialPrompt?: string }) {
  return (
    <div className="entry-screen min-h-screen flex flex-col items-center justify-center px-6 relative overflow-hidden">
      <div className="entry-glow" />
      <h1
        className="text-text-primary tracking-[-0.02em] mb-3"
        style={{ fontFamily: "'Special Elite', cursive", fontSize: "clamp(2.5rem, 5vw, 4rem)", fontWeight: 400, lineHeight: 1.2 }}
      >
        Frankenstein
      </h1>
      <p className="text-[14px] text-text-tertiary mb-8">
        Describe your workflow. Get working AI agents.
      </p>
      <div className="w-full max-w-[480px]">
        <textarea
          autoFocus
          defaultValue={initialPrompt ?? ""}
          placeholder="Describe the workflow you want to automate..."
          rows={3}
          className="w-full resize-none bg-surface border border-border rounded-lg px-4 py-3 text-[14px] leading-[1.6] text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent"
          id="chat-entry-prompt"
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault()
              const val = e.currentTarget.value.trim()
              if (val) onSubmit(val)
            }
          }}
        />
        <button
          className="mt-3 w-full py-2.5 rounded-lg bg-accent text-neutral-900 font-semibold text-[14px] hover:bg-amber-600 transition-colors min-h-[44px]"
          onClick={() => {
            const el = document.getElementById("chat-entry-prompt") as HTMLTextAreaElement | null
            const val = el?.value.trim()
            if (val) onSubmit(val)
          }}
        >
          Assemble
        </button>
      </div>
    </div>
  )
}

function ChatLayout() {
  const state = usePipelineState()
  const dispatch = usePipelineDispatch()
  const { sendMessage } = useWebSocket(state.sessionId)
  const location = useLocation()
  const locationPrompt = (location.state as { prompt?: string } | null)?.prompt

  const startingRef = useRef(false)

  const handleFirstPrompt = useCallback(
    async (text: string) => {
      if (startingRef.current) return
      startingRef.current = true
      let session_id: string
      try {
        session_id = await createSession()
      } catch (err) {
        console.error("Failed to create session:", err)
        startingRef.current = false
        return
      }
      dispatch({ type: "SET_SESSION", payload: session_id })
      dispatch({ type: "SET_STARTED" })
      dispatch({ type: "SET_WORKING", payload: true })

      dispatch({
        type: "CHAT_MESSAGE",
        payload: {
          id: `user-${Date.now()}`,
          variant: "user",
          type: "chat.message",
          payload: { text },
          timestamp: new Date().toISOString(),
        },
      })

      // sendMessage queues if WS not yet open; flushes on connect
      sendMessage({
        type: "control.user_input",
        payload: { text },
        session_id,
      })
    },
    [dispatch, sendMessage]
  )

  const handleMessage = useCallback(
    (text: string) => {
      dispatch({
        type: "CHAT_MESSAGE",
        payload: {
          id: `user-${Date.now()}`,
          variant: "user",
          type: "chat.message",
          payload: { text },
          timestamp: new Date().toISOString(),
        },
      })
      dispatch({ type: "SET_WORKING", payload: true })

      sendMessage({
        type: "control.user_input",
        payload: { text },
        session_id: state.sessionId!,
      })
    },
    [dispatch, sendMessage, state.sessionId]
  )

  const [showResetConfirm, setShowResetConfirm] = useState(false)

  const handleReset = useCallback(() => {
    sessionStorage.removeItem("frankenstein_session")
    dispatch({ type: "RESET" })
    startingRef.current = false
    setShowResetConfirm(false)
  }, [dispatch])

  if (!state.hasStarted) {
    return <EntryScreen onSubmit={handleFirstPrompt} initialPrompt={locationPrompt} />
  }

  return (
    <div className="min-h-screen grid grid-cols-[1fr] min-[1024px]:grid-cols-[1fr_240px]">
      <div className="flex flex-col min-w-0">
        {/* Top bar */}
        <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-bg/80 backdrop-blur-sm shrink-0">
          <span
            className="text-[15px] text-text-primary"
            style={{ fontFamily: "'Special Elite', cursive" }}
          >
            Frankenstein
          </span>
          {showResetConfirm ? (
            <div className="flex items-center gap-2">
              <span className="text-[12px] text-text-tertiary">Start over?</span>
              <button
                onClick={handleReset}
                className="text-[12px] text-red-400 hover:text-red-300 transition-colors px-2 py-1"
              >
                Yes
              </button>
              <button
                onClick={() => setShowResetConfirm(false)}
                className="text-[12px] text-text-tertiary hover:text-text-primary transition-colors px-2 py-1"
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              onClick={() => setShowResetConfirm(true)}
              className="text-[12px] text-text-tertiary hover:text-text-primary transition-colors px-2 py-1 rounded"
              title="Start a new chat"
            >
              New chat
            </button>
          )}
        </div>
        <ChatThread sendMessage={sendMessage} />
        <PromptInput onSubmit={handleMessage} />
      </div>
      <PipelineSidebar />
      {state.toastMessage && (
        <Toast
          message={state.toastMessage}
          onDismiss={() => dispatch({ type: "DISMISS_TOAST" })}
        />
      )}
    </div>
  )
}

export default function ChatApp() {
  return (
    <PipelineProvider>
      <ChatLayout />
    </PipelineProvider>
  )
}
