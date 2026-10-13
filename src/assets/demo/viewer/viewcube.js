// A view box: a small cube that mirrors the camera's orientation. Click a face
// to fly to that side of the model, drag it to rotate the view, or press Home
// to return to the default angle.
//
// The maths (orientationFor, cssMatrix, rotateView) is kept separate from the
// DOM code so it can be checked without a browser.

// Relative so the maths can be checked under plain Node (viewcube.test.mjs);
// the import map in index.html resolves the same file for main.js.
import * as THREE from './three.module.js';

const SIZE = 60;   // edge length of the cube in CSS pixels

// Where the camera sits relative to the target, and which way is up on screen.
// The scene is Y-up with +Z as "front". Top and bottom need an explicit up
// vector because looking straight along Y leaves "up" ambiguous: top puts the
// back of the model at the top of the screen, as CAD packages do.
export const VIEWS = {
  front:  { dir: [0, 0, 1],       up: [0, 1, 0] },
  back:   { dir: [0, 0, -1],      up: [0, 1, 0] },
  right:  { dir: [1, 0, 0],       up: [0, 1, 0] },
  left:   { dir: [-1, 0, 0],      up: [0, 1, 0] },
  top:    { dir: [0, 1, 0],       up: [0, 0, -1] },
  bottom: { dir: [0, -1, 0],      up: [0, 0, 1] },
  home:   { dir: [0.7, 0.6, 1],   up: [0, 1, 0] },
};

// Edge and corner views, so the cube snaps to the full CAD set, not just the
// six faces. An edge direction has one zero component, a corner has none;
// none of them point straight along Y, so world-up is always a valid up.
export const EDGES = {
  frontRight:  [1, 0, 1],
  frontLeft:   [-1, 0, 1],
  backRight:   [1, 0, -1],
  backLeft:    [-1, 0, -1],
  topFront:    [0, 1, 1],
  topBack:     [0, 1, -1],
  bottomFront: [0, -1, 1],
  bottomBack:  [0, -1, -1],
  rightTop:    [1, 1, 0],
  rightBottom: [1, -1, 0],
  leftTop:     [-1, 1, 0],
  leftBottom:  [-1, -1, 0],
};

export const CORNERS = {
  frontRightTop:    [1, 1, 1],
  frontRightBottom: [1, -1, 1],
  frontLeftTop:     [-1, 1, 1],
  frontLeftBottom:  [-1, -1, 1],
  backRightTop:     [1, 1, -1],
  backRightBottom:  [1, -1, -1],
  backLeftTop:      [-1, 1, -1],
  backLeftBottom:   [-1, -1, -1],
};

for (const [name, dir] of [...Object.entries(EDGES), ...Object.entries(CORNERS)]) {
  VIEWS[name] = { dir, up: [0, 1, 0] };
}

// Each face sits half a cube out from the centre along its own axis. CSS has
// +Y pointing down, so the world-up face is the one rotated about X by +90.
const FACES = {
  front:  { label: 'Front',  place: 'translateZ(H)' },
  back:   { label: 'Back',   place: 'rotateY(180deg) translateZ(H)' },
  right:  { label: 'Right',  place: 'rotateY(90deg) translateZ(H)' },
  left:   { label: 'Left',   place: 'rotateY(-90deg) translateZ(H)' },
  top:    { label: 'Top',    place: 'rotateX(90deg) translateZ(H)' },
  bottom: { label: 'Bottom', place: 'rotateX(-90deg) translateZ(H)' },
};

/** The camera orientation that looks at the target from the named side. */
export function orientationFor(name) {
  const view = VIEWS[name];
  const m = new THREE.Matrix4().lookAt(
    new THREE.Vector3(...view.dir).normalize(),
    new THREE.Vector3(),
    new THREE.Vector3(...view.up));
  return new THREE.Quaternion().setFromRotationMatrix(m);
}

/**
 * The CSS transform that makes the cube show the same side the camera sees.
 *
 * The cube's local frame is the world frame with Y flipped (CSS grows
 * downward), so the world-to-view rotation R becomes S R S with S = diag(1,-1,1).
 * CSS matrix3d is column-major.
 */
export function cssMatrix(cameraQuaternion) {
  const r = new THREE.Matrix4().makeRotationFromQuaternion(cameraQuaternion.clone().invert()).elements;
  const s = [1, -1, 1];
  const out = [];
  for (let col = 0; col < 3; col++) {
    for (let row = 0; row < 3; row++) out.push(s[row] * s[col] * r[col * 4 + row]);
    out.push(0);
  }
  out.push(0, 0, 0, 1);
  return `matrix3d(${out.map((n) => n.toFixed(5)).join(',')})`;
}

/**
 * Turn the model by dragging: right drags the near side rightwards, down drags
 * the top towards you. That is the camera moving the opposite way around the
 * target, about its own up and right axes, so there are no poles to get stuck at.
 */
