import { useRef } from 'react'
import { motion, useScroll, useTransform } from 'framer-motion'

interface SectionDividerProps {
  label: string
}

export function SectionDivider({ label }: SectionDividerProps) {
  const ref = useRef<HTMLDivElement>(null)
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ['start end', 'end start'],
  })

  const pathLength = useTransform(scrollYProgress, [0.2, 0.5], [0, 1])
  const labelOpacity = useTransform(scrollYProgress, [0.35, 0.5], [0, 1])

  return (
    <div ref={ref} className="section-divider">
      <svg viewBox="0 0 800 40" preserveAspectRatio="xMidYMid meet" className="divider-svg">
        <motion.line
          x1="40" y1="20" x2="340" y2="20"
          stroke="var(--copper-dim)"
          strokeWidth="1"
          style={{ pathLength }}
        />
        <motion.line
          x1="460" y1="20" x2="760" y2="20"
          stroke="var(--copper-dim)"
          strokeWidth="1"
          style={{ pathLength }}
        />
      </svg>
      <motion.span className="divider-label" style={{ opacity: labelOpacity }}>
        {label}
      </motion.span>

      <style>{`
        .section-divider {
          position: relative;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 2rem 0;
          overflow: hidden;
        }
        .divider-svg {
          position: absolute;
          width: 100%;
          max-width: 800px;
          height: 40px;
        }
        .divider-label {
          position: relative;
          z-index: 1;
          font-family: var(--font-mono);
          font-size: 0.6rem;
          letter-spacing: 0.25em;
          color: var(--copper);
          text-transform: uppercase;
          background: var(--bg);
          padding: 0 1.5rem;
        }
      `}</style>
    </div>
  )
}
