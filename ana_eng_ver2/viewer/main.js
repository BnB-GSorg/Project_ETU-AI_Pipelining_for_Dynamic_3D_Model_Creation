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

// ── mmi-git state ──
let gitMode = false;             // true when loaded scene is mmi-git format
let gitData = null;              // raw git-format JSON
let gitBasePositions = {};       // part_id → Float32Array (base positions, frame 0)
let gitBaseColors = {};          // part_id → Float32Array (base colors, optional)
let gitCurrentPositions = {};    // part_id → Float32Array (current positions)
let gitCurrentFrame = -1;        // last frame we resolved to
let gitCommits = [];             // sorted commits [{t, transforms: {part_id: [16]}}]
let gitKeyframes = [];           // periodic snapshots [{t, parts: {part_id: [x,y,z,...]}}]
let gitParts = [];               // [{id, label, point_indices, color}]

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
  // Reset git state
  gitMode = false;
  gitData = null;
  gitBasePositions = {};
  gitBaseColors = {};
  gitCurrentPositions = {};
  gitCurrentFrame = -1;
  gitCommits = [];
  gitKeyframes = [];
  gitParts = [];
}

// ---------------------------------------------------------------------------
// mmi-git support — base + commit-chain rendering
// ---------------------------------------------------------------------------
function _m4fromArray(a) {
  const m = new THREE.Matrix4();
  m.fromArray(a);
  return m;
}

function _mat16_to_flat(mat16) {
  // mat16 is row-major [m00..m03, m10..m13, m20..m23, m30..m33]
  // Three.js Matrix4.fromArray expects column-major
  const m = new THREE.Matrix4();
  m.set(
    mat16[0], mat16[4], mat16[8],  mat16[12],
    mat16[1], mat16[5], mat16[9],  mat16[13],
    mat16[2], mat16[6], mat16[10], mat16[14],
    mat16[3], mat16[7], mat16[11], mat16[15]
  );
  return m;
}

