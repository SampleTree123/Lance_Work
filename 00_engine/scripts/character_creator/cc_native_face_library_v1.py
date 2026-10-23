"""Read native installed face performances on an isolated character copy.

The bridge dispatch is typed and source-hash bound. No authored expression keys,
source asset writes, profile changes, or neutral calibration replacement.
"""
import os
import traceback

ROOT = r'D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\native_face_library_20261007_v1'
FIVE_SECOND_EXPERIMENT_ID = 'native_face_five_second_20261008_v1'
FIVE_SECOND_ROOT = os.path.join(os.path.dirname(ROOT), FIVE_SECOND_EXPERIMENT_ID)
TEMPLATES = r'D:\CharacterCreator_sucai\Reallusion Templates\Animation'
PROJECT_COPIES = os.path.join(os.path.dirname(__file__), 'runtime_staging', 'native_face_library_20261007_v1', 'source_copies')


def validated_output_directory(request, output_dir):
    """An explicit allowlisted experiment selects only its separate output root."""
    root = ROOT
    if 'experiment_id' in request:
        if request['experiment_id'] != FIVE_SECOND_EXPERIMENT_ID:
            raise ValueError('Unrecognized native face experiment_id')
        root = FIVE_SECOND_ROOT
    output_dir = os.path.realpath(output_dir)
    if os.path.commonpath([root, output_dir]) != root:
        raise ValueError('Native face output must stay in its experiment root')
    return output_dir


def run(library, output_dir, log, api):
    R = api.RLPy
    request = library['native_face_library']
    output_dir = validated_output_directory(request, output_dir)
    if request.get('operation') not in ('inspect', 'inspect_export'):
        raise ValueError('Expected native face inspection or export')
    source, performance = request['project_copy'], request['performance']
    for record, root in ((source, PROJECT_COPIES), (performance, TEMPLATES)):
        path = os.path.realpath(record['path'])
        if os.path.commonpath([root, path]) != root or api.sha256_file(path) != record['sha256']:
            raise ValueError('Unrecognized or changed native performance source')
    if not performance['path'].lower().endswith(('.italk', '.imotionplus')):
        raise ValueError('Expected installed face or motion-plus performance')
    report = {'success': False, 'project_copy': source, 'performance': performance,
              'authored_expression_keys': False, 'phase': 'loading_copy'}
    report_path = os.path.join(output_dir, 'native_face_inspection.json')
    def phase(value):
        report['phase'] = value
        api.write_json(report, report_path)
        log('Native face: ' + value)
    try:
        phase('loading_copy')
        api.checked('Load isolated native face character', R.RFileIO.LoadFile(source['path']))
        avatars = list(R.RScene.GetAvatars() or [])
        if len(avatars) != 1:
            raise ValueError('Expected one isolated face probe avatar')
        avatar = avatars[0]
        R.RScene.SelectObject(avatar)
        face, skeleton = avatar.GetFaceComponent(), avatar.GetSkeletonComponent()
        fps = R.RGlobal.GetFps()
        api.checked('Rewind source copy', R.RGlobal.SetTime(R.IndexedFrameTime(0, fps), True))
        report['face_methods'] = [name for name in dir(face) if name.startswith(('Get', 'Is'))]
        report['profile_uid'] = str(face.GetExpressionSetUid())
        report['before_clip_count'] = int(face.GetClipCount())
        # The saved creation copy may contain calibration clips. Remove them
        # only from the in-memory independent copy, before loading the native
        # performance. No replacement keys are authored and no project saved.
        report['cleared_source_clips'] = {}
        for label, component in (('face', face), ('skeleton', skeleton)):
            report['cleared_source_clips'][label] = int(component.GetClipCount())
            for index in range(int(component.GetClipCount()) - 1, -1, -1):
                api.checked('Clear copy calibration clip', component.DeleteClip(component.GetClip(index)))
        names = list(face.GetExpressionNames('') or [])
        report['expression_names'] = names
        phase('loading_native_performance')
        api.checked('Load installed native performance', R.RFileIO.LoadFile(performance['path']))
        api.QtWidgets.QApplication.processEvents()
        report['current_pose_mode'] = bool(face.IsCurrentPoseMode())
        report['clips'] = []
        for label, component in (('face', face), ('skeleton', skeleton)):
            for index in range(int(component.GetClipCount())):
                clip = component.GetClip(index)
                entry = {'component': label, 'index': index,
                         'type': str(clip.GetType()),
                         'length_ticks': int(clip.GetLength().ToInt64()),
                         'length_frames': int(fps.GetFrameIndex(clip.GetLength())),
                         'methods': [n for n in dir(clip) if n.startswith('Get')]}
                report['clips'].append(entry)
        face_lengths = [r['length_frames'] for r in report['clips'] if r['component'] == 'face']
        if not face_lengths or max(face_lengths) <= 0:
            raise ValueError('Installed performance has no nonempty facial clip')
        length = max(face_lengths)
        report['profile_uid_after_load'] = str(face.GetExpressionSetUid())
        frames = sorted(set([0, min(1, length)] + [round(length*i/12) for i in range(1, 13)]))
        report['samples'] = []
        report['duration_seconds'] = float(R.RTick.ToSecond(R.IndexedFrameTime(length, fps).ToInt64()))
        phase('sampling_native_performance')
        for frame in frames:
            t = R.IndexedFrameTime(frame, fps)
            api.checked('Evaluate native face', R.RGlobal.SetTime(t, True))
            api.QtWidgets.QApplication.processEvents()
            report['samples'].append({'frame': frame, 'ticks': int(t.ToInt64()),
                'weights': dict(zip(names, api.expression_weights_at(face, t, names))),
                'expressiveness': float(face.GetExpressiveness(t)),
                'bones': [{'name': b.GetName(), 'local': api._transform_data(b.LocalTransform()),
                           'world': api._transform_data(b.WorldTransform())} for b in skeleton.GetSkinBones()]})
        api.checked('Rewind native face for preview', R.RGlobal.SetTime(R.IndexedFrameTime(0, fps), True))
        if request['operation'] == 'inspect_export':
            phase('exporting_native_performance')
            report['export'] = export_native(R, api, avatar, fps, length, output_dir)
        for record in (source, performance):
            if api.sha256_file(record['path']) != record['sha256']:
                raise ValueError('Native performance source unexpectedly changed')
        report['source_unchanged'] = True
        report['success'] = True
        phase('complete')
    except Exception:
        report['error'] = traceback.format_exc()
        phase('failed')
        raise
    result = {'success': True, 'report_path': report_path}
    result['summary_path'] = os.path.join(output_dir, 'validation_result.json')
    api.write_json(result, result['summary_path'])
    return result


