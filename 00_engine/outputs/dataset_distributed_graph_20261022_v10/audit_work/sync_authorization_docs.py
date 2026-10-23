"""Scoped v10 authorization sync, not candidate acceptance."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=HERE.parent;REPO=ROOT.parents[2]
DOCS=REPO/'20_planning/data_design/character_creator/full_process'
changed=[]
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,s):p.write_text(s,encoding='utf-8',newline='\n')
def pin(p):return {'path':str(p.relative_to(REPO)).replace('\\','/'),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def edit(rel,old,new):
    p=DOCS/rel;t=p.read_text(encoding='utf-8');assert old in t,rel;write(p,t.replace(old,new,1));changed.append(p)
assert (ROOT/'RULES.json').exists() and (ROOT/'PLAN.md').exists()
assert read(HERE/'wardrobe_binding_feasibility.json')['witness_found']
state_path=DOCS/'project_management/status/PROJECT_STATE.json';old_state=read(state_path)
outside={k:v for k,v in old_state.items() if k!='dataset_design_branch_20261021'}
rules_text='''## 当前第十轮：分散构图与逐值频率规则已确认，执行中（2026-10-22）

用户恢复执行，要求从生成阶段安排丰富、均衡的属性及组合，不再沿用少量富集组合加覆盖叶节点的路线。当前实验根为`%OUTPUT_ROOT%/dataset_distributed_graph_20261022_v10/`，输入规则和计划分别是`RULES.json`与`PLAN.md`；当前没有通过或已采用的候选，v8只作最后已验证结构基线，v9补覆盖路线未采用。

训练须覆盖40人物、25动作、28发型、7发色、21点位及239件正式核心衣物。人物／动作／发型／发色／场景／可见核心衣物逐值频率，分别在实际used唯一内容节点和最终链全部历史位置中核算，均以各自维度均值0.5–1.5倍为目标；越界必须列明，不能只用“出现过”声称通过。训练每动作至少10种合法有效镜头，且该动作在所用镜头中的频率也在自身均值0.5–1.5倍；每件训练core至少3动作、3有效镜头，不要求完整3×3。人物随机合法搭配，没有每件衣物人物数配额。测试不强求全目录，按已选值核算频率；所选动作可用时争取10镜头，仅作诊断和软目标，不增加测试硬门槛。

服装必须由正式解析器展开固定绑定，面部近景不计衣物，五种半身镜头仅计upper与core交集，其余镜头计core；横竖副本不充内容多样性。独立服装域预检找到239件均满足频率范围的合法连续分布正例，固定绑定本身无需自动豁免；该结果不证明完整图、整数节点或链已可行。0.4全历史衰减、平均有向边复用约2.5软目标、cap4及稀少第四次、原历史／原子／服装／配额／跨split隔离与整链画幅规则保持。

当前只完成授权、独立审计入口和服装可行性预检；构图、链、双画幅、参考与成本结果仍待实际核验。下一步在分散可编辑上下文上构造并独立重算节点与链频率，失败项如实保留，再决定候选采用和媒体小样。未启动UE、媒体、渲染或训练；R17、唯一current父计划与其他分支保持。

'''
edit('project_management/status/PROJECT_STATUS.md','## 当前第九轮：动作镜头覆盖重建已授权，执行中（2026-10-22）',rules_text+'## 历史第九轮：补齐动作镜头的路线未采用（2026-10-22）')
edit('project_management/status/PROJECT_STATUS.md','第九轮预定运行根为`%OUTPUT_ROOT%/dataset_action_camera_20261022_v9/`。当前是目标已确认、构造与验证执行中，尚无通过或已采用结论；下面v8数字仅作最后已验证基线，不是v9结果。第九轮完成后须独立重算每动作真实镜头覆盖、节点/链/边复用和参考需求，再更新当前候选指针。不启动UE、媒体、渲染或训练；R17与唯一current父计划保持。','第九轮根`%OUTPUT_ROOT%/dataset_action_camera_20261022_v9/`保留为方法比较与诊断，用户未采用该补丁路线。复查旧239核心件覆盖发现：153件只出现在1个内容节点，184件只搭配1人物、155件只搭配1动作、169件只搭配1镜头、166件只搭配1点位，103件真正换入次数至多4；正式解析含固定绑定。出现与真实换入是已核验事实，分布丰富度未通过新要求。此问题推动上述第十轮从生成阶段分散构图，不再把v9视为待晋升主体。')
edit('technical/dataset/DATASET_DESIGN_EXPLORATION_20261021.md','**当前授权（第九轮执行中）**：用户要求训练25动作各至少10种正式允许的镜头，按真实used主视频内容节点核验；保持衰减0.4，平均边复用软目标改为约2.5以减少节点，具体边cap4及其它规则保持。预定根`%OUTPUT_ROOT%/dataset_action_camera_20261022_v9/`由本Technical拥有，experimental、unclassified_protected；构造及验证待完成，不能写成已达标。','**当前授权（第十轮分散构图执行中）**：用户恢复执行并确认逐值频率与上下文分散规则，见[试构建契约最新修订](./DATASET_TRIAL_CONTRACT_20261021.md)。运行根`%OUTPUT_ROOT%/dataset_distributed_graph_20261022_v10/`的`RULES.json`／`PLAN.md`及`audit_work/`由本Technical拥有，experimental、unclassified_protected；构造和链的实际通过状态待核验。v9补覆盖路线未采用，原目录保留为诊断，不作为新图主体。')
p=DOCS/'technical/dataset/DATASET_DESIGN_EXPLORATION_20261021.md';write(p,p.read_text(encoding='utf-8')+'''

## 第十版：从生成阶段分配频率与上下文（2026-10-22，执行中）

本Technical拥有`%OUTPUT_ROOT%/dataset_distributed_graph_20261022_v10/`全部实验输出，包含构造、采样、整链画幅、参考与独立审计；当前为experimental、unclassified_protected，不晋升生产。精确规则由根`RULES.json`、`PLAN.md`拥有，正式语义见试构建契约第十轮。旧v6/7/8的单项覆盖与真实换入检查保留其原范围，不能改称新频率和分散要求通过；v9为未采用补覆盖路线，诊断见该根`wardrobe_diversity_review.json`。

独立入口`audit_work/check_wardrobe_binding.py`枚举正式解析的core与upper可见集合并保存完整非负权重正例；`wardrobe_binding_feasibility.json`、`wardrobe_binding_witness.json`表明239core在服装域可达到同一均值0.5–1.5范围，未发现必须自动豁免的固定绑定矛盾。这只是合法服装连续混合的正例，不证明整数图、完整链、节点预算或动作镜头联立可行。

`audit_work/audit_distributed.py`独立读取实际nodes／edges／sessions，不信任构造汇总；通过正式Rules解析固定绑定衣物，检查节点与链合法性、完整父历史、配额、cap4和去画幅跨split隔离。频率分别按真实被主链用到的唯一完整内容状态（合并画幅）和每条链全部history位置逐次计数，含初始／弃支／回访。训练完整目录包含零计数；测试只按被选值。head不计core或动作有效镜头，upper取正式upper与core交集，其余计core；不推断像素遮挡。逐值频率、每动作内部镜头频率、动作镜头下限与训练core上下文门槛分别判定；反向的每镜头动作分布只作诊断。约2.5复用是软目标，不为凑平均值复制数据。

调用方式：`python -B audit_work/audit_distributed.py --candidate <含train/test的候选根> --output <新审计JSON>`。旧v8负对照`audit_work/v8_negative_control.json`硬语义通过且新分布检查失败，验证审计没有用画幅副本或“出现过”代替分布。构造／采样与画幅实现分别在根与`aspect_work/`，候选结果待实际生成后独立核验；授权同步记录为`documentation_authorization_sync.json`。不扩展全仓审计、目录重建、UE或媒体接受；R17与父计划状态保持。
''')
p=DOCS/'technical/dataset/DATASET_TRIAL_CONTRACT_20261021.md';write(p,p.read_text(encoding='utf-8')+'''

## 2026-10-22 第十轮：生成阶段分散与逐值频率（当前确认）

用户恢复执行，确认从生成阶段按频率和组合欠额建立可继续编辑的分散上下文，不接受先形成少数富集块、最后补缺值叶节点作为新路线。v9补覆盖候选未采用，不作为新构图主体；旧v6/7/8单项覆盖与真实换入是当时已验证事实，不能代表当前多样性要求通过。

训练全部目录值须实际使用：identity40／action25／hair28／hair_color7／site21及239件正式core。上述六维度逐值频率均以本维度全部值均值的0.5–1.5倍为目标；分别检查忽略画幅后的actual used唯一内容状态与全部最终链history位置次数。history含初始、弃支和回访，不能只统计编辑目标；两种统计各自通过，不能互相替代。测试不要求全目录，按实际选择的值核算，不能将训练全值要求套给测试。越界必须报告，不将目标自动解释为软放行；固定绑定如真有冲突须另列具体证据，不能自动豁免。

训练每动作至少10种正式允许的有效镜头，且每动作在实际采用镜头内的逐镜头频率也分别落在自身均值0.5–1.5；head不充动作有效镜头。不要求25×21全部组合。测试不要求全部25动作；所选动作可用时争取10种镜头，仅作诊断和软目标，不增加测试硬门槛。每件训练core至少3个动作和3种有效镜头，不要求完整3×3组合。服装频率优先，动作／镜头分散其次；人物随机合法分配，没有逐衣物固定人物数要求。

core按正式解析器展开固定绑定，不能把整包捏成一件或遗漏绑定内资产。可见性代理：front_head不计衣物，五种upper镜头取upper_asset_ids与core_asset_ids交集，其余镜头取core；鞋不计core多样性轴。不做像素可见性或遮挡已接受声明，画幅副本与未用池节点不能充内容多样性。

全历史0.4衰减、约2.5平均具体有向内容边复用软目标、cap4与第四次尽量稀少、六非身份轴次数偏差≤10%、起始镜头1.5／1权重和配额、原子合法性、完整历史、服装single／whole及鞋规则、训练测试内容隔离与整链画幅保持。主视频实际成本相对v8的6,439报告，不用旧允许预算冒充已控制成本；结果未构造前不冻结新视频总量。当前根`%OUTPUT_ROOT%/dataset_distributed_graph_20261022_v10/`仅执行中，候选与独立证据实际完成后回填。
''');changed.append(p)
edit('technical/dataset/DATASET_TRIAL_CONTRACT_20261021.md','当前第九轮覆盖修订已授权、执行待核验，见文末。','当前第十轮生成阶段分散与逐值频率规则已确认、执行待核验，见文末；第九轮补覆盖路线未采用。')
for rel in ('project_management/status/workflows/WF-70.md','project_management/plans/active/PLAN-2026-10-CAMERA-MOTION-SCENE-ALIGNMENT.md'):
    p=DOCS/rel;t=p.read_text(encoding='utf-8').replace('## 当前第九轮：动作镜头覆盖重建已授权，执行中','## 历史第九轮：补覆盖路线未采用',1)
    write(p,t+'\n\n'+rules_text);changed.append(p)
edit('registry/README.md','| 第八轮0.4历史衰减离线候选 |','| 第十轮生成阶段分散构图（执行中） | `%OUTPUT_ROOT%/dataset_distributed_graph_20261022_v10/RULES.json`、`PLAN.md`、`audit_work/wardrobe_binding_feasibility.json`及`audit_work/wardrobe_binding_witness.json` | experimental；当前仅规则／方法与服装域连续分布正例，图链候选待独立核验；不能视为已通过分布或正式Render Jobs | [数据集探索第十版](../technical/dataset/DATASET_DESIGN_EXPLORATION_20261021.md) | `WF-60`／`WF-70`（离线研究） |\n| 第八轮0.4历史衰减离线基线 |')
state=read(state_path);b=state['dataset_design_branch_20261021']
b.update(status='distributed_graph_rebuild_authorized_in_progress_not_yet_verified',run_root='%OUTPUT_ROOT%/dataset_distributed_graph_20261022_v10/',previous_round_root='%OUTPUT_ROOT%/dataset_action_camera_20261022_v9/',reading_entry='PLAN.md',candidate=None,current_candidate=None,
    scope=['distributed_editable_contexts_from_construction_not_coverage_leaves','independent_unique_content_and_full_history_frequency_audit','formal_visible_core_including_locked_bundles','fixed_aspect_and_reference_projection_after_semantics_pass'],
    evidence=['RULES.json','PLAN.md','audit_work/wardrobe_binding_feasibility.json','audit_work/wardrobe_binding_witness.json','audit_work/v8_negative_control.json','documentation_authorization_sync.json'],
    next_action='按已确认逐值频率与上下文门槛重建分散可编辑图，实际生成链后独立检查used内容节点和完整history频率，再分配画幅并重算参考／实际主视频成本；当前无候选通过结论。',
    evidence_status='v10_new_rules_authorized_wardrobe_domain_witness_verified_graph_and_sessions_pending')
b['new_target'].update({'frequency_ratio_to_own_mean':[.5,1.5],'frequency_fields':['identity','action','hair','hair_color','site','visible_core_garment'],'frequency_scopes':['actual_used_unique_content_states_ignoring_aspect','every_final_chain_history_occurrence_including_initial_abandoned_and_revisited'],'train_full_catalog_including_zeros':True,'test_selected_values_only':True,'per_action_camera_frequency_ratio_to_own_mean':[.5,1.5],'minimum_actions_per_train_core_garment':3,'minimum_effective_cameras_per_train_core_garment':3,'complete_action_camera_cross_product_required':False,'garment_identity_minimum':None,'garment_visibility':'head none; upper=intersection(formal upper,core); other=core','no_unproven_fixed_binding_exceptions':True,'construction':'distributed editable contexts from the beginning; no singleton coverage patch strategy'})
b['prior_v9_method_review']={'run_root':'%OUTPUT_ROOT%/dataset_action_camera_20261022_v9/','patch_route_adopted':False,'reason':'coverage thresholds alone left concentration and singleton contexts; user requested construction-method discussion then authorized distributed rebuild','wardrobe_review':'wardrobe_diversity_review.json','formal_core_assets':239,'core_assets_only_one_content_state':153,'core_assets_only_one_identity':184,'core_assets_only_one_action':155,'core_assets_only_one_camera':169,'core_assets_only_one_site':166,'core_assets_at_most4_genuine_target_occurrences':103}
b['new_target']['test_action_camera_min10_diagnostic_and_soft_target_only']=True
b['wardrobe_binding_precheck']={'formal_core_asset_count':239,'legal_visible_core_sets':726,'constructive_continuous_frequency_witness_found':True,'min_ratio_to_own_mean':read(HERE/'wardrobe_binding_feasibility.json')['witness_min'],'max_ratio_to_own_mean':read(HERE/'wardrobe_binding_feasibility.json')['witness_max'],'scope':'wardrobe-domain continuous mixture only; not joint graph/session feasibility'}
b['limitations']['sampling_stability']='pending_v10_execution';b['limitations']['user_adoption']='pending_v10_construction_and_independent_verification'
raw=state_path.read_text(encoding='utf-8');marker='"dataset_design_branch_20261021": ';start=raw.index(marker)+len(marker);_,length=json.JSONDecoder().raw_decode(raw[start:]);write(state_path,raw[:start]+json.dumps(b,ensure_ascii=False,indent=2).replace('\n','\n  ')+raw[start+length:]);changed.append(state_path)
assert {k:v for k,v in read(state_path).items() if k!='dataset_design_branch_20261021'}==outside
unique={str(p):p for p in changed}
receipt={'scope':'v10 agreed authorization, independent audit implementation and garment-domain precheck only; no candidate promotion','passed_scoped_authorization_sync':True,'candidate_verified':False,
    'subsystems':{'technical':'output/script owners and exact audit scopes recorded','contract':'latest frequency/context requirements supersede coverage-only sufficiency','status':'v10 in progress, v9 patch not adopted, last verified v8 retained','registry':'v10 rules/precheck reverse lookup; no nonexistent current candidate pointer','plan':'R17 supplement only; current parent and requirement states unchanged','workflow_status':'experimental rebuild; first-batch Gate unchanged'},
    'state_outside_dataset_branch_unchanged':True,'documents':[pin(p) for p in unique.values()],
    'precheck':pin(HERE/'wardrobe_binding_feasibility.json'),'audit_implementation':pin(HERE/'audit_distributed.py'),'negative_control':{'candidate':'v8 selected_candidate','passed_hard_semantics':True,'new_frequency_checks_passed':False},
    'skipped':['full repository audit','catalog rebuild','UE/CC operation','media acceptance','actual v10 graph/session acceptance pending'],
    'unresolved':['construct and independently verify actual v10 used content and complete histories','allocate whole-chain aspect and recompute references/cost','candidate adoption pending']}
write(ROOT/'documentation_authorization_sync.json',json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'scoped_authorization_sync':True,'changed_documents':len(unique),'candidate_verified':False}))
