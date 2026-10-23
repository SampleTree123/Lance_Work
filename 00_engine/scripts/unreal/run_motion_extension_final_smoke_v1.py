"""Root-run serial final-catalog smoke; no map save, no window, no automatic run.

Start from a successful paused old-panel current_case. Any remote exception stops
all further UE commands; its outcome must be reconciled by the operator first.
Technical owner: ANIMATION_EXPRESSION_MORPH section 9.
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
from run_motion_extension_pilot_smoke_v1 import require, same_selection, SEXES, SELECTION_KEYS

CONFIG_KEYS = SELECTION_KEYS + ('framing', 'view', 'focus')


def assert_view(result, active):
    row = result.get('motion_review_view', {})
    require(row.get('success') is True, 'Panorama readback failed')
    require(row.get('fill_visible') is active, 'Auxiliary fill visibility differs')
    floor = row.get('floor', {})
    require(floor.get('success') is True and floor.get('visible') is active, 'Extended floor visibility differs')
    if active:
        require(row.get('framing') == adapter.panorama.FRAMING and row.get('fill_intensity') == 10., 'Panorama profile differs')
        require(floor.get('actual_mesh') == floor.get('source_mesh') and floor.get('actual_materials') == floor.get('source_materials'), 'Floor mesh/material binding differs')
        require(floor.get('collision_disabled') is True and floor.get('cast_shadow') is False, 'Floor flags differ')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--motion-catalog', type=Path, required=True)
    parser.add_argument('--face-overlay', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--action-index', type=int, default=6)
    parser.add_argument('--node-id', required=True)
    parser.add_argument('--expected-pid', type=int, required=True)
    args = parser.parse_args()
    out = args.output_dir.resolve()
    require(out.is_relative_to(adapter.extension.RUN.resolve()) and args.expected_pid > 0, 'Use a new output directory inside the motion expansion output and positive PID')
    require(args.action_index >= 6, 'Select one appended paired action, index6 or higher')
    out.mkdir(parents=True, exist_ok=False)
    source, read = adapter.extension.source, adapter.extension.read
    def write(name, value):
        with (out / name).open('x', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False, default=str)
            stream.write('\n')

    case_path = old_controller.identities.ROOT / 'current_case.json'
    original_bytes = case_path.read_bytes()
    receipt = json.loads(original_bytes)
    require(receipt.get('success') is True, 'Current case must be a real successful old-panel receipt')
    old_data = old_controller.load_catalog()
    baseline = copy.deepcopy(receipt['request'])
    require(baseline['action_index'] == 0 and not baseline['playing'] and baseline['framing'] != adapter.panorama.FRAMING,
        'Start from the paused old-panel index0 baseline and ordinary framing; arbitrary paused clip phase is not recoverable from current_case alone')
    baseline.update(action='show', save=False)
    baseline = old_controller.validate_request(baseline, old_data)
    (out / 'current_case_before_smoke.json').write_bytes(original_bytes)
    write('baseline_request.json', baseline)
    motion_record, face_record = source(args.motion_catalog), source(args.face_overlay)
    app = adapter.controller(motion_record, face_record)
    app.panel.COMMAND_TIMEOUT = old_controller.panel.COMMAND_TIMEOUT = 600
    locks = {name: source(path) for name, path in {
        'motion_catalog': args.motion_catalog, 'face_overlay': args.face_overlay,
        'base_face_registry': adapter.extension.faces.PANEL_REGISTRY,
        'base_active_pointer': adapter.extension.faces.ACTIVE_POINTER,
        'backup': out / 'current_case_before_smoke.json',
        'saved_level': Path('D:/UE/projects/datatry_02/Content/DataMake/Validation/CFDNativeBatch4020261006/L_DM_CFDNativeBatch40_ModularReview_v001.umap')}.items()}
    events, recovery = [], []
    current, data = None, None
    target_verified = mutated = unknown = False
    error = None

    def remote(call):
        nonlocal unknown
        unknown = True
        result = call()
        unknown = False  # Only a returned, controller-verified terminal result clears it.
        return result

    def execute(name, **updates):
        nonlocal current, mutated
        request = dict(copy.deepcopy(current), action='show', save=False)
        request.update(updates)
        app.pin_face_registry(request, data)
        request = app.validate_request(request, data)
        started = time.perf_counter()
        mutated = True
        result = remote(lambda: app.panel.execute(request, args.node_id))
        write(name + '.json', result)
        require(result.get('success') is True, 'Controller returned a failed result')
        current = request
        events.append({'step': name, 'elapsed_seconds': time.perf_counter()-started, 'report': source(out / (name+'.json'))})
        print(json.dumps({'step': name, 'success': True}), flush=True)
        return result

    try:
        preflight = ('import os,unreal\nfrom pathlib import Path\n'
            f'assert os.getpid()=={args.expected_pid!r},"Wrong UE PID"\n'
            'assert Path(unreal.Paths.project_dir()).resolve()==Path("D:/UE/projects/datatry_02").resolve()\n'
            'assert not hasattr(unreal,"_dm_native5_runtime_smoke_v1"),"Old diagnostic callback exists"\n'
            'print("Final extension smoke target verified")\n')
        with app.panel.command_lock():
            remote(lambda: app.target.remote(preflight, out, 'preflight', node_id=args.node_id, timeout=60))
        target_verified = True
        started = time.perf_counter()
        data = app.load_catalog()
        cold = time.perf_counter()-started
        started = time.perf_counter()
        cached = app.load_catalog()
        write('catalog_timing.json', {'first_load_seconds': cold, 'second_load_seconds': time.perf_counter()-started,
            'same_controller_instance': True, 'scope': 'catalog_validation_only_not_UI_latency'})
        require(cached['sources'] == data['sources'], 'Cached source pins changed')
        require(all(args.action_index <= len(data['actions_by_sex'][sex]) for sex in SEXES), 'Selected action pair absent')
        current = app.initial_request(data, baseline)
        current.update(action_index=args.action_index, playing=False, save=False, framing='full')
        for sex in SEXES:
            current['appearance'][sex]['face_id'] = 'smile'
        same_selection(current, baseline, ('character_ids', 'choices'))
        write('initial_request.json', current)

        shown = execute('01_pair_show')
        require(all(r['face_id'] == 'smile' and abs(r['playback']['duration_seconds']-5.) < 1e-6 for r in shown['face_readback'].values()), 'Expected validated five-second smile pair')
        played = execute('02_pair_play', action='playback', playing=True)
        require(all(r['playing'] or r.get('position', 0) >= 4.99 for r in played['animation'].values()), 'Playback did not begin')
        # Remote execution itself advances time. No retiming or direct component edits.
        paused = execute('03_pair_pause', action='playback', playing=False)
        require(all(not r['playing'] and 0. < r['position'] <= 5.001 for r in paused['animation'].values()), 'Playback did not advance and pause')
        panoramic = execute('04_panorama', action='view', framing=adapter.panorama.FRAMING)
        assert_view(panoramic, True)
        config_path = out / 'saved_configuration.json'
        app.configurations.save_configuration(config_path, panoramic, data, app.validate_request)
        saved = copy.deepcopy(panoramic['request'])
        ordinary = execute('05_ordinary', action='view', framing='full')
        assert_view(ordinary, False)
        restored = app.configurations.load_configuration(config_path, data, app.validate_request)
        same_selection(restored, saved, CONFIG_KEYS)
        reply = execute('06_configuration_restored', **{key: restored[key] for key in CONFIG_KEYS})
        same_selection(reply['request'], saved, CONFIG_KEYS)
        assert_view(reply, True)
    except Exception:
        error = traceback.format_exc()
    finally:
        if target_verified and mutated and not unknown:
            try:
                hidden = execute('07_hide_helpers', action='view', framing='full', playing=False)
                assert_view(hidden, False)
                restored = remote(lambda: old_controller.panel.execute(copy.deepcopy(baseline), args.node_id))
                require(restored.get('success') is True, 'Old baseline restore failed')
                same_selection(restored['request'], baseline, CONFIG_KEYS)
                write('08_old_baseline_restored.json', restored)
                require(source(out / 'current_case_before_smoke.json') == locks['backup'], 'Backup changed')
                with old_controller.panel.command_lock():
                    same_selection(read(case_path)['request'], baseline, CONFIG_KEYS)
                    temporary = case_path.with_name('current_case.final_motion_smoke_restore.partial')
                    with temporary.open('xb') as stream:
                        stream.write(original_bytes)
                    temporary.replace(case_path)
                require(case_path.read_bytes() == original_bytes, 'Current case bytes differ after restore')
                recovery.append({'success': True, 'helpers_hidden': True, 'original_case_bytes_restored': True})
            except Exception:
                recovery.append({'success': False, 'error': traceback.format_exc()})
        elif not mutated:
            recovery.append({'success': case_path.read_bytes() == original_bytes, 'scene_mutation_not_started': True})
        else:
            recovery.append({'success': False, 'not_attempted': 'remote_outcome_unknown_requires_operator_reconciliation'})
        try:
            after = {key: source(record['path']) for key, record in locks.items()}
        except Exception:
            after = {'error': traceback.format_exc()}
        success = error is None and not unknown and all(r['success'] for r in recovery) and after == locks
        write('summary.json', {'success': success, 'error': error, 'events': events, 'recovery': recovery,
            'sources_before': locks, 'sources_after': after, 'sources_unchanged': after == locks,
            'unknown_remote_outcome': unknown, 'node_id': args.node_id, 'expected_pid': args.expected_pid,
            'action_index': args.action_index, 'map_saved_or_reloaded': False, 'window_created': False,
            'human_acceptance': 'pending', 'scope': 'one_new_pair_playback_config_panorama_not_all_actions_or_identities'})
        print(json.dumps({'success': success, 'report': str(out/'summary.json')}, ensure_ascii=False), flush=True)
    if not success:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
