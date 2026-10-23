"""Scoped synchronization of verified v10 result; no graph or media mutation."""
import collections
import hashlib
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent;ROOT=HERE.parent;REPO=ROOT.parents[2]
DOCS=REPO/'20_planning/data_design/character_creator/full_process';ASPECT=ROOT/'aspect_work'
changed=[]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pin(p):return {'path':str(p.relative_to(REPO)).replace('\\','/'),'sha256':digest(p)}
def write(p,s):p.write_text(s,encoding='utf-8',newline='\n')
def edit(rel,operation):
    p=DOCS/rel;old=p.read_text(encoding='utf-8');new=operation(old);assert new!=old,rel;write(p,new);changed.append(p)
def section(text,heading,replacement):
    i=text.index(heading);j=text.find('\n## ',i+len(heading));return text[:i]+replacement.rstrip()+'\n'+(text[j:] if j>=0 else '')
def pool_ranges(unit):
    return {k:{'values':v['denominator_values'],'min_ratio':min(v['ratios_to_own_mean'].values()),'max_ratio':max(v['ratios_to_own_mean'].values())} for k,v in unit['distributions'].items()}

freq=read(ROOT/'structural_frequency_audit.json');inherited=read(ROOT/'structural_inherited_audit.json')
projection=read(ASPECT/'aspect_audit.json');projected_freq=read(ASPECT/'projected_frequency_audit.json');projected_inherited=read(ASPECT/'projected_inherited_audit.json')
reference=read(ASPECT/'reference_binding_check.json');selection=read(ROOT/'CURRENT_CANDIDATE.json')
candidate_ref=Path(selection['candidate'])
assert (candidate_ref if candidate_ref.is_absolute() else ROOT/candidate_ref).resolve()==(ASPECT/'selected_candidate').resolve()
assert all(d['passed'] for d in (freq,inherited,projection,projected_freq,projected_inherited,reference))
assert (ROOT/'REPORT.md').exists()
assert reference['checked_step_links']==52560
assert sum(projection['splits'][s]['actual_render_nodes'] for s in ('train','test'))==7203
assert all(projection['splits'][s]['nodes_duplicated_across_aspects']==0 for s in ('train','test'))
state_path=DOCS/'project_management/status/PROJECT_STATE.json';old_state=read(state_path)
outside={k:v for k,v in old_state.items() if k!='dataset_design_branch_20261021'}
protected=[ROOT.parent/v/f for v in ('dataset_dual_aspect_20261022_v7','dataset_decay04_20261022_v8') for f in ('CURRENT_CANDIDATE.json','RULES.json')]
protected_before={str(p):digest(p) for p in protected}
refs=reference['actual_reference_counts'];images=sum(v for k,v in refs.items() if k!='motion');clips=refs['motion']
stats={};l5={}
for split in ('train','test'):
    a=freq['splits'][split];pa=projection['splits'][split];ia=inherited['splits'][split]
    chains=[json.loads(x) for x in (ROOT/'structural_candidate'/split/'sessions.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
    l5[split]={kind:sum(len({st['axis'] for st in c['steps']}) for c in chains if c['length']==5 and (kind=='all' or c['kind']==kind))/sum(c['length']==5 and (kind=='all' or c['kind']==kind) for c in chains) for kind in ('all','linear','fork')}
    stats[split]={'nodes':pa['actual_render_nodes'],'content_nodes':pa['unique_nonaspect_states'],'chains':a['counts']['sessions'],'edits':a['counts']['edit_occurrences'],
        'history_occurrences':a['counts']['history_occurrences'],'render_nodes_by_aspect':pa['render_nodes_by_aspect'],'chains_by_aspect':pa['sessions_by_aspect'],
        'additional_aspect_versions':0,'unique_content_frequency_ranges':pool_ranges(a['unique_content_node_frequency']),
        'history_occurrence_frequency_ranges':pool_ranges(a['chain_history_occurrence_frequency']),
        'minimum_effective_cameras_per_action':min(x['actual'] for x in a['action_effective_camera_minimum'].values()),
        'effective_action_camera_pairs':sum(x['actual'] for x in a['action_effective_camera_minimum'].values()),
        'genuinely_introduced_core':ia['genuinely_introduced_core']['distinct'],
        'semantic_edge_reuse':a['semantic_directed_edge_reuse'],'six_axis_max_relative_deviation':a['six_nonidentity_max_relative_deviation'],
        'conditional_single_fraction':ia['wardrobe_formal_opportunity']['conditional_single_fraction'],
        'single_slot_total_variation':ia['single_slot_legacy_diagnostic']['conditional_actual_vs_expected_total_variation'],
        'formal_slot_opportunities_missing_in_graph_fraction':ia['single_slot_legacy_diagnostic']['graph_missing_formal_slot_opportunity_fraction'],
        'L5_mean_distinct_axes':l5[split]}
refs_sentence=f'参考需求从最终候选重算，共{images:,}张图片和{clips:,}段动作视频（{sum(refs.values()):,}项需求），52,560个步骤链接检查通过；只是未渲染需求。'
current='''## 当前数据集分支：第十轮分散候选离线检查通过，待采用（2026-10-22）

当前主候选由`%OUTPUT_ROOT%/dataset_distributed_graph_20261022_v10/CURRENT_CANDIDATE.json`绑定`aspect_work/selected_candidate`，阅读入口`REPORT.md`。训练来自`trial12/candidate4`、测试来自`test_work/trial12/candidate3`；构造由少数富集块补缺值，改为从生成阶段分配服装与其他属性的普通可编辑上下文。旧v6/7/8及未采用的v9补覆盖路线保留历史范围；第十轮实验candidate5不混入主候选。

训练5,980、测试1,223个实际used内容状态及主视频请求，共7,203；横竖没有重复内容副本，比v8的6,439增加764（11.87%）。保留12,000／2,400条结构链和43,800／8,760次编辑。整连通分量分配画幅，横／竖链训练6,388／5,612、测试1,252／1,148，每条链及全部历史／分支固定画幅；这达到本组固定内容与链的零额外画幅副本成本，不证明其他构图无法更少。

独立检查通过：训练40人物、25动作、28发型、7发色、21点位和239件可见核心衣物全部实际使用；六维度在唯一内容节点和最终完整链history中的频率各自均在本维度均值0.5–1.5范围，每动作内部镜头频率也分别达标。每个训练动作至少15种合法有效镜头（要求10），共443个动作×有效镜头组合；每件训练core至少3动作、3有效镜头。测试只按所选8人物／6动作／6发型／7色／6点／32core核算频率，不宣称测试全目录覆盖；实测各测试动作至少17有效镜头。head不充有效动作镜头，但仍计入全局动作频率，逐动作head集中度另有诊断。

旧约定同样独立重算：训练各轴真实编辑target全目录、239衣物真正换入、两个split的21起始镜头整数配额、正式衣物合法性、完整父历史、链配额及忽略画幅的跨split隔离均通过。六非身份轴最大偏差训练4.66%、测试7.73%；具体边最高4次，四次边占已用不同内容边0.49766%／0.16876%。平均边复用2.137／2.112，低于约2.5软目标，不复制数据凑数。条件single为48.01%／47.39%，部位TV为0.01408／0.09178，低量部位残差仍如实保留，不宣称五部位均等。

方法和代价必须同时保留：最终训练在0.4全历史衰减及全局反馈产生的35,621条不同候选链中，按相同kind／length／起始镜头做673次整链约束交换，保留原子语义与每条被选链的完整历史；不是纯0.4概率抽样，也不是多seed稳定性证明。覆盖和频率改善的代价是L5平均不同编辑轴下降：训练v8约3.950→3.177、测试3.588→3.150；没有新增最少不同轴硬门槛。'''+refs_sentence+'''

当前只通过本轮离线结构／分布／画幅／参考绑定检查，采用仍待用户审阅；最终分辨率、帧率、时长、动作参考载体与场景精确初帧未冻结。下一步审查本候选及上述成本和链内多样性取舍，再确定媒体规格与小样。未操作共享UE、点位、曝光或资产，未启动媒体／渲染／训练，不关闭R17或晋升生产Gate；唯一current父计划与其他分支保持。
'''
edit('project_management/status/PROJECT_STATUS.md',lambda t:section(t,'## 当前第十轮：',current).replace('2026-10-22（仅数据集分支0.4重采样与覆盖核查同步）','2026-10-22（仅第十轮分散候选离线结果同步）',1))
top='**当前入口（第十轮分散候选，离线通过待采用）**：`%OUTPUT_ROOT%/dataset_distributed_graph_20261022_v10/REPORT.md`，由根`CURRENT_CANDIDATE.json`绑定`aspect_work/selected_candidate`。实际结构来自`structural_candidate/SOURCES.json`，训练candidate4、测试test_work candidate3；实验candidate5只作比较。新频率／上下文要求与继承语义、整链画幅、参考绑定独立检查通过，未渲染或接受为生产；结果及方法代价见本节执行回填。\n\n'
def tech_update(t):
    t=re.sub(r'^> 最近核验：.*$', '> 最近核验：2026-10-22（第十轮分散候选实际结果与独立审计同步）',t,count=1,flags=re.M)
    i=t.index('**当前授权（第十轮分散构图执行中）**');j=t.index('**最后已验证入口（第八版',i)
    t=t[:i]+top+t[j:]
    t=t.replace('## 第十版：从生成阶段分配频率与上下文（2026-10-22，执行中）','## 第十版：从生成阶段分配频率与上下文（2026-10-22）',1)
    t=t.replace('候选结果待实际生成后独立核验；授权同步记录为`documentation_authorization_sync.json`。','候选的最终结果见下节，授权时快照为`documentation_authorization_sync.json`，最终同步为`documentation_result_sync.json`。',1)
    return t+'''

### 第十版执行回填：实际节点、完整历史和画幅独立通过

唯一主选择由根`CURRENT_CANDIDATE.json`绑定`aspect_work/selected_candidate`，图链来源由`structural_candidate/SOURCES.json`拥有。训练采用`trial12/candidate4`，其`SELECTION.json`保存35,621不同候选链的来源／sampler哈希、673次同kind／length／起始镜头整链交换及最终绑定；测试采用`test_work/trial12/candidate3`，`repair_trace.json`保存其明确整链选择过程。基础采样为全历史0.4衰减与频率反馈，最终另做显式约束选择；原kind／length配额、完整父历史、原子合法性、自然重复和回访允许性保持。不能宣称独立无条件随机样本或把多次候选生成当三seed稳定性。

训练5,980／测试1,223个内容状态全部被真实主链使用，结构链12,000／2,400、编辑43,800／8,760。`structural_frequency_audit.json`与`structural_inherited_audit.json`分别证明新节点／history频率与旧真实target／起始镜头／单件机会约定，包含注册边、provenance、父历史和跨split检查；旧5,000／800节点上限仅作为已被用户替代的历史限制披露，不重新启用。训练40身份、25动作、28发型、7色、21点和239可见core在唯一内容及完整history计数均落在各自均值0.5–1.5；每动作内部有效镜头频率同样通过。训练每动作至少15有效镜头、443个组合，core各至少3动作／3镜头；head只从有效动作镜头和core可见计数排除，仍计全局动作频率，并输出逐动作head集中度。测试只选值范围通过，不强求全目录。

训练各轴真实编辑target全目录与239core source→target真正新换入保持，两split起始21镜头1.5／1最大余数整数配额精确通过；正式有single机会的分母独立解析，不以图内是否安排该slot替代正式合法性。条件single训练48.01%、测试47.39%，部位TV 0.01408／0.09178，保存图缺少正式slot机会的比例见独立审计；这些是允许局部候选的支持缺口，不是非法slot，也不能宣称全部部位机会均已安排。具体内容有向边cap4通过，4次边占比0.49766%／0.16876%；全边平均reuse2.137／2.112、服装较低，约2.5保持软目标，不复制数据凑平均。

`aspect_work/component_partition.py`按完整连通分量分配画幅，`aspect_work/selected_assignment/SOURCES.json`保存选择。最终实际请求仍5,980／1,223，共7,203，内容无横竖重复副本，比v8实际6,439增11.87%。横／竖链训练6,388／5,612，测试1,252／1,148；分画幅六轴偏差训练6.26%／9.17%、测试9.68%／8.50%，不另设分画幅各值频率硬要求。`aspect_work/aspect_audit.json`、`projected_frequency_audit.json`和`projected_inherited_audit.json`独立确认源新链恰好保留一次、画幅固定、请求绑定及原频率／target不失效。该固定内容集的画幅成本已无额外副本，不是全局最少图节点的证明。

链内多样性是明确代价：五步链平均不同轴训练3.177353（linear3.161／fork3.200714），测试3.150（linear3.1725／fork3.117857），低于v8约3.950294／3.588235。新覆盖与频率通过不写成各维度全面提高；没有新增链内最少不同轴、禁止回访或生产Gate。未选candidate5保留作实验，不混入主候选。

'''+refs_sentence+'''精确需求按`aspect_work/selected_candidate/reference_summary.json`／`reference_manifest.json`及`aspect_work/reference_binding_check.json`读取；动作／场景区分画幅，身份／发型／衣物图按原规则共享。最终媒体规格、参考载体及场景精确初帧仍待确认，camera模板绑定不是最终场景世界轨迹接受。

本Technical还拥有`audit_work/audit_inherited_contract.py`、`audit_work/sync_authorization_docs.py`、`audit_work/sync_final_result_docs.py`及其回执。构图、采样、整链选择和画幅脚本的精确来源／版本由各候选SELECTION／SAMPLER_CODE、根方法清单及`aspect_work/INPUTS_AND_METHODS.json`保存。只做本次合同、证据、哈希和本地链接定向检查，不扩展全仓审计或目录重建；UE、媒体、训练及多seed稳定性未验收，R17／唯一current父计划保持。
'''
edit('technical/dataset/DATASET_DESIGN_EXPLORATION_20261021.md',tech_update)
edit('technical/dataset/DATASET_TRIAL_CONTRACT_20261021.md',lambda t:re.sub(r'^> 最近核验：.*$', '> 最近核验：2026-10-22（第十轮确认规则与离线执行回填）',t,count=1,flags=re.M).replace('当前根`%OUTPUT_ROOT%/dataset_distributed_graph_20261022_v10/`仅执行中，候选与独立证据实际完成后回填。','当前根`%OUTPUT_ROOT%/dataset_distributed_graph_20261022_v10/`的离线执行结果见下述回填；上述目标不因结果反改。',1)+'''

### 第十轮执行回填（2026-10-22）

当前选择由该根`CURRENT_CANDIDATE.json`绑定`aspect_work/selected_candidate`，训练candidate4／测试test_work candidate3。独立结构、真实target、起始配额、两种频率计数、有效动作镜头／训练core上下文、画幅与参考绑定检查通过；采用仍待用户审查，不代表UE／媒体或全阶段Gate通过。最终采用的是0.4基础采样与频率反馈后的明确整链约束选择，不宣称最终数据仍按纯0.4条件概率抽样；来源和交换保存于SELECTION／repair_trace及SOURCES。不同候选生成不作为多seed稳定性证明。

实际请求共7,203，横竖无重复内容副本，较v8增11.87%；约2.5边复用保持软目标，实测约2.14／2.11，不重复数据凑数。五步链不同轴均值较v8下降，具体取舍由探索Technical与REPORT拥有；不新增最少不同轴或禁止回访。原目录和未选实验保持，R17、唯一current父计划及其他分支不变。
''')
wf='''## 当前R17设计实验：第十轮分散候选离线检查通过（2026-10-22）

本节不替换第一批已接受图与GATE-70。当前候选由`%OUTPUT_ROOT%/dataset_distributed_graph_20261022_v10/CURRENT_CANDIDATE.json`绑定`aspect_work/selected_candidate`；训练candidate4、测试test_work candidate3，来源见structural_candidate/SOURCES。新逐值节点／完整history频率、动作有效镜头、训练core上下文及原真实target／起点／合法历史规则均独立通过，整链画幅和参考绑定亦通过。v9补覆盖路线未采用，旧v8保持其原结构验证范围。

该结果仍为experimental离线候选，待采用；成本增加和L5链内不同轴下降见[探索Technical](../../../technical/dataset/DATASET_DESIGN_EXPLORATION_20261021.md)及根REPORT，不能写成整体各维度全面提升。最终媒体与参考实际接入待定，不启动UE／渲染／训练，不晋升既有生产Gate、不关闭R17。
'''
edit('project_management/status/workflows/WF-70.md',lambda t:re.sub(r'^> 最近核验：.*$', '> 最近核验：2026-10-22（仅第十轮离线结果同步；第一批Gate保持）',section(t,'## 当前第十轮：',wf),count=1,flags=re.M))
plan='''## R17 数据集分支：第十轮分散候选离线交付（2026-10-22）

按用户恢复后的逐值频率和上下文要求完成分散构图，选择由`%OUTPUT_ROOT%/dataset_distributed_graph_20261022_v10/CURRENT_CANDIDATE.json`绑定，阅读REPORT。实际used内容与完整链历史分开审计，新频率／动作镜头／训练衣物上下文和既有真实target／起点／原子历史规则均通过；画幅固定与参考需求已重算并检查。v9补覆盖路线未采用，主选择训练candidate4／测试test_work candidate3，未选candidate5不混入。

成本与链内不同轴下降须交用户共同评估，准确数字由项目状态／探索Technical／机器证据拥有；不将约2.5软复用目标当已精确达到，也不把离线分布通过写成媒体或生产接受。下一步审查候选与取舍，再确定媒体规格、参考载体／精确初帧及小样。R17保持in_progress，本父计划唯一current，其他需求与local_work保持。
'''
edit('project_management/plans/active/PLAN-2026-10-CAMERA-MOTION-SCENE-ALIGNMENT.md',lambda t:section(t,'## 当前第十轮：',plan))
def registry(t):
    lines=t.splitlines()
    for i,line in enumerate(lines):
        if line.startswith('| 第十轮生成阶段分散构图'):
            lines[i]='| 第十轮生成阶段分散离线候选 | `%OUTPUT_ROOT%/dataset_distributed_graph_20261022_v10/CURRENT_CANDIDATE.json`、`RULES.json`、`structural_candidate/SOURCES.json`、`structural_frequency_audit.json`／`structural_inherited_audit.json`、`aspect_work/selected_assignment/SOURCES.json`、`aspect_work/aspect_audit.json`、`aspect_work/selected_candidate/reference_manifest.json`及`aspect_work/reference_binding_check.json` | experimental；真实内容／完整history逐值频率、旧target／起点、整链画幅与未渲染参考需求独立通过；当前主候选训练4／测试3，采用与成本／L5取舍查Status，不作为正式Render Jobs | [数据集探索第十版](../technical/dataset/DATASET_DESIGN_EXPLORATION_20261021.md) | `WF-60`／`WF-70`（离线研究），`WF-80`仅后续接入 |'
            break
    else:raise AssertionError('v10 registry row missing')
    return '\n'.join(lines)+'\n'
edit('registry/README.md',registry)
state=read(state_path);b=state['dataset_design_branch_20261021']
b.update(status='distributed_dual_aspect_offline_candidate_verified_pending_user_adoption_not_rendered',reading_entry='REPORT.md',candidate='aspect_work/selected_candidate',current_candidate='CURRENT_CANDIDATE.json',
    scope=['from_scratch_distributed_editable_contexts','actual_used_unique_content_and_full_history_frequency_verified','formal_visible_core_including_locked_bundles','explicit_whole_chain_constrained_selection_after_decay04_feedback_sampling','fixed_component_aspect_assignment_and_unrendered_reference_requests'],
    structural_integrity_passed=True,all_experiment_hard_checks_passed=True,all_registered_nodes_used=True,target_node_and_session_quotas_filled=True,offline_candidate_selected=True,
    new_chain_sampling_for_selected_candidate=True,all_new_structural_sessions_preserved_exactly_once=True,
    next_action='用户审查第十轮7203实际主视频、完整频率与覆盖改善及L5链内不同轴下降的取舍后决定采用，再确认最终媒体规格、动作参考载体／场景精确初帧及小样；未开始UE、媒体、渲染或训练。',
    evidence_status='structural_frequency_inherited_semantics_aspect_and_reference_binding_independent_checks_passed_not_rendered',
    primary_candidate_statistics=stats,actual_render_nodes_total=7203,content_nodes_total=7203,additional_aspect_versions=0,
    actual_render_increase_vs_v8=764,actual_render_fraction_increase_vs_v8=7203/6439-1,
    canonical_content_train_test_overlap=0,structural_chain_train_test_overlap=0,
    explicit_final_semantic_and_distribution_checks_passed=True,
    references={'unrendered_only':True,'counts_by_kind':refs,'images':images,'motion_videos':clips,'checked_step_links':52560},
    selection_method={'train':'trial12/candidate4/SELECTION.json','test':'test_work/trial12/candidate3/repair_trace.json','train_unique_chain_pool':35621,'train_same_kind_length_start_camera_swaps':673,'pure_unconditioned_decay04_sampling_claimed':False,'unselected_candidate5_is_not_current':True},
    evidence=['CURRENT_CANDIDATE.json','REPORT.md','RULES.json','structural_candidate/SOURCES.json','structural_frequency_audit.json','structural_inherited_audit.json','aspect_work/aspect_audit.json','aspect_work/projected_frequency_audit.json','aspect_work/projected_inherited_audit.json','aspect_work/selected_assignment/SOURCES.json','aspect_work/selected_candidate/reference_manifest.json','aspect_work/selected_candidate/reference_summary.json','aspect_work/reference_binding_check.json','documentation_result_sync.json'])
b.pop('all_confirmed_sampling_rules_satisfied',None)
b['limitations'].update(user_adoption='pending',sampling_stability='not_assessed; multiple feedback/selection candidates are not independent-seed stability',final_media_profile='unfrozen',L5_axis_diversity_tradeoff={'v10':l5,'v8_baseline':{'train':3.9502941176470587,'test':3.588235294117647}},mean_reuse_2_5_soft_target_not_exactly_reached=True,no_per_aspect_full_value_frequency_acceptance_claim=True,media_and_training_unstarted=True)
b['overall_diversity_accepted']=False
raw=state_path.read_text(encoding='utf-8');marker='"dataset_design_branch_20261021": ';start=raw.index(marker)+len(marker);_,length=json.JSONDecoder().raw_decode(raw[start:]);write(state_path,raw[:start]+json.dumps(b,ensure_ascii=False,indent=2).replace('\n','\n  ')+raw[start+length:]);changed.append(state_path)
assert {k:v for k,v in read(state_path).items() if k!='dataset_design_branch_20261021'}==outside
assert protected_before=={str(p):digest(p) for p in protected}
for rel in b['evidence']:
    if rel!='documentation_result_sync.json':assert (ROOT/rel).exists(),rel
for p in changed:
    if p.suffix=='.md':
        for ref in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
            if not ref.startswith(('http:','https:','#','mailto:')) and '://' not in ref:assert (p.parent/ref.split('#',1)[0]).exists(),(p,ref)
receipt={'schema':'scoped_v10_verified_result_documentation_sync','passed':True,'scope':'only current dataset experimental branch and affected technical/contract/status/registry/plan/workflow-status owners',
    'candidate':'aspect_work/selected_candidate','train_selection':'trial12/candidate4','test_selection':'test_work/trial12/candidate3','candidate5_selected':False,
    'subsystems':{'technical':'actual method, output ownership, scripts, cost and L5 limitations recorded','contract':'agreed goals unchanged; offline execution and non-pure sampling disclosed','status':'only dataset root member changed; user adoption pending','registry':'current experimental candidate/evidence reverse lookup verified','plan':'R17 in_progress and unique parent plan preserved','workflow_status':'offline experiment only; first-batch production Gate preserved'},
    'state_outside_dataset_branch_unchanged':True,'v7_v8_protected_current_and_rules_unchanged':protected_before,
    'documents':[pin(p) for p in dict.fromkeys(changed)],
    'verified_evidence':[pin(ROOT/p) for p in b['evidence'] if p!='documentation_result_sync.json'],
    'all_changed_document_local_link_targets_exist':True,'main_render_nodes':7203,'additional_aspect_versions':0,'reference_counts':refs,
    'limitations':['pending user adoption','L5 mean distinct axes lower than v8','mean reuse below soft 2.5 target','unfrozen final media profile/reference carrier/exact scene frame','no media or UE acceptance','no independent-seed stability claim'],
    'skipped':['full repository audit','script/output catalog rebuild','full test suite','shared UE/CC operation','media generation','pixel validation','training']}
write(ROOT/'documentation_result_sync.json',json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'passed':True,'documents':len(changed),'actual_render_nodes':7203,'references':refs,'adoption':'pending'},ensure_ascii=False))
