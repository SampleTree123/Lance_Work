"""Isolated A/C skin-material experiment; no morphology or appearance randomization.

Called by the existing CC dispatcher with its API namespace. A captures the
input. C applies exactly one SHA-bound .ccSkin via the known material dialog.
Standard texture channels are exported for UE; custom shader texture slots are
explicitly outside this export and must not be inferred from parameter capture.
"""
import importlib
import os
import re
import sys
import traceback

RUN_ROOT = r'D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\skin_detail_optimization_20261012_v1'
STAGE_ROOT = os.path.join(os.path.dirname(__file__), 'runtime_staging', 'skin_detail_optimization_20261012_v1')
SKIN_MATERIALS = frozenset(('Std_Skin_Head', 'Std_Skin_Body', 'Std_Skin_Arm', 'Std_Skin_Leg'))
# CC's GetImage can return a 616px warning graphic for an unassigned channel.
# Root visually identified this exact SDK graphic on 2026-10-12. It is evidence
# of a missing channel, never usable texture content or a restoration source.
MISSING_TEXTURE_SHA256 = frozenset(('38eb6ecb3423431ffae01afeff4ad43b14260fb47874a2f10677a2ffba298385',))
MATERIAL_PROPERTIES = ('GetShader', 'GetDiffuseColor', 'GetSpecularColor', 'GetOpacity',
                       'GetGlossinessWeight', 'GetSpecularWeight', 'GetTextureWeights',
                       'GetSelfIlluminationWeight', 'GetRefraction', 'GetReflection')


def inside(path, root):
    path, root = [os.path.normcase(os.path.realpath(p)) for p in (path, root)]
    try:
        return os.path.commonpath([path, root]) == root
    except ValueError:
        return False


def helper():
    directory = os.path.dirname(__file__)
    if directory not in sys.path:
        sys.path.insert(0, directory)
    return importlib.import_module('cc_repair_headshot_support_materials_v1')


def validate_config(config, output_dir, api):
    if config.get('mode') not in ('A_capture', 'C_skin_only'):
        raise ValueError('Expected A_capture or C_skin_only')
    if not isinstance(config.get('character_id'), str) or not re.fullmatch(r'[A-Za-z0-9_-]+', config['character_id']):
        raise ValueError('character_id must be a safe nonempty identifier')
    if not inside(output_dir, RUN_ROOT) or os.path.normcase(os.path.realpath(output_dir)) == os.path.normcase(os.path.realpath(RUN_ROOT)):
        raise ValueError('Output must be an independent child of the experiment root')
    source = config['source_project']
    if not any(inside(source['path'], root) for root in (STAGE_ROOT, RUN_ROOT)):
        raise ValueError('Source must already be an independent experiment copy')
    if os.path.splitext(source['path'])[1].lower() != '.ccproject':
        raise ValueError('Source must be a ccProject')
    if api.sha256_file(source['path']) != source['sha256']:
        raise ValueError('Independent source SHA changed')
    target = os.path.join(output_dir, 'independent_' + config['mode'] + '.ccProject')
    if os.path.normcase(os.path.realpath(target)) == os.path.normcase(os.path.realpath(source['path'])):
        raise ValueError('Source cannot be overwritten')
    if os.path.exists(target) or os.path.exists(os.path.join(output_dir, 'skin_experiment_report.json')):
        raise ValueError('Existing experiment must not be rerun or overwritten')
    asset = config.get('skin_asset')
    if config['mode'] == 'A_capture':
        if asset is not None:
            raise ValueError('A_capture must not include a skin asset')
    else:
        if not isinstance(asset, dict) or asset.get('slot') != 'skin':
            raise ValueError('C_skin_only requires exactly a skin asset')
        if os.path.splitext(asset['path'])[1].lower() != '.ccskin':
            raise ValueError('Only a .ccSkin material preset may be applied')
        if api.sha256_file(asset['path']) != asset['sha256']:
            raise ValueError('Skin asset SHA changed')
    return target


def is_skin(row):
    return row['mesh'] == 'CC_Base_Body' and row['material'] in SKIN_MATERIALS


def material_owners(avatar):
    """Read avatar plus recursive parts/hairs; stable paths distinguish owners."""
    seen = set()

    def visit(owner, path):
        identity = str(owner.GetID()) if hasattr(owner, 'GetID') else str(id(owner))
        if identity in seen:
            return
        seen.add(identity)
        yield owner, path
        for accessor in ('GetAvatarParts', 'GetHairs'):
            getter = getattr(owner, accessor, None)
            for child in (getter() or []) if getter else []:
                yield from visit(child, path + '/' + accessor + ':' + str(child.GetName()))
    yield from visit(avatar, 'avatar')


