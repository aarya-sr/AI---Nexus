import { usePipelineState } from "../context/PipelineContext"
import { StageIndicator } from "./StageIndicator"

export function PipelineSidebar() {
  const { stages, hasStarted } = usePipelineState()

  if (!hasStarted) return null

  return (
    <aside className="w-60 shrink-0 border-l border-border p-5 animate-[slideInRight_300ms_ease-out] hidden min-[1024px]:block">
      <h2 className="text-[11px] font-medium uppercase tracking-[0.05em] text-text-tertiary mb-4">
        Pipeline
      </h2>
      <div className="flex flex-col">
        {stages.map((stage, i) => (
          <StageIndicator key={stage.id} stage={stage} isLast={i === stages.length - 1} />
        ))}
      </div>
    </aside>
  )
}
