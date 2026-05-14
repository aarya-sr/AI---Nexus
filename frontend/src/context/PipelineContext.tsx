import { createContext, useContext, useReducer, useEffect, type Dispatch, type ReactNode } from "react"
import { initialState, pipelineReducer, type Action, type PipelineState } from "./pipelineReducer"

const STORAGE_KEY = "frankenstein_session"

function loadPersistedState(): PipelineState {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return initialState
    const saved = JSON.parse(raw)
    return {
      ...initialState,
      sessionId: saved.sessionId ?? null,
      messages: saved.messages ?? [],
      stages: saved.stages ?? initialState.stages,
      currentStage: saved.currentStage ?? "idle",
      hasStarted: saved.hasStarted ?? false,
      isWorking: false,
      isConnected: false,
      toastMessage: null,
    }
  } catch {
    return initialState
  }
}

function persistState(state: PipelineState) {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({
      sessionId: state.sessionId,
      messages: state.messages,
      stages: state.stages,
      currentStage: state.currentStage,
      hasStarted: state.hasStarted,
    }))
  } catch {
    // storage full or unavailable
  }
}

const PipelineStateContext = createContext<PipelineState>(initialState)
const PipelineDispatchContext = createContext<Dispatch<Action>>(() => {})

export function PipelineProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(pipelineReducer, undefined, loadPersistedState)

  useEffect(() => {
    persistState(state)
  }, [state])

  return (
    <PipelineStateContext.Provider value={state}>
      <PipelineDispatchContext.Provider value={dispatch}>
        {children}
      </PipelineDispatchContext.Provider>
    </PipelineStateContext.Provider>
  )
}

export function usePipelineState(): PipelineState {
  return useContext(PipelineStateContext)
}

export function usePipelineDispatch(): Dispatch<Action> {
  return useContext(PipelineDispatchContext)
}
