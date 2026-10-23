"""Portable complete selection presets, bound to exact sources and palette."""
from __future__ import annotations
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import cfd_native_batch40_modular_contract_v1 as identity

SCHEMA = 'cfd40_complete_character_configuration_v1'


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()


def portable_request(request):
    return {**copy.deepcopy(request), 'action': 'show', 'save': False}


def build_configuration(result, data, validate_request):
    if result.get('success') is not True or result.get('sources') != data['sources']:
        raise ValueError('整套配置必须来自当前来源下成功显示的角色。')
    request = validate_request(portable_request(result['request']), data)
    content = {'request': request, 'sources': copy.deepcopy(data['sources']),
               'palette': copy.deepcopy(data['appearance']), 'level': identity.LEVEL}
    return {'schema': SCHEMA, 'created_at': datetime.now(timezone.utc).isoformat(),
            'content': content, 'content_sha256': digest(content),
            'scope': 'two_characters_identity_outfit_footwear_including_barefoot_hair_colors_native_face_motion_playing_and_view',
            'face_behavior': 'verified_native_face_id_and_body_action; none_restores_body_only; registry_sha256_bound',
            'playback_restore': 'selected_clip_and_playing_flag; verified_registry_playback_policy; oneshot_holds_last; phase_not_captured'}


def load_configuration(path, data, validate_request):
    document = identity.read(path)
    if document.get('schema') != SCHEMA or digest(document.get('content')) != document.get('content_sha256'):
        raise ValueError('整套配置格式或内容校验不通过。')
    content = document['content']
    saved_sources, current_sources = copy.deepcopy(content.get('sources')), copy.deepcopy(data['sources'])
    # A body-only preset has no dependency on a face library introduced or
    # updated later. Keep all its identity/wardrobe/palette source locks intact.
    appearance = content.get('request', {}).get('appearance', identity.default_appearance())
    if isinstance(appearance, dict) and all(appearance.get(s, {}).get('face_id') == 'none' for s in identity.SEXES):
        if isinstance(saved_sources, dict): saved_sources.pop('native_face_library', None)
        current_sources.pop('native_face_library', None)
    elif (isinstance(saved_sources, dict) and saved_sources.get('native_face_library') != current_sources.get('native_face_library')
            and data.get('face_library', {}).get('schema') == identity.face_library.SCHEMA_V2):
        legacy = data['face_library']['sources']['legacy_registry']
        if not identity.face_library._same_record(saved_sources.get('native_face_library'), legacy):
            raise ValueError('旧表情配置来源不匹配，不能自动迁移。')
        appearance, changes = identity.face_library.migrate_legacy_appearance(
            appearance, content['request'].get('face_registry_sha256'), data['face_library'])
        content = copy.deepcopy(content)
        content['request']['appearance'] = appearance
        content['request']['face_registry_sha256'] = current_sources['native_face_library']['sha256']
        saved_sources['native_face_library'] = current_sources['native_face_library']
        print('已明确迁移旧表情配置：' + json.dumps(changes, ensure_ascii=False))
    if content.get('level') != identity.LEVEL or saved_sources != current_sources:
        raise ValueError('配置引用的角色、服装或色板版本已经变化，不能静默替换。')
    if content.get('palette') != data['appearance']:
        raise ValueError('配置色板与当前色板不一致。')
    return validate_request(portable_request(content['request']), data)


def save_configuration(path, result, data, validate_request):
    document = build_configuration(result, data, validate_request)
    identity.write(Path(path), document)
    return {'path': str(Path(path).resolve()), 'sha256': identity.source(path)['sha256'],
            'content_sha256': document['content_sha256']}
