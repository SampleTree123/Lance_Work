"""Isolated common-preset review adapter. Owner: SCENE_CAMERA_SEQUENCE."""
from pathlib import Path
import importlib.util

S = Path(__file__).resolve().parent
RUN = S.parents[1] / 'outputs/camera_common_presets_20261014_v1'
ASSETS = '/Game/DataMake/Validation/CommonCameraPresets20261014'


def adapter():
    spec = importlib.util.spec_from_file_location('_common_camera_adapter', S / 'ue_camera_alignment_review_v1.py')
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    result.RUN = RUN
    result.ASSETS = ASSETS
    result.PLAN_NAME = 'camera_trial_plan_v2.json'
    original_configured = result.configured_module

    def configured(name):
        module = original_configured(name)
        if name == 'ue_motion_scene_render_v1':
            module.LIVE_ATTRIBUTE = '_dm_common_camera_render_20261014'
        return module

    result.configured_module = configured
    return result


def prepare(unreal, ids):
    return adapter().prepare(unreal, ids)


def render(unreal, attempt, ids, width, height):
    return adapter().render(unreal, attempt, ids, width=width, height=height)


def status(unreal):
    return adapter().status(unreal)
