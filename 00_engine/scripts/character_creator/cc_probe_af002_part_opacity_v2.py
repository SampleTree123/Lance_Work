"""Four independent AF002 owner-opacity isolates; reload base before each.

No geometry/SkinGen/assembly/export change, candidate save or acceptance.
Opacity PNG readback proves the slot write, not that an HD shader honors it.
"""
import os
import shutil
import sys
import traceback

MODE = 'af002_part_opacity_diagnostic_v2'
SOURCE_SHA = '1b16d42a254bcccf769a5c93560b0e4f4749a7aef076fc10b117c057de0a0f15'
TARGETS = [('new_upper_lash', '9', 'Lash_Up_Dropping'), ('tearline', '6', 'CC_Base_TearLine'),
           ('eye_occlusion', '5', 'CC_Base_EyeOcclusion'), ('new_lower_lash', '9', 'Lash_Low_Outward')]


def actual_materials(avatar, part_type, name, api):
    owners = [p for p in avatar.GetAvatarParts() or []
              if str(p.GetAvatarPartType()) == part_type and str(p.GetName()) == name]
    if len(owners) != 1:
        raise ValueError('One exact actual target owner required: ' + name)
    owner = owners[0]
    component, source = api.hair_material_component(avatar, owner)
    getter = getattr(owner, 'GetMeshNames', None)
    meshes = getter() if callable(getter) else [m.GetName() for m in owner.GetMeshes(False) or []]
    rows = [(str(mesh), str(material)) for mesh in sorted(set(meshes or []))
            for material in sorted(set(component.GetMaterialNames(str(mesh)) or []))]
    if not rows:
        raise ValueError('Target actual material inventory is empty: ' + name)
    return component, rows, dict(owner='avatar/' + part_type + ':' + name,
                                 component_source=source, keys=[list(r) for r in rows])