function buildGitScene(data) {
  disposeCurrent();
  gitMode = true;
  gitData = data;
  duration = data.meta.duration_frames;
  fps = data.meta.fps || 10;

  gitBasePositions = {};
  gitBaseColors = {};
  gitCurrentPositions = {};
  gitCommits = (data.commits || []).slice().sort((a, b) => a.t - b.t);
  gitKeyframes = (data.keyframes || []).slice().sort((a, b) => a.t - b.t);
  gitParts = data.parts || [];
  gitCurrentFrame = -1;

  const allPoints = data.base?.points ? new Float32Array(data.base.points) : new Float32Array(0);
  const allColors = data.base?.colors ? new Float32Array(data.base.colors) : null;

  // Build per-part meshes, dispatching by geometry kind
  for (const part of gitParts) {
    const geom = part.geometry || {};
    const kind = geom.kind || "pointcloud";

    if (kind === "pointcloud") {
      // ── Pointcloud (legacy + explicit) ──
      const indices = part.point_indices || [];
      const nPts = indices.length;
      if (nPts === 0) continue;
      const positions = new Float32Array(nPts * 3);
      const colors = allColors ? new Float32Array(nPts * 3) : null;

      for (let i = 0; i < nPts; i++) {
        const srcIdx = indices[i] * 3;
        const dstIdx = i * 3;
        positions[dstIdx] = allPoints[srcIdx];
        positions[dstIdx + 1] = allPoints[srcIdx + 1];
        positions[dstIdx + 2] = allPoints[srcIdx + 2];
        if (colors) {
          colors[dstIdx] = allColors[srcIdx];
          colors[dstIdx + 1] = allColors[srcIdx + 1];
          colors[dstIdx + 2] = allColors[srcIdx + 2];
        }
      }

      gitBasePositions[part.id] = new Float32Array(positions);
      if (colors) gitBaseColors[part.id] = new Float32Array(colors);

      const g = new THREE.BufferGeometry();
      g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(positions), 3));
      if (colors) g.setAttribute("color", new THREE.BufferAttribute(new Float32Array(colors), 3));

      const mat = new THREE.PointsMaterial({
        size: geom.point_size || 0.03,
        vertexColors: !!colors,
        color: colors ? 0xffffff : new THREE.Color(part.color || "#8ab4ff"),
        clippingPlanes: [slicePlane],
      });

      const mesh = new THREE.Points(g, mat);
      mesh.name = part.id;
      scene.add(mesh);
      objects.push({
        id: part.id, mesh, track: [], layer: part.id,
        layerVisible: true, morph: null, _isPointCloud: true,
      });

    } else if (kind === "box") {
      // ── Box geometry ──
      const [sx, sy, sz] = geom.size || [1, 1, 1];
      const faceColors = geom.face_colors || {};
      const g = new THREE.BoxGeometry(sx, sy, sz);
      const mats = FACE_ORDER.map(
        (f) =>
          new THREE.MeshStandardMaterial({
            color: new THREE.Color(faceColors[f] || "#161616"),
            roughness: 0.45,
            metalness: 0.05,
            clippingPlanes: [slicePlane],
            clipShadows: true,
          })
      );
      const mesh = new THREE.Mesh(g, mats);
      mesh.name = part.id;
      scene.add(mesh);
      objects.push({
        id: part.id, mesh, track: [], layer: part.id,
        layerVisible: true, morph: null, _isPointCloud: false,
      });

    } else if (kind === "surface") {
      // ── Surface geometry ──
      const rows = geom.rows || 2;
      const cols = geom.cols || 2;
      const positions = new Float32Array(geom.positions || []);
      const surfColors = geom.colors ? new Float32Array(geom.colors) : null;
      const hasColors = !!surfColors;

      const g = new THREE.BufferGeometry();
      g.setAttribute("position", new THREE.BufferAttribute(positions, 3));
      if (hasColors) g.setAttribute("color", new THREE.BufferAttribute(surfColors, 3));
      g.setIndex(surfaceIndices(rows, cols));
      g.computeVertexNormals();

      const mat = new THREE.MeshBasicMaterial({
        color: hasColors ? 0xffffff : new THREE.Color(geom.color || part.color || "#5b8cff"),
        vertexColors: hasColors,
        side: THREE.DoubleSide,
        wireframe: !!geom.wireframe,
        transparent: (geom.opacity ?? 1) < 1,
        opacity: geom.opacity ?? 1,
        clippingPlanes: [slicePlane],
      });
      const mesh = new THREE.Mesh(g, mat);
      mesh.name = part.id;
      scene.add(mesh);
      objects.push({
        id: part.id, mesh, track: [], layer: part.id,
        layerVisible: true, morph: null, _isPointCloud: false,
      });

    } else if (kind === "line") {
      // ── Line geometry ──
      const positions = new Float32Array(geom.positions || []);
      const g = new THREE.BufferGeometry();
      g.setAttribute("position", new THREE.BufferAttribute(positions, 3));
      const mat = new THREE.LineBasicMaterial({
        color: new THREE.Color(geom.color || part.color || "#5b8cff"),
        linewidth: geom.width || 2,
        clippingPlanes: [slicePlane],
      });
      const mesh = new THREE.Line(g, mat);
      mesh.name = part.id;
      scene.add(mesh);
      objects.push({
        id: part.id, mesh, track: [], layer: part.id,
        layerVisible: true, morph: null, _isPointCloud: false,
      });
    }
  }

  document.getElementById("title").textContent = data.meta.title || "MMI-git scene";
  document.getElementById("sub").textContent =
    `${gitParts.length} parts · ${duration} frames · ${fps} fps · source: ${data.meta.source || "?"} · git-format`;
  timeSlider.max = String(duration - 1);
  buildLayerControls(data.layers || []);
  frame = 0;
  seekGitToFrame(0);
}

