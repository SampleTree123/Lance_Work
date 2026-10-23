"""Readable comparison of independent verify_local JSON reports; no builder imports."""
from __future__ import annotations
import argparse
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reports', nargs='+', type=Path, required=True)
    p.add_argument('--labels', nargs='+')
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    reports = [json.loads(path.read_text(encoding='utf-8-sig')) for path in a.reports]
    labels = a.labels or [Path(r['candidate']).name for r in reports]
    if len(labels) != len(reports):
        p.error('--labels must match --reports count')
    lines = ['# 候选实际质量对比', '',
        '全部数字来自独立验证器读取的节点、边和链。方向数按不同源值→目标值计数，不是链数；有限局部支持和自然回访均不作为硬失败。', '']
    for split in ('train','test'):
        qs = [r['splits'][split]['quality'] for r in reports]
        lines += [f'## {split}', '', '| 指标 | '+' | '.join(labels)+' |', '|---|'+'---:|'*len(labels)]
        metrics = [
            ('节点（候选/实际使用）', lambda q:f"{q['counts']['nodes']} / {q['counts']['used_nodes']}"),
            ('边（候选/实际使用）', lambda q:f"{q['counts']['registered_edges']} / {q['counts']['used_edges']}"),
            ('实际链', lambda q:str(q['counts']['chains'])),
            ('起点四个身份镜头占比（目标26.09%）', lambda q: f"{sum(row['actual'] for camera,row in q['initial_distribution_targets']['all/camera']['values'].items() if camera in ('front_head','front_upper','dolly_in_front','dolly_out_front')) / q['counts']['chains']:.2%}"),
            ('正式属性权重与实际比例总变差', lambda q:f"{q['axis_distribution_against_formal_eligibility']['total_variation']:.2%}"),
            ('单件/整套目标与实际比例总变差', lambda q:f"{q['wardrobe_mode_distribution']['total_variation']:.2%}"),
            ('正式允许单件时实际选单件（目标50%）', lambda q:f"{q['local_support']['wardrobe_step_mode_support'].get('of_those_single_selected',0) / q['local_support']['wardrobe_step_mode_support'].get('formal_single_available',1):.2%}"),
            ('前10热门节点占出现次数', lambda q:f"{q['concentration']['node_history_occurrences']['top_10_share']:.2%}"),
            ('前10热门边占编辑次数', lambda q:f"{q['concentration']['edge_traversals']['top_10_share']:.2%}"),
            ('回到链内完整旧视频的编辑步', lambda q:f"{q['natural_revisit_metrics'].get('return_to_any_history_node_steps',0)/q['counts']['edit_steps']:.2%}"),
            ('包含完整旧视频回访的链', lambda q:f"{q['natural_revisit_metrics'].get('chains_with_any_history_node_return',0)/q['counts']['chains']:.2%}"),
            ('单属性整链', lambda q:f"{q['natural_revisit_metrics']['distinct_axes_per_chain'].get('1',0)/q['counts']['chains']:.2%}"),
            ('分叉源完整状态与最新视频不同', lambda q:f"{q['fork_effect_metrics'].get('selected_parent_differs_from_latest_complete_state',0)/q['fork_effect_metrics'].get('fork_chains',1):.2%}"),
            ('分叉继承的未编辑属性与最新视频不同', lambda q:f"{q['fork_effect_metrics'].get('non_edited_state_differs_from_latest',0)/q['fork_effect_metrics'].get('fork_chains',1):.2%}"),
            ('整链仅在一对完整视频间编辑', lambda q:f"{q['within_chain_repeated_edge_metrics'].get('chains_using_only_one_undirected_edge',0)/q['counts']['chains']:.2%}"),
            ('一条边正反合计至少经过3次的链', lambda q:f"{q['within_chain_repeated_edge_metrics'].get('chains_with_undirected_edge_traversed_at_least_three_times',0)/q['counts']['chains']:.2%}"),
        ]
        for label, getter in metrics:
            lines.append('| '+label+' | '+' | '.join(getter(q) for q in qs)+' |')
        lines += ['', '总变差越小表示全局属性比例越接近正式目标；这不能证明每个源视频的条件概率完全一致。四个身份镜头各权重1.5，其他17镜头各权重1，目标合计6/23=26.09%；这是全目录平衡目标，未声称所有条件下精确相同。', '',
            '| 实际使用的编辑方向 | '+' | '.join(labels)+' |', '|---|'+'---:|'*len(labels)]
        for axis in ('identity','hair','hair_color','wardrobe_single_piece','wardrobe_whole_family','action','camera','site'):
            lines.append('| '+axis+' | '+' | '.join(str(q['direction_coverage'].get(axis,{}).get('used_directions',0)) for q in qs)+' |')
        lines += ['', '## 每款发型跨属性搭配（中位数）', '',
            '| sex / 搭配 | '+' | '.join(labels)+' |', '|---|'+'---:|'*len(labels)]
        for sex in ('female','male'):
            for axis in ('identity','family','site'):
                lines.append('| '+sex+' / '+axis+' | '+' | '.join(str(q['hair_associations']['summary'][sex][axis]['median']) for q in qs)+' |')
        lines += ['']
    lines += ['## 证据', '']
    for label, source, report in zip(labels,a.reports,reports):
        lines.append(f"- {label}：`{source.resolve()}`；硬检查{'通过' if report['integrity_success'] else '未通过'}；跨划分完整状态重合 {report['canonical_cross_split_overlap_count']}。")
    lines += ['', '尚未渲染或检查画面；分布与方向覆盖仅评价本次离线构造。', '']
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text('\n'.join(lines),encoding='utf-8')
    print(str(a.output))


if __name__ == '__main__':
    main()
