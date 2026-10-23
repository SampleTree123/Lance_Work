"""Experimental refresh compiler; explicit photo-tone skin choice, no CC calls."""
import argparse
import hashlib
import json
from pathlib import Path

DIRECTORY = Path(__file__).resolve().parent
REGISTRY = DIRECTORY / 'cc_facial_production_registry_v1.json'
MAKEUP_ROOT = Path(r'D:/CharacterCreator_sucai/Reallusion Custom/Makeup/Eyebrow/Makeup & SFX')
REDNESS_ROOT = Path(r'D:/CharacterCreator_sucai/Reallusion Templates/Skin/Skin Details/3_Coloration')


def file_ref(path, expected=None):
    path = Path(path).resolve()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if expected is not None and digest != expected:
        raise ValueError('SHA256 changed: ' + str(path))
    return {'path': str(path), 'sha256': digest}


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def choose_eyebrow(sex, seed, character_id):
    pool = sorted((MAKEUP_ROOT / ('Male' if sex == 'male' else 'Trimmed')).glob('*.ccSkinGenPreset'), key=lambda p: p.name.casefold())
    if not pool:
        raise ValueError('Requested Makeup eyebrow pool is empty')
    key = '{}:{}:makeup_eyebrow'.format(seed, character_id).encode('utf-8')
    path = pool[int(hashlib.sha256(key).hexdigest(), 16) % len(pool)]
    return dict(file_ref(path), display_name=path.stem, pool_size=len(pool), application_mode='experimental_makeup_layer')


def approved_asset(registry, pool, asset_id, sex):
    matches = [a for a in registry['component_pools'][pool] if a['asset_id'] == asset_id]
    if len(matches) != 1:
        raise ValueError('Explicit asset must match exactly one approved {} entry'.format(pool))
    asset = dict(matches[0])
    if (asset.get('sex') or asset.get('sex_hint')) in ('male', 'female') and (asset.get('sex') or asset.get('sex_hint')) != sex:
        raise ValueError('Explicit asset sex mismatch')
    asset.update(file_ref(asset['path'], asset['sha256']))
    asset['extension'] = Path(asset['path']).suffix.lower()
    asset['verification_mode'] = 'scene_inventory' if pool == 'eyelashes' else 'material_fingerprint'
    return asset


