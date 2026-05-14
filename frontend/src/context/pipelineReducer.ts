import type { ChatEntry, PipelineStage } from "../types/pipeline"
import { PIPELINE_STAGES } from "../types/pipeline"

export interface PipelineState {
  sessionId: string | null
  messages: ChatEntry[]
  stages: PipelineStage[]
  currentStage: string
  isWorking: boolean
  isConnected: boolean
  hasStarted: boolean
  toastMessage: string | null
}

export const initialState: PipelineState = {
  sessionId: null,
  messages: [],
  stages: PIPELINE_STAGES.map((s) => ({ ...s })),
  currentStage: "idle",
  isWorking: false,
  isConnected: false,
  hasStarted: false,
  toastMessage: null,
}

export type Action =
  | { type: "SET_SESSION"; payload: string }
  | { type: "CHAT_MESSAGE"; payload: ChatEntry }
  | { type: "STAGE_UPDATE"; payload: { stage: string; description: string } }
  | { type: "PROGRESS"; payload: { stage: string; percent: number; detail: string } }
  | { type: "COMPLETE"; payload: { session_id: string; framework: string; download_url: string; summary: string } }
  | { type: "ERROR"; payload: { stage: string; message: string; recoverable: boolean } }
  | { type: "SET_CONNECTED"; payload: boolean }
  | { type: "SET_WORKING"; payload: boolean }
  | { type: "SET_STARTED" }
  | { type: "SHOW_TOAST"; payload: string }
  | { type: "DISMISS_TOAST" }
  | { type: "RESET" }

export function pipelineReducer(state: PipelineState, action: Action): PipelineState {
  switch (action.type) {
    case "SET_SESSION":
      return { ...state, sessionId: action.payload }

    case "CHAT_MESSAGE":
      return { ...state, messages: [...state.messages, action.payload] }

    case "STAGE_UPDATE": {
      const { stage } = action.payload
      const stages = state.stages.map((s) => {
        if (s.id === stage) return { ...s, status: "active" as const, description: action.payload.description }
        if (s.status === "active" && s.id !== stage) return { ...s, status: "complete" as const }
        return s
      })
      return { ...state, stages, currentStage: stage, isWorking: true }
    }

    case "PROGRESS": {
      const { stage, percent, detail } = action.payload
      const stages = state.stages.map((s) =>
        s.id === stage ? { ...s, description: `${detail} (${Math.round(percent)}%)` } : s
      )
      return { ...state, stages }
    }

    case "COMPLETE": {
      const stages = state.stages.map((s) => ({ ...s, status: "complete" as const }))
      return {
        ...state,
        stages,
        isWorking: false,
        messages: [
          ...state.messages,
          {
            id: `complete-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
            variant: "system",
            type: "status.complete",
            payload: action.payload,
            timestamp: new Date().toISOString(),
          },
        ],
      }
    }

    case "ERROR":
      return {
        ...state,
        isWorking: false,
        stages: state.stages.map((s) =>
          s.id === action.payload.stage ? { ...s, status: "error" as const } : s
        ),
        messages: [
          ...state.messages,
          {
            id: `error-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
            variant: "system",
            type: "error",
            payload: action.payload,
            timestamp: new Date().toISOString(),
          },
        ],
      }

    case "SET_CONNECTED":
      return { ...state, isConnected: action.payload }

    case "SET_WORKING":
      return { ...state, isWorking: action.payload }

    case "SET_STARTED":
      return { ...state, hasStarted: true }

    case "SHOW_TOAST":
      return { ...state, toastMessage: action.payload }

    case "DISMISS_TOAST":
      return { ...state, toastMessage: null }

    case "RESET":
      return { ...initialState, stages: PIPELINE_STAGES.map((s) => ({ ...s })) }

    default:
      return state
  }
}
