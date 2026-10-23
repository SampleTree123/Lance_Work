"""Scoped SaveFile evidence plus explicitly enabled measured support restoration.

Reuse the validated skin experiment exporter through a read-only scope adapter.
Identical exported PNG bytes share one object across checkpoints.
"""
import importlib
import json
import os

CHANNELS = frozenset(('diffuse', 'bump', 'roughness', 'opacity', 'metallic', 'ambient_occlusion'))
SKINS = frozenset(('Std_Skin_Head', 'Std_Skin_Body', 'Std_Skin_Arm', 'Std_Skin_Leg'))
SUPPORT_MESHES = frozenset(('CC_Base_Eye', 'CC_Base_EyeOcclusion', 'CC_Base_TearLine', 'CC_Base_Tongue', 'CC_Base_Teeth'))
EYE_SUPPORT_MESHES = frozenset(('CC_Base_Eye', 'CC_Base_EyeOcclusion', 'CC_Base_TearLine'))
RESTORE_EVIDENCE = (
    {'path': r'D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\skin_detail_optimization_20261012_v1\CFD40_AF_005\C_skin_v3\support_restore_readbacks\support_restore_readbacks.json',
     'sha256': '35163122e97d5994d5e61bdfab459f82b7072bce6546304bd67c53b84c914e50'},
    {'path': r'D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\skin_detail_optimization_20261012_v1\CFD40_LM_002\C_skin_v2\support_restore_readbacks\support_restore_readbacks.json',
     'sha256': '13698a8efcf147dc631116d623d6111e1e515cedc7fa6e7906b2364b1a5249a2'},
)
RESTORE_OPERATIONS = {
    ('CC_Base_Body', 'Std_Eyelash', 'bump'): ('load_original_texture', 'EMaterialTextureChannel_Normal'),
    ('CC_Base_Body', 'Std_Eyelash', 'diffuse'): ('load_original_texture', 'EMaterialTextureChannel_Diffuse'),
    ('CC_Base_Body', 'Std_Eyelash', 'opacity'): ('load_original_texture', 'EMaterialTextureChannel_Opacity'),
    ('CC_Base_Body', 'Std_Eyelash', 'metallic'): ('remove_to_restore_missing', 'EMaterialTextureChannel_Metallic'),
    ('CC_Base_Body', 'Std_Eyelash', 'roughness'): ('remove_to_restore_missing', 'EMaterialTextureChannel_Shininess'),
    ('CC_Base_Tongue', 'Std_Tongue', 'bump'): ('remove_to_restore_missing', 'EMaterialTextureChannel_Bump'),
    ('CC_Base_Tongue', 'Std_Tongue', 'diffuse'): ('load_original_texture', 'EMaterialTextureChannel_Diffuse'),
    ('CC_Base_Tongue', 'Std_Tongue', 'opacity'): ('load_original_texture', 'EMaterialTextureChannel_Opacity'),
}
CLOSED_LASH_OPERATIONS = {
    ('CC_Base_Body', 'Std_Eyelash', 'ambient_occlusion'): ('remove_to_restore_missing', 'EMaterialTextureChannel_AmbientOcclusion'),
    ('CC_Base_Body', 'Std_Eyelash', 'bump'): ('load_original_texture', 'EMaterialTextureChannel_Normal'),
    ('CC_Base_Body', 'Std_Eyelash', 'roughness'): ('remove_to_restore_missing', 'EMaterialTextureChannel_Shininess'),
}


def in_scope(mesh, material):
    return (mesh == 'CC_Base_Body' and material in SKINS | {'Std_Eyelash'}) or mesh in SUPPORT_MESHES


class ScopedComponent:
    def __init__(self, component, eye_support_only=False):
        self.component = component
        self.eye_support_only = eye_support_only

    def __getattr__(self, name):
        return getattr(self.component, name)

    def GetMaterialNames(self, mesh):
        if self.eye_support_only and str(mesh) not in EYE_SUPPORT_MESHES:
            return []
        return [name for name in (self.component.GetMaterialNames(mesh) or []) if in_scope(str(mesh), str(name))]


class ScopedApi:
    def __init__(self, api, eye_support_only=False):
        self.api = api
        self.eye_support_only = eye_support_only
        self.MATERIAL_TEXTURE_CHANNELS = [(name, enum) for name, enum in api.MATERIAL_TEXTURE_CHANNELS if name in CHANNELS]

    def __getattr__(self, name):
        return getattr(self.api, name)

    def hair_material_component(self, avatar, owner):
        component, source = self.api.hair_material_component(avatar, owner)
        return (ScopedComponent(component, self.eye_support_only) if component is not None else None), source


