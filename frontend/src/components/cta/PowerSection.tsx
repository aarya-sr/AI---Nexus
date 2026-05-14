import { useState, useRef } from 'react'
import { motion, useScroll, useTransform } from 'framer-motion'
import { ElectricalLever } from './ElectricalLever'
import { EarlyAccessModal } from './EarlyAccessModal'

const MANIFESTO = [
  { text: 'You describe a workflow.', emphasis: false },
  { text: 'We assemble the intelligence.', emphasis: false },
  { text: 'You own the code.', emphasis: true },
]

export function PowerSection() {
  const [modalOpen, setModalOpen] = useState(false)
  const ref = useRef<HTMLElement>(null)
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ['start end', 'center center'],
  })

  // Each line gets a scroll-linked reveal
  const line0 = {
    opacity: useTransform(scrollYProgress, [0.1, 0.25], [0, 1]),
    scale: useTransform(scrollYProgress, [0.1, 0.25], [1.1, 1]),
    blur: useTransform(scrollYProgress, [0.1, 0.25], [4, 0]),
  }
  const line1 = {
    opacity: useTransform(scrollYProgress, [0.25, 0.4], [0, 1]),
    scale: useTransform(scrollYProgress, [0.25, 0.4], [1.1, 1]),
    blur: useTransform(scrollYProgress, [0.25, 0.4], [4, 0]),
  }
  const line2 = {
    opacity: useTransform(scrollYProgress, [0.4, 0.55], [0, 1]),
    scale: useTransform(scrollYProgress, [0.4, 0.55], [1.1, 1]),
    blur: useTransform(scrollYProgress, [0.4, 0.55], [4, 0]),
  }

  const leverOpacity = useTransform(scrollYProgress, [0.55, 0.7], [0, 1])
  const leverY = useTransform(scrollYProgress, [0.55, 0.7], [40, 0])
  const bgBrightness = useTransform(scrollYProgress, [0.1, 0.7], [0.8, 1.1])

  const lines = [line0, line1, line2]

  return (
    <section ref={ref} className="power-section" data-section="power">
      <motion.div className="power-bg" style={{ filter: useTransform(bgBrightness, (v) => `brightness(${v})`) }} />
      <div className="power-content">
        {/* Scroll-linked manifesto */}
        <div className="power-text">
          {MANIFESTO.map((line, i) => (
            <motion.p
              key={i}
              className={`power-line ${line.emphasis ? 'power-line--emphasis' : ''}`}
              style={{
                opacity: lines[i].opacity,
                scale: lines[i].scale,
                filter: useTransform(lines[i].blur, (v) => `blur(${v}px)`),
              }}
            >
              {line.text}
            </motion.p>
          ))}
        </div>

        {/* The Lever — slides up after text */}
        <motion.div
          className="lever-wrapper"
          style={{ opacity: leverOpacity, y: leverY }}
        >
          <ElectricalLever onPull={() => setModalOpen(true)} />
        </motion.div>
      </div>

      <EarlyAccessModal isOpen={modalOpen} onClose={() => setModalOpen(false)} />

      <style>{`
        .power-section {
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: var(--section-pad) clamp(1rem, 5vw, 4rem);
          position: relative;
        }
        .power-bg {
          position: absolute;
          inset: 0;
          background: var(--bg);
          z-index: -1;
        }
        .power-content {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 4rem;
          max-width: 600px;
          text-align: center;
        }
        .power-text {
          display: flex;
          flex-direction: column;
          gap: 0.8rem;
        }
        .power-line {
          font-family: var(--font-display);
          font-size: clamp(1.4rem, 3vw, 2rem);
          color: var(--bone);
          line-height: 1.4;
        }
        .power-line--emphasis {
          color: var(--formaldehyde);
          text-shadow: 0 0 20px var(--formaldehyde-glow);
        }
        .lever-wrapper {
          padding-top: 1rem;
        }
      `}</style>
    </section>
  )
}
