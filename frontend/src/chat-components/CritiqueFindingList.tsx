import { useState } from "react"
import type { Finding } from "../types/models"

interface Props {
  findings: Finding[]
}

const SEVERITY_STYLES: Record<Finding["severity"], { badge: string; text: string }> = {
  critical: { badge: "bg-red-500/20 text-red-400", text: "CRITICAL" },
  warning: { badge: "bg-amber-500/20 text-amber-400", text: "WARNING" },
  suggestion: { badge: "bg-green-500/20 text-green-400", text: "SUGGESTION" },
}

export function CritiqueFindingList({ findings }: Props) {
  // Auto-expand first critical finding
  const firstCriticalIdx = findings.findIndex((f) => f.severity === "critical")
  const [expanded, setExpanded] = useState<Set<number>>(
    () => new Set(firstCriticalIdx >= 0 ? [firstCriticalIdx] : [])
  )

  const prefersReducedMotion =
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches

  function toggle(idx: number) {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(idx)) {
        next.delete(idx)
      } else {
        next.add(idx)
      }
      return next
    })
  }

  return (
    <div className="space-y-2">
      <div className="text-[13px] font-semibold text-text-primary mb-2">
        Review Findings ({findings.length})
      </div>
      {findings.map((finding, i) => {
        const style = SEVERITY_STYLES[finding.severity]
        const isExpanded = expanded.has(i)

        return (
          <div
            key={i}
            className="bg-surface border border-border rounded-lg overflow-hidden"
          >
            <button
              onClick={() => toggle(i)}
              className="w-full flex items-start gap-3 px-4 py-3 text-left hover:bg-surface-elevated transition-colors min-h-[44px]"
            >
              <span
                className={`
                  inline-block text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded mt-0.5 shrink-0
                  ${style.badge}
                  ${!prefersReducedMotion ? "animate-[slideIn_200ms_ease-out]" : ""}
                `}
                style={!prefersReducedMotion ? { animationDelay: `${i * 30}ms` } : undefined}
              >
                {style.text}
              </span>
              <span className="text-[13px] text-text-secondary leading-[1.5] flex-1">
                {finding.description}
              </span>
              <span className="text-text-tertiary text-[12px] shrink-0 mt-0.5">
                {isExpanded ? "\u25B2" : "\u25BC"}
              </span>
            </button>

            {isExpanded && (
              <div className="px-4 pb-3 pt-0 border-t border-border">
                <div className="mt-3 space-y-2">
                  <div>
                    <span className="text-[11px] font-medium text-text-tertiary uppercase tracking-wider">
                      Location
                    </span>
                    <p className="text-[13px] text-text-secondary">{finding.location}</p>
                  </div>
                  <div>
                    <span className="text-[11px] font-medium text-text-tertiary uppercase tracking-wider">
                      Evidence
                    </span>
                    <p className="text-[13px] text-text-secondary">{finding.evidence}</p>
                  </div>
                  <div>
                    <span className="text-[11px] font-medium text-text-tertiary uppercase tracking-wider">
                      Suggested Fix
                    </span>
                    <p className="text-[13px] text-text-secondary">{finding.suggested_fix}</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