def object_record(record, store, api):
    path, digest = record['path'], record['sha256']
    if api.sha256_file(path) != digest:
        raise ValueError('Exported pixel evidence SHA changed')
    target = os.path.join(store, digest + '.png')
    if os.path.exists(target):
        if api.sha256_file(target) != digest:
            raise ValueError('Existing pixel object SHA changed')
        if os.path.realpath(path) != os.path.realpath(target):
            os.remove(path)  # Only the just-exported duplicate inside this capture.
    else:
        os.replace(path, target)
    record['path'] = target
    return record


def capture_stage(avatar, output_root, label, api):
    if label not in ('source', 'after_skin', 'after_support_restore', 'after_eyes', 'saved', 'reloaded', 'after_closed_support_restore'):
        raise ValueError('Unsupported bounded pixel checkpoint')
    exporter = importlib.import_module('cc_skin_detail_experiment_v1')
    destination = os.path.join(output_root, 'pixels_' + label)
    if os.path.exists(destination):
        raise ValueError('Refuse to reuse pixel checkpoint output')
    store = os.path.join(output_root, 'pixel_objects')
    os.makedirs(store, exist_ok=True)
    capture_error = None
    eye_support_only = label == 'after_eyes'
    scoped_api = ScopedApi(api, eye_support_only)
    try:
        result = exporter.capture_materials(avatar, destination, scoped_api)
    except Exception as exc:
        capture_error = str(exc)
        manifest = os.path.join(destination, 'materials.json')
        if os.path.isfile(manifest):
            with open(manifest, encoding='utf-8-sig') as handle:
                result = json.load(handle)
        else:
            result = {'materials': [], 'observation_errors': [{'stage': 'capture', 'error': str(exc)}]}
    decode_errors = []
    for row in result['materials']:
        for channel, record in row['textures'].items():
            object_record(record, store, api)
            record['sha256_kind'] = 'exported_png_bytes'
            try:
                image = api.QtGui.QImage(record['path'])
                record['file_decoded'] = not image.isNull()
                record['decoded_width'], record['decoded_height'] = int(image.width()), int(image.height())
                if image.isNull() or (image.width(), image.height()) != (record['width'], record['height']):
                    raise ValueError('Saved PNG is unreadable or dimensions differ from SDK image')
            except Exception as exc:
                record['file_decoded'] = False
                decode_errors.append({'owner': row['owner'], 'mesh': row['mesh'], 'material': row['material'],
                                      'channel': channel, 'error': str(exc)})
        for record in row.get('missing_textures', {}).values():
            if record.get('evidence'):
                object_record(record['evidence'], store, api)
    errors = result.get('observation_errors', [])
    missing_channels = CHANNELS - {name for name, _ in scoped_api.MATERIAL_TEXTURE_CHANNELS}
    if missing_channels:
        errors.append({'stage': 'texture:channel_scope', 'error': 'Required read channel absent: ' + ','.join(sorted(missing_channels))})
    texture_errors = [error for error in errors if str(error.get('stage', '')).startswith('texture:')
                      or error.get('stage') in CHANNELS or error.get('stage') == 'capture']
    skin_diffuse = {row['material'] for row in result['materials'] if row['mesh'] == 'CC_Base_Body'
                    and row['material'] in SKINS and row['textures'].get('diffuse', {}).get('file_decoded')}
    support_coverage = sorted({row['mesh'] for row in result['materials'] if row['mesh'] in SUPPORT_MESHES})
    required_support = set(EYE_SUPPORT_MESHES) if eye_support_only else set(EYE_SUPPORT_MESHES) | {'CC_Base_Tongue'}
    result.update(checkpoint=label, capture_exception=capture_error, decode_errors=decode_errors,
        texture_observation_errors=texture_errors,
        metadata_observation_errors=[error for error in errors if error not in texture_errors],
        skin_diffuse_coverage=sorted(skin_diffuse), support_mesh_coverage=support_coverage,
        missing_required_support_meshes=sorted(required_support - set(support_coverage)),
        pixel_capture_complete=not texture_errors and not decode_errors and (eye_support_only or skin_diffuse == SKINS)
            and required_support <= set(support_coverage),
        scope=('Native eye/occlusion/tear only; selected eye baseline before Makeup/redness; '
               if eye_support_only else 'Four skin materials plus native eye/occlusion/tear/tongue/teeth and eyelash; ')
              + 'six standard channels; SaveFile and file-decoded PNG evidence only. Custom shader slots and unselected channels are outside scope.',
        required_support_meshes=sorted(required_support),
        channel_scope=sorted(CHANNELS), warnings='Only the exporter exact known-warning SHA is recognized as a placeholder; missing channels are recorded, never substituted or loaded back.',
        material_writes=False, object_store=store)
    result['exporter_implementation_sha256'] = api.sha256_file(exporter.__file__)
    api.write_json(result, os.path.join(destination, 'materials.json'))
    return result


