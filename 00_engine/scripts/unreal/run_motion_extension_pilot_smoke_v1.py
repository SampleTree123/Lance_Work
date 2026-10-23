"""Root-run bounded 032 runtime smoke; external serial commands, no Slate loader.

Does not open a panel or save a map. Always attempts one verified old-baseline
reassembly after a known terminal outcome. An uncertain remote timeout stops
without racing an in-flight editor command. Technical owner: ANIMATION_EXPRESSION_MORPH section 9.
"""
from __future__ import annotations
import argparse
import copy
import json
from pathlib import Path
import time
import traceback

import motion_library_review_adapter_v1 as adapter
import run_cfd_native_batch40_modular_review_v1 as old_controller

RUN = adapter.extension.RUN / 'panel_pilot032'
SEXES = adapter.extension.SEXES
SELECTION_KEYS = ('character_ids', 'choices', 'appearance', 'action_index', 'playing')


def require(value, message):
    if not value:
        raise AssertionError(message)


def same_selection(actual, expected, keys=SELECTION_KEYS):
    require(all(actual[k] == expected[k] for k in keys), 'Selection changed unexpectedly: ' + ','.join(keys))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--node-id', required=True)
    parser.add_argument('--expected-pid', type=int, required=True)
    parser.add_argument('--output', type=Path, default=RUN / 'runtime_smoke01')
    args = parser.parse_args()
    out = args.output.resolve()
    if not out.is_relative_to(RUN.resolve()) or args.expected_pid <= 0:
        raise ValueError('Use a new output directory inside panel_pilot032 and a positive target PID')
    out.mkdir(parents=True, exist_ok=False)
    def write(name, value):
        with (out / name).open('x', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False, default=str)
            stream.write('\n')
    source = adapter.extension.source
    read = adapter.extension.read
    backup_path = RUN / 'current_case_before_pilot.json'
    backup_bytes = backup_path.read_bytes()
    backup_record = source(backup_path)
    baseline = read(RUN / 'baseline_request.json')
    require(baseline['action_index'] == 0 and not baseline['playing'] and not baseline['save'], 'Old baseline must be paused index0 without save')
    same_selection(read(backup_path)['request'], baseline)
    write('old_baseline_request.json', baseline)
    current = read(RUN / 'show_dance_request.json')
    require(current['action_index'] == 6 and not current['playing'] and not current['save'], 'Explicit displayed pilot index6 required')
    same_selection(current, baseline, ('character_ids', 'choices', 'appearance'))
    write('pilot_initial_request.json', current)
    motion_record, face_record = source(RUN / 'motion_catalog_v1.json'), source(RUN / 'face_overlay_v1.json')
    app = adapter.controller(motion_record, face_record)
    app.panel.COMMAND_TIMEOUT = 600
    old_controller.panel.COMMAND_TIMEOUT = 600
    locks = {name: source(path) for name, path in {
        'motion_catalog': RUN / 'motion_catalog_v1.json', 'face_overlay': RUN / 'face_overlay_v1.json',
        'base_face_registry': adapter.extension.faces.PANEL_REGISTRY,
        'base_active_pointer': adapter.extension.faces.ACTIVE_POINTER,
        'original_case_backup': backup_path,
        'saved_level': Path('D:/UE/projects/datatry_02/Content/DataMake/Validation/CFDNativeBatch4020261006/L_DM_CFDNativeBatch40_ModularReview_v001.umap')}.items()}
    events, replies, recovery = [], {}, []
    error, target_verified, unknown_remote_outcome = None, False, False
    data = None

    def execute(name, **updates):
        nonlocal current, unknown_remote_outcome
        request = dict(copy.deepcopy(current), action='show', save=False)
        request.update(updates)
        app.pin_face_registry(request, data)
        request = app.validate_request(request, data)
        started = time.perf_counter()
        try:
            result = app.panel.execute(request, args.node_id)
        except (TimeoutError, ConnectionError):
            unknown_remote_outcome = True
            raise
        elapsed = time.perf_counter() - started
        write(name + '.json', result)
        events.append({'step': name, 'success': True, 'elapsed_seconds': elapsed,
                       'report': source(out / (name + '.json'))})
        replies[name], current = result, request
        print(json.dumps({'step': name, 'success': True, 'elapsed_seconds': round(elapsed, 3)}), flush=True)
        return result

    def face(face_id):
        appearance = copy.deepcopy(current['appearance'])
        for sex in SEXES:
            appearance[sex]['face_id'] = face_id
        return appearance

    def loaded_probe(name, expected, mode='inspect'):
        nonlocal unknown_remote_outcome
        path = out / (name + '.json')
        # Use the known loaded actors directly. Never import/reload a worker,
        # create a new clip, or load any asset in this timing command.
        command = (
            'import os,json,unreal,time\nfrom pathlib import Path\n'
            f'assert os.getpid()=={args.expected_pid!r}\n'
            'actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()\n'
            f'expected={expected!r}\nrows={{}}\n'
            'for sex,expected_path in expected.items():\n'
            ' matches=[a for a in actors if a.get_actor_label()=="DM_CCWH_"+sex+"_Character"]\n'
            ' assert len(matches)==1,"Missing unique review actor"\n'
            ' components=[c for c in matches[0].get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name()=="Body"]\n'
            ' assert len(components)==1,"Missing unique Body"\n'
            ' body=components[0]\n'
            ' clip=body.get_editor_property("animation_data").get_editor_property("anim_to_play")\n'
            ' assert clip is not None and clip.get_path_name()==expected_path,"Loaded clip differs"\n'
            ' before=body.get_position()\n'
            f' mode={mode!r}\n'
            ' if mode=="restart":\n'
            '  body.set_position(0.,False)\n'
            '  body.get_anim_instance().set_playing(True)\n'
            ' elif mode=="pause":\n'
            '  body.get_anim_instance().set_playing(False)\n'
            ' rows[sex]={"animation":clip.get_path_name(),"duration_seconds":clip.get_play_length(),'
            '"before_position":before,"position":body.get_position(),"playing":body.is_playing(),'
            '"skeleton":clip.get_skeleton().get_path_name()}\n'
            f'with Path({str(path)!r}).open("x",encoding="utf-8") as stream:json.dump(rows,stream,indent=2)\n')
        started = time.perf_counter()
        try:
            with app.panel.command_lock():
                app.target.remote(command, out, name, node_id=args.node_id, timeout=60)
        except (TimeoutError, ConnectionError):
            unknown_remote_outcome = True
            raise
        value = read(path)
        events.append({'step': name, 'success': True, 'scope': 'already_loaded_component_probe',
                       'elapsed_seconds': time.perf_counter() - started, 'report': source(path)})
        return value

    try:
        preflight = ('import os,unreal\nfrom pathlib import Path\n'
            f'assert os.getpid()=={args.expected_pid!r},"Wrong UE PID"\n'
            'assert Path(unreal.Paths.project_dir()).resolve()==Path("D:/UE/projects/datatry_02").resolve()\n'
            'assert not hasattr(unreal,"_dm_native5_runtime_smoke_v1"),"Old diagnostic callback exists"\n'
            'print("Motion pilot synchronous target verified")\n')
        with app.panel.command_lock():
            app.target.remote(preflight, out, 'target_preflight', node_id=args.node_id, timeout=60)
        target_verified = True
        started = time.perf_counter()
        data = app.load_catalog()
        first_load = time.perf_counter() - started
        started = time.perf_counter()
        warm = app.load_catalog()
        warm_load = time.perf_counter() - started
        require(warm['sources'] == data['sources'], 'Cached source pins differ')
        write('catalog_timing.json', {'first_load_seconds': first_load, 'second_load_seconds': warm_load,
            'same_controller_instance': True, 'same_sources': True,
            'scope': 'controller_catalog_only_not_UE_switch_latency'})
        app.validate_request(current, data)
        require(all(len(data['actions_by_sex'][s]) == 6 for s in SEXES), 'This bounded smoke expects only one appended pair')

        # 1: Inspect the already-displayed new smile combination; never substitute
        # the old saved IDs as an implicit initial show.
        status = execute('01_pilot_status', action='status')
        require(all(r['face_id'] == 'smile' and r['playback']['duration_seconds'] == 5 for r in status['face_readback'].values()), 'Current smile selection differs')
        for sex in SEXES:
            require({r['face_id'] for r in app.identities.faces_for_action(data, sex, 6)} == {'none', *adapter.extension.faces.FACE_IDS}, 'New four-face choices incomplete')

        # 2: Original full-length BodyOnly, paused, with explicit direct path/rig check.
        result = execute('02_body_only', appearance=face('none'), playing=False)
        expected = {s: data['actions_by_sex'][s][5]['path'] for s in SEXES}
        require(all(result['animation'][s]['animation'] == expected[s] for s in SEXES), 'none did not restore the new BodyOnly asset')
        probe = loaded_probe('02_body_only_readback', expected)
        for sex in SEXES:
            require(not probe[sex]['playing'] and abs(probe[sex]['duration_seconds'] - data['actions_by_sex'][sex][5]['duration_seconds']) < 1e-6
                    and probe[sex]['skeleton'] == adapter.extension.faces.SKELETONS[sex], 'Original BodyOnly duration/rig/pause mismatch')

        # 3: Check the second expression and the new composite playback path.
        result = execute('03_sad_play', appearance=face('sad'), playing=True)
        expected = {s: result['animation'][s]['animation'] for s in SEXES}
        require(all(r['face_id'] == 'sad' and not r['looping'] for r in result['face_readback'].values()), 'Sad composite did not use one-shot playback')
        loaded_probe('03_restart_loaded', expected, 'restart')
        time.sleep(.35)
        paused = loaded_probe('03_pause_loaded', expected, 'pause')
        require(all(.01 < r['position'] < 5 and not r['playing'] and abs(r['duration_seconds'] - 5) < 1e-6 for r in paused.values()), 'Five-second composite did not advance/pause naturally')
        reply = execute('03_panel_pause', action='playback', playing=False)
        require(all(abs(reply['animation'][s]['position'] - paused[s]['position']) < 1e-4 and not reply['animation'][s]['playing'] for s in SEXES), 'Panel pause changed phase')
        reply = execute('03_panel_resume', action='playback', playing=True)
        require(all(abs(reply['animation'][s]['position'] - paused[s]['position']) < .2 for s in SEXES), 'Resume reset phase')
        time.sleep(5.2)
        reply = execute('03_end_hold', action='status', playing=True)
        require(all(r['completed_hold_last'] for r in reply['face_readback'].values()), 'Five-second end did not hold')
        reply = execute('03_replay', action='playback', playing=True)
        require(all(r['playing'] and r['position'] < .2 for r in reply['animation'].values()), 'Replay did not restart')

        # 4–6: Save one real verified result, disturb the selected motion/face,
        # and restore all original identity/appearance fields through new schema.
        config_path = out / 'saved_configuration.json'
        app.configurations.save_configuration(config_path, reply, data, app.validate_request)
        saved_request = copy.deepcopy(reply['request'])
        execute('04_config_disturbed', action_index=0, appearance=face('none'), playing=False)
        restored = app.configurations.load_configuration(config_path, data, app.validate_request)
        same_selection(restored, saved_request)
        result = execute('05_config_restored', **{k: restored[k] for k in SELECTION_KEYS})
        same_selection(result['request'], saved_request)
        switched = {'female': 'CFD40_LF_003', 'male': 'CFD40_WM_004'}
        result = execute('06_identity_switch', character_ids=switched, playing=False)
        require(result['request']['character_ids'] == switched, 'Requested identity switch did not apply')
        same_selection(result['request'], saved_request, ('choices', 'appearance', 'action_index'))

        # One exact old preset is migrated offline, with no extra UE asset load.
        old_data = old_controller.load_catalog()
        old_result = read(backup_path)
        require(old_result.get('success') is True, 'The real pre-pilot receipt was not successful')
        old_config = old_controller.configurations.build_configuration(old_result, old_data, old_controller.validate_request)
        old_path = out / 'old_configuration_from_actual_receipt.json'
        write(old_path.name, old_config)
        migrated = app.configurations.load_configuration(old_path, data, app.validate_request)
        same_selection(migrated, baseline)
        write('old_configuration_migration.json', {'success': True, 'scope': 'offline_exact_N3_configuration_migration',
            'original': source(old_path), 'migrated_request': migrated})
    except Exception:
        error = traceback.format_exc()
    finally:
        if target_verified and not unknown_remote_outcome:
            try:
                # Exactly one old-controller show. Restore backup bytes only once
                # successful assembly/readback confirms the original baseline.
                started = time.perf_counter()
                restored = old_controller.panel.execute(copy.deepcopy(baseline), args.node_id)
                same_selection(restored['request'], baseline)
                write('07_old_baseline_restored.json', restored)
                require(source(backup_path) == backup_record, 'Original current_case backup changed')
                destination = old_controller.identities.ROOT / 'current_case.json'
                before_restore = source(destination)
                temporary = destination.with_name('current_case.motion_pilot_restore.partial')
                with temporary.open('xb') as stream:
                    stream.write(backup_bytes)
                temporary.replace(destination)
                require(destination.read_bytes() == backup_bytes, 'current_case bytes did not restore')
                recovery.append({'success': True, 'elapsed_seconds': time.perf_counter() - started,
                    'report': source(out / '07_old_baseline_restored.json'), 'current_case_before_byte_restore': before_restore,
                    'current_case_restored': source(destination), 'backup': backup_record})
            except Exception:
                recovery.append({'success': False, 'error': traceback.format_exc()})
        else:
            recovery.append({'success': False, 'not_attempted': 'target_not_verified' if not target_verified else 'remote_outcome_unknown_requires_terminal_reconciliation'})
        try:
            after = {key: source(record['path']) for key, record in locks.items()}
        except Exception:
            after = {'error': traceback.format_exc()}
        success = error is None and all(r['success'] for r in recovery) and after == locks
        summary = {'success': success, 'error': error, 'events': events, 'recovery': recovery,
            'sources_before': locks, 'sources_after': after, 'sources_unchanged': after == locks,
            'expected_pid': args.expected_pid, 'node_id': args.node_id, 'unknown_remote_outcome': unknown_remote_outcome,
            'map_saved_or_reloaded': False, 'window_created': False, 'human_acceptance': 'pending',
            'asset_loading': 'external_serial_commands_no_slate_callback',
            'scope': 'one_new_paired_motion_smile_sad_bodyonly_config_identity_and_playback_not_all23_or_all40'}
        write('summary.json', summary)
        print(json.dumps({'success': success, 'report': str(out / 'summary.json')}, ensure_ascii=False), flush=True)
    if not success:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
