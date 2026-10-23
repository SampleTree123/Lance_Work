"""Independent v3 audit: semantic integrity plus bounded, readable diversity metrics.

Imports only earlier independent validators/formal wardrobe resolver. Local target
support, revisits and histogram deviations are descriptive, never hard failures.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
OUTPUTS = HERE.parents[1]
V1 = OUTPUTS / 'dataset_trial_build_20261021_v1'
V2 = OUTPUTS / 'dataset_joint_build_20261021_v2' / 'audit'
sys.path[:0] = [str(V2), str(V1)]
from verify_trial import AXES, UPPER_CAMERAS, read, serial, sha
from verify_joint import Audit


def summary(values):
    values = list(values)
    return {'min': min(values, default=0), 'median': statistics.median(values) if values else 0,
            'mean': statistics.mean(values) if values else 0, 'max': max(values, default=0)}


def concentration(counter, universe=None):
    total = sum(counter.values())
    rows = counter.most_common()
    size = len(universe) if universe is not None else len(counter)
    counts = [counter[value] for value in universe] if universe is not None else list(counter.values())
    share = lambda k: sum(n for _, n in rows[:k]) / total if total else 0
    return {'references': total, 'used_unique': len(counter), 'available_unique': size,
            'unused_unique': size - len(counter), 'references_per_item': summary(counts),
            'top_1_share': share(1), 'top_10_share': share(10),
            'top_1_percent_share': share(max(1, math.ceil(size * .01))),
            'effective_unique_inverse_simpson': total * total / sum(n*n for n in counts) if total else 0,
            'most_used_10': [{'item': str(k), 'references': n} for k, n in rows[:10]]}


def distribution(actual, expected):
    total = sum(actual.values())
    expected_total = sum(expected.values())
    keys = sorted(set(actual) | set(expected))
    rows = {str(k): {'actual': actual[k], 'expected': expected.get(k, 0),
                    'actual_share': actual[k]/total if total else 0,
                    'expected_share': expected.get(k, 0)/expected_total if expected_total else 0,
                    'difference_percentage_points': 100 * ((actual[k]/total if total else 0)
                        - (expected.get(k, 0)/expected_total if expected_total else 0))} for k in keys}
    return {'n': total, 'total_variation': sum(abs(r['difference_percentage_points']) for r in rows.values())/200,
            'max_absolute_difference_percentage_points': max((abs(r['difference_percentage_points']) for r in rows.values()), default=0),
            'values': rows}


class LocalAudit(Audit):
    @lru_cache(maxsize=None)
    def legal_targets(self, state_json, axis):
        state = json.loads(state_json)
        if axis not in self.formal_axes(state):
            return ()
        values = self.targets(state_json, axis)
        if axis == 'hair':
            legal = []
            for value in values:
                try:
                    if not self.resolved(state['sex'], serial(state['wardrobe']), value)['hair_deny']:
                        legal.append(value)
                except ValueError:
                    pass
            return tuple(legal)
        return values

    def quality(self, directory):
        nodes = read(directory / 'nodes.json')
        edges = read(directory / 'edges.json')
        sessions = [json.loads(s) for s in (directory / 'sessions.jsonl').read_text(encoding='utf-8').splitlines() if s]
        states = {n['id']: n['state'] for n in nodes}
        adjacency = defaultdict(lambda: defaultdict(list))
        for e in edges:
            adjacency[e['source']][e['axis']].append(e)
        all_pairs = {(e['source'], e['target']) for e in edges}
        node_refs, source_refs, target_refs, edge_refs, starts = Counter(), Counter(), Counter(), Counter(), Counter()
        used_state_ids = {nid for session in sessions for nid in session['history']}
        values = defaultdict(set)
        node_marginals = defaultdict(Counter)
        hair_links = defaultdict(lambda: defaultdict(set))
        joints = defaultdict(set)
        for nid, state in states.items():
            if nid not in used_state_ids:
                continue
            sex = state['sex']
            node_marginals['all/sex'][sex] += 1
            for axis in ('identity', 'hair', 'hair_color', 'action', 'camera', 'site'):
                values[(sex if axis in ('identity', 'hair') else 'all', axis)].add(state[axis])
                node_marginals[(sex if axis in ('identity', 'hair') else 'all') + '/' + axis][state[axis]] += 1
            values[(sex, 'family')].add(state['wardrobe']['family_id'])
            node_marginals[sex+'/family'][state['wardrobe']['family_id']] += 1
            values[(sex, 'group')].add((state['wardrobe']['family_id'], state['wardrobe']['group_id']))
            actual_assets = set(self.wardrobe(state)['assets'])
            family_assets = {asset for asset in actual_assets if (sex,asset) in self.assets}
            shared_shoes = actual_assets-family_assets
            values[(sex,'family_asset')].update(family_assets)
            values[(sex,'shared_shoe')].update(shared_shoes)
            for attr, value in [('identity', state['identity']), ('family', state['wardrobe']['family_id']), ('site', state['site'])]:
                hair_links[(sex, state['hair'])][attr].add(value)
            for a, b, x, y in [('identity', 'hair', state['identity'], state['hair']),
                               ('hair', 'family', state['hair'], state['wardrobe']['family_id']),
                               ('hair', 'site', state['hair'], state['site']),
                               ('family', 'site', state['wardrobe']['family_id'], state['site'])]:
                joints[(sex, a, b)].add((x, y))
        formal, singles = {}, {}
        missing_axis_nodes, formal_axis_nodes, local_degrees = Counter(), Counter(), defaultdict(Counter)
        mode_nodes = Counter()
        possible_directions = defaultdict(set)
        registered_directions, used_directions = defaultdict(set), defaultdict(set)
        def direction(e):
            a, b, axis = states[e['source']], states[e['target']], e['axis']
            if axis == 'wardrobe':
                if e['mode'] == 'whole_outfit':
                    return 'wardrobe_whole_family', (a['sex'], a['wardrobe']['family_id'], b['wardrobe']['family_id'])
                slot = e['slot']
                return 'wardrobe_single_piece', (a['sex'], a['wardrobe']['family_id'], a['wardrobe']['group_id'], slot,
                         a['wardrobe']['slot_choices'].get(slot), b['wardrobe']['slot_choices'].get(slot))
            return axis, (a['sex'] if axis in ('identity', 'hair') else 'all', a[axis], b[axis])
        for nid, state in states.items():
            sj = serial(state)
            formal[nid] = self.formal_axes(state)
            if 'hair' in formal[nid] and not self.legal_targets(sj, 'hair'):
                formal[nid] = formal[nid] - {'hair'}
            singles[nid] = self.single_options(sj)
            for axis in formal[nid]:
                formal_axis_nodes[axis] += 1
                local_degrees[axis][str(len(adjacency[nid].get(axis, [])))] += 1
                if not adjacency[nid].get(axis):
                    missing_axis_nodes[axis] += 1
                if axis != 'wardrobe':
                    for value in self.legal_targets(sj, axis):
                        possible_directions[axis].add((state['sex'] if axis in ('identity', 'hair') else 'all', state[axis], value))
            for slot, value, _ in singles[nid]:
                possible_directions['wardrobe_single_piece'].add((state['sex'], state['wardrobe']['family_id'],
                    state['wardrobe']['group_id'], slot, state['wardrobe']['slot_choices'].get(slot), value))
            if 'wardrobe' in formal[nid]:
                modes = {e['mode'] for e in adjacency[nid].get('wardrobe', [])}
                if singles[nid]:
                    mode_nodes['formal_single_available'] += 1
                    mode_nodes['local_' + ('both' if {'single_piece','whole_outfit'} <= modes else
                        'single_only' if 'single_piece' in modes else 'whole_only' if 'whole_outfit' in modes else 'neither')] += 1
        # Family-level direction opportunity baseline; full garment legality is
        # independently checked for every actual edge, rather than enumerating outfits.
        for sex, pool in self.catalog['sexes'].items():
            families = [f['family_id'] for f in pool['families']]
            for a in families:
                for b in families:
                    if a != b:
                        possible_directions['wardrobe_whole_family'].add((sex, a, b))
        for edge in edges:
            axis, d = direction(edge)
            registered_directions[axis].add(d)
        actual_axes, expected_axes, expected_local_axes = Counter(), Counter(), Counter()
        camera_axis_actual, camera_axis_expected = defaultdict(Counter), defaultdict(Counter)
        missing_axis_steps, formal_axis_steps = Counter(), Counter()
        modes_actual, modes_expected, modes_support_steps = Counter(), Counter(), Counter()
        returns, same_axis_returns, consecutive_axes = Counter(), Counter(), Counter()
        fork_effects, repeated_edges = Counter(), Counter()
        canonical_features = {nid:json.loads(self.canonical(state)) for nid,state in states.items()}
        fork_rounds, fork_parents = defaultdict(Counter), defaultdict(Counter)
        chain_axes = Counter()
        initial = defaultdict(Counter)
        target_actual, target_expected = defaultdict(Counter), defaultdict(Counter)
        for session in sessions:
            h, steps = session['history'], session['steps']
            node_refs.update(h)
            starts[h[0]] += 1
            state = states[h[0]]
            for axis in ('sex', 'identity', 'hair', 'hair_color', 'site', 'action', 'camera'):
                initial[(state['sex'] if axis in ('identity','hair') else 'all', axis)][state[axis]] += 1
            initial[(state['sex'], 'family')][state['wardrobe']['family_id']] += 1
            chain_axes[str(len({s['axis'] for s in steps}))] += 1
            directed = Counter((step['source'],step['target']) for step in steps)
            undirected = Counter(frozenset((step['source'],step['target'])) for step in steps)
            repeated_edges['chains'] += 1
            repeated_edges['chains_with_repeated_directed_edge'] += max(directed.values(),default=0) > 1
            repeated_edges['chains_with_repeated_undirected_edge'] += max(undirected.values(),default=0) > 1
            repeated_edges['chains_with_undirected_edge_traversed_at_least_three_times'] += max(undirected.values(),default=0) >= 3
            repeated_edges['chains_using_only_one_undirected_edge'] += len(undirected) == 1
            if session['kind'] == 'fork':
                t = session['fork_round']
                fs = steps[t-1]
                parent, latest = canonical_features[fs['source']], canonical_features[h[t-1]]
                other_axes_differ = any(parent.get(k) != latest.get(k) for k in (set(parent)|set(latest))-{fs['axis']})
                fork_effects['fork_chains'] += 1
                fork_effects['selected_parent_differs_from_latest_complete_state'] += parent != latest
                fork_effects['non_edited_state_differs_from_latest'] += other_axes_differ
                fork_effects['fork_target_equals_latest_complete_state'] += fs['target'] == h[t-1]
                fork_effects['fork_target_already_occurs_in_history'] += fs['target'] in h[:t]
                fork_rounds[session['length']][str(t)] += 1
                fork_parents[(session['length'], t)][str(steps[t-1]['source_position'])] += 1
                returns['last_round_fork_chains'] += t == session['length']
            revisited = False
            for t, step in enumerate(steps, 1):
                u, v, axis = step['source'], step['target'], step['axis']
                source, target = states[u], states[v]
                source_refs[u] += 1
                target_refs[v] += 1
                edge_refs[(u, v)] += 1
                d_axis, d = direction(step)
                used_directions[d_axis].add(d)
                actual_axes[axis] += 1
                camera_axis_actual[source['camera']][axis] += 1
                for eligible, dest in [(formal[u], expected_axes), (set(adjacency[u]), expected_local_axes)]:
                    weight = sum(2 if a == 'identity' else 1 for a in eligible)
                    for a in eligible:
                        dest[a] += (2 if a == 'identity' else 1)/weight
                for a in formal[u]:
                    camera_axis_expected[source['camera']][a] += (2 if a == 'identity' else 1)/sum(2 if x == 'identity' else 1 for x in formal[u])
                    formal_axis_steps[a] += 1
                    if not adjacency[u].get(a):
                        missing_axis_steps[a] += 1
                if axis == 'wardrobe':
                    modes_actual[step['mode']] += 1
                    if singles[u]:
                        modes_expected['single_piece'] += .5
                        modes_expected['whole_outfit'] += .5
                        modes = {e['mode'] for e in adjacency[u]['wardrobe']}
                        modes_support_steps['formal_single_available'] += 1
                        modes_support_steps['of_those_single_selected'] += step['mode'] == 'single_piece'
                        modes_support_steps['of_those_local_single_missing'] += 'single_piece' not in modes
                    else:
                        modes_expected['whole_outfit'] += 1
                else:
                    key = (source['sex'] if axis in ('identity', 'hair') else 'all', axis)
                    target_actual[key][target[axis]] += 1
                    legal = self.legal_targets(serial(source), axis)
                    weights = {value: 1.5 if axis == 'camera' and value in
                        ('front_head','front_upper','dolly_in_front','dolly_out_front') else 1 for value in legal}
                    denominator = sum(weights.values())
                    for value, weight in weights.items():
                        target_expected[key][value] += weight/denominator
                returns['edit_steps'] += 1
                hit = v in h[:t]
                returns['return_to_any_history_node_steps'] += hit
                revisited |= hit
                p = step['source_position']
                if p:
                    incoming = steps[p-1]
                    consecutive_axes['selected_parent_incoming_steps'] += 1
                    consecutive_axes['same_axis_steps'] += incoming['axis'] == axis
                    if incoming['axis'] == axis:
                        same_axis_returns[axis + '_opportunities'] += 1
                        same_axis_returns[axis + '_returns'] += v == incoming['source']
            returns['chains_with_any_history_node_return'] += revisited
        expected_values = {}
        for sex in self.ids:
            expected_values[(sex, 'identity')] = self.ids[sex]
            expected_values[(sex, 'hair')] = self.hairs[sex]
            expected_values[(sex, 'family')] = {f['family_id'] for f in self.catalog['sexes'][sex]['families']}
            expected_values[(sex, 'group')] = {(f['family_id'],g['group_id']) for f in self.catalog['sexes'][sex]['families'] for g in f['groups']}
            expected_values[(sex, 'family_asset')] = {asset for (asset_sex,asset) in self.assets if asset_sex == sex}
            expected_values[(sex, 'shared_shoe')] = {row['asset_id'] for row in self.catalog['sexes'][sex]['shared_shoes']}
        expected_values[('all', 'hair_color')] = self.colors
        for axis, pool in self.pools.items():
            expected_values[('all', axis)] = pool
        value_coverage = {'/'.join(key): {'observed_count': len(values[key]), 'catalog_count': len(pool),
            'missing': sorted(str(v) for v in set(pool)-values[key])} for key, pool in expected_values.items()}
        direction_coverage = {}
        for axis, possible in possible_directions.items():
            registered, used = registered_directions[axis], used_directions[axis]
            direction_coverage[axis] = {'possible_directions': len(possible), 'registered_directions': len(registered),
                'used_directions': len(used), 'used_coverage': len(used & possible)/len(possible) if possible else 0,
                'missing_used_count': len(possible-used), 'missing_used_examples_12': [list(x) for x in sorted(possible-used, key=str)[:12]]}
        initial_expected = {}
        for key, counts in initial.items():
            sex, axis = key
            pool = {'male','female'} if axis == 'sex' else expected_values[key]
            weights = {v: 1.5 if axis == 'camera' and v in
                ('front_head','front_upper','dolly_in_front','dolly_out_front') else 1 for v in pool}
            initial_expected['/'.join(key)] = distribution(counts, {v: sum(counts.values())*w/sum(weights.values()) for v,w in weights.items()})
        pairs = {}
        for (sex,a,b), observed in joints.items():
            pool_a = expected_values[(sex,a)]
            pool_b = expected_values[('all' if b == 'site' else sex,b)]
            pairs[f'{sex}/{a}__{b}'] = {'observed_pairs': len(observed),
                'catalog_cartesian_baseline': len(pool_a)*len(pool_b),
                'note': 'Cartesian baseline is descriptive; garment compatibility can limit pairs.'}
        hair_rows = [{'sex': sex, 'hair': hair, **{a: len(hair_links[(sex,hair)][a]) for a in ('identity','family','site')}}
            for sex in sorted(self.hairs) for hair in sorted(self.hairs[sex])]
        return {'counts': {'nodes': len(nodes), 'registered_edges': len(edges), 'chains': len(sessions),
                           'edit_steps': sum(edge_refs.values()), 'used_nodes': len(node_refs), 'used_edges': len(edge_refs)},
            'all_registered_nodes_used': set(node_refs) == set(states),
            'unused_node_ids': [nid for nid in states if not node_refs[nid]],
            'concentration': {'node_history_occurrences': concentration(node_refs, set(states)),
                'chain_initial_nodes': concentration(starts, set(states)), 'source_nodes': concentration(source_refs, set(states)),
                'target_nodes': concentration(target_refs, set(states)), 'edge_traversals': concentration(edge_refs, all_pairs)},
            'value_coverage': value_coverage, 'used_unique_node_value_counts': dict(node_marginals),
            'feature_coverage_scope': 'Values and cross-attribute associations count only nodes occurring in actual chains.', 'direction_coverage': direction_coverage,
            'direction_scope': 'Non-wardrobe and single-piece opportunities are enumerated over actual candidate source states; whole family baseline is all catalog other-family directions. All actual edges receive formal semantic checks.',
            'hair_associations': {'per_hair': hair_rows, 'summary': {sex: {a: summary(row[a] for row in hair_rows if row['sex']==sex)
                for a in ('identity','family','site')} for sex in self.ids}}, 'cross_attribute_pairs': pairs,
            'local_support': {'formal_axis_source_nodes': dict(formal_axis_nodes), 'missing_local_axis_source_nodes': dict(missing_axis_nodes),
                'formal_axis_step_opportunities': dict(formal_axis_steps), 'missing_local_axis_step_opportunities': dict(missing_axis_steps),
                'local_target_degree_by_formally_eligible_axis': dict(local_degrees),
                'wardrobe_source_mode_support': dict(mode_nodes), 'wardrobe_step_mode_support': dict(modes_support_steps)},
            'axis_distribution_against_formal_eligibility': distribution(actual_axes, expected_axes),
            'axis_distribution_by_source_camera': {camera: distribution(counts,camera_axis_expected[camera]) for camera,counts in camera_axis_actual.items()},
            'axis_distribution_against_local_support': distribution(actual_axes, expected_local_axes),
            'wardrobe_mode_distribution': distribution(modes_actual, modes_expected),
            'initial_distribution_targets': initial_expected,
            'edit_target_global_distribution_targets': {'/'.join(k): distribution(v, target_expected[k]) for k,v in target_actual.items()},
            'fork_round_distributions': {str(L): distribution(c,{str(t):sum(c.values())/(L-1) for t in range(2,L+1)}) for L,c in fork_rounds.items()},
            'fork_parent_distributions': {f'L{L}/t{t}': distribution(c,{str(p):sum(c.values())/(t-1) for p in range(t-1)}) for (L,t),c in fork_parents.items()},
            'natural_revisit_metrics': {**returns, 'same_axis_selected_parent_returns': dict(same_axis_returns),
                'selected_parent_axis_repetition': dict(consecutive_axes), 'distinct_axes_per_chain': dict(chain_axes)},
            'fork_effect_metrics': {**fork_effects,
                'scope':'Complete-state difference and non-edited-field difference are separate descriptive metrics. Non-edited-field difference means the saved fork result inherits a different state than applying the same axis target to the latest node.'},
            'within_chain_repeated_edge_metrics': {**repeated_edges,
                'scope':'Undirected edges combine the two directions of one exact node pair; multiple traversals and one-pair-only chains are permitted and descriptive.'},
            'interpretation': 'Diversity and probability differences are descriptive, not new acceptance thresholds. Finite local targets and natural returns never fail integrity. Initial and target histograms summarize balance goals; legality-conditioned axis expectations use actual selected parents.'}


def write_markdown(report, path):
    lines = ['# 第三版独立核验', '', f"候选：`{report['candidate']}`", '',
             f"硬结构检查：{'通过' if report['integrity_success'] else '未通过'}；跨划分完整状态重合 {report['canonical_cross_split_overlap_count']}。", '',
             '局部候选数、自然回访和分布差异均为描述指标，不新增硬阈值。尚未渲染或检查画面。', '']
    for split, data in report['splits'].items():
        q = data['quality']; c = q['counts']; nc = q['concentration']['node_history_occurrences']; ec = q['concentration']['edge_traversals']
        lines += [f'## {split}', '', f"实际 {c['nodes']} 节点、{c['registered_edges']} 边、{c['chains']} 链、{c['edit_steps']} 次编辑；使用 {c['used_nodes']} 节点、{c['used_edges']} 边。", '',
            f"最热节点占出现次数 {nc['top_1_share']:.2%}，前10节点 {nc['top_10_share']:.2%}；最热边占编辑 {ec['top_1_share']:.2%}，前10边 {ec['top_10_share']:.2%}。", '',
            f"按源视频正式可编辑属性计算，属性比例总变差 {q['axis_distribution_against_formal_eligibility']['total_variation']:.2%}；衣物单件/整套比例总变差 {q['wardrobe_mode_distribution']['total_variation']:.2%}。", '',
            '| 编辑方向 | 实际使用 | 可用方向基线 | 覆盖 |', '|---|---:|---:|---:|']
        for axis, row in q['direction_coverage'].items():
            lines.append(f"| {axis} | {row['used_directions']} | {row['possible_directions']} | {row['used_coverage']:.1%} |")
        lines += ['', '方向基线详见JSON中的范围说明；衣物整套按family方向统计。', '']
        for sex, rows in q['hair_associations']['summary'].items():
            lines.append(f"{sex} 每款发型关联身份/服装组/场景的中位数：{rows['identity']['median']} / {rows['family']['median']} / {rows['site']['median']}；最少：{rows['identity']['min']} / {rows['family']['min']} / {rows['site']['min']}。")
        returns = q['natural_revisit_metrics']
        lines += ['', f"回到链内完整旧视频 {returns.get('return_to_any_history_node_steps',0)}/{c['edit_steps']} 次；单属性整链 {returns['distinct_axes_per_chain'].get('1',0)}/{c['chains']} 条。", '']
    if report['errors']:
        lines += ['## 硬检查错误', '', '```json', json.dumps(report['errors'],ensure_ascii=False,indent=2), '```', '']
    path.write_text('\n'.join(lines), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--partial', action='store_true')
    parser.add_argument('--train-dir', type=Path)
    parser.add_argument('--test-dir', type=Path)
    args = parser.parse_args()
    if bool(args.train_dir) != bool(args.test_dir):
        parser.error('--train-dir and --test-dir must be supplied together')
    root = args.candidate.resolve()
    split_paths = {split: root/split for split in ('train','test')}
    if args.train_dir:
        split_paths = {'train':args.train_dir.resolve(), 'test':args.test_dir.resolve()}
    class Routed:
        def __truediv__(self, split):
            return split_paths[split]
    verifier = LocalAudit(partial=args.partial, camera_target_policy='weighted_four')
    report = {'candidate':str(root), 'rendered':False, 'visual_verified':False,
        'contract_revision':'2026-10-21 finite local targets allowed, overall diversity retained',
        'independence':'No generator import; v1 semantic checks plus v2 independent single-piece enumeration.',
        'inputs_sha256':{str(p):sha(p) for p in [V1/'rules.json',V1/'catalog.json',V1/'verify_trial.py',V1/'normalize_catalog.py',V2/'verify_joint.py',Path(__file__)]},
        'splits':{}}
    canonical = {}
    for split,directory in split_paths.items():
        integrity,canonical[split] = verifier.verify_split(Routed(),split,True)
        quality = verifier.quality(directory)
        report['splits'][split] = {'path':str(directory),'integrity':integrity,'quality':quality}
        for name in ('nodes.json','edges.json','sessions.jsonl'):
            report['inputs_sha256'][str(directory/name)] = sha(directory/name)
    overlap = canonical['train'] & canonical['test']
    verifier.check(not overlap,'split_complete_canonical_main_nodes_disjoint',{'count':len(overlap)})
    report.update(canonical_cross_split_overlap_count=len(overlap),integrity_success=not verifier.errors,
        errors=dict(verifier.errors),error_examples=dict(verifier.examples),passed_checks=dict(verifier.counts),
        expected_shortfalls=verifier.expected_shortfalls)
    output = args.output or HERE/('verification_'+root.name+'.json')
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    write_markdown(report,output.with_suffix('.md'))
    print(json.dumps({'integrity_success':report['integrity_success'],'errors':report['errors'],'report':str(output)},ensure_ascii=False))
    raise SystemExit(0 if report['integrity_success'] else 1)


if __name__ == '__main__':
    main()
