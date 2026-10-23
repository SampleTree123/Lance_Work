"""Identity boundaries for the 40-person, two-skeleton fixed-slot review."""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import cfd_native_batch40_contract_v1 as batch
import hair_eye_color_runtime_v1 as color_runtime
import native_face_library_contract_v1 as face_library

RUN, REGISTRY, SCRIPTS = batch.RUN, batch.REGISTRY, batch.SCRIPTS
ROOT = RUN / 'runtime/modular_review_20261007_v1'
LEVEL = batch.UE_ROOT + '/L_DM_CFDNativeBatch40_ModularReview_v001'
SEXES = ('female', 'male')
BASE_ROLES = {'body', 'eyes', 'teeth', 'tongue', 'tearline', 'eye_occlusion'}
DEFAULT_CHARACTER_IDS = {'female': 'CFD40_AF_001', 'male': 'CFD40_AM_001'}
CONFIG_ROOT = SCRIPTS.parents[1] / 'outputs/unreal_character_import/character_runtime_face_library_20261007_v1'
APPEARANCE_KEYS = {'hair_color', 'eye_color', 'face_id'}
read, write = batch.read, batch.write


def default_appearance():
    return {sex: {'hair_color': 'original', 'eye_color': 'original', 'face_id': 'none'} for sex in SEXES}


def appearance_catalog():
    return {'hair': list(color_runtime.CAPABILITIES['hair']), 'eye': ['original'],
            'faces': ['none'], 'source': source(SCRIPTS / 'hair_eye_color_runtime_v1.py')}


def face_catalog():
    # An absent library is normal during preparation. An invalid existing
    # registry must fail visibly, never silently expose its candidates.
    path = face_library.active_registry_path()
    return face_library.catalog(path) if path.is_file() else {'entries': []}


def body_action_id(data, sex, index):
    if index == 0:
        return 'static'
    return data['actions_by_sex'][sex][index - 1]['action_id']


def faces_for_action(data, sex, index):
    return [row for row in face_library.available_faces(data['face_library'], sex, body_action_id(data, sex, index))
            if row['face_id'] == 'none' or face_library.panel_playback(row['playback'])]


def validate_appearance(value, library=None):
    if not isinstance(value, dict) or set(value) != set(SEXES):
        raise ValueError('必须分别指定男女的颜色与表情选项。')
    for sex, row in value.items():
        if not isinstance(row, dict) or set(row) != APPEARANCE_KEYS:
            raise ValueError('颜色配置字段不完整：' + sex)
        color_runtime.validate_request(row)
        if row['eye_color'] != 'original':
            raise ValueError('当前角色配置保留原始眼色，不开放虹膜调色。')
        if row['face_id'] != 'none':
            library = face_catalog() if library is None else library
            if not any(e['sex'] == sex and e['face_id'] == row['face_id'] and face_library.panel_playback(e['playback'])
                       for e in library['entries']):
                raise ValueError('该表情尚未通过此性别的播放验证，face_id=' + str(row['face_id']))
    return copy.deepcopy(value)


def source(path):
    path = Path(path).resolve()
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def validate_registry(document, *, verify_audits=False):
    cases = document.get('cases', [])
    batch.validate_spec({'cases': cases})
    by_id, by_sex, skeletons = {}, {s: [] for s in SEXES}, {}
    paths = set()
    for case in cases:
        identifier, sex = case['character_id'], case['sex']
        expected_id = f"CFD40_{case['group']}{'F' if sex == 'female' else 'M'}_{case['group_index']:03d}"
        expected_skeleton = (batch.UE_ROOT + '/SharedSkeletons/SKEL_CFDShared_' +
                             sex.title() + '_v1.SKEL_CFDShared_' + sex.title() + '_v1')
        if identifier != expected_id or case.get('standard_candidate_ready') is not True:
            raise ValueError('Identity is not a completed expected CFD40 import: ' + identifier)
        if case.get('skeleton') != expected_skeleton:
            raise ValueError('Identity must use its sex-specific shared skeleton: ' + identifier)
        meshes = case.get('meshes', [])
        if len(meshes) != 6 or {m.get('role') for m in meshes} != BASE_ROLES:
            raise ValueError('Identity requires exactly six unique base roles: ' + identifier)
        for mesh in meshes:
            path = mesh.get('path', '')
            if (not path.startswith(batch.UE_ROOT + '/' + identifier + '/') or '/..' in path or path in paths
                    or '.' not in path or path.rsplit('/', 1)[1].split('.')[0] != path.rsplit('.', 1)[1]):
                raise ValueError('Identity has a duplicated or foreign base mesh: ' + identifier)
            paths.add(path)
        if verify_audits:
            audit = case.get('audit_source', {})
            path = Path(audit.get('path', ''))
            if (not path.is_absolute() or not path.resolve().is_relative_to((RUN / 'imports').resolve())
                    or str(path) != case.get('audit') or not path.is_file()
                    or source(path)['sha256'] != audit.get('sha256')
                    or path.stat().st_size != audit.get('bytes')):
                raise ValueError('Import audit is missing, changed or outside the batch: ' + identifier)
        by_id[identifier] = copy.deepcopy(case)
        by_sex[sex].append(by_id[identifier])
        skeletons[sex] = expected_skeleton
    if any(len(rows) != 20 for rows in by_sex.values()) or len(set(skeletons.values())) != 2:
        raise ValueError('Expected 20 female and 20 male identities with exactly two skeletons')
    for rows in by_sex.values():
        rows.sort(key=lambda c: (batch.GROUPS.index(c['group']), c['group_index']))
    return {'cases': list(by_id.values()), 'by_id': by_id, 'by_sex': by_sex, 'skeletons': skeletons}


def identity_catalog():
    before = source(REGISTRY)
    result = validate_registry(read(REGISTRY), verify_audits=True)
    if before != source(REGISTRY):
        raise ValueError('Character registry changed while reading')
    return {**result, 'source': before}


def validate_character_ids(value, catalog=None):
    catalog = identity_catalog() if catalog is None else catalog
    if not isinstance(value, dict) or set(value) != set(SEXES):
        raise ValueError('必须明确选择一名女性和一名男性角色。')
    for sex, identifier in value.items():
        row = catalog['by_id'].get(identifier) if isinstance(identifier, str) else None
        if row is None or row['sex'] != sex:
            raise ValueError('角色编号不属于当前性别或不在已导入的 40 人中。')
    return copy.deepcopy(value)


def switch_identity(request, sex, identifier, catalog=None):
    """Only identity changes; clothes, hair, motion, camera and playing survive."""
    result = copy.deepcopy(request)
    if sex not in SEXES:
        raise ValueError('Unknown sex')
    result['character_ids'][sex] = identifier
    result['character_ids'] = validate_character_ids(result['character_ids'], catalog)
    return result
