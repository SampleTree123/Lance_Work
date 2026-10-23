"""Current offline trial domains and exact formal wardrobe validation.

Imports only pure Python contracts; never imports unreal, opens UE, or writes
source configuration. CLI --export snapshots current inputs beside this file.
Candidate hair excludes None; None passed to wardrobe routines means that the
caller has not yet injected hair. Locked bundles retain exact required assets.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import random
import sys
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENGINE = HERE.parents[1]
SCRIPTS = ENGINE / 'scripts/unreal'
PRODUCTION = ENGINE / 'outputs/production_workflow_20261017_v1'
PAIR = ENGINE / 'outputs/pair_scene_review_20261019_v1'
CORE_SLOTS = ('shirts', 'coats', 'pants', 'skirts', 'full_body')
UPPER_SLOTS = ('shirts', 'coats', 'full_body')
SLOT_VISIBILITY = {'shirts':'upper', 'coats':'upper', 'pants':'lower',
                   'skirts':'lower', 'full_body':'upper_and_lower',
                   'shoes':'feet', 'family_accessory':'context_dependent'}


def _read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def _pin(path):
    path = Path(path).resolve()
    return {'path':str(path), 'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


@lru_cache(maxsize=1)
def _runtime():
    sys.path.insert(0, str(SCRIPTS))
    import scene_site_appearance_v1 as appearance
    import pair_review_fast_runtime_v1 as fast
    # Reuse the CURRENT review entry point, including its approved lightweight
    # lookup and exact formal slot semantics. No startup asset-wide rehash.
    loader, domain = fast.bind_catalog(appearance)
    return loader, domain


@lru_cache(maxsize=1)
def _appearance():
    return _runtime()[1].catalog()


@lru_cache(maxsize=1)
def _registry_snapshot():
    return _runtime()[1].slots._registry()


def validate_choice(sex, choice):
    """Return formal resolution incl normalized_choice/canonical_choice/assignments.

    Rejects retired families too (current registry already removes Rugged).
    Full formal shape is retained, including hair_id.
    """
    registry, source = _registry_snapshot()
    return _runtime()[1].slots._validate(registry, source, sex, choice)


def _family_group(sex, family_id, group_id):
    family = next(f for f in _appearance()['families_by_sex'][sex]
                  if f['family_id'] == family_id)
    group = next(g for g in family['groups'] if g['group_id'] == group_id)
    return family, group


def _selected_assets(sex, choice):
    resolved = validate_choice(sex, choice)
    registry, _ = _registry_snapshot()
    ids = set(resolved['selected_family_asset_ids'])
    return [a for f in registry['families'] for a in f['assets'] if a['asset_id'] in ids]


def resolved_asset_ids(sex, choice):
    """Actual selected clothing + shoe IDs, without family/group/hair labels."""
    resolved = validate_choice(sex, choice)
    values = list(resolved['selected_family_asset_ids'])
    if resolved['shared_shoe_id'] is not None:
        values.append(resolved['shared_shoe_id'])
    return sorted(values)


def wardrobe_key(sex, choice):
    """Hashable asset-only canonical key; group aliases never add a video."""
    return tuple(resolved_asset_ids(sex, choice))


def upper_asset_ids(sex, choice):
    """Selected upper/core IDs, usable for upper-body whole-change checks."""
    return sorted(a['asset_id'] for a in _selected_assets(sex, choice)
                  if a['slot'] in UPPER_SLOTS)


def core_asset_ids(sex, choice):
    return sorted(a['asset_id'] for a in _selected_assets(sex, choice)
                  if a['slot'] in CORE_SLOTS)


def _footwear_options(sex, family, group, choice):
    """Legal shared-shoe values conditioned on actual selected native shoes."""
    native = [a['asset_id'] for a in group['required_assets'] if a['slot']=='shoes']
    native += [v for s,v in choice['slot_choices'].items() if s=='shoes' and v]
    native += [a['asset_id'] for a in group['optional_assets']
               if a['slot']=='shoes' and a['asset_id'] in choice['optional_asset_ids']]
    if native:
        return [None]
    pool = [s['asset_id'] for s in _appearance()['shared_shoes_by_sex'][sex]]
    if group['shared_shoe_policy'] == 'required_universal_female_pool':
        return pool
    return [None] + pool


def sample_choice(sex, rng=None, *, family_id=None, group_id=None, hair_id=None):
    """Hierarchical uniform family -> group -> independent legal pieces/shoe.

    Required locked assets are supplied by the formal contract, never split.
    Core optional slots may be empty only where the current group permits it.
    """
    rng = rng or random.Random()
    families = _appearance()['families_by_sex'][sex]
    family = (next(f for f in families if f['family_id']==family_id)
              if family_id is not None else rng.choice(families))
    group = (next(g for g in family['groups'] if g['group_id']==group_id)
             if group_id is not None else rng.choice(family['groups']))
    choice = {'family_id':family['family_id'], 'group_id':group['group_id'],
              'slot_choices':{}, 'optional_asset_ids':[], 'shared_shoe_id':None,
              'hair_id':hair_id}
    for slot, options in group['slot_options'].items():
        values = [a['asset_id'] for a in options]
        if slot in group['optional_slots']:
            values = [None] + values
        choice['slot_choices'][slot] = rng.choice(values)
    if group['optional_asset_policy'] != 'independent_subset' and group['optional_assets']:
        raise ValueError('Unknown optional asset policy; refusing fabricated combinations')
    choice['optional_asset_ids'] = [a['asset_id'] for a in group['optional_assets']
                                    if rng.randrange(2)]
    choice['shared_shoe_id'] = rng.choice(_footwear_options(sex, family, group, choice))
    return validate_choice(sex, choice)['normalized_choice']


def single_piece_neighbors(sex, choice):
    """List[{choice,slot}]: same family/group; exactly one core slot differs.

    Shoes, accessories and hair are held fixed. Locked bundles have no such
    edges. Optional None is allowed exactly where the formal group allows it.
    """
    choice = validate_choice(sex, choice)['normalized_choice']
    family, group = _family_group(sex, choice['family_id'], choice['group_id'])
    if family['assembly_mode']=='locked_bundle':
        return []
    rows = []
    for slot in CORE_SLOTS:
        if slot not in group['slot_options']:
            continue
        values = [a['asset_id'] for a in group['slot_options'][slot]]
        if slot in group['optional_slots']:
            values.append(None)
        for value in values:
            if value == choice['slot_choices'][slot]:
                continue
            changed = copy.deepcopy(choice)
            changed['slot_choices'][slot] = value
            result = validate_choice(sex, changed)
            if result['hair_deny'] and changed['hair_id'] is not None:
                continue
            rows.append({'choice':result['normalized_choice'], 'slot':slot})
    return rows


def sample_whole_change(sex, choice, rng=None, *, require_upper_change=False):
    """A different source family with changed core; fresh legal group/shoe.

    Family selection is uniform. Source hair is preserved. Optional upper-body
    filter prevents edits confined to trousers/skirts in an upper-body shot.
    """
    rng = rng or random.Random()
    source = validate_choice(sex, choice)['normalized_choice']
    core = core_asset_ids(sex, source)
    upper = upper_asset_ids(sex, source)
    candidates = [f for f in _appearance()['families_by_sex'][sex]
                   if f['family_id'] != source['family_id']]
    for _ in range(256):
        family = rng.choice(candidates)
        target = sample_choice(sex, rng, family_id=family['family_id'], hair_id=source['hair_id'])
        if core_asset_ids(sex, target)==core:
            continue
        if require_upper_change and upper_asset_ids(sex, target)==upper:
            continue
        if validate_choice(sex, target)['hair_deny'] and source['hair_id'] is not None:
            continue
        return target
    raise ValueError('No whole-clothing candidate with required visible core change')


def _scene_inventory():
    import scene_site_catalog_v1 as directory
    import scene_review_selection_policy_v1 as selection
    import pair_review_site_intent_v1 as intent
    # Read production clocks/cameras, not the inherited 30-motion bootstrap.
    camera_path = PRODUCTION/'camera_library/production10/catalog.json'
    camera = _read(camera_path)
    motion_pin = _read(PRODUCTION/'production_motion_formal_runtime_active_v1.json')['catalog']
    motions = _read(motion_pin['path'])
    actions = []
    for row in camera['actions']:
        mid = row.get('motion_id',row.get('id'))
        if mid in selection.RETIRED_MOTION_IDS:
            continue
        actions.append({**row, 'id':mid, 'label':row.get('motion_label',row.get('label',mid)),
                        'variants':[v for v in motions['variants'] if v['motion_id']==mid]})
    cameras = [{**r, 'id':r.get('camera_id',r.get('id')),
                'label':r.get('camera_label',r.get('label',r.get('camera_id')))}
               for r in camera['cameras']]
    scenes = directory.build_catalog(saved_site_roots=(PAIR/'sites',))
    primary = {r['map_path']:r for r in scenes['scenes'] if r['primary']}
    sites, excluded, source_pins = [], [], [_pin(camera_path),_pin(motion_pin['path'])]
    active_actions = {r['id'] for r in actions}
    for path in sorted((PAIR/'sites').glob('site_*.json')):
        doc = _read(path)
        site = doc['site']
        if site['map'] not in primary:
            continue
        if site['site_id'] != path.stem:
            raise ValueError('Site filename does not match saved identity')
        rows = intent.saved_intent(site)['excluded_combinations']
        rows = [r for r in rows if r['action_id'] in active_actions]
        source = _pin(path)
        sites.append({**copy.deepcopy(site), 'id':site['site_id'],
                      'label':site.get('name',primary[site['map']]['name']),
                      'scene_label':primary[site['map']]['name'], 'source':source,
                      'manual_exclusions':rows,
                      'human_acceptance':doc.get('human_acceptance',site.get('human_acceptance'))})
        excluded.extend(dict(r,site_id=site['site_id'],site=site['site_id']) for r in rows)
        source_pins.append(source)
    return actions,cameras,sites,excluded,source_pins


def build_catalog():
    data = _appearance()
    loader, domain = _runtime()
    import night_character_review_v1 as night
    delivery = night.delivery()
    overlay = domain.formal_path_overlay
    def remap(value):
        if isinstance(value,dict):return {k:remap(v) for k,v in value.items()}
        if isinstance(value,list):return [remap(v) for v in value]
        return overlay.get(value,value) if isinstance(value,str) else value
    sexes = {}
    for sex in ('female','male'):
        families = remap(copy.deepcopy(data['families_by_sex'][sex]))
        for family in families:
            for group in family['groups']:
                group['core_slots'] = [s for s in CORE_SLOTS if s in group['slot_options']]
                group['variable_core_slots'] = [s for s in group['core_slots']
                    if len(group['slot_options'][s]) + (s in group['optional_slots']) > 1]
                group['slot_visibility'] = {s:SLOT_VISIBILITY.get(s,'context_dependent')
                                            for s in group['slot_options']}
                # These are exact canonical locked choices, not split slots.
                group['lock_presets'] = ([{'family_id':family['family_id'],
                    'group_id':group['group_id'], 'slot_choices':{},'optional_asset_ids':[],
                    'shared_shoe_id':None, 'hair_id':None}]
                    if family['assembly_mode']=='locked_bundle' else [])
                group['lock_required_asset_ids'] = ([a['asset_id'] for a in group['required_assets']]
                    if family['assembly_mode']=='locked_bundle' else [])
                policy = group['shared_shoe_policy']
                shared_ids = [s['asset_id'] for s in data['shared_shoes_by_sex'][sex]]
                group['shoe_rules'] = {
                    'policy':policy,
                    'shared_options':[] if policy=='forbidden_native_required' else shared_ids,
                    'shared_options_condition':'only_when_no_native_shoe_selected',
                    'shared_forbidden_when_native_selected':True,
                    'shared_required':policy=='required_universal_female_pool',
                    'barefoot_allowed_when_no_native_selected':policy not in (
                        'required_universal_female_pool','forbidden_native_required'),
                    'native_required_asset_ids':[a['asset_id'] for a in group['required_assets'] if a['slot']=='shoes'],
                    'native_slot_options':[a['asset_id'] for a in group['slot_options'].get('shoes',[])],
                    'native_slot_required':'shoes' in group['required_slots'],
                    'selection_function':'_footwear_options(sex,family,group,choice)'}
        sexes[sex] = {'identities':[dict(copy.deepcopy(r),id=r['character_id'],label=r['character_id'])
                                    for r in delivery['cases'] if r['sex']==sex],
                      'hairs':remap(data['hairs_by_sex'][sex]), 'families':families,
                      'shared_shoes':remap(data['shared_shoes_by_sex'][sex]),
                      'presets':remap(data['presets_by_sex'][sex])}
    actions,cameras,sites,exclusions,scene_pins = _scene_inventory()
    return {'schema':'dataset_trial_normalized_catalog_20261021_v1',
        'scope':'offline_current_registered_domains_not_render_or_visual_acceptance',
        'sources':data['sources'], 'source_pins':[_pin(night.DELIVERY),
            *[_pin(SCRIPTS/name) for name in (
                'formal_wardrobe_registry_v1.py','complete_character_slot_review_contract_v1.py',
                'scene_site_appearance_v1.py','pair_review_fast_runtime_v1.py',
                'appearance_selection_policy_v1.py','scene_review_selection_policy_v1.py',
                'pair_review_site_intent_v1.py','scene_site_catalog_v1.py')],
            _pin(PRODUCTION/'asset_inventory_formal_runtime_active_v1.json'),
            _pin(PRODUCTION/'wardrobe_component_corrections_v1.json'),*scene_pins],
        'asset_validation':'current_fast_review_lookup_policy; no full asset-wide hash audit',
        'sexes':sexes, 'actions':actions,'cameras':cameras,'sites':sites,
        'exclusions':exclusions,'aspects':['landscape','portrait'],
        'hair_colors':data['hair_colors'], 'slot_visibility':SLOT_VISIBILITY,
        'candidate_policy':{'retired_families':['male.rugged_trendy'],
            'hair_none_formally_legal_but_not_candidate':True,
            'unclothed_formally_legal_but_not_candidate':True,
            'family_equals_source_wardrobe_group':True,
            'group_equals_legal_combination_group':True,
            'single_piece_core_slots':list(CORE_SLOTS),
            'single_piece_holds_shoes_accessories_hair_fixed':True,
            'whole_requires_different_family_and_core_change':True,
            'counts_are_registered_not_pixel_distinct':True}}


@lru_cache(maxsize=1)
def load_catalog():
    """Read the immutable snapshot; call build_catalog() to refresh explicitly."""
    return _read(HERE/'catalog.json')


if __name__=='__main__':
    if '--export' in sys.argv:
        catalog = build_catalog()
        (HERE/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'sexes':{s:{k:len(v) for k,v in d.items()} for s,d in catalog['sexes'].items()},
                          'actions':len(catalog['actions']),'cameras':len(catalog['cameras']),
                          'sites':len(catalog['sites']),'exclusions':len(catalog['exclusions'])}))
