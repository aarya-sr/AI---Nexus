import type { ExecutionFlow, AgentDef, GraphEdge } from "../types/models"

interface Props {
  executionFlow: ExecutionFlow
  agents: AgentDef[]
}

interface DiagramEdge {
  from: string
  to: string
  condition?: string | null
}

export function FlowDiagram({ executionFlow, agents }: Props) {
  if (agents.length === 0) return null

  const edges = resolveEdges(executionFlow, agents)
  const orderedNodes = resolveNodeOrder(agents, edges)

  return (
    <div className="bg-surface border border-border rounded-[10px] px-6 py-4 overflow-x-auto">
      <div className="flex items-center gap-2 min-w-max">
        {orderedNodes.map((nodeId, i) => {
          const agent = agents.find((a) => a.id === nodeId)
          const label = agent ? agent.role : nodeId
          const edgeToNext = i < orderedNodes.length - 1
            ? edges.find((e) => e.from === nodeId && e.to === orderedNodes[i + 1])
            : null

          return (
            <div key={nodeId} className="flex items-center gap-2">
              <div className="bg-surface-elevated border border-border rounded-lg px-4 py-2 hover:border-amber-500 transition-colors cursor-default">
                <span className="text-[13px] font-medium text-text-primary whitespace-nowrap">
                  {label}
                </span>
              </div>
              {i < orderedNodes.length - 1 && (
                <div className="flex flex-col items-center">
                  <span className="text-text-tertiary text-[14px]">{"\u2192"}</span>
                  {edgeToNext?.condition && (
                    <span className="text-[11px] text-text-tertiary whitespace-nowrap">
                      {edgeToNext.condition}
                    </span>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

function resolveEdges(flow: ExecutionFlow, agents: AgentDef[]): DiagramEdge[] {
  // Use graph edges if available
  if (flow.graph?.edges && flow.graph.edges.length > 0) {
    return flow.graph.edges.map((e: GraphEdge) => ({
      from: e.from_agent,
      to: e.to_agent,
      condition: e.condition,
    }))
  }

  // Infer from agent sends_to/receives_from
  const edges: DiagramEdge[] = []
  const seen = new Set<string>()
  for (const agent of agents) {
    for (const target of agent.sends_to) {
      const key = `${agent.id}->${target}`
      if (!seen.has(key)) {
        edges.push({ from: agent.id, to: target })
        seen.add(key)
      }
    }
  }
  if (edges.length > 0) return edges

  // Fallback: sequential chain from agents list order
  const sequential: DiagramEdge[] = []
  for (let i = 0; i < agents.length - 1; i++) {
    sequential.push({ from: agents[i].id, to: agents[i + 1].id })
  }
  return sequential
}

function resolveNodeOrder(agents: AgentDef[], edges: DiagramEdge[]): string[] {
  if (edges.length === 0) return agents.map((a) => a.id)

  // Topological sort for display order
  const allNodes = new Set(agents.map((a) => a.id))
  for (const e of edges) {
    allNodes.add(e.from)
    allNodes.add(e.to)
  }

  const inDegree = new Map<string, number>()
  const adj = new Map<string, string[]>()
  for (const n of allNodes) {
    inDegree.set(n, 0)
    adj.set(n, [])
  }
  for (const e of edges) {
    adj.get(e.from)!.push(e.to)
    inDegree.set(e.to, (inDegree.get(e.to) || 0) + 1)
  }

  const queue: string[] = []
  for (const [n, deg] of inDegree) {
    if (deg === 0) queue.push(n)
  }

  const ordered: string[] = []
  while (queue.length > 0) {
    const node = queue.shift()!
    ordered.push(node)
    for (const nb of adj.get(node) || []) {
      const newDeg = (inDegree.get(nb) || 1) - 1
      inDegree.set(nb, newDeg)
      if (newDeg === 0) queue.push(nb)
    }
  }

  // Append any remaining nodes (cycles or disconnected)
  for (const n of allNodes) {
    if (!ordered.includes(n)) ordered.push(n)
  }

  return ordered
}