def run(library, output_dir, log, api):
    if os.path.dirname(__file__) not in sys.path:
        sys.path.insert(0, os.path.dirname(__file__))
    import cc_refresh_visual_probe_v1 as visual
    import cc_repair_headshot_support_materials_v1 as png
    c = library[MODE]
    if (c.get('character_id') != 'CFD40_AF_002' or c.get('working_subdivision_level') != 0
            or c.get('operation') != 'independent_owner_opacity_black_reload_between_four_images'
            or c.get('save_current_scene_backup') is not True
            or c['source_project']['sha256'] != SOURCE_SHA):
        raise ValueError('Only exact AF002 independent SubD0 opacity diagnosis allowed')
    for key in ('source_project', 'black_opacity', 'camera', 'light', 'baseline_image', 'prior_native_diagnostic'):
        if api.sha256_file(c[key]['path']) != c[key]['sha256']:
            raise ValueError('Diagnostic input pin changed: ' + key)
    prior = api.read_json(c['prior_native_diagnostic']['path'])
    if not prior.get('success') or not prior['restoration']['success'] or prior['source_project']['sha256'] != SOURCE_SHA:
        raise ValueError('Same-source actual native opacity diagnostic required')
    if not visual.inside(output_dir, visual.RUN_ROOT):
        raise ValueError('Independent refresh artifact output required')
    os.makedirs(output_dir, exist_ok=True)
    report_path = os.path.join(output_dir, 'part_opacity_diagnostic_report.json')
    summary_path = os.path.join(output_dir, 'validation_result.json')
    report = dict(character_id='CFD40_AF_002', success=False, source_project=c['source_project'],
                  implementation_sha256=api.sha256_file(__file__), captures=[], variables=[],
                  baseline_image=c['baseline_image'], prior_native_diagnostic=c['prior_native_diagnostic'],
                  working_subdivision_level=0, report_path=report_path, summary_path=summary_path,
                  accepted_final=False, recipe_complete=False, visual_acceptance='pending_root_comparison',
                  scope='One actual owner at a time; all its actual mesh/material opacity slots only. Each starts from the unchanged base. No inference that a black standard opacity slot disables an HD custom shader.')
    R = api.RLPy
    working = None
    attempted = False
    originals = {}

    def checkpoint(phase):
        report['phase'] = phase
        api.write_json(report, report_path)
        log('AF002 independent part opacity: ' + phase)

    def load(label):
        nonlocal attempted
        attempted = True
        if api.sha256_file(working['path']) != SOURCE_SHA:
            raise ValueError('Independent source copy changed')
        status, dialogs = api.load_file_with_optional_undo_warning(working['path'], label)
        report.setdefault('loads', []).append(dict(label=label, status=status, dialogs=dialogs))
        avatars = list(R.RScene.GetAvatars() or [])
        if len(avatars) != 1 or int(avatars[0].GetSubdivMeshLevel()) != 0:
            raise ValueError('One actual SubD0 source avatar required; no level switching')
        current = avatars[0]
        R.RScene.SelectObject(current)
        api.force_avatar_scene_evaluation(current)
        return current

    def read_opacity(component, keys, label):
        rows = []
        for index, (mesh, material) in enumerate(keys):
            image = component.GetImage(mesh, material, R.EMaterialTextureChannel_Opacity)
            row = dict(mesh=mesh, material=material, available=False)
            if image is not None and image.GetWidth() > 0 and image.GetHeight() > 0:
                path = os.path.join(output_dir, '{}_{}_opacity.png'.format(label, index))
                api.checked('Read actual target opacity', image.SaveFile(path))
                record = api.bodyfit_freeze_file_record(path)
                row.update(available=record['sha256'] != '38eb6ecb3423431ffae01afeff4ad43b14260fb47874a2f10677a2ffba298385',
                           image=record, width=int(image.GetWidth()), height=int(image.GetHeight()))
            rows.append(row)
        return rows

    def front(current, label):
        for key in ('light', 'camera'):
            api.checked('Load same verified ' + key, R.RFileIO.LoadFile(c[key]['path']))
        face = current.GetFaceComponent()
        names = list(face.GetExpressionNames('') or [])
        _, direct, _ = visual.direct_blink_pose(names)
        time = R.RGlobal.GetStartTime()
        api.checked('Begin neutral', face.BeginKeyEditing())
        try:
            api.checked('Set same neutral', face.AddExpressionKeys(time, direct, [0.] * len(direct),
                R.IndexedFrameTime(0, R.RGlobal.GetFps())))
        finally:
            api.checked('End neutral', face.EndKeyEditing())
        api.checked('Evaluate neutral', R.RGlobal.SetTime(time, True))
        api.set_avatar_position(current, -80., 8., 12.)
        api.set_avatar_yaw(current, 90.)
        api.force_avatar_scene_evaluation(current)
        path = os.path.join(output_dir, label + '_neutral_front.png')
        api.render_preview(path, time)
        width, height = visual.png_dimensions(path)
        decoded = api.QtGui.QImage(path)
        pose = visual.expression_readback(face, time, names, {})
        if decoded.isNull() or (decoded.width(), decoded.height()) != (width, height) or not pose['passed']:
            raise ValueError('Actual diagnostic image/neutral readback failed')
        report['captures'].append(dict(variable=label, pose='neutral', view='front', working_subdivision_level=0,
            expression_readback=pose, image=dict(api.bodyfit_freeze_file_record(path), width=width, height=height, image_decoded=True)))

    try:
        checkpoint('backup_and_copy_exact_final')
        backup = os.path.join(output_dir, 'scene_before_diagnostic.ccProject')
        api.checked('Save independent pre-diagnostic backup', R.RFileIO.SaveProject(backup))
        report['scene_backup'] = api.bodyfit_freeze_file_record(backup)
        copy_path = os.path.join(output_dir, 'AF002_unchanged_final_copy.ccProject')
        shutil.copyfile(c['source_project']['path'], copy_path)
        working = api.bodyfit_freeze_file_record(copy_path)
        report['working_source'] = working
        for label, part_type, name in TARGETS:
            checkpoint('fresh_base_for_' + label)
            current = load('Reload independent base before ' + label)
            component, keys, inventory = actual_materials(current, part_type, name, api)
            before = read_opacity(component, keys, label + '_before')
            originals[label] = before
            variable = dict(label=label, actual_inventory=inventory, before=before, writes=[])
            report['variables'].append(variable)
            for mesh, material in keys:
                api.checked('Isolate exact owner opacity only', component.LoadImageToTexture(
                    mesh, material, R.EMaterialTextureChannel_Opacity, c['black_opacity']['path']))
                variable['writes'].append(dict(mesh=mesh, material=material, channel='EMaterialTextureChannel_Opacity'))
            front(current, label)
            after = read_opacity(component, keys, label + '_after')
            variable['after'] = after
            variable['black_slot_pixels_verified'] = all(row['available'] and png.compare_png_images(
                c['black_opacity']['path'], row['image']['path'], api)['rgba_pixels_equal'] for row in after)
            if not variable['black_slot_pixels_verified']:
                raise ValueError('Actual black opacity slot readback failed: ' + label)
            checkpoint('captured_' + label)
        report['capture_complete'] = len(report['captures']) == 4
    except Exception as error:
        report['error'] = dict(type=type(error).__name__, message=str(error), traceback=traceback.format_exc())
    finally:
        report['restoration'] = dict(attempted=attempted, success=False, checks=[])
        if attempted and working is not None:
            try:
                checkpoint('finally_reload_unchanged_base')
                restored = load('Discard every opacity/framing mutation; reload exact AF002 copy')
                for label, part_type, name in TARGETS:
                    if label not in originals:
                        continue
                    component, keys, inventory = actual_materials(restored, part_type, name, api)
                    observed = read_opacity(component, keys, label + '_restored')
                    old = originals[label]
                    passed = [(r['mesh'], r['material'], r['available']) for r in old] == [
                        (r['mesh'], r['material'], r['available']) for r in observed]
                    if passed:
                        passed = all(not a['available'] or png.compare_png_images(a['image']['path'], b['image']['path'], api)['rgba_pixels_equal']
                                     for a, b in zip(old, observed))
                    report['restoration']['checks'].append(dict(variable=label, passed=passed, observed=observed))
                report['restoration']['success'] = bool(report['restoration']['checks']) and all(
                    row['passed'] for row in report['restoration']['checks'])
            except Exception as error:
                report['restoration'].update(error=str(error), traceback=traceback.format_exc())
        report['source_unchanged'] = api.sha256_file(c['source_project']['path']) == SOURCE_SHA
        report['working_copy_unchanged'] = working is not None and api.sha256_file(working['path']) == SOURCE_SHA
        report['success'] = bool(report.get('capture_complete') and not report.get('error') and report['restoration']['success']
                                 and report['source_unchanged'] and report['working_copy_unchanged'])
        checkpoint('diagnostic_captured_pending_root_comparison' if report['success'] else 'diagnostic_failed')
    summary = dict(success=report['success'], report_path=report_path, summary_path=summary_path,
                   restoration=report['restoration'], source_unchanged=report['source_unchanged'],
                   visual_acceptance='pending_root_comparison', error=report.get('error'))
    api.write_json(summary, summary_path)
    return summary
