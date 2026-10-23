"""Recover the approved native smile and bake current production10 variants in UE."""
from pathlib import Path
import importlib.util
import json
import sys
import types
import unreal as u

W = Path('D:/UE/Lance_Work')
R = W / '00_engine/outputs/dataset_smile_20261023_v1'
S = W / '00_engine/scripts/unreal'
OLD = W / '00_engine/outputs/unreal_character_import/native_face_five_second_20261008_v1'
ROOT = '/Game/DataMake/Render/Expressions/SmileV1'
sys.path.insert(0, str(S))

def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))

def write(p, d):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def module(name):
    spec = importlib.util.spec_from_file_location('_smile_build_' + name, S / (name + '.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

def object_path(p):
    return p if '.' in p else p + '.' + p.rsplit('/', 1)[-1]

if u.get_editor_subsystem(u.MoviePipelineQueueSubsystem).is_rendering():
    raise RuntimeError('Render active')

import night_character_review_v1 as night
import ue_pair_revision_runtime_20261019_v1 as revision
import production_motion_contract_v1 as motion

members = night.configuration(revision)['members']
models = {sex: next(v for v in members.values() if v['character_id'].startswith('CFD40_' + initial))
          for sex, initial in [('female', 'AF'), ('male', 'AM')]}
rigs = {sex: row['skeleton'].split('.')[0] for sex, row in models.items()}
contract = motion.load_contract(verify_sources=False)
catalog = {'schema': 'dataset_smile_v1', 'face_id': 'smile',
           'source_window_seconds': [27, 32], 'video_playback': 'repeat_native_5s_without_retiming',
           'static_sample_seconds': 0.0, 'static': {}, 'motions': [],
           'policy': 'Approved native smile, includes native eye movements; body timing and nonfacial tracks preserved.'}
write(R / 'progress.json', {'phase': 'starting'})

for sex, prefix in [('female', 'hd_emote'), ('male', 'hd_emote_female')]:
    importer = module('ue_import_native_face_clip_v1')
    importer.RUN, importer.ASSET_ROOT, importer.SKELETONS = R, ROOT + '/Sources', rigs
    task = read(OLD / 'face_imports' / (sex + '_' + prefix + '_full_v1_task.json'))
    imported_report = R / ('import_' + sex + '.json')
    task['report_path'] = str(imported_report)
    imported = read(imported_report) if imported_report.exists() else importer.run(task)
    if not imported['success']:
        raise RuntimeError('Import failed: ' + sex)
    native = imported['animations'][0]['path']
    if not u.load_asset(native):
        raise RuntimeError('Native smile source missing: ' + native)

    path = S / 'ue_compose_native_face_body_v1.py'
    text = path.read_text(encoding='utf-8')
    old = "expected = '/Game/DataMake/Validation/CFDNativeBatch4020261006/SharedSkeletons/SKEL_CFDShared_' + sex.title() + '_v1'"
    assert text.count(old) == 1
    composer = types.ModuleType('_smile_current_rig_composer')
    composer.__file__ = str(path)
    composer.CURRENT_RIGS = rigs
    exec(compile(text.replace(old, 'expected = CURRENT_RIGS[sex]'), str(path), 'exec'), composer.__dict__)
    composer.RUN, composer.ASSET_ROOT = R, ROOT + '/Clips'
    original = read(OLD / 'compositions' / (sex + '_' + prefix + '_smile_native5_v1_task.json'))
    variants = [(row['motion_id'], object_path(row['variants'][sex]['production_destination']))
                for row in contract['motions']]
    static_task = dict(original, body_animation=variants[0][1], face_animation=native,
                       reference_mesh=models[sex]['base']['Body'], composite_id='smile_static_v1',
                       report_path=str(R / ('static_' + sex + '.json')))
    def compose(t):
        report_path = Path(t['report_path'])
        report = read(report_path) if report_path.exists() else composer.run(t)
        if not report['success'] or not u.load_asset(report['destination']):
            raise RuntimeError('Smile composition failed: ' + str(report_path))
        return object_path(report['destination'])
    static = compose(static_task)
    catalog['static'][sex] = {'animation': static, 'sample_seconds': 0.0}
    for mid, source in variants:
        write(R / 'progress.json', {'phase': 'composing', 'sex': sex, 'motion_id': mid,
                                    'completed_motions': len(catalog['motions'])})
        task = dict(static_task, composite_id='smile_' + mid.lower() + '_10s_v1',
                    body_animation=source, face_animation=static,
                    face_start_seconds=0.0, face_end_seconds=5.0, face_playback='loop',
                    body_mode='animation', static_use_reference_pose=False,
                    report_path=str(R / 'compositions' / (sex + '_' + mid + '.json')))
        Path(task['report_path']).parent.mkdir(parents=True, exist_ok=True)
        dest = compose(task)
        duration = float(u.load_asset(dest).get_play_length())
        if abs(duration - 10.0) > 0.00001:
            raise RuntimeError('Not production10: ' + dest)
        catalog['motions'].append({'sex': sex, 'motion_id': mid, 'source_animation': source,
                                   'animation': dest, 'duration_seconds': duration})
    write(R / 'catalog_partial.json', catalog)

write(W / '00_engine/assets/character_creator/dataset_smile_v1.json', catalog)
write(R / 'progress.json', {'phase': 'completed', 'static_clips': len(catalog['static']),
                           'motion_clips': len(catalog['motions'])})
print('SMILE_BUILD_COMPLETED', len(catalog['motions']))