export function rotateView(camera, target, dx, dy, radiansPerPixel = 0.005) {
  const up = new THREE.Vector3(0, 1, 0).applyQuaternion(camera.quaternion);
  const right = new THREE.Vector3(1, 0, 0).applyQuaternion(camera.quaternion);
  const turn = new THREE.Quaternion()
    .setFromAxisAngle(up, -dx * radiansPerPixel)
    .multiply(new THREE.Quaternion().setFromAxisAngle(right, -dy * radiansPerPixel));

  const offset = camera.position.clone().sub(target).applyQuaternion(turn);
  camera.position.copy(target).add(offset);
  camera.up.copy(up.applyQuaternion(turn));
}

const el = (tag, cls, text) => {
  const node = document.createElement(tag);
  node.className = cls;
  if (text) node.textContent = text;
  return node;
};

// CSS grows +Y downward, so a world direction [x, y, z] becomes [x, -y, z].
const handlePlace = (dir) => {
  const [x, y, z] = dir;
  const h = SIZE / 2;
  return `translate3d(${x * h}px, ${-y * h}px, ${z * h}px)`;
};

/**
 * Build the view box inside `container`.
 *
 * Call animate(now) before controls.update() and sync() after it: animation
 * moves the camera, the controls turn that into an orientation, and only then
 * does the cube have the right orientation to copy.
 */
export function createViewCube(container, camera, controls) {
  const stage = el('div', 'vc-stage');
  const cube = el('div', 'vc-cube');
  cube.style.width = cube.style.height = `${SIZE}px`;

  for (const [name, face] of Object.entries(FACES)) {
    const node = el('div', 'vc-face', face.label);
    node.dataset.view = name;
    node.style.transform = face.place.replace('H', `${SIZE / 2}px`);
    cube.appendChild(node);
  }
  const handles = [];
  const addHandles = (views, extra) => {
    for (const [name, dir] of Object.entries(views)) {
      const node = el('div', `vc-handle ${extra}`);
      node.dataset.view = name;
      node.title = name;
      node.style.transform = handlePlace(dir);
      cube.appendChild(node);
      handles.push({ node, dir });
    }
  };
  addHandles(EDGES, 'vc-edge');
  addHandles(CORNERS, 'vc-corner');
  stage.appendChild(cube);

  const home = el('button', 'vc-home', 'Home');
  home.type = 'button';
  container.replaceChildren(stage, home);

  let flight = null;

  function flyTo(name, ms = 450) {
    flight = {
      from: camera.quaternion.clone(),
      to: orientationFor(name),
      distance: Math.max(camera.position.distanceTo(controls.target), 1e-6),
      start: null,
      ms,
    };
  }

  function animate(now) {
    if (!flight) return;
    if (flight.start === null) flight.start = now;
    const u = Math.min((now - flight.start) / flight.ms, 1);
    const eased = u * u * (3 - 2 * u);
    const q = new THREE.Quaternion().slerpQuaternions(flight.from, flight.to, eased);
    camera.position.copy(controls.target).add(new THREE.Vector3(0, 0, flight.distance).applyQuaternion(q));
    camera.up.set(0, 1, 0).applyQuaternion(q);
    if (u >= 1) flight = null;
  }

  const cancel = () => { flight = null; };

  const tmp = new THREE.Vector3();
  function sync() {
    cube.style.transform = cssMatrix(camera.quaternion);
    // Show a handle only on the side facing the camera. The dir vectors use a
    // Y-up model frame, but the cube's CSS transform renders Y-down, so flip Y
    // before rotating by the (inverted) camera quaternion into world space.
    const cam = new THREE.Vector3().subVectors(camera.position, controls.target);
    const q = camera.quaternion.clone().invert();
    for (const h of handles) {
      tmp.set(h.dir[0], -h.dir[1], h.dir[2]).applyQuaternion(q);
      h.node.style.visibility = tmp.dot(cam) > 0 ? 'visible' : 'hidden';
    }
  }

  // A press that barely moves is a click on a face; anything more is a drag.
  let press = null;
  stage.addEventListener('pointerdown', (e) => {
    cancel();
    press = { x: e.clientX, y: e.clientY, lastX: e.clientX, lastY: e.clientY,
              view: e.target.dataset.view, dragged: false };
    stage.setPointerCapture(e.pointerId);
  });
  stage.addEventListener('pointermove', (e) => {
    if (!press) return;
    if (!press.dragged && Math.hypot(e.clientX - press.x, e.clientY - press.y) < 4) return;
    press.dragged = true;
    rotateView(camera, controls.target, e.clientX - press.lastX, e.clientY - press.lastY);
    press.lastX = e.clientX;
    press.lastY = e.clientY;
  });
  stage.addEventListener('pointerup', () => {
    if (press && !press.dragged && press.view) flyTo(press.view);
    press = null;
  });
  stage.addEventListener('pointercancel', () => { press = null; });
  home.addEventListener('click', () => flyTo('home'));

  sync();
  return { animate, sync, cancel, flyTo };
}
