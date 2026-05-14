import type { PipelineStage } from "../types/pipeline"

interface Props {
  stage: PipelineStage
  isLast: boolean
}

export function StageIndicator({ stage, isLast }: Props) {
  const dotClass = {
    pending: "bg-text-tertiary",
    active: "bg-accent animate-[pulse_1.5s_ease-in-out_infinite]",
    complete: "bg-success",
    error: "bg-critical",
  }[stage.status]

  return (
    <div className="flex items-start gap-3">
      <div className="flex flex-col items-center">
        <div className={`w-[10px] h-[10px] rounded-full shrink-0 ${dotClass}`} />
        {!isLast && <div className="w-px h-6 bg-border mt-1" />}
      </div>
      <div className="-mt-0.5">
        <span
          className={`text-[13px] font-medium ${
            stage.status === "active" ? "text-text-primary" : "text-text-secondary"
          }`}
        >
          {stage.name}
        </span>
        {stage.status === "active" && (
          <p className="text-[11px] text-text-tertiary mt-0.5">{stage.description}</p>
        )}
      </div>
    </div>
  )
}
