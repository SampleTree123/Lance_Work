"""Round-2 offline analyses on pinned round-1 edges. No UE, asset or media reads."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import csv
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROUND1 = OUT.parents[1] / 'dataset_design_exploration_20261021_v1'
PINS = []


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def read(path, lines=False):
    raw = path.read_bytes()
    PINS.append({'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)})
    data = raw.decode('utf-8-sig')
    return [json.loads(x) for x in data.splitlines() if x] if lines else json.loads(data)


inventory = read(ROUND1 / 'graph/topology_inventory_landscape.json')
geometry = read(ROUND1.parent / 'production_workflow_20261017_v1/camera_library/production10/geometry.json')
SEX = {x['id']: x['sex'] for x in inventory['identities']}
CAMERAS = inventory['cameras']


def sector(camera, k):
    """Predeclared semantic buckets, NOT geometric azimuths or validated view coverage."""
    if k == 1:
        return 'canonical_front'
    if k == 2:
        return 'rear' if ('back' in camera or 'rear' in camera) else 'nonrear'
    if k == 4:
        return ('rear' if ('back' in camera or 'rear' in camera) else
                'side' if 'side' in camera else 'elevated' if camera.startswith(('high', 'low')) else 'front')
    if k == 8:
        return ('orbit' if camera.startswith('orbit') else 'dolly' if camera.startswith('dolly') else
                'head' if 'head' in camera else 'upper' if 'upper' in camera else
                'rear' if ('back' in camera or 'rear' in camera) else 'side' if 'side' in camera else
                'elevated' if camera.startswith(('high', 'low')) else 'front')
    return camera


def retained(state, axis):
    return tuple(sorted((k, v) for k, v in state.items() if k != axis))


datasets = {}
all_used = []
for split in ('train', 'test'):
    graph = read(ROUND1 / f'graph/main_scene_holdout_hybrid_{split}_graph.json')
    sessions = read(ROUND1 / f'graph/main_scene_holdout_hybrid_{split}_sessions.jsonl', True)
    nodes = graph['nodes']
    states = [n['state'] for n in nodes]
    used = set()
    for session in sessions:
        for t in range(1, len(session['node_indices'])):
            src = session['node_indices'][session['parent_occurrence_indices_gt'][t]]
            dst = session['node_indices'][t]
            used.add((src, dst, session['edge_axes'][t-1]))
    datasets[split] = (graph, sessions, states, used)
    all_used.extend((split, states[si], states[ti], axis) for si, ti, axis in used)

# Experiment 1: real-edge dedup under reference contracts and planning profiles.
cost_rows = []
for carriers in (1, 2):
    for views in (1, 2, 4, 8, 21):
        for profiles in (1, 2, 4, 8):
            action_keys, site_photo_keys, exact_site_clip_keys = set(), set(), set()
            identity_keys = set()
            action_requests = []
            for split, src, dst, axis in all_used:
                sex = SEX[src['identity']] if carriers == 2 else 'single_neutral_carrier'
                if axis == 'action':
                    base = (dst['action'], sex, sector(src['camera'], views), src['aspect'])
                    action_requests.append(base)
                    # Full coverage of proposed time profiles; these are scenarios,
                    # NOT graph-observed windows/rates (graphs do not contain them).
                    for p in range(profiles):
                        action_keys.add(base + (f'timing_scenario_{p}',))
                elif axis == 'site':
                    site_photo_keys.add((dst['site'], sector(src['camera'], views)))
                    exact_site_clip_keys.add((dst['site'], src['camera'], src['aspect'],
                                              src['action'], SEX[src['identity']]))
                elif axis == 'identity':
                    identity_keys.add(dst['identity'])
            row = {'carrier_count': carriers, 'view_buckets': views, 'timing_profiles_per_key': profiles,
                   'action_clip_count': len(action_keys), 'canonical_scene_photo_count': len(site_photo_keys),
                   'exact_view_trajectory_background_clip_count': len(exact_site_clip_keys),
                   'identity_photo_count': len(identity_keys),
                   'semantic_motion_contract': profiles == 1,
                   'timing_scenario_is_measured': False}
            # Production10 clock is 10 s / 30 fps. Reuse for a planning scenario;
            # not proof every future reference requires or has rendered 300 frames.
            row['planning_action_frames_10s_30fps'] = len(action_keys) * 300
            row['planning_exact_background_frames_10s_30fps'] = len(exact_site_clip_keys) * 300
            cost_rows.append(row)

with (OUT / 'cost_curves.csv').open('w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=list(cost_rows[0]))
    writer.writeheader()
    writer.writerows(cost_rows)

# Experiment 2: metadata upper bound on reference-assisted source shortcuts.
# Experiment 3: mine feasible historical-reference tasks; all target endpoints exist.
leakage = defaultdict(Counter)
task_counts = Counter()
task_sessions = defaultdict(set)
examples = defaultdict(list)
pair_candidates = []
for split, (graph, sessions, states, used) in datasets.items():
    edge_set = {(x['source_index'], x['target_index'], x['axis']) for x in graph['edges']}
    state_index = {canonical(s): i for i, s in enumerate(states)}
    for session in sessions:
        indices = session['node_indices']
        parents = session['parent_occurrence_indices_gt']
        axes = session['edge_axes']
        for t in range(1, len(indices)):
            p = parents[t]
            axis = axes[t-1]
            source, target = states[indices[p]], states[indices[t]]
            ancestors = {p}
            cursor = p
            while cursor > 0:
                cursor = parents[cursor]
                ancestors.add(cursor)
            previous_same_axis = [j for j in range(1, t) if axes[j-1] == axis]
            same_value = [j for j in previous_same_axis if states[indices[j]][axis] == target[axis]]
            abandoned_same_value = [j for j in same_value if j not in ancestors]
            correction = previous_same_axis and states[indices[previous_same_axis[-1]]][axis] != target[axis]
            selected_history = [j for j in range(t) if states[indices[j]][axis] == target[axis]
                                and retained(states[indices[j]], axis) != retained(source, axis)]
            categories = []
            if axis in ('identity', 'action', 'site'):
                if same_value:
                    categories.append('reuse_previously_introduced_reference')
                if abandoned_same_value:
                    categories.append('revive_abandoned_branch_reference')
                if correction:
                    categories.append('correct_prior_reference_choice')
                if selected_history:
                    categories.append('copy_only_one_axis_from_historical_video')
            for category in categories:
                task_counts[(split, category)] += 1
                task_sessions[(split, category)].add(session['session_id'])
                if len(examples[category]) < 6:
                    donor = (abandoned_same_value or same_value or selected_history or previous_same_axis)[-1]
                    examples[category].append({'split': split, 'session_id': session['session_id'], 'turn': t,
                                              'axis': axis, 'source_occurrence_gt': p,
                                              'donor_or_corrected_occurrence': donor,
                                              'history_node_ids': [graph['nodes'][i]['node_id'] for i in indices[:t]],
                                              'target_node_id': graph['nodes'][indices[t]]['node_id'],
                                              'new_target_video_needed': False, 'reference_media_path': None,
                                              'status': 'rewrite_candidate_not_existing_natural_language_annotation'})
            if p == t-1 or axis not in ('identity', 'action', 'site'):
                continue
            unique_candidates = {retained(states[indices[j]], axis): j for j in range(t)}
            for treatment in ('axis_only', 'camera_view', 'camera_motion_fingerprint'):
                def fields(s):
                    if treatment == 'axis_only' or axis == 'identity':
                        return ()
                    keys = ['camera', 'aspect']
                    if treatment == 'camera_motion_fingerprint' and axis == 'site':
                        keys += ['action']
                    return tuple((k, s[k]) for k in keys if k != axis) + (
                        (('sex', SEX[s['identity']]),) if treatment == 'camera_motion_fingerprint' and axis in ('action', 'site') else ())
                eligible = {sig: j for sig, j in unique_candidates.items() if fields(states[indices[j]]) == fields(source)}
                stat = leakage[(split, axis, treatment)]
                stat['branch_requests'] += 1
                stat['candidate_retained_states_before'] += len(unique_candidates)
                stat['candidate_retained_states_after'] += len(eligible)
                stat['unique_source_retained_state_from_reference_metadata'] += len(eligible) == 1
                stat['latest_wrong_state_excluded'] += fields(states[indices[t-1]]) != fields(source)
            # Strong-reference counterfactual pairs: same target-axis and same
            # camera/motion/sex clue, but a different retained source state.
            for candidate_sig, j in unique_candidates.items():
                other = states[indices[j]]
                if candidate_sig == retained(source, axis):
                    continue
                key_fields = ('camera', 'aspect') + (('action',) if axis == 'site' else ())
                if axis != 'identity' and any(other[k] != source[k] for k in key_fields):
                    continue
                if SEX[other['identity']] != SEX[source['identity']]:
                    continue
                alternate_target = {**other, axis: target[axis]}
                ai = state_index.get(canonical(alternate_target))
                if ai is None or (indices[j], ai, axis) not in edge_set:
                    continue
                pair_candidates.append({'split': split, 'session_id': session['session_id'], 'turn': t, 'axis': axis,
                                        'source_a_occurrence': p, 'source_b_occurrence': j,
                                        'source_a_node_id': graph['nodes'][indices[p]]['node_id'],
                                        'source_b_node_id': graph['nodes'][indices[j]]['node_id'],
                                        'target_a_node_id': graph['nodes'][indices[t]]['node_id'],
                                        'target_b_node_id': graph['nodes'][ai]['node_id'],
                                        'different_preserved_axes': [k for k in source if k != axis and source[k] != other[k]],
                                        'same_strong_reference_key_under_projection': True,
                                        'new_target_video_needed': False, 'reference_media_path': None,
                                        'requires_new_source_pointer_instruction': True,
                                        'status': 'metadata_certified_candidate_pending_visual_observability'})
                break

unique_pairs = {}
for pair in pair_candidates:
    signature = (pair['split'], pair['axis'], tuple(sorted([pair['target_a_node_id'], pair['target_b_node_id']])))
    unique_pairs.setdefault(signature, pair)
balanced_pairs = []
pair_example_counts = Counter()
for signature, pair in sorted(unique_pairs.items()):
    group = (pair['split'], pair['axis'])
    if pair_example_counts[group] < 8:
        pair_example_counts[group] += 1
        balanced_pairs.append(pair)
summary = {'generated_at_utc': datetime.now(timezone.utc).isoformat(), 'input_pins': PINS,
           'scope': 'Real round-1 used edges; media-free metadata analyses; no model performance measured',
           'used_unique_edges_by_split': {s: len(d[3]) for s, d in datasets.items()},
           'cost_scenario_rows': len(cost_rows),
           'budget_assumptions': {'view_buckets_are_semantic_not_geometric': True,
                                  'timing_profile_counts_are_scenarios_not_observed': True,
                                  'background_clips_conservative_follow_capable': True,
                                  'union_across_scene_holdout_splits': True},
           'leakage_diagnostics': [{'split': s, 'axis': a, 'treatment': t, **dict(counts)}
                                   for (s, a, t), counts in sorted(leakage.items())],
           'history_reference_task_candidates': [{'split': s, 'task': task, 'turns': n,
                                                  'sessions': len(task_sessions[(s, task)])}
                                                 for (s, task), n in sorted(task_counts.items())],
           'strong_reference_counterfactual_pairs': {'total_requests': len(pair_candidates),
                                                    'unique_unordered_target_pairs': len(unique_pairs),
                                                    'unique_pairs_by_split_axis': dict(Counter(f"{x['split']}:{x['axis']}" for x in unique_pairs.values())),
                                                    'by_split_axis': dict(Counter(f"{x['split']}:{x['axis']}" for x in pair_candidates)),
                                                    'no_new_video_endpoint_required': True},
           'limitations': ['No physical view/visibility or clip timing verified',
                           'Reference metadata decodability is a theoretical shortcut upper potential, not observed image-model leakage',
                           'History task counts are rewrite candidates, not existing annotated reference tasks',
                           'Current graph fixes wardrobe/hair shape; reference-conflict tasks for those axes require new data']}
(OUT / 'analysis_results.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
(OUT / 'history_reference_examples.json').write_text(json.dumps(dict(examples), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
(OUT / 'counterfactual_pair_candidates.json').write_text(json.dumps({'total_requests': len(pair_candidates), 'unique_unordered_target_pairs': len(unique_pairs), 'items': balanced_pairs}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'used_edges': summary['used_unique_edges_by_split'], 'cost_rows': len(cost_rows),
                  'counterfactual_pairs': len(pair_candidates), 'history_task_counts': summary['history_reference_task_candidates']}, ensure_ascii=False))

