"""Sex-specific six-hair pages with original review numbers and bound sources."""
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path

import formal_wardrobe_registry_v1 as formal
import cfd_native_batch40_modular_contract_v1 as identities

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parents[1] / 'outputs/unreal_character_import/female_shared_shoes_hair_color_20261007_v1/hair_review'
ASSET_ROOT = '/Game/DataMake/Validation/HairGroupColor20261007'
LEVEL = ASSET_ROOT + '/L_DM_HairGroupColor_Review_v001'
TARGET_FILE = ROOT.parent / 'ue_target.json'
CAPABILITIES = ROOT / 'color_capabilities.json'
HAIR_COLORS = ('original', 'black', 'blue', 'pink', 'purple', 'red', 'teal', 'orange', 'gold', 'silver_white')
EYE_COLORS = ('original',)
DEFAULT = {'sex': 'female', 'page': 1, 'focus': 'all', 'view': 'front',
           'hair_color': 'original', 'eye_color': 'original', 'save': False}
read, write = identities.read, identities.write


def source(path):
    path = Path(path).resolve()
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()


def validate_colors(value):
    if not isinstance(value, dict) or set(value) != {'hair', 'eye'}:
        raise ValueError('Color capabilities require hair and eye lists')
    for kind, allowed in (('hair', HAIR_COLORS), ('eye', EYE_COLORS)):
        rows = value[kind]
        if (not isinstance(rows, list) or not rows or 'original' not in rows
                or any(not isinstance(v, str) or v not in allowed for v in rows) or len(rows) != len(set(rows))):
            raise ValueError('Invalid or duplicate supported color: ' + kind)
    return copy.deepcopy(value)


def catalog():
    registry_path = formal.current_registry_path()
    publication_path = formal.current_registry_publication_path()
    registry = formal.read_registry(registry_path)
    publication = read(publication_path)
    mapping_path = Path(publication['mapping_report'])
    mapping = read(mapping_path)
    sources = {'registry': source(registry_path), 'publication': source(publication_path), 'mapping_report': source(mapping_path)}
    if sources['mapping_report']['sha256'] != publication['mapping_report_sha256']:
        raise ValueError('Original hair review-number mapping changed')
    numbers = {row['hair_id']: row['historical_review_index'] for row in mapping['hair']}
    if len(numbers) != len(mapping['hair']):
        raise ValueError('Duplicate hair ID in original-number mapping')
    hairs = {'female': [], 'male': []}
    for hair in registry['hair_assets']:
        for sex in hairs:
            if formal.hair_available_to(hair, sex):
                hairs[sex].append({'index': numbers[hair['hair_id']], 'hair_id': hair['hair_id'],
                                   'label': hair.get('display_name') or hair['hair_id'], 'sex': sex,
                                   'reviewed_sexes': list(hair['reviewed_sexes']),
                                   'fit': copy.deepcopy(formal.hair_fit(hair, sex))})
    for sex in ('male', 'female'):
        approved = registry['reviewed_pool']['hair_review_indices_by_sex'][sex]
        count = len(approved)
        hairs[sex].sort(key=lambda row: row['index'])
        indices = [row['index'] for row in hairs[sex]]
        if (len(hairs[sex]) != count or len(set(indices)) != count
                or indices != approved):
            raise ValueError('Sex-specific approved original hairstyle numbers differ: ' + sex)
    characters = identities.identity_catalog()
    sources['character_registry'] = characters['source']
    colors = {'hair': list(HAIR_COLORS), 'eye': list(EYE_COLORS)}
    if CAPABILITIES.exists():
        colors = validate_colors(read(CAPABILITIES))
        sources['color_capabilities'] = source(CAPABILITIES)
    if any(source(item['path']) != item for item in sources.values()):
        raise ValueError('Hair review sources changed while reading')
    return {'sources': sources, 'hairs_by_sex': hairs,
            'characters_by_sex': {sex: copy.deepcopy(characters['by_id'][identifier])
                                  for sex, identifier in identities.DEFAULT_CHARACTER_IDS.items()},
            'colors': colors, 'page_size': 6, 'color_visual_acceptance': 'pending'}


def page_count(data, sex):
    if sex not in ('female', 'male'):
        raise ValueError('请选择女性或男性。')
    return math.ceil(len(data['hairs_by_sex'][sex]) / 6)


def normalize_request(value, data=None):
    data = catalog() if data is None else data
    if not isinstance(value, dict) or set(value) - set(DEFAULT):
        raise ValueError('发型审查请求包含未知字段。')
    result = dict(DEFAULT, **value)
    pages = page_count(data, result['sex'])
    if type(result['page']) is not int or not 1 <= result['page'] <= pages:
        raise ValueError('当前性别的页码超出范围。')
    count = len(data['hairs_by_sex'][result['sex']][(result['page'] - 1) * 6:result['page'] * 6])
    if result['focus'] not in ('all',) + tuple(str(i) for i in range(1, count + 1)):
        raise ValueError('本页不存在该位置；请选择整页或已有的单款发型。')
    if result['view'] not in ('front', 'side', 'back', 'threequarter'):
        raise ValueError('无效的观察角度。')
    if result['hair_color'] not in data['colors']['hair'] or result['eye_color'] not in data['colors']['eye']:
        raise ValueError('该颜色当前未开放，请重新打开面板。')
    if type(result['save']) is not bool:
        raise ValueError('保存选项必须是布尔值。')
    return copy.deepcopy(result)


def page_hairs(data, request):
    request = normalize_request(request, data)
    start = (request['page'] - 1) * 6
    return copy.deepcopy(data['hairs_by_sex'][request['sex']][start:start + 6])


def expected_order(data, request):
    return [{'slot': i, 'index': row['index'], 'hair_id': row['hair_id']}
            for i, row in enumerate(page_hairs(data, request), 1)]


def verify_result(result, request, data):
    if (not isinstance(result, dict) or result.get('success') is not True or result.get('level') != LEVEL
            or result.get('request') != request or result.get('sources') != data['sources']):
        raise RuntimeError('UE 返回的页面、选项或来源版本不一致。')
    expected = expected_order(data, request)
    actual = lambda rows: [{k: row.get(k) for k in ('slot', 'index', 'hair_id')} for row in rows]
    if actual(result.get('page_order', [])) != expected:
        raise RuntimeError('UE 页内发型顺序或旧编号不一致。')
    selected = expected if request['focus'] == 'all' else [expected[int(request['focus']) - 1]]
    if actual(result.get('displayed', [])) != selected:
        raise RuntimeError('UE 实际显示的发型与所选单款不一致。')
    return result
