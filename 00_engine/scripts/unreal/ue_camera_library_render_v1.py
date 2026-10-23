"""Root-injected expansion rendering using the established isolated MRQ runner.

Owner: SCENE_CAMERA_SEQUENCE.md section 8. Importing never accesses Unreal.
"""
from pathlib import Path
import importlib.util
import json
import hashlib

S = Path(__file__).resolve().parent
RUN = S.parents[1] / 'outputs/unreal_character_import/camera_library_expansion_20261010_v1'
ASSET_ROOT = '/Game/DataMake/Validation/CameraLibraryExpansion20261010'


def engine():
    spec = importlib.util.spec_from_file_location('_library_render_engine', S/'ue_camera_pilot_render_v1.py')
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    result.RUN = RUN
    result.ASSET_ROOT = ASSET_ROOT
    result.LIVE_ATTRIBUTE = '_dm_camera_library_render_v1'
    return result


def start(u, attempt_id, shot_ids=None):
    manifest = json.loads((RUN/'prepared_jobs_v1.json').read_text(encoding='utf-8'))
    if manifest.get('success') is not True:
        raise ValueError('Preparation has not passed')
    pin = manifest['plan']
    if hashlib.sha256(Path(pin['path']).read_bytes()).hexdigest() != pin['sha256']:
        raise ValueError('Prepared plan changed')
    for receipt in manifest['sequence_receipts']:
        if hashlib.sha256(Path(receipt['path']).read_bytes()).hexdigest() != receipt['sha256']:
            raise ValueError('Prepared receipt changed')
    jobs = manifest['jobs']
    if shot_ids is not None:
        wanted = set(shot_ids)
        jobs = [j for j in jobs if j['shot_id'] in wanted]
        if {j['shot_id'] for j in jobs} != wanted:
            raise ValueError('Unknown render shot')
    return engine().start_render(u, jobs, attempt_id, width=1280, height=720, spatial_samples=1)


def status(u):
    return engine().status(u)
