export interface DataSpec {
  name: string
  format: string
  description: string
  example?: string
}

export interface ProcessStep {
  step_number: number
  description: string
  rules: string[]
  depends_on: number[]
}

export interface EdgeCase {
  description: string
  expected_handling: string
}

export interface QualityCriterion {
  criterion: string
  validation_method: string
}

export interface RequirementsDoc {
  domain: string
  inputs: DataSpec[]
  outputs: DataSpec[]
  process_steps: ProcessStep[]
  edge_cases: EdgeCase[]
  quality_criteria: QualityCriterion[]
  constraints: string[]
  assumptions: string[]
}

// --- AgentSpec types (mirrors backend app/models/spec.py) ---

export interface SpecMetadata {
  name: string
  domain: string
  framework_target: "crewai" | "langgraph"
  decision_rationale?: string | null
  created_from_pattern?: string | null
}

export interface AgentDef {
  id: string
  role: string
  goal: string
  backstory: string
  tools: string[]
  reasoning_strategy: "react" | "cot" | "plan_execute"
  receives_from: string[]
  sends_to: string[]
}

export interface ToolRef {
  id: string
  library_ref: string
  config: Record<string, unknown>
  accepts: string[]
  outputs: string[]
}

export interface GraphEdge {
  from_agent: string
  to_agent: string
  condition?: string | null
}

export interface GraphDef {
  nodes: string[]
  edges: GraphEdge[]
}

export interface ExecutionFlow {
  pattern: "sequential" | "parallel" | "hierarchical" | "graph"
  graph?: GraphDef | null
}

export interface AgentSpec {
  metadata: SpecMetadata
  agents: AgentDef[]
  tools: ToolRef[]
  memory: { strategy: string; shared_keys: string[]; persistence: string }
  execution_flow: ExecutionFlow
  error_handling: { agent_id: string; on_failure: string; max_retries: number; fallback_agent?: string | null }[]
  io_contracts: { agent_id: string; input_schema: { fields: { name: string; type: string; required: boolean }[] }; output_schema: { fields: { name: string; type: string; required: boolean }[] } }[]
}

// --- CritiqueReport types (mirrors backend app/models/critique.py) ---

export interface Finding {
  vector: string
  severity: "critical" | "warning" | "suggestion"
  description: string
  location: string
  evidence: string
  suggested_fix: string
}

export interface CritiqueReport {
  findings: Finding[]
  summary: string
  iteration: number
}
