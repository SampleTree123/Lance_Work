"""Bounded CC operations for the unified photo/project creation pipeline.

Reuses measured Headshot, replacement, late-bake and assembly operations.
No screenshots, expression matrix, export bundle, wardrobe or UE operations.
"""
import importlib
import importlib.util
import hashlib
import json
import os
import sys
import traceback

RUN_ROOT = r'D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\headshot_character_creation_20261005_v1'
STAGE_ROOT = os.path.join(os.path.dirname(__file__), 'runtime_staging', 'headshot_character_creation_20261005_v1')


def inside(path, root):
    path, root = map(lambda p: os.path.normcase(os.path.realpath(p)), (path, root))
    return os.path.commonpath([path, root]) == root


def _load_local_dependency(name):
    """Load the exact adjacent child afresh, independent of CC's sys.path/cache."""
    if name not in ('cc_headshot_route_validation_v1', 'cc_run_headshot_base_assembly_v1',
                    'cc_repair_headshot_support_materials_v1'):
        raise ValueError('Unsupported creation dependency')
    path = os.path.join(os.path.dirname(os.path.realpath(__file__)), name + '.py')
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError('Cannot load local creation dependency: ' + path)
    module = importlib.util.module_from_spec(spec)
    previous = sys.modules.get(name)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        if previous is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = previous
        raise
    return module


