import { useCallback, useEffect, useRef } from 'react'
import { Howl } from 'howler'
import { useLabStore } from '../store/labState'

type SoundName =
  | 'ambient'
  | 'typewriter'
  | 'assembly'
  | 'lightning'
  | 'heartbeat'
  | 'jar'
  | 'critic'
  | 'seal'
  | 'drawer'
  | 'rattle'
  | 'lever'

// Placeholder audio — we generate tones programmatically since we have no audio files yet
// In production, replace with real .webm samples via Howler sprites
const sounds = new Map<SoundName, Howl>()

function getOrCreateSound(name: SoundName): Howl | null {
  if (sounds.has(name)) return sounds.get(name)!

  // For now, we use a silent placeholder to avoid errors.
  // Real audio files would go in /src/assets/sounds/
  // and be loaded here as Howl instances.
  return null
}

export function useAudio() {
  const { audioEnabled, audioMuted, enableAudio } = useLabStore()
  const ambientRef = useRef<Howl | null>(null)

  // Enable audio on first user interaction
  const initAudio = useCallback(() => {
    if (!audioEnabled) {
      enableAudio()
    }
  }, [audioEnabled, enableAudio])

  // Play a sound effect
  const play = useCallback(
    (name: SoundName) => {
      if (!audioEnabled || audioMuted) return
      const sound = getOrCreateSound(name)
      sound?.play()
    },
    [audioEnabled, audioMuted]
  )

  // Stop a specific sound
  const stop = useCallback((name: SoundName) => {
    const sound = sounds.get(name)
    sound?.stop()
  }, [])

  // Handle mute changes for ambient
  useEffect(() => {
    if (ambientRef.current) {
      ambientRef.current.mute(audioMuted)
    }
  }, [audioMuted])

  return { play, stop, initAudio }
}
