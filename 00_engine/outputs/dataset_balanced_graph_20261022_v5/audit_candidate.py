"""Read-only independent audit of saved offline graph/session candidates.

Only audit.json is written. No builder metrics or construction claims are trusted.
Canonical clothes and actual core assets resolve through the current formal pure
Python wardrobe contract; attribute pools come from the pinned v1 snapshot.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
V1 = HERE.parent / 'dataset_trial_build_20261021_v1'
sys.path.insert(0, str(V1))
import normalize_catalog as nc

AXES = ('identity', 'hair', 'hair_color', 'wardrobe', 'action', 'camera', 'site')
NONIDENTITY = AXES[1:]
ID_CAMERAS = {'front_head', 'front_upper', 'dolly_in_front', 'dolly_out_front'}
UPPER = {'front_upper', 'side_upper', 'back_upper', 'front_three_quarter_upper', 'rear_three_quarter_upper'}
COLORS = {'original', 'black', 'gold', 'silver_white', 'red', 'blue', 'pink'}
LIMITS = {'train': (5000, 12000, 43800), 'test': (800, 2400, 8760)}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def token(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def hist(values):
    return {str(k): v for k, v in sorted(Counter(values).items())}


def distribution(values):
    values = sorted(values)
    n, total = len(values), sum(values)
    return {'count': n, 'sum': total, 'mean': total / n if n else 0,
            'min': min(values, default=0), 'max': max(values, default=0),
            'p95': values[max(0, math.ceil(.95 * n) - 1)] if n else 0,
            'histogram': hist(values)}


class Rules:
    def __init__(self):
        self.cat = nc.load_catalog()
        self.ids = {sex: {r['id'] for r in c['identities']} for sex, c in self.cat['sexes'].items()}
        self.hairs = {sex: {r.get('hair_id', r.get('id')) for r in c['hairs']} for sex, c in self.cat['sexes'].items()}
        self.pools = {'identity': set.union(*self.ids.values()), 'hair': set.union(*self.hairs.values()),
                      'hair_color': COLORS, 'family': set(), 'group': set(), 'core_asset': set()}
        for field, rows in [('action', self.cat['actions']), ('camera', self.cat['cameras']), ('site', self.cat['sites'])]:
            self.pools[field] = {r if isinstance(r, str) else r.get('id', r.get(field + '_id')) for r in rows}
        for sex, rows in self.cat['sexes'].items():
            for f in rows['families']:
                self.pools['family'].add(f['family_id'])
                for g in f['groups']:
                    self.pools['group'].add(f['family_id'] + '/' + g['group_id'])
                    assets = g['required_assets'] + g['optional_assets']
                    assets += [a for opts in g['slot_options'].values() for a in opts]
                    self.pools['core_asset'].update(a['asset_id'] for a in assets if a['slot'] in nc.CORE_SLOTS)
        self.exclusions = {(r.get('site_id', r.get('site')), r['action_id'], r['camera_id'], r.get('aspect', 'landscape'))
                           for r in self.cat['exclusions']}
        self.cache = {}

    def clothes(self, state):
        k = (state['sex'], token(state['wardrobe']))
        if k not in self.cache:
            sex, w = state['sex'], state['wardrobe']
            resolved = nc.validate_choice(sex, w)
            # Calling core_asset_ids is deliberate: slot labels alone miss locked bundles.
            self.cache[k] = {'key': tuple(nc.wardrobe_key(sex, w)), 'core': tuple(nc.core_asset_ids(sex, w)),
                             'upper': tuple(nc.upper_asset_ids(sex, w)), 'resolved': resolved,
                             'singles': nc.single_piece_neighbors(sex, w)}
        return self.cache[k]

    def canonical(self, s):
        # Sex and aspect are immutable context, included to detect exact rendered states.
        return (s['sex'], s['aspect'], *(self.clothes(s)['key'] if a == 'wardrobe' else s[a] for a in AXES))

    def allowed(self, s):
        return [a for a in AXES if (a != 'identity' or s['camera'] in ID_CAMERAS)
                and (a not in ('wardrobe', 'action') or s['camera'] != 'front_head')]

    def singles(self, s):
        if s['camera'] == 'front_head':
            return []
        rows = self.clothes(s)['singles']
        if s['camera'] in UPPER:
            rows = [r for r in rows if tuple(nc.upper_asset_ids(s['sex'], r['choice'])) != self.clothes(s)['upper']]
        return rows

    def valid_state(self, s):
        reasons = []
        sex = s['sex']
        if sex not in self.ids:
            return ['unknown_sex']
        for a, vals in [('identity', self.ids[sex]), ('hair', self.hairs[sex]),
                        ('hair_color', COLORS), ('action', self.pools['action']),
                        ('camera', self.pools['camera']), ('site', self.pools['site'])]:
            if s[a] not in vals:
                reasons.append('unknown_or_wrong_sex_' + a)
        if s['aspect'] not in self.cat['aspects']:
            reasons.append('unknown_aspect')
        if (s['site'], s['action'], s['camera'], s['aspect']) in self.exclusions:
            reasons.append('site_action_camera_exclusion')
        self.clothes(s)
        return reasons

    def edge(self, s, t):
        if s['sex'] != t['sex'] or s['aspect'] != t['aspect']:
            raise ValueError('immutable sex/aspect changed')
        cs, ct = self.canonical(s), self.canonical(t)
        changed = [a for j, a in enumerate(AXES, 2) if cs[j] != ct[j]]
        if len(changed) != 1:
            raise ValueError('actual changed axes=' + repr(changed))
        a = changed[0]
        if a not in self.allowed(s):
            raise ValueError('axis blocked by source camera')
        if a != 'wardrobe':
            return {'axis': a, 'mode': 'attribute'}
        sw, tw = s['wardrobe'], t['wardrobe']
        sc, tc = self.clothes(s), self.clothes(t)
        if s['camera'] in UPPER and sc['upper'] == tc['upper']:
            raise ValueError('upper camera has no upper clothes change')
        if sw['family_id'] != tw['family_id']:
            if sc['core'] == tc['core']:
                raise ValueError('whole outfit did not change actual core assets')
            return {'axis': a, 'mode': 'whole_outfit'}
        if sw['group_id'] != tw['group_id']:
            raise ValueError('single piece changed group')
        for row in self.singles(s):
            if tuple(nc.wardrobe_key(s['sex'], row['choice'])) == tc['key']:
                return {'axis': a, 'mode': 'single_piece', 'slot': row['slot']}
        raise ValueError('same family change is not one legal core slot')


def quota_counts(total):
    fork = total // 3
    out = {}
    for kind, n, weights in [('linear', total-fork, [.25]*4), ('fork', fork, [.1, .2, .35, .35])]:
        counts = [round(n*w) for w in weights]
        counts[-1] += n-sum(counts)
        out.update({f'{kind}_{length}': count for length, count in zip(range(2, 6), counts)})
    return out


def coverage(rules, states):
    counts = {a: Counter() for a in rules.pools}
    sex_counts = Counter()
    for s in states:
        sex_counts[s['sex']] += 1
        for a in AXES:
            if a != 'wardrobe':
                counts[a][s[a]] += 1
        w = s['wardrobe']
        counts['family'][w['family_id']] += 1
        counts['group'][w['family_id'] + '/' + w['group_id']] += 1
        counts['core_asset'].update(rules.clothes(s)['core'])
    return {'sex': dict(sex_counts), **{a: {'distinct': len(c), 'expected': len(rules.pools[a]),
            'missing': sorted(rules.pools[a] - set(c)), 'unexpected': sorted(set(c) - rules.pools[a]),
            'counts': dict(sorted(c.items()))} for a, c in counts.items()}}


def audit_split(path, split, rules):
    rows, edges = read(path/'nodes.json'), read(path/'edges.json')
    sessions = [json.loads(line) for line in (path/'sessions.jsonl').read_text(encoding='utf-8-sig').splitlines() if line.strip()]
    errors, error_counts = [], Counter()

    def fail(kind, detail):
        error_counts[kind] += 1
        if len(errors) < 100:
            errors.append({'kind': kind, 'detail': str(detail)})

    states, canonical, order = {}, {}, {}
    for index, row in enumerate(rows):
        u = row['id']
        if u in states:
            fail('duplicate_node_id', u)
        states[u], order[u] = row['state'], index
        try:
            reasons = rules.valid_state(row['state'])
            for reason in reasons:
                fail('invalid_node', (u, reason))
            canonical[u] = rules.canonical(row['state'])
        except Exception as exc:
            fail('invalid_node', (u, repr(exc)))
    canon_counts = Counter(canonical.values())
    if any(n > 1 for n in canon_counts.values()):
        fail('duplicate_canonical_nodes', sum(n-1 for n in canon_counts.values() if n > 1))
    registered, actual_edges, adjacency = {}, {}, defaultdict(lambda: defaultdict(list))
    for edge in edges:
        pair = edge['source'], edge['target']
        if pair in registered:
            fail('duplicate_registered_edge', pair)
        registered[pair] = edge
        try:
            actual = rules.edge(states[pair[0]], states[pair[1]])
            actual_edges[pair] = actual
            for k, v in actual.items():
                if edge.get(k) != v:
                    fail('registered_edge_metadata', (pair, k, edge.get(k), v))
            adjacency[pair[0]][actual['axis']].append(pair[1])
        except Exception as exc:
            fail('illegal_registered_edge', (pair, repr(exc)))
    provenance = Counter()
    for row in rows:
        u, p = row['id'], row.get('created_by')
        if not isinstance(p, dict) or 'parent' not in p or 'axis' not in p:
            fail('missing_provenance', u)
            continue
        parent, axis = p['parent'], p['axis']
        if parent is None:
            provenance['roots'] += 1
            if axis is not None:
                fail('root_has_axis', u)
            continue
        provenance['non_roots'] += 1
        if parent not in states or order.get(parent, math.inf) >= order[u]:
            fail('invalid_provenance_parent', (u, parent))
            continue
        try:
            actual = rules.edge(states[parent], states[u])
            if actual['axis'] != axis:
                fail('provenance_axis_mismatch', (u, parent, axis, actual))
            if (parent, u) not in registered:
                fail('provenance_edge_missing', (u, parent))
        except Exception as exc:
            fail('illegal_provenance_edge', (u, parent, repr(exc)))
    nodeuse, edgeuse, axes, modes = Counter(), Counter(), Counter(), Counter()
    target_ids, source_ids, kinds = [], [], Counter()
    edited_targets = {a: Counter() for a in rules.pools}
    conditional_modes, conditional_slots, formal_expected = Counter(), Counter(), Counter()
    introduced_core = Counter()
    introduced_core_by_mode = defaultdict(Counter)
    wholeonly_modes, support_missing, opportunities = Counter(), Counter(), Counter()
    seen_sessions, session_ids, fork_rounds, fork_parents = set(), set(), Counter(), Counter()
    first_edge_reuse_before = {}
    fork_effect = Counter()
    perkind = defaultdict(lambda: {'distinct_axes': Counter(), 'axis_repeated_steps': Counter(),
                                   'consecutive_same_axis_steps': Counter(), 'node_revisited_steps': Counter(),
                                   'exact_edge_repeated_steps': Counter()})
    for session in sessions:
        sid, history, steps = session.get('id'), session['history'], session['steps']
        kind, length = session['kind'], session['length']
        if sid in session_ids:
            fail('duplicate_session_id', sid)
        session_ids.add(sid)
        kinds[f'{kind}_{length}'] += 1
        if kind not in ('linear', 'fork') or length not in range(2, 6) or len(steps) != length or len(history) != length+1:
            fail('invalid_session_shape', sid)
            continue
        if any(u not in states for u in history):
            fail('session_node_missing', sid)
            continue
        nodeuse.update(history)
        signature = (canonical.get(history[0]), tuple((r.get('source_position'), canonical.get(r.get('target'))) for r in steps))
        if signature in seen_sessions:
            fail('duplicate_full_chain', sid)
        seen_sessions.add(signature)
        actual_sequence, actual_pairs, forks = [], [], []
        for t, step in enumerate(steps, 1):
            p, u, v = step['source_position'], step['source'], step['target']
            if not isinstance(p, int) or not 0 <= p < t or u != history[p] or v != history[t]:
                fail('history_inheritance', (sid, t))
                continue
            if p < t-1:
                forks.append(t)
                fork_rounds[f'L{length}_t{t}'] += 1
                fork_parents['root' if p == 0 else 'intermediate'] += 1
            pair = u, v
            if pair not in registered:
                fail('session_edge_unregistered', (sid, t, pair))
            try:
                actual = actual_edges.get(pair) or rules.edge(states[u], states[v])
                for k, val in actual.items():
                    if step.get(k) != val:
                        fail('session_edge_metadata', (sid, t, k, step.get(k), val))
                a = actual['axis']
                axes[a] += 1
                if t == 1:
                    first_edge_reuse_before[sid] = edgeuse[pair]
                edgeuse[pair] += 1
                target_ids.append(v)
                source_ids.append(u)
                actual_sequence.append(a)
                actual_pairs.append(pair)
                if a == 'wardrobe':
                    w = states[v]['wardrobe']
                    edited_targets['family'][w['family_id']] += 1
                    edited_targets['group'][w['family_id'] + '/' + w['group_id']] += 1
                    edited_targets['core_asset'].update(rules.clothes(states[v])['core'])
                else:
                    edited_targets[a][states[v][a]] += 1
                formal = rules.allowed(states[u])
                denominator = sum(2 if axis == 'identity' else 1 for axis in formal)
                for axis in formal:
                    opportunities[axis] += 1
                    formal_expected[axis] += (2 if axis == 'identity' else 1)/denominator
                    support_missing[axis] += not bool(adjacency[u].get(axis))
                if a == 'wardrobe':
                    modes[actual['mode']] += 1
                    gained = set(rules.clothes(states[v])['core']) - set(rules.clothes(states[u])['core'])
                    introduced_core.update(gained)
                    introduced_core_by_mode[actual['mode']].update(gained)
                    if rules.singles(states[u]):
                        conditional_modes[actual['mode']] += 1
                        if actual['mode'] == 'single_piece':
                            conditional_slots[actual['slot']] += 1
                    else:
                        wholeonly_modes[actual['mode']] += 1
                if p < t-1:
                    source_key, latest_key = canonical[u], canonical[history[t-1]]
                    preserved = [j for j, axis in enumerate(AXES, 2) if axis != a]
                    fork_effect['preserved_state_differs_from_latest' if any(source_key[j] != latest_key[j] for j in preserved)
                                else 'same_preserved_state_as_latest'] += 1
            except Exception as exc:
                fail('illegal_session_edge', (sid, t, repr(exc)))
        if kind == 'linear' and (forks or session.get('fork_round') is not None):
            fail('linear_has_fork', sid)
        if kind == 'fork' and (len(forks) != 1 or session.get('fork_round') != (forks[0] if forks else None)):
            fail('fork_position', (sid, forks, session.get('fork_round')))
        dst = perkind[f'{kind}_{length}']
        dst['distinct_axes'][len(set(actual_sequence))] += 1
        dst['axis_repeated_steps'][len(actual_sequence)-len(set(actual_sequence))] += 1
        dst['consecutive_same_axis_steps'][sum(a == b for a, b in zip(actual_sequence, actual_sequence[1:]))] += 1
        dst['node_revisited_steps'][len(history)-len(set(history))] += 1
        dst['exact_edge_repeated_steps'][len(actual_pairs)-len(set(actual_pairs))] += 1
    # Construction metadata is a disclosure only; its warmup claims are checked
    # against the independently parsed accepted sessions and actual core gains.
    sampling_meta = {}
    if (path/'metrics.json').exists():
        sampling_meta = read(path/'metrics.json').get('construction', {}).get('sampling', {})
    warmup_records = sampling_meta.get('forced_coverage_jobs', [])
    by_session_id = {s.get('id'): s for s in sessions}
    for record in warmup_records:
        try:
            s = by_session_id[record['session_id']]
            first = s['steps'][0]
            u, v = first['source'], first['target']
            requested_sex, requested_asset = record['requested_core']
            gained = set(rules.clothes(states[v])['core']) - set(rules.clothes(states[u])['core'])
            real_fork_source = s['steps'][s['fork_round']-1]['source_position'] if s['fork_round'] else None
            if (record['forced_round'] != 1 or first['axis'] != 'wardrobe'
                    or record['source'] != u or record['target'] != v
                    or record['mode'] != first['mode'] or record['kind'] != s['kind']
                    or record['length'] != s['length'] or record['fork_round'] != s['fork_round']
                    or record['fork_source_position'] != real_fork_source
                    or requested_sex != states[v]['sex'] or requested_asset not in gained
                    or record['edge_reuse_before'] != first_edge_reuse_before[s['id']]):
                fail('warmup_disclosure_mismatch', record['session_id'])
        except Exception as exc:
            fail('warmup_disclosure_invalid', repr(exc))
    if sampling_meta.get('forced_coverage_job_count', len(warmup_records)) != len(warmup_records):
        fail('warmup_disclosure_count', len(warmup_records))
    expected_nodes, expected_sessions, expected_edits = LIMITS[split]
    for kind, actual, expected in [('sessions', len(sessions), expected_sessions), ('edit_steps', sum(axes.values()), expected_edits)]:
        if actual != expected:
            fail('target_' + kind, (actual, expected))
    if len(rows) > expected_nodes:
        fail('node_budget', (len(rows), expected_nodes))
    expected_quota = quota_counts(expected_sessions)
    if dict(kinds) != expected_quota:
        fail('length_kind_quota', (dict(kinds), expected_quota))
    if max(edgeuse.values(), default=0) > 4:
        fail('edge_reuse_cap4', max(edgeuse.values()))
    mean_six = sum(axes[a] for a in NONIDENTITY)/6
    six_deviation = {a: abs(axes[a]-mean_six)/mean_six if mean_six else 1 for a in NONIDENTITY}
    if max(six_deviation.values()) > .10:
        fail('six_axis_deviation_over_10_percent', six_deviation)
    used_cov = coverage(rules, (states[u] for u in sorted(nodeuse) if u in canonical))
    if split == 'train':
        for attr in rules.pools:
            if used_cov[attr]['missing']:
                fail('train_used_value_coverage', (attr, used_cov[attr]['missing']))
    if any(axes[a] == 0 for a in AXES):
        fail('missing_sampled_axis', dict(axes))
    axis_edges = {a: Counter({pair: n for pair, n in edgeuse.items() if actual_edges.get(pair, {}).get('axis') == a}) for a in AXES}
    four_count = sum(n == 4 for n in edgeuse.values())
    four_fraction = four_count/len(edgeuse) if edgeuse else 0
    conditional_total = sum(conditional_modes.values())
    report = {'passed_hard_checks': not error_counts, 'error_counts': dict(error_counts), 'errors_first_100': errors,
              'counts': {'nodes': len(rows), 'used_nodes': len(nodeuse), 'unused_nodes': len(rows)-len(nodeuse),
                         'registered_directed_edges': len(edges), 'used_directed_edges': len(edgeuse),
                         'sessions': len(sessions), 'edit_steps': sum(axes.values()), 'unique_full_chains': len(seen_sessions)},
              'limits': {'nodes_max': expected_nodes, 'sessions': expected_sessions, 'edit_steps': expected_edits},
              'provenance': dict(provenance), 'length_kind_counts': dict(kinds), 'expected_length_kind_counts': expected_quota,
              'axis_counts': {a: axes[a] for a in AXES},
              'six_nonidentity_axis_mean': mean_six, 'six_nonidentity_relative_deviation': six_deviation,
              'axis_unique_directed_edges': {a: len(axis_edges[a]) for a in AXES},
              'axis_edge_reuse': {a: distribution(axis_edges[a].values()) for a in AXES},
              'edge_reuse': distribution(edgeuse.values()), 'node_use': distribution(nodeuse.values()),
              'soft_targets': {'four_use_edge_fraction': four_fraction, 'four_use_edge_count': four_count,
                               'four_use_fraction_at_most_0_005': four_fraction <= .005,
                               'per_axis_mean_reuse_target': 2,
                               'per_axis_mean_reuse_relative_deviation_from_2': {a: abs(sum(axis_edges[a].values())/len(axis_edges[a])-2)/2 if axis_edges[a] else None for a in AXES}},
              'thresholds_and_flags': {'hard_six_axis_relative_deviation_max': .10,
                  'hard_directed_edge_uses_max': 4, 'soft_four_use_edge_fraction_max': .005,
                  'six_axis_balance_pass': max(six_deviation.values()) <= .10,
                  'edge_reuse_cap_pass': max(edgeuse.values(), default=0) <= 4,
                  'four_use_soft_target_pass': four_fraction <= .005,
                  'all_used_values_covered': all(not used_cov[a]['missing'] for a in rules.pools),
                  'all_edited_axis_target_values_covered': all(set(edited_targets[a]) >= rules.pools[a] for a in rules.pools),
                  'all_core_values_genuinely_introduced': set(introduced_core) >= rules.pools['core_asset'],
                  'coverage_full_value_flags_are_hard_only_for_train_used_nodes': True},
              'coverage_warmup_disclosure': {'sampling_variant_claim': sampling_meta.get('sampling_variant'),
                  'enabled_claim': sampling_meta.get('core_coverage_warmup_enabled'),
                  'forced_first_step_records': len(warmup_records),
                  'records_match_saved_sessions': not any(error_counts[k] for k in ('warmup_disclosure_mismatch', 'warmup_disclosure_invalid', 'warmup_disclosure_count')),
                  'selection_policy_claim': sampling_meta.get('core_coverage_override_policy'),
                  'history_axis_decay_claim': sampling_meta.get('history_axis_decay'),
                  'axis_weight_formula_static_review': 'legal base identity2/other1 times 0.5**prior_count_in_entire_session times count feedback; warmup first step is explicitly selected'},
              'wardrobe': {'all_modes': dict(modes), 'formal_single_eligible_modes': dict(conditional_modes),
                           'introduced_core_target_coverage': {'distinct': len(introduced_core),
                               'expected': len(rules.pools['core_asset']),
                               'missing': sorted(rules.pools['core_asset'] - set(introduced_core)),
                               'counts': dict(sorted(introduced_core.items()))},
                           'introduced_core_targets_by_mode': {mode: {'distinct': len(c), 'counts': dict(sorted(c.items()))}
                                                              for mode, c in introduced_core_by_mode.items()},
                           'formal_single_eligible_total': conditional_total,
                           'formal_single_eligible_single_fraction': conditional_modes['single_piece']/conditional_total if conditional_total else None,
                           'single_slots': dict(conditional_slots), 'formal_whole_only_modes_excluded_from_conditional': dict(wholeonly_modes)},
              'source_conditioned_formal_axis_expectation': dict(formal_expected),
              'formal_axis_opportunities': dict(opportunities), 'formal_axis_missing_in_saved_graph': dict(support_missing),
              'coverage_all_nodes': coverage(rules, (states[u] for u in canonical)), 'coverage_used_nodes': used_cov,
              'target_value_coverage': coverage(rules, (states[u] for u in target_ids)),
              'edited_axis_target_value_coverage': {a: {'distinct': len(c), 'expected': len(rules.pools[a]),
                  'missing': sorted(rules.pools[a] - set(c)), 'counts': dict(sorted(c.items()))} for a, c in edited_targets.items()},
              'source_value_coverage': coverage(rules, (states[u] for u in source_ids)),
              'per_length_kind_sequence_stats': {k: {stat: {str(value): count for value, count in sorted(c.items())}
                                                   for stat, c in data.items()} for k, data in perkind.items()},
              'per_length_kind_sequence_means': {k: {stat: sum(value*count for value, count in c.items())/sum(c.values())
                                                     if c else 0 for stat, c in data.items()} for k, data in perkind.items()},
              'fork_rounds': dict(fork_rounds), 'fork_parents': dict(fork_parents), 'fork_effect': dict(fork_effect),
              'hair_deny_node_count': sum(bool(rules.clothes(states[u])['resolved'].get('hair_deny')) for u in canonical)}
    return report, set(canonical.values()), seen_sessions


def audit_root(root):
    root = Path(root).resolve()
    rules = Rules()
    train, train_keys, train_chains = audit_split(root/'train', 'train', rules)
    test, test_keys, test_chains = audit_split(root/'test', 'test', rules)
    overlap, chain_overlap = train_keys & test_keys, train_chains & test_chains
    result = {'schema': 'independent_saved_candidate_audit_v5',
              'scope': 'offline semantic and sampling audit; no UE render or visual acceptance',
              'candidate_root': str(root), 'catalog_snapshot': str(V1/'catalog.json'),
              'catalog_snapshot_sha256': hashlib.sha256((V1/'catalog.json').read_bytes()).hexdigest(),
              'canonical_train_test_overlap': len(overlap), 'full_chain_train_test_overlap': len(chain_overlap),
              'passed_hard_checks': train['passed_hard_checks'] and test['passed_hard_checks'] and not overlap and not chain_overlap,
              'train': train, 'test': test}
    baseline_path = HERE/'rotated_baseline_sequence_stats.json'
    if baseline_path.exists():
        baseline = read(baseline_path)
        result['sequence_comparison_baseline'] = str(HERE.parent/'dataset_sequence_graph_20261021_v4/rotated')
        for split in ('train', 'test'):
            now, before = result[split], baseline[split]
            comparisons = {}
            for key, means in now['per_length_kind_sequence_means'].items():
                old = before['per_length_kind_sequence_means'][key]['distinct_axes']
                comparisons[key] = {'baseline_mean_distinct_axes': old,
                                    'candidate_mean_distinct_axes': means['distinct_axes'],
                                    'delta': means['distinct_axes']-old}
            bylength = {}
            for length in range(2, 6):
                keys = [f'{kind}_{length}' for kind in ('linear', 'fork')]
                counts = now['length_kind_counts']
                n = sum(counts.get(k, 0) for k in keys)
                if n:
                    new_mean = sum(counts.get(k, 0)*comparisons[k]['candidate_mean_distinct_axes'] for k in keys)/n
                    old_mean = sum(counts.get(k, 0)*comparisons[k]['baseline_mean_distinct_axes'] for k in keys)/n
                    bylength[str(length)] = {'baseline_mean_distinct_axes': old_mean,
                                             'candidate_mean_distinct_axes': new_mean,
                                             'delta': new_mean-old_mean}
            now['vs_v4_rotated_distinct_axes'] = comparisons
            now['vs_v4_rotated_by_length'] = bylength
    (root/'audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True, help='Saved candidate root containing train/ and test/')
    args = parser.parse_args()
    report = audit_root(args.root)
    print(json.dumps({'passed_hard_checks': report['passed_hard_checks'],
                      'canonical_train_test_overlap': report['canonical_train_test_overlap'],
                      **{s: {'counts': report[s]['counts'], 'errors': report[s]['error_counts'],
                             'axis_counts': report[s]['axis_counts'], 'axis_unique_edges': report[s]['axis_unique_directed_edges'],
                             'reuse_histogram': report[s]['edge_reuse']['histogram']} for s in ('train', 'test')}}, ensure_ascii=False))
    return 0 if report['passed_hard_checks'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
