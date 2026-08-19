import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const $ = (id) => document.getElementById(id);

// ---------------------------------------------------------------- three setup

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
document.body.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x111317);
const camera = new THREE.PerspectiveCamera(45, 1, 0.01, 5000);
camera.position.set(6, 5, 8);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;

scene.add(new THREE.HemisphereLight(0xffffff, 0x223344, 1.1));
const sun = new THREE.DirectionalLight(0xffffff, 1.3);
sun.position.set(5, 9, 7);
scene.add(sun);

function resize() {
  renderer.setSize(window.innerWidth, window.innerHeight);
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
}
window.addEventListener('resize', resize);
resize();

// ------------------------------------------------------------------- geometry

const hex = (c, fallback = 0xcccccc) =>
  new THREE.Color(typeof c === 'string' ? c : fallback);

const BOX_FACE_ORDER = ['px', 'nx', 'py', 'ny', 'pz', 'nz'];

function makeBox(g) {
  const [x = 1, y = 1, z = 1] = g.size || [];
  const geo = new THREE.BoxGeometry(x, y, z);
  const base = hex(g.color);
  // BoxGeometry material slots are ordered +x,-x,+y,-y,+z,-z, so a six-material
  // array indexed by BOX_FACE_ORDER lines up without any remapping.
  const mats = g.face_colors
    ? BOX_FACE_ORDER.map((f) =>
        new THREE.MeshStandardMaterial({ color: hex(g.face_colors[f], base.getHex()), roughness: 0.5 }))
    : new THREE.MeshStandardMaterial({ color: base, roughness: 0.5 });
  return new THREE.Mesh(geo, mats);
}

function positionsOf(points) {
  return new THREE.BufferAttribute(new Float32Array(points || []), 3);
}

function makePointCloud(g) {
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', positionsOf(g.points));
  const hasColors = Array.isArray(g.colors) && g.colors.length;
  if (hasColors) geo.setAttribute('color', new THREE.BufferAttribute(new Float32Array(g.colors), 3));
  return new THREE.Points(geo, new THREE.PointsMaterial({
    size: g.point_size ?? 0.02,
    color: hasColors ? 0xffffff : hex(g.color),
    vertexColors: hasColors,
  }));
}

function makeLine(g) {
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', positionsOf(g.points));
  // linewidth is ignored by most WebGL drivers; kept so the scene still reads it.
  return new THREE.Line(geo, new THREE.LineBasicMaterial({ color: hex(g.color), linewidth: g.width ?? 1 }));
}

function makeSurface(g) {
  const rows = g.rows | 0, cols = g.cols | 0;
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', positionsOf(g.vertices));
  const hasColors = Array.isArray(g.colors) && g.colors.length;
  if (hasColors) geo.setAttribute('color', new THREE.BufferAttribute(new Float32Array(g.colors), 3));
  const idx = [];
  for (let r = 0; r < rows - 1; r++) {
    for (let c = 0; c < cols - 1; c++) {
      const a = r * cols + c;
      idx.push(a, a + cols, a + 1, a + 1, a + cols, a + cols + 1);
    }
  }
  geo.setIndex(idx);
  geo.computeVertexNormals();
  return new THREE.Mesh(geo, new THREE.MeshStandardMaterial({
    color: hasColors ? 0xffffff : hex(g.color),
    vertexColors: hasColors,
    side: THREE.DoubleSide,
    roughness: 0.6,
  }));
}

function buildObject(g) {
  switch (g && g.kind) {
    case 'box': return makeBox(g);
    case 'pointcloud': return makePointCloud(g);
    case 'line': return makeLine(g);
    case 'surface': return makeSurface(g);
    default: return new THREE.Object3D();
  }
}

// ---------------------------------------------------------------------- state

let root = null;                 // holds every layer group of the current scene
let nodes = [];                  // { id, obj, mats, track }
let events = new Map();          // frame -> label
let git = null;                  // { commits, snaps } when format is mmi-git
let fps = 30, lastFrame = 0, frame = 0;
let playing = false, reverse = false;

