import { useRef } from 'react'
import { motion, useScroll, useTransform } from 'framer-motion'

const OLD_STEPS = [
  { label: 'Read 47 blog posts about agents', time: 'Day 1-3' },
  { label: 'Argue about frameworks in Slack', time: 'Day 4-7' },
  { label: 'Prototype something that "almost works"', time: 'Week 2-3' },
  { label: 'Debug hallucinations at 2am', time: 'Week 3-4' },
  { label: 'Rewrite from scratch (again)', time: 'Week 5-6' },
  { label: 'Deploy to staging. Pray.', time: 'Week 7+' },
]

const NEW_STEPS = [
  { label: 'Describe what you actually want', time: '0:00' },
  { label: 'Elicitor asks the smart questions', time: '0:04' },
  { label: 'Architect does architecture', time: '0:10' },
  { label: 'Critic tears it apart (constructively)', time: '0:15' },
  { label: 'Builder compiles actual code', time: '0:22' },
  { label: 'Go touch grass', time: '0:28' },
]

export function NecropsisBench() {
  const ref = useRef<HTMLElement>(null)
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ['start end', 'center center'],
  })

  const oldPathLength = useTransform(scrollYProgress, [0.1, 0.6], [0, 1])
  const newPathLength = useTransform(scrollYProgress, [0.4, 0.8], [0, 1])
  const resultOpacity = useTransform(scrollYProgress, [0.75, 0.9], [0, 1])

  return (
    <section ref={ref} className="necropsis-section">
      <div className="necropsis-header">
        <h2>The Autopsy of the Old Way</h2>
        <p className="lab-label">Before vs. After</p>
      </div>

      <div className="necropsis-grid">
        {/* Without */}
        <div className="necropsis-col necropsis-col--old">
          <h3 className="necropsis-col-title necropsis-col-title--old">WITHOUT FRANKENSTEIN</h3>
          <div className="timeline">
            <svg className="timeline-line" viewBox="0 0 4 300" preserveAspectRatio="none">
              <motion.line
                x1="2" y1="0" x2="2" y2="300"
                stroke="var(--crimson)"
                strokeWidth="2"
                strokeDasharray="6 4"
                style={{ pathLength: oldPathLength }}
              />
            </svg>
            {OLD_STEPS.map((step, i) => (
              <motion.div
                key={i}
                className="timeline-step timeline-step--old"
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.15, duration: 0.4 }}
                viewport={{ once: true }}
              >
                <span className="step-time step-time--old">{step.time}</span>
                <span className="step-label">{step.label}</span>
              </motion.div>
            ))}
          </div>
        </div>

        {/* With */}
        <div className="necropsis-col necropsis-col--new">
          <h3 className="necropsis-col-title necropsis-col-title--new">WITH FRANKENSTEIN</h3>
          <div className="timeline">
            <svg className="timeline-line" viewBox="0 0 4 300" preserveAspectRatio="none">
              <motion.line
                x1="2" y1="0" x2="2" y2="300"
                stroke="var(--formaldehyde)"
                strokeWidth="2"
                style={{ pathLength: newPathLength }}
              />
            </svg>
            {NEW_STEPS.map((step, i) => (
              <motion.div
                key={i}
                className="timeline-step timeline-step--new"
                initial={{ opacity: 0, x: 20 }}
                whileInView={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.4 + i * 0.1, duration: 0.3 }}
                viewport={{ once: true }}
              >
                <span className="step-time step-time--new">{step.time}</span>
                <span className="step-label">{step.label}</span>
              </motion.div>
            ))}
          </div>
          <motion.div className="elapsed-badge" style={{ opacity: resultOpacity }}>
            ELAPSED: 0:28
          </motion.div>
        </div>
      </div>

      <style>{`
        .necropsis-section {
          min-height: 80vh;
          padding: var(--section-pad) clamp(1rem, 5vw, 4rem);
        }
        .necropsis-header {
          text-align: center;
          margin-bottom: 3rem;
        }
        .necropsis-header h2 {
          margin-bottom: 0.5rem;
        }
        .necropsis-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 3rem;
          max-width: 800px;
          margin: 0 auto;
        }
        .necropsis-col {
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
        }
        .necropsis-col-title {
          font-family: var(--font-mono);
          font-size: 0.7rem;
          letter-spacing: 0.15em;
          text-align: center;
          padding-bottom: 0.5rem;
          border-bottom: 1px solid var(--copper-dim);
        }
        .necropsis-col-title--old { color: var(--crimson); }
        .necropsis-col-title--new { color: var(--formaldehyde); }
        .timeline {
          position: relative;
          display: flex;
          flex-direction: column;
          gap: 1rem;
          padding-left: 1.5rem;
        }
        .timeline-line {
          position: absolute;
          left: 4px;
          top: 0;
          width: 4px;
          height: 100%;
        }
        .timeline-step {
          display: flex;
          flex-direction: column;
          gap: 0.15rem;
        }
        .step-time {
          font-family: var(--font-mono);
          font-size: 0.6rem;
          letter-spacing: 0.1em;
        }
        .step-time--old { color: var(--crimson); opacity: 0.7; }
        .step-time--new { color: var(--formaldehyde); opacity: 0.7; }
        .step-label {
          font-family: var(--font-body);
          font-size: 0.9rem;
          color: var(--bone-dim);
        }
        .elapsed-badge {
          text-align: center;
          font-family: var(--font-mono);
          font-size: 0.8rem;
          color: var(--formaldehyde);
          letter-spacing: 0.1em;
          padding: 0.5rem;
          border: 1px solid var(--formaldehyde-dim);
          text-shadow: 0 0 10px var(--formaldehyde-glow);
        }
        @media (max-width: 600px) {
          .necropsis-grid {
            grid-template-columns: 1fr;
            gap: 2rem;
          }
        }
      `}</style>
    </section>
  )
}
