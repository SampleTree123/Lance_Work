"""Offline survey-to-sample catalog merge; root choices and frozen plans stay intact."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

from build_primary_scene_samples_v1 import RUN, INDEX, read, write, sha, object_sha, render_definition


DUAL_POLICY = {'id': 'survey_collision_proxy_and_raw_appearance_v3',
    'excluded_actual_class': 'GrassInstancedStaticMeshComponent',
    'required_collision': '<CollisionEnabled.NO_COLLISION: 0>',
    'required_visibility_response': '<CollisionResponseType.ECR_IGNORE: 0>',
    'all_actor_fields_dirty_packages_and_other_components_preserved': True,
    'raw_scene_unchanged_claim': False, 'rendered_grass_visibility_review_required': True,
    'other_particles_or_collisionless_components_excluded': False}


def _canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()


def _uses_dual(report):
    return any(Path(p['path']).name == 'ue_primary_scene_survey_dual_v3.py'
               or 'dual_signature_bindings' in Path(p['path']).parts for p in report.get('source_pins', []))


def _validate_ground(document, base, run, cache):
    """Bind the optional ground-only query adaptation to this fresh1260 attempt."""
    fields = ('ground_query_policy', 'ground_query_evidence', 'ground_adapter_source')
    has_source = any(Path(p['path']).name == 'ue_primary_scene_ground_objects_v1.py'
                     for p in document['source_pins'])
    if not has_source and not any(k in document for k in fields):
        return
    if not all(k in document for k in fields):
        raise ValueError('Object-ground survey lacks its complete ground receipt chain')
    policy = document['ground_query_policy']
    simple = policy.get('id') == 'targeted_object_type_ground_simple_v2'
    required = {'id': 'targeted_object_type_ground_simple_v2' if simple else 'targeted_object_type_ground_v1',
        'ground_domains': ['anchor_and_nine_probes', 'screen_ground_probes', 'full_action_ground_probes'],
        'trace_complex': not simple, 'body_standing_camera_occlusion': 'original Visibility logic unchanged',
        'flat_region_tolerance_cm': 3., 'standing_probe_radius_cm': 80., 'ground_probe_count': 9,
        'full_action_ground_height_tolerance_cm': 5., 'full_matrix_combinations': 1260}
    if any(policy.get(k) != v for k, v in required.items()):
        raise ValueError('Ground-only policy or original1260 thresholds changed')
    evidence_pin, source_pin = document['ground_query_evidence'], document['ground_adapter_source']
    expected_source = 'ue_primary_scene_ground_simple_v2.py' if simple else 'ue_primary_scene_ground_objects_v1.py'
    if Path(source_pin['path']).name != expected_source:
        raise ValueError('Ground policy is not bound to its explicit version adapter')
    Path(evidence_pin['path']).resolve().relative_to(run)
    _verify_pins([evidence_pin, source_pin], cache)
    receipt = read(evidence_pin['path'])
    binding_pin = receipt['binding']
    Path(binding_pin['path']).resolve().relative_to(run)
    _verify_pins([binding_pin], cache)
    binding = read(binding_pin['path'])
    for row, schema in [(receipt, 'primary_scene_object_ground_evidence_v1'),
                        (binding, 'primary_scene_object_ground_binding_v1')]:
        if (row.get('schema') != schema or row.get('attempt_id') != base['attempt_id']
                or row.get('map') != base['map'] or row.get('ground_query_policy') != policy
                or row.get('adapter_source') != source_pin):
            raise ValueError('Ground evidence source/attempt/map/policy differs from the survey')
    if (receipt.get('status') != 'complete' or receipt.get('base_report') != document['base_report']
            or receipt.get('target_components') != binding.get('target_components')
            or any(receipt.get(k) is not False for k in ('body_camera_occlusion_and_standing_changed',
                'original_thresholds_and_full1260_changed', 'old_reports_requalified'))):
        raise ValueError('Ground receipt does not preserve the fresh base and original body/camera checks')
    targets = receipt['target_components']
    paths = [t['component_path'] for t in targets]
    dynamic = any(t['is_world_dynamic'] for t in targets)
    if (not paths or len(set(paths)) != len(paths) or sorted(paths) != sorted(policy.get('target_component_paths', []))
            or policy.get('object_types') != ['WorldStatic']+(['WorldDynamic'] if dynamic else [])
            or policy.get('dynamic_enabled_only_from_named_actual_target_type') is not dynamic):
        raise ValueError('Named ground targets differ from the object-query policy')
    _verify_pins([*binding['frozen_sources'], *binding['local_api_sources']], cache)
    source_keys = {(str(Path(p['path']).resolve()), p['sha256']) for p in document['source_pins']}
    if any((str(Path(p['path']).resolve()), p['sha256']) not in source_keys
           for p in [evidence_pin, binding_pin, source_pin, *binding['local_api_sources'], *binding['frozen_sources']]):
        raise ValueError('Ground binding/API/frozen sources are absent from the survey pins')
    statistics = receipt['query_statistics']
    counts = receipt['queries']['trace_count_by_domain']
    if (any(not isinstance(statistics.get(k), int) or statistics[k] <= 0 or statistics[k] != counts.get(k)
            for k in ('anchor', 'nine_probes', 'screen_ground', 'full_ground'))
            or statistics['nine_probes'] != 9*statistics['anchor']
            or statistics.get('body_camera_visibility_unchanged') is not True
            or statistics.get('standing_visibility_unchanged') is not True
            or receipt.get('ground_candidates') != base.get('ground_candidates')):
        raise ValueError('Ground domains were not measured with unchanged body/camera Visibility')
    candidate = base['full_attempts'][base['selected_full_attempt_index']]['candidate']
    if not any(g.get('eligible') is True and g.get('support_hit', {}).get('component_path') in paths
               and len(g.get('position', [])) == 3 and math.dist(g['position'], candidate['position']) <= 1e-6
               for g in base['ground_candidates']):
        raise ValueError('Selected point lacks measured intended ground support')
    if simple:
        diagnostic_pin, base_pin = policy['diagnostic_evidence'], policy['base_adapter_source']
        Path(diagnostic_pin['path']).resolve().relative_to(run)
        if (len(targets) != 1 or Path(base_pin['path']).name != 'ue_primary_scene_ground_objects_v1.py'
                or not isinstance(policy.get('simple_collision_surface_limitation'), str)
                or not policy['simple_collision_surface_limitation'].strip()):
            raise ValueError('Simple ground lacks its exact target/base adapter/visual limitation')
        _verify_pins([diagnostic_pin, base_pin], cache)
        if any((str(Path(p['path']).resolve()), p['sha256']) not in source_keys for p in [diagnostic_pin, base_pin]):
            raise ValueError('Simple diagnostic and unchanged complex adapter must remain pinned')
        # Reuse the frozen simple entry's read-only same-XY/flat-hit/complex-miss
        # gate. Importing this module is stdlib-only; no UE loading is invoked.
        from ue_primary_scene_ground_simple_v2 import _diagnostic
        _, diagnostic = _diagnostic(diagnostic_pin, candidate['position'], paths[0])
        if not targets[0].get('static_mesh') or targets[0]['static_mesh'] not in str(diagnostic.get('mesh', '')):
            raise ValueError('Simple diagnostic mesh differs from the actual named target')


def _validate_dual(path, run, cache):
    """Require evidence captured by the fresh survey; never qualify a stale overlay."""
    document = read(path)
    allowed = {'collision_proxy_stable_visual_grass_pending', 'collision_proxy_stable_visual_review_pending'}
    if (document.get('schema') != 'primary_scene_survey_dual_evidence_v3'
            or document.get('status') not in allowed or document.get('base_report_status') != 'complete'
            or document.get('geometry_signature_policy') != DUAL_POLICY
            or any(document.get(k) is not True for k in ('collision_proxy_qualified', 'geometry_proxy_stable', 'full_matrix_sampled'))
            or document.get('raw_scene_unchanged_certified') is not False
            or document.get('rendered_visibility_or_exposure_passed') is not False
            or document.get('collision_proxy_changes') != [] or not document.get('visual_warning')):
        raise ValueError('Dual evidence is unqualified or its Grass-only policy changed')
    snapshots = document['snapshots']
    if len(snapshots) < 2:
        raise ValueError('Dual evidence needs original start/end snapshots')
    pins = [document['base_report'], document['binding'], *snapshots]
    for pin in pins:
        Path(pin['path']).resolve().relative_to(run)
    _verify_pins([*document['source_pins'], *pins], cache)
    base = read(document['base_report']['path'])
    binding = read(document['binding']['path'])
    attempt = document['attempt_id']
    if (base.get('status') != 'complete' or base.get('attempt_id') != attempt
            or base.get('map') != document.get('map') or not _uses_dual(base)
            or binding.get('schema') != 'survey_dual_signature_binding_v3'
            or binding.get('attempt_id') != attempt or binding.get('geometry_signature_policy') != DUAL_POLICY
            or binding.get('private_worker_only') is not True
            or binding.get('original_global_worker_functions_modified') is not False):
        raise ValueError('Dual evidence is not bound to this fresh complete survey')
    _verify_pins(base['source_pins'], cache)
    _verify_pins([binding[k] for k in ('entry_source', 'original_worker_source', 'diff_source')], cache)
    source_keys = {(str(Path(p['path']).resolve()), p['sha256']) for p in document['source_pins']}
    if any((str(Path(p['path']).resolve()), p['sha256']) not in source_keys
           for p in [document['binding'], *snapshots, binding['entry_source']]):
        raise ValueError('Dual capture pins missing from job sources')
    captures = []
    for pin in snapshots:
        snapshot = read(pin['path'])
        if (snapshot.get('schema') != 'survey_dual_signature_snapshot_v3'
                or snapshot.get('attempt_id') != attempt or snapshot.get('binding') != document['binding']
                or snapshot.get('geometry_signature_policy') != DUAL_POLICY
                or snapshot.get('captured_at_original_scene_signature_call') is not True):
            raise ValueError('Snapshot was not captured at the bound original survey call')
        raw = snapshot['raw_payload']
        proxy = copy.deepcopy(raw)
        actors = {a['path']: a for a in proxy['actors']}
        for grass in snapshot['excluded_grass_components']:
            component = grass['component']
            if (grass['actual_class'] != DUAL_POLICY['excluded_actual_class']
                    or component.get('get_collision_enabled') != DUAL_POLICY['required_collision']
                    or component.get('visibility_response') != DUAL_POLICY['required_visibility_response']):
                raise ValueError('A non-qualified component was excluded')
            actors[grass['actor']]['components'].remove(component)
        if (proxy != snapshot['collision_proxy_payload']
                or _canonical_sha(raw) != snapshot['raw_scene_signature']
                or _canonical_sha(proxy) != snapshot['collision_proxy_signature']
                or snapshot['collision_proxy_signature'] != base.get('scene_signature')):
            raise ValueError('Raw/proxy payload or base signature differs')
        captures.append(snapshot)
    first, last = captures[0], captures[-1]
    changed = first['raw_scene_signature'] != last['raw_scene_signature']
    if (document['raw_before_signature'] != first['raw_scene_signature']
            or document['raw_after_signature'] != last['raw_scene_signature']
            or document['raw_scene_changed'] is not changed
            or document['excluded_grass_before'] != first['excluded_grass_components']
            or document['excluded_grass_after'] != last['excluded_grass_components']
            or bool(document['raw_before_after_changes']) != changed
            or document['status'] != ('collision_proxy_stable_visual_grass_pending' if changed else 'collision_proxy_stable_visual_review_pending')):
        raise ValueError('Raw appearance change receipt differs from captured endpoints')
    index = base['selected_full_attempt_index']
    if not isinstance(index, int) or not 0 <= index < len(base['full_attempts']):
        raise ValueError('Dual evidence lacks selected full attempt')
    selected = base['full_attempts'][index]
    if not _valid_attempt(selected) or document['summary'] != selected['summary']:
        raise ValueError('Dual evidence does not retain the full1260 matrix')
    _validate_ground(document, base, run, cache)
    return base, index, document


def _position(site):
    value = site.get('position')
    if value is None:
        return None
    return [float(value[k]) for k in ('x', 'y', 'z')] if isinstance(value, dict) else list(map(float, value))


def _same_point(site, candidate):
    position = _position(site)
    return (position is not None and len(position) == 3
            and all(abs(a-b) <= 1e-6 for a, b in zip(position, candidate['position']))
            and abs((float(site.get('yaw', 0.)) - float(candidate['yaw']) + 180.) % 360. - 180.) <= 1e-6)


def _render_choice(site):
    return render_definition(site)


def _valid_attempt(attempt):
    summary = attempt.get('summary', {})
    candidate = attempt.get('candidate', {})
    count = summary.get('no_proxy_conflict_combinations')
    combinations = attempt.get('combinations', [])
    if (summary.get('matrix_combinations') != 1260 or summary.get('full_matrix_sampled') is not True
            or not isinstance(count, int) or not 0 <= count <= 1260
            or summary.get('sample_items_completed', 0) <= 0
            or summary['sample_items_completed'] != summary.get('total_sample_items')
            or len(combinations) != 1260
            or sum(c.get('assessment') == 'no_conflict_detected_at_sampled_proxies' for c in combinations) != count):
        return False
    position = candidate.get('position', [])
    return (len(position) == 3 and all(math.isfinite(float(v)) for v in [*position, candidate.get('yaw', float('nan'))]))


def _verify_pins(pins, cache):
    if not pins:
        raise ValueError('Complete survey lacks source pins')
    for pin in pins:
        path = Path(pin['path']).resolve()
        stat = path.stat()
        key = (str(path), stat.st_size, stat.st_mtime_ns)
        if key not in cache:
            cache[key] = sha(path)
        if cache[key] != pin['sha256']:
            raise ValueError('Survey source pin changed: ' + str(path))


def _metadata(record, *, matches=True):
    if record is None:
        return {'survey_status': 'awaiting_complete_report', 'survey_report': None,
                'survey_summary': {'applies_to_current_site': False, 'full_matrix_sampled': False},
                'survey_warning_zh': '当前点位完整数字检查待完成；疑似问题不会自动成为排除组合。'}
    summary = copy.deepcopy(record['attempt']['summary'])
    summary.update(applies_to_current_site=matches, human_acceptance='pending')
    suspect = summary.get('suspected_conflict_combinations', 1260-summary['no_proxy_conflict_combinations'])
    if not matches:
        warning = '已有其他候选点的数字报告；当前已选点的完整检查待完成，不能沿用其他点位的通过数量。'
    elif suspect:
        warning = f'采样代理检查中{summary["no_proxy_conflict_combinations"]}/1260组合未发现冲突，另{suspect}组合有疑似问题；尚未自动排除，仍需结合画面判断。'
    else:
        warning = '1260组合的采样代理未发现冲突；无碰撞物体、衣发和采样间事件仍需看实际画面。'
    dual = record.get('dual')
    if dual:
        summary.update(collision_proxy_qualified=True, raw_scene_changed=dual['raw_scene_changed'],
                       raw_scene_unchanged_certified=False, rendered_visibility_or_exposure_passed=False)
        warning += ' ' + dual['visual_warning']
    ground_policy = dual.get('ground_query_policy') if dual else None
    ground_pin = dual.get('ground_query_evidence') if dual else None
    if ground_policy:
        warning += (' 地面仅使用简单碰撞代理，碰撞高度不保证与画面网格精确接地；脚底接地、草叶遮挡和曝光仍须看画面。'
                    if ground_policy.get('trace_complex') is False else ' 地面改用指定物体类型的复杂查询；实际地面、草叶遮挡和曝光仍待画面确认。')
        warning += ' 身体、站立、相机及遮挡仍用原Visibility检查。'
    diagnostic_pin = ground_policy.get('diagnostic_evidence') if ground_policy else None
    return {'survey_status': 'complete_for_selected_point' if matches else 'awaiting_matching_selected_point_report',
            'survey_report': record['pin'], 'survey_report_applies_to_site': matches,
            'survey_full_attempt_index': record['attempt_index'],
            'survey_summary': summary, 'survey_warning_zh': warning,
            'survey_dual_evidence': record.get('dual_pin'),
            'survey_qualification_status': dual['status'] if dual else None,
            'survey_ground_query_policy': copy.deepcopy(ground_policy),
            'survey_ground_evidence': ({'path': (Path(ground_pin['path']).resolve().relative_to(record['run']).as_posix()),
                                        'sha256': ground_pin['sha256']} if ground_pin else None),
            'survey_ground_diagnostic': ({'path': Path(diagnostic_pin['path']).resolve().relative_to(record['run']).as_posix(),
                                          'sha256': diagnostic_pin['sha256']} if diagnostic_pin else None),
            'automatic_confirmed_exclusions': False}


def merge_surveys(catalog_path=None, *, run=RUN, report_paths=None):
    """Fill unselected points only; publish separate per-card numeric metadata.

    No new sample plan is frozen here. Root may inspect exposure/representative
    framing before explicitly building a selected site's immutable render plan.
    """
    run = Path(run).resolve()
    catalog_path = Path(catalog_path or run/'scene_samples_sites_v1.json').resolve()
    catalog_hash = sha(catalog_path)
    catalog = read(catalog_path)
    sites = catalog['sites']
    if len(sites) != 26 or len({s['site_id'] for s in sites}) != 26 or len({s['map'] for s in sites}) != 26:
        raise ValueError('Keep exactly the26 existing primary site rows')
    expected_maps = {s['map'].split('.')[0] for s in sites}
    inventory_pin = catalog.get('source_inventory')
    if inventory_pin:
        if sha(inventory_pin['path']) != inventory_pin['sha256']:
            raise ValueError('Existing primary inventory pin changed')
        if {s['map_path'] for s in read(inventory_pin['path'])['scenes']} != expected_maps:
            raise ValueError('Sample catalog scope differs from existing26-primary inventory')
    frozen_before = {str(p): sha(p) for p in (run/'plans').glob('*.json')}
    paths = (sorted(map(Path, report_paths)) if report_paths is not None else
             sorted([*(run/'surveys').glob('*.json'), *(run/'dual_signature_reports').glob('*.json')]))
    by_map, rejected, cache, report_pins, source_pins = {}, [], {}, [], {}
    for path in paths:
        path = path.resolve()
        path.relative_to(run)
        try:
            report = read(path)
            dual = None
            selected_indices = None
            if report.get('schema') == 'primary_scene_survey_dual_evidence_v3':
                report, index, dual = _validate_dual(path, run, cache)
                selected_indices = {index}
            elif _uses_dual(report):
                continue  # A private proxy signature requires its immutable dual receipt.
            if report.get('schema') != 'all_primary_scene_site_survey_v1' or report.get('status') != 'complete':
                continue
            if report.get('map') not in expected_maps:
                continue
            _verify_pins(report.get('source_pins', []), cache)
            for source in [*report['source_pins'], *(dual['source_pins'] if dual else [])]:
                source_pins[(source['path'], source['sha256'])] = copy.deepcopy(source)
            pin = {'path': path.relative_to(run).as_posix(), 'sha256': sha(path)}
            base_pin = ({'path': Path(dual['base_report']['path']).resolve().relative_to(run).as_posix(),
                         'sha256': dual['base_report']['sha256']} if dual else pin)
            for index, attempt in enumerate(report.get('full_attempts', [])):
                if (selected_indices is not None and index not in selected_indices) or not _valid_attempt(attempt):
                    continue
                record = {'attempt': attempt, 'attempt_index': index, 'pin': base_pin,
                          'mtime': path.stat().st_mtime_ns, 'source_pins': report['source_pins'],
                          'dual': dual, 'dual_pin': pin if dual else None, 'run': run}
                by_map.setdefault(report['map'], []).append(record)
            report_pins.append(pin)
        except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
            rejected.append({'path': str(path), 'reason': str(exc)})
    rank = lambda r: (r['attempt']['summary']['no_proxy_conflict_combinations'], r['mtime'],
                       float(r['attempt']['candidate'].get('score', 0.)), r['pin']['path'], r['attempt_index'])
    updated = copy.deepcopy(catalog)
    metadata, populated, preserved = {}, [], []
    for site in updated['sites']:
        options = by_map.get(site['map'].split('.')[0], [])
        if site.get('position') is None:
            best = max(options, key=rank, default=None)
            if best:
                candidate = best['attempt']['candidate']
                site.update(position=dict(zip(('x', 'y', 'z'), candidate['position'])), yaw=float(candidate['yaw']))
                # Preserve root preselected exposure/exclusions/revision and labels.
                if site.get('location_label') in (None, '', '拍摄点待选择'):
                    site['location_label'] = '完整数字检查后的候选点 · 待实际画面审查'
                populated.append(site['site_id'])
            metadata[site['site_id']] = _metadata(best)
        else:
            preserved.append(site['site_id'])
            matching = [r for r in options if _same_point(site, r['attempt']['candidate'])]
            record = max(matching, key=rank, default=None)
            metadata[site['site_id']] = _metadata(record) if record else _metadata(max(options, key=rank, default=None), matches=False)
    updated['survey_metadata'] = metadata
    updated['survey_merge_sources'] = report_pins
    updated['survey_merge_source_pins'] = list(source_pins.values())
    index_path = run/INDEX
    index = read(index_path) if index_path.is_file() else {'schema': 'primary_scene_samples_index_v1', 'sites': []}
    index_hash = sha(index_path) if index_path.is_file() else None
    old = {s['site_id']: s for s in index['sites']}
    cards = []
    for site in updated['sites']:
        prior = old.get(site['site_id'], {})
        card = copy.deepcopy(site)
        sample_plan = prior.get('sample_plan')
        if sample_plan:
            path = run/sample_plan['path']
            if sha(path) != sample_plan['sha256']:
                raise ValueError('Existing immutable sample plan changed')
            if _render_choice(read(path)['site']) != _render_choice(site):
                sample_plan = None  # Preserve prior artifacts, never mislabel their location.
        card.update(sample_plan=sample_plan, sample_count=prior.get('sample_count', 0) if sample_plan else 0,
                    status='planned' if sample_plan else 'point_selected_pending_sample_plan' if site.get('position') is not None else 'point_pending')
        card.update(metadata[site['site_id']])
        cards.append(card)
    if sha(catalog_path) != catalog_hash or (index_hash and sha(index_path) != index_hash):
        raise ValueError('Root choices or sample index changed during merge; retry without overwriting')
    write(catalog_path, updated)
    index.update(sites=cards, scene_count=26, sample_count=sum(s['sample_count'] for s in cards),
                 source_catalog={'path': str(catalog_path), 'sha256': sha(catalog_path)},
                 survey_metadata=metadata, existing_primary_catalog_only=True, scene_purpose_rescreened=False)
    write(index_path, index)
    if any(sha(p) != digest for p, digest in frozen_before.items()):
        raise ValueError('Frozen sample plan changed during observational merge')
    receipt = {'schema': 'primary_scene_survey_catalog_merge_v1', 'success': True,
        'primary_site_count': 26, 'populated_previously_unselected_sites': populated,
        'preserved_existing_root_choices': preserved, 'report_count': len(report_pins),
        'rejected_reports': rejected, 'frozen_plan_hashes_unchanged': frozen_before,
        'confirmed_exclusions_created': 0, 'catalog_pin': {'path': str(catalog_path), 'sha256': sha(catalog_path)},
        'index_pin': {'path': str(index_path), 'sha256': sha(index_path)},
        'scope': 'complete1260 sampled-proxy reports only; root-selected points and exposure remain; suspected findings are warnings'}
    write(run/'scene_survey_merge_v1.json', receipt)
    return {'catalog': str(catalog_path), 'scenes': 26, 'new_points': len(populated),
            'root_choices_preserved': len(preserved), 'rejected_reports': len(rejected)}


def sync_catalog_to_saved_points(catalog_path=None, *, run=RUN, panel_run=None, apply=False):
    """Offline upsert into the existing panel format; default is a read-only preview.

    Only this26-primary catalog's selected IDs are managed. A user-edited file or
    an existing unowned ID is a conflict, never an implicit overwrite. No live
    scene/selection or freshness stamp is manufactured.
    """
    import camera_standard_v3 as standard
    import scene_site_review_geometry_v1 as geo
    from build_primary_scene_samples_v1 import validate_site, excluded
    run = Path(run).resolve()
    panel_run = Path(panel_run or geo.RUN).resolve()
    catalog_path = Path(catalog_path or run/'scene_samples_sites_v1.json').resolve()
    catalog_path.relative_to(run)
    catalog_pin = {'path': str(catalog_path), 'sha256': sha(catalog_path)}
    catalog = read(catalog_path)
    sites = catalog['sites']
    if (len(sites) != 26 or len({s['site_id'] for s in sites}) != 26
            or len({s['map'] for s in sites}) != 26
            or any(not s['site_id'].startswith('primary_') for s in sites)):
        raise ValueError('Sync is restricted to this26-primary catalog namespace')
    inventory = catalog['source_inventory']
    _verify_pins([inventory], {})
    if {s['map_path'] for s in read(inventory['path'])['scenes']} != {s['map'].split('.')[0] for s in sites}:
        raise ValueError('Saved-point scope differs from the existing primary inventory')
    config = standard.load_config(geo.CAMERA_STANDARD)
    config_pin = {'path': str(geo.CAMERA_STANDARD), 'sha256': sha(geo.CAMERA_STANDARD)}
    local_path = panel_run/'site_review_local_geometry_v1.json'
    local = read(local_path)
    local_pin = {'path': str(local_path), 'sha256': sha(local_path)}
    _verify_pins(local['sources'], {})
    if config_pin not in [{'path': p['path'], 'sha256': p['sha256']} for p in local['sources']]:
        raise ValueError('Panel geometry is not prepared with the current50% standard')
    shots = local['shots']
    if len(shots) != 1260:
        raise ValueError('Expected the existing1260 panel combinations for exclusion mapping')
    root = panel_run/'sites'
    staged, skipped = [], []
    for source in sites:
        if not validate_site(source):
            skipped.append(source['site_id'])
            continue
        target = (root/(source['site_id']+'.json')).resolve()
        if target.parent != root.resolve():
            raise ValueError('Saved-point target escapes the existing sites directory')
        previous = read(target) if target.is_file() else None
        if previous:
            origin = previous.get('primary_catalog_sync', {})
            payload = {k: v for k, v in previous.items() if k != 'primary_catalog_sync'}
            if (origin.get('source_run') != str(run) or origin.get('site_id') != source['site_id']
                    or origin.get('managed_payload_sha256') != object_sha(payload)):
                raise ValueError('Existing user-owned or edited saved point is protected: '+str(target))
        decisions = [{'action_id': s['motion_id'], 'camera_id': s['camera_id'],
                      'aspect': s['orientation'], 'decision': 'excluded'}
                     for s in shots if excluded(s, source.get('exclusions', []))]
        if any(not any(excluded(s, [item]) for s in shots) for item in source.get('exclusions', [])):
            raise ValueError('An exclusion does not map to the current panel matrix: '+source['site_id'])
        # These explicit rows are for the coordinated worker import step. Do not
        # spoof decisions_stamp: existing live decisions require a genuine stamp.
        site = copy.deepcopy(source)
        site.update(name=(source.get('scene_label') or source['site_id'])+' · '+(source.get('location_label') or '选定点位'),
                    position=dict(zip(('x', 'y', 'z'), _position(source))),
                    yaw=float(source.get('yaw', 0.)), exposure_compensation=float(source.get('exposure_compensation', 0.)),
                    allowed_combinations=[], issue_reviews={}, needs_recheck=True,
                    imported_excluded_combinations=decisions,
                    imported_camera_standard={'standard_id': config['standard_id'], 'distance_factor': .5,
                        'scope': 'nonface_landscape', 'portrait_and_face_unchanged': True, 'configuration': config_pin},
                    imported_preview_semantics='pending_private_version_adapter_exposure_and_exclusion_integration')
        record = {'site': site, 'input_fingerprint': None, 'scene_signature': None,
                  'report': None, 'human_acceptance': 'pending'}
        record['primary_catalog_sync'] = {'source_run': str(run), 'site_id': source['site_id'],
            'catalog': catalog_pin, 'managed_payload_sha256': object_sha(record),
            'panel_local_geometry': local_pin,
            'exposure_policy': '0 inherits scene; nonzero camera-only absolute auto-exposure bias; no source-map edit',
            'exclusions_policy': 'raw catalog exclusions preserved; explicit excluded rows expanded without allowed/pass decisions',
            'integration_policy': 'original worker stays byte-identical to preserve historical source pins; use a separately pinned private version adapter',
            'human_acceptance': 'pending', 'requires_panel_recheck': True}
        staged.append((target, record, sha(target) if previous else None))
    result = {'schema': 'primary_catalog_panel_saved_points_sync_v1', 'applied': bool(apply),
        'source_catalog': catalog_pin, 'panel_run': str(panel_run),
        'selected_site_ids': [r['site']['site_id'] for _, r, _ in staged], 'unselected_site_ids_skipped': skipped,
        'updates': [{'path': str(p), 'operation': 'update' if old else 'create'} for p, _, old in staged],
        'other_saved_points_and_current_selection_unchanged': True, 'ue_executed': False,
        'human_acceptance': 'pending',
        'limitation': 'A separately pinned private version adapter must import excluded rows and camera EV before those fields affect preview/check scope; never edit the historical pinned worker.'}
    if apply:
        if sha(catalog_path) != catalog_pin['sha256']:
            raise ValueError('Root catalog changed while preparing saved points')
        for target, record, old in staged:
            if (sha(target) if target.is_file() else None) != old:
                raise ValueError('Saved point changed during offline sync; retry without overwriting')
            if old and read(target) == record:
                continue
            if old:
                backup = run/'panel_saved_point_backups'/(target.stem+'_'+old+'.json')
                if not backup.exists():
                    write(backup, read(target))
            temporary = target.with_suffix('.json.sync-tmp')
            write(temporary, record)
            temporary.replace(target)
        result['saved_pins'] = [{'path': str(p), 'sha256': sha(p)} for p, _, _ in staged]
        write(run/'panel_saved_points_sync_v1.json', result)
    return result


if __name__ == '__main__':
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-root', type=Path, default=RUN)
    parser.add_argument('--catalog', type=Path)
    parser.add_argument('--no-gallery', action='store_true')
    parser.add_argument('--sync-panel-sites', action='store_true', help='Only preview saved-point upserts; no survey merge or UE dispatch')
    parser.add_argument('--panel-run', type=Path)
    parser.add_argument('--apply', action='store_true', help='Write the previewed saved-point upserts')
    args = parser.parse_args()
    if args.apply and not args.sync_panel_sites:
        parser.error('--apply requires --sync-panel-sites')
    result = (sync_catalog_to_saved_points(args.catalog, run=args.run_root, panel_run=args.panel_run, apply=args.apply)
              if args.sync_panel_sites else merge_surveys(args.catalog, run=args.run_root))
    if not args.no_gallery and not args.sync_panel_sites:
        from build_primary_scene_samples_v1 import build_gallery
        result['gallery'] = build_gallery(args.run_root)
    print(json.dumps(result, ensure_ascii=False))
