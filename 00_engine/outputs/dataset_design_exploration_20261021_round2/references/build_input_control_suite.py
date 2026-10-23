"""Create a small counterfactual input suite with existing round-1 GT endpoints."""
from collections import Counter
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
r1 = root.parents[1] / 'dataset_design_exploration_20261021_v1'
pairs = json.loads((root / 'counterfactual_pair_candidates.json').read_text(encoding='utf-8'))
graph = json.loads((r1 / 'graph/main_scene_holdout_hybrid_test_graph.json').read_text(encoding='utf-8'))
sessions = {s['session_id']: s for s in (json.loads(line) for line in
            (r1 / 'graph/main_scene_holdout_hybrid_test_sessions.jsonl').read_text(encoding='utf-8').splitlines())}
nodes = {n['node_id']: n for n in graph['nodes']}
sex = {x['id']: x['sex'] for x in json.loads((r1 / 'graph/topology_inventory_landscape.json').read_text(encoding='utf-8'))['identities']}
chosen = []
counts = Counter()
for pair in pairs['items']:
    if pair['split'] == 'test' and counts[pair['axis']] < 4:
        chosen.append(pair)
        counts[pair['axis']] += 1
items = []
for pnum, pair in enumerate(chosen, 1):
    axis = pair['axis']
    axis_word = {'identity': '人物身份', 'action': '身体动作', 'site': '场景'}[axis]
    target_a = nodes[pair['target_a_node_id']]['state']
    source_a = nodes[pair['source_a_node_id']]['state']
    session = sessions[pair['session_id']]
    history_ids = [graph['nodes'][i]['node_id'] for i in session['node_indices'][:pair['turn']]]
    ref_condition = {'axis': axis, 'target_attribute_id': target_a[axis]}
    if axis in ('action', 'site'):
        ref_condition.update({'camera': source_a['camera'], 'aspect': source_a['aspect'], 'carrier_sex_fit': sex[source_a['identity']]})
    if axis == 'site':
        ref_condition['motion_dependent_camera_rule'] = source_a['action']
    ref_key = hashlib.sha256(json.dumps(ref_condition, sort_keys=True).encode()).hexdigest()
    for branch in ('a', 'b'):
        source_occurrence = pair[f'source_{branch}_occurrence']
        instruction = f'从版本V{source_occurrence}继续，只把{axis_word}改成参考R1展示的{axis_word}；参考R2仅为干扰示例，不采用其中任何属性。其他内容保持。'
        items.append({'case_id': f'pair_{pnum:02d}_{branch}', 'pair_id': f'pair_{pnum:02d}',
                      'public_input': {'history': [{'version_label': f'V{i}', 'video_path': None} for i in range(len(history_ids))],
                                       'instruction': instruction,
                                       'references': [{'label': 'R1', 'media_path': None}, {'label': 'R2', 'media_path': None}]},
                      'input_controls': [
                          {'name': 'full_history_correct_reference', 'same_gt': True, 'reference_order': ['R1', 'R2']},
                          {'name': 'reference_order_permutation_keep_labels', 'same_gt': True, 'reference_order': ['R2', 'R1']},
                          {'name': 'remove_irrelevant_reference_R2', 'same_gt': True, 'reference_order': ['R1'],
                           'instruction_change': 'remove R2-ignore sentence only'},
                          {'name': 'remove_required_source_version', 'scored_as_edit_success': False,
                           'reason': 'Intentional information-deficit diagnostic; do not compare against the same GT as a fair input'}],
                      'private_supervision': {'source_occurrence_gt': source_occurrence,
                                              'source_node_id': pair[f'source_{branch}_node_id'],
                                              'target_node_id': pair[f'target_{branch}_node_id'],
                                              'history_node_ids': history_ids,
                                              'primary_reference_library_key': ref_key,
                                              'primary_reference_condition': ref_condition,
                                              'distractor_reference_condition': {'axis': axis, 'attribute_id': source_a[axis]},
                                              'same_primary_reference_in_pair': True,
                                              'different_preserved_axes_between_pair': pair['different_preserved_axes'],
                                              'no_new_gt_endpoint_required': True},
                      'media_status': 'not_rendered', 'visual_observability_gate': 'pending'})
summary = {'status': 'metadata_certified_input_suite_pending_media_and_visual_validation',
           'pairs': len(chosen), 'base_queries': len(items), 'scored_control_variants_per_query': 3,
           'planned_scored_model_calls': len(items) * 3,
           'diagnostic_information_deficit_calls': len(items),
           'axes': dict(counts), 'new_gt_endpoint_count': 0,
           'unique_existing_target_node_ids': len({x['private_supervision']['target_node_id'] for x in items}),
           'primary_reference_library_keys': len({x['private_supervision']['primary_reference_library_key'] for x in items}),
           'items': items,
           'interpretation': 'Same reference and same history, only source-version pointer changes; correct retained attributes must change. This tests history/source selection beyond reference fidelity.',
           'limitations': ['No input media created', 'Reference-order invariance requires stable labels',
                           'Do not score removal of required history against unchanged GT',
                           'Metadata differences such as identity or hair color need view/visibility validation']}
(root / 'input_control_suite.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: v for k, v in summary.items() if k != 'items'}, ensure_ascii=False))
