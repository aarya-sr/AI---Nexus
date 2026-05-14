// Laboratory Void — fragment shader
// Organic simplex noise, green-tinted, vignette

uniform float uTime;
uniform float uScrollOffset;
uniform float uConcentration;
uniform vec2 uResolution;

varying vec2 vUv;

#include "biologicalNoise.glsl"

void main() {
  vec2 uv = vUv;
  vec2 center = uv - 0.5;

  // Organic noise layers
  float noise1 = snoise(vec3(uv * 3.0, uTime * 0.08 + uScrollOffset * 0.5));
  float noise2 = snoise(vec3(uv * 6.0, uTime * 0.12 + 100.0));
  float noise3 = snoise(vec3(uv * 12.0, uTime * 0.04 + 200.0));

  float combined = noise1 * 0.5 + noise2 * 0.3 + noise3 * 0.2;

  // Base color: near-black with organic green undertone
  vec3 baseColor = vec3(0.04, 0.05, 0.03);
  vec3 greenTint = vec3(0.02, 0.08, 0.01) * uConcentration;

  // Noise-driven color variation
  vec3 color = baseColor + greenTint * (combined * 0.5 + 0.5);

  // Formaldehyde wisps — bright spots
  float wisps = smoothstep(0.4, 0.8, combined);
  color += vec3(0.01, 0.04, 0.005) * wisps;

  // Vignette — light from below (lightbox effect)
  float vignette = 1.0 - length(center * vec2(1.2, 1.6));
  vignette = smoothstep(0.0, 0.7, vignette);

  // Bottom glow (lightbox under specimen)
  float bottomGlow = smoothstep(1.0, 0.3, uv.y);
  color += vec3(0.01, 0.03, 0.005) * bottomGlow * 0.5;

  color *= vignette;

  gl_FragColor = vec4(color, 1.0);
}