def compare_pixels(before, after, api, allow_skin_changes=False, allow_eye_changes=False):
    """Compare available pixels; metadata differences are diagnostic, not forbidden."""
    def keyed(snapshot):
        rows = snapshot['materials']
        result = {(row['owner'], row['mesh'], row['material']): row for row in rows}
        if len(result) != len(rows):
            raise ValueError('Duplicate exact material identity in pixel snapshot')
        return result
    old, new = keyed(before), keyed(after)
    differences, metadata_changes, permitted = [], [], []
    protected_count = 0
    for key in sorted(set(old) | set(new)):
        row = old.get(key) or new[key]
        allowed = (allow_skin_changes and key[1] == 'CC_Base_Body' and key[2] in SKINS) or (allow_eye_changes and key[1] == 'CC_Base_Eye')
        if allowed:
            permitted.append(list(key))
            continue
        protected_count += 1
        if key not in old or key not in new:
            differences.append({'key': list(key), 'reason': 'protected_material_inventory_changed'})
            continue
        a, b = old[key], new[key]
        if any(a.get(field) != b.get(field) for field in ('properties', 'shader_parameters', 'component_source')):
            metadata_changes.append(list(key))
        for channel in sorted(CHANNELS):
            left, right = a['textures'].get(channel), b['textures'].get(channel)
            if left is None and right is None:
                continue  # Both honestly missing; never compare warning graphic pixels as maps.
            difference = {'key': list(key), 'channel': channel}
            if left is None or right is None:
                differences.append(dict(difference, reason='protected_channel_availability_changed'))
            elif not left.get('file_decoded') or not right.get('file_decoded'):
                differences.append(dict(difference, reason='protected_pixels_not_decodable'))
            elif (left['width'], left['height']) != (right['width'], right['height']):
                differences.append(dict(difference, reason='protected_pixel_dimensions_changed'))
            elif left['sha256'] != right['sha256']:
                # Different PNG encoding is not automatically a changed pixel image.
                helper = importlib.import_module('cc_repair_headshot_support_materials_v1')
                comparison = helper.compare_png_images(left['path'], right['path'], api)
                if not comparison['rgba_pixels_equal']:
                    differences.append(dict(difference, reason='protected_rgba_pixels_changed', comparison=comparison))
    return {'passed': before.get('pixel_capture_complete') is True and after.get('pixel_capture_complete') is True
                and not differences and protected_count > 0,
            'protected_material_count': protected_count, 'differences': differences,
            'metadata_changes_observed_not_rejected': metadata_changes, 'authorized_materials_not_compared': permitted,
            'scope': 'Selected standard texture availability, dimensions and file-decoded RGBA pixels only; no material/texture writes or automatic restoration.'}


def restore_evidenced_support(avatar, before, after, comparison, api, output_dir):
    """Restore only the eight measured WF003 channels; all writes preflighted.

Reuse the C experiment's Normal/Shininess/RemoveMaterialTexture semantics and
immediate SaveFile readbacks. Never broaden the current difference whitelist.
"""
    return _restore_support(avatar, before, after, comparison, api, output_dir, RESTORE_OPERATIONS)


def restore_closed_lash_support(avatar, before, after, comparison, api, output_dir):
    """Only the three observed post-close lash channels; never a pixel allowance.

AO removal uses the SDK's exact AmbientOcclusion slot, with immediate missing
readback as its first real verification. Unlike Normal/Shininess it has no
retained real successful CC receipt; reports must preserve that distinction.
"""
    if not before.get('pixel_capture_complete') or not after.get('pixel_capture_complete'):
        raise ValueError('Post-close repair requires complete real source/current pixels')
    return _restore_support(avatar, before, after, comparison, api, output_dir,
        CLOSED_LASH_OPERATIONS, first_verification={('CC_Base_Body', 'Std_Eyelash', 'ambient_occlusion')})


