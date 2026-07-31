"""Identity reconciliation — stitch a vision model's frame-to-frame ID drift.

Vision models tracking objects across sampled frames are fragile: the same "blue
ball" may be labelled `b1` in early frames and `b2` later (a *split*), or the same
object may be listed twice in one description (a *duplicate*). The lifter assumes
one id == one object, so a split shows up as two half-lived primitives and a
duplicate as z-fighting twins.

`reconcile` fixes this conservatively, using only what the FeatureGraph already
carries (shape, color, position, time) — no extra model calls:

* **split**: two objects of the same shape and near-identical color whose
  timelines are temporally disjoint and spatially continuous at the seam are the
  same object re-labelled → merge (union their timelines).
* **duplicate**: same shape/color and overlapping time with near-identical
  positions → merge (keep one).

It is deliberately cautious: distinct-colored objects are never merged, so the
two planets / the sun / the comet in a typical clip stay separate.
"""

from __future__ import annotations

from mmi.etu.understand.schema import FeatureGraph, FeatureObject

COLOR_TOL = 45.0    # max RGB euclidean distance (0..441) to be "the same color"
SEAM_TOL = 0.28     # max normalized gap between a split's seam endpoints
DUP_TOL = 0.10      # max mean normalized position gap to call two tracks duplicates


def _rgb(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    if len(c) != 6:
        return (128, 128, 128)
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _color_dist(a: str, b: str) -> float:
    return sum((x - y) ** 2 for x, y in zip(_rgb(a), _rgb(b))) ** 0.5


def _span(o: FeatureObject) -> tuple[int, int]:
    ts = [s.t for s in o.timeline]
    return (min(ts), max(ts)) if ts else (0, -1)


def _sorted(o: FeatureObject):
    return sorted(o.timeline, key=lambda s: s.t)


def _seam_dist(a: FeatureObject, b: FeatureObject) -> float:
    """Gap between the chronologically-adjacent endpoints; ∞ if they time-overlap."""
    (a0, a1), (b0, b1) = _span(a), _span(b)
    ax, bx = _sorted(a), _sorted(b)
    if a1 <= b0:
        s, e = ax[-1], bx[0]
    elif b1 <= a0:
        s, e = bx[-1], ax[0]
    else:
        return float("inf")
    return ((s.x - e.x) ** 2 + (s.y - e.y) ** 2) ** 0.5


def _dup_overlap_dist(a: FeatureObject, b: FeatureObject) -> float:
    """Mean position gap over shared timepoints; ∞ if they don't share any."""
    bm = {s.t: s for s in b.timeline}
    shared = [(s, bm[s.t]) for s in a.timeline if s.t in bm]
    if not shared:
        return float("inf")
    return sum(((p.x - q.x) ** 2 + (p.y - q.y) ** 2) ** 0.5 for p, q in shared) / len(shared)


def _same_object(a: FeatureObject, b: FeatureObject) -> bool:
    if a.shape != b.shape or _color_dist(a.color, b.color) > COLOR_TOL:
        return False
    return _seam_dist(a, b) <= SEAM_TOL or _dup_overlap_dist(a, b) <= DUP_TOL


def reconcile(fg: FeatureGraph) -> FeatureGraph:
    objs = [o for o in fg.objects if o.timeline]  # drop empty tracks
    n = len(objs)

    # union-find over "same object" pairs (transitive: 3 fragments collapse to 1)
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(n):
        for j in range(i + 1, n):
            if find(i) != find(j) and _same_object(objs[i], objs[j]):
                parent[find(i)] = find(j)

    groups: dict[int, list[FeatureObject]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(objs[i])

    merged: list[FeatureObject] = []
    for members in groups.values():
        if len(members) == 1:
            merged.append(members[0])
            continue
        members.sort(key=lambda o: _span(o)[0])
        base = members[0]  # earliest fragment keeps id/label/color
        states = {}
        for o in members:
            for s in o.timeline:
                states.setdefault(s.t, s)  # earlier fragment wins on conflicting t
        base.timeline = [states[t] for t in sorted(states)]
        merged.append(base)

    fg.objects = merged
    fg.duration = max(fg.duration, 1 + max((s.t for o in merged for s in o.timeline), default=0))
    return fg
