import { useEffect } from 'react'
import { useLabStore } from '../store/labState'

export function useScrollProgress() {
  const setScrollProgress = useLabStore((s) => s.setScrollProgress)

  useEffect(() => {
    const onScroll = () => {
      const total = document.documentElement.scrollHeight - window.innerHeight
      const progress = total > 0 ? window.scrollY / total : 0
      setScrollProgress(progress)
    }

    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [setScrollProgress])

  return useLabStore((s) => s.scrollProgress)
}
