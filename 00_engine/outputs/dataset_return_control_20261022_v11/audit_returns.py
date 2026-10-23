"""Independent read-only attribute-return audit of saved graph/session JSON.

Only --output is written. Strict returns follow selected source_position ancestry;
chronological repeats and the resets implicit in a fork are reported separately.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
FORMAL_RULES_PATH = HERE.parent / 'dataset_balanced_graph_20261022_v5' / 'audit_candidate.py'
BASELINE = HERE.parent / 'dataset_distributed_graph_20261022_v10' / 'aspect_work' / 'selected_candidate'
spec = importlib.util.spec_from_file_location('formal_saved_graph_audit_v5', FORMAL_RULES_PATH)
formal = importlib.util.module_from_spec(spec)
spec.loader.exec_module(formal)
AXES = tuple(formal.AXES)
EXPECTED_BASELINE = {'train': (8035, 6107), 'test': (1567, 1192)}


def token(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def digest(value):
    return hashlib.sha256(token(value).encode('utf-8')).hexdigest()


def load_split(path):
    rows = json.loads((path / 'nodes.json').read_text(encoding='utf-8-sig'))
    edges = json.loads((path / 'edges.json').read_text(encoding='utf-8-sig'))
    sessions = [json.loads(line) for line in (path / 'sessions.jsonl').read_text(encoding='utf-8-sig').splitlines() if line.strip()]
    return rows, edges, sessions


def pins(path, data):
    return {name: {'sha256': hashlib.sha256((path / name).read_bytes()).hexdigest(),
                   'canonical_json_sha256': digest(value), 'records': len(value)}
            for name, value in zip(('nodes.json', 'edges.json', 'sessions.jsonl'), data)}


def finish_metric(events, chains, histograms, group_sizes):
    total = sum(events.values())
    return {'events': total, 'chains': len(chains['all']),
            'per_axis': {a: {'events': events[a], 'chains': len(chains[a])} for a in AXES},
            'per_length_kind': {group: {'events': sum(histograms[group]['events'].values()),
                'chains': len(histograms[group]['chains']),
                'event_count_histogram': {str(n): count for n, count in sorted(Counter(
                    histograms[group]['session_counts'].get(i, 0) for i in range(size)).items())},
                'per_axis': {a: {'events': histograms[group]['events'][a],
                                'chains': len(histograms[group]['axis_chains'][a])} for a in AXES}}
                for group, size in sorted(group_sizes.items())}}


class Metric:
    def __init__(self):
        self.events = Counter()
        self.chains = defaultdict(set)
        self.groups = defaultdict(lambda: {'events': Counter(), 'chains': set(),
            'axis_chains': defaultdict(set), 'session_counts': Counter()})

    def add(self, axis, index, group, group_index):
        self.events[axis] += 1
        self.chains['all'].add(index)
        self.chains[axis].add(index)
        row = self.groups[group]
        row['events'][axis] += 1
        row['chains'].add(index)
        row['axis_chains'][axis].add(index)
        row['session_counts'][group_index] += 1

    def report(self, group_sizes):
        return finish_metric(self.events, self.chains, self.groups, group_sizes)


def audit_split(path, rules):
    data = load_split(path)
    rows, edges, sessions = data
    states = {row['id']: row['state'] for row in rows}
    canonical = {u: rules.canonical(s) for u, s in states.items()}
    # The formal wardrobe key is essential: raw wardrobe JSON is not equality.
    values = {u: {a: rules.clothes(s)['key'] if a == 'wardrobe' else s[a] for a in AXES}
              for u, s in states.items()}
    registered = {(e['source'], e['target']) for e in edges}
    metrics = {key: Metric() for key in ('strict_explicit_ancestor_returns',
        'chronological_edited_target_repeats', 'other_branch_edited_target_repeats',
        'implicit_unedited_axis_resets_vs_latest')}
    group_sizes, distinct, full_repeats, full_repeat_chains = Counter(), defaultdict(Counter), Counter(), set()
    axis_counts, edge_use, errors, examples = Counter(), Counter(), Counter(), []
    fork_steps = 0

    def fail(kind, detail):
        errors[kind] += 1
        if len(examples) < 50:
            examples.append({'kind': kind, 'detail': detail})

    seen_session_ids = set()
    for index, session in enumerate(sessions):
        sid, history, steps = session['id'], session['history'], session['steps']
        group = f"{session['kind']}_{session['length']}"
        group_index = group_sizes[group]
        group_sizes[group] += 1
        if sid in seen_session_ids:
            fail('duplicate_session_id', sid)
        seen_session_ids.add(sid)
        if len(history) != len(steps) + 1 or len(steps) != session['length']:
            fail('session_shape', sid)
            continue
        if any(u not in states for u in history):
            fail('missing_node', sid)
            continue
        parents = {0: None}
        sequence = []
        repeat_count = 0
        for t, step in enumerate(steps, 1):
            p, u, v = step['source_position'], step['source'], step['target']
            if not isinstance(p, int) or not 0 <= p < t or u != history[p] or v != history[t]:
                fail('parent_position_topology', [sid, t])
                continue
            parents[t] = p
            if (u, v) not in registered:
                fail('unregistered_edge', [sid, t])
            changed = [a for a in AXES if values[u][a] != values[v][a]]
            if len(changed) != 1:
                fail('non_atomic_edge', [sid, t, changed])
                continue
            axis = changed[0]
            if step['axis'] != axis:
                fail('axis_metadata', [sid, t, step['axis'], axis])
            sequence.append(axis)
            axis_counts[axis] += 1
            edge_use[u, v] += 1
            ancestry, q = [], p
            while q is not None:
                ancestry.append(q)
                q = parents[q]
            target_value = values[v][axis]
            # Source/target inequality is checked independently of metadata.
            strict = values[u][axis] != target_value and any(
                values[history[q]][axis] == target_value for q in ancestry)
            chronological = values[u][axis] != target_value and any(
                values[previous][axis] == target_value for previous in history[:t])
            for key, condition in [('strict_explicit_ancestor_returns', strict),
                    ('chronological_edited_target_repeats', chronological),
                    ('other_branch_edited_target_repeats', chronological and not strict)]:
                if condition:
                    metrics[key].add(axis, index, group, group_index)
            if p < t - 1:
                fork_steps += 1
                latest = history[t-1]
                for other in AXES:
                    if other != axis and values[v][other] != values[latest][other]:
                        metrics['implicit_unedited_axis_resets_vs_latest'].add(other, index, group, group_index)
            if canonical[v] in {canonical[previous] for previous in history[:t]}:
                repeat_count += 1
        distinct[group][len(set(sequence))] += 1
        full_repeats[group] += repeat_count
        if repeat_count:
            full_repeat_chains.add(index)
    result = {'passed_structural_checks': not errors, 'errors': dict(errors), 'errors_first_50': examples,
              'counts': {'nodes': len(rows), 'edges': len(edges), 'sessions': len(sessions),
                         'edit_steps': sum(axis_counts.values()), 'fork_steps': fork_steps,
                         'unique_canonical_nodes': len(set(canonical.values()))},
              'axis_counts': {a: axis_counts[a] for a in AXES},
              'length_kind_counts': dict(sorted(group_sizes.items())),
              'pins': pins(path, data),
              **{key: metric.report(group_sizes) for key, metric in metrics.items()},
              'distinct_axes': {group: {'histogram': {str(n): count for n, count in sorted(c.items())},
                  'mean': sum(n * count for n, count in c.items()) / sum(c.values())}
                  for group, c in sorted(distinct.items())},
              'full_node_repeats': {'events': sum(full_repeats.values()), 'chains': len(full_repeat_chains),
                  'per_length_kind_events': dict(sorted(full_repeats.items())),
                  'equality': 'formal canonical rendered state including sex and aspect'},
              'edge_reuse_histogram': {str(n): count for n, count in sorted(Counter(edge_use.values()).items())}}
    return result, data, canonical


def compare_baseline(candidate_data, baseline_data, rules):
    nodes, _, sessions = candidate_data
    old_nodes, _, old_sessions = baseline_data
    states, old_states = ({r['id']: r['state'] for r in rows} for rows in (nodes, old_nodes))
    old_by_id = {s['id']: s for s in old_sessions}
    differences = Counter()
    for s in sessions:
        old = old_by_id.get(s['id'])
        if old is None:
            differences['session_id_missing_in_baseline'] += 1
            continue
        start, old_start = s['history'][0], old['history'][0]
        if start != old_start or states[start] != old_states[old_start]:
            differences['exact_start_node_changed'] += 1
        if rules.canonical(states[start]) != rules.canonical(old_states[old_start]):
            differences['canonical_start_state_changed'] += 1
        if tuple(step['source_position'] for step in s['steps']) != tuple(step['source_position'] for step in old['steps']):
            differences['parent_position_topology_changed'] += 1
        if any(s.get(k) != old.get(k) for k in ('kind', 'length', 'fork_round', 'aspect')):
            differences['session_shape_context_changed'] += 1
    differences['baseline_sessions_missing_in_candidate'] += len(set(old_by_id) - {s['id'] for s in sessions})
    differences = {k: n for k, n in differences.items() if n}
    return {'passed': not differences, 'differences': differences,
            'exact_start_node_check': 'same session id, node id and full saved state',
            'parent_topology_check': 'source_position sequence for every corresponding session'}


def audit(candidate, baseline=None):
    candidate = candidate.resolve()
    rules = formal.Rules()
    result = {'schema': 'independent_attribute_return_audit_v11', 'candidate': str(candidate),
        'scope': 'offline attribute-return statistics and bounded preservation checks; no UE execution',
        'definitions': {
            'strict_explicit_ancestor_return': 'edited target value differs from source and occurs on selected source_position ancestry (including root/source)',
            'chronological_edited_target_repeat': 'edited target value differs from source and occurs anywhere earlier in chronological history',
            'other_branch_edited_target_repeat': 'chronological edited target repeat that is not a strict ancestor return',
            'implicit_unedited_axis_reset': 'at a fork, an unedited target axis differs from chronological latest; inherited from selected source',
            'event_unit': 'one (step, axis); a fork may reset several unedited axes',
            'wardrobe_equality': "formal Rules.clothes(state)['key']"},
        'formal_rules': {'path': str(FORMAL_RULES_PATH), 'sha256': hashlib.sha256(FORMAL_RULES_PATH.read_bytes()).hexdigest()}}
    keys = {}
    for split in ('train', 'test'):
        report, data, canonical = audit_split(candidate / split, rules)
        keys[split] = set(canonical.values())
        result[split] = report
        if baseline:
            baseline_data = load_split(baseline / split)
            report['baseline_preservation'] = compare_baseline(data, baseline_data, rules)
            report['baseline_pins'] = pins(baseline / split, baseline_data)
        if candidate == BASELINE.resolve():
            events, chains = EXPECTED_BASELINE[split]
            actual = report['strict_explicit_ancestor_returns']
            report['known_baseline_regression'] = {'expected_events': events, 'expected_chains': chains,
                'passed': actual['events'] == events and actual['chains'] == chains}
    result['canonical_train_test_overlap'] = len(keys['train'] & keys['test'])
    result['passed_checks'] = not result['canonical_train_test_overlap'] and all(
        result[s]['passed_structural_checks'] and result[s].get('baseline_preservation', {'passed': True})['passed']
        and result[s].get('known_baseline_regression', {'passed': True})['passed'] for s in ('train', 'test'))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--baseline', type=Path)
    args = parser.parse_args()
    result = audit(args.candidate, args.baseline.resolve() if args.baseline else None)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'passed_checks': result['passed_checks'], **{s: {k: result[s][k]
        for k in ('counts', 'strict_explicit_ancestor_returns', 'full_node_repeats')} for s in ('train', 'test')}}))
    return 0 if result['passed_checks'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
