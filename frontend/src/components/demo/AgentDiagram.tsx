import { useRef } from 'react'
import { motion, useInView } from 'framer-motion'

const NODES = [
  { id: 'pdf', label: 'PDF Parser', x: 100, y: 70, type: 'input' },
  { id: 'credit', label: 'Credit API', x: 340, y: 50, type: 'input' },
  { id: 'db', label: 'Customer DB', x: 100, y: 200, type: 'input' },
  { id: 'analyzer', label: 'Risk Analyzer', x: 220, y: 140, type: 'core' },
  { id: 'compliance', label: 'FCRA Check', x: 380, y: 160, type: 'check' },
  { id: 'scorer', label: 'Score Engine', x: 300, y: 240, type: 'process' },
  { id: 'reporter', label: 'Report Gen', x: 180, y: 320, type: 'output' },
]

const EDGES = [
  { from: 'pdf', to: 'analyzer', label: 'docs' },
  { from: 'credit', to: 'analyzer', label: 'scores' },
  { from: 'db', to: 'analyzer', label: 'history' },
  { from: 'analyzer', to: 'compliance', label: '' },
  { from: 'analyzer', to: 'scorer', label: 'risk factors' },
  { from: 'compliance', to: 'scorer', label: 'pass/fail' },
  { from: 'scorer', to: 'reporter', label: 'final score' },
]

export function AgentDiagram() {
  const ref = useRef<SVGSVGElement>(null)
  const isInView = useInView(ref, { once: true, margin: '-50px' })

  const getNode = (id: string) => NODES.find((n) => n.id === id)!

  const nodeStyles: Record<string, { fill: string; stroke: string; r: number }> = {
    input: { fill: 'rgba(100,80,40,0.06)', stroke: '#8b7b50', r: 28 },
    core: { fill: 'rgba(30,100,30,0.1)', stroke: '#4a7a3a', r: 36 },
    check: { fill: 'rgba(139,0,0,0.06)', stroke: '#8b4040', r: 28 },
    process: { fill: 'rgba(100,80,40,0.08)', stroke: '#8b7b50', r: 30 },
    output: { fill: 'rgba(30,100,30,0.12)', stroke: '#4a7a3a', r: 32 },
  }

  return (
    <svg
      ref={ref}
      viewBox="0 0 480 380"
      style={{ width: '100%', maxWidth: '480px' }}
    >
      <defs>
        <filter id="pencil">
          <feTurbulence type="turbulence" baseFrequency="0.04" numOctaves="2" result="noise" />
          <feDisplacementMap in="SourceGraphic" in2="noise" scale="1.2" />
        </filter>
        <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
          <polygon points="0 0, 8 3, 0 6" fill="#8b6b30" opacity="0.5" />
        </marker>
      </defs>

      {/* Edges with arrows and labels */}
      {EDGES.map((edge, i) => {
        const from = getNode(edge.from)
        const to = getNode(edge.to)
        const dx = to.x - from.x
        const dy = to.y - from.y
        const len = Math.sqrt(dx * dx + dy * dy)
        const style = nodeStyles[from.type]
        const toStyle = nodeStyles[to.type]
        // Offset start/end to be at circle edge
        const startX = from.x + (dx / len) * style.r
        const startY = from.y + (dy / len) * style.r
        const endX = to.x - (dx / len) * toStyle.r
        const endY = to.y - (dy / len) * toStyle.r
        const midX = (startX + endX) / 2 + (i % 2 === 0 ? 6 : -6)
        const midY = (startY + endY) / 2 + (i % 3 === 0 ? 4 : -3)

        return (
          <g key={`${edge.from}-${edge.to}`}>
            <motion.path
              d={`M ${startX} ${startY} Q ${midX} ${midY} ${endX} ${endY}`}
              stroke="#8b6b30"
              strokeWidth="1.5"
              fill="none"
              strokeLinecap="round"
              markerEnd="url(#arrowhead)"
              filter="url(#pencil)"
              initial={{ pathLength: 0, opacity: 0 }}
              animate={isInView ? { pathLength: 1, opacity: 0.55 } : {}}
              transition={{ duration: 0.7, delay: 0.4 + i * 0.18 }}
            />
            {/* Edge label */}
            {edge.label && (
              <motion.text
                x={midX}
                y={midY - 6}
                textAnchor="middle"
                fill="#8b6b30"
                fontSize="7"
                fontFamily="'Special Elite', cursive"
                initial={{ opacity: 0 }}
                animate={isInView ? { opacity: 0.45 } : {}}
                transition={{ delay: 1 + i * 0.15 }}
              >
                {edge.label}
              </motion.text>
            )}
          </g>
        )
      })}

      {/* Nodes */}
      {NODES.map((node, i) => {
        const style = nodeStyles[node.type]
        return (
          <g key={node.id}>
            <motion.circle
              cx={node.x}
              cy={node.y}
              r={style.r}
              fill={style.fill}
              stroke={style.stroke}
              strokeWidth={node.type === 'core' ? 2 : 1.2}
              strokeDasharray={node.type === 'input' ? '4 2' : undefined}
              initial={{ opacity: 0 }}
              animate={isInView ? { opacity: 0.7 } : {}}
              transition={{ duration: 0.3, delay: i * 0.12 }}
            />
            <motion.text
              x={node.x}
              y={node.y + 4}
              textAnchor="middle"
              fill="#3a2a10"
              fontSize="9"
              fontFamily="'IBM Plex Mono', monospace"
              fontWeight={node.type === 'core' ? '600' : '400'}
              initial={{ opacity: 0 }}
              animate={isInView ? { opacity: 0.85 } : {}}
              transition={{ duration: 0.3, delay: i * 0.12 + 0.15 }}
            >
              {node.label}
            </motion.text>
          </g>
        )
      })}

      {/* Hand-drawn annotations */}
      <motion.g initial={{ opacity: 0 }} animate={isInView ? { opacity: 1 } : {}} transition={{ delay: 2 }}>
        {/* Arrow annotation pointing to FCRA */}
        <line x1="430" y1="130" x2="408" y2="152" stroke="#8b0000" strokeWidth="0.8" opacity="0.4" />
        <text x="435" y="125" fill="#8b0000" fontSize="7.5" fontFamily="'Special Elite', cursive" opacity="0.5" transform="rotate(-5, 435, 125)">
          compliance gate!
        </text>

        {/* Output annotation */}
        <line x1="110" y1="340" x2="155" y2="328" stroke="#4a7a3a" strokeWidth="0.8" opacity="0.4" />
        <text x="50" y="350" fill="#4a7a3a" fontSize="7.5" fontFamily="'Special Elite', cursive" opacity="0.5">
          final deliverable
        </text>

        {/* Version note */}
        <text x="420" y="370" fill="#8b6b30" fontSize="7" fontFamily="'Special Elite', cursive" opacity="0.35" transform="rotate(2, 420, 370)">
          spec v2.1 — approved
        </text>
      </motion.g>
    </svg>
  )
}
