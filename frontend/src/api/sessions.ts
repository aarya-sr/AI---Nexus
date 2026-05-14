export async function approveCheckpoint(
  sessionId: string,
  checkpoint: "requirements" | "spec",
  approved: boolean,
  feedback?: string
): Promise<{ status: "resumed" | "revision_requested" }> {
  const res = await fetch(`/api/sessions/${sessionId}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ checkpoint, approved, feedback: feedback ?? null }),
  })
  if (!res.ok) {
    throw new Error(`Approve request failed: ${res.status}`)
  }
  return res.json()
}