const tmpM = new THREE.Matrix4();
const tmpPos = new THREE.Vector3();
const tmpQuat = new THREE.Quaternion();
const tmpScale = new THREE.Vector3();
const qa = new THREE.Quaternion(), qb = new THREE.Quaternion();

// -------------------------------------------------------------- mmi-lite path

const kfPos = (k) => k.position || [0, 0, 0];
const kfScale = (k) => k.scale || [1, 1, 1];
const kfQuat = (k) => k.quaternion || [0, 0, 0, 1];
const kfOpacity = (k) => (k.opacity ?? 1);
const lerp3 = (a, b, u, out) => out.set(
  a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u, a[2] + (b[2] - a[2]) * u);

// Keyframes are sparse, so every frame is interpolated and poses outside the
// track's range clamp to its first/last keyframe.
function sampleTrack(track, t, out) {
  if (!track || !track.length) return false;
  let i = 0;
  while (i < track.length - 1 && track[i + 1].t <= t) i++;
  const a = track[i];
  const b = (i + 1 < track.length && track[i + 1].t > t) ? track[i + 1] : null;
  const span = b ? b.t - a.t : 0;
  const u = (b && span > 0) ? Math.min(Math.max((t - a.t) / span, 0), 1) : 0;

  if (!b || u === 0) {
    out.position.fromArray(kfPos(a));
    out.quaternion.fromArray(kfQuat(a));
    out.scale.fromArray(kfScale(a));
    out.opacity = kfOpacity(a);
    return true;
  }
  lerp3(kfPos(a), kfPos(b), u, out.position);
  lerp3(kfScale(a), kfScale(b), u, out.scale);
  out.opacity = kfOpacity(a) + (kfOpacity(b) - kfOpacity(a)) * u;
  // slerpQuaternions already picks the shortest arc and degrades to a
  // normalized lerp for near-parallel inputs, which is exactly the spec.
  qa.fromArray(kfQuat(a));
  qb.fromArray(kfQuat(b));
  out.quaternion.slerpQuaternions(qa, qb, u);
  return true;
}

// --------------------------------------------------------------- mmi-git path

function poseMatrix(p, out) {
  return out.compose(
    tmpPos.fromArray(p && p.position ? p.position : [0, 0, 0]),
    tmpQuat.fromArray(p && p.quaternion ? p.quaternion : [0, 0, 0, 1]),
    tmpScale.fromArray(p && p.scale ? p.scale : [1, 1, 1]));
}

function applyCommit(state, commit, inverse) {
  const transforms = commit.transforms || {};
  for (const id in transforms) {
    const s = state.get(id);
    const m = transforms[id];
    if (!s || !Array.isArray(m) || m.length !== 16) continue;
    tmpM.set(...m);                          // JSON is row-major; set() is too
    if (inverse) tmpM.invert();
    s.m.multiply(tmpM);                      // local-frame: current on the left
  }
  if (!inverse && commit.opacity) {
    for (const id in commit.opacity) {
      const s = state.get(id);
      if (s) s.opacity = commit.opacity[id];
    }
  }
}

// Seeking anywhere must be cheap, so we jump to whichever snapshot is closest
// and either replay commits forward or undo them backward from there.
function gitDecode(t) {
  const state = new Map();
  let before = null;
  for (const s of git.snaps) if (s.t <= t) before = s;
  const after = git.snaps.find((s) => s.t >= t) || null;
  const rewind = !!after && (!before || (after.t - t) < (t - before.t));
  const from = rewind ? after : before;
  const poses = (from && from.poses) || git.basePoses;

  for (const node of nodes) {
    state.set(node.id, {
      m: poseMatrix(poses[node.id], new THREE.Matrix4()),
      opacity: poses[node.id] ? (poses[node.id].opacity ?? 1) : 1,
    });
  }

  const lo = before ? before.t : -Infinity;
  if (rewind) {
    for (let i = git.commits.length - 1; i >= 0; i--) {
      const c = git.commits[i];
      if (c.t > lo && c.t <= after.t && c.t > t) applyCommit(state, c, true);
    }
  } else {
    for (const c of git.commits) {
      if (c.t > lo && c.t <= t) applyCommit(state, c, false);
    }
  }
  return state;
}

