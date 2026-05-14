import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useLabStore } from '../../store/labState'

export function AssemblyAnimation() {
  const assemblyPhase = useLabStore((s) => s.assemblyPhase)
  const flashRef = useRef<HTMLDivElement>(null)
  const [showBornText, setShowBornText] = useState(false)

  // Lightning flash — invert page one frame
  useEffect(() => {
    if (assemblyPhase === 'lightning' && flashRef.current) {
      flashRef.current.style.opacity = '1'
      setTimeout(() => {
        if (flashRef.current) flashRef.current.style.opacity = '0'
      }, 80)
    }
  }, [assemblyPhase])

  // Born text — show on alive, auto-fade after 4s
  useEffect(() => {
    if (assemblyPhase === 'alive') {
      setShowBornText(true)
      const timer = setTimeout(() => setShowBornText(false), 4000)
      return () => clearTimeout(timer)
    } else {
      setShowBornText(false)
    }
  }, [assemblyPhase])

  return (
    <>
      {/* Lightning flash overlay */}
      <div
        ref={flashRef}
        style={{
          position: 'fixed',
          inset: 0,
          background: '#fff',
          opacity: 0,
          pointerEvents: 'none',
          zIndex: 100,
          transition: 'opacity 0.08s ease-out',
          mixBlendMode: 'difference',
        }}
      />

      {/* Stitching SVG overlay */}
      <AnimatePresence>
        {assemblyPhase === 'stitching' && (
          <motion.svg
            className="stitch-overlay"
            viewBox="0 0 400 400"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              width: '300px',
              height: '300px',
              zIndex: 10,
              pointerEvents: 'none',
            }}
          >
            {/* Stitching paths — needle and thread */}
            {[0, 1, 2, 3, 4].map((i) => (
              <motion.path
                key={i}
                d={`M ${80 + i * 60} ${100 + Math.sin(i) * 40}
                    Q ${100 + i * 50} ${200} ${120 + i * 40} ${300 - Math.cos(i) * 30}`}
                stroke="var(--formaldehyde)"
                strokeWidth="1.5"
                fill="none"
                strokeDasharray="8 4"
                initial={{ pathLength: 0, opacity: 0 }}
                animate={{
                  pathLength: 1,
                  opacity: [0, 1, 1, 0.6],
                }}
                transition={{
                  duration: 1.5,
                  delay: i * 0.2,
                  ease: 'easeInOut',
                }}
                style={{
                  filter: 'drop-shadow(0 0 4px rgba(57,255,20,0.5))',
                }}
              />
            ))}

            {/* Cross-stitches */}
            {[0, 1, 2, 3].map((i) => (
              <motion.g key={`cross-${i}`}>
                <motion.line
                  x1={120 + i * 50}
                  y1={160 + i * 20}
                  x2={135 + i * 50}
                  y2={175 + i * 20}
                  stroke="var(--copper)"
                  strokeWidth="1"
                  initial={{ pathLength: 0 }}
                  animate={{ pathLength: 1 }}
                  transition={{ duration: 0.3, delay: 0.8 + i * 0.15 }}
                />
                <motion.line
                  x1={135 + i * 50}
                  y1={160 + i * 20}
                  x2={120 + i * 50}
                  y2={175 + i * 20}
                  stroke="var(--copper)"
                  strokeWidth="1"
                  initial={{ pathLength: 0 }}
                  animate={{ pathLength: 1 }}
                  transition={{ duration: 0.3, delay: 0.9 + i * 0.15 }}
                />
              </motion.g>
            ))}
          </motion.svg>
        )}
      </AnimatePresence>

      {/* "YOUR AGENT IS BEING BORN" text */}
      <AnimatePresence>
        {showBornText && (
          <motion.div
            className="born-text"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1, delay: 0.5 }}
            style={{
              position: 'absolute',
              bottom: '15%',
              left: '50%',
              transform: 'translateX(-50%)',
              zIndex: 10,
              textAlign: 'center',
            }}
          >
            <p
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: 'clamp(0.8rem, 2vw, 1.2rem)',
                color: 'var(--formaldehyde)',
                letterSpacing: '0.15em',
                textTransform: 'uppercase',
                textShadow: '0 0 20px var(--formaldehyde-glow)',
              }}
            >
              Your agent is being born.
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
