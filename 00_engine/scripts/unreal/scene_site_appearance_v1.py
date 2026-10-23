"""Single-character selections shared by the scene panel and its private worker.

No Unreal import, scene edits or point-file writes. Appearance files are new,
immutable records; a shooting point may retain only their ID as a link.
"""
from __future__ import annotations

import copy
import importlib.util
import re
import uuid
from pathlib import Path

import cfd_native_batch40_modular_contract_v1 as identities
import complete_character_slot_review_contract_v1 as slots
import run_complete_character_wardrobe_hair_review_v1 as io
import scene_site_hair_color_trials_v1 as hair_palette

SCHEMA = 'scene_site_appearance_v1'
ROOT = Path(__file__).resolve().parents[2] / 'outputs/scene_site_review_20261014_v1/appearances'
KEYS = {'character_id', 'sex', 'choice', 'hair_color', 'eye_color', 'face_id', 'sources'}
COLOR_LABELS = {'original': '原色', 'black': '黑色', 'blue': '蓝色', 'pink': '粉色',
                'purple': '紫色', 'red': '红色', 'teal': '青色', 'orange': '橙色',
                'gold': '金色', 'silver_white': '银白色'}
COLOR_LABELS.update(hair_palette.COLOR_LABELS)
FORMAL_HELPER = ROOT.parent.parent / 'production_workflow_20261017_v1/asset_inventory_formal_runtime_v1.py'
FORMAL_POINTER = FORMAL_HELPER.with_name('asset_inventory_formal_runtime_active_v1.json')
FORMAL_CORRECTIONS = FORMAL_HELPER.with_name('wardrobe_component_corrections_v1.json')
FORMAL_COLOR_TRIAL_CATALOG = Path(__file__).with_name('scene_site_hair_color_trials_v1.py')
FORMAL_COLOR_TRIAL_RUNTIME = Path(__file__).with_name('hair_color_neutral_trial_runtime_v1.py')
FORMAL_COLOR_COMPATIBILITY = FORMAL_HELPER.parent / 'panel_followup_audit/hair_color_neutral_base_v2_compatibility_v1.json'
FORMAL_COLOR_COMPATIBILITY_ARCHIVE = FORMAL_COLOR_COMPATIBILITY.with_name('hair_color_trial_catalog_before_neutral_base_v2.py')
FORMAL_SILVER_COMPATIBILITY = FORMAL_COLOR_COMPATIBILITY.with_name('hair_color_silver_comparison_compatibility_v1.json')
FORMAL_SILVER_COMPATIBILITY_ARCHIVE = FORMAL_COLOR_COMPATIBILITY.with_name('hair_color_neutral_base_v2_catalog_before_silver_comparison.py')
FORMAL_WHITE_COMPATIBILITY = FORMAL_COLOR_COMPATIBILITY.with_name('hair_color_white_refinement_compatibility_v1.json')
FORMAL_WHITE_COMPATIBILITY_ARCHIVE = FORMAL_COLOR_COMPATIBILITY.with_name('hair_color_silver_comparison_catalog_before_white_refinement.py')
FORMAL_SOFT_REFLECTION_COMPATIBILITY = FORMAL_COLOR_COMPATIBILITY.with_name('hair_color_soft_reflection_compatibility_v1.json')
FORMAL_SOFT_REFLECTION_COMPATIBILITY_ARCHIVE = FORMAL_COLOR_COMPATIBILITY.with_name('hair_color_white_refinement_catalog_before_soft_reflection.py')
FORMAL_CANONICAL_TEN_COMPATIBILITY = FORMAL_COLOR_COMPATIBILITY.with_name('hair_color_canonical_ten_restore_compatibility_v1.json')
FORMAL_CANONICAL_TEN_COMPATIBILITY_ARCHIVE = FORMAL_COLOR_COMPATIBILITY.with_name('hair_color_soft_reflection_catalog_before_canonical_ten_restore.py')
_formal_cache = None
_original_slots = slots


