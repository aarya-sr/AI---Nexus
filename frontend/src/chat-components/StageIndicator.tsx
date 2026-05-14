import type { PipelineStage } from "../types/pipeline"

interface Props {
  stage: PipelineStage
  isLast: boolean
}

function CheckIcon() {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 12 12"
      fill="none"
      className="animate-[checkmarkPop_50ms_ease-out]"
    >
      <path
        d="M2.5 6L5 8.5L9.5 4"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export function StageIndicator({ stage, isLast }: Props) {
  const isComplete = stage.status === "complete"

  const dotClass = {
    pending: "bg-[#404040]",
    active: "bg-accent animate-[pulse_1.5s_ease-in-out_infinite]",
    complete: "bg-green-500 text-white",
    error: "bg-critical",
  }[stage.status]

  const lineClass = isComplete ? "bg-green-500/50" : "bg-border"

  const nameClass = {
    pending: "text-text-tertiary",
    active: "text-text-primary",
    complete: "text-green-400",
    error: "text-critical",
  }[stage.status]

  return (
    <div className="flex items-start gap-3">
      <div className="flex flex-col items-center">
        <div
          className={`w-[20px] h-[20px] rounded-full shrink-0 flex items-center justify-center transition-colors duration-300 ${dotClass}`}
        >
          {isComplete && <CheckIcon />}
        </div>
        {!isLast && <div className={`w-px h-6 mt-1 transition-colors duration-300 ${lineClass}`} />}
      </div>
      <div className="-mt-0.5">
        <span className={`text-[13px] font-medium transition-colors duration-300 ${nameClass}`}>
          {stage.name}
        </span>
        {stage.status === "active" && (
          <p className="text-[11px] text-text-tertiary mt-0.5">{stage.description}</p>
        )}
      </div>
    </div>
  )
}
