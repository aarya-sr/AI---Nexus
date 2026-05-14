import { useRef } from 'react'

const QUIPS = [
  { label: 'LLMs ARGUING', value: '6' },
  { label: 'COFFEE STATUS', value: 'CRITICAL' },
  { label: 'SPEC REJECTIONS', value: '~3/RUN' },
  { label: 'SENTIENCE RISK', value: 'PROBABLY FINE' },
]

export function VoltageCounter() {
  const ref = useRef<HTMLDivElement>(null)

  return (
    <div ref={ref} className="voltage-strip">
      <div className="voltage-inner">
        {QUIPS.map((q, i) => (
          <div key={i} className="voltage-metric">
            <span className="voltage-value">{q.value}</span>
            <span className="voltage-label">{q.label}</span>
          </div>
        ))}
      </div>
      <div className="voltage-scanline" />

      <style>{`
        .voltage-strip {
          position: sticky;
          top: 0;
          z-index: 50;
          background: rgba(10, 13, 8, 0.95);
          border-top: 1px solid var(--copper-dim);
          border-bottom: 1px solid var(--copper-dim);
          overflow: hidden;
        }
        .voltage-inner {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 2rem;
          padding: 0.75rem 1rem;
          max-width: 900px;
          margin: 0 auto;
          flex-wrap: wrap;
        }
        .voltage-metric {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 0.15rem;
        }
        .voltage-value {
          font-family: var(--font-mono);
          font-size: 1.1rem;
          color: var(--formaldehyde);
          text-shadow: 0 0 8px var(--formaldehyde-glow);
          letter-spacing: 0.05em;
        }
        .voltage-label {
          font-family: var(--font-mono);
          font-size: 0.5rem;
          letter-spacing: 0.15em;
          color: var(--bone-dim);
          text-transform: uppercase;
        }
        .voltage-scanline {
          position: absolute;
          inset: 0;
          background: repeating-linear-gradient(
            0deg,
            transparent,
            transparent 2px,
            rgba(57, 255, 20, 0.02) 2px,
            rgba(57, 255, 20, 0.02) 4px
          );
          pointer-events: none;
        }
        @media (max-width: 600px) {
          .voltage-inner {
            gap: 1rem;
          }
          .voltage-value {
            font-size: 0.9rem;
          }
        }
      `}</style>
    </div>
  )
}