class _CurrentSlots:
    """Keep existing panel callers on the explicitly published private domain."""
    def __getattr__(self, name):
        formal = formal_runtime()
        return getattr(formal[1].slots if formal else _original_slots, name)


slots = _CurrentSlots()


def formal_runtime():
    """Discover only the explicit published catalog; never infer from folders."""
    global _formal_cache
    # Asset inventory creates a private instance of this module and injects its
    # dependencies. It must not recursively create another private instance.
    if globals().get('formal_runtime_source') or not FORMAL_POINTER.is_file():
        return None
    signature = tuple((str(path), (path.stat().st_size, path.stat().st_mtime_ns) if path.is_file() else None)
                      for path in (FORMAL_POINTER, FORMAL_HELPER, FORMAL_CORRECTIONS,
                                   FORMAL_COLOR_TRIAL_CATALOG, FORMAL_COLOR_TRIAL_RUNTIME,
                                   FORMAL_COLOR_COMPATIBILITY, FORMAL_COLOR_COMPATIBILITY_ARCHIVE,
                                   FORMAL_SILVER_COMPATIBILITY, FORMAL_SILVER_COMPATIBILITY_ARCHIVE,
                                   FORMAL_WHITE_COMPATIBILITY, FORMAL_WHITE_COMPATIBILITY_ARCHIVE,
                                   FORMAL_SOFT_REFLECTION_COMPATIBILITY, FORMAL_SOFT_REFLECTION_COMPATIBILITY_ARCHIVE,
                                   FORMAL_CANONICAL_TEN_COMPATIBILITY, FORMAL_CANONICAL_TEN_COMPATIBILITY_ARCHIVE))
    if _formal_cache is None or _formal_cache[0] != signature:
        spec = importlib.util.spec_from_file_location('_dm_scene_formal_runtime', FORMAL_HELPER)
        loader = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(loader)
        contract = loader.appearance_contract()  # Current asset hashes verified here.
        _formal_cache = (signature, loader, contract)
    return _formal_cache[1], _formal_cache[2]


def catalog():
    formal = formal_runtime()
    if formal:
        return formal[1].catalog()
    wardrobe = slots.catalog()
    people = identities.identity_catalog()
    library = identities.face_catalog()
    palette = identities.appearance_catalog()
    sources = {'character_registry': people['source'], 'wardrobe_registry': wardrobe['sources']['registry'],
               'appearance_palette': palette['source']}
    if palette.get('code_compatibility_source'):
        sources['appearance_palette_compatibility'] = palette['code_compatibility_source']
    if palette.get('trial_catalog_source'):
        sources['hair_color_trials'] = palette['trial_catalog_source']
    if palette.get('hair_color_method'):
        # Every source value is a file pin consumed by the worker's input
        # verifier. Carry the method beside that pin, not as a bare string.
        sources['hair_color_method'] = {**copy.deepcopy(palette['trial_catalog_source']),
                                        'method': palette['hair_color_method']}
    if library.get('registry_source'):
        sources['native_face_library'] = library['registry_source']
    return {'schema': SCHEMA, 'sources': sources,
            'identities': [{'id': r['character_id'], 'sex': r['sex'], 'label': r['character_id']}
                           for r in people['cases']],
            **{k: wardrobe[k] for k in ('families_by_sex', 'hairs_by_sex', 'shared_shoes_by_sex',
                                        'presets_by_sex', 'slot_labels')},
            'hair_colors': [next((copy.deepcopy(row) for row in palette.get('hair_color_trials', []) if row['id'] == c),
                                 {'id': c, 'label': COLOR_LABELS[c]}) for c in palette['hair']],
            'faces': [{k: copy.deepcopy(r[k]) for k in ('sex', 'face_id', 'body_action_id', 'label', 'playback')}
                      for r in library['entries'] if identities.face_library.panel_playback(r['playback'])]}


