interface LabLabelProps {
  text: string
  color?: string
  className?: string
}

export function LabLabel({ text, color, className = '' }: LabLabelProps) {
  return (
    <span
      className={`specimen-label ${className}`}
      style={color ? { color, borderColor: color?.startsWith('var(') ? 'rgba(139,0,0,0.2)' : `${color}33` } : undefined}
    >
      {text}
    </span>
  )
}