def capture_materials(avatar, destination, api):
    """Save SDK images directly, avoiding the unbound GetQImage pointer."""
    os.makedirs(destination, exist_ok=False)
    records, errors, duplicate_names = [], [], []
    for owner, owner_path in material_owners(avatar):
        component, component_source = api.hair_material_component(avatar, owner)
        if component is None:
            raise ValueError('Missing material component: ' + owner_path)
        getter = getattr(owner, 'GetMeshNames', None)
        names = list(getter() or []) if getter else [mesh.GetName() for mesh in owner.GetMeshes(False) or []]
        names = [str(name) for name in names]
        if len(names) != len(set(names)):
            duplicate_names.append({'owner': owner_path, 'kind': 'mesh_names',
                                    'raw_count': len(names), 'unique_count': len(set(names))})
        # SDK material access addresses mesh/material by name, not enumeration
        # index. Some CC projects return each mesh name twice. Deduplicate names
        # only within this owner; recursive owners must remain separate.
        for mesh_name in sorted(set(names)):
            material_names = [str(name) for name in component.GetMaterialNames(mesh_name) or []]
            if len(material_names) != len(set(material_names)):
                duplicate_names.append({'owner': owner_path, 'mesh': mesh_name, 'kind': 'material_names',
                                        'raw_count': len(material_names), 'unique_count': len(set(material_names))})
            for material_name in sorted(set(material_names)):
                row = {'owner': owner_path, 'mesh': mesh_name, 'material': material_name,
                       'component_source': component_source, 'properties': {},
                       'shader_parameters': {}, 'textures': {}, 'missing_textures': {}}
                for method in MATERIAL_PROPERTIES:
                    try:
                        row['properties'][method] = api.material_call(component, method, mesh_name, material_name)
                    except Exception as exc:
                        errors.append({'owner': owner_path, 'mesh': mesh_name, 'material': material_name,
                                       'stage': method, 'error': str(exc)})
                try:
                    parameters = sorted(str(name) for name in component.GetShaderParameterNames(mesh_name, material_name) or [])
                    for name in parameters:
                        row['shader_parameters'][name] = api.material_value(component.GetShaderParameter(mesh_name, material_name, name))
                except Exception as exc:
                    errors.append({'owner': owner_path, 'mesh': mesh_name, 'material': material_name,
                                   'stage': 'shader_parameters', 'error': str(exc)})
                for channel_name, constant in api.MATERIAL_TEXTURE_CHANNELS:
                    channel = getattr(api.RLPy, constant, None)
                    if channel is None:
                        errors.append({'owner': owner_path, 'mesh': mesh_name, 'material': material_name,
                                       'stage': channel_name, 'error': 'SDK channel constant unavailable'})
                        continue
                    try:
                        texture = component.GetImage(mesh_name, material_name, channel)
                        if texture is None or texture.GetWidth() <= 0 or texture.GetHeight() <= 0:
                            row['missing_textures'][channel_name] = {'reason': 'sdk_empty_image'}
                            continue
                        filename = '{:03d}_{}_{}_{}.png'.format(len(records), re.sub(r'[^A-Za-z0-9_-]', '_', mesh_name),
                                                              re.sub(r'[^A-Za-z0-9_-]', '_', material_name), channel_name)
                        path = os.path.join(destination, filename)
                        api.checked('Export experiment material texture', texture.SaveFile(path))
                        image_record = {'path': path, 'sha256': api.sha256_file(path),
                                        'bytes': os.path.getsize(path), 'width': int(texture.GetWidth()),
                                        'height': int(texture.GetHeight())}
                        if image_record['sha256'] in MISSING_TEXTURE_SHA256:
                            row['missing_textures'][channel_name] = {'reason': 'sdk_known_warning_image',
                                                                     'evidence': image_record}
                        else:
                            row['textures'][channel_name] = image_record
                    except Exception as exc:
                        errors.append({'owner': owner_path, 'mesh': mesh_name, 'material': material_name,
                                       'stage': 'texture:' + channel_name, 'error': str(exc)})
                records.append(row)
    result = {'materials': records, 'observation_errors': errors,
              'sdk_duplicate_name_observations': duplicate_names,
              'scope': 'Standard SDK texture channels and readable shader parameters; custom shader texture slots not exported.'}
    api.write_json(result, os.path.join(destination, 'materials.json'))
    if errors:
        raise ValueError('Material capture incomplete; see materials.json observation_errors')
    found = {row['material'] for row in records if is_skin(row) and row['textures'].get('diffuse')}
    if found != SKIN_MATERIALS:
        raise ValueError('Four skin diffuse textures are required for matched head/body output')
    if not any(not is_skin(row) and row['textures'] for row in records):
        raise ValueError('No support textures captured; cannot protect supporting appearance')
    return result


