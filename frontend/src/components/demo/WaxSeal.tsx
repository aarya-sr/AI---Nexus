import { useState, useRef, useCallback } from 'react'
import { motion, useInView } from 'framer-motion'

export function WaxSeal() {
  const ref = useRef<HTMLDivElement>(null)
  const isInView = useInView(ref, { once: true, margin: '-50px' })
  const [stamped, setStamped] = useState(false)

  const handleStamp = useCallback(() => {
    if (stamped) return
    setStamped(true)
  }, [stamped])

  return (
    <div ref={ref} className="wax-seal-section">
      {!stamped ? (
        <>
          <motion.p
            className="seal-prompt"
            initial={{ opacity: 0 }}
            animate={isInView ? { opacity: 1 } : {}}
            transition={{ delay: 1 }}
          >
            Human checkpoint required.
          </motion.p>

          <motion.button
            className="stamp-button"
            onClick={handleStamp}
            initial={{ opacity: 0, y: 10 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ delay: 1.3 }}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <svg viewBox="0 0 120 50" width="120" height="50">
              <rect x="5" y="5" width="110" height="40" rx="4"
                fill="#6b4423" stroke="#8b5a33" strokeWidth="1.5" />
              <text x="60" y="30" textAnchor="middle" fill="#f5f0e8" fontSize="11"
                fontFamily="'IBM Plex Mono', monospace" letterSpacing="0.12em">
                APPROVE
              </text>
            </svg>
          </motion.button>
        </>
      ) : (
        <motion.div
          className="wax-impression"
          initial={{ scale: 1.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: 'spring', stiffness: 500, damping: 18 }}
        >
          <svg viewBox="0 0 140 140" width="130" height="130">
            {/* Wax splatter */}
            <path
              d="M 70 10 C 90 6, 115 18, 125 38 C 135 58, 132 72, 130 85
                 C 125 105, 105 125, 70 128 C 40 130, 18 112, 12 85
                 C 6 62, 10 42, 18 28 C 28 12, 50 6, 70 10 Z"
              fill="#8b0000"
            />
            <circle cx="130" cy="55" r="5" fill="#8b0000" opacity="0.7" />
            <circle cx="15" cy="70" r="4" fill="#8b0000" opacity="0.6" />
            <circle cx="70" cy="70" r="40" fill="none" stroke="#a01010" strokeWidth="2.5" opacity="0.5" />
            <text x="70" y="64" textAnchor="middle" fill="#f5f0e8" fontSize="14"
              fontFamily="'IBM Plex Mono', monospace" letterSpacing="0.12em" fontWeight="700">
              APPROVED
            </text>
            <line x1="38" y1="73" x2="102" y2="73" stroke="#f5f0e8" strokeWidth="0.8" opacity="0.3" />
            <text x="70" y="88" textAnchor="middle" fill="#f5f0e8" fontSize="8"
              fontFamily="'IBM Plex Mono', monospace" letterSpacing="0.1em" opacity="0.5">
              CHECKPOINT
            </text>
          </svg>

          {/* Impact ring */}
          <motion.div
            className="stamp-ring"
            initial={{ scale: 0.5, opacity: 0.6 }}
            animate={{ scale: 2.5, opacity: 0 }}
            transition={{ duration: 0.6 }}
          />

          <motion.p
            className="seal-status"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
          >
            Specification approved. Proceeding to Builder.
          </motion.p>
        </motion.div>
      )}

      <style>{`
        .wax-seal-section {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 0.75rem;
          padding: 1.5rem 0 0.5rem;
        }
        .seal-prompt {
          font-family: var(--font-mono);
          font-size: 0.7rem;
          letter-spacing: 0.1em;
          color: #8b0000;
          text-transform: uppercase;
        }
        .stamp-button {
          background: none;
          border: none;
          padding: 0;
          cursor: pointer;
          filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2));
        }
        .stamp-button:hover {
          filter: drop-shadow(0 3px 8px rgba(0,0,0,0.3));
        }
        .wax-impression {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 0.5rem;
          position: relative;
          filter: drop-shadow(0 4px 12px rgba(139,0,0,0.4));
        }
        .stamp-ring {
          position: absolute;
          top: 50%;
          left: 50%;
          width: 50px;
          height: 50px;
          margin: -25px 0 0 -25px;
          border-radius: 50%;
          border: 2px solid rgba(139,0,0,0.3);
          pointer-events: none;
        }
        .seal-status {
          font-family: var(--font-mono);
          font-size: 0.65rem;
          letter-spacing: 0.08em;
          color: #4a7a3a;
        }
      `}</style>
    </div>
  )
}
