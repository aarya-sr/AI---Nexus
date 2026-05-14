import { useEffect, useRef, useCallback } from "react"
import { usePipelineDispatch } from "../context/PipelineContext"
import type { ServerMessage } from "../types/messages"

const WS_BASE = `ws://${window.location.hostname}:8000`

export function useWebSocket(sessionId: string | null) {
  const dispatch = usePipelineDispatch()
  const chatWsRef = useRef<WebSocket | null>(null)
  const statusWsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!sessionId) return

    const chatWs = new WebSocket(`${WS_BASE}/ws/chat/${sessionId}`)
    const statusWs = new WebSocket(`${WS_BASE}/ws/status/${sessionId}`)
    chatWsRef.current = chatWs
    statusWsRef.current = statusWs

    chatWs.onopen = () => dispatch({ type: "SET_CONNECTED", payload: true })
    chatWs.onclose = () => dispatch({ type: "SET_CONNECTED", payload: false })

    chatWs.onmessage = (event) => {
      const msg: ServerMessage = JSON.parse(event.data)
      handleMessage(msg)
    }

    statusWs.onmessage = (event) => {
      const msg: ServerMessage = JSON.parse(event.data)
      handleMessage(msg)
    }

    function handleMessage(msg: ServerMessage) {
      switch (msg.type) {
        case "chat.message":
          dispatch({
            type: "CHAT_MESSAGE",
            payload: {
              id: `msg-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
              variant: "system",
              type: msg.type,
              payload: msg.payload,
              timestamp: msg.timestamp,
            },
          })
          break

        case "chat.question_group":
          dispatch({
            type: "CHAT_MESSAGE",
            payload: {
              id: `qg-${Date.now()}`,
              variant: "system",
              type: msg.type,
              payload: msg.payload,
              timestamp: msg.timestamp,
            },
          })
          break

        case "chat.checkpoint":
          dispatch({
            type: "CHAT_MESSAGE",
            payload: {
              id: `cp-${Date.now()}`,
              variant: "system",
              type: msg.type,
              payload: msg.payload,
              timestamp: msg.timestamp,
            },
          })
          dispatch({ type: "SET_WORKING", payload: false })
          break

        case "status.stage_update":
          dispatch({
            type: "STAGE_UPDATE",
            payload: msg.payload as { stage: string; description: string },
          })
          break

        case "status.progress":
          dispatch({
            type: "PROGRESS",
            payload: msg.payload as { stage: string; percent: number; detail: string },
          })
          break

        case "status.complete":
          dispatch({ type: "COMPLETE", payload: msg.payload })
          break

        case "error.llm_failure":
        case "error.pipeline_failure":
          dispatch({
            type: "ERROR",
            payload: msg.payload as { stage: string; message: string; recoverable: boolean },
          })
          break
      }
    }

    return () => {
      chatWs.close()
      statusWs.close()
      chatWsRef.current = null
      statusWsRef.current = null
    }
  }, [sessionId, dispatch])

  const sendMessage = useCallback(
    (data: Record<string, unknown>) => {
      if (chatWsRef.current?.readyState === WebSocket.OPEN) {
        chatWsRef.current.send(JSON.stringify(data))
      }
    },
    []
  )

  return { sendMessage }
}