def compare_materials(before, after, api, protect_skin=False):
    def keyed(snapshot):
        rows = snapshot['materials']
        result = {(r['owner'], r['mesh'], r['material']): r for r in rows}
        if len(result) != len(rows):
            raise ValueError('Duplicate material identity')
        return result
    old, new = keyed(before), keyed(after)
    differences = []
    if old.keys() != new.keys():
        differences.append({'reason': 'material_owner_or_slot_inventory_changed'})
    checked_count, skin_changed = 0, False
    for key in sorted(old.keys() & new.keys()):
        a, b = old[key], new[key]
        changes = []
        for field in ('properties', 'shader_parameters', 'component_source'):
            if a[field] != b[field]:
                changes.append(field)
        if a['textures'].keys() != b['textures'].keys():
            changes.append('texture_channel_inventory')
        if set(a.get('missing_textures', {})) != set(b.get('missing_textures', {})):
            changes.append('missing_texture_inventory')
        for channel in a['textures'].keys() & b['textures'].keys():
            left, right = a['textures'][channel], b['textures'][channel]
            if left['sha256'] != right['sha256']:
                if not helper().compare_png_images(left['path'], right['path'], api)['rgba_pixels_equal']:
                    changes.append('texture:' + channel)
        if is_skin(a):
            skin_changed = skin_changed or bool(changes)
        if protect_skin or not is_skin(a):
            checked_count += 1
            if changes:
                differences.append({'key': list(key), 'changed': changes})
    return {'passed': not differences and checked_count > 0, 'protected_material_count': checked_count,
            'skin_changed': skin_changed, 'differences': differences,
            'scope': before['scope']}


def looks_like_normal_map(path, api):
    """Recognize a blue/purple normal image, never reinterpret a gray height map."""
    image = api.QtGui.QImage(path)
    if image.isNull() or image.width() <= 0 or image.height() <= 0:
        raise ValueError('Cannot decode bump source to determine its loading semantic')
    samples = []
    for y in range(8):
        for x in range(8):
            color = image.pixelColor(min(image.width()-1, int((x+.5)*image.width()/8)),
                                     min(image.height()-1, int((y+.5)*image.height()/8)))
            samples.append(color.blue() >= 192 and 64 <= color.red() <= 192 and 64 <= color.green() <= 192)
    return sum(samples) >= 56


