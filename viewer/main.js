// MMI viewer — loads an mmi-lite scene and plays it back interactively.
// Pure ES modules, no build step. Three.js comes from the importmap in index.html.

import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const FACE_ORDER = ["px", "nx", "py", "ny", "pz", "nz"]; // matches BoxGeometry material index order

// ---------------------------------------------------------------------------
// renderer / scene / camera
// ---------------------------------------------------------------------------
const stage = document.getElementById("stage");
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.localClippingEnabled = true;
stage.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0e0f13);

const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
const HOME_CAM = new THREE.Vector3(5.2, 4.2, 6.2);
camera.position.copy(HOME_CAM);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;

scene.add(new THREE.HemisphereLight(0xffffff, 0x223044, 1.1));
const key = new THREE.DirectionalLight(0xffffff, 1.6);
key.position.set(6, 10, 7);
scene.add(key);

const grid = new THREE.GridHelper(12, 12, 0x3a3f4b, 0x23262f);
grid.position.y = -2.2;
scene.add(grid);

const slicePlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
let sliceEnabled = false;

// ---------------------------------------------------------------------------
// state
// ---------------------------------------------------------------------------
let sceneData = null;
let objects = []; // { id, mesh, track, layer }
let annotations = []; // { sprite, t, t_end }
let duration = 1;
let fps = 30;
let frame = 0;
let playing = false;
let speed = 1;
let acc = 0;
let lastTs = 0;

// reusable temporaries for pose interpolation (avoid per-frame allocation)
const _qa = new THREE.Quaternion();
const _qb = new THREE.Quaternion();

const hud = document.getElementById("hud");
const hudSub = document.getElementById("hudSub");
const timeSlider = document.getElementById("time");
const frameLabel = document.getElementById("frameLabel");
const playBtn = document.getElementById("playBtn");

// ---------------------------------------------------------------------------
// scene construction
// ---------------------------------------------------------------------------
function disposeCurrent() {
  for (const o of objects) {
    scene.remove(o.mesh);
    o.mesh.geometry.dispose();
    (Array.isArray(o.mesh.material) ? o.mesh.material : [o.mesh.material]).forEach((m) => m.dispose());
  }
  for (const a of annotations) {
    scene.remove(a.sprite);
    a.sprite.material.map?.dispose();
    a.sprite.material.dispose();
  }
  objects = [];
  annotations = [];
}

// Each builder returns { mesh, morph }. morph is null for static geometry, else
// { frames:[{t,pos:Float32Array,col?:Float32Array}], hasColors }.
function buildGeometry(geo) {
  switch (geo.kind) {
    case "pointcloud": return makePointCloudMesh(geo);
    case "line": return makeLineMesh(geo);
    case "surface": return makeSurfaceMesh(geo);
    default: return { mesh: makeBoxMesh(geo), morph: null };
  }
}

function normalizeFrames(frames) {
  return frames
    .map((f) => ({
      t: f.t,
      pos: new Float32Array(f.points || f.positions),
      col: f.colors ? new Float32Array(f.colors) : null,
    }))
    .sort((a, b) => a.t - b.t);
}

function makeBoxMesh(geo) {
  const [sx, sy, sz] = geo.size;
  const g = new THREE.BoxGeometry(sx, sy, sz);
  const mats = FACE_ORDER.map(
    (f) =>
      new THREE.MeshStandardMaterial({
        color: new THREE.Color(geo.face_colors[f] || "#161616"),
        roughness: 0.45,
        metalness: 0.05,
        clippingPlanes: [slicePlane],
        clipShadows: true,
      })
  );
  return new THREE.Mesh(g, mats);
}

