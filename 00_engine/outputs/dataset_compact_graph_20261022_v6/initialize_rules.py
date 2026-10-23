"""Record the authorized v6 delta; never mutate the prior experiment."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
source = ROOT.parent / 'dataset_balanced_graph_20261022_v5/RULES.json'
rules = json.loads(source.read_text(encoding='utf-8-sig'))
rules.update(schema_version=6, rule_set_id=ROOT.name,
             status='optimization_in_progress_not_rendered')
rules.pop('actual_implementation', None)
rules['inherited_rule_snapshot'] = str(source)
rules['optimization'] = {
    'baseline': 'dataset_balanced_graph_20261022_v5/candidate_c_seed1',
    'baseline_nodes': {'train': 4670, 'test': 768},
    'started_at': '2026-10-22T00:45:58+08:00',
    'deadline': '2026-10-22T05:45:58+08:00',
    'may_finish_early_when_good_enough': True,
    'start_camera_weights': {'identity_eligible_camera': 1.5, 'other_camera': 1.0},
    'start_camera_quota': 'largest_remainder_over_all_21_catalog_cameras',
    'coverage_starts_consume_camera_quota': True,
    'unsupported_camera_quota_redistribution': False,
    'single_piece_slot_expected': 'uniform over formal eligible source slots per actual single-piece event',
    'global_equal_counts_of_five_slots_required': False,
    'all_five_legal_core_slot_categories_should_have_actual_samples': True,
    'do_not_hide_slot_imbalance_by_restricting_all_sources_to_shirts': True,
    'quality_comparisons': ['actual_used_nodes', 'start_camera_quota',
        'slot_actual_vs_source_conditioned_expected', 'conditional_single_whole_fraction',
        'edge_reuse_by_axis', 'four_use_edge_fraction', 'distinct_axes_by_chain_length',
        'used_and_actually_introduced_value_coverage'],
    'failure_policy': 'preserve experiments and keep the best passing candidate; disclose tradeoffs',
}
(ROOT / 'RULES.json').write_text(json.dumps(rules, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
