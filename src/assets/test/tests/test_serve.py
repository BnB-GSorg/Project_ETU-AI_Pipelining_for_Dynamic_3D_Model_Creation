"""The local `serve` handler: the viewer's files and their MIME types.

The viewer loads Three.js as an ES module and the scene over `fetch`. Safari
refuses modules whose type is wrong, and the scene is JSON, so these checks pin
the mapping the viewer depends on — a regression here (or a missing vendored
Three.js file) fails the suite instead of silently breaking in a browser.
"""

from __future__ import annotations

import json
import threading
from http.server import ThreadingHTTPServer
from urllib.request import urlopen

import main

# The golden scene doubles as the file the deployed example plays, so it is the
# natural subject for the fetch test.
GOLDEN = "src/assets/test/golden/rubiks_solve.mmi"


def test_serve_extension_mapping():
    assert main.SERVE_EXTENSIONS[".mmi"] == "application/json"
    assert main.SERVE_EXTENSIONS[".js"] == "text/javascript"
    assert main.SERVE_EXTENSIONS[".mjs"] == "text/javascript"


def test_serve_delivers_scene_and_vendored_three():
    """A threaded server serves the .mmi as JSON and the vendored module as JS."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), main.ViewerHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        # The compiled scene, fetched the way main.js fetches it.
        with urlopen(f"{base}/{GOLDEN}") as resp:
            assert resp.status == 200
            assert resp.headers.get("Content-Type") == "application/json"
            doc = json.load(resp)
            assert doc["format"] == "mmi-git"

        # The vendored Three.js entry the import map points at.
        with urlopen(f"{base}/src/assets/demo/viewer/three.module.js") as resp:
            assert resp.status == 200
            assert resp.headers.get("Content-Type") == "text/javascript"

        # The viewer page itself, so the import map is reachable.
        with urlopen(f"{base}/src/assets/demo/viewer/") as resp:
            assert resp.status == 200
            body = resp.read().decode()
            assert '"./three.module.js"' in body
            assert '"three/addons/": "./addons/"' in body
    finally:
        server.shutdown()
        server.server_close()