function makePointCloudMesh(geo) {
  const frames = geo.frames ? normalizeFrames(geo.frames) : null;
  const basePos = frames ? frames[0].pos : new Float32Array(geo.points);
  const baseCol = frames ? frames[0].col : geo.colors ? new Float32Array(geo.colors) : null;
  const hasColors = !!baseCol;

  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(basePos.slice(), 3));
  const mat = new THREE.PointsMaterial({ size: geo.point_size || 0.02, clippingPlanes: [slicePlane] });
  if (hasColors) {
    g.setAttribute("color", new THREE.BufferAttribute(baseCol.slice(), 3));
    mat.vertexColors = true;
  } else {
    mat.color = new THREE.Color(0x9bd1ff);
  }
  return { mesh: new THREE.Points(g, mat), morph: frames ? { frames, hasColors } : null };
}

function makeLineMesh(geo) {
  const frames = geo.frames ? normalizeFrames(geo.frames) : null;
  const base = frames ? frames[0].pos : new Float32Array(geo.points);
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(base.slice(), 3));
  const mat = new THREE.LineBasicMaterial({
    color: new THREE.Color(geo.color || "#5b8cff"),
    linewidth: geo.width || 1,
    clippingPlanes: [slicePlane],
  });
  return { mesh: new THREE.Line(g, mat), morph: frames ? { frames, hasColors: false } : null };
}

function surfaceIndices(rows, cols) {
  const idx = [];
  for (let r = 0; r < rows - 1; r++) {
    for (let c = 0; c < cols - 1; c++) {
      const a = r * cols + c, b = a + 1, d = a + cols, e = d + 1;
      idx.push(a, d, b, b, d, e);
    }
  }
  return idx;
}

function makeSurfaceMesh(geo) {
  const frames = geo.frames ? normalizeFrames(geo.frames) : null;
  const basePos = frames ? frames[0].pos : new Float32Array(geo.positions);
  const baseCol = frames ? frames[0].col : geo.colors ? new Float32Array(geo.colors) : null;
  const hasColors = !!baseCol;

  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(basePos.slice(), 3));
  if (hasColors) g.setAttribute("color", new THREE.BufferAttribute(baseCol.slice(), 3));
  g.setIndex(surfaceIndices(geo.rows, geo.cols));
  g.computeVertexNormals();

  const mat = new THREE.MeshBasicMaterial({
    color: hasColors ? 0xffffff : new THREE.Color(geo.color || "#5b8cff"),
    vertexColors: hasColors,
    side: THREE.DoubleSide,
    wireframe: !!geo.wireframe,
    transparent: (geo.opacity ?? 1) < 1,
    opacity: geo.opacity ?? 1,
    clippingPlanes: [slicePlane],
  });
  return { mesh: new THREE.Mesh(g, mat), morph: frames ? { frames, hasColors } : null };
}

// Interpolate a morphing object's vertex buffers to the given frame.
function applyMorph(o, frame) {
  const fr = o.morph.frames;
  let a = fr[0], b = fr[0];
  for (let i = 0; i < fr.length; i++) {
    if (fr[i].t <= frame) { a = fr[i]; b = fr[Math.min(i + 1, fr.length - 1)]; }
  }
  let alpha = b.t > a.t ? (frame - a.t) / (b.t - a.t) : 0;
  alpha = Math.min(1, Math.max(0, alpha));

  const pos = o.mesh.geometry.getAttribute("position");
  const p = pos.array;
  for (let i = 0; i < p.length; i++) p[i] = a.pos[i] + (b.pos[i] - a.pos[i]) * alpha;
  pos.needsUpdate = true;

  if (o.morph.hasColors && a.col && b.col) {
    const col = o.mesh.geometry.getAttribute("color");
    const c = col.array;
    for (let i = 0; i < c.length; i++) c[i] = a.col[i] + (b.col[i] - a.col[i]) * alpha;
    col.needsUpdate = true;
  }
}

function makeLabel(text) {
  const pad = 24, font = 64;
  const c = document.createElement("canvas");
  const ctx = c.getContext("2d");
  ctx.font = `700 ${font}px ui-sans-serif, system-ui, sans-serif`;
  c.width = ctx.measureText(text).width + pad * 2;
  c.height = font + pad * 2;
  ctx.font = `700 ${font}px ui-sans-serif, system-ui, sans-serif`;
  ctx.fillStyle = "rgba(20,22,28,.85)";
  roundRect(ctx, 0, 0, c.width, c.height, 18);
  ctx.fill();
  ctx.fillStyle = "#5b8cff";
  ctx.textBaseline = "middle";
  ctx.fillText(text, pad, c.height / 2);
  const tex = new THREE.CanvasTexture(c);
  tex.anisotropy = 4;
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthTest: false }));
  sprite.scale.set((c.width / c.height) * 0.6, 0.6, 1);
  return sprite;
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

