import { motion } from 'framer-motion'

export function RoutingPathsRow1() {
  return (
    <svg
      className="routing-paths"
      viewBox="0 0 900 120"
      style={{
        width: '100%',
        height: '80px',
        display: 'block',
        margin: '0.5rem 0',
      }}
    >
      {/* Forward flow: ELICITOR -> ARCHITECT -> CRITIC */}
      <motion.line
        x1="100" y1="60" x2="380" y2="60"
        stroke="var(--formaldehyde)" strokeWidth="2" opacity="0.5"
        initial={{ pathLength: 0 }} whileInView={{ pathLength: 1 }}
        transition={{ duration: 1, delay: 0.3 }}
      />
      <motion.line
        x1="520" y1="60" x2="800" y2="60"
        stroke="var(--formaldehyde)" strokeWidth="2" opacity="0.5"
        initial={{ pathLength: 0 }} whileInView={{ pathLength: 1 }}
        transition={{ duration: 1, delay: 0.6 }}
      />

      {/* Arrows */}
      <motion.polygon
        points="375,52 390,60 375,68" fill="var(--formaldehyde)" opacity="0.6"
        initial={{ opacity: 0 }} whileInView={{ opacity: 0.6 }}
        transition={{ delay: 1.2 }}
      />
      <motion.polygon
        points="795,52 810,60 795,68" fill="var(--formaldehyde)" opacity="0.6"
        initial={{ opacity: 0 }} whileInView={{ opacity: 0.6 }}
        transition={{ delay: 1.5 }}
      />

      {/* CRITIC -> ARCHITECT feedback loop (RED, arcs above) */}
      <motion.path
        d="M 760 40 C 760 0, 440 0, 440 40"
        stroke="var(--crimson)" strokeWidth="2.5" fill="none"
        strokeDasharray="8 5" opacity="0.6"
        initial={{ pathLength: 0 }} whileInView={{ pathLength: 1 }}
        transition={{ duration: 1.5, delay: 1.8 }}
      />
      <motion.polygon
        points="440,40 432,25 448,25" fill="var(--crimson)" opacity="0.6"
        initial={{ opacity: 0 }} whileInView={{ opacity: 0.6 }}
        transition={{ delay: 3 }}
      />
      <motion.text
        x="600" y="15" textAnchor="middle" fill="var(--crimson)" opacity="0"
        fontSize="12" fontFamily="var(--font-mono)" letterSpacing="0.12em"
      >
        <animate attributeName="opacity" from="0" to="0.6" dur="0.5s" begin="3s" fill="freeze" />
        REVISION LOOP
      </motion.text>
    </svg>
  )
}

export function RoutingPathsDown() {
  return (
    <svg
      viewBox="0 0 100 60"
      style={{
        width: '60px',
        height: '50px',
        display: 'block',
        margin: '0 auto',
      }}
    >
      {/* Vertical connector: row 1 -> row 2 */}
      <motion.line
        x1="50" y1="5" x2="50" y2="45"
        stroke="var(--formaldehyde)" strokeWidth="2" opacity="0.4"
        initial={{ pathLength: 0 }} whileInView={{ pathLength: 1 }}
        transition={{ duration: 0.6, delay: 0.5 }}
      />
      <motion.polygon
        points="43,42 50,55 57,42" fill="var(--formaldehyde)" opacity="0.5"
        initial={{ opacity: 0 }} whileInView={{ opacity: 0.5 }}
        transition={{ delay: 1 }}
      />
    </svg>
  )
}

export function RoutingPathsRow2() {
  return (
    <svg
      className="routing-paths-row2"
      viewBox="0 0 900 120"
      style={{
        width: '100%',
        height: '80px',
        display: 'block',
        margin: '0.5rem 0',
      }}
    >
      {/* Forward flow: BUILDER -> TESTER -> LEARNER */}
      <motion.line
        x1="100" y1="60" x2="380" y2="60"
        stroke="var(--formaldehyde)" strokeWidth="2" opacity="0.5"
        initial={{ pathLength: 0 }} whileInView={{ pathLength: 1 }}
        transition={{ duration: 1, delay: 0.3 }}
      />
      <motion.line
        x1="520" y1="60" x2="800" y2="60"
        stroke="var(--formaldehyde)" strokeWidth="2" opacity="0.5"
        initial={{ pathLength: 0 }} whileInView={{ pathLength: 1 }}
        transition={{ duration: 1, delay: 0.6 }}
      />

      <motion.polygon
        points="375,52 390,60 375,68" fill="var(--formaldehyde)" opacity="0.6"
        initial={{ opacity: 0 }} whileInView={{ opacity: 0.6 }}
        transition={{ delay: 1.2 }}
      />
      <motion.polygon
        points="795,52 810,60 795,68" fill="var(--formaldehyde)" opacity="0.6"
        initial={{ opacity: 0 }} whileInView={{ opacity: 0.6 }}
        transition={{ delay: 1.5 }}
      />

      {/* TESTER -> BUILDER feedback loop (AMBER, arcs below) */}
      <motion.path
        d="M 440 80 C 440 118, 760 118, 760 80"
        stroke="var(--amber)" strokeWidth="2.5" fill="none"
        strokeDasharray="8 5" opacity="0.55"
        initial={{ pathLength: 0 }} whileInView={{ pathLength: 1 }}
        transition={{ duration: 1.5, delay: 1.8 }}
      />
      <motion.polygon
        points="440,80 432,95 448,95" fill="var(--amber)" opacity="0.55"
        initial={{ opacity: 0 }} whileInView={{ opacity: 0.55 }}
        transition={{ delay: 3 }}
      />
      <motion.text
        x="600" y="115" textAnchor="middle" fill="var(--amber)" opacity="0"
        fontSize="12" fontFamily="var(--font-mono)" letterSpacing="0.12em"
      >
        <animate attributeName="opacity" from="0" to="0.5" dur="0.5s" begin="3s" fill="freeze" />
        FIX LOOP
      </motion.text>
    </svg>
  )
}
