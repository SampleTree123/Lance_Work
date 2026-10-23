"""Root-only complete-angle review adapter. Owner: SCENE_CAMERA_SEQUENCE §10.

Reuse verified scene copying and isolated MRQ without modifying prior runs.
Importing does not connect to Unreal. Geometry status in this pilot means safe
trajectory; close-up coverage is diagnostic and remains subject to review.
"""
from pathlib import Path
import importlib.util

S = Path(__file__).resolve().parent
RUN = S.parents[1] / 'outputs/unreal_character_import/camera_complete_angles_20261010_v1'
ASSET_ROOT = '/Game/DataMake/Validation/CameraCompleteAngles20261010'


def module(name):
    spec = importlib.util.spec_from_file_location('_complete_angles_' + name, S / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def preparation():
    result = module('ue_camera_library_prepare_v1')
    result.R = RUN
    result.PLAN = RUN / 'expansion_plan_v1.json'
    result.A = ASSET_ROOT
    return result


def inputs():
    return preparation().inputs()


def prepare(u, selected_ids=None):
    return preparation().prepare(u, selected_ids)


def renderer():
    result = module('ue_camera_library_render_v1')
    result.RUN = RUN
    result.ASSET_ROOT = ASSET_ROOT
    old_engine = result.engine
    def isolated_engine():
        runner = old_engine()
        runner.LIVE_ATTRIBUTE = '_dm_complete_angles_render_v1'
        return runner
    result.engine = isolated_engine
    return result


def render(u, attempt, shot_ids=None):
    return renderer().start(u, attempt, shot_ids)


def encode(attempt):
    encoder = module('encode_camera_pilot_v1')
    encoder.RUN = RUN
    encoder.needs_dense_contact = lambda shot: True
    return encoder.process(attempt)