function seekGitToFrame(targetFrame) {
  if (!gitMode) return;
  targetFrame = Math.max(0, Math.min(duration - 1, Math.round(targetFrame)));
  frame = targetFrame;

  // 1. Find nearest keyframe at or before target
  let startT = -1;
  let startParts = null;
  for (const kf of gitKeyframes) {
    if (kf.t <= targetFrame && kf.t > startT) {
      startT = kf.t;
      startParts = kf.parts;
    }
  }

  // 2. Initialize per-part state
  const current = {};         // Float32Array positions (pointcloud only)
  const cumulative = {};      // THREE.Matrix4 accumulated transform (non-pointcloud)
  const identity = new THREE.Matrix4();

  for (const part of gitParts) {
    const obj = objects.find(o => o.id === part.id);
    if (!obj) continue;

    if (obj._isPointCloud) {
      // Pointcloud: initialize positions from keyframe or base
      if (startParts && startParts[part.id]) {
        current[part.id] = new Float32Array(startParts[part.id]);
      } else {
        current[part.id] = new Float32Array(gitBasePositions[part.id] || []);
      }
    } else {
      // Non-pointcloud: start with identity transform
      cumulative[part.id] = new THREE.Matrix4();
      // If this part first appears at a keyframe after frame 0, we still
      // start from identity — the commit chain captures the full motion.
    }
  }

  // 3. Apply commits from (startT+1) to targetFrame
  for (const commit of gitCommits) {
    if (commit.t <= startT) continue;
    if (commit.t > targetFrame) break;

    for (const [partId, mat16] of Object.entries(commit.transforms)) {
      const obj = objects.find(o => o.id === partId);
      if (!obj) continue;

      const M = _mat16_to_flat(mat16);

      if (obj._isPointCloud) {
        // Pointcloud: transform every vertex
        if (!current[partId]) continue;
        const pts = current[partId];
        const v = new THREE.Vector3();
        for (let i = 0; i < pts.length; i += 3) {
          v.set(pts[i], pts[i + 1], pts[i + 2]);
          v.applyMatrix4(M);
          pts[i] = v.x;
          pts[i + 1] = v.y;
          pts[i + 2] = v.z;
        }
      } else {
        // Box / surface / line: accumulate transform
        if (!cumulative[partId]) cumulative[partId] = new THREE.Matrix4();
        cumulative[partId].multiplyMatrices(M, cumulative[partId]);
      }
    }
  }

  // 4. Update meshes
  for (const part of gitParts) {
    const obj = objects.find(o => o.id === part.id);
    if (!obj) continue;

    if (obj._isPointCloud) {
      // Update point cloud vertex buffer
      const posAttr = obj.mesh.geometry.getAttribute("position");
      if (current[part.id]) {
        posAttr.array.set(current[part.id]);
        posAttr.needsUpdate = true;
        gitCurrentPositions[part.id] = current[part.id];
      }
    } else {
      // Decompose accumulated matrix → position / quaternion / scale
      const m = cumulative[part.id] || identity;
      const pos = new THREE.Vector3();
      const quat = new THREE.Quaternion();
      const scl = new THREE.Vector3();
      m.decompose(pos, quat, scl);
      obj.mesh.position.copy(pos);
      obj.mesh.quaternion.copy(quat);
      obj.mesh.scale.copy(scl);
    }
  }

  gitCurrentFrame = targetFrame;

  // Update UI
  timeSlider.value = String(frame);
  frameLabel.textContent = `${frame} / ${duration - 1}  ·  ${(frame / fps).toFixed(2)}s`;
  updateGitHud();
}

function updateGitHud() {
  const events = gitData?.meta?.events || [];
  let cur = null;
  for (const e of events) if (e.t <= frame) cur = e;
  hud.firstChild.textContent = cur ? cur.label : gitData?.meta?.title || "—";
  hudSub.textContent = `frame ${frame} · ${(frame / fps).toFixed(2)}s · ${gitParts.length} parts`;
}

// ── end mmi-git ────────────────────────────────────────────────────────

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
  // Detect format and route
  if (data.format === "mmi-git") {
    buildGitScene(data);
    return;
  }
  gitMode = false;

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
  if (gitMode) {
    seekGitToFrame(t);
    return;
  }
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
  ['split_auto.json', '★ LIVE: split.mp4 → 3D (change-driven sampling)'],
  ['synthetic_git.mmi', '★ mmi-git: synthetic 3-part rotating cloud'],
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
