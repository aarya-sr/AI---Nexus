import { useState, useCallback } from 'react'
import { motion } from 'framer-motion'

interface ElectricalLeverProps {
  onPull: () => void
}

export function ElectricalLever({ onPull }: ElectricalLeverProps) {
  const [pulled, setPulled] = useState(false)
  const [hovering, setHovering] = useState(false)

  const handlePull = useCallback(() => {
    if (pulled) return
    setPulled(true)
    setTimeout(onPull, 600)
  }, [pulled, onPull])

  return (
    <div
      className="lever-container clickable"
      onMouseEnter={() => setHovering(true)}
      onMouseLeave={() => setHovering(false)}
      onClick={handlePull}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && handlePull()}
      aria-label="Pull lever to activate"
    >
      <svg viewBox="0 0 280 340" width="140" height="170" overflow="visible">
        {/* Base plate — offset to center at x=140 */}
        <rect x="110" y="220" width="60" height="70" rx="4" fill="var(--copper)" opacity="0.3" />
        <rect x="115" y="225" width="50" height="60" rx="2" fill="none" stroke="var(--copper)" strokeWidth="1" opacity="0.5" />

        {/* Bolt holes */}
        <circle cx="122" cy="232" r="3" fill="var(--bg)" stroke="var(--copper)" strokeWidth="1" opacity="0.4" />
        <circle cx="158" cy="232" r="3" fill="var(--bg)" stroke="var(--copper)" strokeWidth="1" opacity="0.4" />
        <circle cx="122" cy="278" r="3" fill="var(--bg)" stroke="var(--copper)" strokeWidth="1" opacity="0.4" />
        <circle cx="158" cy="278" r="3" fill="var(--bg)" stroke="var(--copper)" strokeWidth="1" opacity="0.4" />

        {/* Slot */}
        <rect x="130" y="210" width="20" height="30" rx="2" fill="var(--bg)" stroke="var(--copper)" strokeWidth="1.5" />

        {/* Lever arm — framer-motion rotation */}
        <motion.g
          animate={{ rotate: pulled ? 60 : 0 }}
          transition={{ duration: 0.4, ease: 'easeInOut' }}
          style={{ originX: '140px', originY: '220px' }}
        >
          {/* Rod */}
          <rect x="135" y="60" width="10" height="170" rx="3" fill="var(--copper)" />
          {/* Handle ball */}
          <circle cx="140" cy="55" r="18" fill="var(--copper)" />
          <circle cx="140" cy="55" r="12" fill="var(--bg)" stroke="var(--amber)" strokeWidth="1.5" />

          {/* Amber glow on handle */}
          <motion.circle
            cx="140"
            cy="55"
            r="10"
            fill="var(--amber)"
            animate={{ opacity: hovering ? [0.2, 0.5, 0.2] : 0.1 }}
            transition={hovering ? { duration: 1.5, repeat: Infinity } : { duration: 0.3 }}
          />
        </motion.g>

        {/* Spark effects on hover */}
        {hovering && !pulled && (
          <g>
            <line x1="125" y1="205" x2="118" y2="192" stroke="var(--formaldehyde)" strokeWidth="1.5" opacity="0.6">
              <animate attributeName="opacity" values="0;1;0" dur="0.4s" repeatCount="indefinite" />
            </line>
            <line x1="140" y1="205" x2="143" y2="190" stroke="var(--formaldehyde)" strokeWidth="1" opacity="0.4">
              <animate attributeName="opacity" values="0;0.8;0" dur="0.5s" repeatCount="indefinite" begin="0.15s" />
            </line>
            <line x1="155" y1="205" x2="162" y2="193" stroke="var(--formaldehyde)" strokeWidth="1.5" opacity="0.6">
              <animate attributeName="opacity" values="0;1;0" dur="0.3s" repeatCount="indefinite" begin="0.3s" />
            </line>
          </g>
        )}

        {/* Surge effect when pulled */}
        {pulled && (
          <motion.rect
            x="0"
            y="0"
            width="280"
            height="340"
            fill="var(--formaldehyde)"
            initial={{ opacity: 0 }}
            animate={{ opacity: [0, 0.3, 0] }}
            transition={{ duration: 0.6 }}
          />
        )}

        {/* Label */}
        <text x="140" y="320" textAnchor="middle" fill="var(--copper)" fontSize="8" fontFamily="var(--font-mono)" letterSpacing="0.1em" opacity="0.5">
          {pulled ? 'ACTIVATED' : 'PULL TO ACTIVATE'}
        </text>
      </svg>

      <style>{`
        .lever-container {
          display: flex;
          flex-direction: column;
          align-items: center;
          user-select: none;
          outline: none;
        }
        .lever-container:focus-visible {
          outline: 2px solid var(--formaldehyde);
          outline-offset: 8px;
          border-radius: 4px;
        }
      `}</style>
    </div>
  )
}
