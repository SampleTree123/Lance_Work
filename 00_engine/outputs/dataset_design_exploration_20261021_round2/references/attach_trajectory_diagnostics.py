"""Continue round-2 with root's real trajectory diagnostics; writes references only."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

out = Path(__file__).resolve().parent
r2 = out.parent
r1 = r2.parent / 'dataset_design_exploration_20261021_v1'


def read_pin(path):
    raw = path.read_bytes()
    return json.loads(raw.decode('utf-8-sig')), {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest()}


obs, obs_pin = read_pin(r2 / 'observability/camera_observability.json')
suite, suite_pin = read_pin(out / 'input_control_suite.json')
shots = {(s['action'], s['camera'], s['aspect']): s for s in obs['shots']}
nodes = {}
sex = {x['id']: x['sex'] for x in json.loads((r1 / 'graph/topology_inventory_landscape.json').read_text(encoding='utf-8'))['identities']}
site_keys_fit, site_keys_trajectory = set(), set()
site_coverage = Counter()
graph_pins = []
for split in ('train', 'test'):
    graph, pin = read_pin(r1 / f'graph/main_scene_holdout_hybrid_{split}_graph.json')
    graph_pins.append(pin)
    sessions = [json.loads(line) for line in (r1 / f'graph/main_scene_holdout_hybrid_{split}_sessions.jsonl').read_text(encoding='utf-8').splitlines()]
    states = [n['state'] for n in graph['nodes']]
    nodes.update({n['node_id']: n['state'] for n in graph['nodes']})
    used = {(s['node_indices'][s['parent_occurrence_indices_gt'][t]], s['node_indices'][t], s['edge_axes'][t-1])
            for s in sessions for t in range(1, len(s['node_indices']))}
    for si, ti, axis in used:
        if axis != 'site':
            continue
        src, dst = states[si], states[ti]
        shot = shots.get((src['action'], src['camera'], src['aspect']))
        if shot is None:
            site_coverage['unmatched_unique_edges'] += 1
            continue
        site_coverage['matched_unique_edges'] += 1
        site_keys_fit.add((dst['site'], src['action'], sex[src['identity']], src['camera'], src['aspect']))
        site_keys_trajectory.add((dst['site'], shot['trajectory_sha256']))

items = []
summary = Counter()
for item in suite['items']:
    private = item['private_supervision']
    target = nodes[private['target_node_id']]
    shot = shots.get((target['action'], target['camera'], target['aspect']))
    if not shot:
        summary['unmatched_queries'] += 1
        continue
    axis = private['primary_reference_condition']['axis']
    med = shot['head_projected_height_px']['median']
    identity_fraction = shot['identity_proxy_threshold_sweep']['64']
    face_candidate = identity_fraction > 0
    body_candidate = not shot['flags']['torso_proxy_never_intersects_sparse_samples'] and not shot['flags']['lower_proxy_never_intersects_sparse_samples']
    hair_candidate = med >= 64 and shot['head_fraction_with_half_box_in_frame'] >= .5
    preserve = private['different_preserved_axes_between_pair']
    evidence = {field: ('proxy_supports_review' if (
                        (field == 'identity' and face_candidate) or
                        (field == 'hair_color' and hair_candidate) or
                        (field == 'action' and body_candidate) or field in ('site', 'camera'))
                       else 'weak_or_unchecked_proxy') for field in preserve}
    edited_axis_evidence = ('weak_identity_front_proxy' if axis == 'identity' and not face_candidate else
                            'weak_body_coverage_proxy' if axis == 'action' and not body_candidate else
                            'candidate_only_not_visual_acceptance')
    priority = ('review_first' if not edited_axis_evidence.startswith('weak') and any(v == 'proxy_supports_review' for v in evidence.values())
                else 'review_after_better_framed_candidates')
    summary[priority] += 1
    summary[f'{axis}:{priority}'] += 1
    items.append({'case_id': item['case_id'], 'pair_id': item['pair_id'], 'axis': axis,
                  'target_node_id': private['target_node_id'], 'shot_id': shot['shot_id'],
                  'planner_representative_sex': shot['planner_representative_sex'],
                  'target_identity_sex': sex[target['identity']],
                  'head_median_px': med, 'identity_front_64px_fraction': identity_fraction,
                  'head_half_box_in_frame_fraction': shot['head_fraction_with_half_box_in_frame'],
                  'preserved_difference_proxy': evidence, 'edited_axis_evidence': edited_axis_evidence,
                  'review_priority': priority, 'not_an_acceptance_gate': True})

result = {'status': 'offline_planning_sensitivity_not_final_reference_budget', 'input_pins': [obs_pin, suite_pin] + graph_pins,
          'formal_shot_count': obs['shot_count'], 'approximately_static_count': obs['approx_static_count'],
          'conservative_motion_sex_camera_site_reference_clips': len(site_keys_fit),
          'representative_trajectory_hash_site_reference_clips': len(site_keys_trajectory),
          'possible_reduction_if_all_sexes_share_same_resolved_camera_path': len(site_keys_fit) - len(site_keys_trajectory),
          'coverage': dict(site_coverage),
          'interpretation': 'Trajectory dedup can supersede sex labels only if actual identity/sex adaptation uses the same numeric camera path; current planner representatives do not prove that.',
          'limitations': obs['limitations'] + ['Site ground-follow and exposure remain unresolved in these topology-only keys',
                                             'No reference or output pixel inspected',
                                             'Hash-equal paths are planned path equality, not proof of identical rendered backgrounds']}
(out / 'trajectory_reference_budget.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
(out / 'suite_observability.json').write_text(json.dumps({'status': 'review_priority_only_not_visual_acceptance',
                     'input_pins': [obs_pin, suite_pin], 'summary': dict(summary), 'items': items,
                     'limitations': obs['limitations']}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'trajectory_reference_budget': result, 'suite_review_priorities': dict(summary)}, ensure_ascii=False))
