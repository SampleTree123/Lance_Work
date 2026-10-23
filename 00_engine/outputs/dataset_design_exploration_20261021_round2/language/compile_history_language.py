"""Deterministic history-reference language planner; no LLM, media or UE access.

Three-valued predicates keep unknown historical facts as possible matches.
Text facts are explicit planned context, not claimed existing annotations.
"""
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
import argparse
import hashlib
import json
import re

OUT = Path(__file__).resolve().parent
RUN = OUT.parent
OLD = RUN.parent / 'dataset_design_exploration_20261021_v1'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--dataset', choices=['round1', 'round2_main'], default='round2_main')
parser.add_argument('--sample-per-split', type=int, default=50)
args = parser.parse_args()
PREFIX = 'round1_' if args.dataset == 'round1' else ''
FIELDS = ('camera', 'action', 'hair_color', 'identity', 'site') + (() if args.dataset == 'round1' else ('garment_slot', 'hair'))
PHYSICAL = ('camera', 'action', 'hair_color')
AXIS_ZH = {'identity': '人物身份', 'action': '身体动作', 'camera': '镜头', 'site': '场景', 'hair_color': '发色模式', 'garment_slot': '该衣物槽', 'hair': '发型'}
PINS = []


def dump(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def shortid(value):
    return hashlib.sha256(dump(value).encode()).hexdigest()[:20]


def read(path, lines=False):
    raw = path.read_bytes()
    PINS.append({'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)})
    text = raw.decode('utf-8-sig')
    return [json.loads(line) for line in text.splitlines() if line] if lines else json.loads(text)


inventory = read(OLD / 'graph/topology_inventory_landscape.json')
geometry = read(OLD.parent / 'production_workflow_20261017_v1/camera_library/production10/geometry.json')
observability = read(RUN / 'observability/camera_observability.json')
shot_map = {(s['action'], s['camera'], s['aspect']): s for s in observability['shots']}
identity_labels = {x: f'人物P{i+1:02d}' for i, x in enumerate(sorted(x['id'] for x in inventory['identities']))}
action_labels = {x['motion_id']: x['motion_label'] for x in geometry['actions']}
camera_labels = {x['camera_id']: x['camera_label'] for x in geometry['shots']}
site_values = set()
DATA = {}
for split in ('train', 'test'):
    graph_path = (OLD / f'graph/main_scene_holdout_hybrid_{split}_graph.json' if args.dataset == 'round1' else
                  RUN / f'graph/motif_a7_f5_n3000_s20261021_{split}_uq1_ab3_graph.json')
    session_path = (OLD / f'graph/main_scene_holdout_hybrid_{split}_sessions.jsonl' if args.dataset == 'round1' else
                    RUN / f'graph/motif_a7_f5_n3000_s20261021_{split}_uq1_ab3_sessions.jsonl')
    graph = read(graph_path)
    sessions = read(session_path, True)
    DATA[split] = graph, sessions
    site_values.update(n['state']['site'] for n in graph['nodes'])
site_labels = {x: f'场景S{i+1:02d}' for i, x in enumerate(sorted(site_values))}
color_labels = {'original': '原始配色模式', 'black': '黑色', 'gold': '金色', 'silver_white': '银白色', 'red': '红色', 'blue': '蓝色', 'pink': '粉色'}
LABELS = {'identity': identity_labels, 'action': action_labels, 'camera': camera_labels, 'site': site_labels, 'hair_color': color_labels}
for field, prefix in [('garment_slot', '衣物参考G'), ('hair', '发型参考H')]:
    values = sorted({n['state'][field] for graph, _ in DATA.values() for n in graph['nodes'] if field in n['state']})
    LABELS[field] = {value: ('无发型状态' if field == 'hair' and value == 'none' else f'{prefix}{i+1:02d}') for i, value in enumerate(values)}


def verbal(field, value):
    return LABELS[field].get(value, value)


def condition(field, value, negate=False):
    return {'field': field, 'verbal_value': verbal(field, value), 'operator': 'not_equal' if negate else 'equal'}


def state_signature(state):
    return dump(state)


def apply_patch(state, axis, target_value):
    return {**state, axis: target_value}


def text_facts(states, parents, axes, initial):
    """Facts follow the explicitly stated historical source pointer, including forks."""
    facts = [{field: states[0][field] for field in initial}]
    for j in range(1, len(states)):
        known = dict(facts[parents[j]])
        known[axes[j-1]] = states[j][axes[j-1]]
        facts.append(known)
    return facts


def visual_support(state, field, target_verbal_value, introduced_values):
    shot = shot_map.get((state['action'], state['camera'], state['aspect']))
    if not shot:
        return False
    if field == 'camera':
        return True  # Declared planned-shot classification proxy, not a pixel verdict.
    if field == 'hair_color':
        return (state.get('hair') != 'none' and target_verbal_value != color_labels['original'] and
                shot['head_projected_height_px']['median'] >= 64 and
                shot['head_fraction_with_half_box_in_frame'] >= .5)
    if field == 'action':
        return (not shot['flags']['torso_proxy_never_intersects_sparse_samples'] and
                not shot['flags']['lower_proxy_never_intersects_sparse_samples'] and
                shot['feet_fraction_intersecting_frame'] >= .5)
    if field == 'identity':
        return (target_verbal_value in introduced_values['identity'] and
                shot['identity_proxy_threshold_sweep']['64'] > 0)
    return False  # No scene pixel/geometry verification; labels alone are not evidence.


def resolve_attributes(predicates, states, facts, introduced, mode):
    possible, definite, evidence = [], [], {}
    for j, state in enumerate(states):
        outcomes, bases = [], []
        for pred in predicates:
            field, value = pred['field'], pred['verbal_value']
            if mode == 'oracle':
                basis, truth = 'private_metadata_oracle_upper_bound', verbal(field, state[field]) == value
            elif field in facts[j]:
                basis, truth = 'explicit_text_history', verbal(field, facts[j][field]) == value
            elif mode.endswith('plus_proxy') and visual_support(state, field, value, introduced):
                basis, truth = 'visual_geometry_proxy_pending_pixel_validation', verbal(field, state[field]) == value
            else:
                basis, truth = 'unknown', None
            if truth is not None and pred['operator'] == 'not_equal':
                truth = not truth
            outcomes.append(truth)
            bases.append(basis)
        if False not in outcomes:
            possible.append(j)
        if all(x is True for x in outcomes):
            definite.append(j)
        evidence[str(j)] = bases
    return {'possible_source_occurrences': possible, 'definite_source_occurrences': definite, 'evidence_by_occurrence': evidence}


def classify(result, source, states, axis, target_value):
    possible, definite = result['possible_source_occurrences'], result['definite_source_occurrences']
    if source not in definite:
        return 'source_not_grounded'
    if len(possible) == 1:
        return 'unique_source'
    targets = {state_signature(apply_patch(states[j], axis, target_value)) for j in possible}
    return 'multiple_sources_output_equivalent' if len(targets) == 1 else 'ambiguous_different_outputs'


def attribute_phrase(predicates):
    parts = []
    for pred in predicates:
        neg = '不是' if pred['operator'] == 'not_equal' else '是'
        field, value = pred['field'], pred['verbal_value']
        if field == 'camera':
            parts.append(f'镜头{neg}“{value}”')
        elif field == 'action':
            parts.append(f'动作{neg}“{value}”')
        elif field == 'hair_color':
            parts.append(f'发色{neg}{value}')
        else:
            parts.append(f'{AXIS_ZH[field]}{neg}{value}')
    return '、'.join(parts) + '的那个版本'


def resolve_event(ast, states, axes):
    if ast['operator'] == 'initial_version':
        return [0]
    eligible = [j for j in range(1, len(states)) if axes[j-1] == ast['axis']]
    if ast.get('new_verbal_value') is not None:
        eligible = [j for j in eligible if verbal(ast['axis'], states[j][ast['axis']]) == ast['new_verbal_value']]
    if ast.get('ordinal') is not None:
        n = ast['ordinal']
        return [eligible[n-1]] if 1 <= n <= len(eligible) else []
    return eligible


def compile_event(source, states, axes):
    if source == 0:
        return {'operator': 'initial_version'}, '最开始的原视频', [0]
    axis = axes[source-1]
    for ast, phrase in [({'operator': 'after_edit_event', 'axis': axis}, f'修改{AXIS_ZH[axis]}后的版本'),
                        ({'operator': 'after_edit_event', 'axis': axis, 'new_verbal_value': verbal(axis, states[source][axis])},
                         f'把{AXIS_ZH[axis]}改为“{verbal(axis, states[source][axis])}”后的版本')]:
        matches = resolve_event(ast, states, axes)
        if matches == [source]:
            return ast, phrase, matches
    matches = resolve_event({'operator': 'after_edit_event', 'axis': axis}, states, axes)
    ordinal = matches.index(source) + 1
    ast = {'operator': 'after_edit_event', 'axis': axis, 'ordinal': ordinal}
    return ast, f'第{ordinal}次修改{AXIS_ZH[axis]}后的版本', resolve_event(ast, states, axes)


def parse_planned_instruction(text):
    """Parse this compiler's restricted Chinese grammar, never arbitrary prose."""
    edit_match = re.search(r'只把(.+?)改为“(.+?)”，其他内容保持。$', text)
    if not edit_match:
        raise ValueError('Outside supported edit grammar')
    axis = next(k for k, zh in AXIS_ZH.items() if zh == edit_match[1])
    lead = text[:edit_match.start()]
    version = re.fullmatch(r'从V(\d+)继续，', lead)
    if version:
        source_ast = {'operator': 'version', 'value': f'V{version[1]}'}
    elif lead.startswith('回到') and lead.endswith('的那个版本，'):
        terms = lead[2:-len('的那个版本，')].split('、')
        predicates = []
        for term in terms:
            name, op, value = re.fullmatch(r'(.+?)(不是|是)(.+)', term).groups()
            field = {'动作': 'action', '发色': 'hair_color'}.get(name)
            if field is None:
                field = next(k for k, zh in AXIS_ZH.items() if zh == name)
            predicates.append({'field': field, 'verbal_value': value.strip('“”'),
                               'operator': 'not_equal' if op == '不是' else 'equal'})
        source_ast = {'operator': 'conjunction', 'predicates': predicates}
    elif lead == '从最开始的原视频继续，':
        source_ast = {'operator': 'initial_version'}
    else:
        event_value = re.fullmatch(r'从把(.+?)改为“(.+?)”后的版本继续，', lead)
        event_ordinal = re.fullmatch(r'从第(\d+)次修改(.+?)后的版本继续，', lead)
        event_axis = re.fullmatch(r'从修改(.+?)后的版本继续，', lead)
        if event_value:
            source_ast = {'operator': 'after_edit_event', 'axis': next(k for k, zh in AXIS_ZH.items() if zh == event_value[1]),
                          'new_verbal_value': event_value[2]}
        elif event_ordinal:
            source_ast = {'operator': 'after_edit_event', 'axis': next(k for k, zh in AXIS_ZH.items() if zh == event_ordinal[2]),
                          'ordinal': int(event_ordinal[1])}
        elif event_axis:
            source_ast = {'operator': 'after_edit_event', 'axis': next(k for k, zh in AXIS_ZH.items() if zh == event_axis[1])}
        else:
            raise ValueError('Outside supported source grammar')
    return {'select_source': source_ast, 'edit': {'axis': axis, 'target_public_label': edit_match[2]}}


POLICIES = {
    'oracle': (FIELDS, 'oracle'),
    'target_only_text': ((), 'text'),
    'target_text_plus_proxy': ((), 'text_plus_proxy'),
    'named_identity_site_text': (('identity', 'site'), 'text'),
    'named_identity_site_plus_proxy': (('identity', 'site'), 'text_plus_proxy'),
    'full_initial_caption_text': (FIELDS, 'text')
}
stats = defaultdict(Counter)
forks = []
event_counts = Counter()
unknown_visible_text = Counter()
negation_examples = []
semantic_contrasts = []
for split, (graph, sessions) in DATA.items():
    for session in sessions:
        ids, parents, axes = session['node_indices'], session['parent_occurrence_indices_gt'], session['edge_axes']
        states_all = [graph['nodes'][i]['state'] for i in ids]
        for t in range(1, len(ids)):
            source = parents[t]
            if source == t-1:
                continue
            states, axis, target_value = states_all[:t], axes[t-1], states_all[t][axes[t-1]]
            introduced = defaultdict(set)
            for j in range(1, t):
                introduced[axes[j-1]].add(verbal(axes[j-1], states[j][axes[j-1]]))
            facts_by_policy = {p: text_facts(states, parents[:t], axes[:t-1], init) for p, (init, _) in POLICIES.items()}
            found_default = []
            policy_best = {}
            for universe, fields in [('all_available_attributes', FIELDS), ('physical_attributes_only', PHYSICAL)]:
                for policy, (initial, mode) in POLICIES.items():
                    facts = facts_by_policy[policy]
                    best = None
                    for size in (1, 2, 3):
                        classes = Counter()
                        valid = []
                        for subset in combinations(fields, size):
                            predicates = [condition(field, states[source][field]) for field in subset]
                            result = resolve_attributes(predicates, states, facts, introduced, mode)
                            status = classify(result, source, states, axis, target_value)
                            classes[status] += 1
                            if status in ('unique_source', 'multiple_sources_output_equivalent'):
                                valid.append((predicates, result, status))
                        group = stats[(split, universe, policy, size)]
                        group['forks'] += 1
                        group['has_unique_source_description'] += classes['unique_source'] > 0
                        group['has_valid_output_equivalent_description'] += classes['multiple_sources_output_equivalent'] > 0
                        group['has_usable_description'] += bool(valid)
                        group['candidate_descriptions'] += sum(classes.values())
                        for key, value in classes.items():
                            group[f'description_status:{key}'] += value
                        if valid and best is None:
                            best = (size, valid[0])
                        if universe == 'all_available_attributes' and policy == 'named_identity_site_plus_proxy' and valid and not found_default:
                            found_default = [valid[0]]
                    policy_best[(universe, policy)] = best
            event_ast, event_phrase, event_matches = compile_event(source, states, axes[:t-1])
            if event_matches != [source]:
                raise AssertionError('Event compilation did not resolve intended occurrence')
            event_counts[(split, event_ast['operator'], 'ordinal' in event_ast)] += 1
            default_facts = facts_by_policy['named_identity_site_plus_proxy']
            for field in FIELDS:
                if field in default_facts[source] and not visual_support(states[source], field, verbal(field, states[source][field]), introduced):
                    unknown_visible_text[(split, field)] += 1
            if found_default:
                preds, resolved, status = found_default[0]
                structure = {'split': split, 'history_node_ids': [graph['nodes'][i]['node_id'] for i in ids[:t]],
                             'historical_parent_occurrences': parents[:t], 'current_source': source,
                             'current_target_node_id': graph['nodes'][ids[t]]['node_id'], 'axis': axis}
                forks.append({'split': split, 'session_id': session['session_id'], 'turn': t, 'source': source,
                              'states': states, 'target': states_all[t], 'graph': graph,
                              'indices': ids, 'parents': parents, 'axes': axes, 'structure': structure,
                              'interaction_structure_id': shortid(structure),
                              'media_edit_id': shortid((split, ids[source], ids[t], axis)),
                              'predicates': preds, 'resolved': resolved, 'status': status,
                              'event_ast': event_ast, 'event_phrase': event_phrase})
            # Negation is a set complement, not an instruction to select the oracle source.
            if len(negation_examples) < 12:
                neg = {'operator': 'exclude_versions', 'version_labels': [f'V{t-1}']}
                matches = list(range(t-1))
                if len(matches) > 1:
                    negation_examples.append({'split': split, 'session_id': session['session_id'], 'turn': t,
                                              'text': f'不要最后展示的V{t-1}，从之前的版本继续。', 'ast': neg,
                                              'matching_occurrences': matches,
                                              'status': 'ambiguous_unless_all_result_states_equivalent'})
            # Restore a slot on latest versus select an earlier whole version.
            if len(semantic_contrasts) < 12 and source != t-1:
                prior_axis = axes[source-1] if source else 'hair_color'
                restored = apply_patch(states[-1], prior_axis, states[source][prior_axis])
                if restored != states[source]:
                    semantic_contrasts.append({'split': split, 'session_id': session['session_id'], 'turn': t,
                        'select_source': {'ast': {'operator': 'select_source', 'version': f'V{source}'},
                                          'state': states[source], 'text': f'回到V{source}继续。'},
                        'restore_attribute_on_latest': {'ast': {'operator': 'patch_current_state', 'axis': prior_axis,
                                                                'value_from_version': f'V{source}'}, 'state': restored,
                                                       'text': f'留在V{t-1}，只把{AXIS_ZH[prior_axis]}恢复成V{source}的值。'},
                        'different_outputs': True, 'other_latest_edits_survive_only_in_restore_case': True,
                        'new_gt_endpoint_for_restore_not_assumed': True})

# Deterministic balanced 100 interaction structures, each has three language variants.
chosen, per_group, seen_structures = [], Counter(), set()
for fork in sorted(forks, key=lambda f: shortid((f['session_id'], f['turn']))):
    group = fork['split']
    quota = args.sample_per_split
    if per_group[group] < quota and fork['interaction_structure_id'] not in seen_structures:
        chosen.append(fork)
        per_group[group] += 1
        seen_structures.add(fork['interaction_structure_id'])
plans = []
for n, fork in enumerate(chosen, 1):
    source, t, axis, graph, ids = fork['source'], fork['turn'], fork['axes'][fork['turn']-1], fork['graph'], fork['indices']
    target_value = fork['target'][axis]
    suffix = f'只把{AXIS_ZH[axis]}改为“{verbal(axis, target_value)}”，其他内容保持。'
    source_description = attribute_phrase(fork['predicates'])
    current_states = fork['states']
    context = [{'version_label': 'V0', 'instruction': f'将原视频里的人命名为{verbal("identity", current_states[0]["identity"])}，地点命名为{verbal("site", current_states[0]["site"])}。', 'video_path': None}]
    for j in range(1, t):
        past_axis = fork['axes'][j-1]
        entry = {'version_label': f'V{j}', 'instruction': f'从V{fork["parents"][j]}继续，只把{AXIS_ZH[past_axis]}改为“{verbal(past_axis, current_states[j][past_axis])}”。', 'video_path': None}
        if past_axis in ('identity', 'action', 'site', 'hair', 'garment_slot'):
            entry['reference_plan'] = {'public_label': verbal(past_axis, current_states[j][past_axis]), 'axis': past_axis, 'media_path': None, 'contract': 'supply_the_labeled_reference_before_using_its_alias'}
        context.append(entry)
    variants = [
        {'type': 'explicit_version', 'text': f'从V{source}继续，{suffix}',
         'ast': {'select_source': {'operator': 'version', 'value': f'V{source}'}, 'edit_axis': axis},
         'acceptable_source_occurrences': [source], 'evidence': ['public_version_labels']},
        {'type': 'attribute_description', 'text': f'回到{source_description}，{suffix}',
         'ast': {'select_source': {'operator': 'conjunction', 'predicates': fork['predicates']}, 'edit_axis': axis},
         'acceptable_source_occurrences': fork['resolved']['possible_source_occurrences'],
         'resolution_status': fork['status'], 'evidence': fork['resolved']['evidence_by_occurrence']},
        {'type': 'operation_event', 'text': f'从{fork["event_phrase"]}继续，{suffix}',
         'ast': {'select_source': fork['event_ast'], 'edit_axis': axis},
         'acceptable_source_occurrences': [source], 'evidence': ['explicit_historical_edit_events']}
    ]
    for index, variant in enumerate(variants):
        variant['variant_id'] = f'{fork["interaction_structure_id"]}:v{index}'
        variant['ast']['edit'] = {'axis': axis, 'target_public_label': verbal(axis, target_value)}
        parsed = parse_planned_instruction(variant['text'])
        expected = {k: v for k, v in variant['ast'].items() if k != 'edit_axis'}
        if parsed != expected:
            raise AssertionError(f'Constrained grammar roundtrip mismatch: {variant["text"]}')
        variant['template_roundtrip_verified'] = True
    plans.append({'plan_id': f'language_plan_{n:03d}', 'split': fork['split'],
                  'input_session_id': fork['session_id'], 'fork_turn': t,
                  'interaction_structure_id': fork['interaction_structure_id'], 'media_edit_id': fork['media_edit_id'],
                  'context_policy': 'planned_initial_identity_site_aliases_then_explicit_prior_targets',
                  'history': context, 'variants': variants,
                  'current_target_reference_plan': ({'public_label': verbal(axis, target_value), 'axis': axis, 'media_path': None, 'contract': 'resolve_media_via_separate_reference_contract'} if axis in ('identity', 'action', 'site', 'hair', 'garment_slot') else None),
                  'private_supervision': {'source_occurrence_gt_for_explicit_event_variants': source,
                      'history_node_ids': [graph['nodes'][i]['node_id'] for i in ids[:t]],
                      'target_node_id': graph['nodes'][ids[t]]['node_id'], 'target_value': target_value,
                      'source_node_ids_for_attribute_variant': [graph['nodes'][ids[j]]['node_id'] for j in fork['resolved']['possible_source_occurrences']],
                      'attribute_variant_may_have_equivalent_source_labels': fork['status'] == 'multiple_sources_output_equivalent'},
                  'not_new_media_or_new_interaction_structures_per_language_variant': True,
                  'status': 'offline_template_plan_visual_proxy_not_pixel_accepted'})

result = {'status': 'deterministic_three_valued_resolution_of_planned_context', 'dataset': args.dataset, 'input_pins': PINS,
          'editable_attribute_fields': list(FIELDS),
          'policies': {p: {'initial_text_fields': list(init), 'resolver_mode': mode} for p, (init, mode) in POLICIES.items()},
          'attribute_statistics': [{'split': s, 'predicate_universe': u, 'policy': p, 'exact_predicate_count': k, **dict(v)}
                                   for (s, u, p, k), v in sorted(stats.items())],
          'usable_default_fork_candidates': len(forks),
          'text_known_while_visual_proxy_unsupported_at_correct_source': [{'split': s, 'field': f, 'forks': c} for (s, f), c in sorted(unknown_visible_text.items())],
          'event_statistics': [{'split': s, 'operator': op, 'ordinal_needed': ordinal, 'forks': c} for (s, op, ordinal), c in sorted(event_counts.items())],
          'sampled_plans': len(plans), 'language_variants': sum(len(p['variants']) for p in plans),
          'unique_interaction_structure_ids_in_sample': len({p['interaction_structure_id'] for p in plans}),
          'unique_media_edit_ids_in_sample': len({p['media_edit_id'] for p in plans}),
          'sample_split_counts': dict(per_group),
          'template_roundtrip_verified_variants': sum(v.get('template_roundtrip_verified', False) for p in plans for v in p['variants']),
          'limitations': ['Explicit prior instructions and initial aliases are this compiler proposed context, not existing natural-language annotation',
                         'Visual support uses representative sparse geometry; it does not establish pixel observability',
                         'Unknown candidates are retained as possible matches',
                         'Full initial caption can make reference resolution textual; this is declared as a separate input regime',
                         'Identity/site aliases must be publicly introduced; private asset IDs are never presumed understood',
                         'Fixed aspect is omitted as an uninformative source predicate']}
(OUT / f'{PREFIX}resolver_results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
if plans:
    (OUT / f'{PREFIX}instruction_plans_100.json').write_text(json.dumps({'status': result['status'], 'dataset': args.dataset, 'count': len(plans), 'plans': plans}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
(OUT / f'{PREFIX}semantic_distinctions_examples.json').write_text(json.dumps({'negation': negation_examples, 'restore_attribute_vs_select_source': semantic_contrasts,
                 'typed_correction_examples': [
                     {'text': '不是从V4，改从V1继续。', 'ast_type': 'correct_source_selection'},
                     {'text': '仍从V4继续，发色不要红色，改金色。', 'ast_type': 'correct_target_attribute'},
                     {'text': '回到V1。', 'ast_type': 'select_whole_historical_source'},
                     {'text': '留在V4，只把发色恢复成V1的值。', 'ast_type': 'patch_one_attribute_on_current_source'}]}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: result[k] for k in ('usable_default_fork_candidates', 'sampled_plans', 'language_variants', 'unique_interaction_structure_ids_in_sample', 'unique_media_edit_ids_in_sample', 'sample_split_counts')}, ensure_ascii=False))

