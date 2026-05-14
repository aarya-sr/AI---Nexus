interface Props {
  label: string
}

export function PhaseDivider({ label }: Props) {
  return (
    <div className="flex items-center gap-4 my-8 animate-[fadeIn_400ms_ease-out]">
      <div className="flex-1 h-px bg-border" />
      <span className="text-[11px] font-medium uppercase tracking-[0.05em] text-text-tertiary">
        {label}
      </span>
      <div className="flex-1 h-px bg-border" />
    </div>
  )
}
