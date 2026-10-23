"""Assemble v3 trial findings and narrowly synchronize dataset-branch documentation."""
import ast
import hashlib
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[2]
DOC=REPO/'20_planning/data_design/character_creator/full_process'
V1=ROOT.parent/'dataset_trial_build_20261021_v1'

def read(p):return p.read_text(encoding='utf-8')
def load(p):return json.loads(read(p))
def write(p,s):p.write_text(s,encoding='utf-8')
def dump(p,x):write(p,json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def examples():
    labels={'identity':'人物身份','hair':'发型','hair_color':'发色','wardrobe':'服装','action':'动作','camera':'镜头','site':'场景点位'}
    chosen=[]
    for split in ['train','test']:
        nodes={r['id']:r['state'] for r in load(ROOT/'linked_complete'/split/'nodes.json')}
        sessions=[json.loads(s) for s in read(ROOT/'linked_complete'/split/'sessions.jsonl').splitlines()]
        cases=[('多属性直链',lambda s:s['kind']=='linear' and s['length']==4 and len({r['axis'] for r in s['steps']})>=3),
               ('使用中间历史版本的分叉',lambda s:s['kind']=='fork' and s['length']>=4 and any(r['source_position']>0 and r['source_position']<t-1 for t,r in enumerate(s['steps'],1)) and len(set(s['history']))==len(s['history'])),
               ('自然回访示例',lambda s:len(set(s['history']))<len(s['history']) and s['length']==3)]
        for title,predicate in cases:
            s=next(s for s in sessions if predicate(s))
            chosen.append({'split':split,'title':title,'session':s,'states':{str(i):nodes[i] for i in set(s['history'])}})
    dump(ROOT/'REVIEW_EXAMPLES.json',chosen)
    lines=['# 六条实际编辑链示例','','这些是本轮真实节点和边，不是虚构案例；尚无视频。V0是初始视频，每轮新增一个历史位置，回访时可指向已经存在的节点。完整配置见同目录REVIEW_EXAMPLES.json。','']
    for row in chosen:
        s=row['session'];lines += [f"## {row['split']} / {row['title']} / {s['id']}",'']
        for t,step in enumerate(s['steps'],1):
            a=step['axis'];old=row['states'][str(step['source'])];new=row['states'][str(step['target'])]
            if a=='wardrobe':
                change=f"{old[a]['family_id']}/{old[a]['group_id']} → {new[a]['family_id']}/{new[a]['group_id']}（{step['mode']}，单件明细见JSON）"
            else:change=f'{old[a]} → {new[a]}'
            lines.append(f"- 第{t}次：使用V{step['source_position']}，修改{labels[a]}：{change}，得到V{t}。")
        lines.append('')
    write(ROOT/'REVIEW_EXAMPLES.md','\n'.join(lines))


def sync_docs():
    contract=DOC/'technical/dataset/DATASET_TRIAL_CONTRACT_20261021.md'
    text=read(contract).replace('最新结果读取 `%OUTPUT_ROOT%/dataset_joint_build_20261021_v2/REPORT.md` / `trial_status.json`。','最新结果读取 `%OUTPUT_ROOT%/dataset_local_support_20261021_v3/REPORT.md` / `trial_status.json`；v2保留历史实验。')
    text=text.replace('详细规则和JSON位于 `%OUTPUT_ROOT%/dataset_trial_build_20261021_v1/CONFIRMED_RULES.md` / `rules.json`。','早期规则快照位于 `%OUTPUT_ROOT%/dataset_trial_build_20261021_v1/CONFIRMED_RULES.md` / `rules.json`；当前含局部目标修订的机器规则为 `%OUTPUT_ROOT%/dataset_local_support_20261021_v3/CURRENT_RULES.json`。')
    text=text.replace('具体构造与结果尚待实施，例子中的两个候选不是数量上限。','第三版局部候选已完成离线构造，数量与结构通过，整体多样性仍待审阅；例子中的两个候选不是数量上限。')
    section=re.search(r'^## (?:实现未满足项|当前实现与未满足项)',text,re.M)
    assert section
    text=text[:section.start()]+'''## 当前实现与未满足项

v3已按局部候选规则生成`linked_complete`，训练2,500节点/12,000链、测试500节点/2,400链，全部节点被使用，独立结构与精确链长/类型配额检查通过。使用有限多值交叉块、身份连接、全局频次反馈与少量覆盖修补；反馈是实现策略，不意味着每个源节点仍保持全目录条件概率。

两split均覆盖40身份、37服装来源组、45合法搭配组、28独立发型、7色、25动作、21镜头和21点位；类别覆盖不等于全部服装资产、全部编辑方向或所有搭配已覆盖。测试链含回访约67%，分叉中未修改属性体现历史区别的比例约47%，多类编辑方向少于v1；没有宣称整体多样性验收通过。原预算与合法语义保持，下一步审阅这些取舍，暂不正式渲染。媒体规格和文本模板仍未冻结。
'''
    write(contract,text)
    tech=DOC/'technical/dataset/DATASET_DESIGN_EXPLORATION_20261021.md'
    text=read(tech)
    text=text.replace('下一轮实现尚未开始，不因允许局部支持而自动接受旧图。新生成器及验证必须显式记录这一修订。','第三版已按修订实现，最新入口见下段；不因允许局部支持而自动接受旧图。')
    a=text.index('**当前入口（');b=text.index('\n\n',a)
    text=text[:a]+'''**当前入口（2026-10-21 第三版局部候选）**：`%OUTPUT_ROOT%/dataset_local_support_20261021_v3/REPORT.md`，候选`linked_complete/`。已完成原预算内足量节点/链，全部节点实际使用，结构与配额通过；多样性有改善也有退步，尤其测试回访偏多，待用户审阅，尚非正式渲染清单。v1/v2保持历史快照。'''+text[b:]
    marker='## 第三版：局部候选与整体多样性'
    if marker in text:text=text[:text.index(marker)].rstrip()+'\n'
    text+='''
## 第三版：局部候选与整体多样性

本Technical拥有 `%OUTPUT_ROOT%/dataset_local_support_20261021_v3/` 全部试构建输出，生命周期experimental，保留分类unclassified_protected。脚本包括`blocks/build_blocks.py`、`blocks/build_diverse.py`、`blocks/verify_blocks.py`、`resample_local.py`、`refine_identity_links.py`、`complete_coverage.py`、`project_references.py`、`audit/verify_local.py`、`audit/compare_local.py`、`assemble_delivery.py`。仍依赖v1正式目录解析/结构检查和v2独立服装枚举；没有生产入口变更。

当前候选是`linked_complete/`；`blocks/`和其他balanced/linked目录仅是内部中间路线，不得混用。`CURRENT_RULES.json`和`CONTRACT_SNAPSHOT.md`显式保存局部目标修订；`REPORT.md`为简明入口，`REVIEW_EXAMPLES.md/.json`有六条真实链，`audit/verification_linked_complete.json`为最终独立证据。`linked_complete/reference_manifest.json`是该候选实际编辑所需的未渲染参考，不复用v1数量。`trial_status.json`明确整体多样性待审阅，`delivery_verification.json`只核验当前交付及文档一致性。

构造保留单轴合法编辑，先建立多值交叉块，再用预算内替换补充身份连接和缺失合法组/点位，最终按合法边重建父节点引用。会话起点平衡身份，属性/服装模式采用局部候选及累计频次反馈；未禁止自然回访或单属性链，未强制过滤分叉等价结果。该反馈不构成精确条件随机性声明。

已完成原预算、类型/长度配额和完整状态隔离；测试重复较多，部分编辑方向与搭配弱于v1，整体多样性尚未接受。下一步由用户审阅测试重复和覆盖取舍，再确定是否采用该候选及媒体规格。仅做本轮证据、语法、链接与状态字段检查，不扩为全仓审计或UE验证；R17/唯一current计划不变。
'''
    write(tech,text)
    status=DOC/'project_management/status/PROJECT_STATUS.md'
    text=read(status);a=text.index('## 当前数据集分支：');b=text.index('## 当前服装调整：',a)
    text=text[:a]+'''## 当前数据集分支：第三版节点与链已生成，整体多样性待审阅（2026-10-21）

用户接受单节点只安排部分合法编辑目标，以整体多样性为前提。当前`%OUTPUT_ROOT%/dataset_local_support_20261021_v3/linked_complete/`已生成训练2,500节点/12,000链、测试500节点/2,400链，全部节点实际使用。独立检查确认单属性/服装/历史继承、链长与分叉类型配额、结构去重、跨split完整节点不重合。规则及原预算保持，详见[试构建契约](../../technical/dataset/DATASET_TRIAL_CONTRACT_20261021.md)。

两split均覆盖40身份、37服装来源组、45合法搭配组、28独立发型、7色、25动作、21镜头/点位。训练含回访链从v1约70%降到48%，测试仍约67%；一些编辑方向与搭配少于v1，因此未接受整体多样性。类别覆盖不能写成全服装资产/全转换覆盖。简明阅读入口`REPORT.md`，有六条实际链和重新计算的参考需求，全部媒体未生成。

下一步审阅测试重复、分叉区别及覆盖取舍，再定当前候选与媒体参数；不继续把“是否允许局部目标”列为待确认。未改UE/资产/点位/曝光或开始渲染，R17仍in_progress，唯一主计划与原会话资产维护保持。

'''+text[b:];write(status,text)
    plan=DOC/'project_management/plans/active/PLAN-2026-10-CAMERA-MOTION-SCENE-ALIGNMENT.md'
    text=read(plan);marker='## R17 数据集分支：第三版局部候选'
    if marker in text:text=text[:text.index(marker)].rstrip()+'\n'
    text+='''
## R17 数据集分支：第三版局部候选（2026-10-21）

按用户接受的局部目标规则完成离线构造，原节点预算和链数/类型/长度配额通过，全部节点被实际使用，历史继承与训练测试隔离通过。整体多样性尚待审阅，测试重复较多、部分编辑方向少于v1，未将数量达标写成正式接受。最新入口 `%OUTPUT_ROOT%/dataset_local_support_20261021_v3/REPORT.md`，所有权归探索Technical，当前候选`linked_complete`。下一步审阅候选取舍并讨论媒体参数；未改共享UE或启动渲染，R17继续in_progress、父计划唯一current。
''';write(plan,text)
    machine=DOC/'project_management/status/PROJECT_STATE.json'
    raw=read(machine);before=json.loads(raw);key='dataset_design_branch_20261021';start=raw.index('{',raw.index('"'+key+'"'))
    branch,size=json.JSONDecoder().raw_decode(raw[start:])
    branch.update(status='local_support_candidate_generated_diversity_review_pending',run_root='%OUTPUT_ROOT%/dataset_local_support_20261021_v3/',previous_round_root='%OUTPUT_ROOT%/dataset_joint_build_20261021_v2/',reading_entry='REPORT.md',candidate='linked_complete',structural_integrity_passed=True,target_node_and_session_quotas_filled=True,all_registered_nodes_used=True,overall_diversity_accepted=False,all_confirmed_sampling_rules_satisfied=False,next_action='Review test-set repetition, fork distinguishability and coverage tradeoffs before accepting the candidate and freezing media parameters.',evidence=['CURRENT_RULES.json','REPORT.md','trial_status.json','linked_complete/SUMMARY.json','audit/verification_linked_complete.json','audit/COMPARISON_FINAL.md','linked_complete/reference_summary.json','delivery_verification.json'])
    branch['local_target_support_decision']['new_candidate_implemented']=True
    aftertext=raw[:start]+json.dumps(branch,ensure_ascii=False,indent=2).replace('\n','\n  ')+raw[start+size:]
    after=json.loads(aftertext)
    assert {k:v for k,v in before.items() if k!=key}=={k:v for k,v in after.items() if k!=key}
    write(machine,aftertext)
    return contract


def main():
    audit=load(ROOT/'audit/verification_linked_complete.json')
    assert audit['integrity_success'] and audit['canonical_cross_split_overlap_count']==0
    for path,digest in audit['inputs_sha256'].items():assert sha(Path(path))==digest,path
    summary=load(ROOT/'linked_complete/SUMMARY.json')
    assert all(r['unused_nodes']==0 for r in summary.values())
    contract=sync_docs()
    rules=load(V1/'rules.json')
    rules.update(rule_set_id='dataset_local_support_20261021_v3',schema_version=3,status='user_approved_local_support_candidate_diversity_pending')
    rules['scope']['document']='CONTRACT_SNAPSHOT.md'
    rules['edit_sampling']['target_sampling_default']='subset_of_formally_legal_alternatives_planned_per_source'
    rules['local_target_support']={'user_approved':True,'full_catalog_conditional_uniformity_required':False,'dataset_wide_diversity_required':True,'fixed_target_count_per_source':None,'existing_axis_weights_and_wardrobe_mode_targets_retained':True,'base_rules_path':str(V1/'rules.json'),'base_rules_sha256':sha(V1/'rules.json'),'contract_sha256':sha(contract),'candidate_sampling_implementation':'local support with global cumulative frequency feedback, not exact conditional uniformity'}
    dump(ROOT/'CURRENT_RULES.json',rules);write(ROOT/'CONTRACT_SNAPSHOT.md',read(contract))
    examples()
    from project_references import main as project
    project()
    refs=load(ROOT/'linked_complete/reference_summary.json')
    status={'status':'candidate_generated_diversity_review_pending','candidate':'linked_complete','node_session_quotas_passed':True,'structural_integrity_passed':True,'all_registered_nodes_used':True,'overall_diversity_accepted':False,'formal_render_started':False,'shared_UE_modified':False,'media_profile_frozen':False,'rule_revision':'per-source legal target subsets allowed; global diversity required','reference_images_planned':refs['unique_images'],'reference_motion_clips_planned':refs['unique_motion_clips'],'next_action':'审阅测试重复与搭配覆盖取舍，再确定候选和视频规格。'}
    dump(ROOT/'trial_status.json',status)
    rows=[]
    for split in ['train','test']:
        r=summary[split];q=audit['splits'][split]['quality'];n=r['sessions']
        rows.append({'split':split,'nodes':r['nodes'],'chains':n,'chain_revisit_rate':r['sessions_with_revisited_node']/n,'step_revisit_rate':q['natural_revisit_metrics']['return_to_any_history_node_steps']/r['edit_steps'],'single_axis_chain_rate':r['single_axis_sessions']/n,'fork_inherited_difference_rate':q['fork_effect_metrics']['non_edited_state_differs_from_latest']/q['fork_effect_metrics']['fork_chains']})
    dump(ROOT/'READABLE_METRICS.json',rows)
    train,test=rows
    report=f'''# 第三版试构建：已经做到什么，还差什么

这次已经在原来的视频预算内生成足量编辑链，所有节点都实际用到了。**它是一份可继续讨论的完整候选，但测试集重复仍然偏多，暂不直接作为最终渲染清单。**

| 项目 | 训练集 | 测试集 |
| --- | ---: | ---: |
| 不同的视频配置 | 2,500 | 500 |
| 不同结构的编辑链 | 12,000 | 2,400 |
| 没有被链使用的视频配置 | 0 | 0 |
| 人物身份 | 40 | 40 |
| 服装来源组 / 合法搭配组 | 37 / 45 | 37 / 45 |
| 场景点位 | 21 | 21 |

两部分也都覆盖28款独立发型、7种发色、25个动作和21种镜头。这是类别覆盖，不代表每件服装变体、每种搭配或每种编辑方向都已覆盖。当前只有配置和关系，没有生成视频。

## 这次怎么做

同一组视频允许“先换发型再换衣服”和“先换衣服再换发型”等路径共用节点。不同人物分配不同的局部候选，身份替换与其他编辑之间补上连接，避免某个人物只剩身份替换可做。随后在原预算内补齐遗漏的服装搭配组和点位。

链的起点平衡人物；编辑类别和服装模式根据累计使用次数作平衡。这个实现允许局部候选有限，没有宣称每个视频仍能等概率编辑到完整资产库。没有禁止自然回访、单属性整链或末轮分叉，也没有过滤那些用最新版本也可能得到相同结果的分叉。

## 比上一版改善了什么

训练链中，发生过回到历史视频的比例从约70%降到{train['chain_revisit_rate']:.1%}。所有3,000个节点都有实际用途；单件/整套服装在两者正式均可选的情况下接近一半一半。身份、衣物和场景等仍按正式合法规则改变。

独立检查确认：每条边只改变一个语义属性；分叉完整继承被选择的历史版本；训练测试完整视频状态没有重合；链长、直链/分叉比例以及唯一结构数量符合原计划。这些是配置层检查，尚无视觉或训练效果验证。

## 还需要看清的取舍

测试链中仍有{test['chain_revisit_rate']:.1%}曾回到历史视频，和旧代表接近。这个数字不表示重复链；链的完整路径互不相同，但会用回链内之前的视频。若按每次编辑计，训练{train['step_revisit_rate']:.1%}、测试{test['step_revisit_rate']:.1%}回到已有历史节点。测试中约14%的链从头到尾只在同一对视频间修改，这是当前最值得继续讨论的问题。

分叉选择历史版本后，未被本次编辑修改的内容确实与最新版本不同的比例，训练为{train['fork_inherited_difference_rate']:.1%}、测试为{test['fork_inherited_difference_rate']:.1%}。其余并非结构错误，但对检验历史选择能力的信息较少。自然等价分叉仍按用户决定允许。

此外，部分发型、动作、镜头和场景的具体转换方向比v1少；不是所有多样性指标都改善。当前链主要组合两到三个编辑属性，测试单属性整链约{test['single_axis_chain_rate']:.1%}。因此本次可以确认“预算内构造和配置正确性跑通”，不能直接宣布“整体多样性足够”。

## 后续准备

已按这份实际候选重新列出参考需求：**{refs['unique_images']:,}张图片、{refs['unique_motion_clips']:,}段动作参考视频**，另计于3,000个主视频。所有媒体路径仍为空。参考需求会随最终节点/边变化，动作载体、分辨率、帧率、时长、画幅还没有冻结。

下一步建议先讨论测试集的重复程度是否需要进一步降低，再决定是否采用这份候选。没有扩大视频预算，也没有启动UE或渲染。

- [六条实际链示例](./REVIEW_EXAMPLES.md)：直链、中间历史分叉和自然回访各有实例。
- [候选节点、边与链汇总](./linked_complete/SUMMARY.json)。
- [当前确认规则](./CONTRACT_SNAPSHOT.md)、[机器规则](./CURRENT_RULES.json)。
- [独立检查与旧版比较](./audit/COMPARISON_FINAL.md)、[最终检查详情](./audit/verification_linked_complete.md)。
- [参考素材需求](./linked_complete/REFERENCES.md)。

当前只使用`linked_complete/`。其他目录保存构造过程中的对照，不能混成一个候选。重建顺序：`blocks/build_diverse.py --camera-balanced`、`refine_identity_links.py`、`complete_coverage.py`、独立核验，再运行本交付脚本；这些脚本均为实验实现，v1/v2依赖必须一并保留。
'''
    write(ROOT/'REPORT.md',report)
    links=0
    for name in ['REPORT.md','REVIEW_EXAMPLES.md']:
        for target in re.findall(r'\]\((\./[^)]+)\)',read(ROOT/name)):
            assert (ROOT/target).exists(),target
            links+=1
    scripts=list(ROOT.rglob('*.py'))
    for p in scripts:ast.parse(read(p),filename=str(p))
    dump(ROOT/'delivery_verification.json',{'success':True,'scope':'final candidate independent evidence hashes, report links, Python syntax, reference planner self-checks, scoped documentation/state update','structural_and_quota_checks_passed':True,'overall_diversity_accepted':False,'media_checked':False,'unrelated_project_state_fields_preserved':True,'full_repository_audit':False,'checked_links':links,'checked_python_scripts':len(scripts)})
    files=[p for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='DELIVERY_MANIFEST.json']
    dump(ROOT/'DELIVERY_MANIFEST.json',{'candidate':'linked_complete','files':[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(files)]})
    print(json.dumps({'success':True,'files':len(files),'candidate':'linked_complete','diversity_accepted':False,'references':{'images':refs['unique_images'],'motion_clips':refs['unique_motion_clips']}}))


if __name__=='__main__':main()
