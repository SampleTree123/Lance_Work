"""Explicit material-only repair in independent CC copies; no appearance assembly."""
import hashlib
import json
import math
import os
import traceback

RUN_ROOT = r'D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\headshot_character_creation_20261005_v1'
STAGE_ROOT = os.path.join(os.path.dirname(__file__), 'runtime_staging', 'headshot_character_creation_20261005_v1')
REFERENCES_PATH = os.path.join(os.path.dirname(__file__), 'cc_headshot_creation_references_v1.json')
TOLERANCE_MM = 0.002


def inside(path, root):
    path, root = [os.path.normcase(os.path.realpath(p)) for p in (path, root)]
    return os.path.commonpath([path, root]) == root


def capture_geometry(avatar, api=None):
    """Include the avatar's low/high meshes and recursively its eye/teeth parts."""
    rows, parts, seen, transforms, transform_errors = [], [], set(), [], []

    def visit(owner, owner_path):
        identifier = str(owner.GetID()) if hasattr(owner, 'GetID') else str(id(owner))
        if identifier in seen:
            return
        seen.add(identifier)
        serializer = getattr(api, '_transform_data', None)
        if serializer:
            for method, label in (('LocalTransform', 'local'), ('WorldTransform', 'world')):
                getter = getattr(owner, method, None)
                if not callable(getter):
                    continue
                try:
                    transforms.append({'owner': owner_path, 'space': label, 'value': serializer(getter())})
                except Exception as error:
                    transform_errors.append({'owner': owner_path, 'space': label, 'error': str(error)})
        for mesh in owner.GetMeshes(False) or []:
            vertices = [[float(v.x), float(v.y), float(v.z)] for v in mesh.GetVertices(False)]
            if len(vertices) != int(mesh.GetVerticesCount()) or not all(math.isfinite(x) for v in vertices for x in v):
                raise ValueError('Invalid support-repair mesh capture')
            faces = [[int(x) for x in mesh.GetFace(i)] for i in range(mesh.GetFacesCount())]
            rows.append({'owner': owner_path, 'name': str(mesh.GetName()),
                         'vertex_count': len(vertices), 'face_count': len(faces),
                         'faces_sha256': hashlib.sha256(json.dumps(faces, separators=(',', ':')).encode()).hexdigest(),
                         'vertices': vertices})
        getter = getattr(owner, 'GetAvatarParts', None)
        for part in (getter() or []) if getter else []:
            name = str(part.GetName())
            part_type = str(part.GetAvatarPartType())
            path = owner_path + '/' + part_type + ':' + name
            parts.append({'name': name, 'type': part_type, 'owner': owner_path})
            visit(part, path)

    visit(avatar, 'avatar')
    rows.sort(key=lambda x: (x['owner'], x['name'], x['vertex_count'], x['face_count']))
    return {'meshes': rows, 'parts': sorted(parts, key=lambda x: (x['owner'], x['type'], x['name'])),
            'owner_transforms': sorted(transforms, key=lambda x: (x['owner'], x['space'])),
            'owner_transform_errors': transform_errors,
            'working_subdivision': int(avatar.GetSubdivMeshLevel()),
            'expression_count': len(avatar.GetFaceComponent().GetExpressionNames(''))}


def compare_geometry(before, after):
    def topology(snapshot):
        return [{k: row[k] for k in ('owner', 'name', 'vertex_count', 'face_count', 'faces_sha256')} for row in snapshot['meshes']]
    structure_same = (topology(before) == topology(after) and before['parts'] == after['parts']
                      and before['working_subdivision'] == after['working_subdivision']
                      and before['expression_count'] == after['expression_count'])
    comparisons = []
    if structure_same:
        for old, new in zip(before['meshes'], after['meshes']):
            maximum = max((math.dist(a, b) * 10 for a, b in zip(old['vertices'], new['vertices'])), default=0.)
            comparisons.append({'owner': old['owner'], 'name': old['name'], 'vertex_count': old['vertex_count'],
                                'maximum_local_delta_mm': maximum})
    maximum = max((r['maximum_local_delta_mm'] for r in comparisons), default=0.)
    old_transforms, new_transforms = before.get('owner_transforms', []), after.get('owner_transforms', [])
    transform_same = len(old_transforms) == len(new_transforms)
    transform_comparisons = []
    for old, new in zip(old_transforms, new_transforms):
        if (old['owner'], old['space']) != (new['owner'], new['space']):
            transform_same = False
            continue
        a, b = old['value'], new['value']
        def vector(value, axes):
            return [float(value[k]) for k in axes]
        translation_mm = math.dist(vector(a['translation'], 'xyz'), vector(b['translation'], 'xyz')) * 10
        aq, bq = vector(a['rotation'], 'xyzw'), vector(b['rotation'], 'xyzw')
        quaternion_delta = min(math.dist(aq, bq), math.dist(aq, [-x for x in bq]))
        # D/S/U are SDK auxiliary scale representations; record rather than
        # silently ignoring a changed available owner transform.
        auxiliary_same = {k:v for k,v in a.items() if k not in ('translation', 'rotation')} == {
            k:v for k,v in b.items() if k not in ('translation', 'rotation')}
        match = translation_mm <= TOLERANCE_MM and quaternion_delta <= 1e-6 and auxiliary_same
        transform_same = transform_same and match
        transform_comparisons.append({'owner': old['owner'], 'space': old['space'],
                                      'translation_delta_mm': translation_mm, 'quaternion_delta': quaternion_delta,
                                      'auxiliary_unchanged': auxiliary_same, 'passed': match})
    return {'passed': bool(before['meshes']) and structure_same and maximum <= TOLERANCE_MM and transform_same,
            'structure_unchanged': structure_same, 'tolerance_mm': TOLERANCE_MM,
            'maximum_local_delta_mm': maximum, 'meshes': comparisons,
            'available_owner_transforms_preserved': transform_same, 'owner_transform_checks': transform_comparisons,
            'owner_transform_observation_errors': {'before': before.get('owner_transform_errors', []),
                                                   'after': after.get('owner_transform_errors', [])}}


