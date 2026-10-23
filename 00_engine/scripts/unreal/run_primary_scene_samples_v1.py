"""Root-only serial scene sample execution with durable intents and media reuse.

Importing is offline. Running the CLI dispatches UE work; root coordinates the
shared editor. Each site/orientation is encoded before the next bounded group.
"""
from pathlib import Path
import argparse
import json
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone

import run_all_motion_camera_review_v1 as base
from build_primary_scene_samples_v1 import RUN, ASSETS, INDEX, build_gallery, build_plans

S = Path(__file__).resolve().parent
PLAN_NAME = ''

IDLE_GUARD = '''survey=getattr(u,'_dm_all_primary_scene_survey_v1',None)
assert not isinstance(survey,dict) or survey.get('status')!='running','A UE primary-scene survey is active; wait before sample dispatch'
site_worker=getattr(u,'_dm_site_review_v1',None)
assert not isinstance(site_worker,dict) or (site_worker.get('job') or {}).get('status')!='running','A UE point checker is active; wait before sample dispatch'
queue=u.get_editor_subsystem(u.MoviePipelineQueueSubsystem)
assert not queue.is_rendering() and queue.get_active_executor() is None,'An MRQ executor is active; wait before sample dispatch'
'''


def release_owned_world(u):
    """Unload only a clean task-owned trial world; never a source/user map.

    Return from this remote command before prepare is sent, so engine/render
    threads can process deferred releases. Shared/referenced asset residency
    and prepare's internal source-to-copy peak are not certified resolved.
    """
    if Path(u.Paths.project_dir()).resolve()!=Path('D:/UE/projects/datatry_02').resolve():
        raise ValueError('Only the verified datatry_02 project may release an owned sample world')
    queue=u.get_editor_subsystem(u.MoviePipelineQueueSubsystem)
    if queue.is_rendering() or queue.get_active_executor() is not None:
        raise RuntimeError('MRQ is active; do not release its world')
    for key in ('_dm_all_primary_scene_survey_v1','_dm_site_review_v1','_dm_primary_saved_site_review_v1'):
        state=getattr(u,key,None) or {};job=state.get('job') or state
        if job.get('status')=='running':raise RuntimeError('A scene survey/check is active: '+key)
    dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    if dirty:raise RuntimeError('Unsaved packages; release refused: '+str([p.get_name() for p in dirty]))
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    before=editor.get_editor_world().get_path_name().split('.')[0]
    result={'schema':'primary_scene_owned_world_release_v1','before_map':before,'after_map':before,
            'mrq_idle':True,'dirty_packages':[],'source_assets_saved':False,
            'garbage_collection_requested':False,
            'limitation':'Owned editor-world unload only; no guarantee all shared or referenced GPU resources are freed.'}
    if not before.startswith(ASSETS+'/SceneTrials/'):
        return dict(result,status='skipped_already_entry' if before=='/Engine/Maps/Entry' else 'skipped_non_owned_world')
    u.LevelSequenceEditorBlueprintLibrary.close_level_sequence()
    if not u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Engine/Maps/Entry'):
        raise RuntimeError('Could not load Entry for owned-world release; prepare must not proceed')
    if editor.get_editor_world().get_path_name().split('.')[0]!='/Engine/Maps/Entry':
        raise RuntimeError('Owned-world release did not reach Entry')
    u.collect_garbage()
    return dict(result,status='released_to_entry',after_map='/Engine/Maps/Entry',garbage_collection_requested=True)


