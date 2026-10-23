"""AF002-only transient native-lash isolation: two front images, then reload.

One texture write to the original Body/Std_Eyelash opacity. No source save,
mesh replacement, SkinGen activation, asset application or visual acceptance.
"""
import os
import shutil
import sys
import traceback

SOURCE_SHA = '1b16d42a254bcccf769a5c93560b0e4f4749a7aef076fc10b117c057de0a0f15'
MODE = 'af002_native_lash_opacity_diagnostic'
KEY = ('avatar', 'CC_Base_Body', 'Std_Eyelash')


def validate_config(config, api):
    if (config.get('character_id') != 'CFD40_AF_002' or config.get('working_subdivision_level') != 0
            or config.get('operation') != 'two_neutral_front_images_native_opacity_only_then_reload'
            or config.get('save_current_scene_backup') is not True
            or config['source_project']['sha256'] != SOURCE_SHA):
        raise ValueError('Only exact AF002 final source, SubD0 and transient operation allowed')
    for key in ('source_project', 'black_opacity', 'camera', 'light', 'selected_lash_report'):
        record = config[key]
        if api.sha256_file(record['path']) != record['sha256']:
            raise ValueError('Pinned diagnostic input changed: ' + key)
    if config['black_opacity'].get('width') != 512 or config['black_opacity'].get('height') != 512:
        raise ValueError('Actual native opacity dimensions must be retained')


