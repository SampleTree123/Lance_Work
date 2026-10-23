"""Bounded CC-side route validation; invoked by the existing offline bridge.

All outputs are experimental copies. No canonical project or UE asset is saved.
Image review and offline geometry comparisons remain required acceptance gates.
"""
import os
import json
import math
import time
import traceback
import shutil
import hashlib


ROOT = r"D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\headshot_route_compare_20261002_v1"


def _observe_late_bake_readiness(qt, is_valid, pointer, return_control=False):
    """Inspect the same exact controls used below; never enable or click them."""
    actions, buttons, busy, controls = {}, {}, [], {}
    # Keep the wrapper ownership graph alive across return and final invoke.
    # The live probe showed a cached action invalid before return when temporary
    # allWidgets/owner wrappers were released, despite unchanged C++ pointers.
    widgets = list(qt.QApplication.allWidgets())
    owner_refs, owner_ids = [], set()
    for widget in widgets:
        if not is_valid(widget):
            continue
        try:
            if widget.isVisible():
                class_name = str(widget.metaObject().className())
                text = str(widget.text()) if hasattr(widget, 'text') else ''
                if class_name == 'CRLProgressDlg' or text.strip() == 'Updating Scene ...':
                    busy.append({'class': class_name, 'name': str(widget.objectName()), 'text': text})
            for action in widget.findChildren(qt.QAction):
                if (is_valid(action) and action.objectName() == 'qtBakeMorphSliderAction'
                        and action.text().replace('&', '') == 'Bake Morph Slider'):
                    actions[pointer(action)] = {'enabled': bool(action.isEnabled()),
                                               'visible': bool(action.isVisible())}
                    controls[('action', pointer(action))] = action
                    parent = action.parent()
                    for unused in range(32):
                        if parent is None or not is_valid(parent) or id(parent) in owner_ids:
                            break
                        owner_ids.add(id(parent))
                        owner_refs.append(parent)
                        parent = parent.parent()
            if (isinstance(widget, qt.QAbstractButton) and widget.objectName() == 'qtBakeToolButton'
                    and widget.text() == 'Bake' and widget.toolTip() == 'Bake Slider'):
                names, parent = [], widget.parentWidget()
                while parent is not None and len(names) < 20:
                    names.append(str(parent.objectName()))
                    parent = parent.parentWidget()
                if 'AvatarCreatorShaping' in names:
                    buttons[pointer(widget)] = {'enabled': bool(widget.isEnabled()),
                                               'visible': bool(widget.isVisible())}
                    controls[('button', pointer(widget))] = widget
        except RuntimeError:
            continue
    enabled_buttons = [key for key, value in buttons.items() if value['enabled']]
    ready_token = None
    if not busy:
        if len(actions) == 1:
            key = next(iter(actions))
            if actions[key]['enabled'] and actions[key]['visible']:
                ready_token = ('action', key)
        elif not actions and len(enabled_buttons) == 1:
            ready_token = ('button', enabled_buttons[0])
    result = ({'busy': busy, 'actions': list(actions.values()), 'buttons': list(buttons.values()),
               'ready': ready_token is not None}, ready_token)
    keepalive = {'widgets': widgets, 'action_owners': owner_refs}
    return result + (controls.get(ready_token), keepalive) if return_control else result


def _wait_for_late_bake_readiness(api, output_dir, timeout=180.0, clock=None, sleep=None, invoke=False):
    """Pump pending scene updates until one legal control is stably available."""
    from shiboken2 import isValid, getCppPointer
    clock, sleep = clock or time.monotonic, sleep or time.sleep
    start, previous_token, stable_count, polls = clock(), None, 0, 0
    control, keepalive, poll_history = None, None, []
    path = os.path.join(output_dir, 'late_bake_invoke_readiness.json' if invoke else 'late_bake_readiness.json')
    while True:
        api.QtWidgets.QApplication.processEvents()
        prior_token = previous_token
        if invoke:
            # Retain the returned Qt object through validation/invoke and the
            # next poll. A third scan used to discard/reacquire this reference.
            observation, token, control, keepalive = _observe_late_bake_readiness(
                api.QtWidgets, isValid, lambda x: int(getCppPointer(x)[0]), return_control=True)
        else:
            observation, token = _observe_late_bake_readiness(
                api.QtWidgets, isValid, lambda x: int(getCppPointer(x)[0]))
        stable_count = stable_count + 1 if token is not None and token == previous_token else (1 if token else 0)
        previous_token = token
        polls += 1
        elapsed = clock() - start
        record = {'scope': 'Read-only scene/control readiness; no clicks or force-enable',
                  'success': stable_count >= 2, 'elapsed_seconds': elapsed, 'poll_count': polls,
                  'stable_observations': stable_count, 'timeout_seconds': timeout,
                  'observation': observation}
        if invoke:
            record['scope'] = 'Exact stable control selection and immediate invoke; no force-enable'
            poll = {'poll': polls, 'elapsed_seconds': elapsed, 'previous_token': prior_token,
                    'token': token, 'stable_observations': stable_count,
                    'reason': 'selection_not_ready' if token is None else
                              ('await_second_stable_observation' if prior_token is None or prior_token == token
                               else 'selected_pointer_changed')}
            poll_history.append(poll)
            record['poll_history'] = poll_history
            if record['success']:
                # This poll just established uniqueness with the same selector.
                # Validate its retained object and invoke immediately: no third
                # scan, phase, capture, file IO or processEvents in between.
                available = False
                try:
                    if control is None:
                        poll['reason'] = 'selected_control_missing'
                    elif not isValid(control):
                        poll['reason'] = 'selected_control_invalid'
                    else:
                        native = {'name': str(control.objectName()), 'text': str(control.text()),
                                  'visible': bool(control.isVisible()),
                                  'method': 'Qt ' + ('action trigger' if token[0] == 'action' else 'button click')
                                            + ', no cursor or foreground activation'}
                        if token[0] == 'button':
                            native.update(tooltip='Bake Slider', ancestor='AvatarCreatorShaping')
                        if not isValid(control):
                            poll['reason'] = 'selected_control_invalid'
                        elif int(getCppPointer(control)[0]) != token[1]:
                            poll['reason'] = 'selected_control_pointer_changed'
                        elif not control.isEnabled():
                            poll['reason'] = 'selected_control_disabled'
                        elif token[0] == 'action' and not control.isVisible():
                            poll['reason'] = 'selected_action_hidden'
                        else:
                            available = True
                except RuntimeError as error:
                    available = False
                    poll['reason'] = 'selected_control_runtime_error'
                    poll['error'] = str(error)
                if available:
                    # A trigger exception must propagate; retrying it could bake twice.
                    if token[0] == 'action':
                        control.trigger()
                    else:
                        control.click()
                    poll['reason'] = 'invoked'
                    record['native_control'] = native
                    record['invoked'] = True
                    api.write_json(record, path)
                    return record
                stable_count, previous_token = 0, None
                record['success'] = False
                record['stable_observations'] = 0
        api.write_json(record, path)
        if record['success']:
            return record
        if elapsed >= timeout:
            raise TimeoutError('Late bake scene/control readiness timed out; inspect ' + path)
        sleep(min(0.1, max(0.0, timeout - elapsed)))