// ------------------------------------------------------------------ animation

function setOpacity(mats, o) {
  for (const m of mats) {
    m.transparent = o < 1;
    m.opacity = o;
    m.depthWrite = o >= 1;
  }
}

const litePose = { position: new THREE.Vector3(), quaternion: new THREE.Quaternion(),
                   scale: new THREE.Vector3(1, 1, 1), opacity: 1 };

function applyFrame(t) {
  if (git) {
    const state = gitDecode(t);
    for (const node of nodes) {
      const s = state.get(node.id);
      if (!s) continue;
      s.m.decompose(node.obj.position, node.obj.quaternion, node.obj.scale);
      setOpacity(node.mats, s.opacity);
    }
  } else {
    for (const node of nodes) {
      if (!sampleTrack(node.track, t, litePose)) continue;
      node.obj.position.copy(litePose.position);
      node.obj.quaternion.copy(litePose.quaternion);
      node.obj.scale.copy(litePose.scale);
      setOpacity(node.mats, litePose.opacity);
    }
  }
  $('counter').textContent = `frame ${t} / ${lastFrame}`;
  $('event').textContent = events.get(t) || '';
  $('seek').value = t;
}

function setFrame(t) {
  frame = Math.min(Math.max(Math.round(t), 0), lastFrame);
  applyFrame(frame);
}

let clockPrev = performance.now(), accum = 0;
function tick(now) {
  requestAnimationFrame(tick);
  const dt = (now - clockPrev) / 1000;
  clockPrev = now;
  if (playing && lastFrame > 0) {
    accum += dt * fps;
    const steps = Math.floor(accum);
    if (steps) {
      accum -= steps;
      let next = frame + (reverse ? -steps : steps);
      if (next > lastFrame) next -= lastFrame + 1;      // loop in both directions
      if (next < 0) next += lastFrame + 1;
      setFrame(next);
    }
  }
  controls.update();
  renderer.render(scene, camera);
}
requestAnimationFrame(tick);

// --------------------------------------------------------------------- loading

function disposeScene() {
  if (!root) return;
  root.traverse((o) => {
    if (o.geometry) o.geometry.dispose();
    const m = o.material;
    if (m) (Array.isArray(m) ? m : [m]).forEach((x) => x.dispose());
  });
  scene.remove(root);
  root = null;
}

function frameCamera() {
  const box = new THREE.Box3().setFromObject(root);
  if (box.isEmpty()) return;
  const size = box.getSize(new THREE.Vector3()).length() || 1;
  const center = box.getCenter(new THREE.Vector3());
  controls.target.copy(center);
  camera.position.copy(center).add(new THREE.Vector3(0.7, 0.6, 1).normalize().multiplyScalar(size * 1.4));
  camera.near = size / 200;
  camera.far = size * 50;
  camera.updateProjectionMatrix();
}

function buildLayerUI(layers, used) {
  const host = $('layers');
  host.textContent = '';
  for (const id of used) {
    const def = layers.find((l) => l.id === id) || {};
    const label = document.createElement('label');
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.checked = true;
    cb.onchange = () => { root.getObjectByName(`layer:${id}`).visible = cb.checked; };
    const sw = document.createElement('span');
    sw.className = 'swatch';
    sw.style.background = def.color || '#666';
    const text = document.createElement('span');
    text.textContent = def.name || id;
    label.append(cb, sw, text);
    host.append(label);
  }
}

function showMedia(media) {
  const panel = $('media');
  panel.textContent = '';
  panel.style.display = 'none';
  if (!media) return;
  if (media.video) {
    const v = document.createElement('video');
    v.src = media.video;
    v.controls = true;
    panel.append(v);
  } else if (media.poster) {
    const img = document.createElement('img');
    img.src = media.poster;
    panel.append(img);
  }
  if (panel.childElementCount) panel.style.display = 'block';
}