def run(library, output_dir, log, api):
    if os.path.dirname(__file__) not in sys.path:
        sys.path.insert(0, os.path.dirname(__file__))
    import cc_refresh_visual_probe_v1 as visual
    import cc_repair_headshot_support_materials_v1 as geometry
    config = library['af002_native_lash_opacity_diagnostic']
    validate_config(config, api)
    if not visual.inside(output_dir, visual.RUN_ROOT):
        raise ValueError('Independent refresh artifact output required')
    source = config['source_project']
    lash = api.read_json(config['selected_lash_report']['path'])
    if lash.get('success') is not True or lash['saved_project']['sha256'] != SOURCE_SHA:
        raise ValueError('Actual own successful selected-lash final is required')
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, 'native_lash_opacity_diagnostic_report.json')
    summary_path = os.path.join(output_dir, 'validation_result.json')
    report = dict(character_id='CFD40_AF_002', diagnostic_mode=MODE, success=False,
                  source_project=source, captures=[], opacity_readbacks={},
                  implementation_sha256=api.sha256_file(__file__), report_path=path,
                  summary_path=summary_path, changed_texture_key=list(KEY) + ['opacity'],
                  accepted_final=False, recipe_complete=False, diagnosis='pending_root_image_comparison',
                  working_subdivision_level=0, render_subdivision_verified=False)
    R = api.RLPy
    working = None
    attempted = False
    original_opacity = None

    def checkpoint(phase):
        report['phase'] = phase
        api.write_json(report, path)
        log('AF002 native lash opacity diagnostic: ' + phase)

    def avatar():
        rows = list(R.RScene.GetAvatars() or [])
        if len(rows) != 1 or int(rows[0].GetSubdivMeshLevel()) != 0:
            raise ValueError('One actual SubD0 avatar required; no subdivision switching')
        return rows[0]

    def load(record, label):
        if api.sha256_file(record['path']) != record['sha256']:
            raise ValueError('Independent load source pin changed')
        status, dialogs = api.load_file_with_optional_undo_warning(record['path'], label)
        report.setdefault('loads', []).append(dict(label=label, status=status, dialogs=dialogs, source=record))
        current = avatar()
        R.RScene.SelectObject(current)
        api.force_avatar_scene_evaluation(current)
        return current

    def capture_opacity(current, label):
        image = current.GetMaterialComponent().GetImage('CC_Base_Body', 'Std_Eyelash', R.EMaterialTextureChannel_Opacity)
        if image is None or image.GetWidth() != 512 or image.GetHeight() != 512:
            raise ValueError('Real 512x512 native opacity readback required')
        image_path = os.path.join(output_dir, label + '_native_opacity.png')
        api.checked('Save native opacity readback only', image.SaveFile(image_path))
        record = api.bodyfit_freeze_file_record(image_path)
        report['opacity_readbacks'][label] = record
        return record

    def image_record(label, current, face, names, time_value):
        if int(current.GetSubdivMeshLevel()) != 0:
            raise ValueError('Working subdivision changed')
        image_path = os.path.join(output_dir, label + '.png')
        api.render_preview(image_path, time_value)
        width, height = visual.png_dimensions(image_path)
        decoded = api.QtGui.QImage(image_path)
        if decoded.isNull() or (decoded.width(), decoded.height()) != (width, height):
            raise ValueError('Actual diagnostic PNG decode failed')
        expression = visual.expression_readback(face, time_value, names, {})
        if not expression['passed']:
            raise ValueError('Neutral expression readback changed')
        report['captures'].append(dict(label=label, pose='neutral', view='front', yaw_degrees=90,
            working_subdivision_level=0, expression_readback=expression,
            image=dict(api.bodyfit_freeze_file_record(image_path), width=width, height=height, image_decoded=True)))

    try:
        checkpoint('backup_then_load_independent_final')
        backup = os.path.join(output_dir, 'scene_before_diagnostic.ccProject')
        api.checked('Save independent scene backup', R.RFileIO.SaveProject(backup))
        report['scene_backup'] = api.bodyfit_freeze_file_record(backup)
        working_path = os.path.join(output_dir, 'AF002_final_diagnostic_copy.ccProject')
        shutil.copyfile(source['path'], working_path)
        working = api.bodyfit_freeze_file_record(working_path)
        report['working_source'] = working
        attempted = True
        current = load(working, 'Load AF002 diagnostic final copy')
        original_opacity = capture_opacity(current, 'original')
        for key in ('light', 'camera'):
            api.checked('Load verified existing ' + key, R.RFileIO.LoadFile(config[key]['path']))
        face = current.GetFaceComponent()
        names = list(face.GetExpressionNames('') or [])
        _, direct, _ = visual.direct_blink_pose(names)
        time_value = R.RGlobal.GetStartTime()
        api.checked('Begin neutral expression', face.BeginKeyEditing())
        try:
            api.checked('Set neutral direct expression', face.AddExpressionKeys(
                time_value, direct, [0.] * len(direct), R.IndexedFrameTime(0, R.RGlobal.GetFps())))
        finally:
            api.checked('End neutral expression', face.EndKeyEditing())
        api.checked('Evaluate neutral expression', R.RGlobal.SetTime(time_value, True))
        api.set_avatar_position(current, -80., 8., 12.)
        api.set_avatar_yaw(current, 90.)
        api.force_avatar_scene_evaluation(current)
        checkpoint('original_neutral_front')
        image_record('original_neutral_front', current, face, names, time_value)
        checkpoint('only_native_opacity_write')
        component = current.GetMaterialComponent()
        black = api.QtGui.QImage(config['black_opacity']['path'])
        if black.isNull() or (black.width(), black.height()) != (512, 512):
            raise ValueError('Prepared opacity PNG decode failed')
        for y in range(512):
            for x in range(512):
                color = black.pixelColor(x, y)
                if color.red() or color.green() or color.blue():
                    raise ValueError('Diagnostic opacity must be entirely black')
        api.checked('Temporarily isolate native Std_Eyelash only', component.LoadImageToTexture(
            'CC_Base_Body', 'Std_Eyelash', R.EMaterialTextureChannel_Opacity, config['black_opacity']['path']))
        report['write'] = dict(mesh='CC_Base_Body', material='Std_Eyelash',
            channel='EMaterialTextureChannel_Opacity', image=config['black_opacity'])
        api.force_avatar_scene_evaluation(current)
        image_record('native_opacity_black_neutral_front', current, face, names, time_value)
        readback = capture_opacity(current, 'black')
        opacity_check = geometry.compare_png_images(config['black_opacity']['path'], readback['path'], api)
        report['black_opacity_pixels_verified'] = opacity_check
        if not opacity_check['rgba_pixels_equal']:
            raise ValueError('Black native opacity readback failed')
        report['capture_complete'] = len(report['captures']) == 2
    except Exception as error:
        report['error'] = dict(type=type(error).__name__, message=str(error), traceback=traceback.format_exc())
    finally:
        report['restoration'] = dict(attempted=attempted, success=False)
        if attempted and working is not None:
            try:
                checkpoint('restore_unchanged_independent_final')
                restored = load(working, 'Reload AF002 final copy; discard temporary opacity and framing')
                restored_opacity = capture_opacity(restored, 'restored')
                check = geometry.compare_png_images(original_opacity['path'], restored_opacity['path'], api)
                report['restoration'].update(success=check['rgba_pixels_equal'],
                    native_opacity=check, source=working, working_subdivision_level=0)
            except Exception as error:
                report['restoration'].update(error=str(error), traceback=traceback.format_exc())
        report['source_unchanged'] = api.sha256_file(source['path']) == SOURCE_SHA
        report['working_copy_unchanged'] = working is not None and api.sha256_file(working['path']) == SOURCE_SHA
        report['success'] = bool(report.get('capture_complete') and not report.get('error')
                                 and report['restoration']['success'] and report['source_unchanged'] and report['working_copy_unchanged'])
        checkpoint('diagnostic_captured_pending_root_review' if report['success'] else 'diagnostic_failed')
    summary = dict(success=report['success'], report_path=path, summary_path=summary_path,
                   restoration=report['restoration'], source_unchanged=report['source_unchanged'],
                   diagnosis='pending_root_image_comparison', error=report.get('error'))
    api.write_json(summary, summary_path)
    return summary
