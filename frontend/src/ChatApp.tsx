import { useCallback } from "react"
import { PipelineProvider, usePipelineState, usePipelineDispatch } from "./context/PipelineContext"
import { useWebSocket } from "./hooks/useWebSocket"
import { ChatThread } from "./chat-components/ChatThread"
import { PipelineSidebar } from "./chat-components/PipelineSidebar"
import { PromptInput } from "./chat-components/PromptInput"

function EntryScreen({ onSubmit }: { onSubmit: (text: string) => void }) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4">
      <h1 className="text-[28px] font-bold text-text-primary tracking-[-0.02em] mb-2">
        Frankenstein
      </h1>
      <p className="text-[14px] text-text-tertiary mb-12">
        Describe your workflow. Get working AI agents.
      </p>
      <div className="w-full max-w-[560px]">
        <textarea
          autoFocus
          placeholder="Describe the workflow you want to automate..."
          rows={3}
          className="w-full resize-none bg-surface border border-border rounded-xl px-5 py-4 text-[15px] leading-[1.6] text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent"
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault()
              const val = e.currentTarget.value.trim()
              if (val) onSubmit(val)
            }
          }}
        />
      </div>
    </div>
  )
}

function ChatLayout() {
  const state = usePipelineState()
  const dispatch = usePipelineDispatch()
  const { sendMessage } = useWebSocket(state.sessionId)

  const handleFirstPrompt = useCallback(
    async (text: string) => {
      let session_id: string
      try {
        const res = await fetch("/api/sessions", { method: "POST" })
        if (!res.ok) throw new Error(`Server error: ${res.status}`)
        const body = await res.json()
        session_id = body.session_id
      } catch (err) {
        console.error("Failed to create session:", err)
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

  if (!state.hasStarted) {
    return <EntryScreen onSubmit={handleFirstPrompt} />
  }

  return (
    <div className="min-h-screen flex">
      <div className="flex-1 flex flex-col min-w-0">
        <ChatThread />
        <PromptInput onSubmit={handleMessage} />
      </div>
      <PipelineSidebar />
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
