import { createContext, useContext, useReducer, type Dispatch, type ReactNode } from "react"
import { initialState, pipelineReducer, type Action, type PipelineState } from "./pipelineReducer"

const PipelineStateContext = createContext<PipelineState>(initialState)
const PipelineDispatchContext = createContext<Dispatch<Action>>(() => {})

export function PipelineProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(pipelineReducer, initialState)

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
