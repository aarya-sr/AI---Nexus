import { useRef } from 'react'
import { motion, useScroll, useTransform } from 'framer-motion'
import { SpecimenJar } from './SpecimenJar'
import { RoutingPathsRow1, RoutingPathsDown, RoutingPathsRow2 } from './RoutingPaths'
import { PIPELINE_STAGES } from './pipelineData'

export function DissectionTable() {
  const sectionRef = useRef<HTMLElement>(null)
  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ['start end', 'end start'],
  })

  const rotateX = useTransform(scrollYProgress, [0, 0.3, 0.7], [12, 0, -3])
  const perspective = useTransform(scrollYProgress, [0, 0.5], [1200, 800])

  // Header cinematic reveals
  const titleClip = useTransform(scrollYProgress, [0.05, 0.2], [100, 0])
  const subtitleOpacity = useTransform(scrollYProgress, [0.15, 0.25], [0, 1])
  const lineWidth = useTransform(scrollYProgress, [0.18, 0.3], [0, 100])

  const row1 = PIPELINE_STAGES.slice(0, 3)
  const row2 = PIPELINE_STAGES.slice(3, 6)

  return (
    <section ref={sectionRef} className="dissection-section" data-section="dissection">
      <motion.div
        className="dissection-table"
        style={{ perspective, transformStyle: 'preserve-3d' }}
      >
        <motion.div className="dissection-inner" style={{ rotateX }}>
          <div className="dissection-header">
            <motion.h2 style={{ clipPath: useTransform(titleClip, (v) => `inset(0 ${v}% 0 0)`) }}>
              The Dissection Table
            </motion.h2>
            <motion.p className="lab-label" style={{ opacity: subtitleOpacity }}>
              Six Stages — Six Agents — One Pipeline
            </motion.p>
            <motion.div className="header-line" style={{ width: useTransform(lineWidth, (v) => `${v}%`) }} />
          </div>

          {/* Row 1: Elicitor, Architect, Critic */}
          <div className="jars-row">
            {row1.map((stage, i) => (
              <SpecimenJar key={stage.name} stage={stage} index={i} row={0} sectionProgress={scrollYProgress} />
            ))}
          </div>

          {/* Routing between row 1 jars */}
          <div className="routing-wrapper">
            <RoutingPathsRow1 />
          </div>

          {/* Vertical connector */}
          <div className="routing-wrapper">
            <RoutingPathsDown />
          </div>

          {/* Routing between row 2 jars */}
          <div className="routing-wrapper">
            <RoutingPathsRow2 />
          </div>

          {/* Row 2: Builder, Tester, Learner */}
          <div className="jars-row">
            {row2.map((stage, i) => (
              <SpecimenJar key={stage.name} stage={stage} index={i + 3} row={1} sectionProgress={scrollYProgress} />
            ))}
          </div>
        </motion.div>
      </motion.div>

      <style>{`
        .dissection-section {
          min-height: 100vh;
          padding: var(--section-pad) clamp(1rem, 5vw, 4rem);
          position: relative;
        }
        .dissection-table {
          max-width: 1200px;
          margin: 0 auto;
        }
        .dissection-inner {
          transform-origin: center top;
        }
        .dissection-header {
          text-align: center;
          margin-bottom: 3rem;
          display: flex;
          flex-direction: column;
          align-items: center;
        }
        .dissection-header h2 {
          color: var(--bone);
          margin-bottom: 0.5rem;
        }
        .header-line {
          height: 1px;
          background: var(--copper-dim);
          margin-top: 0.75rem;
          max-width: 300px;
        }
        .jars-row {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 1.5rem;
        }
        @media (max-width: 900px) {
          .jars-row {
            grid-template-columns: repeat(2, 1fr);
          }
          .routing-wrapper {
            display: none;
          }
        }
        @media (max-width: 600px) {
          .jars-row {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </section>
  )
}
