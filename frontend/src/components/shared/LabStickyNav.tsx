import { motion } from 'framer-motion'
import { useLabStore } from '../../store/labState'

const SECTIONS = [
  { id: 'hero', label: 'I' },
  { id: 'dissection', label: 'II' },
  { id: 'journal', label: 'III' },
  { id: 'cabinet', label: 'IV' },
  { id: 'power', label: 'V' },
]

export function LabStickyNav() {
  const scrollProgress = useLabStore((s) => s.scrollProgress)
  const activeIndex = Math.min(
    Math.floor(scrollProgress * SECTIONS.length),
    SECTIONS.length - 1
  )

  const handleClick = (id: string) => {
    const el = document.querySelector(`[data-section="${id}"]`)
    el?.scrollIntoView({ behavior: 'smooth' })
  }

  return (
    <nav className="lab-sticky-nav">
      <div className="nav-track">
        <div className="nav-line">
          <motion.div
            className="nav-line-fill"
            style={{ height: `${scrollProgress * 100}%` }}
          />
        </div>
        {SECTIONS.map((s, i) => (
          <button
            key={s.id}
            className={`nav-dot ${i === activeIndex ? 'nav-dot--active' : ''}`}
            onClick={() => handleClick(s.id)}
            aria-label={`Go to section ${s.label}`}
            title={s.label}
          >
            <span className="nav-dot-inner" />
          </button>
        ))}
      </div>

      <style>{`
        .lab-sticky-nav {
          position: fixed;
          left: 1rem;
          top: 50%;
          transform: translateY(-50%);
          z-index: 80;
        }
        .nav-track {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 1.5rem;
          position: relative;
        }
        .nav-line {
          position: absolute;
          left: 50%;
          top: 0;
          bottom: 0;
          width: 2px;
          transform: translateX(-50%);
          background: var(--copper-dim);
          overflow: hidden;
          z-index: -1;
        }
        .nav-line-fill {
          width: 100%;
          background: var(--formaldehyde);
          box-shadow: 0 0 6px var(--formaldehyde-glow);
          transition: height 0.1s linear;
        }
        .nav-dot {
          width: 14px;
          height: 14px;
          border-radius: 50%;
          border: 1px solid var(--copper-dim);
          background: var(--bg);
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: border-color 0.3s;
          padding: 0;
        }
        .nav-dot:hover {
          border-color: var(--copper);
        }
        .nav-dot--active {
          border-color: var(--formaldehyde);
        }
        .nav-dot-inner {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: transparent;
          transition: background 0.3s, box-shadow 0.3s;
        }
        .nav-dot--active .nav-dot-inner {
          background: var(--formaldehyde);
          box-shadow: 0 0 8px var(--formaldehyde-glow);
        }
        @media (max-width: 900px) {
          .lab-sticky-nav {
            display: none;
          }
        }
      `}</style>
    </nav>
  )
}
