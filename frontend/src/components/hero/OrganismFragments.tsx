import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { Text } from '@react-three/drei'
import { useLabStore } from '../../store/labState'
import fragmentDisplaceVert from '../../shaders/fragmentDisplace.vert'

const FRAGMENT_FRAG = `
  uniform float uTime;
  uniform vec3 uColor;
  uniform float uGlow;
  varying float vDisplacement;
  varying vec2 vUv;

  void main() {
    vec3 color = uColor * (0.4 + uGlow * 0.6);

    // Subtle edge highlight
    float fresnel = pow(1.0 - abs(dot(vec3(0.0, 0.0, 1.0), vec3(vUv - 0.5, 0.5))), 2.0);
    color += uColor * fresnel * 0.3;

    // Gentle pulse
    float pulse = sin(uTime * 1.5 + vUv.x * 3.14) * 0.1 + 0.9;
    color *= pulse;

    gl_FragColor = vec4(color, 0.75);
  }
`

const AGENTS = [
  { name: 'ELICITOR', position: [-2.2, 0.9, 0] as [number, number, number], color: '#22aa10' },
  { name: 'ARCHITECT', position: [0, 1.1, 0] as [number, number, number], color: '#22aa10' },
  { name: 'CRITIC', position: [2.2, 0.9, 0] as [number, number, number], color: '#8b0000' },
  { name: 'BUILDER', position: [-2.2, -0.9, 0] as [number, number, number], color: '#22aa10' },
  { name: 'TESTER', position: [0, -1.1, 0] as [number, number, number], color: '#cc8833' },
  { name: 'LEARNER', position: [2.2, -0.9, 0] as [number, number, number], color: '#22aa10' },
]

function OrganismFragment({
  name,
  basePosition,
  color,
  index,
}: {
  name: string
  basePosition: [number, number, number]
  color: string
  index: number
}) {
  const groupRef = useRef<THREE.Group>(null)
  const meshRef = useRef<THREE.Mesh>(null)
  const assemblyPhase = useLabStore((s) => s.assemblyPhase)
  const voltageIntensity = useLabStore((s) => s.voltageIntensity)
  const originalColor = useMemo(() => new THREE.Color(color), [color])

  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uIntensity: { value: 0.5 },
      uColor: { value: new THREE.Color(color) },
      uGlow: { value: 0.3 },
    }),
    [color]
  )

  useFrame((state, delta) => {
    if (!groupRef.current || !meshRef.current) return
    const mat = meshRef.current.material as THREE.ShaderMaterial
    mat.uniforms.uTime.value += delta
    mat.uniforms.uIntensity.value = voltageIntensity * 0.4

    const t = state.clock.elapsedTime

    if (assemblyPhase === 'idle' || assemblyPhase === 'orbiting') {
      // Gentle orbit
      groupRef.current.position.x =
        basePosition[0] + Math.sin(t * 0.4 + index * 1.047) * 0.15
      groupRef.current.position.y =
        basePosition[1] + Math.cos(t * 0.35 + index * 0.8) * 0.1
      groupRef.current.position.z =
        basePosition[2] + Math.sin(t * 0.25 + index * 0.5) * 0.08
      meshRef.current.rotation.x = Math.sin(t * 0.15 + index) * 0.08
      meshRef.current.rotation.y = t * 0.1 + index
      mat.uniforms.uGlow.value = 0.3
      mat.uniforms.uColor.value.copy(originalColor)
      groupRef.current.scale.setScalar(1)
    } else if (assemblyPhase === 'pulling') {
      groupRef.current.position.x = THREE.MathUtils.lerp(
        groupRef.current.position.x, 0, delta * 2.5
      )
      groupRef.current.position.y = THREE.MathUtils.lerp(
        groupRef.current.position.y, 0, delta * 2.5
      )
      groupRef.current.position.z = THREE.MathUtils.lerp(
        groupRef.current.position.z, 0, delta * 2.5
      )
    } else if (assemblyPhase === 'stitching') {
      // Tight cluster with vibration
      const radius = 0.15
      const angle = (index / AGENTS.length) * Math.PI * 2 + t * 8
      groupRef.current.position.x = Math.cos(angle) * radius
      groupRef.current.position.y = Math.sin(angle) * radius
      groupRef.current.position.z = 0
      mat.uniforms.uGlow.value = 0.6
    } else if (assemblyPhase === 'lightning') {
      groupRef.current.position.set(0, 0, 0)
      mat.uniforms.uGlow.value = 2.0
      mat.uniforms.uColor.value.setRGB(1, 1, 1)
    } else if (assemblyPhase === 'alive') {
      // Heartbeat — 72bpm
      const bpm = 72
      const beat = Math.sin(t * ((bpm / 60) * Math.PI * 2)) * 0.5 + 0.5
      const scale = 1.0 + beat * 0.015
      // Arrange in a compact cluster
      const radius = 0.2
      const angle = (index / AGENTS.length) * Math.PI * 2
      groupRef.current.position.x = Math.cos(angle) * radius
      groupRef.current.position.y = Math.sin(angle) * radius
      groupRef.current.position.z = 0
      groupRef.current.scale.setScalar(scale)
      mat.uniforms.uColor.value.copy(originalColor)
      mat.uniforms.uGlow.value = 0.35 + beat * 0.2
    }
  })

  const geometries: Record<string, React.JSX.Element> = {
    ELICITOR: <sphereGeometry args={[0.22, 24, 24]} />,
    ARCHITECT: <boxGeometry args={[0.35, 0.35, 0.35]} />,
    CRITIC: <octahedronGeometry args={[0.22]} />,
    BUILDER: <cylinderGeometry args={[0.18, 0.22, 0.35, 6]} />,
    TESTER: <dodecahedronGeometry args={[0.2]} />,
    LEARNER: <icosahedronGeometry args={[0.2]} />,
  }

  const showLabel = assemblyPhase === 'idle' || assemblyPhase === 'orbiting'

  return (
    <group ref={groupRef} position={basePosition}>
      <mesh ref={meshRef}>
        {geometries[name] || <sphereGeometry args={[0.2, 24, 24]} />}
        <shaderMaterial
          vertexShader={fragmentDisplaceVert}
          fragmentShader={FRAGMENT_FRAG}
          uniforms={uniforms}
          transparent
          side={THREE.DoubleSide}
        />
      </mesh>
      {showLabel && (
        <Text
          position={[0, -0.4, 0]}
          fontSize={0.09}
          font="https://fonts.gstatic.com/s/ibmplexmono/v19/-F63fjptAgt5VM-kVkqdyU8n5ig.woff2"
          color="#39ff14"
          anchorX="center"
          anchorY="top"
          letterSpacing={0.15}
        >
          {name}
        </Text>
      )}
    </group>
  )
}

export function OrganismFragments() {
  return (
    <group>
      {AGENTS.map((agent, i) => (
        <OrganismFragment
          key={agent.name}
          name={agent.name}
          basePosition={agent.position}
          color={agent.color}
          index={i}
        />
      ))}
    </group>
  )
}
