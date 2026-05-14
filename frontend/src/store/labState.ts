import { create } from 'zustand'

export type AssemblyPhase =
  | 'idle'
  | 'orbiting'
  | 'pulling'
  | 'stitching'
  | 'lightning'
  | 'alive'

interface LabState {
  // Assembly
  assemblyPhase: AssemblyPhase
  setAssemblyPhase: (phase: AssemblyPhase) => void

  // Audio
  audioEnabled: boolean
  audioMuted: boolean
  toggleMute: () => void
  enableAudio: () => void

  // Shader uniforms (controlled by Leva)
  assemblySpeed: number
  voltageIntensity: number
  neuralDensity: number
  formaldehydeConcentration: number
  setUniform: (key: string, value: number) => void

  // Prompt
  userPrompt: string
  setUserPrompt: (prompt: string) => void

  // Target interest for cabinet → modal flow
  targetInterest: string
  setTargetInterest: (interest: string) => void

  // Scroll
  scrollProgress: number
  setScrollProgress: (progress: number) => void
}

export const useLabStore = create<LabState>((set) => ({
  assemblyPhase: 'idle',
  setAssemblyPhase: (phase) => set({ assemblyPhase: phase }),

  audioEnabled: false,
  audioMuted: false,
  toggleMute: () => set((s) => ({ audioMuted: !s.audioMuted })),
  enableAudio: () => set({ audioEnabled: true }),

  assemblySpeed: 1.0,
  voltageIntensity: 1.0,
  neuralDensity: 1.0,
  formaldehydeConcentration: 0.5,
  setUniform: (key, value) => set({ [key]: value }),

  userPrompt: '',
  setUserPrompt: (prompt) => set({ userPrompt: prompt }),

  targetInterest: '',
  setTargetInterest: (interest) => set({ targetInterest: interest }),

  scrollProgress: 0,
  setScrollProgress: (progress) => set({ scrollProgress: progress }),
}))