def run(library, output_dir, log, api):
    # The creation orchestrator reuses the measured native late-bake operation
    # inside a second explicit scope; arbitrary caller-selected roots are denied.
    ROOT = globals()['ROOT']
    execution_root = library.get('headshot_execution_root')
    if execution_root is not None:
        creation_root = r'D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\headshot_character_creation_20261005_v1'
        if os.path.normcase(os.path.realpath(execution_root)) != os.path.normcase(os.path.realpath(creation_root)):
            raise ValueError('Unsupported Headshot execution root')
        ROOT = creation_root
    c = library['headshot_route_validation']
    R = api.RLPy
    check = api.checked
    output_dir = os.path.realpath(output_dir)
    if os.path.commonpath([ROOT, output_dir]) != ROOT:
        raise ValueError('Route validation must stay inside the experiment root')
    report = {'success': False, 'case_id': c['case_id'], 'route': c['route'],
              'started_at': api.now(), 'visual_acceptance': 'pending', 'stages': {},
              'implementation_file': __file__, 'implementation_sha256': api.sha256_file(__file__),
              'eye_snapshot_mode': library.get('eye_snapshot_mode', 'sdk_t_pose'),
              'preview_capture_mode': library.get('preview_capture_mode')}
    report_path = os.path.join(output_dir, 'route_validation_report.json')

    def phase(name, details=None):
        report['phase'] = name
        report['updated_at'] = api.now()
        if details is not None:
            report['stages'][name] = details
        api.write_json(report, report_path)
        log('Headshot route validation: ' + name)
        api.QtWidgets.QApplication.processEvents()

    def load(record):
        if api.sha256_file(record['path']) != record['sha256']:
            raise ValueError('Input SHA mismatch: ' + record['path'])
        check('Load route copy', R.RFileIO.LoadFile(record['path']))
        avatars = list(R.RScene.GetAvatars() or [])
        if len(avatars) != 1:
            raise ValueError('Expected one route avatar')
        avatar = avatars[0]
        R.RScene.SelectObject(avatar)
        api.force_avatar_scene_evaluation(avatar)
        return avatar

    def state(avatar):
        face = avatar.GetFaceComponent()
        return {'subdivision': int(avatar.GetSubdivMeshLevel()),
                'max_subdivision': int(avatar.GetMaxSubdivMeshLevel()),
                'profile_uid': str(face.GetExpressionSetUid()),
                'expression_count': len(face.GetExpressionNames('')),
                'bounds': api.capture_bounds(avatar),
                'eyes': api.capture_eye_integrity_state(avatar),
                'parts': api.avatar_part_inventory(avatar),
                'materials': api.avatar_material_fingerprint(avatar),
                'bones': [{'name': b.GetName(), 'world_transform': api._transform_data(b.WorldTransform())}
                          for b in avatar.GetSkeletonComponent().GetSkinBones()],
                'vectors': api.capture_vectors(avatar)}

    def mesh_capture(avatar, label):
        api.force_avatar_scene_evaluation(avatar)
        meshes = [m for m in avatar.GetMeshes(False) if m.GetName() == 'CC_Base_Body' and m.GetVerticesCount() == 14164]
        if len(meshes) != 1:
            raise ValueError('Expected CC3+ body topology')
        mesh = meshes[0]
        record = {'vertices': [[float(v.x), float(v.y), float(v.z)] for v in mesh.GetVertices(True)],
                  'avatar_transform': api._transform_data(avatar.WorldTransform())}
        api.write_json(record, os.path.join(output_dir, label + '_world_mesh.json'))
        path = os.path.join(output_dir, label + '_body.obj')
        check('Export route body OBJ', R.RFileIO.ExportObjFile(avatar, path, R.EExport3DFileOption_BodyPart))
        return api.bodyfit_freeze_file_record(path)

    def save(avatar, label):
        path = os.path.join(output_dir, label + '.ccProject')
        if os.path.exists(path):
            raise ValueError('Refusing to overwrite candidate: ' + path)
        check('Save independent route copy', R.RFileIO.SaveProject(path))
        return api.bodyfit_freeze_file_record(path)

    def camera(avatar):
        sex_name = 'Female' if c['sex'] == 'female' else 'Male'
        light = r'D:\CharacterCreator_sucai\Reallusion Templates\Stage\Light Room\Default\Default_CC5.ccLightroom'
        cam = r'D:\CharacterCreator_sucai\Reallusion Templates\Stage\Camera\Headshot Ref\Ref Cam {} L.ccCam'.format(sex_name)
        check('Load route light', R.RFileIO.LoadFile(light))
        check('Load route camera', R.RFileIO.LoadFile(cam))
        api.set_avatar_position(avatar, 0.0, 8.0, 6.0)
        api.set_avatar_yaw(avatar, 90.0)
        api.force_avatar_scene_evaluation(avatar)

    try:
        if c.get('operation') == 'late_bake_native_control':
            source = os.path.realpath(c['source_project']['path'])
            evidence = os.path.realpath(c['geometry_evidence']['path'])
            if any(os.path.commonpath([ROOT, p]) != ROOT for p in (source, evidence)):
                raise ValueError('Late bake requires independent source and evidence')
            if api.sha256_file(evidence) != c['geometry_evidence']['sha256']:
                raise ValueError('Geometry evidence SHA mismatch')
            with open(evidence, encoding='utf-8-sig') as stream:
                prior = json.load(stream)
            if prior['candidate_project'] != c['source_project']:
                raise ValueError('Late bake must follow this exact normalized candidate')
            avatar = load(c['source_project'])
            if int(avatar.GetSubdivMeshLevel()) != 0:
                raise ValueError('Late bake requires active SubD0')
            phase('late_bake_wait_scene_and_control_ready')
            report['readiness'] = _wait_for_late_bake_readiness(api, output_dir)
            def capture_bake(label):
                component, catalog, unused = api.morph_catalog(avatar)
                meshes = []
                for mesh in avatar.GetMeshes(False):
                    row = {'name': mesh.GetName(), 'count': int(mesh.GetVerticesCount()),
                           'local': [[float(v.x), float(v.y), float(v.z)] for v in mesh.GetVertices(False)]}
                    if mesh.GetName() == 'CC_Base_Body' and row['count'] == 14164:
                        row['world'] = [[float(v.x), float(v.y), float(v.z)] for v in mesh.GetVertices(True)]
                    meshes.append(row)
                weights = {k: float(component.GetShapingMorphWeight(k)) for k in catalog}
                data = {'meshes': meshes, 'state': state(avatar),
                        'head_scale': weights['cc embed morphs/embed_full_head9'],
                        'nonzero_morphs': {k: v for k, v in weights.items() if abs(v) > 1e-7}}
                path = os.path.join(output_dir, label + '_geometry.json')
                api.write_json(data, path)
                return api.bodyfit_freeze_file_record(path), data
            phase('late_bake_before')
            report['before'], before = capture_bake('before')
            if abs(before['head_scale'] - .1) > 1e-6:
                raise ValueError('Expected measured female final Head Scale 0.1 before late bake')
            phase('late_bake_invoke_exact_control')
            report['invoke_readiness'] = _wait_for_late_bake_readiness(api, output_dir, invoke=True)
            report['native_control'] = report['invoke_readiness']['native_control']
            report['bake_actions'] = [dict(row, name='qtBakeMorphSliderAction',
                text=report['native_control']['text'])
                for row in report['invoke_readiness']['observation']['actions']]
            api.QtWidgets.QApplication.processEvents()
            api.force_avatar_scene_evaluation(avatar)
            report['after'], after = capture_bake('after')
            if abs(after['head_scale']) > 1e-7:
                raise ValueError('Bake did not reset Head Scale')
            report['local_meshes_exactly_preserved'] = (
                [(x['name'], x['count'], x['local']) for x in before['meshes']] ==
                [(x['name'], x['count'], x['local']) for x in after['meshes']])
            if not report['local_meshes_exactly_preserved']:
                raise ValueError('Late bake changed local geometry; preserve evidence and reject candidate')
            report['saved_project'] = save(avatar, 'late_baked_subd0')
            avatar = load(report['saved_project'])
            report['after_reload'], unused = capture_bake('after_reload')
            report['source_project'] = c['source_project']
            report['success'] = True
            report['acceptance'] = 'Bake control and immediate local invariance verified; roundtrip and visual gates remain'
            phase('late_bake_native_control_collected')
            result = {'success': True, 'report_path': report_path,
                      'summary_path': os.path.join(output_dir, 'validation_result.json')}
            api.write_json(result, result['summary_path'])
            return result
        if c.get('operation') == 'native_control_inventory':
            source = os.path.realpath(c['source_project']['path'])
            if os.path.commonpath([ROOT, source]) != ROOT:
                raise ValueError('Native control inspection requires an independent copy')
            avatar = load(c['source_project'])
            report['source_project'] = c['source_project']
            report['state'] = state(avatar)
            controls = []
            for widget in api.QtWidgets.QApplication.allWidgets():
                row = {'class': type(widget).__name__, 'name': str(widget.objectName()),
                       'visible': bool(widget.isVisible()), 'enabled': bool(widget.isEnabled())}
                ancestry = []
                parent = widget.parentWidget()
                while parent is not None and len(ancestry) < 12:
                    ancestry.append({'class': type(parent).__name__, 'name': str(parent.objectName()),
                                     'visible': bool(parent.isVisible())})
                    parent = parent.parentWidget()
                row['parents'] = ancestry
                if isinstance(widget, api.QtWidgets.QComboBox):
                    row.update(items=[str(widget.itemText(i)) for i in range(widget.count())],
                               current_text=str(widget.currentText()), current_index=int(widget.currentIndex()))
                elif isinstance(widget, (api.QtWidgets.QSpinBox, api.QtWidgets.QDoubleSpinBox, api.QtWidgets.QSlider)):
                    row.update(value=float(widget.value()), minimum=float(widget.minimum()), maximum=float(widget.maximum()))
                elif isinstance(widget, api.QtWidgets.QAbstractButton):
                    row.update(text=str(widget.text()), tooltip=str(widget.toolTip()))
                else:
                    continue
                controls.append(row)
            actions = []
            for widget in api.QtWidgets.QApplication.allWidgets():
                for action in widget.findChildren(api.QtWidgets.QAction):
                    row = {'text': str(action.text()), 'name': str(action.objectName()),
                           'enabled': bool(action.isEnabled()), 'visible': bool(action.isVisible())}
                    if row not in actions:
                        actions.append(row)
            report['controls'] = controls
            report['actions'] = actions
            report['avatar_methods'] = [n for n in dir(avatar) if not n.startswith('_')]
            report['morph_methods'] = [n for n in dir(avatar.GetMorphComponent()) if not n.startswith('_')]
            report['success'] = True
            report['acceptance'] = 'Read-only control inventory; no action or acceptance inferred'
            phase('native_control_inventory_collected')
            result = {'success': True, 'report_path': report_path,
                      'summary_path': os.path.join(output_dir, 'validation_result.json')}
            api.write_json(result, result['summary_path'])
            return result
        if c.get('operation') == 'current_scene_backup':
            phase('current_scene_backup')
            path = os.path.join(output_dir, 'current_scene.ccProject')
            if os.path.exists(path):
                raise ValueError('Refusing to overwrite current-scene backup')
            # Save the existing scene before loading any experiment. Do not
            # force a pose, change subdivision, or infer a source identity.
            check('Save current scene backup', R.RFileIO.SaveProject(path))
            report['backup_project'] = api.bodyfit_freeze_file_record(path)
            report['avatar_count'] = len(list(R.RScene.GetAvatars() or []))
            report['success'] = True
            phase('current_scene_backup_saved')
            result = {'success': True, 'report_path': report_path,
                      'summary_path': os.path.join(output_dir, 'validation_result.json')}
            api.write_json(result, result['summary_path'])
            return result
        if c.get('operation') == 'morph_bake_checkpoint':
            source = os.path.realpath(c['source_project']['path'])
            if os.path.commonpath([ROOT, source]) != ROOT or api.sha256_file(source) != c['source_project']['sha256']:
                raise ValueError('Morph bake requires locked independent input')
            if c.get('capture_current_after_ui'):
                if not c.get('ui_observation'):
                    raise ValueError('Current bake checkpoint requires UI observation')
                avatars = list(R.RScene.GetAvatars() or [])
                if len(avatars) != 1:
                    raise ValueError('Expected one experimental avatar')
                avatar = avatars[0]
            else:
                avatar = load(c['source_project'])
            if int(avatar.GetSubdivMeshLevel()) != 0:
                raise ValueError('Bake checkpoint requires active SubD0')
            report['source_project'] = c['source_project']
            report['ui_observation'] = c.get('ui_observation')
            def bake_capture(label):
                api.force_avatar_scene_evaluation(avatar)
                component, catalog, unused = api.morph_catalog(avatar)
                meshes = []
                for owner, is_hair in [(avatar, False)] + [(h, True) for h in avatar.GetHairs()]:
                    for m in owner.GetMeshes(False):
                        n = int(m.GetVerticesCount())
                        row = {'name':m.GetName(), 'count':n, 'is_hair':is_hair,
                               'local':[[float(v.x),float(v.y),float(v.z)] for v in m.GetVertices(False)]}
                        if not (m.GetName() == 'CC_Base_Body' and n != 14164) and not (m.GetName() == 'CC_Base_Tongue' and n != 309):
                            row['world'] = [[float(v.x),float(v.y),float(v.z)] for v in m.GetVertices(True)]
                        meshes.append(row)
                weights = {k:float(component.GetShapingMorphWeight(k)) for k in catalog}
                path = os.path.join(output_dir,label+'_geometry.json')
                api.write_json({'meshes':meshes,'head_scale':weights['cc embed morphs/embed_full_head9'],
                                'nonzero_morphs':{k:v for k,v in weights.items() if abs(v)>1e-7},
                                'state':state(avatar),'avatar_transform':api._transform_data(avatar.WorldTransform())},path)
                return api.bodyfit_freeze_file_record(path)
            report['before_save'] = bake_capture('before_save')
            report['saved_project'] = save(avatar,'morph_bake_checkpoint')
            avatar = load(report['saved_project'])
            report['after_reload'] = bake_capture('after_reload')
            report['success'] = True
            phase('morph_bake_checkpoint_collected')
            result = {'success':True,'report_path':report_path,'summary_path':os.path.join(output_dir,'validation_result.json')}
            api.write_json(result,result['summary_path'])
            return result
        if c.get('operation') == 'fixed_hair_subdivision_probe':
            source = os.path.realpath(c['source_project']['path'])
            if os.path.commonpath([ROOT, source]) != ROOT:
                raise ValueError('Hair subdivision probe requires independent source')
            avatar = load(c['source_project'])
            if int(avatar.GetSubdivMeshLevel()) != 0 or int(avatar.GetMaxSubdivMeshLevel()) < 1:
                raise ValueError('Hair subdivision probe requires saved SubD0 with existing level1')
            if not avatar.GetHairs():
                raise ValueError('Hair subdivision probe requires assembled hair')
            report['source_project'] = c['source_project']
            report['captures'] = []
            def hair_level_capture(label):
                api.force_avatar_scene_evaluation(avatar)
                level = int(avatar.GetSubdivMeshLevel())
                meshes = []
                for mesh in avatar.GetMeshes(False):
                    if mesh.GetName() != 'CC_Base_Body':
                        continue
                    meshes.append({'name':mesh.GetName(),'vertex_count':mesh.GetVerticesCount(),
                                   'vertices':[[float(v.x),float(v.y),float(v.z)] for v in mesh.GetVertices(False)]})
                hair = [{'mesh':m.GetName(),'vertex_count':m.GetVerticesCount(),
                         'local_vertices':[[float(v.x),float(v.y),float(v.z)] for v in m.GetVertices(False)],
                         'vertices':[[float(v.x),float(v.y),float(v.z)] for v in m.GetVertices(True)]}
                        for h in avatar.GetHairs() for m in h.GetMeshes(False)]
                path = os.path.join(output_dir,label+'.json')
                api.write_json({'working_subdivision_level':level,'body_local_layers':meshes,'hair':hair,
                                'avatar_transform':api._transform_data(avatar.WorldTransform())},path)
                report['captures'].append({'label':label,'working_level':level,'capture':api.bodyfit_freeze_file_record(path)})
                phase('hair_subdivision_'+label)
            if 'diagnostic_head_scale' in c:
                target = c['diagnostic_head_scale']
                if isinstance(target, bool) or target not in (0.0, 0.1):
                    raise ValueError('Head-scale diagnostic is limited to 0 or 0.1')
                hair_level_capture('before_head_scale')
                report['head_scale_diagnostic'] = api.apply_single_morph_weight(
                    avatar, 'cc embed morphs/embed_full_head9', target,
                    'Independent hair subdivision diagnostic')
                report['head_scale_diagnostic']['accepted_proportion_change'] = False
                api.force_avatar_scene_evaluation(avatar)
                phase('diagnostic_head_scale_applied')
            hair_level_capture('before0')
            for label,level in [('first1',1),('first0',0),('second1',1),('second0',0)]:
                check('Switch hair subdivision probe',avatar.SwitchSubdivMeshLevel(level))
                if int(avatar.GetSubdivMeshLevel()) != level:
                    raise ValueError('Hair subdivision switch did not apply')
                hair_level_capture(label)
            report['saved0'] = save(avatar,'hair_roundtrip_subd0')
            avatar = load(report['saved0'])
            hair_level_capture('reload0')
            check('Save hair level1 probe',avatar.SwitchSubdivMeshLevel(1))
            api.force_avatar_scene_evaluation(avatar)
            report['saved1'] = save(avatar,'hair_roundtrip_subd1')
            avatar = load(report['saved1'])
            hair_level_capture('reload1')
            check('Return hair probe level0',avatar.SwitchSubdivMeshLevel(0))
            hair_level_capture('reload1_to0')
            avatar = load(report['saved0'])
            report['success'] = True
            report['acceptance'] = 'Captured geometry across subdivision and reload; visual/render and dynamic acceptance separate'
            phase('hair_subdivision_evidence_collected')
            result = {'success':True,'report_path':report_path,
                      'summary_path':os.path.join(output_dir,'validation_result.json')}
            api.write_json(result,result['summary_path'])
            return result
        if c.get('operation') == 'hair_obj_template_probe':
            source = os.path.realpath(c['source_project']['path'])
            if os.path.commonpath([ROOT, source]) != ROOT:
                raise ValueError('Hair OBJ probe requires an independent experiment source')
            avatar = load(c['source_project'])
            if int(avatar.GetSubdivMeshLevel()) != 0 or not avatar.GetHairs():
                raise ValueError('Hair OBJ probe requires SubD0 and existing hair')
            path = os.path.join(output_dir, 'avatar_with_hair_native.obj')
            phase('export_avatar_with_hair_native_obj')
            option = R.EExport3DFileOption_AllClothes | R.EExport3DFileOption_FullBodyPart
            check('Export avatar hair OBJ template', R.RFileIO.ExportObjFile(avatar, path, option))
            report['source_project'] = c['source_project']
            report['native_obj'] = api.bodyfit_freeze_file_record(path)
            report['export_options'] = int(option)
            report['hair_meshes'] = [{'name':m.GetName(), 'vertex_count':m.GetVerticesCount()}
                                     for h in avatar.GetHairs() for m in h.GetMeshes(False)]
            report['success'] = True
            phase('hair_obj_template_collected')
            result = {'success':True,'report_path':report_path,
                      'summary_path':os.path.join(output_dir,'validation_result.json')}
            api.write_json(result,result['summary_path'])
            return result
        if c.get('operation') == 'root_alignment_probe':
            source = os.path.realpath(c['source_project']['path'])
            if os.path.commonpath([ROOT, source]) != ROOT:
                raise ValueError('Root alignment requires an independent candidate')
            avatar = load(c['source_project'])
            if int(avatar.GetSubdivMeshLevel()) != 0:
                raise ValueError('Root alignment capture requires working SubD 0')
            def alignment_capture(label):
                api.force_avatar_scene_evaluation(avatar)
                meshes = [m for m in avatar.GetMeshes(False)
                          if m.GetName() == 'CC_Base_Body' and m.GetVerticesCount() == 14164]
                if len(meshes) != 1:
                    raise ValueError('Expected one low body mesh')
                mesh = meshes[0]
                data = {'local_vertices': [[float(v.x), float(v.y), float(v.z)]
                                           for v in mesh.GetVertices(False)],
                        'world_vertices': [[float(v.x), float(v.y), float(v.z)]
                                           for v in mesh.GetVertices(True)],
                        'avatar_transform': api._transform_data(avatar.WorldTransform()),
                        'working_subdivision_level': int(avatar.GetSubdivMeshLevel())}
                api.write_json(data, os.path.join(output_dir, label + '.json'))
                return data
            phase('root_alignment_before')
            before = alignment_capture('before_alignment')
            api.set_avatar_yaw(avatar, 0.0)
            api.set_avatar_position(avatar, 0.0, 0.0, 0.0)
            aligned = alignment_capture('after_alignment')
            report['aligned_project'] = save(avatar, 'root_aligned_subd0')
            avatar = load(report['aligned_project'])
            reloaded = alignment_capture('reloaded_alignment')
            report['local_max_error_mm'] = {}
            for name, measured in [('after', aligned), ('reload', reloaded)]:
                error = max(math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))
                            for a,b in zip(before['local_vertices'], measured['local_vertices']))*10
                report['local_max_error_mm'][name] = error
                if error > 0.001:
                    raise ValueError('Root alignment unexpectedly changed local body geometry')
            report['success'] = True
            report['acceptance'] = 'Coordinate alignment only; offline rigid-world check still required'
            phase('root_alignment_collected')
            result = {'success': True, 'report_path': report_path,
                      'summary_path': os.path.join(output_dir, 'validation_result.json')}
            api.write_json(result, result['summary_path'])
            return result
        if c.get('operation') == 'tongue_diffuse_only':
            source = os.path.realpath(c['source_project']['path'])
            if os.path.commonpath([ROOT, source]) != ROOT:
                raise ValueError('Tongue repair requires an independent candidate')
            texture = c['tongue_diffuse']
            p = os.path.realpath(texture['path'])
            if os.path.commonpath([ROOT, p]) != ROOT or api.sha256_file(p) != texture['sha256']:
                raise ValueError('Tongue diffuse input path/hash mismatch')
            phase('tongue_diffuse_load_candidate')
            avatar = load(c['source_project'])
            def geometry(a):
                return [{'name':m.GetName(), 'vertices':[[float(v.x),float(v.y),float(v.z)] for v in m.GetVertices(False)]}
                        for m in a.GetMeshes(False)]
            before = geometry(avatar)
            api.write_json(before, os.path.join(output_dir, 'before_meshes_local.json'))
            component = avatar.GetMaterialComponent()
            mesh, material = 'CC_Base_Tongue', 'Std_Tongue'
            if material not in component.GetMaterialNames(mesh):
                raise ValueError('Expected existing tongue material')
            before_image = os.path.join(output_dir, 'tongue_diffuse_before.png')
            check('Save original tongue diffuse', component.GetImage(mesh,material,R.EMaterialTextureChannel_Diffuse).SaveFile(before_image))
            check('Replace only tongue diffuse', component.LoadImageToTexture(mesh,material,R.EMaterialTextureChannel_Diffuse,p))
            api.force_avatar_scene_evaluation(avatar)
            report['source_project'] = c['source_project']
            report['tongue_diffuse_source'] = texture
            report['mesh_invariance'] = {'after_application_exact': geometry(avatar) == before}
            if not report['mesh_invariance']['after_application_exact']:
                raise ValueError('Tongue material update changed local mesh vertices')
            report['repaired_project'] = save(avatar, 'tongue_repaired_subd1')
            avatar = load(report['repaired_project'])
            after = geometry(avatar)
            api.write_json(after, os.path.join(output_dir, 'reloaded_meshes_local.json'))
            report['mesh_invariance']['after_reload_exact'] = after == before
            if [ (x['name'],len(x['vertices'])) for x in after] != [(x['name'],len(x['vertices'])) for x in before]:
                raise ValueError('Reloaded repair mesh layout changed')
            report['mesh_invariance']['reload_max_delta_mm'] = max(
                math.sqrt(sum((v-w)**2 for v,w in zip(a,b)))*10
                for old,new in zip(before,after) for a,b in zip(old['vertices'],new['vertices']))
            after_image = os.path.join(output_dir, 'tongue_diffuse_reloaded.png')
            check('Save reloaded tongue diffuse', avatar.GetMaterialComponent().GetImage(mesh,material,R.EMaterialTextureChannel_Diffuse).SaveFile(after_image))
            report['reloaded_texture'] = api.bodyfit_freeze_file_record(after_image)
            report['texture_sha_equal'] = report['reloaded_texture']['sha256'] == texture['sha256']
            if not report['texture_sha_equal']:
                raise ValueError('Reloaded tongue diffuse SHA mismatch')
            report['success'] = True
            report['acceptance'] = 'Isolated tongue diffuse repair and reload only; visual acceptance pending'
            phase('tongue_diffuse_repair_collected')
            result = {'success': True, 'report_path': report_path,
                      'summary_path': os.path.join(output_dir, 'validation_result.json')}
            api.write_json(result, result['summary_path'])
            return result
        if c.get('operation') == 'sdk_face_preview':
            # Separate from observed Render1 reviews: the SDK only verifies the
            # active working level. Reload the source after temporary pose keys.
            source = os.path.realpath(c['source_project']['path'])
            if os.path.commonpath([ROOT, source]) != ROOT:
                raise ValueError('Face preview requires an independent source')
            avatar = load(c['source_project'])
            if int(avatar.GetSubdivMeshLevel()) != 1:
                raise ValueError('Face preview requires working SubD1')
            def neutral_digests(a):
                return [{'name': m.GetName(), 'count': m.GetVerticesCount(),
                         'sha256': hashlib.sha256(json.dumps(
                             [[float(v.x), float(v.y), float(v.z)] for v in m.GetVertices(False)],
                             separators=(',', ':')).encode('utf-8')).hexdigest()}
                        for m in a.GetMeshes(False)]
            report['before_neutral_mesh_digests'] = neutral_digests(avatar)
            face = avatar.GetFaceComponent()
            names = list(face.GetExpressionNames('') or [])
            specs, targets = api.profile_upgrade_pose_specs(names)
            report['expression_count'] = len(names)
            report['profile_uid'] = str(face.GetExpressionSetUid())
            report['resolved_targets'] = targets
            report['source_project'] = c['source_project']
            report['render_subdivision_verified'] = False
            report['captures'] = []
            t = R.RGlobal.GetStartTime()
            interval = R.IndexedFrameTime(0, R.RGlobal.GetFps())
            try:
                for pose, weights_by_name in [('neutral', {}), ('blink', specs['blink_bilateral_front']),
                                              ('smile', specs['smile_broad_front']), ('jaw_open', specs['jaw_open_front'])]:
                    phase('sdk_face_preview_' + pose)
                    camera(avatar)
                    check('Begin face preview expression', face.BeginKeyEditing())
                    try:
                        check('Set face preview expression', face.AddExpressionKeys(
                            t, names, [float(weights_by_name.get(name, 0.0)) for name in names], interval))
                    finally:
                        check('End face preview expression', face.EndKeyEditing())
                    check('Evaluate face preview expression', R.RGlobal.SetTime(t, True))
                    api.force_avatar_scene_evaluation(avatar)
                    path = os.path.join(output_dir, pose + '_front.png')
                    api.render_preview(path, t)
                    report['captures'].append({'pose': pose, 'image': api.bodyfit_freeze_file_record(path),
                        'target_weights': weights_by_name,
                        'evaluated_weights': dict(zip(sorted(weights_by_name),
                            api.expression_weights_at(face, t, sorted(weights_by_name)))) if weights_by_name else {}})
            finally:
                avatar = load(c['source_project'])
                report['reloaded_neutral_mesh_digests'] = neutral_digests(avatar)
                report['restored_state'] = state(avatar)
            if report['before_neutral_mesh_digests'] != report['reloaded_neutral_mesh_digests']:
                raise ValueError('Face preview reload changed neutral local meshes')
            report['success'] = True
            report['acceptance'] = 'Working SubD1 SDK previews only; framing and visual review required; Render level unverified'
            phase('sdk_face_preview_evidence_collected')
            result = {'success': True, 'report_path': report_path,
                      'summary_path': os.path.join(output_dir, 'validation_result.json')}
            api.write_json(result, result['summary_path'])
            return result
        if c.get('operation') == 'current_verified_face_multiview':
            level = c.get('observed_render_level')
            if level != 1 or c.get('observed_viewport_level') != 1 or not c.get('ui_observation'):
                raise ValueError('Face review requires observed Viewport1/Render1')
            source = os.path.realpath(c['source_project']['path'])
            if os.path.commonpath([ROOT, source]) != ROOT or api.sha256_file(source) != c['source_project']['sha256']:
                raise ValueError('Face review source lineage mismatch')
            avatars = list(R.RScene.GetAvatars() or [])
            if len(avatars) != 1 or int(avatars[0].GetSubdivMeshLevel()) != 1:
                raise ValueError('Current face review avatar level mismatch')
            avatar = avatars[0]
            phase('save_observed_face_review_copy')
            baseline = save(avatar, 'observed_render1')
            report['observed_project'] = baseline
            report['source_project'] = c['source_project']
            report['ui_observation'] = c['ui_observation']
            report['observed_render_level'] = 1
            report['observed_viewport_level'] = 1
            if c.get('record_neutral_meshes'):
                def record_neutral_geometry(a, label):
                    meshes = [{'name': m.GetName(), 'vertices': [[float(v.x), float(v.y), float(v.z)]
                               for v in m.GetVertices(False)]} for m in a.GetMeshes(False)]
                    path = os.path.join(output_dir, label + '_neutral_meshes.json')
                    api.write_json(meshes, path)
                    return api.bodyfit_freeze_file_record(path)
                report['before_neutral_meshes'] = record_neutral_geometry(avatar, 'before')
                p = os.path.join(output_dir, 'head_diffuse.png')
                check('Save observed head diffuse', avatar.GetMaterialComponent().GetImage(
                      'CC_Base_Body', 'Std_Skin_Head', R.EMaterialTextureChannel_Diffuse).SaveFile(p))
                report['head_diffuse'] = api.bodyfit_freeze_file_record(p)
            camera(avatar)
            face = avatar.GetFaceComponent()
            if c.get('full_head_neck_views'):
                framing_position = [-80.0, 8.0, 12.0]
                api.set_avatar_position(avatar, *framing_position)
                api.force_avatar_scene_evaluation(avatar)
                report['full_head_neck_framing'] = {'avatar_position_cm': list(framing_position),
                    'acceptance': 'Framing must be inspected in rendered images; not an automatic visual pass'}
                head_bones = [b for b in avatar.GetSkeletonComponent().GetSkinBones()
                              if b.GetName() == 'CC_Base_Head']
                if len(head_bones) != 1:
                    raise ValueError('Full-head framing requires one CC_Base_Head bone')
                api.render_preview(os.path.join(output_dir, '_framing_reference.png'))
                head_center = api._transform_data(head_bones[0].WorldTransform())['translation']
                report['full_head_neck_framing']['fixed_head_center_world_cm'] = head_center
                report['full_head_neck_framing']['views'] = []
            names = list(face.GetExpressionNames('') or [])
            specs, targets = api.profile_upgrade_pose_specs(names)
            report['resolved_targets'] = targets
            report['expression_count'] = len(names)
            report['profile_uid'] = str(face.GetExpressionSetUid())
            t = R.RGlobal.GetStartTime()
            interval = R.IndexedFrameTime(0, R.RGlobal.GetFps())
            report['captures'] = []
            chosen = [('neutral', {}), ('blink', specs['blink_bilateral_front']),
                      ('smile', specs['smile_broad_front']), ('jaw_open', specs['jaw_open_front'])]
            if c.get('capture_poses'):
                requested = set(c['capture_poses'])
                if not requested.issubset({name for name, _ in chosen}):
                    raise ValueError('Unsupported face review pose selection')
                chosen = [(name, values) for name, values in chosen if name in requested]
            isolation = bool(c.get('eyelid_isolation'))
            component = avatar.GetMaterialComponent()
            material_isolation = c.get('eyelid_material_isolation')
            if isolation and material_isolation:
                raise ValueError('Run weight and material isolation separately')
            if isolation:
                full = specs['blink_bilateral_front']
                base = {k:v for k,v in full.items() if k.startswith('Eye_Blink_')}
                lashes = {k:v for k,v in full.items() if k.startswith('Eyelashes_')}
                corrective = {k:v for k,v in full.items() if k.startswith('C_Blink')}
                if len(base) != 2 or len(corrective) != 2 or len(lashes) != 4:
                    raise ValueError('Unexpected blink isolation target layout')
                if 'Std_Eyelash' not in component.GetMaterialNames('CC_Base_Body'):
                    raise ValueError('Expected eyelash material on body')
                report['original_eyelash_opacity'] = float(component.GetOpacity('CC_Base_Body', 'Std_Eyelash'))
                variants = [('base', base), ('base_lashes', dict(base, **lashes)),
                            ('base_corrective', dict(base, **corrective)), ('full', full)]
                chosen = [(pose + '_' + visibility, values) for visibility in ('visible', 'hidden')
                          for pose, values in variants]
            if material_isolation:
                for texture in material_isolation.values():
                    p = os.path.realpath(texture['path'])
                    if os.path.commonpath([ROOT, p]) != ROOT or api.sha256_file(p) != texture['sha256']:
                        raise ValueError('Diagnostic texture path/hash mismatch')
                chosen = [(mode, specs['blink_bilateral_front']) for mode in
                          ('original_lashes_hidden', 'flat_diffuse', 'flat_diffuse_normal', 'flat_no_eye_support')]
                report['diagnostic_texture_inputs'] = material_isolation
                report['original_head_textures'] = []
                for channel in ('Diffuse', 'Bump', 'Normal'):
                    path = os.path.join(output_dir, 'original_head_' + channel + '.png')
                    original = component.GetImage('CC_Base_Body', 'Std_Skin_Head', getattr(R, 'EMaterialTextureChannel_' + channel))
                    if original is None:
                        report['original_head_textures'].append({'channel': channel, 'available': False})
                        continue
                    check('Export diagnostic original head ' + channel, original.SaveFile(path))
                    report['original_head_textures'].append(api.bodyfit_freeze_file_record(path))
            try:
                for pose, targets_for_pose in chosen:
                    if isolation:
                        opacity = 0.0 if pose.endswith('_hidden') else report['original_eyelash_opacity']
                        key = R.RKey()
                        key.SetTime(t)
                        check('Set diagnostic eyelash opacity', component.AddOpacityKey(key, 'CC_Base_Body', 'Std_Eyelash', opacity))
                    if material_isolation:
                        key = R.RKey()
                        key.SetTime(t)
                        check('Hide diagnostic eyelashes', component.AddOpacityKey(key, 'CC_Base_Body', 'Std_Eyelash', 0.0))
                        if pose != 'original_lashes_hidden':
                            check('Diagnostic flat head diffuse', component.LoadImageToTexture('CC_Base_Body', 'Std_Skin_Head',
                                  R.EMaterialTextureChannel_Diffuse, material_isolation['diffuse']['path']))
                        if pose in ('flat_diffuse_normal', 'flat_no_eye_support'):
                            check('Diagnostic flat head normal', component.LoadImageToTexture('CC_Base_Body', 'Std_Skin_Head',
                                  R.EMaterialTextureChannel_Normal, material_isolation['normal']['path']))
                        if pose == 'flat_no_eye_support':
                            for mesh_name in ('CC_Base_EyeOcclusion', 'CC_Base_TearLine'):
                                for material_name in component.GetMaterialNames(mesh_name):
                                    check('Hide diagnostic eye support', component.AddOpacityKey(key, mesh_name, material_name, 0.0))
                    weights = [float(targets_for_pose.get(name, 0.0)) for name in names]
                    check('Begin multiview expression', face.BeginKeyEditing())
                    try:
                        check('Set multiview expression', face.AddExpressionKeys(t, names, weights, interval))
                    finally:
                        check('End multiview expression', face.EndKeyEditing())
                    check('Evaluate multiview expression', R.RGlobal.SetTime(t, True))
                    views = [('front', 90.0), ('quarter_left', 45.0), ('quarter_right', 135.0), ('side', 0.0)]
                    if c.get('full_head_neck_views') and pose == 'neutral':
                        views += [('opposite_side', 180.0), ('back', -90.0)]
                    if c.get('capture_views'):
                        requested_views = set(c['capture_views'])
                        if not requested_views.issubset({name for name, _ in views}):
                            raise ValueError('Unsupported view selection for pose ' + pose)
                        views = [(name, yaw) for name, yaw in views if name in requested_views]
                    if isolation or material_isolation:
                        views = views[:3]
                    for view, yaw in views:
                        phase('face_multiview_' + pose + '_' + view)
                        api.set_avatar_yaw(avatar, yaw)
                        api.force_avatar_scene_evaluation(avatar)
                        if c.get('full_head_neck_views'):
                            # Bone world transforms can retain the previous evaluation
                            # after a root transform; render first to refresh them.
                            api.render_preview(os.path.join(output_dir, '_framing_unaligned_' + pose + '_' + view + '.png'))
                            current_head = api._transform_data(head_bones[0].WorldTransform())['translation']
                            # Transform-control position differs from WorldTransform
                            # translation by the rotated source-root offset.
                            position = [framing_position[j] + head_center[k] - current_head[k]
                                        for j,k in enumerate(('x', 'y', 'z'))]
                            api.set_avatar_position(avatar, *position)
                            framing_position = position
                            api.force_avatar_scene_evaluation(avatar)
                        path = os.path.join(output_dir, pose + '_' + view + '.png')
                        api.render_preview(path, t)
                        if c.get('full_head_neck_views'):
                            observed_head = api._transform_data(head_bones[0].WorldTransform())['translation']
                            report['full_head_neck_framing']['views'].append({'pose': pose, 'view': view,
                                'before_world_cm': current_head, 'root_position_cm': position,
                                'after_world_cm': observed_head,
                                'center_error_mm': math.sqrt(sum((observed_head[k]-head_center[k])**2 for k in ('x','y','z')))*10})
                            if report['full_head_neck_framing']['views'][-1]['center_error_mm'] > 0.02:
                                raise ValueError('Head centering did not converge; reject incomplete framing')
                        capture = {'pose': pose, 'view': view,
                            'target_weights': targets_for_pose,
                            'evaluated_weights': dict(zip(sorted(targets_for_pose), api.expression_weights_at(face, t, sorted(targets_for_pose)))) if targets_for_pose else {},
                            'image': api.bodyfit_freeze_file_record(path)}
                        if isolation:
                            capture['eyelash_opacity'] = float(component.GetOpacity('CC_Base_Body', 'Std_Eyelash'))
                            if abs(capture['eyelash_opacity'] - opacity) > 1e-6:
                                raise ValueError('Diagnostic eyelash opacity readback mismatch')
                            capture['local_mesh_digests'] = [{'name': m.GetName(), 'count': m.GetVerticesCount(),
                                'sha256': hashlib.sha256(json.dumps([[float(v.x),float(v.y),float(v.z)]
                                    for v in m.GetVertices(False)], separators=(',', ':')).encode('utf-8')).hexdigest()}
                                for m in avatar.GetMeshes(False)]
                        if material_isolation:
                            capture['material_opacity_readback'] = {mesh_name: {material_name: float(component.GetOpacity(mesh_name, material_name))
                                for material_name in component.GetMaterialNames(mesh_name)}
                                for mesh_name in ('CC_Base_Body', 'CC_Base_EyeOcclusion', 'CC_Base_TearLine')}
                        report['captures'].append(capture)
            finally:
                # Reload the independent baseline; no expression edits survive in the source.
                avatar = load(baseline)
                report['restored_state'] = state(avatar)
                if c.get('record_neutral_meshes'):
                    report['reloaded_neutral_meshes'] = record_neutral_geometry(avatar, 'reloaded')
            report['success'] = True
            report['acceptance'] = 'Render1 multiview evidence only; eye/oral visual review and Average remain separate gates'
            phase('face_multiview_evidence_collected')
            result = {'success': True, 'report_path': report_path,
                      'summary_path': os.path.join(output_dir, 'validation_result.json')}
            api.write_json(result, result['summary_path'])
            return result
        if c.get('operation') == 'restore_source_only':
            phase('restore_source_load')
            source = os.path.realpath(c['source_project']['path'])
            if os.path.commonpath([ROOT, source]) != ROOT:
                raise ValueError('Restore must use a saved independent experiment project')
            avatar = load(c['source_project'])
            report['restored_source'] = c['source_project']
            report['restored_state'] = state(avatar)
            shaping, catalog, _ = api.morph_catalog(avatar)
            report['diagnostic_morph_weights'] = [
                {'id': mid, 'weight': float(shaping.GetShapingMorphWeight(mid))}
                for mid, item in catalog.items()
                if 'dm_diagnostic_' in mid.lower()]
            if any(abs(x['weight']) > 1e-8 for x in report['diagnostic_morph_weights']):
                raise ValueError('Restored source has an active experimental diagnostic morph')
            report['success'] = True
            phase('independent_source_restored')
            result = {'success': True, 'report_path': report_path,
                      'summary_path': os.path.join(output_dir, 'validation_result.json')}
            api.write_json(result, result['summary_path'])
            return result
        if c.get('operation') == 'native_morph_export':
            phase('native_morph_export_load')
            avatar = load(c['source_project'])
            check('Morph source subdivision zero', avatar.SwitchSubdivMeshLevel(0))
            api.force_avatar_scene_evaluation(avatar)
            report['before_state'] = state(avatar)
            report['before_obj'] = mesh_capture(avatar, 'before_morph_export')
            path = os.path.join(output_dir, 'morph_source.obj')
            flags = (R.EExport3DFileOption_FullBodyPart |
                     R.EExport3DFileOption_ResetToBindPose |
                     R.EExport3DFileOption_GenerateDrmProtectedFile |
                     R.EExport3DFileOption_GenerateMeshGroupIni)
            phase('native_morph_export_obj')
            check('Export native morph source with original OBJ key',
                  R.RFileIO.ExportObjFile(avatar, path, flags))
            report['export_flags'] = int(flags)
            report['source_obj'] = api.bodyfit_freeze_file_record(path)
            report['export_files'] = [api.bodyfit_freeze_file_record(os.path.join(output_dir, name))
                                      for name in os.listdir(output_dir)
                                      if name.lower().startswith('morph_source.')]
            report['after_state'] = state(avatar)
            report['after_obj'] = mesh_capture(avatar, 'after_morph_export')
            report['prepared_project'] = save(avatar, 'morph_source_subd0')
            report['success'] = True
            phase('native_morph_source_collected')
            result = {'success': True, 'report_path': report_path,
                      'summary_path': os.path.join(output_dir, 'validation_result.json')}
            api.write_json(result, result['summary_path'])
            return result
        if c.get('operation') in ('native_morph_probe', 'native_morph_apply_existing'):
            phase('native_morph_load')
            inputs = {}
            for key in ('target_obj', 'target_obj_key'):
                record = c[key]
                path = os.path.realpath(record['path'])
                if os.path.commonpath([ROOT, path]) != ROOT:
                    raise ValueError('Native morph inputs must be independent experiment files')
                if api.sha256_file(path) != record['sha256']:
                    raise ValueError('Native morph input SHA mismatch: ' + key)
                inputs[key] = path
            source_path = os.path.realpath(c['source_project']['path'])
            if os.path.commonpath([ROOT, source_path]) != ROOT:
                raise ValueError('Native morph mutation requires an independent project')
            avatar = load(c['source_project'])
            check('Native morph working subdivision zero', avatar.SwitchSubdivMeshLevel(0))
            report['before_state'] = state(avatar)
            report['before_obj'] = mesh_capture(avatar, 'before_morph')
            shaping = avatar.GetAvatarShapingComponent()
            before_ids = set(api.morph_catalog(avatar)[1])
            morph_name = 'DM_Diagnostic_' + c['case_id']
            morph_path = os.path.join(output_dir, 'diagnostic_body_correction.ccCustomMorph')
            if os.path.exists(morph_path):
                raise ValueError('Refusing to overwrite diagnostic morph')
            category = c.get('morph_category', 'Body')
            if category not in ('Body', 'Head'):
                raise ValueError('Diagnostic morph category must be Body or Head')
            adjust_bones = bool(c.get('adjust_bones', False))
            report['settings'] = {'name': morph_name, 'source': 'Current',
                                  'category': category, 'axis': 'ZUp',
                                  'adjust_bones': adjust_bones, 'auto_apply': True,
                                  'output': morph_path}
            if c.get('operation') == 'native_morph_apply_existing':
                existing = c['existing_morph']
                if api.sha256_file(existing['file']['path']) != existing['file']['sha256']:
                    raise ValueError('Existing diagnostic slider SHA mismatch')
                morph_id = existing['id']
                if morph_id not in before_ids:
                    raise ValueError('Existing diagnostic slider is not registered; no implicit recreation')
                new_ids = [morph_id]
                morph_path = existing['file']['path']
                report['settings']['reuse_existing'] = True
                report['settings']['output'] = morph_path
                report['settings']['explicit_weight'] = 1.0
                phase('native_morph_apply_existing')
                check('Apply registered diagnostic morph at full weight',
                      shaping.SetShapingMorphWeight(morph_id, 1.0))
            else:
                setting = R.RMorphSliderSetting()
                setting.SetMorphName(morph_name)
                setting.SetCategory(getattr(R, 'ESetCategory_' + category))
                setting.SetSliderPath('DataMakeExperiments/HeadshotRoute')
                setting.SetMorphValueRange(0.0, 100.0)
                setting.SetSourceBaseType(R.EChooseBase_Current)
                setting.SetTargetFilePath(inputs['target_obj'])
                setting.SetTargetMorphChecksumFilePath(inputs['target_obj_key'])
                setting.SetAxisSettingForObj(R.EAxisSetting_ZUp)
                setting.SetAdjustBonesToFitMorph(adjust_bones)
                setting.SetAutoApplyToCurrentCharacter(True)
                phase('native_morph_create_slider')
                raw_result = shaping.CreateSlider(setting, morph_path)
                report['create_slider_return'] = str(raw_result)
                if not isinstance(raw_result, (list, tuple)) or len(raw_result) != 2:
                    raise ValueError('Unexpected native CreateSlider return contract')
                check('Create independent native morph slider', raw_result[0])
                after_ids = set(api.morph_catalog(avatar)[1])
                new_ids = sorted(after_ids - before_ids)
                if len(new_ids) == 1:
                    registered = os.path.realpath(str(raw_result[1]))
                    registration_root = r'D:\CharacterCreator_sucai\Reallusion Custom\Actor\Avatar Control'
                    if os.path.commonpath([registration_root, registered]) != registration_root:
                        raise ValueError('Unexpected diagnostic slider registration directory')
                    if not os.path.isfile(registered):
                        raise ValueError('Created slider registration file not found')
                    report['registered_morph_file'] = api.bodyfit_freeze_file_record(registered)
                    morph_path = os.path.join(output_dir, 'diagnostic_morph.ccCustomSlider')
                    if os.path.exists(morph_path):
                        raise ValueError('Refusing to overwrite diagnostic slider evidence')
                    shutil.copyfile(registered, morph_path)
                    report['settings']['explicit_weight'] = 1.0
                    check('Explicitly apply newly registered diagnostic morph',
                          shaping.SetShapingMorphWeight(new_ids[0], 1.0))
            api.force_avatar_scene_evaluation(avatar)
            report['new_morphs'] = [{'id': x, 'weight': shaping.GetShapingMorphWeight(x)}
                                    for x in new_ids]
            if len(new_ids) != 1:
                raise ValueError('Expected one newly registered diagnostic slider')
            report['morph_file'] = api.bodyfit_freeze_file_record(morph_path)
            report['after_morph_state'] = state(avatar)
            report['after_morph_obj'] = mesh_capture(avatar, 'after_morph')
            project0 = save(avatar, 'morph_applied_subd0')
            report['subd0_project'] = project0
            avatar = load(project0)
            report['reloaded_obj'] = mesh_capture(avatar, 'morph_reloaded')
            report['subdivision_sequence'] = []
            for level, label in ((1, 'first_1'), (0, 'return_0'), (1, 'second_1'), (0, 'second_return_0')):
                phase('native_morph_subdivision_' + label)
                check('Native morph subdivision roundtrip', avatar.SwitchSubdivMeshLevel(level))
                api.force_avatar_scene_evaluation(avatar)
                report['subdivision_sequence'].append({'level': level, 'actual': int(avatar.GetSubdivMeshLevel())})
                if level == 0:
                    report[label + '_obj'] = mesh_capture(avatar, label)
            check('Restore native morph target subdivision', avatar.SwitchSubdivMeshLevel(1))
            report['subd1_project'] = save(avatar, 'morph_applied_subd1')
            avatar = load(report['subd1_project'])
            report['final_state'] = state(avatar)
            report['success'] = True
            phase('native_morph_evidence_collected')
            result = {'success': True, 'report_path': report_path,
                      'summary_path': os.path.join(output_dir, 'validation_result.json')}
            api.write_json(result, result['summary_path'])
            return result
        if c.get('operation') == 'prepare_headshot_skin_source':
            phase('prepare_skin_load_average')
            avatar = load(c['source_project'])
            check('Skin preparation working subdivision', avatar.SwitchSubdivMeshLevel(0))
            api.force_avatar_scene_evaluation(avatar)

            def local_body():
                body = [m for m in avatar.GetMeshes(False) if m.GetName() == 'CC_Base_Body' and m.GetVerticesCount() == 14164]
                if len(body) != 1:
                    raise ValueError('Skin preparation body topology mismatch')
                return [[float(v.x),float(v.y),float(v.z)] for v in body[0].GetVertices(False)]

            before = local_body()
            api.write_json({'vertices':before},os.path.join(output_dir,'before_skin_body_local.json'))
            report['before_state'] = state(avatar)
            if c.get('skin_texture_assets'):
                records = c['skin_texture_assets']
                expected = {(m, ch) for m in ('Std_Skin_Head', 'Std_Skin_Body', 'Std_Skin_Arm', 'Std_Skin_Leg') for ch in ('Diffuse', 'Bump')}
                if len(records) != 8 or {(x['material'], x['channel']) for x in records} != expected:
                    raise ValueError('Texture-only preparation requires exactly eight locked skin textures')
                component = avatar.GetMaterialComponent()
                report['skin_application'] = {'mode': 'texture_channels_only', 'records': []}
                phase('prepare_skin_apply_locked_texture_channels')
                for item in records:
                    p = os.path.realpath(item['path'])
                    if os.path.commonpath([ROOT, p]) != ROOT or api.sha256_file(p) != item['sha256']:
                        raise ValueError('Prepared skin texture path/hash mismatch')
                    load_channel = item.get('load_channel', item['channel'])
                    if load_channel not in (('Diffuse',) if item['channel'] == 'Diffuse' else ('Bump', 'Normal')):
                        raise ValueError('Invalid skin texture load channel')
                    status = check('Load skin texture only', component.LoadImageToTexture(
                        'CC_Base_Body', item['material'], getattr(R, 'EMaterialTextureChannel_' + load_channel), p))
                    report['skin_application']['records'].append({'source': item, 'load_channel': load_channel, 'status': status})
            else:
                skin = c['skin_asset']
                if api.sha256_file(skin['path']) != skin['sha256'] or not skin['path'].lower().endswith('.ccskin'):
                    raise ValueError('Skin preparation asset mismatch')
                phase('prepare_skin_apply_official_preset')
                status,dialogs = api.load_file_with_known_cc_dialogs(skin['path'],'Load official skin into Average copy',allow_skin_material=True)
                report['skin_application']={'mode': 'official_ccskin', 'source':skin,'status':status,'dialogs':dialogs}
            api.force_avatar_scene_evaluation(avatar)
            after = local_body()
            api.write_json({'vertices':after},os.path.join(output_dir,'after_skin_body_local.json'))
            error=max(math.sqrt(sum((a-b)**2 for a,b in zip(x,y))) for x,y in zip(before,after))*10
            report['skin_body_max_delta_mm']=error
            if error > 0.002:
                raise ValueError('Skin-only preparation unexpectedly changed the body')
            report['skin_images']=[]
            component=avatar.GetMaterialComponent()
            for name in ('Std_Skin_Head','Std_Skin_Body','Std_Skin_Arm','Std_Skin_Leg'):
                for channel in ('Diffuse','Bump'):
                    im=component.GetImage('CC_Base_Body',name,getattr(R,'EMaterialTextureChannel_'+channel))
                    p=os.path.join(output_dir,name+'_'+channel+'.png')
                    check('Save prepared skin evidence',im.SaveFile(p))
                    row={'material':name,'channel':channel,'width':im.GetWidth(),'height':im.GetHeight(),'file':api.bodyfit_freeze_file_record(p)}
                    report['skin_images'].append(row)
                    if min(row['width'],row['height'])<1024:
                        raise ValueError('Prepared skin has missing or low-resolution texture')
            report['prepared_project']=save(avatar,'prepared_average_skin_subd0')
            avatar=load(report['prepared_project'])
            report['reloaded_state']=state(avatar)
            report['prepared_body_obj']=mesh_capture(avatar,'prepared_skin')
            report['success']=True
            phase('prepared_skin_source_complete')
            result={'success':True,'report_path':report_path,'summary_path':os.path.join(output_dir,'validation_result.json')}
            api.write_json(result,result['summary_path'])
            return result
        if c.get('operation') in ('skin_shader_calibration_probe', 'skin_normal_channel_probe', 'skin_preserve_head_material_probe'):
            # Isolate scalar shading settings; do not replace photo textures,
            # procedural skin state, or geometry. Render level stays unverified.
            reference = c['shader_reference_report']
            normal_mode = c['operation'] == 'skin_normal_channel_probe'
            preserve_head_mode = c['operation'] == 'skin_preserve_head_material_probe'
            if preserve_head_mode:
                skin = c['skin_asset']
                if not skin['path'].lower().endswith('.ccskin') or api.sha256_file(skin['path']) != skin['sha256']:
                    raise ValueError('Preserve-head skin source mismatch')
            for record in (reference, c['source_project']):
                p = os.path.realpath(record['path'])
                if os.path.commonpath([ROOT, p]) != ROOT or api.sha256_file(p) != record['sha256']:
                    raise ValueError('Skin calibration experiment input mismatch')
            with open(reference['path'], encoding='utf-8') as stream:
                reference_data = json.load(stream)
            materials = ('Std_Skin_Head', 'Std_Skin_Body', 'Std_Skin_Arm', 'Std_Skin_Leg')
            parameters = ('MicroNormal Strength', 'Cavity Strength', '_Specular')
            targets = {}
            for name in materials:
                matches = [x for x in reference_data['material_records']
                           if x['mesh'] == 'CC_Base_Body' and x['material'] == name]
                if not matches:
                    raise ValueError('Missing reference skin material: ' + name)
                selected = {p: matches[0]['parameters'][p] for p in parameters}
                if any({p: x['parameters'][p] for p in parameters} != selected for x in matches):
                    raise ValueError('Ambiguous reference skin parameters')
                if any(len(v) != 1 or not math.isfinite(v[0]) for v in selected.values()):
                    raise ValueError('Expected finite scalar shader settings')
                targets[name] = selected
            phase('skin_calibration_load_copy')
            report['pre_probe_current_copy'] = save(None, 'pre_probe_current_unverified')
            avatar = load(c['source_project'])
            check('Skin calibration working level', avatar.SwitchSubdivMeshLevel(0))
            component = avatar.GetMaterialComponent()
            report['render_subdivision_verified'] = False
            report['shader_reference_report'] = reference

            def capture_skin(label):
                api.force_avatar_scene_evaluation(avatar)
                meshes = [m for m in avatar.GetMeshes(False)
                          if m.GetName() == 'CC_Base_Body' and m.GetVerticesCount() == 14164]
                if len(meshes) != 1:
                    raise ValueError('Skin calibration body topology mismatch')
                vertices = [[float(v.x), float(v.y), float(v.z)] for v in meshes[0].GetVertices(False)]
                rows = []
                for name in materials:
                    row = {'material': name, 'parameters': {}, 'textures': {}}
                    for parameter in parameters:
                        row['parameters'][parameter] = api.material_value(component.GetShaderParameter('CC_Base_Body', name, parameter))
                    for channel in ('Diffuse', 'Bump'):
                        p = os.path.join(output_dir, label + '_' + name + '_' + channel + '.png')
                        check('Preserve calibration texture', component.GetImage('CC_Base_Body', name, getattr(R, 'EMaterialTextureChannel_' + channel)).SaveFile(p))
                        row['textures'][channel] = api.bodyfit_freeze_file_record(p)
                    rows.append(row)
                api.write_json({'vertices': vertices}, os.path.join(output_dir, label + '_body_local.json'))
                return vertices, rows

            before, report['before_skin'] = capture_skin('before')
            camera(avatar)
            api.set_avatar_position(avatar, -50.0, 8.0, 12.0)
            report['images'] = []
            variants = ('original_channel', 'normal_channel') if normal_mode else ('original_scalars', 'calibrated_scalars')
            if preserve_head_mode:
                variants = ('before_official_skin', 'preserve_head_skin')
            for variant in variants:
                if variant == variants[1]:
                    if preserve_head_mode:
                        status, dialogs = api.load_file_with_known_cc_dialogs(
                            skin['path'], 'Apply body skin while retaining generated head textures',
                            require_skin_material=True, preserve_head_textures=True)
                        report['skin_application'] = {'source': skin, 'status': status, 'dialogs': dialogs}
                        component = avatar.GetMaterialComponent()
                    elif normal_mode:
                        for row in report['before_skin']:
                            check('Reload same image through Normal enum', component.LoadImageToTexture(
                                'CC_Base_Body', row['material'], R.EMaterialTextureChannel_Normal,
                                row['textures']['Bump']['path']))
                    else:
                        for name, values in targets.items():
                            for parameter, value in values.items():
                                check('Apply bounded skin scalar', component.SetShaderParameter('CC_Base_Body', name, parameter, tuple(value)))
                for view, yaw in [('front', 90.0), ('quarter', 45.0), ('side', 0.0)]:
                    phase(variant + '_' + view)
                    api.set_avatar_yaw(avatar, yaw)
                    api.force_avatar_scene_evaluation(avatar)
                    p = os.path.join(output_dir, variant + '_' + view + '.png')
                    api.render_preview(p)
                    report['images'].append(api.bodyfit_freeze_file_record(p))
            api.set_avatar_yaw(avatar, 90.0)
            after, report['after_skin'] = capture_skin('after')
            error = max(math.sqrt(sum((a-b)**2 for a,b in zip(x,y))) for x,y in zip(before, after)) * 10
            report['body_local_max_delta_mm'] = error
            if error > 0.002:
                raise ValueError('Skin scalar adjustment changed body geometry')
            report['candidate_project'] = save(avatar, 'calibrated_skin_subd0')
            avatar = load(report['candidate_project'])
            component = avatar.GetMaterialComponent()
            _, report['reloaded_skin'] = capture_skin('reloaded')
            for stage in ('after_skin', 'reloaded_skin'):
                for original, row in zip(report['before_skin'], report[stage]):
                    expected_parameters = original['parameters'] if normal_mode else targets[row['material']]
                    if not preserve_head_mode and row['parameters'] != expected_parameters:
                        raise ValueError('Skin scalar readback mismatch: ' + stage)
                    for channel in ('Diffuse', 'Bump'):
                        if preserve_head_mode and row['material'] != 'Std_Skin_Head':
                            continue
                        if original['textures'][channel]['sha256'] != row['textures'][channel]['sha256']:
                            raise ValueError('Skin calibration changed texture: ' + stage)
            phase('skin_material_reloaded_front')
            p = os.path.join(output_dir, 'reloaded_front.png')
            api.render_preview(p)
            report['images'].append(api.bodyfit_freeze_file_record(p))
            report['success'] = True
            report['acceptance'] = 'Isolated skin material evidence; no render-level or skin visual acceptance'
            phase('skin_preserve_head_collected' if preserve_head_mode else
                  ('skin_normal_channel_collected' if normal_mode else 'skin_scalar_calibration_collected'))
            result = {'success': True, 'report_path': report_path,
                      'summary_path': os.path.join(output_dir, 'validation_result.json')}
            api.write_json(result, result['summary_path'])
            return result
        if c.get('operation') == 'current_verified_neck_capture':
            level = c.get('observed_render_level')
            if level not in (0, 1) or c.get('observed_viewport_level') != level or not c.get('ui_observation'):
                raise ValueError('Neck capture requires observed matching Viewport/Render levels')
            expected = os.path.realpath(c['source_project']['path'])
            if os.path.commonpath([ROOT, expected]) != ROOT or api.sha256_file(expected) != c['source_project']['sha256']:
                raise ValueError('Current neck capture source lineage mismatch')
            avatars = list(R.RScene.GetAvatars() or [])
            if len(avatars) != 1 or int(avatars[0].GetSubdivMeshLevel()) != level:
                raise ValueError('Current experimental avatar level does not match observation')
            avatar = avatars[0]
            phase('save_observed_neck_capture_copy')
            baseline = save(avatar, 'observed_subd{}'.format(level))
            report['observed_project'] = baseline
            report['render_subdivision_evidence'] = c['ui_observation']
            report['observed_render_level'] = level
            report['observed_viewport_level'] = level
            camera(avatar)
            api.set_avatar_position(avatar, -50.0, 8.0, 12.0)
            report['images'] = []
            for view, yaw in [('front', 90.0), ('quarter', 45.0), ('side', 0.0)]:
                phase('verified_neck_' + view)
                api.set_avatar_yaw(avatar, yaw)
                api.force_avatar_scene_evaluation(avatar)
                p = os.path.join(output_dir, 'render{}_{}.png'.format(level, view))
                api.render_preview(p)
                report['images'].append(api.bodyfit_freeze_file_record(p))
            avatar = load(baseline)
            report['success'] = True
            report['acceptance'] = 'Verified render-level full-neck evidence; visual acceptance remains separate'
            phase('verified_neck_evidence_collected')
            result = {'success': True, 'report_path': report_path,
                      'summary_path': os.path.join(output_dir, 'validation_result.json')}
            api.write_json(result, result['summary_path'])
            return result
        if c.get('operation') == 'current_neck_material_contrast':
            # Only entered immediately after an observed UI render-level change
            # on this experiment's saved hair candidate; no canonical input save.
            if c.get('observed_viewport_level') != 0 or c.get('observed_render_level') != 0:
                raise ValueError('Current neck contrast requires observed Viewport0/Render0')
            expected = os.path.realpath(c['source_project']['path'])
            if os.path.commonpath([ROOT, expected]) != ROOT or api.sha256_file(expected) != c['source_project']['sha256']:
                raise ValueError('Current scene lineage input mismatch')
            avatars = list(R.RScene.GetAvatars() or [])
            if len(avatars) != 1 or int(avatars[0].GetSubdivMeshLevel()) != 0:
                raise ValueError('Expected one current SubD0 experimental avatar')
            avatar = avatars[0]
            baseline = save(avatar, 'ui_render0_baseline')
            report['render0_baseline_project'] = baseline
            report['render_subdivision_evidence'] = c['ui_observation']
            camera(avatar)
            api.set_avatar_position(avatar,-50.0,8.0,12.0)
            component = avatar.GetMaterialComponent()
            report['original_bump_images'] = []
            for name in ('Std_Skin_Head','Std_Skin_Body'):
                p = os.path.join(output_dir,name+'_original_bump.png')
                check('Preserve original neck Bump',component.GetImage('CC_Base_Body',name,R.EMaterialTextureChannel_Bump).SaveFile(p))
                report['original_bump_images'].append(api.bodyfit_freeze_file_record(p))
            replacement = c['flat_normal']
            if os.path.commonpath([ROOT,os.path.realpath(replacement['path'])]) != ROOT or api.sha256_file(replacement['path']) != replacement['sha256']:
                raise ValueError('Flat normal diagnostic source mismatch')
            report['before_obj'] = mesh_capture(avatar,'before_flat_bump')
            report['images'] = []
            for variant in ('original_bump','flat_bump'):
                if variant == 'flat_bump':
                    for name in ('Std_Skin_Head','Std_Skin_Body'):
                        check('Apply diagnostic flat Bump',component.LoadImageToTexture('CC_Base_Body',name,R.EMaterialTextureChannel_Bump,replacement['path']))
                    api.force_avatar_scene_evaluation(avatar)
                for view,yaw in [('front',90.0),('quarter',45.0),('side',0.0)]:
                    phase('render0_' + variant + '_' + view)
                    api.set_avatar_yaw(avatar,yaw)
                    api.force_avatar_scene_evaluation(avatar)
                    p=os.path.join(output_dir,variant+'_'+view+'.png')
                    api.render_preview(p)
                    report['images'].append(api.bodyfit_freeze_file_record(p))
            api.set_avatar_yaw(avatar,90.0)
            api.force_avatar_scene_evaluation(avatar)
            report['after_obj'] = mesh_capture(avatar,'after_flat_bump')
            avatar = load(baseline)
            report['success'] = True
            report['acceptance'] = 'Diagnostic material isolation only; original Render0 baseline restored, not a final skin repair'
            phase('render0_material_contrast_collected')
            result={'success':True,'report_path':report_path,'summary_path':os.path.join(output_dir,'validation_result.json')}
            api.write_json(result,result['summary_path'])
            return result
        if c.get('operation') == 'fixed_scalp_hair_visual_probe':
            if library.get('preview_capture_mode') != 'render_image_native_aspect':
                raise ValueError('Hair visual probe requires native-aspect captures')
            if library.get('eye_snapshot_mode') != 'transforms_only':
                raise ValueError('Hair visual probe requires transforms_only eye snapshots')

            def evidence(record):
                path = os.path.realpath(record['path'])
                if os.path.commonpath([ROOT, path]) != ROOT or api.sha256_file(path) != record['sha256']:
                    raise ValueError('Hair evidence path/hash mismatch')
                with open(path, encoding='utf-8') as stream:
                    return json.load(stream)

            reference = evidence(c['hair_reference_meshes'])
            reference_body = evidence(c['reference_body_world'])
            phase('fixed_hair_load_fixed_B_copy')
            avatar = load(c['source_project'])
            if int(avatar.GetSubdivMeshLevel()) != 0:
                raise ValueError('Fixed B copy must be saved at working SubD 0')
            if avatar.GetHairs():
                raise ValueError('Expected hair-free fixed B copy')
            body = [m for m in avatar.GetMeshes(False) if m.GetName() == 'CC_Base_Body' and m.GetVerticesCount() == 14164][0]
            before_body = [[float(v.x), float(v.y), float(v.z)] for v in body.GetVertices(False)]
            api.write_json({'vertices': before_body}, os.path.join(output_dir, 'before_body_local.json'))
            reference_transform = reference_body['avatar_transform']
            target_transform = api._transform_data(avatar.WorldTransform())
            report['reference_transform'] = reference_transform
            report['target_transform'] = target_transform
            # Reject rotation/scale differences; the bounded experiment only
            # transfers the same hair using an actor-root translation offset.
            for key in ('rotation', 's'):
                if reference_transform[key] != target_transform[key]:
                    raise ValueError('Hair transfer rotation/scale differs')
            shift = [target_transform['translation'][k]-reference_transform['translation'][k] for k in ('x','y','z')]
            asset = c['hair_asset']
            if api.sha256_file(asset['path']) != asset['sha256']:
                raise ValueError('Representative hair source SHA mismatch')
            check('Load representative hair materials and rig', R.RFileIO.LoadFile(asset['path']))
            api.force_avatar_scene_evaluation(avatar)
            meshes = {m.GetName(): m for h in avatar.GetHairs() or [] for m in h.GetMeshes(False) or []}
            if len(meshes) != len(reference) or set(meshes) != {x['mesh'] for x in reference}:
                raise ValueError('Representative hair mesh set changed')
            transfer = c.get('transfer_hair_geometry', True)
            report['hair_geometry_policy'] = ('replace_with_exact_A_target' if transfer else 'CC_autofit_measured_against_A_not_fixed_geometry_render')
            obj_templates = {}
            if transfer:
                template = os.path.join(output_dir, 'avatar_with_hair_native.obj')
                # The live CC5 API rejects ExportObjFile(RIHair). Export the
                # owning avatar and preserve its exact group/UV layout instead.
                option = R.EExport3DFileOption_AllClothes | R.EExport3DFileOption_FullBodyPart
                check('Export avatar hair OBJ layout', R.RFileIO.ExportObjFile(avatar, template, option))
                report['native_hair_template'] = api.bodyfit_freeze_file_record(template)
            for hair_index, hair in enumerate((avatar.GetHairs() or []) if transfer else []):
                with open(template, encoding='utf-8-sig') as stream:
                    lines = stream.readlines()
                group, groups = '', {}
                for line in lines:
                    parts = line.split()
                    if parts and parts[0] in ('g','o'):
                        group = ' '.join(parts[1:])
                    elif parts and parts[0] == 'f':
                        groups.setdefault(group,set()).update(int(t.split('/')[0])-1 for t in parts[1:])
                for mesh in hair.GetMeshes(False) or []:
                    ids = sorted(groups.get(mesh.GetName(),[]))
                    if len(ids) != mesh.GetVerticesCount() or ids != list(range(ids[0],ids[0]+len(ids))):
                        raise ValueError('Native hair OBJ group does not match API vertex layout: ' + mesh.GetName())
                    obj_templates[mesh.GetName()] = (lines, ids[0], ids[-1])
            report['hair_transfer'] = []
            for index, row in enumerate(reference):
                mesh = meshes[row['mesh']]
                faces = [list(mesh.GetFace(i)) for i in range(mesh.GetFacesCount())]
                if mesh.GetVerticesCount() != len(row['vertices']) or faces != row['faces']:
                    raise ValueError('Representative hair topology changed')
                target = [[v[k]+shift[k] for k in range(3)] for v in row['vertices']]
                if not transfer:
                    actual = [[float(v.x),float(v.y),float(v.z)] for v in mesh.GetVertices(True)]
                    error = max(math.sqrt(sum((a-b)**2 for a,b in zip(x,y))) for x,y in zip(actual,target))*10
                    report['hair_transfer'].append({'mesh':row['mesh'], 'autofit_vs_A_max_mm':error,'replacement_performed':False})
                    continue
                requested = [v[:] for v in target]
                errors = []
                for attempt in range(3):
                    phase('fixed_hair_mesh_{}_attempt_{}'.format(index, attempt))
                    obj = os.path.join(output_dir, 'hair_{}_attempt_{}.obj'.format(index, attempt))
                    lines, start, end = obj_templates[mesh.GetName()]
                    vertex_index = 0
                    with open(obj, 'w', encoding='utf-8') as stream:
                        for line in lines:
                            if line.startswith('v '):
                                if start <= vertex_index <= end:
                                    line = 'v {:.12f} {:.12f} {:.12f}\n'.format(*requested[vertex_index-start])
                                vertex_index += 1
                            stream.write(line)
                    check('Apply A-fitted hair geometry to fixed B', mesh.ReplaceMesh(obj, R.EReplaceMeshOption_ZUp, False))
                    api.force_avatar_scene_evaluation(avatar)
                    actual = [[float(v.x),float(v.y),float(v.z)] for v in mesh.GetVertices(True)]
                    error = max(math.sqrt(sum((a-b)**2 for a,b in zip(x,y))) for x,y in zip(actual,target))*10
                    errors.append(error)
                    if error < 0.02:
                        break
                    requested = [[r[k]+t[k]-a[k] for k in range(3)] for r,t,a in zip(requested,target,actual)]
                report['hair_transfer'].append({'mesh':row['mesh'], 'residual_mm':errors})
                if errors[-1] >= 0.02:
                    raise ValueError('Hair transfer did not converge to requested A geometry')
            project = save(avatar, 'fixed_B_with_A_hair_subd0')
            avatar = load(project)
            body = [m for m in avatar.GetMeshes(False) if m.GetName() == 'CC_Base_Body' and m.GetVerticesCount() == 14164][0]
            api.write_json({'vertices': [[float(v.x),float(v.y),float(v.z)] for v in body.GetVertices(False)]}, os.path.join(output_dir, 'after_body_local.json'))
            captured = []
            for hair in avatar.GetHairs() or []:
                for mesh in hair.GetMeshes(False) or []:
                    captured.append({'mesh':mesh.GetName(), 'vertices':[[float(v.x),float(v.y),float(v.z)] for v in mesh.GetVertices(True)]})
            api.write_json(captured, os.path.join(output_dir, 'reloaded_hair_world.json'))
            report['assembled_project'] = project
            report['source_state'] = state(avatar)
            if c.get('capture_visuals', True) is False:
                report['success'] = True
                report['render_subdivision_verified'] = False
                report['acceptance'] = 'Geometry-only assembly and reload; appearance and subdivision hair stability remain pending'
                phase('fixed_hair_geometry_evidence_collected')
                result = {'success':True,'report_path':report_path,
                          'summary_path':os.path.join(output_dir,'validation_result.json')}
                api.write_json(result,result['summary_path'])
                return result
            camera(avatar)
            position = [-50.0, 8.0, 12.0]
            api.set_avatar_position(avatar, *position)
            check('Representative visual working level 1', avatar.SwitchSubdivMeshLevel(1))
            api.force_avatar_scene_evaluation(avatar)
            report['images'] = []
            for view,yaw in [('front',90.0),('quarter',45.0),('side',0.0),('back',-90.0)]:
                phase('fixed_hair_visual_' + view)
                api.set_avatar_yaw(avatar,yaw)
                api.force_avatar_scene_evaluation(avatar)
                path = os.path.join(output_dir, view + '.png')
                api.render_preview(path)
                report['images'].append(api.bodyfit_freeze_file_record(path))
            pose_dir = os.path.join(output_dir,'poses')
            os.makedirs(pose_dir)
            # Rendering evaluates the skeleton after the previous back view;
            # otherwise the first world-space eye snapshot can retain its yaw.
            api.set_avatar_yaw(avatar,90.0)
            api.force_avatar_scene_evaluation(avatar)
            api.render_preview(os.path.join(output_dir,'pre_pose_neutral_front.png'))
            report['poses'] = api.render_profile_upgrade_pose_matrix(avatar, pose_dir, phase, R.RGlobal.GetStartTime(), position)
            report['render_subdivision_verified'] = False
            avatar = load(project)
            report['success'] = True
            phase('fixed_hair_visual_evidence_collected')
            result = {'success':True,'report_path':report_path,'summary_path':os.path.join(output_dir,'validation_result.json')}
            api.write_json(result,result['summary_path'])
            return result
        if c.get('operation') == 'neck_subdivision_probe':
            if library.get('eye_snapshot_mode') != 'transforms_only':
                raise ValueError('Neck probe requires transforms_only eye snapshots')
            phase('neck_probe_load_copy')
            avatar = load(c['source_project'])
            camera(avatar)
            if c.get('diagnostic_normal_override'):
                replacement = c['diagnostic_normal_override']
                replacement_path = os.path.realpath(replacement['path'])
                if os.path.commonpath([ROOT, replacement_path]) != ROOT or api.sha256_file(replacement_path) != replacement['sha256']:
                    raise ValueError('Diagnostic normal map path/hash mismatch')
                component = avatar.GetMaterialComponent()
                report['material_normal_override'] = []
                for material in ('Std_Skin_Head', 'Std_Skin_Body'):
                    row = {'material': material, 'channels': {}}
                    for channel_name in ('Diffuse', 'Normal', 'Bump'):
                        channel = getattr(R, 'EMaterialTextureChannel_' + channel_name)
                        original = os.path.join(output_dir, material + '_' + channel_name + '_original.png')
                        try:
                            check('Preserve original diagnostic texture', component.GetImage('CC_Base_Body', material, channel).SaveFile(original))
                            row['channels'][channel_name] = api.bodyfit_freeze_file_record(original)
                        except Exception as exc:
                            row['channels'][channel_name] = {'error': str(exc)}
                    override_channel = c.get('diagnostic_normal_channel', 'Normal')
                    if override_channel not in ('Normal', 'Bump'):
                        raise ValueError('Unsupported diagnostic normal channel')
                    check('Diagnostic flat normal only', component.LoadImageToTexture('CC_Base_Body', material, getattr(R, 'EMaterialTextureChannel_' + override_channel), replacement_path))
                    row['overridden_channel'] = override_channel
                    report['material_normal_override'].append(row)
            if c.get('full_neck_views'):
                cam = R.RScene.GetCurrentCamera()
                t = R.RGlobal.GetStartTime()
                report['original_camera'] = api.camera_state(cam)
                # CC's Preview Camera rejects focal-length keys. Move only the
                # experiment avatar farther from the fixed reference camera.
                api.set_avatar_position(avatar, -70.0, 8.0, 15.0)
                report['neck_framing_avatar_position_cm'] = [-70.0, 8.0, 15.0]
                report['neck_camera'] = api.camera_state(cam)
            report['captures'] = []
            levels = c.get('neck_probe_levels', [0, 1, 0])
            if not isinstance(levels, list) or not levels or len(levels) > 3 or any(x not in (0, 1) for x in levels):
                raise ValueError('Neck probe accepts at most three level 0/1 observations')
            for step, level in enumerate(levels):
                label = 'step{}_working_level{}'.format(step, level)
                if int(avatar.GetSubdivMeshLevel()) != level:
                    check('Neck probe subdivision', avatar.SwitchSubdivMeshLevel(level))
                api.force_avatar_scene_evaluation(avatar)
                phase('neck_probe_' + label)
                images = []
                views = [('front', 90.0), ('quarter', 45.0), ('side', 0.0)] if c.get('full_neck_views') else [('front', 90.0)]
                if c.get('diagnostic_normal_override'):
                    views = [('front', 90.0)]
                for view, yaw in views:
                    api.set_avatar_yaw(avatar, yaw)
                    image_path = os.path.join(output_dir, label + '_' + view + '.png')
                    api.render_preview(image_path)
                    images.append(api.bodyfit_freeze_file_record(image_path))
                api.set_avatar_yaw(avatar, 90.0)
                api.force_avatar_scene_evaluation(avatar)
                obj_path = os.path.join(output_dir, label + '.obj')
                check('Neck probe OBJ', R.RFileIO.ExportObjFile(avatar, obj_path, R.EExport3DFileOption_BodyPart))
                report['captures'].append({'label': label, 'subdivision': int(avatar.GetSubdivMeshLevel()),
                                           'images': images,
                                           'render_subdivision_verified': False,
                                           'obj': api.bodyfit_freeze_file_record(obj_path),
                                           'materials': api.avatar_material_fingerprint(avatar)})
            if not c.get('leave_preview_open'):
                avatar = load(c['source_project'])
            report['success'] = True
            phase('neck_probe_complete')
            result = {'success': True, 'report_path': report_path,
                      'summary_path': os.path.join(output_dir, 'validation_result.json')}
            api.write_json(result, result['summary_path'])
            return result
        if c.get('operation') == 'representative_expression_motion_export':
            for record in (c['source_project'], c['restore_project']):
                source = os.path.realpath(record['path'])
                if os.path.commonpath([ROOT, source]) != ROOT or api.sha256_file(source) != record['sha256']:
                    raise ValueError('Expression export requires locked independent source and restore copies')
            case_id = c['case_id']
            if not case_id or not all(x.isalnum() or x == '_' for x in case_id):
                raise ValueError('Unsafe expression export identifier')
            export_root = os.path.join(r'D:\UE\exports\character_creator\headshot_routes_20261002_v1', case_id)
            if os.path.exists(export_root):
                raise ValueError('Refusing to overwrite expression export')
            os.makedirs(export_root)
            report['source_project'] = c['source_project']
            report['restore_project'] = c['restore_project']
            try:
                phase('expression_motion_load')
                avatar = load(c['source_project'])
                if c.get('motion_seed'):
                    seed = c['motion_seed']
                    if api.sha256_file(seed['path']) != seed['sha256']:
                        raise ValueError('Motion seed SHA mismatch')
                    report['motion_seed'] = seed
                    report['current_pose_mode_before_seed'] = bool(avatar.GetFaceComponent().IsCurrentPoseMode())
                    check('Load installed facial calibration motion', R.RFileIO.LoadFile(seed['path']))
                    api.QtWidgets.QApplication.processEvents()
                face = avatar.GetFaceComponent()
                skeleton = avatar.GetSkeletonComponent()
                names = list(face.GetExpressionNames('') or [])
                specs, targets = api.profile_upgrade_pose_specs(names)
                report['profile_uid'] = str(face.GetExpressionSetUid())
                report['expression_count'] = len(names)
                report['resolved_targets'] = targets
                report['removed_clip_counts'] = {}
                report['current_pose_mode'] = bool(face.IsCurrentPoseMode())
                if report['current_pose_mode']:
                    phase('expression_motion_mode_rejected')
                    raise ValueError('Current Pose mode is not a verified animation writer; load a locked facial motion seed first')
                for label, component in (('face', face), ('skeleton', skeleton)):
                    report['removed_clip_counts'][label] = 0
                    if c.get('preserve_profile_clip'):
                        continue
                    report['removed_clip_counts'][label] = int(component.GetClipCount())
                    for i in range(int(component.GetClipCount()) - 1, -1, -1):
                        check('Clear independent animation clip', component.DeleteClip(component.GetClip(i)))
                fps = R.RGlobal.GetFps()
                frame_time = lambda frame: R.IndexedFrameTime(frame, fps)
                check('Expression timeline start', R.RGlobal.SetStartTime(frame_time(0)))
                check('Expression timeline end', R.RGlobal.SetEndTime(frame_time(180)))
                if c.get('preserve_profile_clip'):
                    clip = face.GetClipByTime(frame_time(0))
                    if clip is None or not clip.IsValid():
                        raise ValueError('No existing facial profile clip at start')
                    report['profile_clip_original_length_ticks'] = int(clip.GetLength().ToInt64())
                    if clip.GetLength() < frame_time(180):
                        check('Extend independent profile clip', clip.SetLength(frame_time(180)))
                else:
                    check('Add expression diagnostic clip', face.AddClip(frame_time(0), 'Headshot_Full_Expression_Probe', frame_time(180)))
                timeline = [(0, 'neutral', {}), (30, 'blink', specs['blink_bilateral_front']),
                            (60, 'neutral', {}), (90, 'smile', specs['smile_broad_front']),
                            (120, 'neutral', {}), (150, 'jaw_open', specs['jaw_open_front']), (180, 'neutral', {})]
                report['timeline'] = [{'frame': f, 'pose': p, 'weights': w} for f, p, w in timeline]
                report['duration_ticks'] = int(frame_time(180).ToInt64())
                report['duration_seconds'] = float(R.RTick.ToSecond(frame_time(180).ToInt64()))
                report['key_readback'] = []
                for frame, pose, weights in timeline:
                    check('Begin expression timeline key', face.BeginKeyEditing())
                    try:
                        check('Expression key ' + pose, face.AddExpressionKeys(frame_time(frame), names,
                              [float(weights.get(n, 0.0)) for n in names], frame_time(0)))
                    finally:
                        check('End expression timeline key', face.EndKeyEditing())
                    report['key_readback'].append({'frame': frame, 'weights': dict(zip(names,
                        api.expression_weights_at(face, frame_time(frame), names))),
                        'expressiveness': float(face.GetExpressiveness(frame_time(frame)))})
                report['poses'] = []
                for frame, pose, weights in timeline:
                    check('Evaluate actual expression frame', R.RGlobal.SetTime(frame_time(frame), True))
                    api.settle_cc_ui(0.5)
                    report['poses'].append({'frame': frame, 'pose': pose,
                        'actual_frame': int(fps.GetFrameIndex(R.RGlobal.GetTime())),
                        'readback_weights': dict(zip(names, api.expression_weights_at(face, frame_time(frame), names))),
                        'bones': [{'name': b.GetName(), 'world_transform': api._transform_data(b.WorldTransform())}
                                  for b in skeleton.GetSkinBones()]})
                check('Return timeline to neutral', R.RGlobal.SetTime(frame_time(0), True))
                phase('expression_motion_keys_recorded')
                for row in report['poses']:
                    requested = next(w for f, p, w in timeline if f == row['frame'])
                    errors = {n: abs(row['readback_weights'][n] - w) for n, w in requested.items()
                              if not n.startswith('C_')}
                    if errors and max(errors.values()) > 0.0001:
                        raise ValueError('Expression key readback mismatch at frame ' + str(row['frame']))
                report['animation_project'] = save(avatar, 'expression_timeline')
                setting = R.RExportFbxSetting()
                flags = R.EExportFbxOptions__None | R.EExportFbxOptions_AutoSkinRigidMesh | R.EExportFbxOptions_ExportRootMotion
                flags2 = R.EExportFbxOptions2__None
                option_names = ('UnrealEngine4BoneAxis', 'UnrealPreset', 'UnrealIkBone',
                    'RenameDuplicateBoneName', 'RenameDuplicateMaterialName', 'RenameDuplicateMorphName',
                    'RenameTransparencyWithPostFix', 'RenameBoneRootToGameType', 'RenameBoneToLowerCase',
                    'RenameBoneOnStd', 'RenameMorphInvalidCharacter', 'ResetBoneScale',
                    'ResetSelfillumination', 'ExtraWordForUnityAndUnreal')
                for name in option_names:
                    flags2 |= getattr(R, 'EExportFbxOptions2_' + name)
                for label, status in (
                    ('Motion enabled', setting.EnableExportMotion(True)),
                    ('Motion FPS', setting.SetExportMotionFps(fps)),
                    ('Motion range', setting.SetExportMotionRange(R.RRangePair(0, 180))),
                    ('Primary flags', setting.SetOption(flags)), ('Unreal flags', setting.SetOption2(flags2)),
                    ('JSON sidecar', setting.SetOption3(R.EExportFbxOptions3_ExportJson)),
                    ('Original textures', setting.SetTextureSize(R.EExportTextureSize_Original)),
                    ('Default textures', setting.SetTextureFormat(R.EExportTextureFormat_Default)),
                    ('UE5 bones', setting.SetUnrealBoneStructure(R.EUnrealBoneStructure_UE5_BoneStructure)),
                    ('Original bind', setting.EnableBasicBindPose(False)), ('Base mesh', setting.EnableBakeSubdivision(False))):
                    check(label, status)
                report['export_settings'] = {'motion': True, 'range': [0, 180], 'option': int(flags),
                    'option2': int(flags2), 'option2_names': list(option_names), 'bake_subdivision': False, 'bone_structure': 'UE5'}
                fbx = os.path.join(export_root, 'character.fbx')
                phase('expression_motion_export')
                check('Export full expression animation', R.RFileIO.ExportFbxFile(avatar, fbx, setting))
                if not os.path.isfile(fbx) or not os.path.isfile(os.path.splitext(fbx)[0] + '.json'):
                    raise ValueError('Expression FBX or sidecar missing')
                report['export_files'] = [api.bodyfit_freeze_file_record(os.path.join(base, name))
                    for base, dirs, files in os.walk(export_root) for name in files]
                phase('expression_motion_capture')
                report['captures'] = []
                for frame, pose, weights in timeline:
                    if frame not in (0, 30, 90, 150):
                        continue
                    path = os.path.join(output_dir, 'cc_' + pose + '.png')
                    api.render_preview(path, frame_time(frame))
                    report['captures'].append({'frame': frame, 'pose': pose, 'image': api.bodyfit_freeze_file_record(path)})
            finally:
                phase('expression_motion_restore')
                if int(c.get('restore_expected_avatar_count', 1)) == 0:
                    restore = c['restore_project']
                    if api.sha256_file(restore['path']) != restore['sha256']:
                        raise ValueError('Empty-scene restore hash mismatch')
                    check('Restore locked empty scene', R.RFileIO.LoadFile(restore['path']))
                    report['restored_avatar_count'] = len(list(R.RScene.GetAvatars() or []))
                    if report['restored_avatar_count'] != 0:
                        raise ValueError('Empty-scene backup unexpectedly contains an avatar')
                else:
                    restored = load(c['restore_project'])
                    report['restored_profile_uid'] = str(restored.GetFaceComponent().GetExpressionSetUid())
            report['success'] = True
            report['acceptance'] = 'Animation collected; actual bone motion, images and UE playback remain to validate'
            phase('expression_motion_collected')
            result = {'success': True, 'report_path': report_path, 'summary_path': os.path.join(output_dir, 'validation_result.json')}
            api.write_json(result, result['summary_path'])
            return result
        if c.get('operation') == 'representative_export_probe':
            if library.get('eye_snapshot_mode') != 'transforms_only':
                raise ValueError('Representative export requires explicit transforms_only eye snapshots')
            legacy_export_root = r'D:\UE\exports\character_creator\headshot_routes_20261002_v1'
            native_pair_export_root = r'D:\UE\exports\character_creator\cfd_native_pair_20261006_v1'
            native_batch40_export_root = r'D:\UE\exports\character_creator\cfd_native_batch40_20261006_v1'
            refresh40_export_root = r'D:\UE\exports\character_creator\character_refresh_20261018_v1'
            refresh40_v2_export_root = r'D:\UE\exports\character_creator\character_refresh_20261018_v2'
            short_root = os.path.realpath(c.get('export_parent_root', legacy_export_root))
            allowed_export_roots = {os.path.normcase(os.path.realpath(p)) for p in
                                    (legacy_export_root, native_pair_export_root, native_batch40_export_root, refresh40_export_root, refresh40_v2_export_root)}
            if os.path.normcase(short_root) not in allowed_export_roots:
                raise ValueError('Unsupported representative export parent root')
            repeat_count = c.get('export_repeat_count', 2)
            if isinstance(repeat_count, bool) or not isinstance(repeat_count, int) or repeat_count not in (1, 2):
                raise ValueError('Representative export count must be 1 or 2')
            report['export_parent_root'] = short_root
            report['export_repeat_count'] = repeat_count
            case_id = c['case_id']
            if not case_id or not all(x.isalnum() or x == '_' for x in case_id):
                raise ValueError('Unsafe representative export case identifier')
            export_root = os.path.join(short_root, case_id)
            if os.path.exists(export_root):
                raise ValueError('Refusing to overwrite representative export')
            os.makedirs(export_root)
            setting = R.RExportFbxSetting()
            flags = R.EExportFbxOptions__None | R.EExportFbxOptions_AutoSkinRigidMesh | R.EExportFbxOptions_TPoseForCreateMorphTargetMesh | R.EExportFbxOptions_ExportPbrTextureAsImageInFormatDirectory
            flags2 = R.EExportFbxOptions2__None
            names = ('UnrealEngine4BoneAxis', 'UnrealPreset', 'UnrealIkBone',
                     'RenameDuplicateBoneName', 'RenameDuplicateMaterialName', 'RenameDuplicateMorphName',
                     'RenameTransparencyWithPostFix', 'RenameBoneRootToGameType', 'RenameBoneToLowerCase',
                     'RenameBoneOnStd', 'RenameMorphInvalidCharacter', 'ResetBoneScale',
                     'ResetSelfillumination', 'ExtraWordForUnityAndUnreal')
            for name in names:
                flags2 |= getattr(R, 'EExportFbxOptions2_' + name)
            for label, status in (
                ('No motion export', setting.EnableExportMotion(False)),
                ('Primary export flags', setting.SetOption(flags)),
                ('Unreal export flags', setting.SetOption2(flags2)),
                ('Sidecar JSON', setting.SetOption3(R.EExportFbxOptions3_ExportJson)),
                ('Original textures', setting.SetTextureSize(R.EExportTextureSize_Original)),
                ('Default texture format', setting.SetTextureFormat(R.EExportTextureFormat_Default)),
                ('UE5 bones', setting.SetUnrealBoneStructure(R.EUnrealBoneStructure_UE5_BoneStructure)),
                ('Original bind pose', setting.EnableBasicBindPose(False)),
                ('Base topology export', setting.EnableBakeSubdivision(False)),
            ):
                check(label, status)
            report['export_settings'] = {'option': int(flags), 'option2': int(flags2),
                                         'option2_names': list(names), 'motion': False,
                                         'bake_subdivision': False, 'bone_structure': 'UE5',
                                         'texture_size': 'Original', 'texture_format': 'Default'}
            report['exports'] = []
            for repeat in range(repeat_count):
                phase('representative_export_load_' + str(repeat))
                avatar = load(c['source_project'])
                report['export_source_state_' + str(repeat)] = state(avatar)
                attempt = os.path.join(export_root, 'reload_' + str(repeat))
                os.makedirs(attempt)
                fbx = os.path.join(attempt, 'character.fbx')
                phase('representative_export_fbx_' + str(repeat))
                check('Export independent representative FBX', R.RFileIO.ExportFbxFile(avatar, fbx, setting))
                sidecar = os.path.splitext(fbx)[0] + '.json'
                if not os.path.isfile(fbx) or not os.path.isfile(sidecar):
                    raise ValueError('Representative FBX or sidecar absent')
                files = [api.bodyfit_freeze_file_record(os.path.join(base, name))
                         for base, dirs, names in os.walk(attempt) for name in names]
                report['exports'].append({'repeat': repeat, 'fbx': fbx, 'sidecar': sidecar, 'files': files})
                report['post_export_state_' + str(repeat)] = state(avatar)
            report['success'] = True
            phase('representative_export_collected')
            result = {'success': True, 'report_path': report_path,
                      'summary_path': os.path.join(output_dir, 'validation_result.json')}
            api.write_json(result, result['summary_path'])
            return result
        if c.get('operation') == 'subdivision_level_mesh_probe':
            # Capture every exposed mesh level, not just the low-resolution cage.
            # This diagnoses which stored level changes during the first switch.
            restore = c['restore_project']
            restore_path = os.path.realpath(restore['path'])
            if os.path.commonpath([ROOT, restore_path]) != ROOT or api.sha256_file(restore_path) != restore['sha256']:
                raise ValueError('Mesh-level probe requires a locked independent restore project')
            report['source_project'] = c['source_project']
            report['restore_project'] = restore
            report['captures'] = []
            try:
                phase('mesh_level_probe_load')
                avatar = load(c['source_project'])
                def capture_levels(label):
                    meshes = []
                    keys = set()
                    for mesh in avatar.GetMeshes(False):
                        key = (str(mesh.GetName()), int(mesh.GetVerticesCount()))
                        if key in keys:
                            raise ValueError('Ambiguous exposed mesh level: ' + str(key))
                        keys.add(key)
                        vertices = [[float(v.x), float(v.y), float(v.z)] for v in mesh.GetVertices(False)]
                        if len(vertices) != key[1]:
                            raise ValueError('Mesh-level vertex count/query length mismatch')
                        if not all(math.isfinite(x) for v in vertices for x in v):
                            raise ValueError('Non-finite mesh-level probe coordinates')
                        meshes.append({'name': key[0], 'vertex_count': key[1], 'vertices': vertices})
                        if c.get('verify_vertex_queries', False):
                            # A second query path and reverse enumeration distinguish
                            # reproducible SDK arrays from stale Python proxy reads.
                            count = key[1]
                            indices = {int(i * (count - 1) / 127) for i in range(128)} if count else set()
                            indices.update(c.get('vertex_probe_indices', {}).get(key[0] + ':' + str(count), []))
                            if any(not isinstance(i, int) or i < 0 or i >= count for i in indices):
                                raise ValueError('Invalid scalar vertex probe index')
                            samples = []
                            for index in sorted(indices):
                                value = mesh.GetVertex(index, False)
                                scalar = [float(value.x), float(value.y), float(value.z)]
                                if not all(math.isfinite(x) for x in scalar):
                                    raise ValueError('Non-finite scalar vertex query')
                                samples.append({'index': index, 'vertex': scalar,
                                                'delta_mm': math.sqrt(sum((a-b)**2 for a,b in zip(scalar, vertices[index]))) * 10.0})
                            meshes[-1]['scalar_vertex_query'] = samples
                    if c.get('verify_vertex_queries', False):
                        by_key = {(m['name'], m['vertex_count']): m for m in meshes}
                        reverse_keys = set()
                        for mesh in reversed(list(avatar.GetMeshes(False))):
                            key = (str(mesh.GetName()), int(mesh.GetVerticesCount()))
                            if key not in by_key or key in reverse_keys:
                                raise ValueError('Mesh identity changed during reverse query')
                            reverse_keys.add(key)
                            repeated = [[float(v.x), float(v.y), float(v.z)] for v in mesh.GetVertices(False)]
                            original = by_key[key]['vertices']
                            if len(repeated) != len(original) or not all(math.isfinite(x) for v in repeated for x in v):
                                raise ValueError('Invalid reverse mesh query')
                            by_key[key]['reverse_query_max_delta_mm'] = max(
                                (math.sqrt(sum((a-b)**2 for a,b in zip(v, w))) * 10.0 for v,w in zip(original, repeated)), default=0.0)
                        if reverse_keys != set(by_key):
                            raise ValueError('Missing mesh during reverse query')
                    path = os.path.join(output_dir, label + '_all_mesh_levels.json')
                    api.write_json(meshes, path)
                    report['captures'].append({'label': label,
                                              'subdivision': int(avatar.GetSubdivMeshLevel()),
                                              'max_subdivision': int(avatar.GetMaxSubdivMeshLevel()),
                                              'meshes': api.bodyfit_freeze_file_record(path)})
                capture_levels('loaded')
                for label, level in [('initial0', 0), ('first1', 1), ('return0', 0),
                                     ('second1', 1), ('second_return0', 0)]:
                    phase('mesh_level_probe_' + label)
                    check('Switch mesh-level probe', avatar.SwitchSubdivMeshLevel(level))
                    api.force_avatar_scene_evaluation(avatar)
                    if int(avatar.GetSubdivMeshLevel()) != level:
                        raise ValueError('Mesh-level probe switch did not take effect')
                    capture_levels(label)
            finally:
                avatar = load(restore)
                report['restored_subdivision'] = int(avatar.GetSubdivMeshLevel())
            report['success'] = True
            report['acceptance'] = 'Exposed mesh-level diagnosis only; no body or route acceptance'
            phase('mesh_level_probe_complete')
            result = {'success': True, 'report_path': report_path,
                      'summary_path': os.path.join(output_dir, 'validation_result.json')}
            api.write_json(result, result['summary_path'])
            return result
        if c.get('operation') == 'measurement_side_effect_probe':
            phase('measurement_probe_load_without_morph_notification')
            record = c['source_project']
            if api.sha256_file(record['path']) != record['sha256']:
                raise ValueError('Measurement source SHA mismatch')
            check('Load independent measurement source', R.RFileIO.LoadFile(record['path']))
            avatars = list(R.RScene.GetAvatars() or [])
            if len(avatars) != 1:
                raise ValueError('Expected one measurement avatar')
            avatar = avatars[0]
            report['measurements'] = []

            def raw_capture(label):
                mesh = [m for m in avatar.GetMeshes(False)
                        if m.GetName() == 'CC_Base_Body' and m.GetVerticesCount() == 14164][0]
                data = {'subdivision': int(avatar.GetSubdivMeshLevel()),
                        'world': [[float(v.x), float(v.y), float(v.z)] for v in mesh.GetVertices(True)],
                        'local': [[float(v.x), float(v.y), float(v.z)] for v in mesh.GetVertices(False)],
                        'bones': [{'name': b.GetName(), 'world': api._transform_data(b.WorldTransform())}
                                  for b in avatar.GetSkeletonComponent().GetSkinBones()]}
                path = os.path.join(output_dir, label + '.json')
                api.write_json(data, path)
                report['measurements'].append({'label': label, 'file': path})

            raw_capture('loaded')
            raw_capture('read_only_repeat')
            operations = [('set_time', lambda: R.RGlobal.SetTime(R.RGlobal.GetStartTime(), True)),
                          ('notify_morph', lambda: R.RGlobal.ObjectModified(avatar, R.EObjectModifiedType_MorphWeight)),
                          ('export_obj', None),
                          ('switch_same', lambda: avatar.SwitchSubdivMeshLevel(avatar.GetSubdivMeshLevel())),
                          ('switch_1', lambda: avatar.SwitchSubdivMeshLevel(1)),
                          ('switch_0', lambda: avatar.SwitchSubdivMeshLevel(0))]
            for name, operation in operations:
                for repeat in range(2):
                    label = '{}_{}'.format(name, repeat)
                    phase('measurement_probe_' + label)
                    if name == 'export_obj':
                        check(label, R.RFileIO.ExportObjFile(avatar, os.path.join(output_dir, label + '.obj'),
                                                           R.EExport3DFileOption_BodyPart))
                    else:
                        check(label, operation())
                    api.QtWidgets.QApplication.processEvents()
                    raw_capture(label)
            report['success'] = True
            phase('measurement_probe_complete')
            result = {'success': True, 'report_path': report_path,
                      'summary_path': os.path.join(output_dir, 'validation_result.json')}
            api.write_json(result, result['summary_path'])
            return result
        if c.get('operation') == 'subdivision_roundtrip_probe':
            phase('subdivision_probe_load')
            avatar = load(c['source_project'])
            report['source_state'] = state(avatar)
            report['probe_sequence'] = []
            for level, label in ((0, 'initial_0'), (0, 'repeat_0'), (1, 'first_1'), (0, 'return_0'),
                                 (1, 'second_1'), (0, 'second_return_0')):
                phase('subdivision_probe_' + label)
                check('Probe switch subdivision', avatar.SwitchSubdivMeshLevel(level))
                api.force_avatar_scene_evaluation(avatar)
                record = {'label': label, 'requested': level,
                          'actual': int(avatar.GetSubdivMeshLevel())}
                if level == 0:
                    record['obj'] = mesh_capture(avatar, label)
                    mesh = [m for m in avatar.GetMeshes(False)
                            if m.GetName() == 'CC_Base_Body' and m.GetVerticesCount() == 14164][0]
                    api.write_json({'vertices': [[float(v.x), float(v.y), float(v.z)]
                                                 for v in mesh.GetVertices(False)],
                                    'bones': [{'name': b.GetName(),
                                               'world_transform': api._transform_data(b.WorldTransform())}
                                              for b in avatar.GetSkeletonComponent().GetSkinBones()]},
                                   os.path.join(output_dir, label + '_local_and_bones.json'))
                report['probe_sequence'].append(record)
            report['roundtrip_subd0_project'] = save(avatar, 'roundtrip_subd0')
            avatar = load(report['roundtrip_subd0_project'])
            report['roundtrip_reload_obj'] = mesh_capture(avatar, 'roundtrip_reload_0')
            check('Probe save at subdivision 1', avatar.SwitchSubdivMeshLevel(1))
            report['roundtrip_subd1_project'] = save(avatar, 'roundtrip_subd1')
            avatar = load(report['roundtrip_subd1_project'])
            check('Probe reload subdivision 1 then switch 0', avatar.SwitchSubdivMeshLevel(0))
            report['subd1_reload_to0_obj'] = mesh_capture(avatar, 'subd1_reload_to0')
            avatar = load(c['source_project'])
            report['restored_state'] = state(avatar)
            report['success'] = True
            phase('subdivision_probe_complete')
            result = {'success': True, 'report_path': report_path,
                      'summary_path': os.path.join(output_dir, 'validation_result.json')}
            api.write_json(result, result['summary_path'])
            return result
        if c.get('operation') == 'current_subdivision_checkpoint':
            # Capture the UI operation before any load or subdivision switch can
            # replace its result. Source is lineage only, never loaded here.
            source = os.path.realpath(c['source_project']['path'])
            if os.path.commonpath([ROOT, source]) != ROOT or api.sha256_file(source) != c['source_project']['sha256']:
                raise ValueError('Subdivision checkpoint source lineage mismatch')
            if not c.get('ui_observation'):
                raise ValueError('Current-scene checkpoint requires a recorded UI observation')
            avatars = list(R.RScene.GetAvatars() or [])
            if len(avatars) != 1:
                raise ValueError('Expected one independent subdivision avatar')
            avatar = avatars[0]
            actual = (int(avatar.GetSubdivMeshLevel()), int(avatar.GetMaxSubdivMeshLevel()))
            expected = (int(c['expected_subdivision']), int(c['expected_max_subdivision']))
            if actual != expected or actual[0] != 0:
                raise ValueError('Checkpoint requires observed active base mesh: {} != {}'.format(actual, expected))
            report['source_project'] = c['source_project']
            report['ui_observation'] = c['ui_observation']
            phase('current_subdivision_checkpoint_capture')
            def checkpoint_geometry(label):
                data = [{'name': m.GetName(), 'count': int(m.GetVerticesCount()),
                         'local': [[float(v.x), float(v.y), float(v.z)] for v in m.GetVertices(False)]}
                        for m in avatar.GetMeshes(False)]
                path = os.path.join(output_dir, label + '_local_meshes.json')
                api.write_json(data, path)
                return api.bodyfit_freeze_file_record(path)
            report['before_state'] = state(avatar)
            report['before_local_meshes'] = checkpoint_geometry('before_save')
            report['before_obj'] = mesh_capture(avatar, 'before_save')
            report['checkpoint_project'] = save(avatar, 'subdivision_checkpoint')
            avatar = load(report['checkpoint_project'])
            report['reloaded_state'] = state(avatar)
            report['reloaded_local_meshes'] = checkpoint_geometry('reloaded')
            report['reloaded_obj'] = mesh_capture(avatar, 'reloaded')
            report['success'] = True
            report['acceptance'] = 'Checkpoint evidence only; geometry comparisons and visual review remain required'
            phase('current_subdivision_checkpoint_saved')
            result = {'success': True, 'report_path': report_path,
                      'summary_path': os.path.join(output_dir, 'validation_result.json')}
            api.write_json(result, result['summary_path'])
            return result
        if c.get('operation') == 'capture_ui_subdivision':
            phase('capture_ui_subdivision')
            avatars = list(R.RScene.GetAvatars() or [])
            if len(avatars) != 1:
                raise ValueError('Expected one prepared subdivision avatar')
            avatar = avatars[0]
            report['prepared_source'] = c['source_project']
            if api.sha256_file(c['source_project']['path']) != c['source_project']['sha256']:
                raise ValueError('Prepared source changed on disk')
            report['ui_subdivision_state'] = state(avatar)
            if report['ui_subdivision_state']['subdivision'] != 1 or report['ui_subdivision_state']['max_subdivision'] < 1:
                raise ValueError('UI Subdivide did not create target level')
            local_path = os.path.join(output_dir, 'ui_rebuilt_local_meshes.json')
            api.write_json([{'name': m.GetName(), 'count': int(m.GetVerticesCount()),
                             'local': [[float(v.x), float(v.y), float(v.z)] for v in m.GetVertices(False)]}
                            for m in avatar.GetMeshes(False)], local_path)
            report['ui_rebuilt_local_meshes'] = api.bodyfit_freeze_file_record(local_path)
            report['subdivision_ready_project'] = save(avatar, 'subdivision_ready')
            check('UI subdivision base mesh comparison', avatar.SwitchSubdivMeshLevel(0))
            report['after_ui_subdivision_obj'] = mesh_capture(avatar, 'after_ui_subdivision')
            avatar = load(report['subdivision_ready_project'])
            report['reloaded_ui_subdivision_state'] = state(avatar)
            report['success'] = True
            phase('ui_subdivision_captured')
            result = {'success': True, 'report_path': report_path,
                      'summary_path': os.path.join(output_dir, 'validation_result.json')}
            api.write_json(result, result['summary_path'])
            return result
        if c.get('operation') == 'material_probe':
            phase('material_probe_load_copy')
            avatar = load(c['source_project'])
            component = avatar.GetMaterialComponent()
            report['material_records'] = []
            for mesh_name in avatar.GetMeshNames():
                for material_name in component.GetMaterialNames(mesh_name):
                    item = {'mesh': str(mesh_name), 'material': str(material_name),
                            'shader': str(component.GetShader(mesh_name, material_name)),
                            'properties': {}, 'parameters': {}}
                    for method in ('GetDiffuseColor', 'GetAmbientColor', 'GetSpecularColor',
                                   'GetSelfIlluminationWeight', 'GetOpacity'):
                        try:
                            value = getattr(component, method)(mesh_name, material_name)
                            item['properties'][method] = ([float(value.R()), float(value.G()), float(value.B())]
                                                         if isinstance(value, R.RRgb) else api.material_value(value))
                        except Exception as exc:
                            item['properties'][method] = {'error': str(exc)}
                    for name in component.GetShaderParameterNames(mesh_name, material_name) or []:
                        try:
                            item['parameters'][str(name)] = api.material_value(component.GetShaderParameter(mesh_name, material_name, name))
                        except Exception as exc:
                            item['parameters'][str(name)] = {'error': str(exc)}
                    if str(material_name) in c.get('texture_probe_materials', []):
                        item['texture_images'] = {}
                        item['texture_color_adjustments'] = {}
                        for channel_name in ('Diffuse', 'Opacity', 'Bump'):
                            try:
                                channel = getattr(R, 'EMaterialTextureChannel_' + channel_name)
                                try:
                                    item['texture_color_adjustments'][channel_name] = api.material_value(
                                        component.GetImageColor(mesh_name, material_name, channel))
                                except Exception as exc:
                                    item['texture_color_adjustments'][channel_name] = {'error': str(exc)}
                                texture = component.GetImage(mesh_name, material_name, channel)
                                path = os.path.join(output_dir, str(material_name) + '_' + channel_name + '.png')
                                info = {'width': texture.GetWidth(), 'height': texture.GetHeight()}
                                check('Save probe texture', texture.SaveFile(path))
                                info['file'] = api.bodyfit_freeze_file_record(path)
                                item['texture_images'][channel_name] = info
                            except Exception as exc:
                                item['texture_images'][channel_name] = {'error': str(exc)}
                    report['material_records'].append(item)
            report['success'] = True
            phase('material_probe_complete')
            result = {'success': True, 'report_path': report_path,
                      'summary_path': os.path.join(output_dir, 'validation_result.json')}
            api.write_json(result, result['summary_path'])
            return result
        if c.get('operation') == 'eye_snapshot_probe':
            phase('eye_probe_load_copy')
            avatar = load(c['source_project'])
            skeleton = avatar.GetSkeletonComponent()
            bones = [b for b in skeleton.GetSkinBones() if 'eye' in b.GetName().lower()]
            report['probe_calls'] = []

            def eye_transforms():
                return [{'name': b.GetName(),
                         'local_transform': api._transform_data(b.LocalTransform()),
                         'basis_transform': api._transform_data(b.BasisTransform()),
                         'world_transform': api._transform_data(b.WorldTransform())}
                        for b in bones]

            report['before_transforms'] = eye_transforms()
            report['before_probe_obj'] = mesh_capture(avatar, 'before_probe')
            # Separate progress records identify exactly which SDK call blocks.
            # This probe deliberately does not run the existing combined helper.
            for operation in ('update', 't_pose_position'):
                for bone in bones:
                    label = 'eye_probe_{}_{}'.format(operation, bone.GetName())
                    phase(label)
                    started = time.monotonic()
                    value = bone.Update() if operation == 'update' else skeleton.GetBoneTPosePosition(bone)
                    report['probe_calls'].append({
                        'operation': operation, 'bone': bone.GetName(),
                        'elapsed_seconds': time.monotonic() - started,
                        'value': api._vector3_data(value) if operation == 't_pose_position' else str(value),
                    })
                    phase(label + '_returned')
                report['after_' + operation + '_transforms'] = eye_transforms()
            report['after_probe_obj'] = mesh_capture(avatar, 'after_probe')
            report['success'] = True
            phase('eye_snapshot_probe_complete')
            result = {'success': True, 'report_path': report_path,
                      'summary_path': os.path.join(output_dir, 'validation_result.json')}
            api.write_json(result, result['summary_path'])
            return result
        if c.get('operation') == 'capture_calibration':
            phase('capture_calibration')
            avatar = load(c['source_project'])
            report['state'] = state(avatar)
            report['stable_eye_state'], report['eye_stabilization'] = api.capture_stable_neutral_eye_state(avatar)
            camera(avatar)
            report['view_size'] = api.current_view_size()
            api.render_preview(os.path.join(output_dir, 'native_aspect_front.png'))
            avatar = load(c['source_project'])
            report['success'] = True
            phase('capture_calibration_complete')
            result = {'success': True, 'report_path': report_path,
                      'summary_path': os.path.join(output_dir, 'validation_result.json')}
            api.write_json(result, result['summary_path'])
            return result
        if c.get('operation') == 'prepare_subdivision':
            phase('prepare_independent_subdivision_copy')
            avatar = load(c['source_project'])
            report['before_subdivision'] = state(avatar)
            check('Prepared subdivision base mesh', avatar.SwitchSubdivMeshLevel(0))
            report['before_ui_subdivision_obj'] = mesh_capture(avatar, 'before_ui_subdivision')
            report['prepared_project'] = save(avatar, 'subdivision_preparation')
            report['success'] = True
            report['acceptance'] = 'Independent copy prepared; UI subdivision and recapture still required'
            phase('prepared_for_ui_subdivision')
            result = {'success': True, 'report_path': report_path,
                      'summary_path': os.path.join(output_dir, 'validation_result.json')}
            api.write_json(result, result['summary_path'])
            return result
        if c.get('capture_average_reference'):
            phase('average_reference')
            avatar = load(library['presets'][0]['source_project'])
            report['average_reference_state'] = state(avatar)
            camera(avatar)
            api.render_preview(os.path.join(output_dir, 'average_before_obj_front.png'))
            avatar = load(library['presets'][0]['source_project'])
            check('Reference SubD 0', avatar.SwitchSubdivMeshLevel(0))
            report['average_reference_obj'] = mesh_capture(avatar, 'average_reference')
            camera(avatar)
            api.render_preview(os.path.join(output_dir, 'average_reference_front.png'))

        phase('load_generated_copy')
        avatar = load(c['source_project'])
        camera(avatar)
        api.render_preview(os.path.join(output_dir, 'generated_before_obj_front.png'))
        avatar = load(c['source_project'])
        check('Route working SubD 0', avatar.SwitchSubdivMeshLevel(0))
        report['generated_state'] = state(avatar)
        report['generated_obj'] = mesh_capture(avatar, 'generated')
        if c.get('eyelash_diffuse_repair'):
            phase('repair_eyelash_diffuse_only')
            record = c['eyelash_diffuse_repair']
            path = os.path.realpath(record['path'])
            if os.path.commonpath([ROOT, path]) != ROOT or api.sha256_file(path) != record['sha256']:
                raise ValueError('Eyelash diffuse evidence path/hash mismatch')
            component = avatar.GetMaterialComponent()
            mesh_name, material_name = 'CC_Base_Body', 'Std_Eyelash'
            if material_name not in component.GetMaterialNames(mesh_name):
                raise ValueError('Expected existing legacy eyelash material')
            opacity_before = os.path.join(output_dir, 'eyelash_opacity_before.png')
            opacity_after = os.path.join(output_dir, 'eyelash_opacity_after.png')
            check('Save unchanged opacity before repair', component.GetImage(
                mesh_name, material_name, R.EMaterialTextureChannel_Opacity).SaveFile(opacity_before))
            check('Replace only eyelash diffuse texture', component.LoadImageToTexture(
                mesh_name, material_name, R.EMaterialTextureChannel_Diffuse, path))
            api.force_avatar_scene_evaluation(avatar)
            check('Save unchanged opacity after repair', component.GetImage(
                mesh_name, material_name, R.EMaterialTextureChannel_Opacity).SaveFile(opacity_after))
            if api.sha256_file(opacity_before) != api.sha256_file(opacity_after):
                raise ValueError('Opacity changed during diffuse-only repair')
            report['eyelash_diffuse_repair'] = {'source': record, 'opacity_unchanged': True,
                                               'opacity_sha256': api.sha256_file(opacity_after)}
            report['eyelash_repaired_obj'] = mesh_capture(avatar, 'eyelash_repaired')
            report['eyelash_repaired_state'] = state(avatar)
        if c.get('appearance_support_assets'):
            phase('apply_existing_appearance_support')
            report['appearance_support_assets'] = c['appearance_support_assets']
            report['appearance_support_dialogs'] = []
            for record in c['appearance_support_assets']:
                if api.sha256_file(record['path']) != record['sha256']:
                    raise ValueError('Appearance input SHA mismatch')
                if not record['path'].lower().endswith(('.cceye', '.ccteeth')):
                    raise ValueError('Route material-only support is limited to existing eyes and teeth')
                R.RScene.SelectObject(avatar)
                status, dialogs = api.load_file_with_material_only_dialog(
                    record['path'], 'Load existing appearance support material only')
                report['appearance_support_dialogs'].append({
                    'source': record, 'status': status, 'dialogs': dialogs})
                api.force_avatar_scene_evaluation(avatar)
            report['appearance_support_state'] = state(avatar)
            report['appearance_support_obj'] = mesh_capture(avatar, 'appearance_support')
        if c['route'] == 'r2':
            phase('upgrade_cc5_facial_profile')
            pc = avatar.GetFacialProfileComponent()
            check('Save source facial profile', pc.SaveProfile(os.path.join(output_dir, 'source_profile.ccFacialProfile')))
            record = c['target_facial_profile']
            if api.sha256_file(record['path']) != record['sha256']:
                raise ValueError('Target profile SHA mismatch')
            check('Load CC5 HD facial profile', pc.LoadProfile(record['path']))
            api.force_avatar_scene_evaluation(avatar)
            report['profile_upgraded_state'] = state(avatar)
            report['profile_upgraded_obj'] = mesh_capture(avatar, 'profile_upgraded')
            phase('apply_average_bodyfit')
            preset = library['presets'][0]
            report['bodyfit_application'] = api.apply_bodyfit(avatar, preset['target_body_morphs'], preset['target_junction_morphs'])
            api.force_avatar_scene_evaluation(avatar)
            report['average_bodyfit_obj'] = mesh_capture(avatar, 'average_bodyfit')
        if c.get('proportion_preset'):
            phase('apply_head_neck_proportion')
            avatar, report['proportion_application'] = api.apply_bodyfit_proportion_adjustment(avatar, c['proportion_preset'], phase)
        if c.get('normalize_subdivision_before_save'):
            phase('normalize_first_subdivision_before_final_measurement')
            report['pre_normalization_obj'] = mesh_capture(avatar, 'pre_normalization')
            for level in (1, 0):
                if int(avatar.GetSubdivMeshLevel()) != level:
                    check('Normalize initial subdivision transition', avatar.SwitchSubdivMeshLevel(level))
                api.force_avatar_scene_evaluation(avatar)
            report['normalized_obj'] = mesh_capture(avatar, 'normalized')
            report['normalization_scope'] = 'Experimental first 0-1-0 transition before final-body measurement; not an acceptance waiver'
        report['final_state_before_save'] = state(avatar)
        report['before_save_obj'] = mesh_capture(avatar, 'before_save')
        phase('save_subd0_copy')
        project0 = save(avatar, 'final_subd0')
        report['subd0_project'] = project0
        avatar = load(project0)
        report['reloaded_subd0_state'] = state(avatar)
        report['reloaded_subd0_obj'] = mesh_capture(avatar, 'reloaded_subd0')
        phase('restore_subd1_and_save')
        check('Restore target SubD 1', avatar.SwitchSubdivMeshLevel(1))
        api.force_avatar_scene_evaluation(avatar)
        report['subd1_state'] = state(avatar)
        report['target_subd1_achieved'] = report['subd1_state']['subdivision'] == 1
        project1 = save(avatar, 'final_subd1')
        report['subd1_project'] = project1
        avatar = load(project1)
        report['reloaded_subd1_state'] = state(avatar)
        camera(avatar)
        phase('render_neutral_after_reload')
        api.render_preview(os.path.join(output_dir, 'neutral_subd1_front.png'))
        api.set_avatar_yaw(avatar, 45.0)
        api.force_avatar_scene_evaluation(avatar)
        api.render_preview(os.path.join(output_dir, 'neutral_subd1_three_quarter.png'))
        phase('dynamic_face_validation')
        pose_dir = os.path.join(output_dir, 'poses')
        os.makedirs(pose_dir)
        report['poses'] = api.render_profile_upgrade_pose_matrix(avatar, pose_dir, phase, R.RGlobal.GetStartTime(), [0.0, 8.0, 6.0])
        avatar = load(project1)
        phase('post_subdivision_export')
        check('Return to SubD 0 for comparable OBJ', avatar.SwitchSubdivMeshLevel(0))
        report['after_subdivision_obj'] = mesh_capture(avatar, 'after_subdivision')
        avatar = load(project1)
        report['final_restored_state'] = state(avatar)
        report['success'] = True
        report['acceptance'] = 'Evidence collected; offline geometry and image inspection required'
        phase('evidence_collected')
    except Exception as exc:
        report['error'] = str(exc)
        report['traceback'] = traceback.format_exc()
        phase('failed')
    result = {'success': report['success'], 'report_path': report_path,
              'summary_path': os.path.join(output_dir, 'validation_result.json')}
    api.write_json(result, result['summary_path'])
    return result
