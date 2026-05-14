import { SystemAvatar } from "./ChatMessage"

export function TypingIndicator() {
  return (
    <div className="flex items-start gap-3 animate-[fadeUp_200ms_ease-out]">
      <SystemAvatar />
      <div className="bg-surface rounded-2xl rounded-bl-md px-4 py-3 flex items-center gap-1.5">
        <span className="w-1.5 h-1.5 rounded-full bg-text-tertiary animate-[bounce_1.2s_ease-in-out_infinite]" />
        <span className="w-1.5 h-1.5 rounded-full bg-text-tertiary animate-[bounce_1.2s_ease-in-out_0.2s_infinite]" />
        <span className="w-1.5 h-1.5 rounded-full bg-text-tertiary animate-[bounce_1.2s_ease-in-out_0.4s_infinite]" />
      </div>
    </div>
  )
}
