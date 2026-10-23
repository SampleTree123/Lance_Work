"""Match render triangles by UVs and position, independent of build reordering."""
from collections import defaultdict
import math


def canonical_uv(record):
    uv = record["uv_0"][1:]
    return min(tuple(x for v in uv[i:] + uv[:i] for x in v) for i in range(3))


def match_corners(left, right, position_tolerance=1e-4):
    groups = defaultdict(list)
    for index, record in enumerate(right):
        groups[(tuple(record["material"]), canonical_uv(record))].append(index)
    used, matches, missing = set(), [], []
    for i, record in enumerate(left):
        candidates = groups.get((tuple(record["material"]), canonical_uv(record)), [])
        best = None
        for j in candidates:
            if j in used:
                continue
            other = right[j]
            for rotation in range(3):
                uv = other["uv_0"][1:]
                if record["uv_0"][1:] != uv[rotation:] + uv[:rotation]:
                    continue
                positions = other["positions"][1:]
                rotated = positions[rotation:] + positions[:rotation]
                deltas = [abs(a-b) for p, q in zip(record["positions"][1:], rotated)
                          for a, b in zip(p, q)]
                if not all(math.isfinite(d) for d in deltas):
                    continue
                delta = max(deltas)
                if delta <= position_tolerance and (best is None or delta < best[0]):
                    best = (delta, j, rotation)
        if best is None:
            missing.append(i)
        else:
            used.add(best[1])
            matches.append((i, best[1], best[2]))
    return matches, missing, sorted(set(range(len(right))) - used)