function buildScene(data) {
  disposeCurrent();
  sceneData = data;
  duration = data.meta.duration_frames;
  fps = data.meta.fps || 30;

  for (const od of data.objects) {
    const { mesh, morph } = buildGeometry(od.geometry);
    scene.add(mesh);
    objects.push({ id: od.id, mesh, track: od.track, layer: od.layer || "default", morph, layerVisible: true });
  }
  for (const ad of data.annotations || []) {
    const sprite = makeLabel(ad.text);
    sprite.position.fromArray(ad.position);
    sprite.visible = false;
    scene.add(sprite);
    annotations.push({ sprite, t: ad.t, t_end: ad.t_end ?? ad.t + 6 });
  }

  document.getElementById("title").textContent = data.meta.title || "MMI scene";
  document.getElementById("sub").textContent =
    `${data.objects.length} objects · ${duration} frames · ${fps} fps · source: ${data.meta.source || "?"}`;
  timeSlider.max = String(duration - 1);
  buildLayerControls(data.layers || []);
  frame = 0;
  applyFrame(0);
}

// Find the two keyframes bracketing frame t and the interpolation factor between
// them. Pose is then *computed* between sparse (event) keyframes rather than
// snapping — the "calculate the in-between" half of keyframes-at-change.
function bracket(track, t) {
  let lo = 0, hi = track.length - 1, best = 0;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (track[mid].t <= t) { best = mid; lo = mid + 1; } else { hi = mid - 1; }
  }
  const a = track[best];
  const b = track[Math.min(best + 1, track.length - 1)];
  const alpha = b.t > a.t ? Math.min(1, Math.max(0, (t - a.t) / (b.t - a.t))) : 0;
  return { a, b, alpha };
}

const _lerp = (x, y, s) => x + (y - x) * s;

// Opacity drives object lifetime. Unlike pose (step-held), opacity is linearly
// interpolated between keyframes so objects fade in/out smoothly; a keyframe
// without an explicit opacity is treated as fully opaque.
function opacityAt(track, t) {
  let prev = track[0], next = track[track.length - 1];
  for (let i = 0; i < track.length; i++) {
    if (track[i].t <= t) { prev = track[i]; next = track[Math.min(i + 1, track.length - 1)]; }
  }
  const op = (k) => (k.opacity === undefined || k.opacity === null ? 1 : k.opacity);
  if (next.t <= prev.t) return op(prev);
  const a = Math.min(1, Math.max(0, (t - prev.t) / (next.t - prev.t)));
  return op(prev) + (op(next) - op(prev)) * a;
}

// Apply an opacity to a mesh's material(s). Visibility (layer toggle ∧ lifetime)
// is owned by applyFrame; this only sets the material blend state.
function setMeshOpacity(mesh, opacity) {
  const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
  for (const m of mats) {
    m.transparent = opacity < 0.999;
    m.opacity = opacity;
    m.depthWrite = opacity >= 0.999;
  }
}