def compile_request(request, registry_path=REGISTRY):
    sex, person = request['sex'], request['character_id']
    if sex not in ('male', 'female') or not isinstance(person, str) or not person.strip():
        raise ValueError('Expected sex and nonempty character_id')
    seed = request['seed']
    if isinstance(seed, bool) or not isinstance(seed, (str, int)):
        raise ValueError('Explicit string/integer seed required')
    reason = request.get('skin_selection_reason')
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError('Explicit visible-photo-tone skin selection reason required; no random skin choice')
    registry = read_json(registry_path)
    if len(registry['component_pools']['eyelashes']) != 9 or len(registry['component_pools']['eyes']) != 12:
        raise ValueError('This experiment retains exactly the existing9 lash and12 eye pools')
    assets = {slot: approved_asset(registry, pool, request[field], sex) for slot, pool, field in (
        ('skin', 'skins', 'skin_asset_id'), ('eyelashes', 'eyelashes', 'eyelash_asset_id'), ('eyes', 'eyes', 'eye_asset_id'))}
    assets['makeup_eyebrow'] = choose_eyebrow(sex, seed, person)
    redness_policy = request.get('redness_policy', 'excluded_by_user')
    if redness_policy not in ('experimental_optional', 'excluded_by_user'):
        raise ValueError('Unknown redness policy')
    excluded_redness = redness_policy == 'excluded_by_user'
    if not excluded_redness or 'redness_choice' in request or 'redness_opacity' in request:
        redness, opacity = request['redness_choice'], request['redness_opacity']
        if redness not in ('hemoglobin', 'redness', 'mature_redness') or isinstance(opacity, bool) or opacity not in (50, 100):
            raise ValueError('Redness must be one type and opacity50/100')
        path = {'hemoglobin': 'Hemoglobin {}.ccSkinGenPreset'.format('M' if sex == 'male' else 'F'),
                'redness': 'Redness/{}.ccSkinGenPreset'.format(sex.title()),
                'mature_redness': 'Redness/Mature {}.ccSkinGenPreset'.format(sex.title())}[redness]
        assets['redness'] = dict(file_ref(REDNESS_ROOT / path), choice=redness, opacity=opacity,
            requested_layers=['Hemoglobin'] if redness == 'hemoglobin' else ['upper face', 'mid face', 'lower face'],
            application_status='excluded_by_user_historical_reference_only' if excluded_redness else
                'pending_real_layer_names_opacity_and_persistence_validation')
    source = request['source_project']
    backup = request['current_scene_backup']
    include_redness = request.get('include_redness_layers', False)
    if excluded_redness and include_redness is not False:
        raise ValueError('User-excluded redness cannot be included')
    verify_layers = request.get('verify_layer_persistence', True)
    capture_pixels = request.get('capture_pixel_evidence', True)
    restore_support = request.get('restore_non_skin_materials', False)
    close_editor = request.get('finalize_editor_closed', excluded_redness)
    if not isinstance(include_redness, bool) or not isinstance(verify_layers, bool) or (include_redness and not verify_layers):
        raise ValueError('Explicit boolean layer options required; redness requires persistence verification')
    if not isinstance(capture_pixels, bool):
        raise ValueError('capture_pixel_evidence must be an explicit boolean')
    if not isinstance(restore_support, bool) or (restore_support and not capture_pixels):
        raise ValueError('Measured support restoration requires real pixel capture')
    if not isinstance(close_editor, bool) or (close_editor and (not excluded_redness or not verify_layers or not capture_pixels)):
        raise ValueError('Editor-closed finalization requires excluded redness, actual layers and real pixels')
    return {'diagnostic_mode': 'character_refresh', 'refresh_assembly': {
        'schema_version': 1, 'status': 'experimental_partial_candidate_only', 'character_id': person, 'sex': sex,
        'seed': seed, 'source_project': file_ref(source['path'], source['sha256']),
        'current_scene_backup': file_ref(backup['path'], backup['sha256']),
        'skin_selection_reason': reason, 'registry': file_ref(registry_path), 'assets': assets,
        'phases': ['skin', 'remove_legacy_brow_parts', 'eyes', 'makeup_eyebrow'],
        'include_redness_layers': include_redness, 'verify_layer_persistence': verify_layers,
        'redness_policy': redness_policy,
        'capture_pixel_evidence': capture_pixels,
        'restore_non_skin_materials': restore_support,
        'finalize_editor_closed': close_editor,
        'pending_phases': ['eyelashes_measured_asset_specific_geometry_policy'] + ([] if excluded_redness else ['redness_exact_layer_opacity_and_reload']),
        'pending_validation': ['Makeup_actual_layer_identity_and_persistence_after_first_real_load',
                               'protected_eye_support_texture_pixels_via_real_SaveFile_exports_where_required',
                               'layer_enable_button_visual_semantics_and_baked_texture_effect'],
        'geometry': {'mesh': 'CC_Base_Body', 'space': 'local', 'vertices': 14164,
                     'working_subdivision_level': 0, 'maximum_displacement_mm': 0.002, 'allowances': []},
        'geometry_working_level_policy': ('Material phases measure actual0 then restore SkinGen1; after actual editing-layer persistence close editor and persist actual0 with full native geometry/pixels.' if close_editor else
            'Historical experimental path: capture real raw state; switch1_to0 for actual-base measurement then restore SkinGen1; partial may remain1.'),
        'preserve_modified_materials': True, 'recipe_complete': False}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--request', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        raise ValueError('Refuse to overwrite compiled experiment')
    result = compile_request(read_json(args.request))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
