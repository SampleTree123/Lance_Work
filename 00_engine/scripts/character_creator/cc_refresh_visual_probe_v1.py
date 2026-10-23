"""Independent SubD0 neutral/blink front/side SDK images; no Render1 claim."""
import math
import os
import shutil
import struct
import traceback
from collections.abc import Mapping


CREATION_ROOT = r'D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\headshot_character_creation_20261005_v1'
RUN_ROOT = r'D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\character_refresh_20261018_v1'
CAMERA_ROOT = r'D:\CharacterCreator_sucai\Reallusion Templates\Stage\Camera\Headshot Ref'
LIGHT = r'D:\CharacterCreator_sucai\Reallusion Templates\Stage\Light Room\Default\Default_CC5.ccLightroom'


def inside(path, root):
    path, root = (os.path.normcase(os.path.realpath(p)) for p in (path, root))
    return os.path.commonpath([path, root]) == root


def png_dimensions(path):
    with open(path, 'rb') as stream:
        header = stream.read(24)
    if len(header) != 24 or header[:8] != b'\x89PNG\r\n\x1a\n' or header[12:16] != b'IHDR':
        raise ValueError('SDK output is not a PNG with a valid IHDR')
    width, height = struct.unpack('>II', header[16:24])
    if not 16 <= width <= 16384 or not 16 <= height <= 16384:
        raise ValueError('SDK output has invalid image dimensions')
    return width, height


def maximum_mesh_error_mm(before, after):
    if [(m['name'], len(m['vertices'])) for m in before] != [(m['name'], len(m['vertices'])) for m in after]:
        raise ValueError('Restored mesh layout differs from independent source')
    maximum = 0.0
    for first, second in zip(before, after):
        for u, v in zip(first['vertices'], second['vertices']):
            value = math.sqrt(sum((a - b) ** 2 for a, b in zip(u, v))) * 10
            if not math.isfinite(value):
                raise ValueError('Nonfinite restored geometry')
            maximum = max(maximum, value)
    return maximum


def expression_readback(face, time_value, names, selected):
    """Record the real SDK result and align by name, without guessing units."""
    result = {'passed': False, 'threshold': 1e-5,
              'units': 'Raw SDK values; no scaling or normalization applied.'}
    try:
        raw = face.GetExpressionWeights(time_value, list(names))
        result.update(raw_return_type=type(raw).__name__, raw_return_repr=repr(raw)[:6000])
        candidates = [raw]
        if isinstance(raw, (list, tuple)):
            candidates.extend(x for x in raw if isinstance(x, (list, tuple, Mapping)))
        observed = None
        for candidate in candidates:
            try:
                if isinstance(candidate, Mapping):
                    if set(candidate) != set(names):
                        continue
                    observed = {name: float(candidate[name]) for name in names}
                elif isinstance(candidate, (list, tuple)) and len(candidate) == len(names):
                    observed = dict(zip(names, [float(value) for value in candidate]))
                else:
                    continue
                break
            except (TypeError, ValueError):
                observed = None
        if observed is None:
            result['error'] = 'SDK return cannot be matched to the complete requested expression-name list'
            return result
        result['evaluated_weights'] = observed
        result['evaluated_nonzero_weights'] = {name: value for name, value in observed.items() if abs(value) > 1e-7}
        if not all(math.isfinite(value) for value in observed.values()):
            result['error'] = 'Nonfinite raw SDK expression value'
            return result
        result['numeric_min'] = min(observed.values())
        result['numeric_max'] = max(observed.values())
        differences = [(name, abs(value - float(selected.get(name, 0)))) for name, value in observed.items()]
        result['maximum_error'] = max(value for name, value in differences)
        result['worst_mismatches'] = [
            {'name': name, 'requested': float(selected.get(name, 0)), 'observed': observed[name], 'error': value}
            for name, value in sorted(differences, key=lambda pair: -pair[1])[:16] if value > result['threshold']]
        if selected and result['numeric_max'] > 2:
            result['unit_diagnostic'] = 'Values exceed expected0..1 request scale; retained raw and rejected, not divided by100'
        result['passed'] = result['maximum_error'] <= result['threshold']
        if not result['passed']:
            result['error'] = 'Expression raw readback differs from requested complete pose'
    except Exception as error:
        result['error'] = str(error)
        result['traceback'] = traceback.format_exc()
    return result


