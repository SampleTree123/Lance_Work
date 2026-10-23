"""Read the already-loaded representative; never load/save/apply scene content.

The existing material exporter saves RImage PNG evidence only. Shader image
accessors are inventoried with their actual SDK docstrings, not guessed/called.
"""
import importlib
import os
import traceback

CHANNELS = (('diffuse', 'EMaterialTextureChannel_Diffuse'),
            ('bump', 'EMaterialTextureChannel_Bump'),
            ('normal', 'EMaterialTextureChannel_Normal'),
            ('roughness', 'EMaterialTextureChannel_Roughness'),
            ('shininess', 'EMaterialTextureChannel_Shininess'),
            ('ambient_occlusion', 'EMaterialTextureChannel_AmbientOcclusion'),
            ('metallic', 'EMaterialTextureChannel_Metallic'),
            ('opacity', 'EMaterialTextureChannel_Opacity'))


def source_check(config, api):
    record = config['expected_loaded_source']
    if (not os.path.isfile(record['path']) or api.sha256_file(record['path']) != record['sha256']
            or os.path.getsize(record['path']) != record['bytes']):
        raise ValueError('Expected saved source pin changed; no scene access permitted')
    return record


def fingerprint(avatar):
    return {'id': str(avatar.GetID()), 'name': str(avatar.GetName()),
            'meshes': sorted(set(str(n) for n in avatar.GetMeshNames() or []))}


def run(library, output_dir, log, api):
    config = library['refresh_skin_material_readonly']
    source = source_check(config, api)
    if config.get('scene_policy') != 'current_loaded_read_only' or config['character_id'] != 'CFD40_LM_002':
        raise ValueError('This single probe is bound to the currently loaded male representative')
    avatars = list(api.RLPy.RScene.GetAvatars() or [])
    if len(avatars) != 1:
        raise ValueError('Exactly one already-loaded avatar required; this probe cannot load one')
    avatar = avatars[0]
    before = fingerprint(avatar)
    component = avatar.GetMaterialComponent()
    pixels = importlib.import_module('cc_refresh_material_pixels_v1')
    exporter = importlib.import_module('cc_skin_detail_experiment_v1')
    scoped = pixels.ScopedApi(api)
    scoped.MATERIAL_TEXTURE_CHANNELS = [(n, constant) for n, constant in CHANNELS
                                      if hasattr(api.RLPy, constant)]
    unavailable = [constant for _, constant in CHANNELS if not hasattr(api.RLPy, constant)]
    destination = os.path.join(output_dir, 'pixels_current_loaded')
    capture_error = None
    try:
        captured = exporter.capture_materials(avatar, destination, scoped)
    except Exception:
        capture_error = traceback.format_exc()
        path = os.path.join(destination, 'materials.json')
        captured = api.read_json(path) if os.path.isfile(path) else None
    shader_api = {name: str(getattr(component, name).__doc__) for name in dir(component)
                  if name.startswith('Get') and 'Shader' in name
                  and ('Image' in name or 'Texture' in name)}
    export_constants = {}
    for name in dir(api.RLPy):
        if name.startswith('EExport') and any(s in name.lower() for s in ('texture', 'pbr', 'normal', 'shader')):
            value = getattr(api.RLPy, name)
            try:
                export_constants[name] = int(value)
            except (TypeError, ValueError):
                export_constants[name] = str(value)
    setting = api.RLPy.RExportFbxSetting()
    setting_api = {name: str(getattr(setting, name).__doc__) for name in dir(setting)
                   if any(s in name.lower() for s in ('texture', 'option', 'shader')) and not name.startswith('_')}
    after = fingerprint(avatar)
    source_check(config, api)
    if before != after:
        raise ValueError('Avatar identity/mesh inventory changed during read-only capture')
    report = {'success': capture_error is None and not unavailable,
              'probe_completed': True, 'recipe_complete': False, 'accepted_final': False,
              'character_id': config['character_id'], 'scene_policy': config['scene_policy'],
              'expected_loaded_source': source,
              'loaded_source_binding_scope': 'Root must confirm this exact saved source is currently loaded; file pin plus avatar identity/inventory does not independently prove disk-to-scene equivalence.',
              'scene_before': before, 'scene_after': after,
              'channel_scope': scoped.MATERIAL_TEXTURE_CHANNELS,
              'unavailable_channel_constants': unavailable, 'capture_error': capture_error,
              'material_capture': api.bodyfit_freeze_file_record(os.path.join(destination, 'materials.json')) if captured else None,
              'shader_image_read_api': shader_api,
              'shader_images_captured': False,
              'shader_image_scope': 'Actual read accessor names/docstrings only; no guessed signatures or shader-image substitutions.',
              'export_constants': export_constants, 'export_setting_api': setting_api,
              'source_export_completeness_or_visual_acceptance': False,
              'scene_writes': False, 'image_savefile_only': True}
    report_path = os.path.join(output_dir, 'skin_material_readonly_report.json')
    api.write_json(report, report_path)
    summary = {'success': report['success'], 'probe_completed': True,
               'report_path': report_path, 'summary_path': os.path.join(output_dir, 'validation_result.json'),
               'scene_policy': config['scene_policy'], 'recipe_complete': False, 'accepted_final': False}
    api.write_json(summary, summary['summary_path'])
    log('Current loaded material channels read only; no source reload, scene save or material apply.')
    return summary
