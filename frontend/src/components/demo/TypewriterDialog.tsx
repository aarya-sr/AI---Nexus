import { useState, useEffect, useRef } from 'react'
import { motion, useInView } from 'framer-motion'

interface DialogLine {
  speaker: 'elicitor' | 'human'
  text: string
}

const DIALOG: DialogLine[] = [
  { speaker: 'elicitor', text: 'What is the primary goal of this agent?' },
  { speaker: 'human', text: 'Evaluate loan applications by analyzing applicant documents and generating a risk assessment report.' },
  { speaker: 'elicitor', text: 'What data sources does it need to access?' },
  { speaker: 'human', text: 'PDF application forms, credit bureau API, internal customer database.' },
  { speaker: 'elicitor', text: 'What are the critical constraints or compliance requirements?' },
  { speaker: 'human', text: 'Must follow FCRA guidelines. No automated final decisions — human underwriter reviews.' },
  { speaker: 'elicitor', text: 'What does a successful output look like?' },
  { speaker: 'human', text: 'A structured risk report with score, rationale, flagged concerns, and recommended action.' },
]

export function TypewriterDialog() {
  const ref = useRef<HTMLDivElement>(null)
  const isInView = useInView(ref, { once: true, margin: '-100px' })
  const [visibleLines, setVisibleLines] = useState(0)
  const [currentText, setCurrentText] = useState('')

  useEffect(() => {
    if (!isInView) return
    if (visibleLines >= DIALOG.length) return

    const line = DIALOG[visibleLines]
    let charIndex = 0

    const typeInterval = setInterval(() => {
      if (charIndex <= line.text.length) {
        setCurrentText(line.text.slice(0, charIndex))
        charIndex++
      } else {
        clearInterval(typeInterval)
        setTimeout(() => {
          setVisibleLines((v) => v + 1)
          setCurrentText('')
        }, 400)
      }
    }, line.speaker === 'elicitor' ? 30 : 20)

    return () => clearInterval(typeInterval)
  }, [isInView, visibleLines])

  return (
    <div ref={ref} className="dialog-container">
      {DIALOG.slice(0, visibleLines).map((line, i) => (
        <motion.div
          key={i}
          className={`dialog-line dialog-line--${line.speaker}`}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          <span className="dialog-speaker">
            {line.speaker === 'elicitor' ? 'ELICITOR:' : 'HUMAN:'}
          </span>
          <span className="dialog-text">{line.text}</span>
        </motion.div>
      ))}

      {/* Currently typing line */}
      {visibleLines < DIALOG.length && currentText && (
        <div className={`dialog-line dialog-line--${DIALOG[visibleLines].speaker}`}>
          <span className="dialog-speaker">
            {DIALOG[visibleLines].speaker === 'elicitor' ? 'ELICITOR:' : 'HUMAN:'}
          </span>
          <span className="dialog-text">
            {currentText}
            <span className="dialog-cursor">|</span>
          </span>
        </div>
      )}

      <style>{`
        .dialog-container {
          display: flex;
          flex-direction: column;
          gap: 1rem;
          font-family: var(--font-display);
          font-size: 0.95rem;
          line-height: 1.6;
        }
        .dialog-line {
          display: flex;
          gap: 0.75rem;
        }
        .dialog-speaker {
          font-family: var(--font-mono);
          font-size: 0.7rem;
          letter-spacing: 0.1em;
          flex-shrink: 0;
          padding-top: 0.15em;
          min-width: 7em;
        }
        .dialog-line--elicitor .dialog-speaker {
          color: #1a6b1a;
        }
        .dialog-line--human .dialog-speaker {
          color: #8b5e20;
        }
        .dialog-line--elicitor .dialog-text {
          color: #2a2520;
        }
        .dialog-line--human .dialog-text {
          color: #5a4020;
        }
        .dialog-cursor {
          color: #1a6b1a;
          animation: blink 0.8s step-end infinite;
        }
        @keyframes blink {
          50% { opacity: 0; }
        }
      `}</style>
    </div>
  )
}
