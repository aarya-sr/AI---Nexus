export interface PipelineStage {
  name: string
  model: string
  description: string
  color: string
  details: string[]
  isCritic?: boolean
}

export const PIPELINE_STAGES: PipelineStage[] = [
  {
    name: 'ELICITOR',
    model: 'gpt-4o-mini',
    description: 'Structured domain extraction. Asks 5 categories of targeted questions to extract what the agent needs to know.',
    color: 'var(--formaldehyde)',
    details: [
      'Domain-specific question generation',
      '5 knowledge categories: goals, constraints, data, tools, edge cases',
      'Structured requirements document output',
    ],
  },
  {
    name: 'ARCHITECT',
    model: 'claude-sonnet-4-6',
    description: 'Generates framework-agnostic spec. Designs agent roles, memory, flow, and selects tools from validated library.',
    color: 'var(--formaldehyde)',
    details: [
      'Framework-agnostic agent specification',
      'Tool selection from pre-validated library',
      'Agent roles, memory architecture, control flow',
    ],
  },
  {
    name: 'CRITIC',
    model: 'gpt-4o',
    description: 'Multi-vector adversarial attack on spec. Different model family on purpose. Finds edge cases, dead-ends, tool mismatches.',
    color: 'var(--crimson)',
    details: [
      'Multi-vector spec attack surface',
      'Edge case identification, dead-end detection',
      'Forces Architect revision until no criticals remain',
    ],
    isCritic: true,
  },
  {
    name: 'BUILDER',
    model: 'claude-sonnet-4-6',
    description: 'Compiles validated spec into CrewAI or LangGraph code. Template-driven, not free-form generation.',
    color: 'var(--formaldehyde)',
    details: [
      'Spec-to-code compilation',
      'CrewAI or LangGraph target frameworks',
      'Template-driven generation with guardrails',
    ],
  },
  {
    name: 'TESTER',
    model: 'gpt-4o-mini',
    description: 'Runs agents in Docker sandbox. Validates output against spec contracts. Traces failures to spec decisions.',
    color: 'var(--amber)',
    details: [
      'Docker-sandboxed execution',
      'Contract-based output validation',
      'Failure → spec-level root cause tracing',
    ],
  },
  {
    name: 'LEARNER',
    model: 'gpt-4o-mini',
    description: 'Stores build outcomes in Chroma for future RAG. The system gets better at building agents over time.',
    color: 'var(--formaldehyde)',
    details: [
      'Build outcome persistence to Chroma',
      'Spec patterns for future RAG retrieval',
      'Continuous improvement loop',
    ],
  },
]
