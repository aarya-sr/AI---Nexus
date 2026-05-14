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
