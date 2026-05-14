import { useRef, useState } from 'react'
import { motion, useInView, useScroll, useTransform, AnimatePresence } from 'framer-motion'
import { EarlyAccessModal } from '../cta/EarlyAccessModal'

// --- Pipeline SVG component ---

interface PipelineNode {
  label: string
  x: number
}

function AnimatedPipeline({ nodes, active }: { nodes: PipelineNode[]; active: boolean }) {
  return (
    <div className="pipeline-svg-wrapper">
      <svg viewBox="0 0 600 60" className="pipeline-svg" preserveAspectRatio="xMidYMid meet">
        {nodes.map((node, i) => (
          <g key={i}>
            {/* Node rect */}
            <motion.rect
              x={node.x}
              y="15"
              width="90"
              height="30"
              rx="6"
              fill="none"
              stroke="var(--formaldehyde-dim)"
              strokeWidth="1.5"
              initial={{ opacity: 0.2 }}
              animate={active ? { opacity: 1, stroke: 'var(--formaldehyde)' } : {}}
              transition={{ delay: i * 0.4, duration: 0.3 }}
            />
            <motion.text
              x={node.x + 45}
              y="34"
              textAnchor="middle"
              fill="var(--formaldehyde)"
              fontSize="8"
              fontFamily="var(--font-mono)"
              letterSpacing="0.05em"
              initial={{ opacity: 0 }}
              animate={active ? { opacity: 1 } : {}}
              transition={{ delay: i * 0.4 + 0.1, duration: 0.2 }}
            >
              {node.label}
            </motion.text>

            {/* Connector line + data packet */}
            {i < nodes.length - 1 && (
              <>
                <line
                  x1={node.x + 90}
                  y1="30"
                  x2={nodes[i + 1].x}
                  y2="30"
                  stroke="var(--copper-dim)"
                  strokeWidth="1"
                />
                {active && (
                  <motion.rect
                    width="8"
                    height="4"
                    rx="1"
                    fill="var(--formaldehyde)"
                    y="28"
                    initial={{ x: node.x + 90, opacity: 0 }}
                    animate={{
                      x: [node.x + 90, nodes[i + 1].x],
                      opacity: [0, 1, 1, 0],
                    }}
                    transition={{
                      duration: 1.5,
                      delay: i * 0.4 + 0.5,
                      repeat: Infinity,
                      repeatDelay: 2,
                    }}
                  />
                )}
              </>
            )}
          </g>
        ))}
      </svg>
      {active && (
        <motion.span
          className="pipeline-complete-label"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: nodes.length * 0.4 + 1 }}
        >
          PIPELINE COMPLETE
        </motion.span>
      )}
    </div>
  )
}

// --- Drawer component ---

interface DrawerProps {
  title: string
  subtitle: string
  locked?: boolean
  lockedDomain?: string
  nodes?: PipelineNode[]
  stats?: string
  index: number
  onLockedClick?: () => void
}

function CabinetDrawer({ title, subtitle, locked, nodes, stats, index, onLockedClick }: DrawerProps) {
  const ref = useRef<HTMLDivElement>(null)
  const isInView = useInView(ref, { once: true, margin: '-50px' })
  const [isOpen, setIsOpen] = useState(!locked)
  const [flickering, setFlickering] = useState(false)

  const handleClick = () => {
    if (locked) {
      onLockedClick?.()
    } else {
      setIsOpen((o) => !o)
    }
  }

  const handleHover = () => {
    if (locked) {
      setFlickering(true)
      setTimeout(() => setFlickering(false), 200)
    }
  }

  return (
    <motion.div
      ref={ref}
      className={`cabinet-drawer ${locked ? 'cabinet-drawer--locked' : ''} clickable`}
      initial={{ opacity: 0, x: index % 2 === 0 ? -40 : 40 }}
      animate={isInView ? { opacity: 1, x: 0 } : {}}
      transition={{ duration: 0.5, delay: index * 0.15 }}
      whileHover={locked ? { x: [0, -3, 3, -2, 2, 0] } : undefined}
      onClick={handleClick}
      onMouseEnter={handleHover}
    >
      {/* Drawer front */}
      <div className="drawer-front">
        <motion.div
          className="drawer-handle"
          animate={isOpen && !locked ? { x: -4 } : { x: 0 }}
        />
        <div className="drawer-label">
          <span className="drawer-title">{title}</span>
          <span className="drawer-subtitle">{subtitle}</span>
        </div>
        {/* LED indicator */}
        <div className={`drawer-led ${locked ? 'drawer-led--crimson' : isOpen ? 'drawer-led--green' : 'drawer-led--amber'}`} />
        {locked && (
          <div className="drawer-lock">
            <svg width="24" height="28" viewBox="-1 -1 18 22" fill="none">
              <rect x="1" y="8" width="14" height="11" rx="2" stroke="var(--copper)" strokeWidth="1.5" />
              <path d="M 4 8 V 5 C 4 2.8 5.8 1 8 1 C 10.2 1 12 2.8 12 5 V 8" stroke="var(--copper)" strokeWidth="1.5" fill="none" />
              <circle cx="8" cy="14" r="1.5" fill="var(--copper)" />
            </svg>
          </div>
        )}
      </div>

      {/* Drawer content */}
      <AnimatePresence>
        {isOpen && !locked && nodes && (
          <motion.div
            className="drawer-content"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 400, damping: 35 }}
          >
            <div className="drawer-content-inner">
              <AnimatedPipeline nodes={nodes} active={isOpen} />
              {stats && <p className="drawer-stats">{stats}</p>}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Locked overlay with frozen pipeline */}
      {locked && (
        <div className={`locked-overlay ${flickering ? 'locked-overlay--flicker' : ''}`}>
          {nodes && (
            <div className="locked-pipeline-ghost">
              <AnimatedPipeline nodes={nodes} active={false} />
            </div>
          )}
          <div className="classified-stamp">CLASSIFIED</div>
        </div>
      )}
    </motion.div>
  )
}