def _remote_once(code, label, run=RUN):
    folder = Path(run) / 'commands'
    folder.mkdir(parents=True, exist_ok=True)
    script = folder / (base.identifier(label) + '.py')
    script.write_text('import sys,json,importlib,unreal as u\nfrom pathlib import Path\nsys.path.insert(0,' + repr(str(S)) + ')\n'
        'import ue_primary_scene_samples_v1 as review\nimportlib.reload(review)\nreview.RUN=Path(' + repr(str(run)) + ')\n'
        'review.ASSETS=' + repr(ASSETS) + '\nreview.PLAN_NAME=' + repr(PLAN_NAME) + '\n' + IDLE_GUARD + code + '\n', encoding='utf-8')
    with script.with_suffix('.log').open('w', encoding='utf-8') as log:
        result = subprocess.run([sys.executable, '-X', 'utf8', str(S / 'ue_remote_exec.py'),
                                 '--project', 'datatry_02', '--script', str(script)], stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError('UE sample command failed; inspect ' + str(script.with_suffix('.log')))


def remote(code, label, run=RUN):
    if label.endswith('_prepare') and 'review.prepare(' in code:
        # Two separate remote executions, never load Entry and the next large
        # world inside the same editor Python callback.
        target=Path(run)/'resource_boundaries'/(base.identifier(label)+'.json')
        release_code=('import run_primary_scene_samples_v1 as owned_runner\n'
            'release_result=owned_runner.release_owned_world(u)\n'
            'release_path=Path('+repr(str(target))+')\n'
            'release_path.parent.mkdir(parents=True,exist_ok=True)\n'
            'release_path.write_text(json.dumps(release_result,ensure_ascii=False,indent=2),encoding="utf-8")\n'
            'print(json.dumps(release_result))')
        _remote_once(release_code,label+'_release',run)
        # This pause is in the external runner, never on the editor thread.
        # Let the editor tick/render thread process deferred releases before
        # the next separately connected prepare command requests a large map.
        time.sleep(.5)
    return _remote_once(code,label,run)


def stage_clear_sites(run=RUN, catalog_path=None, *, library=None):
    """Offline preparation only; root invokes execute separately after UE is idle."""
    from merge_primary_scene_surveys_v1 import merge_surveys
    run = Path(run).resolve()
    catalog_path = Path(catalog_path or run/'scene_samples_sites_v1.json').resolve()
    merged = merge_surveys(catalog_path, run=run)
    index = base.read(run/INDEX)
    eligible = []
    for site in index['sites']:
        summary = site.get('survey_summary', {})
        if (site.get('position') is not None and site.get('survey_status') == 'complete_for_selected_point'
                and summary.get('applies_to_current_site') is True
                and summary.get('full_matrix_sampled') is True
                and summary.get('matrix_combinations') == 1260
                and summary.get('no_proxy_conflict_combinations') == 1260
                and summary.get('suspected_conflict_combinations', 0) == 0):
            eligible.append(site['site_id'])
    if eligible:
        build_plans(catalog_path, run=run, site_ids=eligible, library=library)
    gallery = build_gallery(run)
    staged = base.read(run/INDEX)
    result = {'schema': 'primary_scene_clear_site_staging_v1', 'eligible_site_ids': eligible,
              'pending_site_ids': [s['site_id'] for s in staged['sites'] if s['site_id'] not in eligible],
              'eligible_plans': [s['sample_plan'] for s in staged['sites'] if s['site_id'] in eligible],
              'merge': merged, 'gallery': gallery, 'ue_dispatched': False,
              'policy': 'stage only source-pinned matching1260-clear sampled-proxy sites; root reviews remaining sites; no automatic exclusions',
              'root_next_step': 'execute(run, site_ids=eligible_site_ids, retire_raw=True) only after all UE survey/check/MRQ work is idle'}
    base.atomic_json(run/'clear_sites_staging_v1.json', result)
    return result


def _record_site_failure(run, site, attempt, path, digest, error):
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')
    target = run/'sample_failures'/(site['site_id'] + '_' + stamp + '.json')
    base.atomic_json(target, {'schema': 'primary_scene_sample_site_failure_v1',
        'site_id': site['site_id'], 'revision': site.get('revision', 'v1'), 'attempt': attempt,
        'plan': {'path': str(path), 'sha256': digest}, 'error': error,
        'traceback': traceback.format_exc(), 'policy': 'STOP; root must inspect durable intents, receipts and partial assets before deciding recovery; never blindly resubmit'})
    try:
        with (run/'STOP').open('x', encoding='utf-8') as stop:
            stop.write('Sample site failed; inspect ' + str(target) + '\n')
    except FileExistsError:
        pass
    return target


def execute(run=RUN, site_ids=None, *, retire_raw=False, gallery_every_scenes=1):
    global PLAN_NAME
    if type(gallery_every_scenes) is not int or gallery_every_scenes<1:
        raise ValueError('gallery_every_scenes must be a positive integer')
    run = Path(run).resolve()
    if not run.is_relative_to(S.parents[1] / 'outputs'):
        raise ValueError('Sample output must stay in the explicit project outputs')
    index = base.read(run / INDEX)
    if site_ids is not None and not site_ids:
        return dict(build_gallery(run), no_site_dispatch_requested=True)
    known = {s['site_id'] for s in index['sites']}
    if site_ids and not set(site_ids).issubset(known):
        raise ValueError('Unknown selected primary site')
    base.RUN, base.remote = run, remote
    gallery = None
    pending_gallery_sites = 0
    with base.run_lock(run):
        for site in index['sites']:
            if (run / 'STOP').exists():
                raise RuntimeError('STOP marker; no further UE sample dispatch')
            if site_ids and site['site_id'] not in site_ids or not site['sample_plan']:
                continue
            PLAN_NAME = site['sample_plan']['path']
            base.PLAN_NAME = PLAN_NAME
            path = run / PLAN_NAME
            digest = base.sha(path)
            if digest != site['sample_plan']['sha256']:
                raise ValueError('Scene plan changed since index creation')
            shots = {s['shot_id']: s for s in base.read(path)['shots']}
            done = base.verified_rows(shots, run)
            site_updated = False
            for orientation in ('landscape', 'portrait'):
                if (run / 'STOP').exists():
                    raise RuntimeError('STOP marker; no further UE sample dispatch')
                group = [s for s in shots.values() if s['orientation'] == orientation]
                if not group:
                    continue
                attempt = 'ps_' + base.object_sha([site['site_id'], site.get('revision', 'v1'), orientation])[:12] + '_' + digest[:8]
                try:
                    report = (None if all(s['shot_id'] in done for s in group) else
                              base.complete_batch(attempt, group, done, path, digest, run))
                except Exception as exc:
                    failure = _record_site_failure(run, site, attempt, path, digest, str(exc))
                    raise RuntimeError('Scene sample failed; STOP recorded for root inspection: ' + str(failure)) from exc
                if report:
                    done.update({r['shot_id']: r for r in report['videos']})
                    site_updated = True
                    if retire_raw:
                        base.retire_verified_raw(attempt, report, shots, run, fresh_process=True)
                base.atomic_json(run / 'scene_sample_progress_v1.json', {'site_id': site['site_id'],
                    'verified_site_samples': len(done), 'target_site_samples': len(shots), 'last_attempt': attempt})
                print(f'{site["site_id"]}: {len(done)}/{len(shots)} samples verified', flush=True)
            # Keep complete gallery validation; only batch its refresh cadence.
            if site_updated:
                pending_gallery_sites += 1
                if pending_gallery_sites >= gallery_every_scenes:
                    gallery = build_gallery(run)
                    pending_gallery_sites = 0
    # Flush the tail; a reuse-only run still validates the full final gallery.
    return build_gallery(run) if pending_gallery_sites or gallery is None else gallery


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-root', type=Path, default=RUN)
    parser.add_argument('--site-ids', nargs='*')
    parser.add_argument('--retire-verified-raw', action='store_true')
    parser.add_argument('--gallery-every-scenes',type=int,default=1,
                        help='refresh the fully validated gallery after N scenes with newly verified videos (default1); always flush the final tail')
    parser.add_argument('--stage-clear-sites', action='store_true', help='offline merge/plan/gallery only; do not dispatch UE')
    parser.add_argument('--catalog', type=Path)
    args = parser.parse_args()
    result = stage_clear_sites(args.run_root, args.catalog) if args.stage_clear_sites else execute(args.run_root, args.site_ids, retire_raw=args.retire_verified_raw,gallery_every_scenes=args.gallery_every_scenes)
    print(json.dumps(result, ensure_ascii=False))
