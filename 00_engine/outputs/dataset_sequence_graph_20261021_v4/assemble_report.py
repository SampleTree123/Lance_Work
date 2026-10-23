"""Assemble the scoped research delivery; do not promote diagnostic graphs."""
from pathlib import Path
import hashlib,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[2]
FP=REPO/'20_planning/data_design/character_creator/full_process'
V3=ROOT.parent/'dataset_local_support_20261021_v3'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    comparison=read(ROOT/'audit/final_comparison.json');runs=comparison['runs'];candidate=runs['rotated'];baseline=runs['baseline_v3']
    stability=read(ROOT/'audit/sampling_stability.json')
    (ROOT/'CURRENT_RULES.json').write_bytes((V3/'CURRENT_RULES.json').read_bytes())
    contract=FP/'technical/dataset/DATASET_TRIAL_CONTRACT_20261021.md'
    lines=['# 第四轮同预算构图试验', '',
           '结论：宽属性、少取值的局部组合显著改善链内属性数，但会压缩人物的跨服装/发型/动作/场景搭配。当前最佳折中诊断 `rotated` 仍有服装单件比例不足，未替换v3候选，也未获准正式渲染。', '',
           '本轮只做离线节点/边/编辑链构造。训练2500节点、12000链；测试500节点、2400链。没有UE调用、媒体生成或新参考素材预算承诺。', '',
           '## 先看用户关心的指标', '',
           '同属性重复只计一次，分叉按完整对话中实际发生的全部编辑计数。服装上衣/裤子等均属于服装属性。', '',
           '| 编辑次数 | 旧训练 | 新训练 | 旧测试 | 新测试 |', '|---|---:|---:|---:|---:|']
    for length in range(2,6):
        vals=[runs[n]['splits'][s]['explicit_metrics']['chains']['by_kind_and_length'][f'all/L{length}']['distinct_axes']['mean'] for s in ('train','test') for n in ('baseline_v3','rotated')]
        lines.append('| '+str(length)+' | '+' | '.join(f'{v:.3f}' for v in vals)+' |')
    lines += ['', '没有要求每步换不同属性，也没有禁止回退。交付链沿用v3同一采样器；对照额外使用三个匹配抽样种子，因此改善不是仅由换随机种子产生。这里没有验证不同构图种子的稳健性。', '',
              '## 四条实际路线', '',
              '| 路线 | 结果与问题 |', '|---|---|',
              '| sequence：先构造五步编辑，再共享合法换序路径 | 改善有限，实际使用2360/2500和455/500节点；测试还有未使用类别。说明本次实现未把顺序覆盖转化成均匀的可选编辑，不代表所有序列规划方法无效。 |',
              '| wide：尽量完整的宽属性小组合 | 链内属性数高，但正面身份镜头初始占比约86%/69%；训练短链缺99条。只作诊断。 |',
              '| wide_balanced：给宽属性组合分配更多非正面镜头 | 配额和节点使用完整，但测试固定变发型/衣物/镜头，导致发色/动作/场景编辑过少。 |',
              '| rotated：在不同局部组合轮换可编辑属性 | 解决上一版明显属性偏置，配额/覆盖通过；仍损失搭配广度，且单件服装编辑比例不足。是本轮主要讨论对象，非正式接受候选。 |', '',
              '构图阶段的启发式与最终采样规则分开：sequence规划时偏向未覆盖的顺序和未编辑轴（已用轴权重乘0.45），但交付链没有强制不重复；组合候选通过合法单属性边逐步产生，而非任意挑独立节点再拼链。所有非种子节点保存真实创建边。', '',
              '## 收益与剩余代价', '']
    for split,cn in [('train','训练'),('test','测试')]:
        old=baseline['splits'][split];new=candidate['splits'][split];x=new['explicit_metrics'];q=new['quality'];o=old['explicit_metrics']['chains']['all'];r=x['chains']['all'];m=x['conditional_wardrobe_mode_target']
        def pair_total(data,axis):return sum(v['observed_pairs'] for k,v in data['explicit_metrics']['identity_cross_attribute_value_pairs'].items() if k.endswith('__'+axis))
        lines += [f'### {cn}', '',
                  f"- 原子编辑、正式服装合法性、源历史版本完整继承、配额、结构去重和跨划分完整节点隔离通过；实际使用全部{q['counts']['nodes']}个节点。",
                  f"- 涉及至少三个属性的链：{o['at_least_3_axes_share']:.1%} → {r['at_least_3_axes_share']:.1%}；至少四个属性：{o['at_least_4_axes_share']:.1%} → {r['at_least_4_axes_share']:.1%}。",
                  f"- 含旧节点回访的链：{o['history_revisit_share']:.1%} → {r['history_revisit_share']:.1%}。这与不同属性数是两个指标。",
                  f"- 分叉中保留属性体现历史区别：{o['fork_preserves_different_non_edited_state_share_of_forks']:.1%} → {r['fork_preserves_different_non_edited_state_share_of_forks']:.1%}。",
                  f"- 实际人物×发型搭配：{pair_total(old,'hair')} → {pair_total(new,'hair')}；人物×服装来源组：{pair_total(old,'wardrobe_family')} → {pair_total(new,'wardrobe_family')}。目录类别仍齐全，实际搭配变少。",
                  f"- 在正式允许单件替换的服装编辑中，单件占{m['single_piece_selected']}/{m['formal_single_available_steps']}={m['conditional_single_share']:.2%}，目标50%。正式不允许单件的整套编辑未放进分母。",
                  f"- 按实际源状态正式可编辑属性计算，七属性频次总变差{q['axis_distribution_against_formal_eligibility']['total_variation']:.2%}；初始镜头分布总变差{q['initial_distribution_targets']['all/camera']['total_variation']:.2%}。这是偏差描述，不是新通过阈值。", '']
    lines += ['两划分实际链仍覆盖40人物、28独立发型（男女适配目录合计33项）、37服装来源组、45合法搭配组、7色、25动作、21镜头和21点位。并不代表全部衣物单品或全部搭配覆盖。', '',
              '服装偏差来自图内缺少单件目标，不是仅有抽样随机波动：按当前实际源节点分布，即使所有有单件边的机会都选择单件，训练/测试上限也只有约38.85%/30.03%。需要补单件连接或重新分配服装编辑源，不能仅加权就宣称恢复50/50。', '',
              '## 三个抽样种子的复核', '', '| 图/划分 | 五步链平均属性数范围 | 完成链数 |', '|---|---:|---|']
    for name,splits in stability['runs'].items():
        for split,rows in splits.items():
            vals=[r['by_length']['5']['mean_axes'] for r in rows]
            lines.append(f"| {name}/{split} | {min(vals):.3f}–{max(vals):.3f} | {', '.join(str(r['chains']) for r in rows)} |")
    lines += ['', 'rotated有一个复核种子的测试链仅2396条，短缺4条，已保留失败证据；实际交付的冻结种子为完整2400条。不能把本轮写成“任何种子都能完成配额”。', '',
              '## 建议下一步', '',
              '保留宽属性结构的收益，把更多节点用于不同人物上下文之间的搭配共享，同时明确补足单件/整套两种服装编辑机会。不要先增加视频预算，也不要为改善平均数而禁止自然重复。需要同时比较链内属性数、人物搭配广度和既定编辑比例，当前尚无一个候选在这些指标上全面胜出。', '',
              '## 阅读与复现', '',
              '- `audit/final_comparison.json/.md`：独立核验、按链长/直链/分叉完整统计、真实搭配和方向覆盖。对照wide的99条缺额使总报告integrity_success为false；rotated自身的硬检查为true，两者不可混淆。',
              '- `audit/sampling_stability.json`：固定图、三个相同抽样种子对照。',
              '- `REVIEW_EXAMPLES.json/.md`：实际链及每一步源历史位置，不是编造示例。',
              '- `CURRENT_RULES.json`和`CONTRACT_SNAPSHOT.md`：本轮未修改已确认规则。',
              '- 构图：`build_sequence.py`、`build_wide.py`、`build_wide_balanced.py`、`build_rotated.py`。后三者先构图，再用`sample_wide.py --variant <目录>`统一抽样。',
              '- 独立对照：`audit/compare.py --candidate <目录> --output <报告JSON>`；默认基线是v3/linked_complete。',
              '- 稳定性：`check_sampling_stability.py --candidate <rotated目录>`。', '',
              '来源：本地第一版`MULTI_ROUND_CHAIN_SAMPLING_V1.md`与构图实现；[NIST序列覆盖研究](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=911348)启发“先列目标顺序再安排共享路径”。本轮启发式不是该论文算法的原样实现，也没有声称最优或证明预算下界。', '']
    (ROOT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    names={'identity':'人物','hair':'发型','hair_color':'发色','wardrobe':'服装','action':'动作','camera':'镜头','site':'场景'}
    examples=[];exlines=['# 真实编辑链示例','','节点ID只在相应划分内有效；完整源/目标状态见JSON。','']
    for split in ('train','test'):
        path=ROOT/'rotated'/split;nodes={r['id']:r['state'] for r in read(path/'nodes.json')}
        sessions=[json.loads(s) for s in (path/'sessions.jsonl').read_text(encoding='utf-8').splitlines()]
        for kind in ('linear','fork'):
            ss=max((s for s in sessions if s['kind']==kind and s['length']==5),key=lambda s:len(set(r['axis'] for r in s['steps'])))
            examples.append({'split':split,'session':ss,'states':{str(n):nodes[n] for n in set(ss['history'])}})
            exlines += [f"## {split}/{kind}：{ss['id']}",'',f"涉及{len(set(r['axis'] for r in ss['steps']))}个不同属性。",'']
            for j,e in enumerate(ss['steps'],1):exlines.append(f"{j}. 从历史v{e['source_position']}（节点{e['source']}）修改{names[e['axis']]}，得到v{j}（节点{e['target']}）。")
            exlines.append('')
    write(ROOT/'REVIEW_EXAMPLES.json',examples);(ROOT/'REVIEW_EXAMPLES.md').write_text('\n'.join(exlines),encoding='utf-8')
    status={'status':'same_budget_graph_experiment_complete_tradeoffs_pending','discussion_candidate':'rotated',
            'adopted_candidate':None,'previous_complete_candidate':'../dataset_local_support_20261021_v3/linked_complete',
            'structural_integrity_passed':candidate['integrity_success'],'target_node_and_session_quotas_filled':True,
            'all_registered_nodes_used':True,'all_confirmed_sampling_rules_satisfied':False,'overall_diversity_accepted':False,
            'formal_render_started':False,'shared_UE_modified':False,'reference_projection_recomputed':False,
            'remaining_issues':['reduced_identity_cross_attribute_pair_coverage','conditional_single_piece_share_below_50_percent','test_seed_sensitivity_2396_of_2400_in_one_repeat'],
            'next_action':'Discuss joint preservation of within-chain diversity, cross-context asset pair breadth and conditional wardrobe mode support; keep old candidate and budgets.'}
    write(ROOT/'trial_status.json',status)
    # Update only this branch's status and owner; other UE threads retain their fields.
    tech=FP/'technical/dataset/DATASET_DESIGN_EXPLORATION_20261021.md'
    text=tech.read_text(encoding='utf-8');marker='## 第四版：宽属性组合与序列覆盖对照'
    if marker in text:text=text.split(marker)[0].rstrip()+'\n'
    text+='\n'+marker+'\n\n本Technical拥有`%OUTPUT_ROOT%/dataset_sequence_graph_20261021_v4/`全部离线研究产物，experimental、unclassified_protected。脚本为`build_sequence.py`、`build_wide.py`、`build_wide_balanced.py`、`build_rotated.py`、`sample_wide.py`、`check_sampling_stability.py`、`audit/compare.py`、`assemble_report.py`；依赖v1正式目录与规范化、v3共同采样及独立v1/v2/v3检查。\n\n用户授权同预算尝试。最新入口`REPORT.md`，讨论候选`rotated/`，没有替换v3/linked_complete或采用新规则。独立证据`audit/final_comparison.json`；wide对照缺额是预期负例，rotated硬结构、数量和节点使用通过。宽属性提高链内不同属性数，但人物搭配广度下降、单件服装编辑比例不足；三个匹配抽样种子中一个测试种子短缺4条。`trial_status.json`明确整体未接受，参考需求未重算，未渲染。\n\n下一步讨论联合兼顾链内多样性、跨上下文搭配及服装两模式支持，保留旧候选和节点预算。仅做本轮独立语义/配额/实际覆盖、定向文档同步及证据哈希检查，不重建全仓目录、不启动UE。R17和唯一current主计划保持。\n'
    tech.write_text(text,encoding='utf-8')
    statuspath=FP/'project_management/status/PROJECT_STATUS.md';text=statuspath.read_text(encoding='utf-8')
    start=text.index('## 当前数据集分支：');end=text.index('\n## ',start+4)
    new='## 当前数据集分支：第四轮同预算构图试验完成，取舍待讨论（2026-10-21）\n\n用户认为链内不同属性过少，授权参考第一版及序列覆盖研究做对照。已完成sequence、wide、wide_balanced、rotated四条离线路线，最新入口`%OUTPUT_ROOT%/dataset_sequence_graph_20261021_v4/REPORT.md`，所有权归[探索Technical](../../technical/dataset/DATASET_DESIGN_EXPLORATION_20261021.md)。\n\nrotated训练/测试原节点预算、链数/类型/长度配额、原子编辑、服装合法性、历史继承、完整状态隔离及全部节点使用通过；链内属性数改善，但人物搭配广度下降、服装单件比例未达到已有50/50目标，一个复核种子测试短缺4条。整体多样性和采样未全部接受，v3候选保留，不能把新诊断写成正式队列。\n\n下一步讨论链内丰富度、人物搭配覆盖和服装两模式机会的联合分配。已确认规则不变，参考需求尚未重算，未改共享UE或启动渲染，R17仍in_progress、唯一current主计划保持。\n'
    statuspath.write_text(text[:start]+new+text[end:],encoding='utf-8')
    statepath=statuspath.with_name('PROJECT_STATE.json');state=read(statepath);old_other={k:v for k,v in state.items() if k!='dataset_design_branch_20261021'}
    branch=state['dataset_design_branch_20261021'];branch.update(status=status['status'],run_root='%OUTPUT_ROOT%/dataset_sequence_graph_20261021_v4/',previous_round_root='%OUTPUT_ROOT%/dataset_local_support_20261021_v3/',candidate='rotated_diagnostic_not_adopted',reading_entry='REPORT.md',
       evidence=['CURRENT_RULES.json','REPORT.md','trial_status.json','rotated/SUMMARY.json','audit/final_comparison.json','audit/sampling_stability.json','delivery_verification.json'],
       next_action=status['next_action'],all_confirmed_sampling_rules_satisfied=False,structural_integrity_passed=True,target_node_and_session_quotas_filled=True,all_registered_nodes_used=True,overall_diversity_accepted=False)
    branch['previous_complete_candidate']='%OUTPUT_ROOT%/dataset_local_support_20261021_v3/linked_complete/'
    write(statepath,state)
    assert {k:v for k,v in read(statepath).items() if k!='dataset_design_branch_20261021'}==old_other
    plan=FP/'project_management/plans/active/PLAN-2026-10-CAMERA-MOTION-SCENE-ALIGNMENT.md';text=plan.read_text(encoding='utf-8');marker='## R17 数据集分支：第四轮同预算构图对照'
    if marker in text:text=text.split(marker)[0].rstrip()+'\n'
    text+='\n'+marker+'\n\n同预算宽属性/序列覆盖对照已完成，见`%OUTPUT_ROOT%/dataset_sequence_graph_20261021_v4/REPORT.md`与探索Technical。新诊断链内属性更多，但实际人物搭配减少、服装单件比例不足；保留v3，未接受正式候选。下一步讨论联合分配与取舍，不新增禁止重复属性规则、不改节点预算。R17继续in_progress，唯一主计划保持；UE、参考媒体和渲染均未启动。\n'
    plan.write_text(text,encoding='utf-8')
    text=contract.read_text(encoding='utf-8');marker='## 第四轮构图试验状态（不改变上述规则）'
    if marker in text:text=text.split(marker)[0].rstrip()+'\n'
    text+='\n'+marker+'\n\n最新研究结果读取`%OUTPUT_ROOT%/dataset_sequence_graph_20261021_v4/REPORT.md`；前述v3段落为该版本历史完成记录。rotated为同预算讨论候选，结构与固定种子配额通过，但跨人物搭配广度及服装单件50/50目标尚未同时满足，未取代v3或冻结生产。未增设最少不同属性数、禁止回访等规则。\n'
    contract.write_text(text,encoding='utf-8');(ROOT/'CONTRACT_SNAPSHOT.md').write_bytes(contract.read_bytes())
    pins=[ROOT/'CURRENT_RULES.json',ROOT/'CONTRACT_SNAPSHOT.md',V3/'resample_local.py',V3/'blocks/build_blocks.py',ROOT.parent/'dataset_trial_build_20261021_v1/catalog.json',ROOT.parent/'dataset_trial_build_20261021_v1/build_trial.py',ROOT.parent/'dataset_trial_build_20261021_v1/normalize_catalog.py']
    pins+=list(ROOT.glob('*.py'))+[ROOT/'audit/compare.py']
    write(ROOT/'INPUTS_AND_METHODS.json',{'sha256':{str(p):sha(p) for p in pins},'old_candidate_preserved':str(V3/'linked_complete'),'runtime':'C:/ProgramData/anaconda3/python.exe'})
    delivery={'scope':'Selected diagnostic only; no full repository/UE/media acceptance. Failed control wide and one sampling repeat are retained.',
              'discussion_candidate_integrity_passed':candidate['integrity_success'],'overall_diversity_accepted':False,
              'all_confirmed_sampling_rules_satisfied':False,'other_project_state_fields_unchanged':True,
              'rules_snapshot_matches_previous_confirmed_rules':sha(ROOT/'CURRENT_RULES.json')==sha(V3/'CURRENT_RULES.json'),
              'evidence_sha256':{str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'REPORT.md',ROOT/'trial_status.json',ROOT/'audit/final_comparison.json',ROOT/'audit/sampling_stability.json',ROOT/'INPUTS_AND_METHODS.json']}}
    write(ROOT/'delivery_verification.json',delivery)
    print(json.dumps(status,ensure_ascii=False))

if __name__=='__main__':main()