// --- Main component ---

const PS08_NODES: PipelineNode[] = [
  { label: 'PDF Intake', x: 10 },
  { label: 'Credit Check', x: 140 },
  { label: 'Risk Analysis', x: 270 },
  { label: 'Compliance', x: 400 },
  { label: 'Report', x: 510 },
]

const PS06_NODES: PipelineNode[] = [
  { label: 'CSV Import', x: 30 },
  { label: 'Data Clean', x: 170 },
  { label: 'Scoring', x: 310 },
  { label: 'Risk Graph', x: 450 },
]

const LOCKED_NODES: PipelineNode[] = [
  { label: '???', x: 60 },
  { label: '???', x: 200 },
  { label: '???', x: 340 },
  { label: '???', x: 480 },
]

export function SpecimenCabinet() {
  const sectionRef = useRef<HTMLElement>(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [modalInterest, setModalInterest] = useState('')
  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ['start end', 'end start'],
  })

  const titleClip = useTransform(scrollYProgress, [0.05, 0.2], [100, 0])
  const subtitleOpacity = useTransform(scrollYProgress, [0.12, 0.22], [0, 1])

  const openLockedModal = (domain: string) => {
    setModalInterest(domain)
    setModalOpen(true)
  }

  return (
    <section ref={sectionRef} className="cabinet-section" data-section="cabinet">
      <div className="cabinet-container">
        <div className="cabinet-header">
          <motion.h2 style={{ clipPath: useTransform(titleClip, (v) => `inset(0 ${v}% 0 0)`) }}>
            The Specimen Cabinet
          </motion.h2>
          <motion.p className="lab-label" style={{ opacity: subtitleOpacity }}>
            Verified Agent Configurations
          </motion.p>
        </div>

        <div className="cabinet-two-col">
          {/* Left: open drawers */}
          <div className="cabinet-col cabinet-col--open">
            <CabinetDrawer
              title="PS-08 Loan Underwriting"
              subtitle="Co-pilot for document analysis and risk assessment"
              nodes={PS08_NODES}
              stats="~28s  |  5 agents  |  FCRA compliant"
              index={0}
            />
            <CabinetDrawer
              title="PS-06 Supplier Scoring"
              subtitle="Reliability scoring from structured and unstructured data"
              nodes={PS06_NODES}
              stats="~22s  |  4 agents  |  1000+ suppliers/batch"
              index={1}
            />
          </div>

          {/* Right: locked drawers */}
          <div className="cabinet-col cabinet-col--locked">
            <CabinetDrawer
              title="Healthcare"
              subtitle="Clinical trial data processing"
              locked
              lockedDomain="healthcare"
              nodes={LOCKED_NODES}
              index={2}
              onLockedClick={() => openLockedModal('healthcare')}
            />
            <CabinetDrawer
              title="Legal"
              subtitle="Contract review and compliance"
              locked
              lockedDomain="legal"
              nodes={LOCKED_NODES}
              index={3}
              onLockedClick={() => openLockedModal('legal')}
            />
            <CabinetDrawer
              title="Operations"
              subtitle="Supply chain optimization"
              locked
              lockedDomain="operations"
              nodes={LOCKED_NODES}
              index={4}
              onLockedClick={() => openLockedModal('operations')}
            />
          </div>
        </div>
      </div>

      <EarlyAccessModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        targetInterest={modalInterest}
      />

      <style>{`
        .cabinet-section {
          min-height: 80vh;
          padding: var(--section-pad) clamp(1rem, 5vw, 4rem);
          background:
            repeating-linear-gradient(
              88deg,
              transparent,
              transparent 40px,
              rgba(184,115,51,0.02) 40px,
              rgba(184,115,51,0.02) 41px
            );
        }
        .cabinet-container {
          max-width: 1100px;
          margin: 0 auto;
        }
        .cabinet-header {
          text-align: center;
          margin-bottom: 3rem;
          display: flex;
          flex-direction: column;
          align-items: center;
        }
        .cabinet-header h2 {
          margin-bottom: 0.5rem;
        }
        .cabinet-two-col {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 2rem;
          align-items: start;
        }
        .cabinet-col {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }
        .cabinet-drawer {
          border: 1px solid var(--copper-dim);
          border-radius: 4px;
          overflow: hidden;
          transition: border-color 0.3s;
          background: rgba(255,255,255,0.02);
          position: relative;
        }
        .cabinet-drawer:hover {
          border-color: var(--copper);
        }
        .cabinet-drawer--locked {
          opacity: 0.6;
        }
        .cabinet-drawer--locked:hover {
          opacity: 0.75;
        }
        .drawer-front {
          display: flex;
          align-items: center;
          gap: 1rem;
          padding: 1rem 1.5rem;
          background: linear-gradient(135deg, rgba(184,115,51,0.05) 0%, transparent 100%);
          cursor: pointer;
        }
        .drawer-handle {
          width: 40px;
          height: 6px;
          border-radius: 3px;
          background: var(--copper);
          opacity: 0.5;
          flex-shrink: 0;
        }
        .drawer-label {
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: 0.2rem;
        }
        .drawer-title {
          font-family: var(--font-mono);
          font-size: 0.8rem;
          letter-spacing: 0.1em;
          color: var(--bone);
          text-transform: uppercase;
        }
        .drawer-subtitle {
          font-family: var(--font-body);
          font-size: 0.85rem;
          color: var(--bone-dim);
        }
        .drawer-led {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          flex-shrink: 0;
        }
        .drawer-led--amber {
          background: var(--amber);
          box-shadow: 0 0 6px rgba(255,179,71,0.4);
        }
        .drawer-led--green {
          background: var(--formaldehyde);
          box-shadow: 0 0 6px var(--formaldehyde-glow);
        }
        .drawer-led--crimson {
          background: var(--crimson);
          box-shadow: 0 0 6px rgba(139,0,0,0.4);
        }
        .drawer-lock {
          flex-shrink: 0;
          opacity: 0.5;
        }
        .drawer-content {
          overflow: hidden;
        }
        .drawer-content-inner {
          padding: 1.5rem;
          border-top: 1px solid var(--copper-dim);
          background: rgba(0,0,0,0.2);
        }
        .pipeline-svg-wrapper {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }
        .pipeline-svg {
          width: 100%;
          height: 60px;
        }
        .pipeline-complete-label {
          font-family: var(--font-mono);
          font-size: 0.6rem;
          color: var(--formaldehyde);
          letter-spacing: 0.1em;
          text-align: center;
          text-shadow: 0 0 8px var(--formaldehyde-glow);
        }
        .drawer-stats {
          font-family: var(--font-mono);
          font-size: 0.65rem;
          color: var(--bone-dim);
          letter-spacing: 0.05em;
          text-align: center;
          margin-top: 0.5rem;
        }

        /* Locked overlay */
        .locked-overlay {
          position: relative;
          padding: 1rem 1.5rem;
          border-top: 1px solid var(--copper-dim);
          background: rgba(0,0,0,0.3);
          overflow: hidden;
        }
        .locked-pipeline-ghost {
          opacity: 0.15;
          filter: grayscale(1);
          pointer-events: none;
        }
        .locked-overlay--flicker .locked-pipeline-ghost {
          opacity: 0.4;
          filter: none;
        }
        .classified-stamp {
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%) rotate(-12deg);
          font-family: var(--font-mono);
          font-size: 1.2rem;
          letter-spacing: 0.2em;
          color: var(--crimson);
          border: 2px solid var(--crimson);
          padding: 0.3rem 0.8rem;
          opacity: 0.5;
          pointer-events: none;
        }

        @media (max-width: 768px) {
          .cabinet-two-col {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </section>
  )
}
