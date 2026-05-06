/* Hero Section — WebGL Chromatic Sine-Wave Shader
   Converted from React/Three.js to Vanilla JS
   Original: RawShaderMaterial with chromatic aberration */
(function() {
  var canvas = document.getElementById('heroParticles');
  if (!canvas || typeof THREE === 'undefined') return;

  var hero = canvas.parentElement;
  var W = hero.offsetWidth;
  var H = hero.offsetHeight;

  /* ── Scene Setup ── */
  var scene = new THREE.Scene();
  var camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, -1);
  var renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: false });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setClearColor(new THREE.Color(0x000000), 0);

  /* ── Uniforms ── */
  var uniforms = {
    resolution: { value: [W, H] },
    time:       { value: 0.0 },
    xScale:     { value: 1.0 },
    yScale:     { value: 0.5 },
    distortion: { value: 0.05 }
  };

  /* ── Vertex Shader ── */
  var vertexShader = [
    'attribute vec3 position;',
    'void main() {',
    '  gl_Position = vec4(position, 1.0);',
    '}'
  ].join('\n');

  /* ── Fragment Shader (Chromatic Sine-Wave + Navy/Blue palette) ── */
  var fragmentShader = [
    'precision highp float;',
    'uniform vec2 resolution;',
    'uniform float time;',
    'uniform float xScale;',
    'uniform float yScale;',
    'uniform float distortion;',
    '',
    'void main() {',
    '  vec2 p = (gl_FragCoord.xy * 2.0 - resolution) / min(resolution.x, resolution.y);',
    '  float d = length(p) * distortion;',
    '',
    '  float rx = p.x * (1.0 + d);',
    '  float gx = p.x;',
    '  float bx = p.x * (1.0 - d);',
    '',
    '  float r = 0.05 / abs(p.y + sin((rx + time) * xScale) * yScale);',
    '  float g = 0.05 / abs(p.y + sin((gx + time) * xScale) * yScale);',
    '  float b = 0.05 / abs(p.y + sin((bx + time) * xScale) * yScale);',
    '',
    '  /* Navy-Blue-Teal palette shift */',
    '  float finalR = r * 0.024 + g * 0.12 + b * 0.02;',
    '  float finalG = r * 0.075 + g * 0.32 + b * 0.40;',
    '  float finalB = r * 0.29 + g * 0.65 + b * 0.96;',
    '',
    '  float alpha = clamp((finalR + finalG + finalB) * 0.5, 0.0, 0.35);',
    '  gl_FragColor = vec4(finalR, finalG, finalB, alpha);',
    '}'
  ].join('\n');

  /* ── Fullscreen Quad ── */
  var positions = new Float32Array([
    -1.0, -1.0, 0.0,
     1.0, -1.0, 0.0,
    -1.0,  1.0, 0.0,
     1.0, -1.0, 0.0,
    -1.0,  1.0, 0.0,
     1.0,  1.0, 0.0
  ]);

  var geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

  var material = new THREE.RawShaderMaterial({
    vertexShader: vertexShader,
    fragmentShader: fragmentShader,
    uniforms: uniforms,
    side: THREE.DoubleSide,
    transparent: true,
    blending: THREE.AdditiveBlending,
    depthWrite: false
  });

  var mesh = new THREE.Mesh(geometry, material);
  scene.add(mesh);

  /* ── Resize ── */
  function handleResize() {
    W = hero.offsetWidth;
    H = hero.offsetHeight;
    renderer.setSize(W, H, false);
    uniforms.resolution.value = [W, H];
  }
  handleResize();

  /* ── Animation Loop ── */
  function animate() {
    uniforms.time.value += 0.01;
    renderer.render(scene, camera);
    requestAnimationFrame(animate);
  }
  animate();

  window.addEventListener('resize', handleResize);
})();