def default_selection(data=None, sex='female'):
    data = catalog() if data is None else data
    choice = copy.deepcopy(data['presets_by_sex'][sex][0]['choice'])
    # Match the retained modular panel's reviewed opening hairstyle.
    hair = next((h for h in data['hairs_by_sex'][sex] if h['index'] == 2), None)
    choice['hair_id'] = hair['hair_id'] if hair else None
    return {'character_id': next(r['id'] for r in data['identities'] if r['sex'] == sex),
            'sex': sex, 'choice': choice, 'hair_color': 'original', 'eye_color': 'original',
            'face_id': 'none', 'sources': copy.deepcopy(data['sources'])}


def default_choice(family_id, group_id):
    formal = formal_runtime()
    return (formal[1].slots if formal else slots).default_choice(family_id, group_id)


def faces_for_action(data, sex, body_action_id):
    # Accepted curves can be composed over any actual body by the scene worker.
    # The old registry's six precomposed body IDs only locate accepted sources.
    rows = {}
    for row in data['faces']:
        if row['sex'] == sex:
            rows.setdefault(row['face_id'], {k: copy.deepcopy(v) for k, v in row.items() if k != 'body_action_id'})
    return [{'face_id': 'none', 'label': '无表情（身体动作）'}] + list(rows.values())


def validate_selection(value, data=None, *, body_action_id=None):
    formal = formal_runtime()
    if formal:
        return formal[1].validate_selection(value, data, body_action_id=body_action_id)
    data = catalog() if data is None else data
    if not isinstance(value, dict) or set(value) != KEYS:
        raise ValueError('人物外观配置字段不完整。')
    sex = value['sex']
    if not any(r['id'] == value['character_id'] and r['sex'] == sex for r in data['identities']):
        raise ValueError('请选择当前 40 人目录中的角色。')
    if value['sources'] != data['sources']:
        raise ValueError('外观所用角色、服装、发色或表情目录已变化，请重新选择。')
    resolved = slots.validate_choice(sex, value['choice'])
    color = hair_palette.canonical_color(value['hair_color'])
    if color not in {r['id'] for r in data['hair_colors']} or value['eye_color'] != 'original':
        raise ValueError('请选择当前目录中的发色；眼色保留原色。')
    if value['face_id'] != 'none' and not any(r['sex'] == sex and r['face_id'] == value['face_id'] for r in data['faces']):
        raise ValueError('请选择已验收的四种表情之一，或选择无表情。')
    result = copy.deepcopy(value)
    result['hair_color'] = color
    result['choice'] = resolved['normalized_choice']
    return result


def _path(config_id, root):
    if not isinstance(config_id, str) or not re.fullmatch(r'appearance_[0-9a-f]{32}', config_id):
        raise ValueError('外观配置编号无效。')
    return Path(root) / (config_id + '.json')


def save_configuration(name, selection, data=None, *, root=ROOT):
    value = validate_selection(selection, data)
    name = str(name).strip()
    if not name or len(name) > 120:
        raise ValueError('外观名称须为 1 到 120 个字符。')
    config_id = 'appearance_' + uuid.uuid4().hex
    document = {'schema': SCHEMA, 'id': config_id, 'name': name, 'created_at': io.now(),
                'selection': value, 'selection_sha256': io.digest(value)}
    path = _path(config_id, root)
    if path.exists():
        raise ValueError('外观编号已存在，不会覆盖。')
    io.write(path, document)
    return document


def load_configuration(config_id, data=None, *, root=ROOT):
    document = io.read(_path(config_id, root))
    if (document.get('schema') != SCHEMA or document.get('id') != config_id
            or document.get('selection_sha256') != io.digest(document.get('selection'))):
        raise ValueError('外观配置格式或内容校验失败。')
    return {**document, 'selection': validate_selection(document['selection'], data)}


def list_configurations(*, root=ROOT):
    rows = []
    for path in sorted(Path(root).glob('appearance_*.json')):
        try:
            d = io.read(path)
            if d.get('schema') == SCHEMA and _path(d.get('id'), root).name == path.name:
                rows.append({k: d[k] for k in ('id', 'name', 'created_at')})
        except (ValueError, OSError, KeyError):
            continue
    return rows
