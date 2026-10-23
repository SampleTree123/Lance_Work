"""Projection coverage for the adaptive reference camera, without Unreal."""
import importlib.util
import itertools
import math
from pathlib import Path

spec = importlib.util.spec_from_file_location('hair_reference_worker', Path(__file__).resolve().parents[1] / 'ue_dataset_reference_v11.py')
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)


def test_long_hair_moves_camera_back_and_both_views_keep_all_corners():
    head = [0., 0., 160.]
    short = [{'center': [0., 0., 174.], 'extent': [12., 11., 12.]}]
    long = [{'center': [0., -5., 150.], 'extent': [20., 15., 38.]}]
    near = worker.adaptive_hair_framing(head, short, 'front', 1024, 1024)
    far = worker.adaptive_hair_framing(head, long, 'front', 1024, 1024)
    assert near['camera_distance_cm'] < far['camera_distance_cm']
    for view in ('front', 'back'):
        pose = worker.adaptive_hair_framing(head, long, view, 1024, 1024)
        assert pose['camera_distance_cm'] == far['camera_distance_cm']
        camera = pose['position']
        tangent = math.tan(math.radians(pose['horizontal_fov_degrees'] / 2))
        for box in long:
            for signs in itertools.product((-1, 1), repeat=3):
                point = [box['center'][k] + signs[k] * box['extent'][k] for k in range(3)]
                depth = camera[1] - point[1] if view == 'front' else point[1] - camera[1]
                assert depth > 0
                assert abs(point[0] - camera[0]) < depth * tangent
                assert abs(point[2] - camera[2]) < depth * tangent
