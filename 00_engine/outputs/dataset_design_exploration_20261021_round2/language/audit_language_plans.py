"""Validate emitted plans, attach source provenance, and retain rejected examples."""
from collections import Counter
from pathlib import Path
import hashlib
import json
import re

OUT = Path(__file__).resolve().parent
RUN = OUT.parent


def sid(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(raw).hexdigest()[:20]


plans_path = OUT / 'instruction_plans_100.json'
bundle = json.loads(plans_path.read_text(encoding='utf-8'))
contexts = {}
for split in ('train', 'test'):
    graph = json.loads((RUN / f'graph/motif_a7_f5_n3000_s20261021_{split}_uq1_ab3_graph.json').read_text(encoding='utf-8'))
    for line in (RUN / f'graph/motif_a7_f5_n3000_s20261021_{split}_uq1_ab3_sessions.jsonl').read_text(encoding='utf-8').splitlines():
        session = json.loads(line)
        indices, parents, axes = session['node_indices'], session['parent_occurrence_indices_gt'], session['edge_axes']
        for t in range(1, len(indices)):
            source = parents[t]
            if source == t-1:
                continue
            structure = {'split': split, 'history_node_ids': [graph['nodes'][i]['node_id'] for i in indices[:t]],
                         'historical_parent_occurrences': parents[:t], 'current_source': source,
                         'current_target_node_id': graph['nodes'][indices[t]]['node_id'], 'axis': axes[t-1]}
            contexts[sid(structure)] = {'session_id': session['session_id'], 'turn': t, 'structure': structure,
                                       'states': [graph['nodes'][i]['state'] for i in indices[:t+1]]}
axes = {'人物身份': 'identity', '身体动作': 'action', '镜头': 'camera', '场景': 'site', '发色模式': 'hair_color', '该衣物槽': 'garment_slot', '发型': 'hair'}
rejected, rejected_counts, source_positions = [], Counter(), Counter()
predicate_sizes = Counter()
for plan in bundle['plans']:
    context = contexts[plan['interaction_structure_id']]
    structure, states = context['structure'], context['states']
    plan['input_session_id'], plan['fork_turn'] = context['session_id'], context['turn']
    plan['private_supervision']['history_node_ids'] = structure['history_node_ids']
    source = structure['current_source']
    source_positions[f'{plan["split"]}:V{source}'] += 1
    # Public text-only fact reconstruction; no hidden state used to reject unknowns.
    initial = re.fullmatch(r'将原视频里的人命名为(.+)，地点命名为(.+)。', plan['history'][0]['instruction'])
    facts = [{'identity': initial[1], 'site': initial[2]}]
    for entry in plan['history'][1:]:
        m = re.fullmatch(r'从V(\d+)继续，只把(.+?)改为“(.+?)”。', entry['instruction'])
        known = dict(facts[int(m[1])])
        known[axes[m[2]]] = m[3]
        facts.append(known)
    axis, target_value = structure['axis'], states[-1][structure['axis']]
    for variant in plan['variants']:
        assert variant['template_roundtrip_verified']
        candidates = variant['acceptable_source_occurrences']
        assert source in candidates
        assert candidates and all(0 <= j < len(plan['history']) for j in candidates)
        targets = {sid({**states[j], axis: target_value}) for j in candidates}
        assert len(targets) == 1 and sid(states[-1]) in targets
        if variant['type'] == 'attribute_description':
            predicate_sizes[len(variant['ast']['select_source']['predicates'])] += 1
    # Keep actual ambiguous attribute descriptions as rejected training plans.
    for field, value in facts[source].items():
        possible = [j for j, known in enumerate(facts) if field not in known or known[field] == value]
        outputs = {sid({**states[j], axis: target_value}) for j in possible}
        if len(possible) > 1 and len(outputs) > 1 and rejected_counts[plan['split']] < 10:
            rejected_counts[plan['split']] += 1
            rejected.append({'split': plan['split'], 'input_session_id': context['session_id'], 'fork_turn': context['turn'],
                             'predicate': {'field': field, 'value_label': value},
                             'text_source_description': f'{field}是{value}的那个版本',
                             'all_possible_source_occurrences': possible,
                             'unknown_candidates_retained': [j for j in possible if field not in facts[j]],
                             'distinct_output_states_if_applied': len(outputs),
                             'status': 'reject_or_request_more_detail_not_single_oracle_label'})
unique_structure_ids = {p['interaction_structure_id'] for p in bundle['plans']}
summary = {'status': 'planned_template_semantics_validated_not_visual_acceptance',
           'sampled_structures': len(bundle['plans']), 'unique_interaction_structures': len(unique_structure_ids),
           'language_variants': sum(len(p['variants']) for p in bundle['plans']),
           'same_gt_structure_counted_once': True,
           'unique_media_edit_ids': len({p['media_edit_id'] for p in bundle['plans']}),
           'unique_existing_target_nodes': len({p['private_supervision']['target_node_id'] for p in bundle['plans']}),
           'source_position_distribution_in_sample': dict(source_positions),
           'attribute_predicate_count_distribution_in_sample': dict(predicate_sizes),
           'rejected_attribute_examples': len(rejected),
           'all_accepted_candidate_source_sets_produce_the_expected_target_state': True,
           'all_variants_roundtrip_in_supported_chinese_grammar': True}
assert len(bundle['plans']) == len(unique_structure_ids) == 100
plans_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
(OUT / 'plan_audit.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
(OUT / 'rejected_attribute_examples.json').write_text(json.dumps({'items': rejected, 'scope': 'Examples from the sampled main plans under text-only facts; not the full rejection pool'}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
examples = []
selected = [p for p in bundle['plans'] if p['private_supervision']['source_occurrence_gt_for_explicit_event_variants'] > 0][:4]
selected += [p for p in bundle['plans'] if p['private_supervision']['source_occurrence_gt_for_explicit_event_variants'] == 0][:2]
for plan in selected:
    examples.append(f'## {plan["plan_id"]}（{plan["split"]}）\n\n')
    examples.append('以下三句共享一个GT结构，不计为三个编辑样本。人物/场景别名与reference标签须按JSON中的history先展示。\n\n')
    for variant in plan['variants']:
        examples.append(f'- {variant["type"]}：{variant["text"]}\n')
    examples.append('\n')
(OUT / 'CHINESE_TEMPLATE_EXAMPLES.md').write_text('# 100条计划中的中文模板例子\n\n仅为受约束语法模板，不是自由文本理解器；所有媒体路径仍未绑定。\n\n' + ''.join(examples), encoding='utf-8')
print(json.dumps(summary, ensure_ascii=False))
