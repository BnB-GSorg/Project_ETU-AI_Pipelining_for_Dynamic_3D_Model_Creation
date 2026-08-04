"""Download Three.js files locally so the viewer works offline / without CDN."""
import urllib.request
import os

output_dir = os.path.join(os.path.dirname(__file__), 'threejs')
os.makedirs(output_dir, exist_ok=True)

files = {
    'three.module.js': 'https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js',
    'OrbitControls.js': 'https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/controls/OrbitControls.js',
    'OBJLoader.js': 'https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/loaders/OBJLoader.js',
}

for name, url in files.items():
    path = os.path.join(output_dir, name)
    try:
        urllib.request.urlretrieve(url, path)
        size_kb = os.path.getsize(path) / 1024
        print(f'OK: {name} ({size_kb:.0f} KB)')
    except Exception as e:
        print(f'FAIL: {name} - {e}')

print('Done.')
