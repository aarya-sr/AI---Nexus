// Fragment displacement vertex shader — surfaces bubble and breathe
uniform float uTime;
uniform float uIntensity;

varying vec2 vUv;
varying float vDisplacement;

#include "biologicalNoise.glsl"

void main() {
  vUv = uv;

  // Organic displacement
  float displacement = snoise(vec3(position * 2.0 + uTime * 0.3)) * 0.08 * uIntensity;
  displacement += snoise(vec3(position * 4.0 + uTime * 0.5)) * 0.03 * uIntensity;

  vDisplacement = displacement;

  vec3 newPosition = position + normal * displacement;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(newPosition, 1.0);
}
