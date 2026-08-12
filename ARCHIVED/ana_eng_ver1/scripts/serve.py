#!/usr/bin/env python3
"""Serve the repo root over HTTP so the viewer can fetch the sample scene.

    python scripts/serve.py        # then open http://localhost:8000/viewer/

(Opening viewer/index.html directly via file:// also works, but the auto-load
of the sample scene is blocked by browser CORS — use drag-and-drop there.)
"""

from __future__ import annotations

import http.server
import socketserver
import webbrowser
from pathlib import Path

PORT = 8000
ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    handler = lambda *a, **k: http.server.SimpleHTTPRequestHandler(*a, directory=str(ROOT), **k)
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        url = f"http://localhost:{PORT}/viewer/"
        print(f"serving {ROOT} at {url}  (Ctrl-C to stop)")
        try:
            webbrowser.open(url)
        except Exception:
            pass
        httpd.serve_forever()


if __name__ == "__main__":
    main()