def compare_png_images(donor, actual, api):
    """Use Qt's file decoder, never the SDK's unbound GetQImage pointer."""
    expected, observed = api.QtGui.QImage(donor), api.QtGui.QImage(actual)
    if expected.isNull() or observed.isNull():
        raise ValueError('Cannot decode repaired support texture')
    fmt = api.QtGui.QImage.Format_RGBA8888
    same = expected.convertToFormat(fmt) == observed.convertToFormat(fmt)
    return {'donor_width': expected.width(), 'donor_height': expected.height(),
            'saved_width': observed.width(), 'saved_height': observed.height(),
            'rgba_pixels_equal': bool(same), 'method': 'Qt file-decoded RGBA image equality'}


def run(library, output_dir, log, api):
    config = library['headshot_support_repair']
    output_dir = os.path.realpath(output_dir)
    source = config['source_project']
    target = os.path.join(output_dir, 'support_materials_repaired_subd0.ccProject')
    outer = library.get('character_creation', {})
    if outer.get('appearance_mode', 'assembled') != 'assembled':
        raise ValueError('Support repair is explicit and separate from headshot_native')
    if outer.get('source_project', source) != source:
        raise ValueError('Support repair source differs from creation source')
    if not inside(output_dir, RUN_ROOT) or not any(inside(source['path'], root) for root in (RUN_ROOT, STAGE_ROOT)):
        raise ValueError('Support repair requires an independent bounded source/output')
    if os.path.exists(target):
        raise ValueError('Refusing to overwrite a support repair project')
    if api.sha256_file(source['path']) != source['sha256']:
        raise ValueError('Support repair source SHA changed')
    references = config['references_file']
    if os.path.normcase(os.path.realpath(references['path'])) != os.path.normcase(os.path.realpath(REFERENCES_PATH)):
        raise ValueError('Support repair references must be the registered adjacent file')
    if api.sha256_file(REFERENCES_PATH) != references['sha256']:
        raise ValueError('Support repair references SHA changed')
    if config.get('sex') not in ('male', 'female'):
        raise ValueError('Support repair sex must be male or female')
    selected = api.read_json(REFERENCES_PATH)['sexes'][config['sex']]
    support = selected['appearance_support_assets']
    if len(support) != 2 or [os.path.splitext(r['path'])[1].lower() for r in support] != ['.cceye', '.ccteeth']:
        raise ValueError('Expected only pinned eye and teeth material support')
    textures = [('eyelash', 'CC_Base_Body', 'Std_Eyelash', selected['eyelash_diffuse_repair']),
                ('tongue', 'CC_Base_Tongue', 'Std_Tongue', selected['tongue_diffuse'])]
    for record in support + [row[3] for row in textures]:
        if api.sha256_file(record['path']) != record['sha256']:
            raise ValueError('Pinned support source SHA changed')
    report_path = os.path.join(output_dir, 'support_repair_report.json')
    report = {'schema_version': 1, 'success': False, 'sex': config['sex'], 'source_project': source,
              'references': references,
              'implementation_sha256': api.sha256_file(__file__), 'material_only_support': [],
              'diffuse_repairs': [], 'geometry_checks': [], 'summary_path': report_path,
              'scope': 'Repair existing eyes, teeth, eyelash diffuse and tongue diffuse; no skin/brows/random assembly/proportion/subdivision changes.',
              'visual_acceptance': 'pending'}

    def phase(name):
        report['phase'] = name
        api.write_json(report, report_path)
        log('Headshot support repair: ' + name)
        api.QtWidgets.QApplication.processEvents()

    def avatar_now():
        avatars = list(api.RLPy.RScene.GetAvatars() or [])
        if len(avatars) != 1:
            raise ValueError('Support repair requires exactly one avatar')
        return avatars[0]

    def image_record(avatar, mesh, material, channel, label):
        image = avatar.GetMaterialComponent().GetImage(mesh, material, channel)
        if image is None or image.GetWidth() <= 0 or image.GetHeight() <= 0:
            raise ValueError('Expected support texture is unavailable: ' + label)
        path = os.path.join(output_dir, label + '.png')
        api.checked('Save support texture evidence', image.SaveFile(path))
        return {**api.bodyfit_freeze_file_record(path), 'width': int(image.GetWidth()), 'height': int(image.GetHeight())}

    def check_geometry(label):
        after = capture_geometry(avatar_now(), api)
        path = os.path.join(output_dir, label + '_geometry.json')
        api.write_json(after, path)
        check = compare_geometry(before, after)
        report['geometry_checks'].append({'phase': label, 'snapshot': api.bodyfit_freeze_file_record(path), **check})
        if not check['passed']:
            raise ValueError('Support-only repair changed protected local geometry at ' + label)

    try:
        phase('loading_independent_source')
        status, dialogs = api.load_file_with_optional_undo_warning(source['path'], 'Load support repair working copy')
        report['load'] = {'status': status, 'dialogs': dialogs}
        avatar = avatar_now()
        api.RLPy.RScene.SelectObject(avatar)
        api.force_avatar_scene_evaluation(avatar)
        if int(avatar.GetSubdivMeshLevel()) != 0:
            raise ValueError('Support repair source must already be active SubD0; no switching is performed')
        before = capture_geometry(avatar, api)
        names = {row['name'] for row in before['meshes']}
        if not {'CC_Base_Body', 'CC_Base_Eye', 'CC_Base_Teeth', 'CC_Base_Tongue'} <= names:
            raise ValueError('Recursive body/eyes/teeth/tongue geometry capture is incomplete')
        path = os.path.join(output_dir, 'before_geometry.json')
        api.write_json(before, path)
        report['before_geometry'] = api.bodyfit_freeze_file_record(path)
        opacity = api.RLPy.EMaterialTextureChannel_Opacity
        diffuse = api.RLPy.EMaterialTextureChannel_Diffuse
        report['eyelash_opacity_before'] = image_record(avatar, 'CC_Base_Body', 'Std_Eyelash', opacity, 'eyelash_opacity_before')
        phase('apply_pinned_material_only_support')
        for record in support:
            status, dialogs = api.load_file_with_material_only_dialog(record['path'], 'Repair existing support material only')
            report['material_only_support'].append({'source': record, 'status': status, 'dialogs': dialogs})
            api.force_avatar_scene_evaluation(avatar_now())
        component = avatar_now().GetMaterialComponent()
        phase('repair_only_eyelash_and_tongue_diffuse')
        for label, mesh, material, donor in textures:
            api.checked('Repair existing support diffuse', component.LoadImageToTexture(mesh, material, diffuse, donor['path']))
            actual = image_record(avatar_now(), mesh, material, diffuse, label + '_diffuse_after')
            pixels = compare_png_images(donor['path'], actual['path'], api)
            report['diffuse_repairs'].append({'label': label, 'mesh': mesh, 'material': material,
                                             'donor': donor, 'saved': actual, **pixels})
            if not pixels['rgba_pixels_equal']:
                raise ValueError('Saved support diffuse does not match donor pixels')
        api.force_avatar_scene_evaluation(avatar_now())
        report['eyelash_opacity_after'] = image_record(avatar_now(), 'CC_Base_Body', 'Std_Eyelash', opacity, 'eyelash_opacity_after')
        if report['eyelash_opacity_after']['sha256'] != report['eyelash_opacity_before']['sha256']:
            raise ValueError('Eyelash opacity changed during diffuse-only repair')
        report['eyelash_opacity_unchanged'] = True
        check_geometry('after_material_repair')
        phase('save_and_reload_independent_repair')
        api.checked('Save support repair project', api.RLPy.RFileIO.SaveProject(target))
        saved = api.bodyfit_freeze_file_record(target)
        api.load_file_with_optional_undo_warning(target, 'Reload independent support repair')
        api.force_avatar_scene_evaluation(avatar_now())
        check_geometry('after_reload')
        for label, mesh, material, donor in textures:
            actual = image_record(avatar_now(), mesh, material, diffuse, label + '_diffuse_reloaded')
            pixels = compare_png_images(donor['path'], actual['path'], api)
            report.setdefault('reloaded_diffuse', []).append({'label': label, 'saved': actual, **pixels})
            if not pixels['rgba_pixels_equal']:
                raise ValueError('Reloaded support diffuse does not match donor pixels')
        report['eyelash_opacity_reloaded'] = image_record(avatar_now(), 'CC_Base_Body', 'Std_Eyelash', opacity, 'eyelash_opacity_reloaded')
        if report['eyelash_opacity_reloaded']['sha256'] != report['eyelash_opacity_before']['sha256']:
            raise ValueError('Reloaded eyelash opacity changed')
        report['source_unchanged'] = api.sha256_file(source['path']) == source['sha256']
        if not report['source_unchanged']:
            raise ValueError('Support repair source changed')
        report['saved_project'] = saved
        report['success'] = True
        phase('completed')
    except Exception as error:
        report['error'] = str(error)
        report['traceback'] = traceback.format_exc()
        report['source_unchanged'] = api.sha256_file(source['path']) == source['sha256']
        phase('failed')
    api.write_json(report, report_path)
    return report
