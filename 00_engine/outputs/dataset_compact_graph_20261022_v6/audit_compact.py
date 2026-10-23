"""Read-only v6 graph audit, retaining the independent v5 semantic checks.

Writes only diagnostics_*.json beside this file. Never changes a graph, session,
catalog, UE state, or v5 file. Formal clothing-domain probes are not chain sampling.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
V5 = HERE.parent/'dataset_balanced_graph_20261022_v5'
sys.path.insert(0, str(V5))
import audit_candidate as base

SLOTS = ('shirts', 'coats', 'pants', 'skirts', 'full_body')


def write_diagnostic(path, value):
    path = Path(path).resolve()
    if path.parent != HERE or not path.name.startswith('diagnostics_') or path.suffix != '.json':
        raise ValueError('Audit writes must be v6/diagnostics_*.json')
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def catalog_slot_diagnostic(rules=None):
    rules = rules or base.Rules()
    rng = random.Random(20261022)
    groups = []
    byslot = {slot: {'catalog_core_asset_ids': set(), 'variable_groups': [],
                     'formal_option_value_count_sum': 0,
                     'slot_only_directed_value_transitions_sum': 0,
                     'verified_actual_neighbor_slots': 0} for slot in SLOTS}
    for sex, data in rules.cat['sexes'].items():
        for family in data['families']:
            for group in family['groups']:
                fid, gid = family['family_id'], group['group_id']
                source = base.nc.sample_choice(sex, rng, family_id=fid, group_id=gid)
                neighbors = base.nc.single_piece_neighbors(sex, source)
                actual_slots = Counter(row['slot'] for row in neighbors)
                row = {'sex': sex, 'family': fid, 'group': gid,
                       'assembly_mode': family['assembly_mode'], 'slots': {}}
                assets = group['required_assets'] + group['optional_assets']
                assets += [a for options in group['slot_options'].values() for a in options]
                for asset in assets:
                    if asset['slot'] in byslot:
                        byslot[asset['slot']]['catalog_core_asset_ids'].add(asset['asset_id'])
                for slot in SLOTS:
                    options = [a['asset_id'] for a in group['slot_options'].get(slot, [])]
                    if slot in group['optional_slots']:
                        options.append(None)
                    variable = family['assembly_mode'] != 'locked_bundle' and len(options) > 1
                    row['slots'][slot] = {'option_values': options, 'variable_within_group': variable,
                                          'actual_legal_neighbors_from_probe': actual_slots[slot]}
                    if variable:
                        d = byslot[slot]
                        d['variable_groups'].append(fid+'/'+gid)
                        d['formal_option_value_count_sum'] += len(options)
                        d['slot_only_directed_value_transitions_sum'] += len(options)*(len(options)-1)
                        d['verified_actual_neighbor_slots'] += bool(actual_slots[slot])
                        if not actual_slots[slot]:
                            row['slots'][slot]['warning'] = 'Structural alternatives failed formal neighbor probe'
                groups.append(row)
    summary = {}
    for slot, data in byslot.items():
        assets = data.pop('catalog_core_asset_ids')
        summary[slot] = {**data, 'catalog_core_asset_distinct': len(assets),
                         'catalog_core_asset_ids': sorted(assets),
                         'variable_group_count': len(data['variable_groups'])}
    return {'schema': 'v6_formal_single_slot_catalog_diagnostic',
            'catalog_snapshot': str(base.V1/'catalog.json'),
            'catalog_snapshot_sha256': hashlib.sha256((base.V1/'catalog.json').read_bytes()).hexdigest(),
            'scope': 'Current formal wardrobe resolution with immutable normalized attribute snapshot; no UE or graph mutation',
            'summary': summary, 'groups': groups,
            'interpretation': [
                'Option/transition sums describe one varying slot inside a legal family/group; they do not count full outfit combinations.',
                'Upper-body cameras exclude pants/skirts-only changes; front_head excludes all wardrobe edits.',
                'Formal single slot availability must be conditioned on the actual source outfit and camera.',
                'Locked bundles and groups with one slot value do not create single-piece alternatives.',
            ]}


def start_camera_diagnostic(states, sessions, rules):
    cameras = sorted(rules.pools['camera'])
    weights = {c: 1.5 if c in base.ID_CAMERAS else 1 for c in cameras}
    weight_sum = sum(weights.values())
    counts = Counter(states[s['history'][0]]['camera'] for s in sessions)
    total = sum(counts.values())
    rows = {}
    for camera in cameras:
        target = weights[camera]/weight_sum
        actual = counts[camera]/total if total else 0
        rows[camera] = {'weight': weights[camera], 'target_fraction': target,
                        'target_count': total*target, 'actual_count': counts[camera],
                        'actual_fraction': actual, 'relative_deviation': actual/target-1,
                        'absolute_relative_deviation': abs(actual/target-1)}
    eligible_count = sum(counts[c] for c in base.ID_CAMERAS)
    complete_jobs = defaultdict(Counter)
    distinct_axes = defaultdict(list)
    for session in sessions:
        camera = states[session['history'][0]]['camera']
        complete_jobs[camera][f"{session['kind']}_{session['length']}"] += 1
        if session['length'] == 5:
            distinct_axes[camera].append(len({step['axis'] for step in session['steps']}))
    for camera in cameras:
        rows[camera]['completed_length_kind_counts'] = dict(complete_jobs[camera])
        vals = distinct_axes[camera]
        rows[camera]['observed_L5_mean_distinct_axes'] = sum(vals)/len(vals) if vals else None
    target_front = sum(weights.get(c, 0) for c in base.ID_CAMERAS)/weight_sum
    front = eligible_count/total if total else 0
    return {'definition': 'Session history[0] camera, including explicit coverage jobs',
            'camera_count': len(cameras), 'total_starts': total, 'catalog_weight_sum': weight_sum,
            'cameras': rows, 'missing_start_cameras': [c for c in cameras if not counts[c]],
            'all_21_start_cameras_covered': not any(not counts[c] for c in cameras),
            'max_absolute_relative_deviation': max(r['absolute_relative_deviation'] for r in rows.values()),
            'total_variation': .5*sum(abs(r['actual_fraction']-r['target_fraction']) for r in rows.values()),
            'identity_eligible_front_count': eligible_count, 'identity_eligible_front_fraction': front,
            'identity_eligible_front_target_fraction': target_front,
            'identity_eligible_front_relative_deviation': front/target_front-1,
            'diagnostic_soft_flag_within_10_percent_each_camera': all(r['absolute_relative_deviation'] <= .10 for r in rows.values()),
            'new_camera_tolerance_not_added_to_v5_hard_checks': True}


def graph_structure_diagnostic(root, rules=None):
    """Optimistic length support without running a sampler or inventing edges.

    Reachable axis-mask sets use exact directed walks of length L. They are an
    upper bound because accumulated reuse, global axis caps and uniqueness are
    deliberately absent. Observed accepted sessions remain the capacity proof.
    """
    root = Path(root).resolve()
    rules = rules or base.Rules()
    report = {'graph_root': str(root), 'walk_support_is_optimistic_not_quota_feasibility_proof': True}
    mask_has = {axis: sum(1 << mask for mask in range(128) if mask & (1 << index))
                for index, axis in enumerate(base.AXES)}
    all_masks = (1 << 128)-1
    popcount_masks = {k: sum(1 << mask for mask in range(128) if mask.bit_count() == k) for k in range(8)}
    for split in ('train', 'test'):
        states = {row['id']: row['state'] for row in base.read(root/split/'nodes.json')}
        edges = base.read(root/split/'edges.json')
        adj = defaultdict(lambda: defaultdict(list))
        counts, singles = Counter(), Counter()
        for edge in edges:
            adj[edge['source']][edge['axis']].append(edge['target'])
            counts[edge['axis']] += 1
            if edge.get('mode') == 'single_piece':
                singles[edge['slot']] += 1
        previous = {u: 1 for u in states}
        walks = {u: 1 for u in states}
        by_length = {}
        for length in range(1, 6):
            current, nextwalks = {}, {}
            for u in states:
                possible, total = 0, 0
                for index, axis in enumerate(base.AXES):
                    merged = 0
                    for v in adj[u].get(axis, []):
                        merged |= previous[v]
                        total += walks[v]
                    # Map each achievable suffix mask to mask OR this axis.
                    possible |= (merged & mask_has[axis]) | ((merged & (all_masks ^ mask_has[axis])) << (1 << index))
                current[u], nextwalks[u] = possible, total
            cameras = {}
            for camera in sorted(rules.pools['camera']):
                ids = [u for u, s in states.items() if s['camera'] == camera]
                maximums = [max((k for k in range(8) if current[u] & popcount_masks[k]), default=0) for u in ids]
                cameras[camera] = {'nodes': len(ids), 'nodes_with_complete_walk': sum(bool(current[u]) for u in ids),
                    'maximum_distinct_axes_histogram': base.hist(maximums),
                    'mean_of_per_node_maximum_distinct_axes': sum(maximums)/len(maximums) if maximums else None,
                    'fraction_nodes_supporting_all_L_axes': sum(k >= length for k in maximums)/len(maximums) if maximums else None,
                    'directed_walk_count': sum(nextwalks[u] for u in ids)}
            by_length[str(length)] = cameras
            previous, walks = current, nextwalks
        formal_missing = single_slot_diagnostic(states, edges, [], rules)
        planned = base.LIMITS[split][2]
        ideal_six = planned*(1-.09)/6
        report[split] = {'nodes': len(states), 'edges': len(edges), 'axis_edges': dict(counts),
            'single_slot_edges': dict(singles),
            'per_axis_optimistic_capacity': {a: {'directed_edges': counts[a], 'at_reuse2': 2*counts[a],
                'at_reuse3': 3*counts[a], 'at_reuse4': 4*counts[a],
                'ideal_nonidentity_target_at_9_percent_identity': ideal_six if a != 'identity' else None,
                'reuse2_capacity_fraction_of_ideal': 2*counts[a]/ideal_six if a != 'identity' else None} for a in base.AXES},
            'exact_length_walk_axis_support_by_camera': by_length,
            'formal_single_slot_graph_gaps': formal_missing}
    return report


def single_slot_diagnostic(states, edges, sessions, rules):
    # Formal availability comes from the exact source clothes+camera; saved
    # adjacency is audited separately and never defines the formal denominator.
    graph_slots = defaultdict(set)
    for edge in edges:
        if edge.get('axis') == 'wardrobe' and edge.get('mode') == 'single_piece':
            graph_slots[edge['source']].add(edge['slot'])
    formal_cache = {}

    def formal_slots(u):
        if u not in formal_cache:
            formal_cache[u] = {row['slot'] for row in rules.singles(states[u])}
        return formal_cache[u]

    node_offers, node_missing = Counter(), Counter()
    for u in states:
        available = formal_slots(u)
        for slot in available:
            node_offers[slot] += 1
            node_missing[slot] += slot not in graph_slots[u]
    actual, expected, expected_on_eligible_wardrobe = Counter(), Counter(), Counter()
    single_offers, single_missing = Counter(), Counter()
    wardrobe_offers, wardrobe_missing = Counter(), Counter()
    available_patterns, graph_patterns = Counter(), Counter()
    illegal_chosen_slot = []
    single_events, eligible_wardrobe_events = 0, 0
    for session in sessions:
        for turn, step in enumerate(session['steps'], 1):
            if step['axis'] != 'wardrobe':
                continue
            u = step['source']
            available = formal_slots(u)
            if available:
                eligible_wardrobe_events += 1
                for slot in available:
                    # Overall formal 50:50 single/whole target, excluding whole-only contexts.
                    expected_on_eligible_wardrobe[slot] += .5/len(available)
                    wardrobe_offers[slot] += 1
                    wardrobe_missing[slot] += slot not in graph_slots[u]
            if step['mode'] != 'single_piece':
                continue
            single_events += 1
            actual[step['slot']] += 1
            available_patterns['+'.join(sorted(available))] += 1
            graph_patterns['+'.join(sorted(graph_slots[u]))] += 1
            if step['slot'] not in available:
                illegal_chosen_slot.append({'session': session['id'], 'turn': turn, 'slot': step['slot']})
            for slot in available:
                expected[slot] += 1/len(available)
                single_offers[slot] += 1
                single_missing[slot] += slot not in graph_slots[u]
    rows = {}
    for slot in SLOTS:
        n, ex = actual[slot], expected[slot]
        rows[slot] = {'actual_single_edit_count': n,
                      'formal_conditional_expected_given_actual_single_events': ex,
                      'actual_minus_expected': n-ex,
                      'relative_deviation_when_expected_positive': n/ex-1 if ex else None,
                      'formal_expected_at_half_of_eligible_wardrobe_events': expected_on_eligible_wardrobe[slot],
                      'graph_node_formal_slot_opportunities': node_offers[slot],
                      'graph_node_missing_slot_count': node_missing[slot],
                      'graph_node_missing_slot_fraction': node_missing[slot]/node_offers[slot] if node_offers[slot] else None,
                      'single_event_formal_slot_opportunities': single_offers[slot],
                      'single_event_missing_graph_slot_count': single_missing[slot],
                      'single_event_missing_graph_slot_fraction': single_missing[slot]/single_offers[slot] if single_offers[slot] else None,
                      'wardrobe_event_formal_slot_opportunities': wardrobe_offers[slot],
                      'wardrobe_event_missing_graph_slot_count': wardrobe_missing[slot],
                      'wardrobe_event_missing_graph_slot_fraction': wardrobe_missing[slot]/wardrobe_offers[slot] if wardrobe_offers[slot] else None}
    return {'definition': 'For each actual single event, add 1/number_of_formally_available_slots to each source-legal slot; availability includes camera visibility and exact outfit rules.',
            'no_uniform_five_slot_requirement': True, 'single_events': single_events,
            'formal_single_eligible_wardrobe_events': eligible_wardrobe_events,
            'slots': rows, 'formal_available_slot_patterns_at_single_events': dict(available_patterns),
            'saved_graph_available_slot_patterns_at_single_events': dict(graph_patterns),
            'conditional_actual_vs_expected_total_variation': .5*sum(abs(actual[s]-expected[s]) for s in SLOTS)/single_events if single_events else None,
            'graph_missing_formal_slot_opportunity_fraction': sum(node_missing.values())/sum(node_offers.values()) if node_offers else None,
            'illegal_chosen_slot_count': len(illegal_chosen_slot), 'illegal_chosen_slots_first_20': illegal_chosen_slot[:20]}


def compare_same_start_camera(candidate_path, baseline_path, rules):
    """Separate camera-mixture effects from within-camera chain diversity.

    Every kind/length is compared separately. Missing baseline cameras (notably
    the v5 test) remain missing; no unsupported mean is imputed.
    """
    buckets = {}
    for name, path in [('candidate', Path(candidate_path)), ('baseline', Path(baseline_path))]:
        states = {row['id']: row['state'] for row in base.read(path/'nodes.json')}
        groups = defaultdict(lambda: defaultdict(lambda: [0, 0]))
        for line in (path/'sessions.jsonl').read_text(encoding='utf-8-sig').splitlines():
            if not line.strip():
                continue
            session = json.loads(line)
            camera = states[session['history'][0]]['camera']
            key = f"{session['kind']}_{session['length']}"
            groups[key][camera][0] += 1
            groups[key][camera][1] += len({step['axis'] for step in session['steps']})
        buckets[name] = groups
    weights = {c: 1.5 if c in base.ID_CAMERAS else 1 for c in rules.pools['camera']}
    total_weight = sum(weights.values())
    result = {'baseline_root': str(Path(baseline_path).parent),
              'definition': 'Compare each kind and length within identical starting camera; standardize both means to the requested 1.5/1 camera weights over common represented cameras only.',
              'missing_baseline_cameras_are_not_imputed': True, 'per_length_kind': {}}
    for key in sorted(set(buckets['candidate']) | set(buckets['baseline'])):
        newer, older = buckets['candidate'][key], buckets['baseline'][key]
        common = sorted(set(newer) & set(older))
        denominator = sum(weights[c] for c in common)
        details = {}
        for c in common:
            nn, ns = newer[c]
            on, os = older[c]
            details[c] = {'candidate_n': nn, 'baseline_n': on,
                          'candidate_mean_distinct_axes': ns/nn,
                          'baseline_mean_distinct_axes': os/on, 'delta': ns/nn-os/on}
        result['per_length_kind'][key] = {
            'candidate_raw_mean': sum(row[1] for row in newer.values())/sum(row[0] for row in newer.values()) if newer else None,
            'baseline_raw_mean': sum(row[1] for row in older.values())/sum(row[0] for row in older.values()) if older else None,
            'common_camera_target_probability_mass': denominator/total_weight,
            'candidate_common_camera_standardized_mean': sum(weights[c]*details[c]['candidate_mean_distinct_axes'] for c in common)/denominator if denominator else None,
            'baseline_common_camera_standardized_mean': sum(weights[c]*details[c]['baseline_mean_distinct_axes'] for c in common)/denominator if denominator else None,
            'same_camera_standardized_delta': sum(weights[c]*details[c]['delta'] for c in common)/denominator if denominator else None,
            'missing_baseline_cameras': sorted(set(weights)-set(older)),
            'missing_candidate_cameras': sorted(set(weights)-set(newer)),
            'within_camera_means_and_counts': details}
    return result


def validate_allaxis_coverage_disclosure(path, states, sessions, rules):
    metrics = base.read(Path(path)/'metrics.json') if (Path(path)/'metrics.json').exists() else {}
    sampling = metrics.get('construction', {}).get('sampling', {})
    records = sampling.get('forced_allaxis_coverage_jobs', [])
    records_by_id, errors = {}, []
    for record in records:
        sid = record.get('session_id')
        if sid in records_by_id:
            errors.append({'kind': 'allaxis_warmup_duplicate_record', 'detail': sid})
        records_by_id[sid] = record

    def attributes(step):
        u, v, axis = step['source'], step['target'], step['axis']
        s, t = states[u], states[v]
        if axis != 'wardrobe':
            value = [t['sex'], t[axis]] if axis in ('identity', 'hair') else t[axis]
            return {(axis, base.token(value))}
        w = t['wardrobe']
        gained = set(rules.clothes(t)['core'])-set(rules.clothes(s)['core'])
        return {('wardrobe_family', base.token([t['sex'], w['family_id']])),
                ('wardrobe_group', base.token([t['sex'], w['family_id'], w['group_id']])),
                *(('wardrobe_core', base.token([t['sex'], asset])) for asset in gained)}

    seen, edge_use, found = set(), Counter(), set()
    for session in sessions:
        sid = session['id']
        if sid in records_by_id:
            record = records_by_id[sid]
            found.add(sid)
            try:
                first = session['steps'][0]
                request = record['requested_attribute']
                requested = request['field'], base.token(request['value'])
                actual = attributes(first)
                claims = {(r['field'], base.token(r['value'])) for r in record['new_attribute_target_gains']}
                real_fork_parent = session['steps'][session['fork_round']-1]['source_position'] if session['fork_round'] else None
                if (requested not in actual or requested in seen or not claims <= (actual-seen)
                        or record['forced_round'] != 1 or record['axis'] != first['axis']
                        or record['source'] != first['source'] or record['target'] != first['target']
                        or record['kind'] != session['kind'] or record['length'] != session['length']
                        or record['fork_round'] != session['fork_round']
                        or record['fork_source_position'] != real_fork_parent
                        or record['edge_reuse_before'] != edge_use[first['source'], first['target']]):
                    errors.append({'kind': 'allaxis_warmup_disclosure_mismatch', 'detail': sid})
            except Exception as exc:
                errors.append({'kind': 'allaxis_warmup_disclosure_invalid', 'detail': [sid, repr(exc)]})
        for step in session['steps']:
            seen.update(attributes(step))
            edge_use[step['source'], step['target']] += 1
    if set(records_by_id)-found:
        errors.append({'kind': 'allaxis_warmup_session_missing', 'detail': sorted(set(records_by_id)-found)})
    if sampling.get('forced_allaxis_coverage_job_count', len(records)) != len(records):
        errors.append({'kind': 'allaxis_warmup_disclosure_count', 'detail': len(records)})
    return {'record_count': len(records), 'records_match_saved_sessions_and_previously_unseen_actual_targets': not errors,
            'selection_is_explicit_coverage_not_pure_random': bool(records)}, errors


def audit_compact(root=None, output=None, *, train_root=None, test_root=None):
    root = Path(root).resolve() if root is not None else None
    paths = {}
    for split, override in [('train', train_root), ('test', test_root)]:
        path = Path(override).resolve() if override is not None else (root/split if root is not None else None)
        if path is not None:
            if not (path/'nodes.json').exists() and (path/split/'nodes.json').exists():
                path = path/split
            paths[split] = path
    if not paths:
        raise ValueError('Provide root, train_root, test_root, or a pair of split roots')
    rules = base.Rules()
    report = {'schema': 'independent_compact_saved_candidate_audit_v6', 'candidate_root': str(root) if root else None,
              'audited_split_source_paths': {split: str(path) for split, path in paths.items()},
              'audited_splits': list(paths), 'complete_train_test_audit': len(paths) == 2,
              'base_hard_check_implementation': str(V5/'audit_candidate.py'),
              'base_hard_check_sha256': hashlib.sha256((V5/'audit_candidate.py').read_bytes()).hexdigest(),
              'scope': 'Offline saved-node/edge/session semantics and marginal diagnostics; no UE or visual acceptance'}
    keys, chains = {}, {}
    for split, path in paths.items():
        result, keys[split], chains[split] = base.audit_split(path, split, rules)
        result['passed_v5_hard_checks'] = result['passed_hard_checks']
        if split == 'train':
            # This run requires the actual edited target values as well as the
            # v5 used-node coverage. Core clothes must be genuinely introduced,
            # not merely retained beside another changed garment.
            extra = []
            for axis, coverage in result['edited_axis_target_value_coverage'].items():
                if axis != 'core_asset' and coverage['missing']:
                    extra.append(('train_edited_axis_target_coverage', {'axis': axis, 'missing': coverage['missing']}))
            missing_core = result['wardrobe']['introduced_core_target_coverage']['missing']
            if missing_core:
                extra.append(('train_true_introduced_core_coverage', {'missing': missing_core}))
            for kind, detail in extra:
                result['error_counts'][kind] = result['error_counts'].get(kind, 0)+1
                if len(result['errors_first_100']) < 100:
                    result['errors_first_100'].append({'kind': kind, 'detail': detail})
            if extra:
                result['passed_hard_checks'] = False
            result['thresholds_and_flags']['v6_train_all_edited_axis_values_are_hard_required'] = True
            result['thresholds_and_flags']['v6_train_core_coverage_uses_true_introduced_assets'] = True
        states = {row['id']: row['state'] for row in base.read(path/'nodes.json')}
        edges = base.read(path/'edges.json')
        sessions = [json.loads(line) for line in (path/'sessions.jsonl').read_text(encoding='utf-8-sig').splitlines() if line.strip()]
        sampling = base.read(path/'metrics.json').get('construction', {}).get('sampling', {}) if (path/'metrics.json').exists() else {}
        decay = sampling.get('history_axis_decay')
        result['sampling_policy_disclosures'] = {
            'saved_history_axis_decay': decay, 'legacy_decay_0_5_preserved': decay == .5,
            'history_axis_decay_is_not_inferred_from_observed_sessions': True,
            'weight_formula': 'legal base identity2/other1 times history_axis_decay**prior_axis_count_in_entire_session times global feedback; explicit coverage first steps override the axis draw',
            'feedback_exponent_claim': sampling.get('feedback_exponent'),
            'cap2_attempts_before_cap3_claim': sampling.get('cap2_attempts_before_cap3')}
        source = path.parent/'sampler_source.py'
        if source.exists():
            result['sampling_policy_disclosures']['saved_sampler_source_path'] = str(source)
            result['sampling_policy_disclosures']['saved_sampler_source_sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
        result['coverage_warmup_disclosure']['axis_weight_formula_static_review'] = result['sampling_policy_disclosures']['weight_formula']
        disclosure, disclosure_errors = validate_allaxis_coverage_disclosure(path, states, sessions, rules)
        result['allaxis_coverage_warmup_disclosure'] = disclosure
        for error in disclosure_errors:
            kind = error['kind']
            result['error_counts'][kind] = result['error_counts'].get(kind, 0)+1
            if len(result['errors_first_100']) < 100:
                result['errors_first_100'].append(error)
        if disclosure_errors:
            result['passed_hard_checks'] = False
        result['start_camera_diagnostic'] = start_camera_diagnostic(states, sessions, rules)
        result['single_slot_diagnostic'] = single_slot_diagnostic(states, edges, sessions, rules)
        v5_baseline = V5/'candidate_c_seed1'/split
        if (v5_baseline/'sessions.jsonl').exists():
            result['vs_v5_start_camera_conditioned'] = compare_same_start_camera(path, v5_baseline, rules)
        report[split] = result
    report['canonical_train_test_overlap'] = len(keys['train'] & keys['test']) if len(paths) == 2 else None
    report['full_chain_train_test_overlap'] = len(chains['train'] & chains['test']) if len(paths) == 2 else None
    report['cross_split_disjointness_checked'] = len(paths) == 2
    cross_ok = len(paths) != 2 or (not report['canonical_train_test_overlap'] and not report['full_chain_train_test_overlap'])
    report['passed_v5_hard_checks'] = all(report[s]['passed_v5_hard_checks'] for s in paths) and cross_ok
    report['passed_hard_checks'] = all(report[s]['passed_hard_checks'] for s in paths) and cross_ok
    baseline_path = V5/'rotated_baseline_sequence_stats.json'
    if baseline_path.exists():
        baseline = base.read(baseline_path)
        report['sequence_comparison_baseline'] = str(HERE.parent/'dataset_sequence_graph_20261021_v4/rotated')
        for split in paths:
            report[split]['vs_v4_rotated_distinct_axes'] = {
                key: {'baseline_mean_distinct_axes': baseline[split]['per_length_kind_sequence_means'][key]['distinct_axes'],
                      'candidate_mean_distinct_axes': means['distinct_axes'],
                      'delta': means['distinct_axes']-baseline[split]['per_length_kind_sequence_means'][key]['distinct_axes']}
                for key, means in report[split]['per_length_kind_sequence_means'].items()}
    if output is None:
        if root is not None and train_root is None and test_root is None:
            label = root.name
        elif len(paths) == 1:
            split, path = next(iter(paths.items()))
            label = (path.parent.name if path.name == split else path.name)+'_'+split
        else:
            label = 'composite_'+hashlib.sha256(base.token(report['audited_split_source_paths']).encode()).hexdigest()[:12]
        output = HERE/('diagnostics_'+label+'_audit.json')
    write_diagnostic(output, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path)
    parser.add_argument('--train-root', type=Path, help='Train split folder, or its parent containing train/')
    parser.add_argument('--test-root', type=Path, help='Test split folder, or its parent containing test/')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--diagnose-catalog', action='store_true')
    args = parser.parse_args()
    if args.diagnose_catalog:
        report = catalog_slot_diagnostic()
        output = args.output or HERE/'diagnostics_catalog_single_slots.json'
        write_diagnostic(output, report)
        print(json.dumps({slot: {k: v for k, v in row.items() if k != 'catalog_core_asset_ids'} for slot, row in report['summary'].items()}, ensure_ascii=False))
        return 0
    if not any((args.root, args.train_root, args.test_root)):
        parser.error('--root, --train-root, --test-root, or --diagnose-catalog is required')
    report = audit_compact(args.root, args.output, train_root=args.train_root, test_root=args.test_root)
    print(json.dumps({'passed_hard_checks': report['passed_hard_checks'], 'passed_v5_hard_checks': report['passed_v5_hard_checks'],
        'audited_splits': report['audited_splits'], 'cross_split_disjointness_checked': report['cross_split_disjointness_checked'],
        **{split: {'counts': report[split]['counts'], 'errors': report[split]['error_counts'],
                   'start_camera_max_relative_deviation': report[split]['start_camera_diagnostic']['max_absolute_relative_deviation'],
                   'start_camera_tv': report[split]['start_camera_diagnostic']['total_variation'],
                   'single_slot_tv': report[split]['single_slot_diagnostic']['conditional_actual_vs_expected_total_variation']}
           for split in report['audited_splits']}}, ensure_ascii=False))
    return 0 if report['passed_hard_checks'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
