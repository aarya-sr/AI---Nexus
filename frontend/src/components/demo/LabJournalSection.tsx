import { useRef, useState } from 'react'
import { motion, useScroll, useTransform, useInView } from 'framer-motion'
import { TypewriterDialog } from './TypewriterDialog'
import { AgentDiagram } from './AgentDiagram'
import { WaxSeal } from './WaxSeal'
import { TransmissionLog } from '../shared/TransmissionLog'

export function LabJournalSection() {
  const sectionRef = useRef<HTMLElement>(null)
  const isInView = useInView(sectionRef, { once: true, margin: '-150px' })
  const [leftPageReady, setLeftPageReady] = useState(false)
  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ['start end', 'end start'],
  })

  // Header animations
  const titleClip = useTransform(scrollYProgress, [0.05, 0.18], [100, 0])
  const subtitleOpacity = useTransform(scrollYProgress, [0.12, 0.22], [0, 1])
  const coffeeOpacity = useTransform(scrollYProgress, [0.35, 0.5], [0, 1])

  return (
    <section ref={sectionRef} className="journal-section" data-section="journal">
      <div className="journal-header">
        <motion.h2 style={{ clipPath: useTransform(titleClip, (v) => `inset(0 ${v}% 0 0)`) }}>
          The Lab Journal
        </motion.h2>
        <motion.p className="lab-label" style={{ opacity: subtitleOpacity }}>
          Experiment Log — Live Session
        </motion.p>
      </div>

      <div className="journal-spread">
        {/* Left page — Elicitor Q&A */}
        <motion.div
          className="journal-page journal-page--left"
          initial={{ opacity: 0, x: -60, rotate: -2 }}
          animate={isInView ? { opacity: 1, x: 0, rotate: 0 } : {}}
          transition={{ duration: 0.7, ease: 'easeOut' }}
          onAnimationComplete={() => setLeftPageReady(true)}
        >
          <div className="page-header">
            <span className="page-number">pg. 47</span>
            <h3>Elicitor Session</h3>
            <span className="page-date">Experiment #F-031</span>
          </div>
          {leftPageReady && <TypewriterDialog />}
        </motion.div>

        {/* Right page — Architecture diagram */}
        <motion.div
          className="journal-page journal-page--right"
          initial={{ opacity: 0, x: 60 }}
          animate={isInView ? { opacity: 1, x: 0 } : {}}
          transition={{ duration: 0.7, delay: 0.4, ease: 'easeOut' }}
        >
          <div className="page-header">
            <span className="page-number">pg. 48</span>
            <h3>Architectural Spec</h3>
            <span className="page-date">Agent Blueprint</span>
          </div>
          <AgentDiagram />
          <WaxSeal />
        </motion.div>
      </div>

      {/* Transmission Log */}
      <div className="journal-log-wrapper">
        <TransmissionLog />
      </div>

      {/* Coffee stain decorations */}
      <motion.div className="coffee-stain coffee-stain--1" style={{ opacity: coffeeOpacity }} />
      <motion.div className="coffee-stain coffee-stain--2" style={{ opacity: coffeeOpacity }} />

      <style>{`
        .journal-section {
          min-height: 100vh;
          padding: var(--section-pad) clamp(1rem, 5vw, 4rem);
          background: linear-gradient(180deg, var(--bg) 0%, #1a1710 5%, #1a1710 95%, var(--bg) 100%);
          position: relative;
          overflow: hidden;
        }
        .journal-header {
          text-align: center;
          margin-bottom: 3rem;
          display: flex;
          flex-direction: column;
          align-items: center;
        }
        .journal-header h2 {
          margin-bottom: 0.5rem;
        }
        .journal-spread {
          max-width: 1100px;
          margin: 0 auto;
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 3rem;
        }
        .journal-log-wrapper {
          max-width: 1100px;
          margin: 0 auto;
        }
        .journal-page {
          background: linear-gradient(135deg, #f5f0e8 0%, #ebe5d8 50%, #e0d8c8 100%);
          color: #2a2520;
          padding: 2.5rem 2rem;
          border-radius: 2px;
          position: relative;
          box-shadow:
            2px 4px 12px rgba(0,0,0,0.3),
            inset 0 0 60px rgba(0,0,0,0.05);
        }
        .journal-page--left {
          border-right: 1px solid #d0c8b8;
        }
        .journal-page::before {
          content: '';
          position: absolute;
          inset: 0;
          background: repeating-linear-gradient(
            transparent,
            transparent 27px,
            rgba(0,0,0,0.04) 28px
          );
          pointer-events: none;
        }
        .page-header {
          display: flex;
          align-items: baseline;
          gap: 1rem;
          margin-bottom: 1.5rem;
          padding-bottom: 0.75rem;
          border-bottom: 1px solid rgba(0,0,0,0.1);
        }
        .page-header h3 {
          font-family: var(--font-display);
          color: #2a2520;
          font-size: 1.2rem;
          flex: 1;
        }
        .page-number, .page-date {
          font-family: var(--font-mono);
          font-size: 0.65rem;
          color: rgba(0,0,0,0.3);
        }

        /* Coffee stains */
        .coffee-stain {
          position: absolute;
          border-radius: 50%;
          pointer-events: none;
        }
        .coffee-stain--1 {
          width: 80px;
          height: 80px;
          top: 15%;
          right: 8%;
          border: 2px solid rgba(139,100,50,0.08);
          background: radial-gradient(circle, transparent 50%, rgba(139,100,50,0.04) 100%);
        }
        .coffee-stain--2 {
          width: 50px;
          height: 45px;
          bottom: 25%;
          left: 5%;
          border: 1.5px solid rgba(139,100,50,0.06);
          background: radial-gradient(ellipse, transparent 40%, rgba(139,100,50,0.03) 100%);
          transform: rotate(15deg);
        }

        @media (max-width: 768px) {
          .journal-spread {
            grid-template-columns: 1fr;
            gap: 1.5rem;
          }
          .journal-page--left {
            border-right: none;
            border-bottom: 1px solid #d0c8b8;
          }
        }
      `}</style>
    </section>
  )
}
