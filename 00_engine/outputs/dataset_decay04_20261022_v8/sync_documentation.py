"""Experimental scoped documentation sync; owner: TECH-DATASET-EXPLORE-20261021."""
import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
DOCS = REPO / '20_planning/data_design/character_creator/full_process'
STATE = DOCS / 'project_management/status/PROJECT_STATE.json'

def read(p):
    return json.loads(p.read_text(encoding='utf-8'))

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def write(p, text):
    p.write_text(text, encoding='utf-8', newline='\n')

def dump(p, value):
    write(p, json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def edit(relative, operation):
    p = DOCS / relative
    old = p.read_text(encoding='utf-8')
    new = operation(old)
    assert new != old, relative
    write(p, new)
    changed.append(p)

assert read(ROOT/'structural_audit.json')['passed_hard_checks']
assert read(ROOT/'aspect_audit.json')['passed']
assert read(ROOT/'reference_binding_check.json')['passed']
assert read(ROOT/'CURRENT_CANDIDATE.json')['history_decay'] == .4
assert (ROOT/'REPORT.md').exists()
old_state = read(STATE)
old_branch = old_state['dataset_design_branch_20261021']
assert old_branch['history_axis_decay'] == .2
outside_before = {k:v for k,v in old_state.items() if k != 'dataset_design_branch_20261021'}
v7 = ROOT.parent/'dataset_dual_aspect_20261022_v7'
protected = [v7/'RULES.json', v7/'CURRENT_CANDIDATE.json']
protected += [v7/'selected_candidate'/s/f for s in ('train','test') for f in ('nodes.json','edges.json','sessions.jsonl')]
protected_before = {str(p):digest(p) for p in protected}
changed = []

edit('technical/dataset/DATASET_DESIGN_EXPLORATION_20261021.md', lambda t: t.replace(
    '2026-10-22（第七轮保原链双画幅离线候选定向同步）', '2026-10-22（第八轮历史衰减0.4实际重采样与动作镜头覆盖定向同步）', 1).replace(
    '**当前入口（2026-10-22 第七版双画幅离线候选）**',
    '**当前入口（第八版历史衰减0.4）**：`%OUTPUT_ROOT%/dataset_decay04_20261022_v8/REPORT.md`，由同根`CURRENT_CANDIDATE.json`绑定`selected_candidate`。使用同一第六版图，实际重采样新链后重新分配画幅并重算参考；不是只改参数记录。结构、画幅与参考绑定离线检查通过，采用及整体多样性仍待审。方法和限制见文末第八版。\n\n**第七版历史入口（保留0.2原链）**', 1) + '''

## 第八版：历史轴衰减0.4与动作镜头覆盖核查（2026-10-22）

本Technical拥有`%OUTPUT_ROOT%/dataset_decay04_20261022_v8/`全部离线输出，experimental、unclassified_protected。用户将全历史轴衰减从0.2改为0.4，即某轴已在完整历史出现n次时乘0.4^n；包括弃支，不改为只看当前分支。旧v6/v7的0.2记录与目录保持冻结。新规则为`RULES.json`，当前候选由`CURRENT_CANDIDATE.json`绑定，完整说明见`REPORT.md`。

实际实现复用v6 `selected_seed1`训练N/测试T节点和边，`same_graph_check.json`逐值确认图相同；保存的v68 sampler与种子train2026102261/test2026102262实际生成新链。其他既有采样参数、覆盖预热、反馈和尾期fallback保持并在`INPUTS_AND_METHODS.json`／`structural_candidate/SAMPLER_CODE.json`披露，不能宣称纯概率采样。实验脚本为`finish_candidate.py`、`compare_decay.py`、`analyze_action_camera.py`与`sync_documentation.py`；sampler副本与来源由机器方法清单拥有。重建会覆盖本实验输出，复算应先复制到新运行根；不覆盖历史输入。

结构候选保留3,752／800个内容状态，生成12,000／2,400条新链与43,800／8,760次编辑；双画幅物化后为5,256／1,183个实际used主视频请求，共6,439。每条新链及历史／分支固定同一画幅，分配完整保留的是本轮新链，不是v7原链。横／竖链训练6,013／5,987、测试1,200／1,200；整体六非身份轴偏差训练3.63%、测试4.60%，分画幅训练3.02%／4.23%、测试4.59%／5.37%。初始21镜头整数配额、训练全单项真实编辑目标、239核心衣物真正换入、原子合法性、完整历史、配额及去画幅跨split隔离检查通过。具体边最高训练3次、测试4次，测试4次边3条占已用不同具体边0.06494%。

同图单种子对比较显示：训练／测试重复轴步骤占比由11.58%／18.28%升至15.97%／22.19%；训练L5不同轴均值linear3.954、fork3.945，测试3.620／3.5429。该变化符合较弱重复抑制的方向，不写成链内轴多样性全面改善。仅核验一个新采样种子对和一次画幅分配，未执行0.4三seed稳定性或全局最优搜索，旧0.2三seed证据不继承为新候选稳定性。

动作覆盖单独核查：`baseline_action_camera.json/.md`统计v7；`selected_action_camera.json/.md`统计本轮。主视频按唯一渲染请求计数，镜头种类合并男女与画幅；参考只统计实际action编辑需求，不等于全部主视频组合。v7训练25动作中13个各只有1个主视频／1种镜头，前10动作占训练主视频92.63%；全体合并仅86个动作×镜头组合、9动作只有1镜头。v8保持同一内容图，动作×镜头支持仍为86，动作参考支持78；调整衰减没有解决该稀疏性。单项25动作／21镜头全覆盖和七轴总次数平衡不能作为动作镜头充分覆盖或各动作频次均衡的证据。覆盖不足进入下一步讨论，本轮未获授权重构图或新增覆盖门槛。

条件single训练48.70%、测试51.59%，正式合法部位条件分布TV为0.00259／0.00097；训练仍有约5.89%正式部位机会未在保存图内安排，且分画幅小量残差未宣称全面均衡。参考按最终候选重算：1,002图片与153动作视频，共1,155项需求，52,560步骤链接检查通过；最终媒体规格、动作参考载体、场景精确初帧仍未冻结。独立证据为`structural_audit.json`、`aspect_audit.json`、`reference_binding_check.json`和本轮`documentation_result_sync.json`。限定核验不包括全树审计、目录重建、UE/像素或训练收益；未启动媒体、渲染或训练，不晋升生产Gate，R17与唯一current父计划保持。
''')

edit('technical/dataset/DATASET_TRIAL_CONTRACT_20261021.md', lambda t: t.replace(
    '2026-10-22（第七轮整链双画幅与预算放宽修订）', '2026-10-22（第八轮历史轴衰减0.4修订）', 1).replace(
    '当前第七轮机器规则为', '第七轮历史机器规则为', 1).replace(
    '冲突条款以文末第七轮修订为准。', '冲突条款以文末最新修订为准。当前第八轮规则为`%OUTPUT_ROOT%/dataset_decay04_20261022_v8/RULES.json`，采用0.4衰减实际重采样，选择与检查由同根`CURRENT_CANDIDATE.json`、`structural_audit.json`、`aspect_audit.json`及`reference_binding_check.json`拥有。', 1) + '''

## 2026-10-22 第八轮：全历史轴衰减改为0.4

用户明确将0.2改为0.4。本节替代当前采样政策的冲突值：全历史轴权重乘0.4^n，n包括此前所有编辑及弃支；允许自然重复、回访和同轴连续编辑，不增加最少不同轴数。旧v6/v7仍如实记录0.2，不回写历史。整链固定画幅、局部合法候选、原子编辑、完整历史继承、服装条件规则、配额与跨split内容隔离继续适用。

第八轮已在相同内容图上实际生成新链，再为新链分配双画幅并重算参考需求，选择入口为`dataset_decay04_20261022_v8/CURRENT_CANDIDATE.json`。本轮保全的是新0.4链；没有宣称保留v7每条旧链。仅一个采样种子对离线验证，采用及整体多样性待审，0.4三seed稳定性未评估。修改衰减不扩展原图的动作镜头支持；单项值全覆盖不能替代每动作的镜头与频次覆盖，具体不足见探索Technical与本轮动作统计。本轮只记录不足供后续讨论，未新增覆盖下限或启动重构。
''')

edit('project_management/status/PROJECT_STATUS.md', lambda t: t.replace(
    '2026-10-22（仅数据集分支第七轮双画幅离线候选结果同步）', '2026-10-22（仅数据集分支0.4重采样与覆盖核查同步）', 1).replace(
    '## 当前数据集分支：保留原链的第七轮双画幅离线候选已验证，待采用（2026-10-22）', '''## 当前数据集分支：0.4衰减已实际重采样，动作镜头覆盖仍待讨论（2026-10-22）

用户将历史轴衰减改为0.4，当前离线候选为`%OUTPUT_ROOT%/dataset_decay04_20261022_v8/selected_candidate`，由同根`CURRENT_CANDIDATE.json`绑定，入口`REPORT.md`。同一第六轮图上实际生成新链，再分配整链画幅与重算参考；旧v7及0.2记录保留。实现与规则由[探索Technical](../../technical/dataset/DATASET_DESIGN_EXPLORATION_20261021.md)和[试构建契约](../../technical/dataset/DATASET_TRIAL_CONTRACT_20261021.md)拥有。

实际主视频训练5,256、测试1,183，总6,439，比v7增加289；内容状态仍为3,752／800。新链12,000／2,400、编辑43,800／8,760；横／竖链训练6,013／5,987，测试1,200／1,200。结构、画幅保全、去画幅跨split隔离、每节点渲染请求和52,560步参考绑定检查通过；参考需求为1,002图片与153动作视频，尚未渲染。分画幅六轴偏差训练3.02%／4.23%、测试4.59%／5.37%，训练全单项真实目标与239核心件真正换入保持。

这次核查发现覆盖仍稀疏：v7训练25动作中13个各只有1个主视频和1种镜头，前10动作占92.63%；全部主视频仅86个动作×镜头组合、9动作只有1镜头。`baseline_action_camera.md/.json`是v7统计，`selected_action_camera.md/.json`是v8统计；v8同图仍为86个主视频组合、78个动作参考组合，0.4未修复原图支持不足。训练全25动作与21镜头各自出现，不代表每动作镜头丰富或频次均衡。后续需讨论是否改善覆盖，本轮未重构图或新增覆盖要求。

同图单种子对中，重复轴步骤占比训练11.58%→15.97%、测试18.28%→22.19%；这是衰减减弱后的真实变化。结构通过不等于整体多样性已接受；仅一个0.4采样种子对，旧0.2三seed证据不能转为本轮稳定性。条件single训练48.70%、测试51.59%，低量部位及保存图机会不足继续披露。下一步讨论动作镜头覆盖与候选采用，再确认媒体规格、参考载体／精确初帧及小样；R17、唯一current父计划、其他分支及local_work保持，未启动UE、媒体、渲染或训练。

## 历史数据集分支：保留原链的第七轮双画幅离线候选（0.2，2026-10-22）''', 1))

edit('project_management/status/workflows/WF-70.md', lambda t: t.replace(
    '2026-10-22（仅R17双画幅离线候选状态同步；第一批Gate保持）', '2026-10-22（仅R17的0.4重采样与覆盖限制同步；第一批Gate保持）', 1).replace(
    '## 独立R17设计实验：第七轮双画幅离线候选', '## 历史R17设计实验：第七轮双画幅离线候选', 1) + '''

## 当前R17设计实验：第八轮0.4实际重采样（2026-10-22）

当前候选为`%OUTPUT_ROOT%/dataset_decay04_20261022_v8/selected_candidate`，选择由`CURRENT_CANDIDATE.json`绑定。用户确认全历史轴衰减0.4；相同内容图上实际重采样新链，重新分配整链画幅与参考，结构／画幅／参考绑定限定离线检查通过。旧v7保留0.2历史范围，本轮仅一个采样种子对，未验证三seed稳定性。

动作镜头覆盖仍有明显不足，单项值全覆盖不代表每动作镜头或频次充分；同图调整衰减没有扩展支持范围。统计与准确成本由[探索Technical](../../../technical/dataset/DATASET_DESIGN_EXPLORATION_20261021.md)、本轮REPORT及baseline／selected动作统计拥有。下一步讨论覆盖与采用，整体多样性未接受，不晋升第一批GATE-70、不关闭R17，媒体规格与参考实际接入待定。
''')

edit('project_management/plans/active/PLAN-2026-10-CAMERA-MOTION-SCENE-ALIGNMENT.md', lambda t: t + '''

## R17 数据集分支：历史轴衰减改为0.4与覆盖核查（2026-10-22）

用户将0.2调整为0.4，已在同一第六轮内容图上实际采样新链，并另建`%OUTPUT_ROOT%/dataset_decay04_20261022_v8/`，完成新链双画幅分配、参考需求重算及限定离线检查。当前由该根`CURRENT_CANDIDATE.json`绑定；旧v7/0.2及三seed历史保留，不能作为本轮0.4稳定性证据。

本轮同时发现原动作镜头支持明显稀疏，改变衰减未解决该问题；具体事实归[探索Technical](../../../technical/dataset/DATASET_DESIGN_EXPLORATION_20261021.md)及运行根baseline／selected统计。下一步讨论是否改善覆盖与是否采用，再确定媒体和小样，不静默重构图或添加新门槛。R17仍in_progress，当前父计划唯一current，其他需求、local_work及既有生产Gate保持。
''')

edit('registry/README.md', lambda t: t.replace(
    '| 第七轮整链双画幅离线候选 |',
    '| 第八轮0.4历史衰减离线候选 | `%OUTPUT_ROOT%/dataset_decay04_20261022_v8/CURRENT_CANDIDATE.json`、`RULES.json`、`same_graph_check.json`、`structural_audit.json`、`aspect_audit.json`、`selected_candidate/{train,test}/render_requests.json`及`reference_binding_check.json` | experimental；同图实际重采样、整链双画幅与未渲染参考需求。仅单种子对，动作镜头支持不足仍在；采用和生产范围查Status | [数据集探索第八版](../technical/dataset/DATASET_DESIGN_EXPLORATION_20261021.md) | `WF-60`／`WF-70`（离线研究），`WF-80`仅后续接入 |\n| 第七轮历史整链双画幅候选（0.2） |', 1))

audit=read(ROOT/'structural_audit.json')
selection=read(ROOT/'CURRENT_CANDIDATE.json')
sources=read(ROOT/'selected_assignment/SOURCES.json')
comparison=read(ROOT/'decay_comparison.json')
coverage=read(ROOT/'selected_action_camera.json')
stats={}
for split in ('train','test'):
    a=audit[split]
    stats[split]={
        **selection['counts'][split],
        'coverage':{k:v['distinct'] for k,v in a['coverage_used_nodes'].items() if isinstance(v,dict) and 'distinct' in v},
        'edited_target_coverage':{k:v['distinct'] for k,v in a['edited_axis_target_value_coverage'].items()},
        'six_axis_max_relative_deviation':max(a['six_nonidentity_relative_deviation'].values()),
        'conditional_single_fraction':a['wardrobe']['formal_single_eligible_single_fraction'],
        'single_slot_total_variation':a['single_slot_diagnostic']['conditional_actual_vs_expected_total_variation'],
        'graph_missing_formal_slot_opportunity_fraction':a['single_slot_diagnostic']['graph_missing_formal_slot_opportunity_fraction'],
        'maximum_semantic_directed_edge_uses':a['edge_reuse']['max'],
        'semantic_per_axis_mean_reuse':{k:v['mean'] for k,v in a['axis_edge_reuse'].items()},
        'per_aspect_six_axis_max_relative_deviation':sources[split]['max_relative_axis_deviation'],
        'sequence_comparison':{k:comparison['splits'][split][k] for k in ('delta_mean_distinct_axes','delta_repeated_axis_step_fraction')},
    }
branch={
    'thread_id':old_branch['thread_id'],
    'status':'decay04_offline_candidate_verified_coverage_limitations_pending_user_adoption_not_rendered',
    'run_root':'%OUTPUT_ROOT%/dataset_decay04_20261022_v8/',
    'previous_round_root':old_branch['run_root'],
    'technical_document':old_branch['technical_document'],
    'confirmed_contract_document':old_branch['confirmed_contract_document'],
    'reading_entry':'REPORT.md','candidate':'selected_candidate','current_candidate':'CURRENT_CANDIDATE.json',
    'parent_requirement':'R17','history_axis_decay':.4,
    'scope':['same_v6_content_graph_actual_decay04_resampling','fixed_aspect_per_new_complete_history_and_forks','recomputed_unrendered_reference_demand','action_camera_coverage_diagnosis_only_no_graph_redesign'],
    'production_frozen':False,'formal_render_started':False,'shared_UE_modified':False,'training_started':False,
    'next_action':'讨论现有动作镜头覆盖不足与0.4候选采用，再确认媒体规格、动作参考载体、场景精确初帧与小样；本轮未重构覆盖或启动渲染。',
    'evidence':['RULES.json','REPORT.md','CURRENT_CANDIDATE.json','INPUTS_AND_METHODS.json','same_graph_check.json','structural_audit.json','aspect_audit.json','selected_assignment/SOURCES.json','reference_binding_check.json','selected_candidate/reference_manifest.json','selected_candidate/reference_summary.json','decay_comparison.json','baseline_action_camera.json','selected_action_camera.json','documentation_result_sync.json'],
    'source_graph':'%OUTPUT_ROOT%/dataset_compact_graph_20261022_v6/selected_seed1/',
    'new_chain_sampling_for_selected_candidate':True,
    'all_new_structural_sessions_preserved_exactly_once':True,
    'all_v7_original_sessions_preserved':False,
    'structural_integrity_passed':True,'all_experiment_hard_checks_passed':True,
    'all_confirmed_sampling_rules_satisfied':False,'all_registered_nodes_used':True,
    'target_node_and_session_quotas_filled':True,'overall_diversity_accepted':False,'offline_candidate_selected':True,
    'primary_candidate_statistics':stats,
    'actual_render_nodes_total':sum(v['render_nodes'] for v in selection['counts'].values()),
    'action_camera_coverage':{**coverage['summary'],'scope':coverage['scope'],'same_graph_support_gap_resolved':False,'v7_train_one_video_actions':13,'v7_train_top10_video_share':0.926254281684465},
    'sampling_stability':{'sampling_seeds':{'train':2026102261,'test':2026102262},'new_seed_pairs_verified':1,'decay04_three_seed_stability_assessed':False,'previous_decay02_evidence_not_transferred':True},
    'aspect_selection_policy':{'initial':'economy','refine_if_either_aspect_six_axis_deviation_above':.10,'train_triggered':False,'test_triggered':True,'source':'partition_trials.json'},
    'wardrobe_conditional_50_50_relaxed':False,'test_full_value_coverage_required':False,
    'budget_revision':old_branch['budget_revision'],
    'limitations':{'user_adoption':'pending','final_media_profile':'unfrozen','camera_binding_scope':'existing orientation-specific local trajectory template, not final site world trajectory','motion_reference_carrier_and_exact_scene_initial_frame_pending':True,'per_value_frequency_uniformity_claimed':False,'action_camera_coverage_sufficient_claimed':False,'graph_redesign_authorized_in_this_change':False,'per_aspect_slot_balance_not_all_uniform':True,'single_seed_pair_only':True,'reuse_near_two_is_soft':True},
    'previous_v7_result':{'run_root':old_branch['run_root'],'candidate':old_branch['candidate'],'history_axis_decay':.2,'actual_render_nodes_total':6150,'statistics_and_evidence':'dataset_dual_aspect_20261022_v7/REPORT.md; CURRENT_CANDIDATE.json; audit_agent/audit_selected.json','immutable_baseline':True},
    'previous_v6_result':old_branch['previous_v6_result'],
}
# Replace only this root member and preserve every other byte outside it.
raw=STATE.read_text(encoding='utf-8')
marker='"dataset_design_branch_20261021": '
start=raw.index(marker)+len(marker)
_,length=json.JSONDecoder().raw_decode(raw[start:])
replacement=json.dumps(branch,ensure_ascii=False,indent=2).replace('\n','\n  ')
write(STATE,raw[:start]+replacement+raw[start+length:])
changed.append(STATE)
new_state=read(STATE)
assert {k:v for k,v in new_state.items() if k!='dataset_design_branch_20261021'}==outside_before
assert protected_before=={str(p):digest(p) for p in protected}
for f in branch['evidence']:
    if f != 'documentation_result_sync.json':
        assert (ROOT/f).exists(),f
dump(ROOT/'documentation_result_sync.json',{
    'scope':'targeted v8 dataset documentation only; no full tree audit or catalog rebuild',
    'passed':True,
    'subsystems':{'technical':'0.4 actual method, owners and scope verified','contract':'current .4 distinguished from immutable .2 snapshots','status':'only dataset_design_branch root member changed; parent and other branches exact equal','registry':'new experimental reverse lookup and prior v7 historical scope','plan':'R17 supplementary record only; requirement status/current plan preserved','workflow_status':'offline experiment only; first-batch accepted Gate unchanged'},
    'independent_baseline_spotcheck':{'train_render_nodes':4963,'test_render_nodes':1187,'train_one_video_actions':13,'global_one_camera_actions':9,'global_action_camera_pairs':86,'train_top10_video_share':0.926254281684465},
    'structural_audit_passed':True,'aspect_audit_passed':True,'reference_binding_passed':True,
    'state_outside_dataset_branch_unchanged':True,
    'v7_protected_hashes_unchanged':protected_before,
    'current_evidence_paths_exist':True,
    'changed_document_hashes':[{'path':str(p.relative_to(REPO)).replace('\\','/'),'sha256':digest(p)} for p in changed],
    'skipped':['full repository audit','script/output catalog rebuild','full test suite','UE or CC operation','media and pixel acceptance','three sampling seed stability for .4','coverage graph redesign'],
    'unresolved':['action camera support remains sparse','candidate adoption pending','final media profile and reference carriers unconfirmed'],
})
print(json.dumps({'passed':True,'changed_documents':len(changed),'current_render_nodes':6439},ensure_ascii=False))
