import { usePipelineState } from "../context/PipelineContext"
import { StageIndicator } from "./StageIndicator"

export function PipelineSidebar() {
  const { stages, hasStarted, isConnected } = usePipelineState()

  if (!hasStarted) return null

  return (
    <aside className="border-l border-border p-5 animate-[slideInRight_300ms_ease-out] hidden min-[1024px]:block sticky top-0 h-screen overflow-y-auto">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-[11px] font-medium uppercase tracking-[0.05em] text-text-tertiary">
          Pipeline
        </h2>
        <div className="flex items-center gap-1.5">
          <div className={`w-1.5 h-1.5 rounded-full ${isConnected ? "bg-green-500" : "bg-red-500"}`} />
          <span className="text-[10px] text-text-tertiary">
            {isConnected ? "Connected" : "Disconnected"}
          </span>
        </div>
      </div>
      <div className="flex flex-col">
        {stages.map((stage, i) => (
          <StageIndicator key={stage.id} stage={stage} isLast={i === stages.length - 1} />
        ))}
      </div>
    </aside>
  )
}
