import { useCallback, useRef } from 'react'
import { useLabStore, type AssemblyPhase } from '../store/labState'

const PHASE_DURATIONS: Record<string, number> = {
  pulling: 1200,
  stitching: 1800,
  lightning: 600,
}

export function useAssemblyTrigger() {
  const { assemblyPhase, setAssemblyPhase, assemblySpeed } = useLabStore()
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const advancePhase = useCallback(
    (phase: AssemblyPhase, nextPhase: AssemblyPhase | null, duration: number) => {
      setAssemblyPhase(phase)
      if (nextPhase) {
        timeoutRef.current = setTimeout(() => {
          if (nextPhase === 'alive') {
            setAssemblyPhase('alive')
          } else {
            const next = getNextPhase(nextPhase)
            if (next) {
              advancePhase(
                nextPhase,
                next.next,
                next.duration / assemblySpeed
              )
            }
          }
        }, duration / assemblySpeed)
      }
    },
    [setAssemblyPhase, assemblySpeed]
  )

  const triggerAssembly = useCallback(() => {
    if (assemblyPhase !== 'idle' && assemblyPhase !== 'orbiting' && assemblyPhase !== 'alive') return

    advancePhase('pulling', 'stitching', PHASE_DURATIONS.pulling)
  }, [assemblyPhase, advancePhase, assemblySpeed])

  return { triggerAssembly, assemblyPhase }
}

function getNextPhase(phase: AssemblyPhase): { next: AssemblyPhase | null; duration: number } | null {
  switch (phase) {
    case 'stitching':
      return { next: 'lightning', duration: PHASE_DURATIONS.stitching }
    case 'lightning':
      return { next: 'alive', duration: PHASE_DURATIONS.lightning }
    default:
      return null
  }
}
