from pathlib import Path
import json, hashlib, copy, re

ROOT = Path(__file__).resolve().parents[3]
RUN = Path(__file__).resolve().parent
DOC = ROOT / '20_planning/data_design/character_creator/full_process'
REL = '%OUTPUT_ROOT%/dataset_return_control_20261022_v11/'
def readj(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
current = readj(RUN/'CURRENT_CANDIDATE.json')
freq = readj(RUN/'frequency_audit.json')
inherited = readj(RUN/'inherited_audit.json')
returns = readj(RUN/'return_audit.json')
refs = readj(RUN/'reference_binding_check.json')
preserved = readj(RUN/'PRESERVATION.json')
assert current['all_requested_offline_checks_passed']
assert all([freq['passed'],inherited['passed'],returns['passed_checks'],refs['passed'],preserved['passed']])
assert all(sha(Path(p['path'])) == p['sha256'] for p in current['selected_file_pins'])
assert all(sha(Path(p['path'])) == p['sha256'] for p in current.get('implementation_pins',[]))
changed = []
before_pins = {}
def save(relative, text):
    path = DOC/relative
    before_pins[relative] = sha(path)
    path.write_text(text,encoding='utf-8',newline='\n')
    changed.append(relative)
def append(relative, text):
    old=(DOC/relative).read_text(encoding='utf-8-sig')
    assert '## 第十一轮' not in old and '## 第十一版' not in old
    save(relative,old.rstrip()+'\n\n'+text.strip()+'\n')

technical='technical/dataset/DATASET_DESIGN_EXPLORATION_20261021.md'
old=(DOC/technical).read_text(encoding='utf-8-sig')
old=old.replace('第十轮分散候选实际结果与独立审计同步','第十一轮属性回换控制实际结果与独立审计同步',1)
old=old.replace('**最后已验证入口（第八版历史衰减0.4）**','**历史入口（第八版历史衰减0.4）**',1)
old=old.replace('**当前入口（第十轮分散候选，离线通过待采用）**','**历史入口（第十轮分散候选，作为回换控制基线）**',1)
entry='**当前入口（第十一轮属性回换控制，离线通过待审）**：`%OUTPUT_ROOT%/dataset_return_control_20261022_v11/REPORT.md`；根`CURRENT_CANDIDATE.json`绑定`selected_candidate`，采用`trial2`。在第十轮不变图内重采样链后缀，回换降低且继承的频率／覆盖／合法历史与参考绑定检查通过；未渲染、未晋升生产。精确定义、方法保护条件与限制见本文第十一版。\n\n'
pos=old.index('**历史入口（第十轮')
old=old[:pos]+entry+old[pos:]
technical_add='''
## 第十一版：在原图内降低属性回换（2026-10-22）

本Technical拥有`%OUTPUT_ROOT%/dataset_return_control_20261022_v11/`全部离线实验输出及根`optimize_returns.py`、`optimize_returns_trial1_snapshot.py`、`audit_returns.py`、`finalize_candidate.py`、`sync_documentation.py`。当前选择由`CURRENT_CANDIDATE.json`绑定`selected_candidate`；采用`trial2`，`trial1`只作历史比较。节点、已注册合法图边与主视频请求同v10逐字节一致；每条链的实际起始节点、全部source_position父位置、kind／length、分叉轮次和画幅保持，只在已有合法图内提出并替换后缀路径，旧v10不改写。

显式属性回换是本步**编辑轴**的目标值存在于所选source的祖先路径；仅在弃支出现过的同值另计，分叉从历史source完整继承导致未编辑轴恢复也另计，二者不冒充显式回换。提议目标相对权重为新值1、刚换掉的祖先值0.05、更早祖先值0.20、仅其他分支出现值0.35；全history轴衰减0.4保持。属性提议还乘合法目标历史新颖权重均值，再按目标新颖度、剩余复用容量及暴露反馈抽样；整链随后经全局约束选择，权重不是最终概率，也不是纯0.4无条件随机样本。

第二轮增加保护旧编辑混合的实现条件：正式有single机会下的single比例47%–53%，身份次数相对v10偏移≤2%，六个非身份轴各自偏移≤5%，原六轴相对均值偏差≤10%仍独立通过；每条对应链不同轴数不低于旧链。这些是本轮实现保护条件，不新增用户数据硬契约，也没有禁止自然回访或新增统一最少不同轴门槛。隐式分叉恢复不受回换惩罚。第一轮虽通过原检查，但single约45%、身份次数约下降5%，故未采用。

| 指标 | 训练v10 | 训练v11 | 测试v10 | 测试v11 |
| --- | ---: | ---: | ---: | ---: |
| 显式祖先属性回换编辑 | 8,035 | 2,003 | 1,567 | 344 |
| 含显式回换链 | 6,107 | 1,584 | 1,192 | 273 |
| 完整节点重复出现 | 6,405 | 862 | 1,218 | 95 |
| 五步链平均不同编辑轴 | 3.177353 | 3.776765 | 3.150000 | 3.780882 |

主视频请求仍为5,980／1,223，共7,203，新增0；所有节点仍被链使用，结构链12,000／2,400及编辑43,800／8,760保持。训练全目录实际使用、各轴真实target、239core真正换入、唯一内容与完整history各自0.5–1.5频率、每动作有效镜头与每core上下文、起始镜头整数配额、服装合法性、原子完整历史、去画幅跨split隔离与cap4均复核通过。六轴最大偏差9.55355%／9.93474%，平均具体边reuse2.02778／2.03674，约2.5仍是软目标；四次边比例0.50000%／0.48826%。条件single47.01164%／47.04711%，不能写成精确50%。图内合法候选对正式slot机会的支持缺口仍由inherited审计诊断，不宣称所有机会均已安排。

参考需求按新链重算为1,609图片与809动作视频，共2,418项需求（旧v10动作视频789），52,560个步骤链接通过；均未渲染。精确结果由`return_audit.json`、`frequency_audit.json`、`inherited_audit.json`、`PRESERVATION.json`、`reference_binding_check.json`及`selected_candidate/reference_summary.json`／`reference_manifest.json`拥有；原频率与继承审计使用v10已有独立实现，结果与输入pin指向v11，不沿用旧通过结论。

复现先查`trial2/{train,test}_optimization.json`来源、seed、sampler哈希和实际尝试数；以根`optimize_returns.py`同source／seed及`--max-attempts`重放，训练450,000、测试150,000尝试，再执行`finalize_candidate.py`和`audit_returns.py`。本次文档同步由`sync_documentation.py`及`documentation_result_sync.json`拥有，只核验本轮7个所有者、证据pin与本地链接，不重建全树catalog或运行全库审计。剩余回换集中长链，隐式分叉恢复可能增加且另列诊断；未证明全局最优、多seed稳定性或媒体质量。当前待用户审阅采用，媒体规格／动作参考载体／精确场景初帧仍未冻结；未操作UE、媒体、渲染或训练，R17及唯一current父计划保持。
'''
save(technical,old.rstrip()+'\n\n'+technical_add.strip()+'\n')

contract='technical/dataset/DATASET_TRIAL_CONTRACT_20261021.md'
append(contract,'''## 第十一轮：降低显式属性回换偏好（2026-10-22）

用户授权在当前第十轮候选上减少A→B→A式属性回换。判定只沿本步所选source的真实祖先路径：被编辑轴目标值曾在该路径出现才是显式回换；只有其他分支出现的值另记重复，分叉完整继承导致未编辑轴恢复不算显式回换，也不施加该惩罚。仍允许自然回访与同轴连续编辑，不升级成禁止回换或统一最少不同轴门槛。

本轮以不变合法图提出新链后缀，起始节点、全部父位置、kind／length、分叉轮次与整链画幅固定。历史轴0.4衰减保持；新值／刚换掉值／更早祖先值／其他分支值提议相对权重1／0.05／0.20／0.35。合法目标新颖度参与轴提议，随后整链约束选择，因此权重不等于最终采样概率。原覆盖、两种频率0.5–1.5范围、动作镜头及core上下文、六轴均值±10%、具体边cap4、起始配额、服装条件、完整继承与跨split隔离均保持。

执行采用`%OUTPUT_ROOT%/dataset_return_control_20261022_v11/CURRENT_CANDIDATE.json`绑定的`selected_candidate`，来源`trial2`；第一轮未采用。single47%–53%、身份次数相对v10±2%、各非身份轴次数±5%与逐链不同轴不下降是保护原混合的本轮实现条件，不追加为用户长期硬契约。独立回换／频率／继承／保存边界／参考绑定检查通过；实际结果、代价及复现见[探索Technical第十一版](./DATASET_DESIGN_EXPLORATION_20261021.md)与根REPORT。仍待用户采用，未启动UE／媒体／渲染／训练，不晋升生产Gate或关闭R17。
''')

status='project_management/status/PROJECT_STATUS.md'
old=(DOC/status).read_text(encoding='utf-8-sig')
old=old.replace('> 最近更新：2026-10-22（仅第十轮分散候选离线结果同步）','> 最近更新：2026-10-22（第十一轮属性回换控制离线结果同步）',1)
old=old.replace('## 当前数据集分支：第十轮分散候选离线检查通过，待采用（2026-10-22）','## 历史第十轮：分散候选作为回换控制基线（2026-10-22）',1)
pos=old.index('## 历史第十轮')
new='''## 当前数据集分支：第十一轮属性回换明显减少，离线通过待审（2026-10-22）

当前入口为`%OUTPUT_ROOT%/dataset_return_control_20261022_v11/REPORT.md`，同根`CURRENT_CANDIDATE.json`绑定`selected_candidate`（trial2）。在原v10合法图内重采样链后缀；节点、图边、主视频请求逐字节保持，实际起始节点、全部历史父位置、链类型／长度／分叉轮次及画幅固定。v10保留作比较，trial1未采用。

训练显式属性回换由8,035降至2,003次，含回换链6,107降至1,584；测试1,567降至344次，含回换链1,192降至273。只把编辑目标回到所选source祖先值计为回换，其他分支重复和隐式分叉恢复分别诊断；后者不受惩罚。五步链平均不同编辑轴训练3.177353→3.776765、测试3.150000→3.780882。主视频仍5,980／1,223，共7,203，新增0；链12,000／2,400及编辑43,800／8,760保持。

全历史轴衰减0.4与原覆盖、两种频率、有效镜头／core上下文、起点、服装、合法完整历史、跨split隔离和cap4均独立复核通过。第二轮保护旧编辑混合，条件single47.01164%／47.04711%，身份次数相对v10偏移≤2%、各非身份轴≤5%，六轴最大均值偏差9.55355%／9.93474%；每条链不同轴数未下降。这些保护条件属于本轮实现，未追加长期硬契约。提议权重与整链选择方法见[探索Technical](../../technical/dataset/DATASET_DESIGN_EXPLORATION_20261021.md)，不宣称最终纯0.4概率抽样或全局最优。

参考按新链重算为1,609图片和809动作视频，共2,418项未渲染需求，52,560步骤链接通过。限定证据为`return_audit.json`、`frequency_audit.json`、`inherited_audit.json`、`PRESERVATION.json`、`reference_binding_check.json`及`documentation_result_sync.json`。下一步审阅剩余长链回换与候选取舍并决定采用，再确认最终媒体规格、参考载体／精确场景初帧及小样。未操作共享UE或启动媒体／渲染／训练，R17与唯一current父计划保持，不晋升生产Gate；全库审计和多seed稳定性未开展。

'''
save(status,old[:pos]+new+old[pos:])

wf='project_management/status/workflows/WF-70.md'
append(wf,'''## 第十一轮：当前R17回换控制候选离线通过（2026-10-22）

当前选择改由`%OUTPUT_ROOT%/dataset_return_control_20261022_v11/CURRENT_CANDIDATE.json`绑定`selected_candidate`（trial2）；前述第十轮保留为基线。原节点／合法图边／主视频请求逐字节保持，只重采样链后缀；实际起始节点、全部父位置、kind／length、分叉轮次及整链画幅固定。独立回换、原频率／真实target／起点／合法完整历史、保存边界及参考绑定检查通过，证据读取根REPORT及对应JSON。

显式回换只沿被选source祖先判定；未编辑轴的隐式分叉恢复另记且不罚。结果、保护旧编辑混合的实现条件和残余长链回换由[探索Technical](../../../technical/dataset/DATASET_DESIGN_EXPLORATION_20261021.md)拥有。仍为experimental离线候选待用户审阅，不替换第一批正式接受图或GATE-70；未启动UE、媒体、渲染或训练，不关闭R17。
''')

plan='project_management/plans/active/PLAN-2026-10-CAMERA-MOTION-SCENE-ALIGNMENT.md'
append(plan,'''## 第十一轮：R17属性回换控制离线交付（2026-10-22）

用户授权减少当前候选的属性回换；执行在不变v10合法图内重采样后缀，保存实际起始节点、全部父位置、kind／length、分叉轮次及画幅，原0.4历史轴衰减和覆盖／频率／服装／复用上限等条件保持。当前由`%OUTPUT_ROOT%/dataset_return_control_20261022_v11/CURRENT_CANDIDATE.json`绑定`selected_candidate`（trial2），旧v10和未采用trial1保留。

回换显著减少、逐链不同轴不下降与原约定已限定离线核验；准确结果和剩余长链回换由项目状态／探索Technical／根REPORT拥有。只沿所选source祖先值判显式回换，隐式分叉恢复不受惩罚；第二轮保护旧编辑混合的条件属于实现选择，不追加用户长期硬契约。下一步用户审阅后决定采用，再确定媒体规格、参考载体／精确初帧及小样；R17仍in_progress，本父计划唯一current，其他需求及local_work保持。未启动UE、媒体、渲染或训练，不关闭生产Gate，也不扩大为全库审计。
''')

registry='registry/README.md'
old=(DOC/registry).read_text(encoding='utf-8-sig')
old=old.replace('| 第十轮生成阶段分散离线候选 |','| 第十轮生成阶段分散历史基线 |',1)
old=old.replace('当前主候选训练4／测试3，采用与成本／L5取舍查Status','历史主选择训练4／测试3，当前已由第十一轮回换控制候选接续；原成本／L5取舍查Status',1)
row='| 第十一轮属性回换控制离线候选 | `%OUTPUT_ROOT%/dataset_return_control_20261022_v11/CURRENT_CANDIDATE.json`、`RULES.json`、`PRESERVATION.json`、`return_audit.json`、`frequency_audit.json`、`inherited_audit.json`、`selected_candidate/reference_manifest.json`及`reference_binding_check.json` | experimental；不变v10图内重采样后缀，trial2为当前选择；显式祖先属性回换降低，原频率／覆盖／父位置及参考绑定复核通过；实际采用与未渲染边界查Status | [数据集探索第十一版](../technical/dataset/DATASET_DESIGN_EXPLORATION_20261021.md) | `WF-70`（离线研究），`WF-80`仅后续接入 |\n'
pos=old.index('| 第十轮生成阶段分散历史基线 |')
save(registry,old[:pos]+row+old[pos:])

state_path=DOC/'project_management/status/PROJECT_STATE.json'
state_text=state_path.read_text(encoding='utf-8-sig')
state=readj(state_path)
branch=copy.deepcopy(state['dataset_design_branch_20261021'])
old_branch=copy.deepcopy(branch)
branch['previous_v10_result']={k:copy.deepcopy(old_branch[k]) for k in ['run_root','candidate','primary_candidate_statistics','selection_method','references','limitations']}
branch['status']='attribute_return_control_offline_candidate_verified_pending_user_adoption_not_rendered'
branch['run_root']=REL
branch['previous_round_root']=old_branch['run_root']
branch['candidate']='selected_candidate'
branch['scope']=['history_aware_suffix_resampling_on_unchanged_v10_graph','explicit_selected_source_ancestor_value_returns_reduced','initial_nodes_all_parent_positions_kind_length_fork_round_and_aspect_preserved','original_frequency_coverage_inheritance_and_reference_checks_recomputed','trial2_selected_with_baseline_edit_mixture_guards']
branch['next_action']='用户审阅第十一轮显式属性回换降低、剩余长链回换与隐式分叉恢复诊断后决定采用，再确认最终媒体规格、动作参考载体／场景精确初帧及小样；未开始UE、媒体、渲染或训练。'
branch['evidence']=['CURRENT_CANDIDATE.json','REPORT.md','RULES.json','return_audit.json','frequency_audit.json','inherited_audit.json','PRESERVATION.json','reference_binding_check.json','selected_candidate/reference_manifest.json','selected_candidate/reference_summary.json','trial2/train_optimization.json','trial2/test_optimization.json','documentation_result_sync.json']
branch['evidence_status']='v11_independent_return_frequency_inherited_preservation_and_reference_checks_passed_offline_only'
branch.pop('all_new_structural_sessions_preserved_exactly_once',None)
branch['all_baseline_chain_slots_preserved_exactly_once']=True
branch['new_target']['attribute_return_control']=readj(RUN/'RULES.json')['attribute_return_control']
branch['limitations']['L5_axis_diversity_tradeoff']['v11']={s:{'all':current['summary'][s]['final']['by_length']['5']['mean_distinct_axes'],'linear':returns[s]['distinct_axes']['linear_5']['mean'],'fork':returns[s]['distinct_axes']['fork_5']['mean']} for s in ['train','test']}
branch['limitations']['sampling_stability']='not_assessed; trial1/trial2 constrained searches are not independent-seed stability evidence'
branch['limitations']['implicit_unedited_fork_resets_penalized']=False
branch['limitations']['remaining_returns_concentrated_in_longer_chains']=True
branch['limitations']['graph_redesign_authorized_in_this_change']=False
branch['limitations']['global_optimum_claimed']=False
for s in ['train','test']:
    stat=branch['primary_candidate_statistics'][s]
    f=freq['splits'][s]; i=inherited['splits'][s]
    for dest,source in [('unique_content_frequency_ranges','unique_content_node_frequency'),('history_occurrence_frequency_ranges','chain_history_occurrence_frequency')]:
        stat[dest]={k:{'values':v['denominator_values'],'min_ratio':min(v['ratios_to_own_mean'].values()),'max_ratio':max(v['ratios_to_own_mean'].values())} for k,v in f[source]['distributions'].items()}
    stat['semantic_edge_reuse']=f['semantic_directed_edge_reuse']
    stat['six_axis_max_relative_deviation']=f['six_nonidentity_max_relative_deviation']
    stat['conditional_single_fraction']=i['wardrobe_formal_opportunity']['conditional_single_fraction']
    stat['single_slot_total_variation']=i['single_slot_legacy_diagnostic']['conditional_actual_vs_expected_total_variation']
    stat['formal_slot_opportunities_missing_in_graph_fraction']=i['single_slot_legacy_diagnostic']['graph_missing_formal_slot_opportunity_fraction']
    stat['L5_mean_distinct_axes']=branch['limitations']['L5_axis_diversity_tradeoff']['v11'][s]
    stat['explicit_ancestor_attribute_returns']={k:returns[s]['strict_explicit_ancestor_returns'][k] for k in ['events','chains']}
    stat['axis_edit_counts']=returns[s]['axis_counts']
branch['references'].update(counts_by_kind=current['reference_counts'],images=current['reference_image_total'],motion_videos=current['reference_video_total'],checked_step_links=refs['checked_step_links'])
branch['selection_method']={'source':old_branch['run_root']+old_branch['candidate'],'train':'trial2/train_optimization.json','test':'trial2/test_optimization.json','trial1_selected':False,'initial_nodes_and_all_parent_positions_preserved':True,'graph_nodes_edges_render_requests_byte_identical':True,'pure_unconditioned_decay04_sampling_claimed':False,'weights_are_proposal_not_final_probabilities':True,'implementation_guards_not_new_user_hard_contract':True}
decoder=json.JSONDecoder()
start=state_text.index('  "dataset_design_branch_20261021": ')
value_start=state_text.index('{',start)
_,length=decoder.raw_decode(state_text[value_start:])
replacement=json.dumps(branch,ensure_ascii=False,indent=2)
replacement='\n'.join(('  '+line if n else line) for n,line in enumerate(replacement.splitlines()))
new_state_text=state_text[:value_start]+replacement+state_text[value_start+length:]
new_state=json.loads(new_state_text)
assert {k:v for k,v in state.items() if k!='dataset_design_branch_20261021'} == {k:v for k,v in new_state.items() if k!='dataset_design_branch_20261021'}
save('project_management/status/PROJECT_STATE.json',new_state_text)

for relative,pairs in {
    contract:[('第十轮确认规则与离线执行回填','第十一轮属性回换控制与离线执行回填'),('最近已验证的第八轮规则为','第八轮历史规则为'),('当前第十轮生成阶段分散与逐值频率规则已确认、执行待核验，见文末；第九轮补覆盖路线未采用。','第十轮分散与逐值频率已离线核验，当前第十一轮降低显式属性回换的规则和结果见文末；第九轮补覆盖路线未采用。')],
    wf:[('## 当前R17设计实验：第十轮分散候选离线检查通过','## 历史R17设计实验：第十轮分散候选离线检查通过')]
}.items():
    path=DOC/relative
    text=path.read_text(encoding='utf-8')
    for old,new in pairs:
        text=text.replace(old,new,1)
    path.write_text(text,encoding='utf-8',newline='\n')

local_links=[]
for relative in changed:
    path=DOC/relative
    if path.suffix != '.md': continue
    for link in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
        if '://' in link or link.startswith('#') or link.startswith('mailto:'): continue
        target=link.split('#')[0]
        if not target: continue
        resolved=(path.parent/target).resolve()
        local_links.append({'document':relative,'target':link,'exists':resolved.exists()})
assert all(link['exists'] for link in local_links),[l for l in local_links if not l['exists']]
result={'passed':True,'scope':'7 localized documentation owners and v11 evidence pins only; no full-tree audit or catalog rebuild','changed_documents':[{'path':str(DOC/p),'before_sha256':before_pins[p],'sha256':sha(DOC/p)} for p in changed],'other_project_state_branches_unchanged':True,'current_plan_id_unchanged':new_state.get('current_plan_id')==state.get('current_plan_id'),'R17_and_production_gate_not_closed':True,'selected_file_pins_checked':len(current['selected_file_pins']),'local_file_links_checked':len(local_links),'local_file_links_passed':True,'evidence_files':[{'path':str(RUN/name),'sha256':sha(RUN/name)} for name in ['CURRENT_CANDIDATE.json','return_audit.json','frequency_audit.json','inherited_audit.json','PRESERVATION.json','reference_binding_check.json']],'skipped':['full documentation audit','catalog and output inventory rebuild','full repository tests','UE/media/render/training acceptance','multi-seed stability']}
result['implementation_pins_checked']=len(current.get('implementation_pins',[]))
result['implementation_files']=current.get('implementation_pins',[])
(RUN/'documentation_result_sync.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'passed':True,'documents':len(changed),'selected_file_pins':8,'local_links':len(local_links),'receipt':str(RUN/'documentation_result_sync.json')},ensure_ascii=False))
