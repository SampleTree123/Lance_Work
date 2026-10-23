"""Independent same-budget v4 comparison; diversity metrics are descriptive.

No candidate-generator imports. Reuses v1 semantic/provenance/session checks,
v2 independent garment enumeration, and v3 local-support diagnostics.
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
OUTPUTS = HERE.parents[1]
V3 = OUTPUTS / 'dataset_local_support_20261021_v3'
sys.path.insert(0, str(V3 / 'audit'))
from verify_local import LocalAudit, AXES, read, serial, sha, summary


def histogram(values):
    values = list(values)
    return {**summary(values), 'histogram': dict(sorted(Counter(map(str, values)).items(), key=lambda r: int(r[0])))}


def share(n, denominator):
    return n / denominator if denominator else 0


def chain_summary(rows):
    n = len(rows)
    result = {'chains': n, 'distinct_axes': histogram(r['distinct_axes'] for r in rows)}
    for k in (3, 4, 5):
        count = sum(r['distinct_axes'] >= k for r in rows)
        result[f'at_least_{k}_axes_count'] = count
        result[f'at_least_{k}_axes_share'] = share(count, n)
    for key in ('history_revisit', 'mono_axis', 'same_pair_only', 'pair_traversed_at_least_three',
                'repeated_directed_edge', 'repeated_undirected_edge'):
        count = sum(r[key] for r in rows)
        result[key + '_count'] = count
        result[key + '_share'] = share(count, n)
    forks = [r for r in rows if r['kind'] == 'fork']
    result['fork_chains'] = len(forks)
    for key in ('fork_source_differs_from_latest', 'fork_preserves_different_non_edited_state',
                'fork_target_equals_latest', 'fork_target_in_history'):
        count = sum(r[key] for r in forks)
        result[key + '_count'] = count
        result[key + '_share_of_forks'] = share(count, len(forks))
    return result


def extra_metrics(verifier, directory):
    nodes = read(directory / 'nodes.json')
    edges = read(directory / 'edges.json')
    sessions = [json.loads(s) for s in (directory / 'sessions.jsonl').read_text(encoding='utf-8').splitlines() if s]
    states = {n['id']: n['state'] for n in nodes}
    used = {nid for s in sessions for nid in s['history']}
    canonical = {nid: json.loads(verifier.canonical(state)) for nid, state in states.items()}
    adjacency = defaultdict(set)
    for e in edges:
        adjacency[e['source']].add(e['axis'])
    formal = {}
    for nid, state in states.items():
        axes = verifier.formal_axes(state)
        if 'hair' in axes and not verifier.legal_targets(serial(state), 'hair'):
            axes = axes - {'hair'}
        formal[nid] = axes
    chain_rows, buckets = [], defaultdict(list)
    sequence = {'chronological': {2: Counter(), 3: Counter()}, 'selected_parent_path': {2: Counter(), 3: Counter()}}
    source_ids = []
    source_buckets = defaultdict(list)
    for session in sessions:
        steps, h = session['steps'], session['history']
        axes = [s['axis'] for s in steps]
        directed = Counter((s['source'], s['target']) for s in steps)
        pairs = Counter(tuple(sorted((s['source'], s['target']))) for s in steps)
        row = {'kind': session['kind'], 'length': session['length'], 'distinct_axes': len(set(axes)),
               'mono_axis': len(set(axes)) == 1, 'same_pair_only': len(pairs) == 1,
               'pair_traversed_at_least_three': max(pairs.values(), default=0) >= 3,
               'repeated_directed_edge': max(directed.values(), default=0) > 1,
               'repeated_undirected_edge': max(pairs.values(), default=0) > 1,
               'history_revisit': any(s['target'] in h[:t] for t, s in enumerate(steps, 1))}
        if session['kind'] == 'fork':
            t = session['fork_round']
            fs = steps[t - 1]
            parent, latest = canonical[fs['source']], canonical[h[t - 1]]
            row.update(fork_source_differs_from_latest=parent != latest,
                       fork_preserves_different_non_edited_state=any(parent.get(k) != latest.get(k)
                           for k in (set(parent) | set(latest)) - {fs['axis']}),
                       fork_target_equals_latest=fs['target'] == h[t - 1],
                       fork_target_in_history=fs['target'] in h[:t])
        chain_rows.append(row)
        buckets[f"{session['kind']}/L{session['length']}"] .append(row)
        buckets[f"all/L{session['length']}"] .append(row)
        buckets[session['kind']].append(row)
        paths = [[]]
        for step in steps:
            source_ids.append(step['source'])
            source_buckets[f"{session['kind']}/L{session['length']}"] .append(step['source'])
            path = paths[step['source_position']] + [step['axis']]
            paths.append(path)
            for order in (2, 3):
                if len(path) >= order:
                    sequence['selected_parent_path'][order][tuple(path[-order:])] += 1
        for order in (2, 3):
            sequence['chronological'][order].update(tuple(axes[i:i+order]) for i in range(len(axes)-order+1))
    sequence_metrics = {}
    for mode, orders in sequence.items():
        sequence_metrics[mode] = {}
        for order, counts in orders.items():
            universe = list(itertools.product(AXES, repeat=order))
            sequence_metrics[mode][str(order)] = {'observed_unique': len(counts),
                'all_axis_sequences_descriptive_baseline': len(universe),
                'coverage': share(len(counts), len(universe)), 'occurrences': sum(counts.values()),
                'counts': {'>'.join(k): v for k, v in sorted(counts.items())},
                'missing': ['>'.join(k) for k in universe if k not in counts]}
    def available(ids):
        ids = list(ids)
        return {'observations': len(ids), 'formal_legal_axis_count': histogram(len(formal[nid]) for nid in ids),
                'locally_registered_axis_count': histogram(len(adjacency[nid]) for nid in ids),
                'formal_axes_missing_locally_count': histogram(len(formal[nid] - adjacency[nid]) for nid in ids)}
    pairs = {}
    # Count actual value pairs, including zero-count catalog values in partner breadth.
    # All associations count only unique main nodes used by actual sessions.
    for sex in sorted(verifier.ids):
        identity_pool = verifier.ids[sex]
        pool = verifier.catalog['sexes'][sex]
        b_pools = {'hair': verifier.hairs[sex], 'wardrobe_family': {f['family_id'] for f in pool['families']},
                   'wardrobe_group': {(f['family_id'], g['group_id']) for f in pool['families'] for g in f['groups']},
                   'site': verifier.pools['site'], 'action': verifier.pools['action']}
        for axis, b_pool in b_pools.items():
            counts = Counter()
            for nid in used:
                state = states[nid]
                if state['sex'] != sex:
                    continue
                value = (state['wardrobe']['family_id'] if axis == 'wardrobe_family' else
                         (state['wardrobe']['family_id'], state['wardrobe']['group_id']) if axis == 'wardrobe_group' else state[axis])
                counts[state['identity'], value] += 1
            per_identity = {str(identity): len({b for a, b in counts if a == identity}) for identity in sorted(identity_pool)}
            per_value = {serial(value): len({a for a, b in counts if b == value}) for value in sorted(b_pool, key=str)}
            denominator = len(identity_pool) * len(b_pool)
            pairs[f'{sex}/identity__{axis}'] = {'observed_pairs': len(counts), 'catalog_cartesian_baseline': denominator,
                'coverage': share(len(counts), denominator), 'unique_node_pair_counts': [
                    {'identity': a, 'value': b, 'nodes': n} for (a, b), n in sorted(counts.items(), key=str)],
                'partner_breadth_per_identity': histogram(per_identity.values()), 'per_identity': per_identity,
                'identity_breadth_per_partner': histogram(per_value.values()), 'per_partner': per_value}
    roots = sum(n.get('created_by', {}).get('parent') is None for n in nodes)
    catalog_values = {'identity': set().union(*map(set, verifier.ids.values())),
        'hair_unique_ids': set().union(*map(set, verifier.hairs.values())),
        'wardrobe_family': {f['family_id'] for p in verifier.catalog['sexes'].values() for f in p['families']},
        'wardrobe_group': {(f['family_id'], g['group_id']) for p in verifier.catalog['sexes'].values()
                           for f in p['families'] for g in f['groups']}}
    used_values = {'identity': {states[nid]['identity'] for nid in used},
        'hair_unique_ids': {states[nid]['hair'] for nid in used},
        'wardrobe_family': {states[nid]['wardrobe']['family_id'] for nid in used},
        'wardrobe_group': {(states[nid]['wardrobe']['family_id'], states[nid]['wardrobe']['group_id']) for nid in used}}
    catalog_totals = {axis: {'observed_count': len(used_values[axis]), 'catalog_count': len(pool),
        'missing': sorted(map(str, pool-used_values[axis]))} for axis, pool in catalog_values.items()}
    return {'chains': {'all': chain_summary(chain_rows), 'by_kind_and_length': {k: chain_summary(v) for k, v in sorted(buckets.items())}},
        'axis_sequence_coverage': sequence_metrics,
        'available_axis_counts': {'all_registered_nodes': available(states), 'used_unique_nodes': available(used),
            'selected_parent_occurrences': available(source_ids),
            'selected_parent_occurrences_by_kind_length': {k: available(v) for k, v in sorted(source_buckets.items())}},
        'identity_cross_attribute_value_pairs': pairs,
        'aggregate_used_node_catalog_coverage': catalog_totals,
        'pair_scope': 'Actual value pairs in unique used nodes; Cartesian denominator is descriptive and may include compatibility-limited combinations.',
        'provenance_counts': {'seed_nodes': roots, 'nodes_with_creation_parent': len(nodes)-roots},
        'metric_definitions': {'same_pair_only': 'All edits traverse one exact undirected complete-state node pair.',
            'pair_traversed_at_least_three': 'At least three edits traverse one exact undirected pair in a chain.',
            'fork_preserves_different_non_edited_state': 'Selected historical source differs from latest complete node in a semantic field other than the edited axis; independent atomic inheritance checks preserve this difference.',
            'selected_parent_path': 'Each new edit contributes its terminal axis pair/triple along its actual inherited source path.',
            'chronological': 'Adjacent edit axes in recorded round order, including the change to an abandoned branch at a fork.'}}


def conditional_wardrobe_modes(quality):
    support = quality['local_support']['wardrobe_step_mode_support']
    eligible = support.get('formal_single_available', 0)
    singles = support.get('of_those_single_selected', 0)
    total = quality['wardrobe_mode_distribution']['n']
    return {'formal_single_available_steps': eligible, 'single_piece_selected': singles,
        'whole_outfit_selected_when_single_available': eligible-singles,
        'conditional_single_share': share(singles, eligible), 'conditional_single_target_share': 0.5,
        'conditional_single_target_count': eligible*0.5,
        'conditional_single_deviation_percentage_points': 100*(share(singles, eligible)-0.5) if eligible else None,
        'formal_single_unavailable_wardrobe_steps': total-eligible,
        'scope': '50/50 target is conditioned on independently enumerated legal single-piece availability at the actual selected source; observed finite-sample deviation is descriptive.'}


def evaluate(root):
    verifier = LocalAudit(camera_target_policy='weighted_four')
    result = {'candidate': str(root), 'splits': {}, 'inputs_sha256': {}}
    canonical = {}
    for split in ('train', 'test'):
        directory = root / split
        prior_errors = Counter(verifier.errors)
        integrity, canonical[split] = verifier.verify_split(root, split, True)
        split_errors = dict(Counter(verifier.errors) - prior_errors)
        quality = verifier.quality(directory)
        extra = extra_metrics(verifier, directory)
        extra['conditional_wardrobe_mode_target'] = conditional_wardrobe_modes(quality)
        result['splits'][split] = {'integrity_success': not split_errors, 'errors': split_errors,
                                  'integrity': integrity, 'quality': quality, 'explicit_metrics': extra}
        for name in ('nodes.json', 'edges.json', 'sessions.jsonl'):
            result['inputs_sha256'][str(directory/name)] = sha(directory/name)
    overlap = canonical['train'] & canonical['test']
    verifier.check(not overlap, 'split_complete_canonical_main_nodes_disjoint', {'count': len(overlap)})
    result.update(integrity_success=not verifier.errors, errors=dict(verifier.errors),
                  error_examples=dict(verifier.examples), passed_checks=dict(verifier.counts),
                  canonical_cross_split_overlap_count=len(overlap))
    return result


def markdown(report):
    lines = ['# v4 同预算独立比较', '', '全部多样性指标仅作描述，不新增最少属性数、禁止回访或分叉可观察性门槛。未渲染，未检查画面。', '',
             '| 候选/划分 | 结构/配额检查 | 实际链数 | 节点/边使用 | 平均属性数 | ≥3属性 | ≥4属性 | ≥5属性 | 回访链 | 单属性链 | 单对往返链 | 历史非编辑状态区别 |',
             '|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for name, result in report['runs'].items():
        for split, data in result['splits'].items():
            c = data['quality']['counts']; row = data['explicit_metrics']['chains']['all']
            lines.append(f"| {name}/{split} | {'通过' if data['integrity_success'] else '失败'} | {c['chains']} | {c['used_nodes']}/{c['nodes']}；{c['used_edges']}/{c['registered_edges']} | {row['distinct_axes']['mean']:.3f} | {row['at_least_3_axes_share']:.1%} | {row['at_least_4_axes_share']:.1%} | {row['at_least_5_axes_share']:.1%} | {row['history_revisit_share']:.1%} | {row['mono_axis_share']:.1%} | {row['same_pair_only_share']:.1%} | {row['fork_preserves_different_non_edited_state_share_of_forks']:.1%} |")
    for name, result in report['runs'].items():
        lines += ['', f'## {name}', '', f"路径：`{result['candidate']}`。跨划分完整状态重合：{result['canonical_cross_split_overlap_count']}。", '']
        for split, data in result['splits'].items():
            q = data['quality']; x = data['explicit_metrics']
            lines += [f'### {split}', '', '| 类型/长度 | 链数 | 平均属性数 | 属性数直方图 | ≥3属性 | ≥4属性 | ≥5属性 | 回访 | 单对往返 |', '|---|---:|---:|---|---:|---:|---:|---:|---:|']
            for key, row in x['chains']['by_kind_and_length'].items():
                lines.append(f"| {key} | {row['chains']} | {row['distinct_axes']['mean']:.3f} | {json.dumps(row['distinct_axes']['histogram'])} | {row['at_least_3_axes_share']:.1%} | {row['at_least_4_axes_share']:.1%} | {row['at_least_5_axes_share']:.1%} | {row['history_revisit_share']:.1%} | {row['same_pair_only_share']:.1%} |")
            lines += ['', '| 目录值 | 使用/可用 |', '|---|---:|']
            for key, row in q['value_coverage'].items():
                lines.append(f"| {key} | {row['observed_count']}/{row['catalog_count']} |")
            lines += ['', '| 身份跨属性值对 | 实际/目录笛卡尔基线 | 每身份关联数均值 |', '|---|---:|---:|']
            for key, row in x['identity_cross_attribute_value_pairs'].items():
                lines.append(f"| {key} | {row['observed_pairs']}/{row['catalog_cartesian_baseline']} | {row['partner_breadth_per_identity']['mean']:.2f} |")
            n = q['concentration']['node_history_occurrences']; e = q['concentration']['edge_traversals']
            a = x['available_axis_counts']['selected_parent_occurrences']
            seq = x['axis_sequence_coverage']['chronological']
            modes = x['conditional_wardrobe_mode_target']
            lines += ['', f"最热节点/前10节点引用份额：{n['top_1_share']:.2%}/{n['top_10_share']:.2%}；最热边/前10边：{e['top_1_share']:.2%}/{e['top_10_share']:.2%}。", '',
                f"实际编辑源平均正式合法/图内可用属性数：{a['formal_legal_axis_count']['mean']:.2f}/{a['locally_registered_axis_count']['mean']:.2f}；按轮序属性对/三元序列覆盖：{seq['2']['observed_unique']}/49、{seq['3']['observed_unique']}/343。", '',
                f"正式合法属性权重目标总变差：{q['axis_distribution_against_formal_eligibility']['total_variation']:.2%}；服装模式目标总变差：{q['wardrobe_mode_distribution']['total_variation']:.2%}；初始镜头加权目标总变差：{q['initial_distribution_targets']['all/camera']['total_variation']:.2%}。", '',
                f"独立枚举确认可改单件的服装编辑中，单件/整套为 {modes['single_piece_selected']}/{modes['whole_outfit_selected_when_single_available']}，单件比例 {modes['conditional_single_share']:.2%}（目标50%）；另有 {modes['formal_single_unavailable_wardrobe_steps']} 次服装编辑源没有合法单件目标。", '']
        if result['errors']:
            lines += ['```json', json.dumps(result['errors'], ensure_ascii=False, indent=2), '```', '']
    lines += ['', 'JSON保存全部精确配额、语义/服装/历史继承/创建来源检查、目录缺失、引用集中程度、编辑方向、值对明细、序列计数和可用属性数直方图。目录笛卡尔积仅作描述，不代表全部组合都合法。']
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paths', nargs='*', type=Path)
    parser.add_argument('--candidate', action='append', default=[], type=Path)
    parser.add_argument('--baseline', type=Path, default=V3/'linked_complete')
    parser.add_argument('--output', type=Path, default=HERE/'comparison.json')
    args = parser.parse_args()
    candidates = args.candidate + args.paths
    report = {'scope': 'Offline same-budget semantic integrity and descriptive diversity; no media or visual verification.',
              'independence': 'No generator import. Earlier independent v1/v2/v3 validators plus explicit measured metrics.',
              'contract': 'Current finite-local-target contract; no diversity acceptance threshold added.',
              'inputs_sha256': {str(p): sha(p) for p in (Path(__file__), V3/'CURRENT_RULES.json',
                  V3/'audit'/'verify_local.py', OUTPUTS/'dataset_joint_build_20261021_v2'/'audit'/'verify_joint.py',
                  OUTPUTS/'dataset_trial_build_20261021_v1'/'verify_trial.py',
                  OUTPUTS/'dataset_trial_build_20261021_v1'/'normalize_catalog.py',
                  OUTPUTS/'dataset_trial_build_20261021_v1'/'catalog.json',
                  OUTPUTS/'dataset_trial_build_20261021_v1'/'rules.json')}, 'runs': {}}
    roots = [('baseline_v3', args.baseline.resolve())] + [(p.resolve().name, p.resolve()) for p in candidates]
    for name, root in roots:
        if name in report['runs']:
            parser.error(f'Duplicate candidate label {name}; use directories with distinct names')
        print(f'Evaluating {name}: {root}', flush=True)
        report['runs'][name] = evaluate(root)
        print(json.dumps({'run': name, 'integrity_success': report['runs'][name]['integrity_success'],
                          'errors': report['runs'][name]['errors']}, ensure_ascii=False), flush=True)
    report['integrity_success'] = all(r['integrity_success'] for r in report['runs'].values())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    args.output.with_suffix('.md').write_text(markdown(report), encoding='utf-8')
    print(json.dumps({'integrity_success': report['integrity_success'], 'report': str(args.output)}, ensure_ascii=False))
    return 0 if report['integrity_success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
