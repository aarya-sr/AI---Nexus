import { useState, type KeyboardEvent } from "react"
import { usePipelineState } from "../context/PipelineContext"

interface Props {
  onSubmit: (text: string) => void
}

export function PromptInput({ onSubmit }: Props) {
  const [value, setValue] = useState("")
  const { isWorking } = usePipelineState()

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  function submit() {
    const trimmed = value.trim()
    if (!trimmed || isWorking) return
    onSubmit(trimmed)
    setValue("")
  }

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-surface-elevated border-t border-border p-4 z-10">
      <div className="max-w-[720px] mx-auto flex gap-3 items-end">
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isWorking}
          placeholder={
            isWorking
              ? "Frankenstein is working..."
              : "Describe the workflow you want to automate..."
          }
          rows={1}
          className="flex-1 resize-none bg-bg border border-border rounded-lg px-4 py-3 text-[15px] leading-[1.6] text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent disabled:opacity-50 disabled:cursor-not-allowed"
        />
        <button
          onClick={submit}
          disabled={isWorking || !value.trim()}
          className="h-[44px] px-5 bg-accent text-bg font-semibold text-sm rounded-lg hover:bg-accent-hover active:scale-[0.97] transition-all duration-100 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Send
        </button>
      </div>
    </div>
  )
}