function applyFrame(t) {
  frame = Math.max(0, Math.min(duration - 1, Math.round(t)));
  for (const o of objects) {
    const { a, b, alpha } = bracket(o.track, frame);
    // position (lerp)
    o.mesh.position.set(
      _lerp(a.position[0], b.position[0], alpha),
      _lerp(a.position[1], b.position[1], alpha),
      _lerp(a.position[2], b.position[2], alpha));
    // rotation (slerp) — quaternion defaults to identity when absent
    _qa.fromArray(a.quaternion || [0, 0, 0, 1]);
    _qb.fromArray(b.quaternion || [0, 0, 0, 1]);
    o.mesh.quaternion.copy(_qa).slerp(_qb, alpha);
    // scale (lerp) — defaults to unit when absent
    const sa = a.scale || [1, 1, 1], sb = b.scale || [1, 1, 1];
    o.mesh.scale.set(_lerp(sa[0], sb[0], alpha), _lerp(sa[1], sb[1], alpha), _lerp(sa[2], sb[2], alpha));
    if (o.morph) applyMorph(o, frame);
    const opacity = opacityAt(o.track, frame);
    setMeshOpacity(o.mesh, opacity);
    o.mesh.visible = o.layerVisible && opacity > 0.004; // layer toggle ∧ alive
  }
  const showAnn = document.getElementById("annToggle").checked;
  for (const a of annotations) a.sprite.visible = showAnn && frame >= a.t && frame <= a.t_end;

  timeSlider.value = String(frame);
  frameLabel.textContent = `${frame} / ${duration - 1}  ·  ${(frame / fps).toFixed(2)}s`;
  updateHud();
}

function updateHud() {
  const events = sceneData?.meta?.events || [];
  let cur = null;
  for (const e of events) if (e.t <= frame) cur = e;
  hud.firstChild.textContent = cur ? cur.label : sceneData?.meta?.title || "—";
  hudSub.textContent = `frame ${frame} · ${(frame / fps).toFixed(2)}s`;
}

// ---------------------------------------------------------------------------
// controls wiring
// ---------------------------------------------------------------------------
function buildLayerControls(layers) {
  const host = document.getElementById("layers");
  host.innerHTML = "";
  for (const l of layers) {
    const row = document.createElement("div");
    row.className = "row";
    const sw = `<span class="swatch" style="background:${l.color}"></span>`;
    row.innerHTML = `<label>${sw} ${l.name}</label>`;
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.checked = l.visible !== false;
    cb.addEventListener("change", () => {
      for (const o of objects) if (o.layer === l.id) o.layerVisible = cb.checked;
      applyFrame(frame); // re-evaluate visibility (layer ∧ lifetime)
    });
    row.appendChild(cb);
    host.appendChild(row);
  }
}

playBtn.addEventListener("click", () => setPlaying(!playing));
timeSlider.addEventListener("input", () => { setPlaying(false); applyFrame(+timeSlider.value); });
document.getElementById("speed").addEventListener("change", (e) => (speed = +e.target.value));
document.getElementById("annToggle").addEventListener("change", () => applyFrame(frame));
document.getElementById("gridToggle").addEventListener("change", (e) => (grid.visible = e.target.checked));
document.getElementById("resetCam").addEventListener("click", () => {
  camera.position.copy(HOME_CAM);
  controls.target.set(0, 0, 0);
});

const sliceAxis = document.getElementById("sliceAxis");
const slicePos = document.getElementById("slicePos");
const sliceFlip = document.getElementById("sliceFlip");
function updateSlice() {
  // Three.js keeps fragments where dot(normal, point) + constant >= 0.
  const axis = +sliceAxis.value;
  sliceEnabled = axis >= 0;
  const pos = +slicePos.value;
  const n = [0, 0, 0];
  if (!sliceEnabled) {
    // No clipping: any normal with a huge constant keeps everything.
    slicePlane.normal.set(1, 0, 0);
    slicePlane.constant = 1e9;
    return;
  }
  if (sliceFlip.checked) {
    n[axis] = 1; // keep the half where coord >= pos
    slicePlane.normal.set(n[0], n[1], n[2]);
    slicePlane.constant = -pos;
  } else {
    n[axis] = -1; // keep the half where coord <= pos
    slicePlane.normal.set(n[0], n[1], n[2]);
    slicePlane.constant = pos;
  }
}
[sliceAxis, slicePos, sliceFlip].forEach((el) => el.addEventListener("input", updateSlice));

document.getElementById("loadBtn").addEventListener("click", () => document.getElementById("fileInput").click());
document.getElementById("fileInput").addEventListener("change", (e) => {
  const f = e.target.files[0];
  if (f) loadFromFile(f);
});

