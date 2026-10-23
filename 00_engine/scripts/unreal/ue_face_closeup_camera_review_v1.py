"""Isolated face-camera adapter; coordinator is the only UE executor."""
from pathlib import Path
import importlib.util

S = Path(__file__).resolve().parent
RUN = S.parents[1] / 'outputs/camera_face_closeup_20261014_v1'
ASSETS = '/Game/DataMake/Validation/FaceCloseupCamera20261014'


def adapter():
    spec = importlib.util.spec_from_file_location('_face_camera_adapter', S / 'ue_all_motion_camera_review_v1.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.RUN, module.ASSETS = RUN, ASSETS
    original_adapter = module.adapter

    def face_adapter():
        result = original_adapter()
        original_configure = result.configured_module

        def configure(name):
            component = original_configure(name)
            if name == 'ue_motion_scene_render_v1':
                component.LIVE_ATTRIBUTE = '_dm_face_closeup_camera_20261014'
            return component

        result.configured_module = configure
        return result

    module.adapter = face_adapter
    return module


def prepare(u, ids, plan_sha256):
    return adapter().prepare(u, ids, plan_sha256)


def render(u, attempt, ids, width, height, plan_sha256):
    return adapter().render(u, attempt, ids, width, height, plan_sha256)


def status(u):
    return adapter().status(u)
