// View-cube maths, checked without a browser:  node viewcube.test.mjs
//
// viewcube.js imports the vendored three.module.js by relative path, so this
// runs with a plain `node` and no npm install (package.json only sets ESM).

import * as THREE from './three.module.js';
import * as vc from './viewcube.js';

let failures = 0;
const check = (name, ok, detail = '') => {
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  (${detail})` : ''}`);
  if (!ok) failures++;
};

check('VIEWS: 27 views (6 faces + home + 12 edges + 8 corners)',
  Object.keys(vc.VIEWS).length === 27, `${Object.keys(vc.VIEWS).length}`);
check('EDGES: 12 entries', Object.keys(vc.EDGES).length === 12);
check('CORNERS: 8 entries', Object.keys(vc.CORNERS).length === 8);

const zeros = (v) => v.filter((n) => n === 0).length;
check('edges have exactly one zero component',
  Object.values(vc.EDGES).every((d) => zeros(d) === 1));
check('corners have no zero component',
  Object.values(vc.CORNERS).every((d) => zeros(d) === 0));
check('edge/corner dirs never parallel to world-up',
  [...Object.values(vc.EDGES), ...Object.values(vc.CORNERS)]
    .every((d) => d[0] !== 0 || d[2] !== 0));

for (const name of Object.keys(vc.VIEWS)) {
  let q;
  try {
    q = vc.orientationFor(name);
  } catch (err) {
    check(`orientationFor('${name}') throws`, false, err.message);
    continue;
  }
  const n = Math.hypot(q.x, q.y, q.z, q.w);
  check(`orientationFor('${name}') quaternion normalised`,
    Math.abs(n - 1) < 1e-6, n.toFixed(9));
}

const m = vc.cssMatrix(vc.orientationFor('home'));
check('cssMatrix: matrix3d with 16 numbers',
  /^matrix3d\([-0-9.,]+\)$/.test(m) && m.split(',').length === 16,
  m.split(',').length);

{
  const camera = {
    position: new THREE.Vector3(0, 0, 10),
    quaternion: new THREE.Quaternion(),
    up: new THREE.Vector3(0, 1, 0),
  };
  const target = new THREE.Vector3();
  vc.rotateView(camera, target, 40, 0); // pure horizontal drag
  check('horizontal drag: up stays world-Y (no tilt)',
    Math.abs(camera.up.x) < 1e-9 && Math.abs(camera.up.y - 1) < 1e-9,
    `up=(${camera.up.x.toFixed(4)}, ${camera.up.y.toFixed(4)}, ${camera.up.z.toFixed(4)})`);
  vc.rotateView(camera, target, 0, 20); // then vertical
  check('vertical drag tilts the view',
    Math.abs(camera.up.z) > 0.01,
    `up=(${camera.up.x.toFixed(4)}, ${camera.up.y.toFixed(4)}, ${camera.up.z.toFixed(4)})`);
}

console.log(failures ? `\n${failures} FAILURE(S)` : '\nALL VIEWCUBE CHECKS PASSED');
process.exitCode = failures ? 1 : 0;