def run(library, output_dir, log, api):
    output_dir = os.path.realpath(output_dir)
    if not inside(output_dir, RUN_ROOT):
        raise ValueError('Creation output must stay in the authorized run')
    config = library['character_creation']
    source = config['source_project']
    if not any(inside(source['path'], root) for root in (RUN_ROOT, STAGE_ROOT)):
        raise ValueError('Creation source must be an independent working project')
    if api.sha256_file(source['path']) != source['sha256']:
        raise ValueError('Creation source SHA changed')
    operation = config['operation']
    appearance_mode = config.get('appearance_mode', 'assembled')
    if appearance_mode not in ('assembled', 'headshot_native'):
        raise ValueError('Unsupported creation appearance_mode')
    native = appearance_mode == 'headshot_native'
    report_path = os.path.join(output_dir, 'creation_report.json')
    report = {'schema_version': 1, 'success': False, 'operation': operation,
              'source_project': source, 'implementation_sha256': api.sha256_file(__file__),
              'appearance_mode': appearance_mode}

    def native_appearance(label, avatar=None):
        if not native:
            return
        if avatar is None:
            avatars = list(api.RLPy.RScene.GetAvatars() or [])
            if len(avatars) != 1:
                raise ValueError('Native appearance capture requires one avatar')
            avatar = avatars[0]
        meshes = []
        for mesh in avatar.GetMeshes(False) or []:
            faces = [[int(index) for index in mesh.GetFace(i)] for i in range(mesh.GetFacesCount())]
            meshes.append({'name': mesh.GetName(), 'vertex_count': int(mesh.GetVerticesCount()),
                           'face_count': len(faces), 'face_indices_sha256': hashlib.sha256(
                               json.dumps(faces, separators=(',', ':')).encode('utf-8')).hexdigest()})
        snapshot = {'appearance_mode': appearance_mode, 'working_subdivision': int(avatar.GetSubdivMeshLevel()),
                    'geometry_topology': sorted(meshes, key=lambda m: m['name']),
                    'parts': api.avatar_part_inventory(avatar), 'assets': api.avatar_asset_inventory(avatar),
                    'materials': api.avatar_material_fingerprint(avatar),
                    'sampling_scope': {'texture_pixels': '5x5 grid of ARGB samples per nonempty texture',
                                       'texture_file_sha256': False, 'all_texture_pixels_equal_proven': False},
                    'limits': ['Material fingerprint samples 25 ARGB pixels per texture, not all pixels.',
                               'Geometry topology captures face indices and counts; UV coordinates are not measured here.',
                               'No visual, expression, export, or UE acceptance is implied.']}
        path = os.path.join(output_dir, 'native_appearance_' + label + '.json')
        api.write_json(snapshot, path)
        report.setdefault('native_appearance', {})[label] = api.bodyfit_freeze_file_record(path)
        return snapshot

    def phase(name):
        report['phase'] = name
        api.write_json(report, report_path)
        log('Character creation: ' + name)
        api.QtWidgets.QApplication.processEvents()

    def load():
        status, dialogs = api.load_file_with_optional_undo_warning(source['path'], 'Load creation working copy')
        report['load'] = {'status': status, 'dialogs': dialogs}
        avatars = list(api.RLPy.RScene.GetAvatars() or [])
        if len(avatars) != 1:
            raise ValueError('Expected exactly one creation avatar')
        avatar = avatars[0]
        api.RLPy.RScene.SelectObject(avatar)
        api.force_avatar_scene_evaluation(avatar)
        return avatar

    def save(avatar, name):
        path = os.path.join(output_dir, name + '.ccProject')
        if os.path.exists(path):
            raise ValueError('Refusing to overwrite a creation project')
        api.checked('Save creation project', api.RLPy.RFileIO.SaveProject(path))
        return api.bodyfit_freeze_file_record(path)

    def body_local(avatar):
        meshes = [m for m in avatar.GetMeshes(False) if m.GetName() == 'CC_Base_Body' and m.GetVerticesCount() == 14164]
        if len(meshes) != 1:
            raise ValueError('Expected the validated CC3+ 14164-vertex topology')
        return [[float(v.x), float(v.y), float(v.z)] for v in meshes[0].GetVertices(False)]

    try:
        phase('start_' + operation)
        if native:
            if operation in ('assemble', 'repair_support'):
                raise ValueError('headshot_native is geometry-only; appearance assembly is prohibited')
            if any(config.get(field) for field in ('support_assets', 'eyelash_diffuse', 'tongue_diffuse', 'facial_components')):
                raise ValueError('headshot_native prohibits appearance support assets or overrides')
            if operation == 'photo':
                options = library.get('headshot_photo_probe', {})
                if options.get('skin_preset') != 'Clean Soft' or options.get('body_type', 'current') != 'current':
                    raise ValueError('Native photo generation requires Current + Clean Soft')
            elif operation in ('capture', 'replace'):
                probe = library.get('headshot_mesh_replace', {})
                expected = 'capture_only' if operation == 'capture' else 'normalized'
                if probe.get('mode') != expected:
                    raise ValueError('Native geometry operation requires ' + expected)
            elif operation == 'late_bake':
                if library.get('headshot_route_validation', {}).get('operation') != 'late_bake_native_control':
                    raise ValueError('Native late bake is limited to the validated geometry control')
        if operation == 'photo':
            result = api.probe_headshot_photo_generation(library, output_dir, log)
            if not result.get('success'):
                raise ValueError('Headshot generation rejected: ' + str(result.get('error')))
            report['backend'] = result
            photo_report = api.read_json(result['report_path'])
            report['saved_project'] = {'path': photo_report['project_path'], 'sha256': photo_report['project_sha256']}
        elif operation in ('capture', 'replace'):
            result = api.probe_headshot_mesh_replace(library, output_dir, log)
            if not result.get('success'):
                raise ValueError('Geometry operation rejected: ' + str(result.get('error')))
            report['backend'] = result
            if result.get('project_path'):
                report['saved_project'] = api.bodyfit_freeze_file_record(result['project_path'])
        elif operation == 'prepare':
            avatar = load()
            if int(avatar.GetSubdivMeshLevel()) != 0:
                raise ValueError('Raw Headshot input must be saved at working SubD 0')
            if len(avatar.GetFaceComponent().GetExpressionNames('')) != 379:
                raise ValueError('Use the supplied CC5 Average starter with Current + Clean Soft; CC5 profile must have379 expressions')
            if list(avatar.GetHairs() or []) or api.avatar_asset_inventory(avatar)['object_count']:
                raise ValueError('Raw input must have no scalp hair, wardrobe or props')
            native_before = native_appearance('before', avatar)
            report['support_materials'] = []
            for record in ([] if native else config.get('support_assets', [])):
                if api.sha256_file(record['path']) != record['sha256'] or not record['path'].lower().endswith(('.cceye', '.ccteeth')):
                    raise ValueError('Unsupported or changed material-only support asset')
                status, dialogs = api.load_file_with_material_only_dialog(record['path'], 'Apply creation support material only')
                report['support_materials'].append({'source': record, 'status': status, 'dialogs': dialogs})
            materials = None if native else avatar.GetMaterialComponent()
            for field, mesh, material in (('eyelash_diffuse', 'CC_Base_Body', 'Std_Eyelash'),
                                           ('tongue_diffuse', 'CC_Base_Tongue', 'Std_Tongue')):
                texture = None if native else config.get(field)
                if texture:
                    if api.sha256_file(texture['path']) != texture['sha256']:
                        raise ValueError('Support texture SHA changed')
                    api.checked('Apply supported ' + field, materials.LoadImageToTexture(mesh, material,
                        api.RLPy.EMaterialTextureChannel_Diffuse, texture['path']))
            phase('normalize_proportions_and_initial_subdivision')
            avatar, report['proportions'] = api.apply_bodyfit_proportion_adjustment(avatar, config['proportion_preset'], lambda *a: phase(a[0]))
            for level in (1, 0):
                api.checked('Normalize creation subdivision', avatar.SwitchSubdivMeshLevel(level))
                api.force_avatar_scene_evaluation(avatar)
            report['expression_count'] = len(avatar.GetFaceComponent().GetExpressionNames(''))
            report['saved_project'] = save(avatar, 'prepared_subd0')
        elif operation == 'roundtrip':
            avatar = load()
            if int(avatar.GetSubdivMeshLevel()) != 0:
                raise ValueError('Roundtrip input must be active SubD0')
            native_before = native_appearance('before', avatar)
            api.write_json({'vertices': body_local(avatar)}, os.path.join(output_dir, 'initial_0_local_and_bones.json'))
            for level in (1, 0):
                api.checked('Creation normalization switch', avatar.SwitchSubdivMeshLevel(level))
                api.force_avatar_scene_evaluation(avatar)
            api.write_json({'vertices': body_local(avatar)}, os.path.join(output_dir, 'return_0_local_and_bones.json'))
            report['saved_project'] = save(avatar, 'roundtrip_subd0')
        elif operation == 'late_bake':
            module = _load_local_dependency('cc_headshot_route_validation_v1')
            result = module.run(library, output_dir, log, api)
            backend = api.read_json(result['report_path'])
            if not backend.get('success'):
                raise ValueError('Late bake rejected: ' + str(backend.get('error')))
            report['backend'] = result
            report['saved_project'] = backend['saved_project']
        elif operation == 'assemble':
            module = _load_local_dependency('cc_run_headshot_base_assembly_v1')
            result = module.run(library, output_dir, log, api)
            if not result.get('success'):
                raise ValueError('Base assembly rejected: ' + str(result.get('error')))
            report['backend'] = result
            report['saved_project'] = result['saved_project']
        elif operation == 'repair_support':
            module = _load_local_dependency('cc_repair_headshot_support_materials_v1')
            result = module.run(library, output_dir, log, api)
            if not result.get('success'):
                raise ValueError('Support material repair rejected: ' + str(result.get('error')))
            report['backend'] = result
            report['saved_project'] = result['saved_project']
        else:
            raise ValueError('Unsupported creation operation: ' + str(operation))
        if native:
            native_after = native_appearance('after')
            if operation in ('prepare', 'roundtrip'):
                report['native_appearance']['material_metadata_unchanged'] = (
                    native_before['materials']['digest'] == native_after['materials']['digest'])
                report['native_appearance']['geometry_topology_unchanged'] = (
                    native_before['geometry_topology'] == native_after['geometry_topology'])
            report['native_appearance']['appearance_substitution_performed'] = False
            report['native_appearance']['acceptance'] = 'Read-only metadata evidence; real appearance review remains required'
        report['source_unchanged'] = api.sha256_file(source['path']) == source['sha256']
        if not report['source_unchanged']:
            raise ValueError('Working input changed')
        report['success'] = True
        phase('completed')
    except Exception as error:
        report['error'] = str(error)
        report['traceback'] = traceback.format_exc()
        phase('failed')
    report['summary_path'] = report_path
    api.write_json(report, report_path)
    return report