def restore_support_textures(avatar, before, after, comparison, api, output_dir):
    """Restore only known standard images; reject changes requiring new setters.

    Preflight the entire change before the first write. The original C capture
    remains as evidence; callers must capture and compare again after repair.
    """
    old = {(r['owner'], r['mesh'], r['material']): r for r in before['materials']}
    new = {(r['owner'], r['mesh'], r['material']): r for r in after['materials']}
    owners = dict((path, owner) for owner, path in material_owners(avatar))
    constants = dict(api.MATERIAL_TEXTURE_CHANNELS)
    actions = []
    for difference in comparison['differences']:
        key = tuple(difference.get('key', ()))
        changes = difference.get('changed', ())
        if key not in old or key not in new or is_skin(old[key]):
            raise ValueError('Support restoration cannot change material inventory')
        if any(not (change.startswith('texture:') or change in ('texture_channel_inventory', 'missing_texture_inventory')) for change in changes):
            raise ValueError('Support restoration is limited to standard textures; shader/parameter change retained for diagnosis')
        added = set(new[key]['textures']) - set(old[key]['textures'])
        if added - set(old[key].get('missing_textures', {})):
            raise ValueError('New support texture has no original missing-channel observation')
        owner = owners[key[0]]
        component, _ = api.hair_material_component(avatar, owner)
        changed_channels = {change.split(':', 1)[1] for change in changes if change.startswith('texture:')}
        changed_channels.update(set(old[key]['textures']) - set(new[key]['textures']))
        changed_channels.update(added)
        for channel in sorted(changed_channels, key=lambda item: (item == 'diffuse', item)):
            texture = old[key]['textures'].get(channel)
            if texture is not None:
                if texture['sha256'] in MISSING_TEXTURE_SHA256:
                    raise ValueError('SDK warning graphic must never be loaded as a texture')
                if api.sha256_file(texture['path']) != texture['sha256']:
                    raise ValueError('Original protected texture changed on disk')
            elif not callable(getattr(component, 'RemoveMaterialTexture', None)):
                raise ValueError('SDK RemoveMaterialTexture unavailable; cannot restore missing channel')
            # GetImage's Roughness enum is not a proven write target: the first
            # real C attempt routed it into Diffuse. Test the historic physical
            # Shininess slot explicitly, without inversion, and read back the
            # Roughness channel immediately. Normal data read from Bump uses the
            # separately verified Normal loading semantic; gray height stays Bump.
            load_constant_name = constants[channel]
            if channel == 'roughness':
                load_constant_name = 'EMaterialTextureChannel_Shininess'
            elif channel == 'bump' and texture is not None and looks_like_normal_map(texture['path'], api):
                load_constant_name = 'EMaterialTextureChannel_Normal'
            actions.append((component, key, channel, getattr(api.RLPy, constants[channel]),
                            load_constant_name, getattr(api.RLPy, load_constant_name), texture))
    if not actions:
        raise ValueError('No supported texture-only restoration was found')
    os.makedirs(output_dir, exist_ok=False)
    evidence_path = os.path.join(output_dir, 'support_restore_readbacks.json')
    result = []
    for index, (component, key, channel, read_constant, load_name, load_constant, texture) in enumerate(actions):
        row = {'key': list(key), 'channel': channel, 'load_constant': load_name,
               'operation': 'load_original_texture' if texture is not None else 'remove_to_restore_missing',
               'source_texture': texture, 'passed': False}
        result.append(row)
        api.write_json({'passed': False, 'writes': result}, evidence_path)
        try:
            if texture is None:
                api.checked('Restore originally missing support channel', component.RemoveMaterialTexture(key[1], key[2], load_constant))
            else:
                api.checked('Restore protected support texture', component.LoadImageToTexture(key[1], key[2], load_constant, texture['path']))
            image = component.GetImage(key[1], key[2], read_constant)
            empty = image is None or image.GetWidth() <= 0 or image.GetHeight() <= 0
            if not empty:
                path = os.path.join(output_dir, '{:03d}_{}.png'.format(index, channel))
                api.checked('Save immediate restoration readback', image.SaveFile(path))
                row['readback'] = {'path': path, 'sha256': api.sha256_file(path),
                                   'width': int(image.GetWidth()), 'height': int(image.GetHeight())}
            if texture is None:
                row['missing_after_remove'] = bool(empty or row['readback']['sha256'] in MISSING_TEXTURE_SHA256)
                row['passed'] = row['missing_after_remove']
            else:
                if empty:
                    raise ValueError('Restoration readback image is unavailable')
                row['pixel_comparison'] = helper().compare_png_images(texture['path'], path, api)
                row['passed'] = row['pixel_comparison']['rgba_pixels_equal']
            if not row['passed']:
                raise ValueError('Texture restore readback differs: {} {} via {}'.format(key, channel, load_name))
        except Exception as exc:
            row['error'] = str(exc)
            api.write_json({'passed': False, 'writes': result}, evidence_path)
            raise
        api.write_json({'passed': all(r['passed'] for r in result), 'writes': result}, evidence_path)
    return result


