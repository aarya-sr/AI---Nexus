import { useRef, useEffect, useState } from 'react'
import { useInView } from 'framer-motion'

const LOG_ENTRIES = [
  { time: '13:42:07', agent: 'elicitor', msg: 'extracting domain knowledge... politely' },
  { time: '13:42:09', agent: 'architect', msg: 'spec generated: 5 agents, 0 regrets' },
  { time: '13:42:11', agent: 'critic', msg: '3 issues found. "ambitious" architecture detected' },
  { time: '13:42:14', agent: 'architect', msg: 'fine. revised.' },
  { time: '13:42:16', agent: 'critic', msg: 'approved. reluctantly.' },
  { time: '13:42:18', agent: 'builder', msg: 'compiling pipeline... hold my tokens' },
  { time: '13:42:22', agent: 'builder', msg: 'code generation complete. it compiles. do not ask more' },
  { time: '13:42:24', agent: 'tester', msg: 'sandbox initialized. nothing on fire yet' },
  { time: '13:42:26', agent: 'tester', msg: 'all tests passing. suspicious but proceeding' },
  { time: '13:42:27', agent: 'learner', msg: 'outcome stored. will remember this.' },
  { time: '13:42:27', agent: 'SYSTEM', msg: 'PIPELINE COMPLETE. YOU ARE WELCOME.' },
]

function getAgentColor(agent: string): string {
  switch (agent) {
    case 'critic': return 'var(--crimson)'
    case 'SYSTEM': return 'var(--amber)'
    default: return 'var(--formaldehyde)'
  }
}

export function TransmissionLog() {
  const ref = useRef<HTMLDivElement>(null)
  const isInView = useInView(ref, { once: false, margin: '-100px' })
  const [visibleLines, setVisibleLines] = useState(0)

  useEffect(() => {
    if (!isInView) {
      setVisibleLines(0)
      return
    }
    let i = 0
    const interval = setInterval(() => {
      i++
      if (i > LOG_ENTRIES.length) {
        // Reset after pause
        setTimeout(() => setVisibleLines(0), 2000)
        clearInterval(interval)
        return
      }
      setVisibleLines(i)
    }, 350)
    return () => clearInterval(interval)
  }, [isInView])

  return (
    <div ref={ref} className="transmission-log">
      <div className="log-header">
        <span className="log-dot" />
        <span className="log-title">TRANSMISSION LOG</span>
      </div>
      <div className="log-body">
        {LOG_ENTRIES.slice(0, visibleLines).map((entry, i) => (
          <div key={i} className="log-line">
            <span className="log-time">[{entry.time}]</span>
            <span className="log-agent" style={{ color: getAgentColor(entry.agent) }}>
              {entry.agent}
            </span>
            <span className="log-sep">&mdash;</span>
            <span className="log-msg">{entry.msg}</span>
          </div>
        ))}
        {visibleLines < LOG_ENTRIES.length && (
          <span className="log-cursor">_</span>
        )}
      </div>

      <style>{`
        .transmission-log {
          background: rgba(0, 0, 0, 0.85);
          border: 1px solid var(--copper-dim);
          border-radius: 2px;
          font-family: var(--font-mono);
          font-size: 0.7rem;
          overflow: hidden;
          margin-top: 1.5rem;
        }
        .log-header {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.4rem 0.8rem;
          background: rgba(184, 115, 51, 0.1);
          border-bottom: 1px solid var(--copper-dim);
        }
        .log-dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: var(--formaldehyde);
          box-shadow: 0 0 6px var(--formaldehyde-glow);
          animation: log-blink 1s infinite;
        }
        @keyframes log-blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
        .log-title {
          color: var(--copper);
          letter-spacing: 0.1em;
          font-size: 0.55rem;
        }
        .log-body {
          padding: 0.6rem 0.8rem;
          min-height: 120px;
          max-height: 200px;
          overflow-y: auto;
        }
        .log-line {
          display: flex;
          gap: 0.4rem;
          line-height: 1.8;
          white-space: nowrap;
        }
        .log-time {
          color: var(--bone-dim);
          opacity: 0.5;
        }
        .log-agent {
          min-width: 60px;
        }
        .log-sep {
          color: var(--copper-dim);
        }
        .log-msg {
          color: var(--bone-dim);
        }
        .log-cursor {
          color: var(--formaldehyde);
          animation: log-blink 0.7s infinite;
        }
      `}</style>
    </div>
  )
}
