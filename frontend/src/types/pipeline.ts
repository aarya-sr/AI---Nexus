export type StageStatus = "pending" | "active" | "complete" | "error"

export interface PipelineStage {
  id: string
  name: string
  description: string
  status: StageStatus
}

export const PIPELINE_STAGES: PipelineStage[] = [
  { id: "elicitor", name: "Understanding", description: "Understanding your needs", status: "pending" },
  { id: "requirements_review", name: "Requirements Review", description: "Reviewing requirements with you", status: "pending" },
  { id: "architect", name: "Designing", description: "Designing your agent architecture", status: "pending" },
  { id: "critic", name: "Reviewing", description: "Reviewing the blueprint", status: "pending" },
  { id: "spec_review", name: "Spec Review", description: "Reviewing spec with you", status: "pending" },
  { id: "builder", name: "Building", description: "Building your agents", status: "pending" },
  { id: "tester", name: "Testing", description: "Testing the agents", status: "pending" },
  { id: "learner", name: "Learning", description: "Storing learnings", status: "pending" },
]

const AUTONOMOUS_STAGES = new Set(["architect", "critic", "builder", "tester", "learner"])

export function isAutonomousStage(stageId: string): boolean {
  return AUTONOMOUS_STAGES.has(stageId)
}

export interface ChatEntry {
  id: string
  variant: "system" | "user"
  type: string
  payload: Record<string, unknown>
  timestamp: string
}