def direct_blink_pose(names):
    """Six directly observed animation controls; C_Blink rules are not keyed."""
    names = list(names)
    selected = {}
    for aliases in [('Eye_Blink_L', 'Blink_L'), ('Eye_Blink_R', 'Blink_R'),
                    ('Eyelashes_Down_IN_L',), ('Eyelashes_Down_OUT_L',),
                    ('Eyelashes_Down_IN_R',), ('Eyelashes_Down_OUT_R',)]:
        found = next((name for name in aliases if name in names), None)
        if found is None:
            raise ValueError('Missing required directly verified blink control: ' + str(aliases))
        selected[found] = 1.0
    derived = [name for name in ('C_BlinkL', 'C_BlinkR') if name in names]
    key_names = [name for name in names if name not in derived]
    return selected, key_names, derived


def run(library, output_dir, log, api):
    config = library['refresh_visual_probe']
    if config.get('poses') != ['neutral', 'blink'] or config.get('views') != ['front', 'side']:
        raise ValueError('Only neutral/blink x front/side is implemented')
    if config.get('save_current_scene_backup') is not True or config.get('working_subdivision_level') != 0:
        raise ValueError('Explicit scene backup and actual SubD0 are required')
    if config.get('blink_pose_mode') != 'direct_six_channels_v3':
        raise ValueError('Explicit direct_six_channels_v3 pose contract required')
    sex = config.get('sex')
    if sex not in ('female', 'male'):
        raise ValueError('Explicit female/male source required')
    output_dir = os.path.realpath(output_dir)
    if not inside(output_dir, RUN_ROOT) or os.path.normcase(output_dir) == os.path.normcase(os.path.realpath(RUN_ROOT)):
        raise ValueError('Visual outputs must be an independent refresh run child')
    if os.path.exists(output_dir) and os.listdir(output_dir):
        raise ValueError('Refusing existing visual outputs')
    source = config['source_project']
    if (not source['path'].lower().endswith('.ccproject')
            or not any(inside(source['path'], root) for root in (CREATION_ROOT, RUN_ROOT))
            or api.sha256_file(source['path']) != source['sha256']):
        raise ValueError('Source project path/SHA mismatch')
    camera_path = os.path.join(CAMERA_ROOT, 'Ref Cam {} L.ccCam'.format(sex.title()))
    for label, expected in [('camera', camera_path), ('light', LIGHT)]:
        record = config[label]
        if (os.path.normcase(os.path.realpath(record['path'])) != os.path.normcase(os.path.realpath(expected))
                or api.sha256_file(record['path']) != record['sha256']):
            raise ValueError('Visual ' + label + ' path/SHA mismatch')
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, 'refresh_visual_report.json')
    summary_path = os.path.join(output_dir, 'validation_result.json')
    report = {'schema_version': 1, 'diagnostic_mode': 'refresh_visual_probe', 'success': False,
              'case_id': config['case_id'], 'sex': sex, 'source_project': source,
              'implementation_sha256': api.sha256_file(__file__), 'captures': [],
              'visual_acceptance': 'pending', 'working_subdivision_level': None,
              'render_subdivision_verified': False, 'render_subdivision_level': None,
              'material_pixels_verified': False, 'report_path': path, 'summary_path': summary_path,
              'scope': 'Actual SubD0 SDK images only. No Render1, expression quality, UE or human visual acceptance is asserted.'}
    R = api.RLPy
    attempted_source_load = False
    before_meshes = None
    working = None

    def checkpoint(phase=None):
        if phase:
            report['phase'] = phase
            log('Refresh visual: ' + phase)
        report['updated_at'] = api.now()
        api.write_json(report, path)

    def avatar():
        avatars = list(R.RScene.GetAvatars() or [])
        if len(avatars) != 1:
            raise ValueError('Expected exactly one independent visual avatar')
        return avatars[0]

    def load(record, label):
        if api.sha256_file(record['path']) != record['sha256']:
            raise ValueError('Load source SHA changed')
        status, dialogs = api.load_file_with_optional_undo_warning(record['path'], label)
        report.setdefault('loads', []).append({'label': label, 'status': status, 'dialogs': dialogs, 'source': record})
        current = avatar()
        R.RScene.SelectObject(current)
        api.force_avatar_scene_evaluation(current)
        return current

    def meshes(current):
        return [{'name': m.GetName(), 'vertices': [[float(v.x), float(v.y), float(v.z)]
                for v in m.GetVertices(False)]} for m in current.GetMeshes(False)]

    def image_record(image_path):
        width, height = png_dimensions(image_path)
        image = api.QtGui.QImage(image_path)
        if image.isNull() or image.width() != width or image.height() != height:
            raise ValueError('Saved SDK image cannot be decoded at its recorded dimensions')
        return dict(api.bodyfit_freeze_file_record(image_path), width=width, height=height,
                    image_decoded=True, aspect_ratio=float(width) / height)

    try:
        checkpoint('backing_up_current_scene')
        backup_path = os.path.join(output_dir, 'scene_before_visual.ccProject')
        api.checked('Save independent scene backup', R.RFileIO.SaveProject(backup_path))
        report['current_scene_backup'] = api.bodyfit_freeze_file_record(backup_path)
        working_path = os.path.join(output_dir, 'visual_source_copy.ccProject')
        shutil.copyfile(source['path'], working_path)
        working = api.bodyfit_freeze_file_record(working_path)
        if working['sha256'] != source['sha256']:
            raise ValueError('Independent visual source copy differs')
        report['working_source'] = working
        checkpoint('loading_independent_source')
        attempted_source_load = True
        current = load(working, 'Load independent visual source')
        level = int(current.GetSubdivMeshLevel())
        report['working_subdivision_level'] = level
        if level != 0:
            raise ValueError('Visual source must actually be active SubD0; no level switching is performed')
        before_meshes = meshes(current)
        before_path = os.path.join(output_dir, 'source_neutral_meshes.json')
        api.write_json(before_meshes, before_path)
        report['source_neutral_meshes'] = api.bodyfit_freeze_file_record(before_path)
        checkpoint('loading_verified_light_and_camera')
        api.checked('Load existing neutral light', R.RFileIO.LoadFile(config['light']['path']))
        api.checked('Load existing sex-specific reference camera', R.RFileIO.LoadFile(config['camera']['path']))
        if len(list(R.RScene.GetAvatars() or [])) != 1 or str(avatar().GetID()) != str(current.GetID()):
            raise ValueError('Camera/light load changed avatar identity')
        face = current.GetFaceComponent()
        names = list(face.GetExpressionNames('') or [])
        if not names or len(set(names)) != len(names):
            raise ValueError('Expression names are empty/ambiguous')
        blink, key_names, derived = direct_blink_pose(names)
        report.update(expression_count=len(names), resolved_targets=blink,
                      blink_pose_mode='direct_six_channels_v3',
                      independently_keyed_expression_names=key_names,
                      derived_corrective_rules_not_independently_keyed=derived,
                      corrective_rule_evaluation_verified=False,
                      expression_set_uid=str(face.GetExpressionSetUid()))
        t = R.RGlobal.GetStartTime()
        interval = R.IndexedFrameTime(0, R.RGlobal.GetFps())
        bones = [b for b in current.GetSkeletonComponent().GetSkinBones() if b.GetName() == 'CC_Base_Head']
        if len(bones) != 1:
            raise ValueError('Head/neck framing requires exactly one CC_Base_Head')
        head = bones[0]
        framing = [-80.0, 8.0, 12.0]
        api.set_avatar_position(current, *framing)
        api.set_avatar_yaw(current, 90.0)
        api.force_avatar_scene_evaluation(current)
        reference_path = os.path.join(output_dir, '_framing_reference.png')
        api.render_preview(reference_path, t)  # refresh skin-bone world transforms
        center = api._transform_data(head.WorldTransform())['translation']
        report['framing_reference'] = image_record(reference_path)
        report['fixed_head_center_world_cm'] = center
        for pose, selected in [('neutral', {}), ('blink', blink)]:
            api.checked('Begin visual expression', face.BeginKeyEditing())
            try:
                api.checked('Set visual expression', face.AddExpressionKeys(
                    t, key_names, [float(selected.get(name, 0.0)) for name in key_names], interval))
            finally:
                api.checked('End visual expression', face.EndKeyEditing())
            api.checked('Evaluate visual expression', R.RGlobal.SetTime(t, True))
            for view, yaw in [('front', 90.0), ('side', 0.0)]:
                checkpoint('render_' + pose + '_' + view)
                if int(current.GetSubdivMeshLevel()) != 0:
                    raise ValueError('Working subdivision changed during visual capture')
                api.set_avatar_yaw(current, yaw)
                api.force_avatar_scene_evaluation(current)
                unaligned = os.path.join(output_dir, '_framing_unaligned_' + pose + '_' + view + '.png')
                api.render_preview(unaligned, t)
                old_center = api._transform_data(head.WorldTransform())['translation']
                framing = [framing[j] + center[k] - old_center[k] for j, k in enumerate(('x', 'y', 'z'))]
                api.set_avatar_position(current, *framing)
                api.force_avatar_scene_evaluation(current)
                image_path = os.path.join(output_dir, pose + '_' + view + '.png')
                api.render_preview(image_path, t)
                observed_center = api._transform_data(head.WorldTransform())['translation']
                error = math.sqrt(sum((observed_center[k] - center[k]) ** 2 for k in ('x', 'y', 'z'))) * 10
                readback = expression_readback(face, t, names, selected)
                capture = {'pose': pose, 'view': view, 'yaw_degrees': yaw, 'working_subdivision_level': 0,
                    'render_subdivision_verified': False, 'target_weights': selected,
                    'evaluated_nonzero_weights': readback.get('evaluated_nonzero_weights', {}),
                    'maximum_expression_weight_error': readback.get('maximum_error'),
                    'expression_readback': readback,
                    'derived_corrective_rule_readback': {name: readback.get('evaluated_weights', {}).get(name) for name in derived},
                    'corrective_rule_evaluation_verified': False,
                    'root_position_cm': list(framing), 'head_center_world_cm': observed_center,
                    'head_center_error_mm': error, 'image': image_record(image_path)}
                report['captures'].append(capture)
                checkpoint()
                if not readback['passed']:
                    raise ValueError('Expression raw readback failed; exact values retained in capture.expression_readback')
                if error > .02:
                    raise ValueError('Head framing did not converge within0.02mm')
        report['capture_complete'] = len(report['captures']) == 4
    except Exception as error:
        report['error'] = {'type': type(error).__name__, 'message': str(error), 'traceback': traceback.format_exc()}
    finally:
        report['restoration'] = {'attempted': attempted_source_load}
        if attempted_source_load and working is not None:
            try:
                checkpoint('restoring_independent_source')
                restored = load(working, 'Restore independent visual source after temporary expressions/framing')
                after = meshes(restored)
                after_path = os.path.join(output_dir, 'restored_neutral_meshes.json')
                api.write_json(after, after_path)
                error = maximum_mesh_error_mm(before_meshes, after) if before_meshes is not None else None
                report['restoration'].update(success=True, source=working,
                    working_subdivision_level=int(restored.GetSubdivMeshLevel()),
                    neutral_meshes=api.bodyfit_freeze_file_record(after_path), maximum_local_mesh_error_mm=error)
                if int(restored.GetSubdivMeshLevel()) != 0:
                    raise ValueError('Restored source is not active SubD0')
                if error is not None and error > .002:
                    raise ValueError('Restored neutral source geometry changed beyond0.002mm')
            except Exception as error:
                report['restoration'].update(success=False, error=str(error), traceback=traceback.format_exc())
        report['source_unchanged'] = api.sha256_file(source['path']) == source['sha256']
        report['success'] = bool(report.get('capture_complete') and not report.get('error')
                                 and report['restoration'].get('success') and report['source_unchanged'])
        checkpoint('completed_visual_evidence_pending_review' if report['success'] else 'failed_visual_evidence')
    summary = {'success': report['success'], 'report_path': path, 'summary_path': summary_path,
               'captures': report['captures'], 'visual_acceptance': 'pending',
               'error': report.get('error'), 'restoration': report['restoration'],
               'source_unchanged': report['source_unchanged']}
    api.write_json(summary, summary_path)
    return summary
