import { useRef } from 'react'
import { motion, useInView, useTransform, type MotionValue } from 'framer-motion'
import { LabLabel } from '../shared/LabLabel'
import type { PipelineStage } from './pipelineData'

interface SpecimenJarProps {
  stage: PipelineStage
  index: number
  row?: number
  sectionProgress?: MotionValue<number>
}

function getLiquidGradient(stage: PipelineStage): string {
  if (stage.isCritic) {
    return 'linear-gradient(180deg, rgba(139,0,0,0.1) 0%, rgba(139,0,0,0.25) 100%)'
  }
  if (stage.color === 'var(--amber)') {
    return 'linear-gradient(180deg, rgba(255,179,71,0.05) 0%, rgba(255,179,71,0.15) 100%)'
  }
  return 'linear-gradient(180deg, rgba(57,255,20,0.03) 0%, rgba(57,255,20,0.1) 100%)'
}

export function SpecimenJar({ stage, index, row = 0, sectionProgress }: SpecimenJarProps) {
  const ref = useRef<HTMLDivElement>(null)
  const isInView = useInView(ref, { once: true, margin: '-100px' })

  // Parallax: row 0 moves slower, row 1 moves faster
  const parallaxY = sectionProgress
    ? useTransform(sectionProgress, [0.2, 0.8], row === 0 ? [20, -10] : [-10, 20])
    : undefined

  // Liquid fill animates with scroll
  const liquidHeight = sectionProgress
    ? useTransform(sectionProgress, [0.15 + index * 0.05, 0.4 + index * 0.05], [0, 75])
    : undefined

  // Jar glass border brightness
  const borderOpacity = sectionProgress
    ? useTransform(sectionProgress, [0.2, 0.5], [0.3, 1])
    : undefined

  return (
    <motion.div
      ref={ref}
      className={`specimen-jar ${stage.isCritic ? 'specimen-jar--critic' : ''}`}
      initial={{ opacity: 0, y: 80, scale: 0.85 }}
      animate={isInView ? { opacity: 1, y: 0, scale: 1 } : {}}
      transition={{
        duration: 0.7,
        delay: index * 0.15,
        ease: 'easeOut',
      }}
      style={parallaxY ? { y: parallaxY } : undefined}
      whileHover={{ y: -6, transition: { duration: 0.2 } }}
    >
      {/* Critic flash on entrance */}
      {stage.isCritic && isInView && (
        <motion.div
          className="critic-flash"
          initial={{ opacity: 0.6 }}
          animate={{ opacity: 0 }}
          transition={{ duration: 0.4 }}
        />
      )}

      {/* Jar glass */}
      <motion.div
        className="jar-glass"
        style={borderOpacity ? { opacity: borderOpacity } : undefined}
      >
        {/* Jar liquid */}
        <motion.div
          className="jar-liquid"
          style={{
            background: getLiquidGradient(stage),
            height: liquidHeight ? useTransform(liquidHeight, (v) => `${v}%`) : '75%',
          }}
        />

        {/* Crack overlay for Critic */}
        {stage.isCritic && (
          <svg className="jar-crack" viewBox="0 0 100 120" preserveAspectRatio="none">
            <path
              d="M 45 5 L 48 25 L 42 35 L 50 50 L 44 65 L 52 80 L 46 95 L 48 115"
              stroke="var(--crimson)"
              strokeWidth="1.5"
              fill="none"
              opacity="0.6"
            />
            <path d="M 48 25 L 55 30" stroke="var(--crimson)" strokeWidth="1" fill="none" opacity="0.4" />
            <path d="M 50 50 L 58 48" stroke="var(--crimson)" strokeWidth="1" fill="none" opacity="0.4" />
          </svg>
        )}

        {/* Inner content */}
        <div className="jar-inner">
          <div className="jar-icon">{getJarIcon(stage.name)}</div>
        </div>

        {/* Pulse effect for Critic */}
        {stage.isCritic && <div className="jar-pulse" />}
      </motion.div>

      {/* Label plate */}
      <div className="jar-plate">
        <LabLabel text={stage.name} color={stage.isCritic ? 'var(--crimson)' : undefined} />
        <span className="jar-model">{stage.model}</span>
      </div>

      {/* Description */}
      <p className="jar-description">{stage.description}</p>

      {/* Detail bullets — staggered reveal */}
      <ul className="jar-details">
        {stage.details.map((detail, i) => (
          <motion.li
            key={i}
            initial={{ opacity: 0, x: -10 }}
            animate={isInView ? { opacity: 1, x: 0 } : {}}
            transition={{ delay: index * 0.15 + 0.4 + i * 0.1 }}
          >
            {detail}
          </motion.li>
        ))}
      </ul>

      <style>{`
        .specimen-jar {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 1rem;
          padding: 1.5rem;
          position: relative;
        }
        .critic-flash {
          position: absolute;
          inset: 0;
          background: radial-gradient(circle, rgba(139,0,0,0.3), transparent);
          border-radius: 8px;
          pointer-events: none;
          z-index: 5;
        }
        .jar-glass {
          position: relative;
          width: 160px;
          height: 200px;
          border: 1px solid var(--copper-dim);
          border-radius: 8px 8px 20px 20px;
          overflow: hidden;
          background: rgba(255,255,255,0.02);
          box-shadow: inset 0 0 30px rgba(0,0,0,0.3);
          transition: border-color 0.3s, box-shadow 0.3s;
        }
        .specimen-jar:hover .jar-glass {
          border-color: var(--copper);
          box-shadow: inset 0 0 30px rgba(0,0,0,0.3), 0 0 15px rgba(184,115,51,0.15);
        }
        .specimen-jar--critic .jar-glass {
          border-color: rgba(139,0,0,0.4);
          box-shadow: inset 0 0 30px rgba(139,0,0,0.15), 0 0 20px rgba(139,0,0,0.1);
        }
        .jar-liquid {
          position: absolute;
          bottom: 0;
          left: 0;
          right: 0;
          transition: height 0.5s ease;
        }
        .jar-crack {
          position: absolute;
          inset: 0;
          width: 100%;
          height: 100%;
          pointer-events: none;
        }
        .jar-inner {
          position: relative;
          z-index: 1;
          display: flex;
          align-items: center;
          justify-content: center;
          height: 100%;
        }
        .jar-icon {
          font-size: 2.5rem;
          opacity: 0.7;
        }
        .jar-pulse {
          position: absolute;
          inset: 0;
          border-radius: inherit;
          background: radial-gradient(circle, rgba(139,0,0,0.2) 0%, transparent 70%);
          animation: pulse-critic 2s ease-in-out infinite;
        }
        @keyframes pulse-critic {
          0%, 100% { opacity: 0.3; }
          50% { opacity: 0.8; }
        }
        .jar-plate {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 0.3rem;
        }
        .jar-model {
          font-family: var(--font-mono);
          font-size: 0.6rem;
          color: var(--bone-dim);
          letter-spacing: 0.05em;
        }
        .jar-description {
          font-family: var(--font-body);
          font-size: 0.95rem;
          text-align: center;
          color: var(--bone);
          line-height: 1.5;
        }
        .jar-details {
          list-style: none;
          display: flex;
          flex-direction: column;
          gap: 0.3rem;
        }
        .jar-details li {
          font-family: var(--font-mono);
          font-size: 0.7rem;
          color: var(--bone-dim);
          padding-left: 1em;
          position: relative;
        }
        .jar-details li::before {
          content: '\\25C6';
          position: absolute;
          left: 0;
          color: var(--formaldehyde-dim);
          font-size: 0.5rem;
          top: 0.15em;
        }
        .specimen-jar--critic .jar-details li::before {
          color: rgba(139,0,0,0.4);
        }
      `}</style>
    </motion.div>
  )
}

function getJarIcon(name: string): string {
  const icons: Record<string, string> = {
    ELICITOR: '?',
    ARCHITECT: '\u25A1',
    CRITIC: '\u2620',
    BUILDER: '\u2692',
    TESTER: '\u26A0',
    LEARNER: '\u2699',
  }
  return icons[name] || '\u25CF'
}