def _restore_support(avatar, before, after, comparison, api, output_dir, operations, first_verification=frozenset()):
    exporter = importlib.import_module('cc_skin_detail_experiment_v1')
    proved = set()
    for reference in RESTORE_EVIDENCE:
        if api.sha256_file(reference['path']) != reference['sha256']:
            raise ValueError('Retained real CC restoration evidence SHA changed')
        with open(reference['path'], encoding='utf-8-sig') as handle:
            evidence = json.load(handle)
        if evidence.get('passed') is not True:
            raise ValueError('Restoration evidence is not a successful real CC receipt')
        for action in evidence['writes']:
            if action.get('passed') is True and (action.get('operation') != 'remove_to_restore_missing' or action.get('missing_after_remove') is True):
                proved.add((tuple(action['key']), action['channel'], action.get('operation'), action['load_constant']))
    old = {(row['owner'], row['mesh'], row['material']): row for row in before['materials']}
    new = {(row['owner'], row['mesh'], row['material']): row for row in after['materials']}
    grouped, plan = {}, []
    for difference in comparison['differences']:
        key, channel = tuple(difference.get('key', [])), difference.get('channel')
        if len(key) != 3 or key[0] != 'avatar' or key not in old or key not in new:
            raise ValueError('Support restore refuses an unmeasured owner/material inventory change')
        identity = (key[1], key[2], channel)
        if identity not in operations or difference.get('reason') not in (
                'protected_channel_availability_changed', 'protected_pixel_dimensions_changed', 'protected_rgba_pixels_changed'):
            raise ValueError('Support restore difference is outside the measured channel policy')
        operation, constant = operations[identity]
        if (key, channel, operation, constant) not in proved and identity not in first_verification:
            raise ValueError('No real successful CC proof for this exact operation/enum')
        source = old[key]['textures'].get(channel)
        if operation == 'load_original_texture':
            if not source or not source.get('file_decoded') or source['sha256'] in exporter.MISSING_TEXTURE_SHA256:
                raise ValueError('Only a decoded real source map may be restored; never a warning graphic')
            if api.sha256_file(source['path']) != source['sha256']:
                raise ValueError('Original source SaveFile pixels changed')
            if channel == 'bump' and not exporter.looks_like_normal_map(source['path'], api):
                raise ValueError('Measured lash map must be Normal; refusing any Bump write fallback')
        else:
            missing = old[key].get('missing_textures', {}).get(channel)
            if source is not None or not missing or missing.get('reason') not in ('sdk_known_warning_image', 'sdk_empty_image'):
                raise ValueError('Clearing requires an observed originally missing source channel')
            if missing.get('evidence') and missing['evidence']['sha256'] not in exporter.MISSING_TEXTURE_SHA256:
                raise ValueError('Unrecognized missing-map evidence; no inferred clearing')
        if old[key].get('properties', {}).get('GetShader') != new[key].get('properties', {}).get('GetShader'):
            raise ValueError('Changed support shader requires separate diagnosis before any texture write')
        grouped.setdefault(key, set()).add(channel)
        plan.append({'key': list(key), 'channel': channel, 'operation': operation, 'write_constant': constant,
                     'retained_real_operation_proof': identity not in first_verification,
                     'first_real_verification_required': identity in first_verification,
                     'source': source, 'missing_source': old[key].get('missing_textures', {}).get(channel)})
    if not plan:
        raise ValueError('No evidenced support restoration actions')
    # Legacy helper also handles added/dropped channels. Ensure it cannot infer
    # a write not already present in the audited pixel differences above.
    for key, channels in grouped.items():
        inventory_delta = set(old[key]['textures']) ^ set(new[key]['textures'])
        if not inventory_delta <= channels:
            raise ValueError('Unplanned channel inventory delta; no restoration started')
    adapted = {'differences': [{'key': list(key), 'changed': ['texture:' + name for name in sorted(channels)]}
                               for key, channels in sorted(grouped.items())]}
    os.makedirs(output_dir, exist_ok=False)
    api.write_json({'source': 'retained real C experiment and current source SaveFile maps',
        'evidence': list(RESTORE_EVIDENCE), 'actions': plan, 'skin_writes': False,
        'warning_graphic_loads': False}, os.path.join(output_dir, 'restore_plan.json'))
    writes = exporter.restore_support_textures(avatar, before, after, adapted, api,
                                              os.path.join(output_dir, 'readbacks'))
    return {'passed': bool(writes) and all(write['passed'] for write in writes), 'writes': writes,
            'evidence': list(RESTORE_EVIDENCE), 'plan_path': os.path.join(output_dir, 'restore_plan.json'),
        'scope': 'Only current measured allowed channels; exact enums and per-write SaveFile readback. Full re-capture and skin preservation must follow.',
        'first_real_verification_channels': [list(identity) for identity in sorted(first_verification)]}


def compare_skin_pixels(before, after, api):
    def skin_only(snapshot):
        selected = dict(snapshot)
        selected['materials'] = [row for row in snapshot['materials'] if row['mesh'] == 'CC_Base_Body' and row['material'] in SKINS]
        return selected
    return compare_pixels(skin_only(before), skin_only(after), api)


def compare_eye_pixels(before, after, api):
    """No eye-change allowance after the explicitly chosen eye preset."""
    def eyes_only(snapshot):
        selected = dict(snapshot)
        selected['materials'] = [row for row in snapshot['materials'] if row['mesh'] in EYE_SUPPORT_MESHES]
        selected['pixel_capture_complete'] = snapshot.get('pixel_capture_complete') is True and EYE_SUPPORT_MESHES <= {
            row['mesh'] for row in selected['materials']}
        return selected
    return compare_pixels(eyes_only(before), eyes_only(after), api)