def export_native(R, api, avatar, fps, length, output_dir):
    """Export the loaded native performance without authoring expression keys."""
    fbx = os.path.join(output_dir, 'native_face.fbx')
    if os.path.exists(fbx):
        raise ValueError('Refusing to overwrite face export')
    api.checked('Native export start', R.RGlobal.SetStartTime(R.IndexedFrameTime(0, fps)))
    api.checked('Native export end', R.RGlobal.SetEndTime(R.IndexedFrameTime(length, fps)))
    api.checked('Native export license', R.RFileIO.CheckExportFbxHasLicense(avatar))
    setting = R.RExportFbxSetting()
    opt = R.EExportFbxOptions__None | R.EExportFbxOptions_AutoSkinRigidMesh | R.EExportFbxOptions_ExportRootMotion
    opt2 = R.EExportFbxOptions2__None
    for name in ('UnrealEngine4BoneAxis', 'UnrealPreset', 'UnrealIkBone',
                 'RenameDuplicateBoneName', 'RenameDuplicateMaterialName', 'RenameDuplicateMorphName',
                 'RenameTransparencyWithPostFix', 'RenameBoneRootToGameType', 'RenameBoneToLowerCase',
                 'RenameBoneOnStd', 'RenameMorphInvalidCharacter', 'ResetBoneScale',
                 'ResetSelfillumination', 'ExtraWordForUnityAndUnreal'):
        opt2 |= getattr(R, 'EExportFbxOptions2_' + name)
    for label, status in (
        ('motion', setting.EnableExportMotion(True)),
        ('fps', setting.SetExportMotionFps(fps)),
        ('range', setting.SetExportMotionRange(R.RRangePair(0, length))),
        ('options', setting.SetOption(opt)), ('Unreal options', setting.SetOption2(opt2)),
        ('JSON', setting.SetOption3(R.EExportFbxOptions3_ExportJson)),
        ('texture size', setting.SetTextureSize(R.EExportTextureSize_Original)),
        ('texture format', setting.SetTextureFormat(R.EExportTextureFormat_Default)),
        ('UE5 bones', setting.SetUnrealBoneStructure(R.EUnrealBoneStructure_UE5_BoneStructure)),
        ('bind pose', setting.EnableBasicBindPose(False)),
        ('subdivision', setting.EnableBakeSubdivision(False)),
    ):
        api.checked('Native export ' + label, status)
    api.checked('Export native face FBX', R.RFileIO.ExportFbxFile(avatar, fbx, setting))
    if not os.path.isfile(fbx) or os.path.getsize(fbx) <= 0:
        raise RuntimeError('Native face export did not produce an FBX')
    return {'path': fbx, 'sha256': api.sha256_file(fbx), 'bytes': os.path.getsize(fbx),
            'start_frame': 0, 'end_frame': length, 'mesh_mode': 'full_reference',
            'authored_expression_keys': False}
