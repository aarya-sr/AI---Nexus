import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { useLabStore } from '../../store/labState'
import laboratoryVoidShader from '../../shaders/laboratoryVoid.glsl'

const vertexShader = `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = vec4(position, 1.0);
  }
`

export function LaboratoryVoid() {
  const meshRef = useRef<THREE.Mesh>(null)
  const scrollProgress = useLabStore((s) => s.scrollProgress)
  const concentration = useLabStore((s) => s.formaldehydeConcentration)

  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uScrollOffset: { value: 0 },
      uConcentration: { value: 0.5 },
      uResolution: { value: new THREE.Vector2(window.innerWidth, window.innerHeight) },
    }),
    []
  )

  useFrame((_, delta) => {
    if (meshRef.current) {
      const material = meshRef.current.material as THREE.ShaderMaterial
      material.uniforms.uTime.value += delta
      material.uniforms.uScrollOffset.value = scrollProgress
      material.uniforms.uConcentration.value = concentration
    }
  })

  return (
    <mesh ref={meshRef} frustumCulled={false}>
      <planeGeometry args={[2, 2]} />
      <shaderMaterial
        vertexShader={vertexShader}
        fragmentShader={laboratoryVoidShader}
        uniforms={uniforms}
        depthWrite={false}
        depthTest={false}
      />
    </mesh>
  )
}
