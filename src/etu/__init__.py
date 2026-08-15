"""Project ETU — lift flat 2D process videos into interactive 3D/4D scenes.

Two scene formats live under `etu.formats`: mmi-lite (per-object keyframe
tracks, human-readable) and mmi-git (initial model + commit chain of 4x4
deltas + final model). `etu.router` turns frames into one of them.
"""

__version__ = "0.2.0"
