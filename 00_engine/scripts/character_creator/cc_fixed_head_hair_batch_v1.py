"""CC-side fixed-head hair source preparation and single-case export.

Owner: CC_TO_UE_MODULAR_OUTFIT_PILOT.md. Uses the existing offline bridge.
No Headshot generation or repeated full-character validation.
"""
import os
import hashlib
import json

RUN_ROOT = r"D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\fixed_head_hair_20261004_v1"
EXPORT_ROOT = r"D:\UE\exports\character_creator\fixed_head_hair_20261004_v1"
REFERENCE_ROOT = r"D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\headshot_route_compare_20261002_v1"


def inside(path, root):
    return os.path.commonpath([os.path.realpath(path), os.path.realpath(root)]) == os.path.realpath(root)


def run(library, output_dir, log, api):
    c = library['fixed_head_hair_batch']
    if not inside(output_dir, RUN_ROOT):
        raise ValueError('Output must be inside the fixed-head batch root')
    source = c['source_project']
    if not any(inside(source['path'], root) for root in [RUN_ROOT, REFERENCE_ROOT]):
        raise ValueError('Source outside approved reference/batch roots')
    if api.sha256_file(source['path']) != source['sha256']:
        raise ValueError('Source SHA changed')
    report = {'success': False, 'case_id': c['case_id'], 'sex': c['sex'],
              'source_project': source, 'started_at': api.now(),
              'implementation_sha256': api.sha256_file(__file__)}
    path = os.path.join(output_dir, 'fixed_head_hair_report.json')
    def mark(phase, detail=None):
        report.update(phase=phase, updated_at=api.now())
        if detail is not None:
            report[phase] = detail
        api.write_json(report, path)
        log('Fixed-head hair: ' + c['case_id'] + ' ' + phase)
        api.QtWidgets.QApplication.processEvents()
    def body_state(avatar):
        meshes = [m for m in avatar.GetMeshes(False) if m.GetName() == 'CC_Base_Body' and m.GetVerticesCount() == 14164]
        if len(meshes) != 1:
            raise ValueError('Expected one CC_Base_Body')
        coords = [[float(v.x), float(v.y), float(v.z)] for v in meshes[0].GetVertices(False)]
        return {'vertex_count': len(coords), 'vertices_sha256': hashlib.sha256(
            json.dumps(coords, separators=(',', ':')).encode()).hexdigest()}
    mark('loading')
    status, dialogs = api.load_file_with_optional_undo_warning(source['path'], 'Load approved fixed-head source')
    report['load'] = {'status': status, 'dialogs': dialogs}
    api.settle_cc_ui(1.0)
    avatar, avatars = api.resolve_avatar()
    if len(avatars) != 1:
        raise ValueError('Expected one source avatar')
    if int(avatar.GetSubdivMeshLevel()) != 0:
        api.checked('Set source working SubD0', avatar.SwitchSubdivMeshLevel(0))
    api.force_avatar_scene_evaluation(avatar, settle_seconds=0.5)
    before = body_state(avatar)
    report['body_before'] = before
    if c['action'] == 'prepare_source':
        mark('remove_attached_assets')
        report['cleanup'] = api.remove_all_attached_avatar_assets(avatar)
        api.force_avatar_scene_evaluation(avatar, settle_seconds=0.5)
        after = body_state(avatar)
        if before != after:
            raise ValueError('Removing attached assets changed body vertices')
        target = c['prepared_project_path']
        if not inside(target, RUN_ROOT) or os.path.exists(target):
            raise ValueError('Prepared source must be a new batch copy')
        os.makedirs(os.path.dirname(target), exist_ok=True)
        api.checked('Save fixed-head bare source', api.RLPy.RFileIO.SaveProject(target))
        report['prepared_project'] = {'path': target, 'sha256': api.sha256_file(target),
                                      'bytes': os.path.getsize(target)}
        report['body_after'] = after
        report['working_subdivision'] = int(avatar.GetSubdivMeshLevel())
        body = [m for m in avatar.GetMeshes(False) if m.GetName() == 'CC_Base_Body' and m.GetVerticesCount() == 14164][0]
        geometry = {'vertices': [[float(v.x), float(v.y), float(v.z)] for v in body.GetVertices(False)],
                    'world_vertices': [[float(v.x), float(v.y), float(v.z)] for v in body.GetVertices(True)],
                    'faces': [list(body.GetFace(i)) for i in range(body.GetFacesCount())],
                    'avatar_transform': api._transform_data(avatar.WorldTransform()),
                    'source_project': report['prepared_project']}
        api.write_json(geometry, os.path.join(output_dir, 'reference_body_geometry.json'))
    elif c['action'] == 'export':
        hair = c.get('hair_asset')
        if hair is not None:
            if api.sha256_file(hair['resolved_path']) != hair['sha256']:
                raise ValueError('Hair source changed')
            mark('apply_hair', {'hair_id': c['hair_id'], 'path': hair['resolved_path']})
            avatar, application = api.apply_appearance_assets(avatar, [hair], cleanup_names=[],
                allow_missing_cleanup=True, progress_callback=lambda p, d=None: mark(p, d),
                asset_load_pacing=api.resolve_asset_load_pacing(library['presets'][0]))
            report['application'] = application
            after = body_state(avatar)
            if before != after:
                raise ValueError('Hair application changed body geometry')
            report['body_after'] = after
            report['hair_meshes'] = [m.GetName() for m in avatar.GetMeshes(False)
                                     if m.GetName() not in ('CC_Base_Body',)]
        export_dir = c['export_root']
        if not inside(export_dir, EXPORT_ROOT):
            raise ValueError('Export outside batch root')
        os.makedirs(os.path.dirname(export_dir), exist_ok=True)
        api.set_avatar_yaw(avatar, 90.0)
        api.force_avatar_scene_evaluation(avatar, settle_seconds=0.5)
        mark('exporting')
        report['production_export'] = api._outfit_gate_export_reference_character(
            avatar, export_dir, c['export_basename'], output_dir, 900,
            license_wait_seconds=0, export_motion=False)
    else:
        raise ValueError('Unknown fixed-head action')
    report['success'] = True
    mark('complete')
    summary = {'success': True, 'report_path': path,
               'summary_path': os.path.join(output_dir, 'validation_result.json')}
    api.write_json(summary, summary['summary_path'])
    return summary
