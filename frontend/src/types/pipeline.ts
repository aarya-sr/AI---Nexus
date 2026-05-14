export type StageStatus = "pending" | "active" | "complete" | "error"

export interface PipelineStage {
  id: string
  name: string
  description: string
  status: StageStatus
}

export const PIPELINE_STAGES: PipelineStage[] = [
  { id: "elicitor", name: "Understanding", description: "Understanding your needs", status: "pending" },
  { id: "architect", name: "Designing", description: "Designing your agent architecture", status: "pending" },
  { id: "critic", name: "Reviewing", description: "Reviewing the blueprint", status: "pending" },
  { id: "builder", name: "Building", description: "Building your agents", status: "pending" },
  { id: "tester", name: "Testing", description: "Testing the agents", status: "pending" },
  { id: "learner", name: "Learning", description: "Storing learnings", status: "pending" },
]

export interface ChatEntry {
  id: string
  variant: "system" | "user"
  type: string
  payload: Record<string, unknown>
  timestamp: string
}