function loadScene(doc) {
  disposeScene();
  root = new THREE.Group();
  scene.add(root);
  nodes = [];
  git = null;

  const meta = doc.meta || {};
  const parts = doc.format === 'mmi-git'
    ? ((doc.base && doc.base.parts) || [])
    : (doc.objects || []);

  const groups = new Map();
  const used = [];
  for (const part of parts) {
    const layerId = part.layer || 'default';
    if (!groups.has(layerId)) {
      const g = new THREE.Group();
      g.name = `layer:${layerId}`;
      groups.set(layerId, g);
      root.add(g);
      used.push(layerId);
    }
    const obj = buildObject(part.geometry);
    obj.name = part.id;
    groups.get(layerId).add(obj);
    const m = obj.material;
    nodes.push({
      id: part.id,
      obj,
      mats: m ? (Array.isArray(m) ? m : [m]) : [],
      track: part.track ? part.track.slice().sort((a, b) => a.t - b.t) : null,
    });
  }

  if (doc.format === 'mmi-git') {
    const snaps = (doc.keyframes || []).slice();
    if (doc.final) snaps.push(doc.final);
    snaps.sort((a, b) => a.t - b.t);
    git = {
      snaps,
      commits: (doc.commits || []).slice().sort((a, b) => a.t - b.t),
      // Where the parts sit before any commit runs. Without this a scrambled
      // model would start stacked at the origin instead of assembled.
      basePoses: (doc.base && doc.base.poses) || {},
    };
  }

  fps = meta.fps || 30;
  let maxT = (meta.duration_frames || 1) - 1;
  const seen = git
    ? git.snaps.concat(git.commits)
    : nodes.flatMap((n) => n.track || []);
  for (const k of seen) maxT = Math.max(maxT, k.t || 0);
  lastFrame = Math.max(maxT, 0);

  events = new Map((meta.events || []).map((e) => [e.t, e.label]));
  $('title').textContent = meta.title || 'untitled scene';
  $('seek').max = lastFrame;
  buildLayerUI(doc.layers || [], used);
  showMedia(doc.media);
  $('hint').style.display = 'none';
  setFrame(0);
  frameCamera();          // after posing, so the bounds are the real ones
}

function loadText(text) {
  try {
    loadScene(JSON.parse(text));
  } catch (err) {
    $('title').textContent = `load failed: ${err.message}`;
  }
}

// ------------------------------------------------------------------------- UI

function setPlaying(on) {
  playing = on;
  accum = 0;
  $('play').textContent = on ? 'Pause' : 'Play';
  $('play').classList.toggle('on', on);
}

$('play').onclick = () => setPlaying(!playing);
$('rev').onclick = () => {
  reverse = !reverse;
  $('rev').classList.toggle('on', reverse);
};
$('seek').oninput = (e) => { setPlaying(false); setFrame(+e.target.value); };
$('file').onchange = (e) => {
  const f = e.target.files[0];
  if (f) f.text().then(loadText);
};

window.addEventListener('keydown', (e) => {
  if (e.target.tagName === 'INPUT' && e.target.type !== 'range') return;
  if (e.code === 'Space') { e.preventDefault(); setPlaying(!playing); }
  // preventDefault keeps a focused slider from also stepping itself.
  else if (e.code === 'ArrowLeft') { e.preventDefault(); setPlaying(false); setFrame(frame - 1); }
  else if (e.code === 'ArrowRight') { e.preventDefault(); setPlaying(false); setFrame(frame + 1); }
});

window.addEventListener('dragover', (e) => e.preventDefault());
window.addEventListener('drop', (e) => {
  e.preventDefault();
  const f = e.dataTransfer.files[0];
  if (f) f.text().then(loadText);
});

const wanted = new URLSearchParams(location.search).get('file');
if (wanted) {
  fetch(wanted)
    .then((r) => { if (!r.ok) throw new Error(`${r.status} ${wanted}`); return r.text(); })
    .then(loadText)
    .catch((err) => { $('title').textContent = `load failed: ${err.message}`; });
}
