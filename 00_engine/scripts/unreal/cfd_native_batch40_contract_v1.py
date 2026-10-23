"""Offline identity, source and page contracts for the bounded 40-person review."""
import importlib.util
import json
from pathlib import Path
import re

SCRIPTS = Path(__file__).resolve().parent
REPO = SCRIPTS.parents[2]
RUN = REPO / '00_engine/outputs/unreal_character_import/cfd_native_batch40_20261006_v1'
UE_ROOT = '/Game/DataMake/Validation/CFDNativeBatch4020261006'
LEVEL = UE_ROOT + '/L_DM_CFDNativeBatch40_Review_v001'
SPEC = RUN / 'batch_source_spec.json'
REGISTRY = RUN / 'imported_character_registry.json'
GROUPS = ('A', 'B', 'L', 'W')
SEXES = ('male', 'female')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.partial')
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False, default=str) + '\n', encoding='utf-8')
    temp.replace(path)


def module(name):
    spec = importlib.util.spec_from_file_location('_cfd40_' + name, SCRIPTS / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def validate_spec(spec):
    cases = spec.get('cases', [])
    expected = {(sex, group, n) for sex in SEXES for group in GROUPS for n in range(1, 6)}
    actual, ids = set(), set()
    for case in cases:
        key = (case.get('sex'), case.get('group'), case.get('group_index'))
        identifier = case.get('character_id', '')
        if (type(case.get('group_index')) is not int or key not in expected or key in actual or identifier in ids
                or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_]{0,63}', identifier)):
            raise ValueError('Duplicate/invalid batch identity or A/B/L/W group slot: ' + repr(case))
        actual.add(key)
        ids.add(identifier)
    if len(cases) != 40 or actual != expected:
        raise ValueError('Exactly five male and five female identities in each A/B/L/W group are required')
    return cases


def page_cases(cases, page):
    if type(page) is not int or not 1 <= page <= 5:
        raise ValueError('Page must be 1..5')
    by_key = {(c['sex'], c['group'], c['group_index']): c for c in cases}
    if len(by_key) != len(cases):
        raise ValueError('Duplicate imported group slots')
    wanted = [(sex, group, page) for sex in SEXES for group in GROUPS]
    if any(key not in by_key for key in wanted):
        raise ValueError('Selected page does not have eight completed imports')
    return [by_key[key] for key in wanted]


def normalize_request(value):
    result = {'page': 1, 'focus': 'all', 'view': 'front', 'framing': 'full', 'hair': True, 'save': False}
    if set(value) - set(result):
        raise ValueError('Unsupported batch review request')
    result.update(value)
    if type(result['page']) is not int or not 1 <= result['page'] <= 5:
        raise ValueError('Page must be 1..5')
    if result['focus'] not in ('all',) + tuple(str(i) for i in range(1, 9)):
        raise ValueError('Focus must be all or page slot 1..8')
    if result['view'] not in ('front', 'side', 'back') or result['framing'] not in ('full', 'head'):
        raise ValueError('Invalid view or framing')
    if type(result['hair']) is not bool or type(result['save']) is not bool:
        raise ValueError('Hair/save must be boolean')
    return result


def target_remote():
    helper = module('cfd_native_pair_ue_target_v1')
    helper.RUN, helper.TARGET_FILE = RUN, RUN / 'ue_target.json'
    return helper.remote
