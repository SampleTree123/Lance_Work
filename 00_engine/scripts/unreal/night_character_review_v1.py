"""Completed 40-person import lookup for the existing fast review runtime."""
import copy
import json
from pathlib import Path

DELIVERY = Path(__file__).resolve().parents[2] / 'outputs/character_refresh_20261018_v1/user_edited_night_import_20261020_v1/delivery.json'
SCHEMA = 'night_character_review_20261020_v1'
# These three choices were removed from the shooting menu, but remain in old
# immutable appearances linked by saved sites. Unknown colors must still fail.
REMOVED_HAIR_COLORS = frozenset(('purple', 'teal', 'orange'))


def delivery():
    value = json.loads(DELIVERY.read_text(encoding='utf-8-sig'))
    if value['status'] != 'imports_completed' or value['completed_count'] != 40:
        raise ValueError('需要昨晚40人导入完成的交接。')
    return value


def configuration(revision):
    source = delivery()
    members = {}
    for case in source['cases']:
        identifier = case['character_id']
        audit = revision._read(case['audit'])
        rows = audit['meshes']
        base = {revision.ROLES[r['role']]:r['path'] for r in rows if r['role'] in revision.ROLES}
        followers = [copy.deepcopy(r) for r in rows if r['role'] == 'eyelashes']
        if set(base) != set(revision.ROLES.values()) or not followers:
            raise ValueError('角色部件不完整：' + identifier)
        if {r['path'] for r in rows} != {r['path'] for r in case['meshes']}:
            raise ValueError('交接部件路径不一致：' + identifier)
        members[identifier] = {'character_id':identifier, 'sex':case['sex'],
                              'skeleton':case['skeleton'], 'base':base, 'followers':followers}
    return {'schema':SCHEMA, 'ue_root':source['ue_root'], 'members':members,
            'pins':[revision._pin(DELIVERY)], 'inputs':[], 'stamps':{},
            'asset_validation':False}


def bind_saved_selections(contract, data):
    """Keep saved looks usable after delivery and shooting-palette changes."""
    original = contract.validate_selection
    def validate(value, current=None, **kwargs):
        current = data if current is None else current
        old_sources = value.get('sources', {}) if isinstance(value, dict) else {}
        new_sources = current['sources']
        if ({k:v for k,v in old_sources.items() if k != 'character_revision'}
                == {k:v for k,v in new_sources.items() if k != 'character_revision'}):
            value = copy.deepcopy(value)
            value['sources'] = copy.deepcopy(new_sources)
        color = value.get('hair_color') if isinstance(value, dict) else None
        available = {row['id'] for row in current['hair_colors']}
        if (isinstance(color, str) and color in REMOVED_HAIR_COLORS
                and color not in available and 'original' in available):
            # Normalize only the look in memory. The linked appearance's digest
            # is checked by load_configuration before reaching this validator;
            # point decisions, pose and camera never enter this migration.
            value = copy.deepcopy(value)
            value['hair_color'] = 'original'
        return original(value, current, **kwargs)
    contract.validate_selection = validate
