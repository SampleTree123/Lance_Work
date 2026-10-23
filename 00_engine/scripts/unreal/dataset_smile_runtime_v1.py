"""Load prebuilt native smile clips; production never composes expressions."""
from pathlib import Path
import copy
import hashlib
import json
import math

WORKSPACE = Path(__file__).resolve().parents[3]
CATALOG = WORKSPACE / '00_engine/assets/character_creator/dataset_smile_v1.json'
VERSION = 1


def object_path(value):
    value = value if isinstance(value, str) else value.get_path_name()
    if not isinstance(value, str) or not value.startswith('/Game/'):
        raise ValueError('Smile animation must have a /Game asset path')
    return value if '.' in value else value + '.' + value.rsplit('/', 1)[-1]


def manifest_bytes():
    if not CATALOG.is_file():
        raise FileNotFoundError('Missing production smile catalog: ' + str(CATALOG))
    return CATALOG.read_bytes()


def manifest_digest():
    return hashlib.sha256(manifest_bytes()).hexdigest()


def resolve(sex, motion=None):
    raw = manifest_bytes()
    catalog = json.loads(raw.decode('utf-8-sig'))
    if catalog.get('face_id') != 'smile' or sex not in ('female', 'male'):
        raise ValueError('Invalid production smile catalog or character sex')
    source = object_path(motion) if motion is not None else None
    if source is None:
        row = catalog.get('static', {}).get(sex)
    else:
        matches = [r for r in catalog.get('motions', [])
                   if r.get('sex') == sex and object_path(r['source_animation']) == source]
        if len(matches) != 1:
            raise ValueError('Require one prebuilt smile for ' + sex + ': ' + source)
        row = matches[0]
    if not isinstance(row, dict) or not row.get('animation'):
        raise ValueError('Missing prebuilt static smile for ' + sex)
    return {**copy.deepcopy(row), 'animation': object_path(row['animation']),
            'source_animation': source, 'face_id': 'smile',
            'catalog_sha256': hashlib.sha256(raw).hexdigest()}


def apply(u, current, actor, selected, t, motion, *, body_action_id=None):
    if selected.get('face_id') != 'smile':
        raise ValueError('Production character presentation requires smile')
    if type(t) not in (int, float) or not math.isfinite(t) or t < 0:
        raise ValueError('Smile sample time must be finite and nonnegative')
    row = resolve(selected['sex'], motion)
    clip = u.load_asset(row['animation'])
    if not isinstance(clip, u.AnimSequence):
        raise RuntimeError('Missing prebuilt production smile animation: ' + row['animation'])
    if motion is not None and clip.get_skeleton() != motion.get_skeleton():
        raise ValueError('Prebuilt smile and source motion skeletons differ')
    duration = float(clip.get_play_length())
    if (not math.isfinite(duration) or duration <= 0 or t > duration + 1e-5
            or ('duration_seconds' in row and not math.isclose(duration, float(row['duration_seconds']), abs_tol=1e-5, rel_tol=0))
            or (motion is not None and not math.isclose(duration, float(motion.get_play_length()), abs_tol=1e-5, rel_tol=0))):
        raise ValueError('Prebuilt smile duration differs from its motion/catalog')
    assembly = current['assembly']
    result = assembly.apply_actor(u, actor, dict(copy.deepcopy(selected), face_id='none'), t, motion,
                                  body_action_id=body_action_id, data=current['data'])
    body = assembly.fixed.actor_components(actor)['Body']
    if clip.get_skeleton() != body.get_skeletal_mesh_asset().get_editor_property('skeleton'):
        raise ValueError('Prebuilt smile does not use the character skeleton')
    body.set_animation_mode(u.AnimationMode.ANIMATION_SINGLE_NODE)
    body.override_animation_data(clip, False, False, t, 1.)
    body.play_animation(clip, False)
    body.set_position(t, False)
    body.stop()
    face = {**row, 'kind': 'prebuilt_native_smile_static' if motion is None else 'prebuilt_native_smile_body',
            'animation_path': row['animation'], 'time_seconds': t,
            'catalog': str(CATALOG), 'runtime_composition': False}
    return dict(result, selection=copy.deepcopy(selected), animation_path=row['animation'], face=face,
                time_seconds=t)
