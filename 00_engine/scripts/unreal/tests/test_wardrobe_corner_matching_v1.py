import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("corner_match", Path(__file__).parents[1] / "wardrobe_corner_matching_v1.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def record(offset=0):
    return {"positions": [True, [offset, 0, 0], [offset+1, 0, 0], [offset, 1, 0]],
            "uv_0": [True, [0, 0], [1, 0], [0, 1]], "material": [0, True]}


def test_triangle_reorder():
    pairs, missing, extra = mod.match_corners([record(), record(5)], [record(5), record()])
    assert pairs == [(0, 1, 0), (1, 0, 0)] and not missing and not extra


def test_cyclic_rotation():
    r = record()
    for key in ("positions", "uv_0"):
        values = r[key][1:]
        r[key] = [True, *values[1:], values[0]]
    assert mod.match_corners([record()], [r])[0] == [(0, 0, 2)]


def test_position_change_and_duplicate_rejected():
    assert mod.match_corners([record()], [record(0.01)])[1:] == ([0], [0])
    assert mod.match_corners([record(), record()], [record()])[1] == [1]


def test_nonfinite_and_material_change_rejected():
    r = record()
    r["positions"][1][0] = float("nan")
    assert mod.match_corners([record()], [r])[1] == [0]
    r = record()
    r["material"][0] = 1
    assert mod.match_corners([record()], [r])[1] == [0]


def test_reversed_winding_rejected():
    r = record()
    for key in ("positions", "uv_0"):
        r[key][2], r[key][3] = r[key][3], r[key][2]
    assert mod.match_corners([record()], [r])[1:] == ([0], [0])