def run(library, output_dir, log, api):
    config = library['skin_detail_experiment']
    output_dir = os.path.realpath(output_dir)
    target = validate_config(config, output_dir, api)
    os.makedirs(output_dir, exist_ok=True)
    source = config['source_project']
    report_path = os.path.join(output_dir, 'skin_experiment_report.json')
    report = {'schema_version': 1, 'success': False, 'config': config,
              'started_at': api.now(), 'summary_path': report_path, 'geometry_checks': [],
              'implementation_sha256': api.sha256_file(__file__), 'visual_acceptance': 'pending',
              'source_unchanged': None, 'recovery': None}

    def phase(name):
        report.update(phase=name, updated_at=api.now())
        api.write_json(report, report_path)
        log('Skin detail experiment: ' + name)
        api.QtWidgets.QApplication.processEvents()

    def current():
        avatars = list(api.RLPy.RScene.GetAvatars() or [])
        if len(avatars) != 1:
            raise ValueError('Experiment requires exactly one avatar')
        return avatars[0]

    def check_geometry(label):
        captured = helper().capture_geometry(current(), api)
        path = os.path.join(output_dir, label + '_geometry.json')
        api.write_json(captured, path)
        result = helper().compare_geometry(before_geometry, captured)
        report['geometry_checks'].append({'phase': label, 'snapshot': path, **result})
        if not result['passed']:
            raise ValueError('Protected geometry changed: ' + label)

    try:
        phase('load_independent_source')
        status, dialogs = api.load_file_with_optional_undo_warning(source['path'], 'Load isolated skin experiment source')
        report['load'] = {'status': status, 'dialogs': dialogs}
        avatar = current()
        api.RLPy.RScene.SelectObject(avatar)
        api.force_avatar_scene_evaluation(avatar)
        if int(avatar.GetSubdivMeshLevel()) != 0:
            raise ValueError('Source must be SubD0; experiment never switches subdivision')
        before_geometry = helper().capture_geometry(avatar, api)
        if not {'CC_Base_Body', 'CC_Base_Eye', 'CC_Base_Teeth', 'CC_Base_Tongue'} <= {r['name'] for r in before_geometry['meshes']}:
            raise ValueError('Body and support geometry capture incomplete')
        api.write_json(before_geometry, os.path.join(output_dir, 'before_geometry.json'))
        phase('capture_original_materials')
        before = capture_materials(avatar, os.path.join(output_dir, 'before_materials'), api)
        if config['mode'] == 'C_skin_only':
            phase('apply_only_skin')
            status, dialogs = api.load_file_with_skin_material_dialog(config['skin_asset']['path'], 'Apply isolated material-only skin candidate')
            report['skin_application'] = {'status': status, 'dialogs': dialogs}
            api.force_avatar_scene_evaluation(current())
            check_geometry('after_skin')
        phase('capture_result_materials')
        after = capture_materials(current(), os.path.join(output_dir, 'after_materials'), api)
        comparison = compare_materials(before, after, api, protect_skin=config['mode'] == 'A_capture')
        report['initial_material_comparison'] = comparison
        final_material_dir = 'after_materials'
        if not comparison['passed'] and config['mode'] == 'C_skin_only':
            phase('restore_only_changed_support_textures')
            report['support_texture_restore'] = restore_support_textures(current(), before, after, comparison, api,
                                                                          os.path.join(output_dir, 'support_restore_readbacks'))
            api.force_avatar_scene_evaluation(current())
            check_geometry('after_support_restore')
            final_material_dir = 'after_support_restore'
            after = capture_materials(current(), os.path.join(output_dir, final_material_dir), api)
            comparison = compare_materials(before, after, api)
        report['material_preservation'] = comparison
        if not comparison['passed']:
            raise ValueError('Protected support material changed; no automatic support replacement')
        if config['mode'] == 'C_skin_only' and not comparison['skin_changed']:
            raise ValueError('Skin candidate produced no observed material change')
        check_geometry('pre_save')
        if api.sha256_file(source['path']) != source['sha256']:
            raise ValueError('Immutable source changed')
        phase('save_independent_project')
        api.checked('Save isolated skin experiment', api.RLPy.RFileIO.SaveProject(target))
        check_geometry('post_save')
        report['saved_project'] = {'path': target, 'sha256': api.sha256_file(target), 'bytes': os.path.getsize(target)}
        report['texture_manifest'] = os.path.join(output_dir, final_material_dir, 'materials.json')
        report['source_unchanged'] = api.sha256_file(source['path']) == source['sha256']
        if not report['source_unchanged']:
            raise ValueError('Source changed after save')
        report['success'] = True
        phase('completed')
    except Exception as exc:
        report.update(success=False, failed_phase=report.get('phase'),
                      error={'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()})
        try:
            if api.sha256_file(source['path']) != source['sha256']:
                raise ValueError('Cannot restore changed input')
            api.load_file_with_optional_undo_warning(source['path'], 'Restore independent experiment input')
            report['recovery'] = {'status': 'restored_input'}
        except Exception as recovery:
            report['recovery'] = {'status': 'restore_failed', 'error': str(recovery)}
        report['source_unchanged'] = api.sha256_file(source['path']) == source['sha256']
        phase('failed')
    report['finished_at'] = api.now()
    api.write_json(report, report_path)
    return report
