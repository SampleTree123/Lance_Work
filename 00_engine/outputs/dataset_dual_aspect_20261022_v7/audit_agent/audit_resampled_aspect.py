"""Independent audit for the new-session v7 resampling alternative.

Reuse immutable v5 pure semantic checks, while disclosing the waived old video
budget. Add v6 state/edge projection, aspect-agnostic uniqueness, and v6 target
coverage checks. No sampler, metrics, or RESULT claims are trusted as evidence.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import importlib.util
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
from audit_dual_aspect import BASELINE, HERE, OUTPUTS, RULES_SOURCE, pin, read, sessions, token, without_aspect


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--train-root', type=Path, default=HERE.parent/'resample_agent/train_4200_component_split')
    parser.add_argument('--test-root', type=Path, default=HERE.parent/'resample_agent/test_1100')
    parser.add_argument('--output', type=Path, default=HERE/'resampled_independent_audit.json')
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location('_v5_resampled_independent_semantics', RULES_SOURCE)
    base = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(base)
    compact_path = OUTPUTS/'dataset_compact_graph_20261022_v6/audit_compact.py'
    compact_spec = importlib.util.spec_from_file_location('_v6_resampled_slot_diagnostics', compact_path)
    compact = importlib.util.module_from_spec(compact_spec)
    compact_spec.loader.exec_module(compact)
    rules = base.Rules()
    report = {'schema': 'independent_dual_aspect_resampled_audit_v1',
              'scope': 'Offline new-session candidate; not a preservation of original v6 sessions; no media generated',
              'original_node_budget_is_informational_after_user_relaxation': True,
              'independent_semantic_check_source': pin(RULES_SOURCE), 'audit_source': pin(__file__),
              'inputs': [], 'splits': {}}
    noaspect_keys, noaspect_chains = {}, {}
    for split, root in [('train', args.train_root.resolve()), ('test', args.test_root.resolve())]:
        result, _, _ = base.audit_split(root, split, rules)
        rows, edges, ss = read(root/'nodes.json'), read(root/'edges.json'), sessions(root/'sessions.jsonl')
        state = {r['id']: r['state'] for r in rows}
        old = {r['id']: r['state'] for r in read(BASELINE/split/'nodes.json')}
        origins = read(root/'ORIGIN.json')
        origin = {r['id']: r for r in origins}
        errors, counts = [], Counter()

        def fail(kind, detail):
            counts[kind] += 1
            if len(errors) < 100:
                errors.append({'kind': kind, 'detail': detail})

        if len(origin) != len(origins) or set(origin) != set(state):
            fail('origin_ids_not_exactly_nodes', split)
        for nid, s in state.items():
            o = origin.get(nid, {})
            original = old.get(o.get('source_id'))
            if original is None or without_aspect(s) != without_aspect(original) or o.get('aspect') != s['aspect']:
                fail('v6_nonaspect_state_projection_invalid', nid)
        oldedge = {token(e) for e in read(BASELINE/split/'edges.json')}
        for e in edges:
            projected = {**e, 'source': origin[e['source']]['source_id'], 'target': origin[e['target']]['source_id']}
            if token(projected) not in oldedge:
                fail('edge_not_a_v6_projection', e)
        used = set()
        keys, projected_signatures = set(), set()
        first_signature_session, duplicate_pairs = {}, []
        aspect_sessions, aspect_axes, aspect_starts, aspect_nodeuse = Counter(), {}, {}, {}
        canonical_edge_use = Counter()
        fork_parents = Counter()
        for s in state.values():
            c = rules.canonical(s)
            keys.add(token((c[0], *c[2:])))
        for session in ss:
            history, steps = session['history'], session['steps']
            used.update(history)
            aspects = {state[n]['aspect'] for n in history}
            if len(aspects) != 1:
                fail('mixed_aspect_session', session['id'])
            aspect = state[history[0]]['aspect']
            aspect_sessions[aspect] += 1
            aspect_axes.setdefault(aspect, Counter()).update(st['axis'] for st in steps)
            aspect_starts.setdefault(aspect, Counter())[state[history[0]]['camera']] += 1
            aspect_nodeuse.setdefault(aspect, set()).update(history)
            canonical_history = [rules.canonical({**state[n], 'aspect': 'landscape'}) for n in history]
            signature = token((canonical_history[0], [(st['source_position'], canonical_history[j]) for j, st in enumerate(steps, 1)]))
            if signature in projected_signatures:
                fail('duplicate_structural_chain_ignoring_aspect', session['id'])
                duplicate_pairs.append([first_signature_session[signature], session['id']])
            else:
                first_signature_session[signature] = session['id']
            projected_signatures.add(signature)
            for round_no, st in enumerate(steps, 1):
                u, v = st['source'], st['target']
                canonical_edge_use[token((rules.canonical(state[u]), rules.canonical(state[v])))] += 1
                if st['source_position'] < round_no-1:
                    fork_parents[f"L{session['length']}:t{round_no}:p{st['source_position']}"] += 1
        if max(canonical_edge_use.values(), default=0) > 4:
            fail('canonical_directed_edge_cap4', max(canonical_edge_use.values()))
        if split == 'train':
            for attr, cov in result['edited_axis_target_value_coverage'].items():
                if attr != 'core_asset' and cov['missing']:
                    fail('train_actual_axis_target_coverage', [attr, cov['missing']])
            missing = result['wardrobe']['introduced_core_target_coverage']['missing']
            if missing:
                fail('train_core_not_genuinely_introduced', missing)
        slot_diagnostic = compact.single_slot_diagnostic(state, edges, ss, rules)
        old_ss = sessions(BASELINE/split/'sessions.jsonl')
        old_edges = read(BASELINE/split/'edges.json')
        old_slot = compact.single_slot_diagnostic(old, old_edges, old_ss, rules)
        graph_modes = defaultdict(set)
        for edge in edges:
            if edge['axis'] == 'wardrobe':
                graph_modes[edge['source']].add(edge['mode'])
        conditional_by_aspect, missing_whole = defaultdict(Counter), Counter()
        for session in ss:
            for st in session['steps']:
                if st['axis'] != 'wardrobe' or not rules.singles(state[st['source']]):
                    continue
                conditional_by_aspect[state[st['source']]['aspect']][st['mode']] += 1
                missing_whole['eligible_wardrobe_events'] += 1
                missing_whole['events_with_no_whole_outfit_exit'] += 'whole_outfit' not in graph_modes[st['source']]
        eligible_nodes = [n for n in used if rules.singles(state[n])]
        missing_whole['used_formal_single_eligible_nodes'] = len(eligible_nodes)
        missing_whole['eligible_nodes_with_no_whole_outfit_exit'] = sum('whole_outfit' not in graph_modes[n] for n in eligible_nodes)
        hair_coverage = {'used_global_unique_hair_ids': len({state[n]['hair'] for n in used}),
                         'used_sex_specific_hair_instances': len({(state[n]['sex'], state[n]['hair']) for n in used}),
                         'edited_global_unique_hair_ids': len({state[st['target']]['hair'] for session in ss for st in session['steps'] if st['axis'] == 'hair'}),
                         'edited_sex_specific_hair_instances': len({(state[st['target']]['sex'], state[st['target']]['hair']) for session in ss for st in session['steps'] if st['axis'] == 'hair'})}
        six_by_aspect = {}
        for aspect, c in aspect_axes.items():
            mean = sum(c[a] for a in base.NONIDENTITY)/6
            dev = {a: abs(c[a]-mean)/mean for a in base.NONIDENTITY}
            six_by_aspect[aspect] = {'six_axis_mean': mean, 'relative_deviation': dev,
                                    'max_relative_deviation': max(dev.values()),
                                    'within_10_percent_diagnostic': max(dev.values()) <= .1}
        unexpected_base_errors = {k: n for k, n in result['error_counts'].items() if k != 'node_budget'}
        noaspect_keys[split], noaspect_chains[split] = keys, projected_signatures
        result.update({'saved_candidate_root': str(root),
                       'raw_legacy_hard_checks_passed': result['passed_hard_checks'],
                       'waived_legacy_errors': {k: n for k, n in result['error_counts'].items() if k == 'node_budget'},
                       'unexpected_legacy_errors': unexpected_base_errors,
                       'projection_and_v6_extra_error_counts': dict(counts), 'projection_errors_first_100': errors,
                       'passed_current_checks': not unexpected_base_errors and not counts,
                       'actual_render_node_count': len(used), 'unused_node_ids': sorted(set(state)-used),
                       'unused_nodes_are_excluded_from_render_count': True,
                       'session_counts_by_aspect': dict(aspect_sessions),
                       'used_render_nodes_by_aspect': {a: len(ns) for a, ns in aspect_nodeuse.items()},
                       'axis_counts_by_aspect': {a: dict(c) for a, c in aspect_axes.items()},
                       'start_camera_counts_by_aspect': {a: dict(c) for a, c in aspect_starts.items()},
                       'canonical_directed_edge_reuse_max': max(canonical_edge_use.values(), default=0),
                       'unique_structural_chains_ignoring_aspect': len(projected_signatures),
                       'duplicate_structural_session_pairs_ignoring_aspect': duplicate_pairs,
                       'single_slot_diagnostic': slot_diagnostic,
                       'v6_baseline_single_slot_diagnostic': old_slot,
                       'formal_single_eligible_modes_by_aspect': {a: {**dict(c), 'single_fraction': c['single_piece']/sum(c.values())}
                                                                for a, c in conditional_by_aspect.items()},
                       'formal_single_eligible_missing_whole_exit': dict(missing_whole),
                       'explicit_hair_coverage_count_scope': hair_coverage,
                       'six_axis_diagnostic_by_aspect': six_by_aspect,
                       'fork_round_and_parent_joint_counts': dict(fork_parents)})
        report['splits'][split] = result
        report['inputs'] += [pin(root/f) for f in ('nodes.json','edges.json','sessions.jsonl','ORIGIN.json','metrics.json')]
        report['inputs'] += [pin(BASELINE/split/f) for f in ('nodes.json','edges.json')]
    report['noaspect_cross_split_state_overlap'] = len(noaspect_keys['train'] & noaspect_keys['test'])
    report['noaspect_cross_split_chain_overlap'] = len(noaspect_chains['train'] & noaspect_chains['test'])
    report['registered_nodes_total'] = sum(r['counts']['nodes'] for r in report['splits'].values())
    report['actual_render_nodes_total'] = sum(r['actual_render_node_count'] for r in report['splits'].values())
    report['passed_current_checks'] = (all(r['passed_current_checks'] for r in report['splits'].values())
                                       and not report['noaspect_cross_split_state_overlap']
                                       and not report['noaspect_cross_split_chain_overlap'])
    destination = args.output.resolve()
    if destination.parent != HERE or destination.suffix != '.json':
        raise ValueError('Only audit_agent/*.json writes are permitted')
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'passed': report['passed_current_checks'], 'actual_render_nodes_total': report['actual_render_nodes_total'],
                      'cross_split_overlap': report['noaspect_cross_split_state_overlap'],
                      'splits': {split: {k: r[k] for k in ('counts','unused_node_ids','waived_legacy_errors',
                                 'unexpected_legacy_errors','projection_and_v6_extra_error_counts',
                                 'unique_structural_chains_ignoring_aspect','session_counts_by_aspect',
                                 'canonical_directed_edge_reuse_max')} for split, r in report['splits'].items()}}, ensure_ascii=False))
    raise SystemExit(0 if report['passed_current_checks'] else 1)


if __name__ == '__main__':
    main()