// drag & drop
const drop = document.getElementById("drop");
window.addEventListener("dragover", (e) => { e.preventDefault(); drop.style.display = "flex"; });
drop.addEventListener("dragleave", () => (drop.style.display = "none"));
window.addEventListener("drop", (e) => {
  e.preventDefault();
  drop.style.display = "none";
  if (e.dataTransfer.files[0]) loadFromFile(e.dataTransfer.files[0]);
});

window.addEventListener("keydown", (e) => {
  if (e.code === "Space") { e.preventDefault(); setPlaying(!playing); }
  else if (e.code === "ArrowRight") { setPlaying(false); applyFrame(frame + 1); }
  else if (e.code === "ArrowLeft") { setPlaying(false); applyFrame(frame - 1); }
});

function setPlaying(v) {
  playing = v;
  playBtn.textContent = v ? "❚❚" : "▶";
  if (v && frame >= duration - 1) frame = 0;
}

function loadFromFile(file) {
  const r = new FileReader();
  r.onload = () => {
    try { buildScene(JSON.parse(r.result)); }
    catch (err) { alert("Failed to parse scene: " + err.message); }
  };
  r.readAsText(file);
}

// ---------------------------------------------------------------------------
// resize + loop
// ---------------------------------------------------------------------------
function resize() {
  const w = stage.clientWidth, h = stage.clientHeight;
  if (!w || !h) return; // stage not laid out yet (avoids NaN aspect / 0-size buffer)
  // updateStyle defaults to true: keep the canvas's CSS size == its drawing buffer.
  // (Passing false here while pixelRatio>1 and no CSS sizing makes the canvas render
  // at 2× the stage, pushing the scene off-screen — the viewport then looks black.)
  renderer.setSize(w, h);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(stage);
resize();

function tick(ts) {
  const dt = lastTs ? (ts - lastTs) / 1000 : 0;
  lastTs = ts;
  if (playing) {
    acc += dt * fps * speed;
    if (acc >= 1) {
      let next = frame + Math.floor(acc);
      acc -= Math.floor(acc);
      if (next >= duration - 1) {
        if (document.getElementById("loop").checked) next = 0;
        else { next = duration - 1; setPlaying(false); }
      }
      applyFrame(next);
    }
  }
  controls.update();
  renderer.render(scene, camera);
  requestAnimationFrame(tick);
}
requestAnimationFrame(tick);

// ---------------------------------------------------------------------------
// scene picker + initial load (works over http; drag/drop fallback on file://)
// ---------------------------------------------------------------------------
const SAMPLES = [
  ["complex_surface.json", "Complex f(z) → 3D landscape"],
  ["graph_surface.json", "Surface z = f(x,y)"],
  ["fourier_stack.json", "Fourier: square wave decomposed"],
  ["taylor_series.json", "Taylor series approximation"],
  ["vector_field.json", "3D vector field"],
  ["linear_transform.json", "Linear transform (matrix action)"],
  ["parametric_surface.json", "Parametric surface (torus…)"],
  ["rubiks.json", "Rubik's cube (3D process)"],
  ["lifetime_demo.json", "Lifetime demo — collide & merge (fade/hide)"],
  ["orbit_auto.json", "★ LIVE: orbit.mp4 → 3D (Gemini general engine)"],
  ["split_auto.json", "★ LIVE: split.mp4 → 3D (change-driven sampling)"],
];

const sceneSelect = document.getElementById("sceneSelect");
for (const [file, label] of SAMPLES) {
  const opt = document.createElement("option");
  opt.value = file;
  opt.textContent = label;
  sceneSelect.appendChild(opt);
}

function loadSample(file) {
  fetch(`../data/samples/${file}`)
    .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then((data) => { buildScene(data); setPlaying(true); })
    .catch(() => {
      hudSub.textContent = "couldn't fetch sample — run scripts/serve.py, or drag a .json in";
    });
}

sceneSelect.addEventListener("change", () => loadSample(sceneSelect.value));

updateSlice();
loadSample(SAMPLES[0][0]);
