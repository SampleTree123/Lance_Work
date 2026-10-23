# 新版多轮图与参考素材探索

> 文档 ID：`TECH-DATASET-EXPLORE-20261021`
> 文档类型：`technical`
> 生命周期：`experimental`
> 实现所有权：本次离线图构造比较、参考需求投影、预算计算与研究报告
> 适用阶段：`WF-10/WF-70` 的新批次设计探索，关联当前计划R17的渲染规划
> 最近核验：2026-10-22（第十一轮配置／内容采用与限定复审同步）

## 范围与状态

**当前入口（第十一轮配置／内容已采用，限定离线复审通过）**：`%OUTPUT_ROOT%/dataset_return_control_20261022_v11/REPORT.md`；根`CURRENT_CANDIDATE.json`绑定`selected_candidate`，采用`trial2`。在第十轮不变图内重采样链后缀，回换降低且继承的频率／覆盖／合法历史与参考绑定检查通过；未渲染、未晋升生产。精确定义、方法保护条件与限制见本文第十一版。

**历史入口（第十轮分散候选，作为回换控制基线）**：`%OUTPUT_ROOT%/dataset_distributed_graph_20261022_v10/REPORT.md`，由根`CURRENT_CANDIDATE.json`绑定`aspect_work/selected_candidate`。实际结构来自`structural_candidate/SOURCES.json`，训练candidate4、测试test_work candidate3；实验candidate5只作比较。新频率／上下文要求与继承语义、整链画幅、参考绑定独立检查通过，未渲染或接受为生产；结果及方法代价见本节执行回填。

**历史入口（第八版历史衰减0.4）**：`%OUTPUT_ROOT%/dataset_decay04_20261022_v8/REPORT.md`，由同根`CURRENT_CANDIDATE.json`绑定`selected_candidate`。使用同一第六版图，实际重采样新链后重新分配画幅并重算参考；不是只改参数记录。结构、画幅与参考绑定离线检查通过，采用及整体多样性仍待审。方法和限制见文末第八版。

**第七版历史入口（保留0.2原链）**：`%OUTPUT_ROOT%/dataset_dual_aspect_20261022_v7/REPORT.md`，主候选`selected_candidate`，选择由`CURRENT_CANDIDATE.json`绑定。沿用第六版`selected_seed1`的全部内容与原链，只分配整链画幅并按需复用／复制渲染节点；没有重采样主候选的链。当前为experimental离线候选，待用户采用、未渲染；媒体规格尚未冻结。独立证据为`audit_agent/audit_selected.json`，按最终候选重算的参考需求在`selected_candidate/reference_summary.json`与`reference_manifest.json`。

**第六版历史输入**：`%OUTPUT_ROOT%/dataset_compact_graph_20261022_v6/selected_seed1`，训练图N、测试图T，v68统一历史轴衰减0.2；`FINAL_SELECTION.json`、三seed独立组合证据和原目录保持不可变。另两seed仍只作稳定性备选，不合并为额外数据。

**第五版历史入口**：`%OUTPUT_ROOT%/dataset_balanced_graph_20261022_v5/REPORT.md`，`candidate_c_seed1`与源图`candidate_b`及原检查保留。下文旧版本保持其当时范围，不能拼接成第六版。

**最新决定（第二次试构建之后）**：用户已接受单节点候选目标有限、整个数据集保持多样性的构造方向，见[试构建契约](./DATASET_TRIAL_CONTRACT_20261021.md)“最新确认”节。下文v1/v2结果是修订前实验，不重写快照；其“等待讨论全目录均匀取舍”已由本决定替代。第三版已按修订实现，最新入口见下段；不因允许局部支持而自动接受旧图。

**历史入口（2026-10-21 第三版局部候选）**：`%OUTPUT_ROOT%/dataset_local_support_20261021_v3/REPORT.md`，候选`linked_complete/`。已完成原预算内足量节点/链，全部节点实际使用，结构与配额通过；多样性有改善也有退步，尤其测试回访偏多，待用户审阅，尚非正式渲染清单。v1/v2保持历史快照。

用户授权分支会话研究新阶段的数据集构造与渲染规划。原会话继续维护UE资产／场景／审查面板。此次交付是离线探索，不是新批次已冻结、图已投入生产或渲染已开始。第一轮已交付；用户随后授权第二轮自主发散研究，新的实验及对第一轮建议的修订另存，不覆盖第一轮快照。

已确认的新阶段规则包括2–5次单属性编辑、最多一次选择非最新历史源、完整继承被选源、文本改写不新增结构链、训练测试主视频不重合、沿编辑扩展再去重节点。此前V1的640节点／4000条直链及媒体参数仍作为历史首批规范保留，不自动套入这次候选。

当前唯一主计划不变，R17仍`in_progress`。本次不是第二个current主计划，未提升任何UE或正式数据发布Gate。

## 输出所有权

本Technical拥有：

```text
%OUTPUT_ROOT%/dataset_design_exploration_20261021_v1/
%OUTPUT_ROOT%/dataset_design_exploration_20261021_round2/
%OUTPUT_ROOT%/dataset_trial_build_20261021_v1/
```

运行根为研究证据，保留分类暂为`unclassified_protected`，本次不清理。下列入口是研究结果，不是正式Render Job或accepted Registry：

- `MORNING_BRIEF.md`：用户阅读入口与待决问题。
- `DISCUSSION_RECAP.md`：已确认语义和前次未细读讨论。
- `DESIGN_OPTIONS.md`：路线判断、实际实验及下一步推荐。
- `NODE_SESSION_SCHEMA.md`：非冻结字段草案。
- `RENDER_PREPARATION.md`、`render_budget_scenarios.json`：渲染接入与成本口径。
- `inventory/`：只读目录快照，动作以当前有效生产库过滤结果为准。
- `graph/`：构造程序、会话索引、指标及修正记录；最终主比较以`main_scene_holdout_*`为准，`sourcebalanced_scene_*`补充中间历史源比例。
- `references/`：原始文献阅读、参考设计、实际边需求投影与无媒体的manifest示例。
- `splits/`：划分候选、分叉正反例、独立图复验。
- `DELIVERY_MANIFEST.json`、`verification.json`：交付文件和限定检查。

根目录与索引仅链接本Technical，不复制动态实验数字。所有脚本生命周期为`experimental`，不进入生产入口。

## 实现入口

运行根内：

1. `graph/explore_graph_routes.py`：标准库离线生长与会话采样。可复现参数、主候选和早期被替代结果见`graph/GRAPH_ROUTES.md`。
2. `graph/verify_artifacts.py`：限定图／会话结构核验；不证明媒体可渲染。
3. `references/plan_reference_demand.py`：读取实际图和已用边、按参考键求并集。媒体URI为空，不能当已渲清单。
4. `prepare_render_budget.py`：目录计数和候选分辨率／帧率／时长的算术表；耗时、码率均为假设，非性能实测。
5. `verify_delivery.py`：主候选及中间历史源配额候选的限定独立复验，参考输入哈希、交付链接和状态检查；生成交付manifest。
6. `graph/export_topology_inventory.py`：只读导出本轮所用有效动作／人物／镜头和点位输入，不调用UE。

仅重算预算：

```powershell
python 00_engine/outputs/dataset_design_exploration_20261021_v1/prepare_render_budget.py
```

原分支曝光／纹理交接仍由`technical/unreal/SCENE_CAMERA_SEQUENCE.md`及`%OUTPUT_ROOT%/render_readiness_20261021_v1/HANDOFF.md`拥有，本次不复制实现或修改共享UE状态。

## 检查边界与后续

实际图复验包括父历史引用、单轴继承、性别兼容域、训练测试节点和场景点隔离、分叉数、长度配额、输出状态去重、至少两个编辑轴，以及错误沿用最新源是否会留下可辨差异。详见运行根`verification.json`和`splits/INDEPENDENT_GRAPH_REVIEW.md`。

只检查本次研究交付及链接；按用户CVPR优先要求，没有扩展全仓审计／全库测试／共享目录重建。资产族独立性、实际衣物可见性、媒体效果和训练收益尚不是本轮已验证内容。

下一步由用户审阅主视频与参考预算、编辑轴语义、测试主张、长度／分叉来源配额及视频规格，再形成新批次冻结输入和一小组完整会话样例。不要直接将探索JSON提交UE渲染器。

## 第二轮自主发散研究

第二轮离线探索已交付，阅读入口为 `%OUTPUT_ROOT%/dataset_design_exploration_20261021_round2/MORNING_BRIEF.md`，完整导航为同根 `RESEARCH_MAP.md`，不同图来源见 `EXPERIMENT_FAMILIES.md`。以下输出同属本 Technical 的实验范围，保留分类仍为 `unclassified_protected`：

- `graph/`：两轴方格、多任务族、跨身份上下文扩展、节点预算、多 seed 与会话曝光策略的离线比较。
- `references/`：参考条件强度、原始文献、历史参考复用和成对输入控制。
- `evaluation/`：历史必要性、源等价、分叉位置、逐轮与滚动生成的评测语义。
- `experimental_design/`：场景分组候选与等视频／边／监督次数的对照实验。
- `observability/`：现有 production10 相机轨迹与代表骨骼的离线投影；不作为像素验收。
- `language/`：历史指代的可判定条件、中文模板及输入证据分层。
- `pilot_references/`、`pilot_session_proposal.json`：小样候选，不是正式任务。
- `wardrobe_domains/`：完整衣柜的单槽编辑域调查，不替换正式装配规则。
- `plan_render_order.py`、`select_pilot_sessions.py`、`explore_revision_controls.py`：离线渲染排序、会话小样与修订控制结构。
- `verify_round2_core.py`、`core_verification.json`：稳定七轴小任务族候选的独立限定核验；不代表所有实验文件、完整资产库或媒体通过。
- `verify_delivery.py`、`delivery_verification.json`、`DELIVERY_MANIFEST.json`：本轮语法、本地链接、固定核心输入哈希及交付清单；通过限定检查，未扩为全仓审计。

第二轮脚本生命周期均为 `experimental`。不同实验根、图候选和参考预算不得交叉拼成“已验证生产方案”；尤其第一轮五轴图的参考数量不能直接套给第二轮七轴图。媒体参数、场景语义分组、服装域、身份定义和最终比例继续等待用户讨论。当前唯一主计划与 R17 状态不变。

## 用户确认规则后的第一次试构建

本Technical同样拥有 `dataset_trial_build_20261021_v1/` 全部离线产物与下列experimental脚本：`normalize_catalog.py`、`verify_catalog.py`、`build_trial.py`、`probe_requested_sampling.py`、`verify_trial.py`、`plan_references.py`、`build_adversarial_cases.py`、`assemble_trial_report.py`、`verify_delivery.py`。分类为研究试构建、`unclassified_protected`，不删除旧结果，不晋升生产Registry或Render Job。

输入为当前正式轻量运行目录、真实衣柜验证、保存点位及人工排除。更新后的Rugged退役状态已纳入。已确认契约、详细旧规则替代清单、机器规则分别是本目录链接的试构建契约、运行根 `CONFIRMED_RULES.md`、`rules.json`；后两者保留完整用户决定。运行根有100条初步样本、1,000条无预算截断诊断、四种目标规模候选、独立完整状态/原子边/父历史/配额验证、11个案例及参考素材投影。

`TRIAL_REPORT.md` 是当前人类阅读入口，`trial_status.json` 是本次实验状态，`comparison.json` 仅比较本轮同域候选。`full_squares_uniform_nodes` 是诊断代表而非最终选择，未引用池节点不能计作有效数据；图内起点均匀、图内可用编辑重归一化与确认的全域分层抽样存在偏差。结构通过不证明条件概率、覆盖或渲染已接受。其参考需求只适用于该候选，所有媒体路径为空。

下一步修正节点/链的联合分配，保持用户已确认规则，先在原预算内改善条件选择机会与重复；分辨率、帧率、时长和画幅仍未冻结。暂用横屏符号域调用排除记录，不代表画幅已获最终确认。限定交付核验见运行根 `delivery_verification.json`，不扩展全仓目录重建或测试。R17保持in_progress，当前主计划仍唯一current。

## 用户确认规则后的第二次联合构造

本Technical拥有 `%OUTPUT_ROOT%/dataset_joint_build_20261021_v2/` 全部实验产物；分类为研究试构建、`unclassified_protected`。脚本生命周期均为experimental：`build_joint.py`、`alternative/pooled_exact.py`、`alternative/verify_prefix.py`、`audit/verify_joint.py`、`assemble_delivery.py`。依赖v1目录、正式服装解析和v1独立语义检查器；不进入生产脚本或Render Job。

当前阅读入口 `REPORT.md`，机器状态 `trial_status.json`，交付检查 `delivery_verification.json`。`joint_reserve35/` 保存固定预算内的联合构造，包含未完成提案；`alternative/` 保存完整域抽样的预算前缀及较大抽样诊断汇总；`audit/` 独立核验两条路线。统计支持不足和结构错误分开记录，partial核验不表示配额或采样通过。完整域较大诊断的节点增长不是理论下界，不得用它宣称预算无解。

当前发现：旧图内邻边重归一化放大回访；联合构造能降低回访，但失败重试产生接受偏差，长链缺额明显；完整域抽样条件分布较好，但节点成本大，初始有限根仍有支持偏差。下一步讨论局部候选支持与全目录条件均匀的取舍；用户尚未批准任何规则/预算变更。参考预算未重算，媒体未产出。只检查本轮文件、证据哈希与改动状态，不扩展全仓审计。R17和唯一current计划保持。

## 第三版：局部候选与整体多样性

本Technical拥有 `%OUTPUT_ROOT%/dataset_local_support_20261021_v3/` 全部试构建输出，生命周期experimental，保留分类unclassified_protected。脚本包括`blocks/build_blocks.py`、`blocks/build_diverse.py`、`blocks/verify_blocks.py`、`resample_local.py`、`refine_identity_links.py`、`complete_coverage.py`、`project_references.py`、`audit/verify_local.py`、`audit/compare_local.py`、`assemble_delivery.py`。仍依赖v1正式目录解析/结构检查和v2独立服装枚举；没有生产入口变更。

当前候选是`linked_complete/`；`blocks/`和其他balanced/linked目录仅是内部中间路线，不得混用。`CURRENT_RULES.json`和`CONTRACT_SNAPSHOT.md`显式保存局部目标修订；`REPORT.md`为简明入口，`REVIEW_EXAMPLES.md/.json`有六条真实链，`audit/verification_linked_complete.json`为最终独立证据。`linked_complete/reference_manifest.json`是该候选实际编辑所需的未渲染参考，不复用v1数量。`trial_status.json`明确整体多样性待审阅，`delivery_verification.json`只核验当前交付及文档一致性。

构造保留单轴合法编辑，先建立多值交叉块，再用预算内替换补充身份连接和缺失合法组/点位，最终按合法边重建父节点引用。会话起点平衡身份，属性/服装模式采用局部候选及累计频次反馈；未禁止自然回访或单属性链，未强制过滤分叉等价结果。该反馈不构成精确条件随机性声明。

已完成原预算、类型/长度配额和完整状态隔离；测试重复较多，部分编辑方向与搭配弱于v1，整体多样性尚未接受。下一步由用户审阅测试重复和覆盖取舍，再确定是否采用该候选及媒体规格。仅做本轮证据、语法、链接与状态字段检查，不扩为全仓审计或UE验证；R17/唯一current计划不变。

## 第四版：宽属性组合与序列覆盖对照

本Technical拥有`%OUTPUT_ROOT%/dataset_sequence_graph_20261021_v4/`全部离线研究产物，experimental、unclassified_protected。脚本为`build_sequence.py`、`build_wide.py`、`build_wide_balanced.py`、`build_rotated.py`、`sample_wide.py`、`check_sampling_stability.py`、`audit/compare.py`、`assemble_report.py`；依赖v1正式目录与规范化、v3共同采样及独立v1/v2/v3检查。

用户授权同预算尝试。最新入口`REPORT.md`，讨论候选`rotated/`，没有替换v3/linked_complete或采用新规则。独立证据`audit/final_comparison.json`；wide对照缺额是预期负例，rotated硬结构、数量和节点使用通过。宽属性提高链内不同属性数，但人物搭配广度下降、单件服装编辑比例不足；三个匹配抽样种子中一个测试种子短缺4条。`trial_status.json`明确整体未接受，参考需求未重算，未渲染。

下一步讨论联合兼顾链内多样性、跨上下文搭配及服装两模式支持，保留旧候选和节点预算。仅做本轮独立语义/配额/实际覆盖、定向文档同步及证据哈希检查，不重建全仓目录、不启动UE。R17和唯一current主计划保持。

### 第四轮用户反馈

用户接受人物搭配范围下降，后续单项属性值覆盖优先，跨属性搭配数量不再阻塞。本Technical另拥有v4运行根`REVIEW_DECISION_20261021.json`，其为后续评审结论；旧REPORT、trial_status和规则/契约快照保留当时状态，不再用其中的搭配不足作为当前待处理项。条件单件比例仍须澄清，尚未修改50/50目标；本次未重构图。

## 第五版：平衡、边复用与全历史衰减（2026-10-22，执行待核验）

本Technical拥有`%OUTPUT_ROOT%/dataset_balanced_graph_20261022_v5/`内全部离线构图、采样、验证及报告；生命周期experimental，保留分类unclassified_protected。稳定目标入口是`GOAL.md`，机器规则为`RULES.json`，优先于v3/v4预算、测试全值硬覆盖与旧待澄清项；正式语义依据[试构建契约最新修订](./DATASET_TRIAL_CONTRACT_20261021.md)。下文执行结果节已回填当前证据，不能将旧候选检查继承为v5通过。

训练/测试均重建，采用同语义、完整状态隔离、实际used节点/对应target覆盖检查、六非身份轴平衡、canonical具体有向边cap4与全历史轴衰减；训练要求全单项值，测试不强求全值但七轴充分样本且尽量广覆盖。边四次占比和各轴reuse为软优化，分母在RULES明确，偏差须报告。原链型/长度/fork抽样与single合法时约50/50保持。至少三个sampling seed检查两split，不要求全pair组合。

本轮不改UE、资产、点位、曝光，不启动参考媒体、正式渲染或模型训练；旧v4/trial保留，不做全树审计或目录重建。验证结果、实际实现入口及复现命令见下节；当前R17仍in_progress，父计划唯一current。

### 第五版执行结果、入口与限制（2026-10-22）

本Technical拥有运行根`build_balanced.py`、`sample_balanced.py`（v5.3）、`run_sampling.py`、`audit_candidate.py`、`summarize_results.py`，均为experimental离线入口，不进入生产Registry。当前实际选择由`CURRENT_CANDIDATE.json`绑定`candidate_c_seed1`与`candidate_b`；三seed各自有完整清单与audit，`candidate_c_seed2/3`仅是稳定性备选，不能合并使用。

主候选训练4,670个实际节点/12,000链/43,800编辑，测试768节点/2,400链/8,760编辑；没有闲置注册节点，canonical跨split重合0。训练40身份、28发型、7色、37family、45group、239core、25动作、21镜头、21点均在used节点和相应编辑目标全覆盖，core239件均真正换入。测试实际覆盖8身份、8发型、7色、8family、8group、35core、8动作、7镜头、8点；测试无全值硬要求。

训练六非身份轴次数最大相对偏差3.456%，测试1.972%；三seed最差约3.464%/2.022%，均低于10%。主seed具体有向边最高使用3次、4次边占比0；身份平均reuse训练2.106/测试1.968，其余非服装约1.846–1.891/1.822–1.846，服装1.300/1.435。服装低于2保留以减少重复，不为软目标额外复制数据。条件single为47.71%/50.56%，报告约50/50的偏差。

相对v4 rotated，L5平均不同轴数训练3.342→3.924、测试2.716→4.041。实际方法使用身份base2与软终局目标9%、六轴终局反馈、整段历史0.5^n及低复用边；显式衣物换入任务训练122/测试11，不改变原任务type/length/fork时刻及历史源。初始镜头分布仍受图影响，identity允许的四镜头占59.0167%/56.625%，不是全目录按weight1.5抽样的实测通过。六轴总次数均衡不等于各具体值均衡。测试单件边只涉及shirts；训练有shirts/coats/pants/full_body，不能声称测试覆盖全部部位。

复现顺序在本运行根执行：

```powershell
python -B build_balanced.py --variant candidate_b
python -B run_sampling.py --graph candidate_b --output candidate_c_seed1 --seed 2026102251
python -B audit_candidate.py --root candidate_c_seed1
```

另两训练sampling seed为2026102271/2026102291，测试各加1；只能证明固定同图采样稳定性，不能宣称构图seed稳定。结果和审查入口为`REPORT.md`、`comparison.json`、`sampling_stability.json`、`initial_camera_distribution.json`、`independent_three_seed_audit_summary.json`；输入版本、哈希及精确方法由运行根`INPUTS_AND_METHODS.json`保存。未改UE或资产、未产参考媒体、未渲染或训练；主候选待用户采用，R17未关闭。

## 第六版：紧凑图、完整起始镜头与合法单件部位条件（2026-10-22）

本Technical拥有`%OUTPUT_ROOT%/dataset_compact_graph_20261022_v6/`全部离线构图、采样、独立审计、选择与打包输出，分类仍为experimental、unclassified_protected，不进入生产Registry或Render Jobs。入口包括`build_compact.py`、`prune_head_contexts.py`、`sample_compact.py`、`run_sampling.py`、`audit_compact.py`、`initialize_rules.py`、`record_progress.py`、`report_selection.py`、`package_selection.py`、`finalize_selection.py`，以及`sample_compact_v61_snapshot.py`至`sample_compact_v68_snapshot.py`和各图/候选内源码快照；旧变体是实验来源而非共同主候选。`GOAL.md`、`RULES.json`、`INPUTS_AND_METHODS.json`拥有精确输入与参数，`FINAL_SELECTION.json`、`CURRENT_CANDIDATE.json`、各`ASSEMBLY.json`和`DELIVERY_MANIFEST.json`拥有选择、来源及交付闭包。

当前推荐`selected_seed1`组装自`candidate_n_v68_train_decay02_seed1/train`与`candidate_t_v68_test_decay02_seed1/test`，分别绑定`graph_n/train`与`graph_t/test`。训练4670→3752节点，测试768→800节点，总5438→4552，减少886个待渲染主视频（16.29%）；参考媒体另计。训练/测试为12000/2400链、43800/8760编辑，全部注册节点实际使用，canonical和整链跨split重叠均为0。训练40身份、28发型、7色、37family、45group、239核心件、25动作、21镜头、21点均成为实际对应轴编辑目标；239核心件按相对来源真正新换入计数，不把陪同保留的旧衣服算作换入。全值目标覆盖不等于逐值编辑频次均匀，部分长尾值只有少量目标编辑。测试实际使用/编辑目标为14身份、6发型、6色、8family/8group、34核心件、6动作、21镜头、7点，不强求全目录值。

21种起始镜头用完整目录整数配额：四种身份编辑镜头各weight1.5、其余各1，目标身份镜头合计6/23；覆盖任务也占用这些配额。主seed起始身份镜头占比训练26.0833%、测试26.1667%，单镜头相对偏差最大0.142%/0.625%来自整数舍入。单件部位平衡按每次实际single来源正式可用部位累计条件期望，包含镜头可见性、锁套装及精确衣服规则，不要求五部位各20%，不从期望中删除图中欠缺的合法部位。whole-only来源从约50/50单件比例分母排除。主seed条件single为48.64%/51.95%，部位最大相对偏差2.28%/8.57%。

实际v68 sampler保留identity基础2/其他1、全历史轴次数衰减与累计平衡反馈，统一历史衰减改为0.2，显式全轴目标覆盖任务及尾期残余支持fallback均有记录；不宣称每一步纯随机或完整目录精确条件均匀。原linear/fork与长度配额、先抽fork时刻/非最新父位置、完整父状态继承和具体有向边cap4不变。三个固定同图sampling seed分别训练2026102261/2281/2301、测试各加1，均完整独立通过；只能证明该固定图/代码的采样稳定性，不能声称构图seed稳定。三组测试4次边占已用不同有向边为0%/0.4583%/0.3268%，均满足≤0.5%软目标；各轴reuse约2仍有残差，尤其主seed服装1.219/1.282、镜头1.551/1.426，不复制数据凑数。

主seed L5不同轴均值训练4.215、测试3.813；相较v5约3.924/4.041，训练提高、测试下降。此取舍伴随较少节点、修正后的21镜头起点分布和合法部位支持，不把测试下降隐藏成全面胜出。同起始镜头、同kind/length的对照与共同支持范围见独立审计；旧测试缺少14种起始镜头，不能补造这些镜头的历史均值。第三seed测试coats15次vs条件期望17次只差2次，其相对−11.76%是低计数残差，正式与实际事件中的coats图缺slot率均为0，不解释为结构缺边。

从本运行根复核已组装候选：

```powershell
python -B audit_compact.py --root selected_seed1 --output diagnostics_selected_seed1_independent_audit.json
```

也可用`--train-root`和`--test-root`直接核验不同来源split，无需复制文件，报告保存精确source paths；单split结果明确未检查跨集隔离。三组源组合证据为`diagnostics_n_t_decay02_seed1/2/3_composite_audit.json`及`diagnostics_n_t_decay02_v68_three_seed_summary.json`。构造与采样复现使用`INPUTS_AND_METHODS.json`、每个图/候选的源码快照、参数与hash，不用最终默认入口冒充旧变体。失败和保底记录见`ITERATIONS.md`与`diagnostics_iteration_summary.json`；n+S/0.3保底、旧v5及未采用U等不覆盖、不合并、不删除。

本轮只完成离线候选验证，未改共享UE、资产、点位或曝光，未产参考媒体、未渲染或训练，未冻结生产规格或推进生产Gate。下一步由用户审查`selected_seed1`的节点成本、镜头/服装分布及测试L5取舍后决定是否采用，再讨论媒体规格和参考素材；R17继续in_progress，唯一父计划保持current。

## 第七版：保留原链的双画幅分配（2026-10-22）

本Technical拥有`%OUTPUT_ROOT%/dataset_dual_aspect_20261022_v7/`全部离线分配、物化、参考需求、独立审计与报告；生命周期experimental、保留分类unclassified_protected。实现入口包括`materialize.py`、`assemble_selection.py`、`check_references.py`，`partition_agent/`、`resample_agent/`内离线实验脚本，以及`audit_agent/audit_dual_aspect.py`、`verify_audit_rejections.py`、`audit_resampled_aspect.py`、`diagnose_selected_aspects.py`和`sync_v7_documentation.py`。它们不进入生产渲染器；旧目录与未选重采样备选保持独立，不拼接。

主候选`selected_candidate`从`dataset_compact_graph_20261022_v6/selected_seed1`保留4,552个非画幅完整内容状态、12,000／2,400条原链及43,800／8,760次原编辑。每条链的初始、完整历史与全部分支固定同一画幅；画幅不作为编辑轴，横竖副本不增加独立结构链。训练使用`partition_agent/economy/train`，测试使用`partition_agent/axis_balanced/test`，精确来源及统一政策由`selected_assignment/SOURCES.json`绑定。政策先以共享节点少的整链分配控制成本；若任一画幅的六非身份轴次数相对该画幅六轴均值偏差超过10%，再细化分配。训练没有触发，测试触发；不是训练测试使用互不相关的选择口径。

实际渲染节点训练4,963、测试1,187，总6,150；相对4,552个内容状态新增1,598个画幅版本（35.1%），每个实际used渲染节点只安排一份请求。用户已允许横竖链数近似与视频数适度超出原5,000／800预算，参考素材另计。每画幅均有男女、21种起始镜头及七编辑轴；起始镜头的横竖分配约20–80%，不声称每个镜头精确各半。六非身份轴在每画幅内的最大偏差训练横1.99%／竖6.08%、测试横5.37%／竖8.52%；精确实际次数及条件single／部位分布由最终分画幅诊断拥有。

由于主候选原链逐条保留，忽略画幅后的整体编辑次数、训练全属性目标覆盖、239核心件真正换入、L5不同轴均值和原有具体边复用计数均保持。实际带画幅渲染边仍满足cap4，跨split在去掉画幅后完整状态仍隔离；不把画幅版本包装成新内容或新链。分画幅部位条件比例须如实报告，不能用整体不变推断每个画幅逐项均匀。`audit_agent/selected_per_aspect_diagnostics.json`独立确认整体axes/modes/conditional及slot实际数和正式条件期望exact保持；分画幅条件single训练横50.016%／竖47.402%、测试横53.077%／竖50.791%。训练外套横93次vs条件期望119.5、竖71vs46.5，仍有分画幅残差；测试竖外套1vs3.5、裙子7vs4只是少量事件但相对偏差大，不能写成全部部位均衡。重采样备选虽可用更少节点，曾有跨画幅结构重复并已另存修复，仍有训练换衣部位支持与分布回归，未作为主候选；详见`audit_agent/RESAMPLED_REVIEW.md`。

`selected_candidate/{train,test}/render_requests.json`为未执行的离线请求，每项含完整state、original_node_id及camera_binding。正式库`production_workflow_20261017_v1/camera_library/production10/camera_plan.json`按`motion_id/camera_id/orientation`选择双画幅条目；请求绑定其shot_id、尺寸与局部trajectory_sha256，实际保存点位变换后的世界轨迹需另算。库中1280×720／720×1280及既有时钟仅为当前轨迹预设，不能写成最终分辨率、帧率或时长已冻结。正式排除也按site/action/camera/aspect区分，当前原节点的portrait合法性检查通过。

参考需求由最终候选实际使用边重算：动作视频和场景空背景图的键含画幅；人物正脸、发型正背与单件衣物／鞋素材可以跨主画幅共享。`reference_manifest.json`和`reference_summary.json`均为planned_not_rendered，`reference_binding_check.json`核对实际52,560次步骤链接和画幅需求绑定；动作载体、最终时钟与场景精确初帧绑定仍按清单所列边界待定，不宣称参考媒体已存在。

最终定向复核：

```powershell
python -B 00_engine/outputs/dataset_dual_aspect_20261022_v7/audit_agent/audit_dual_aspect.py --root 00_engine/outputs/dataset_dual_aspect_20261022_v7/selected_candidate --require-render-requests --output 00_engine/outputs/dataset_dual_aspect_20261022_v7/audit_agent/audit_selected.json
```

独立审核逐原节点／原链映射核对完整历史、恰一次fork、正式合法边、同链画幅、去画幅split隔离、真实节点数及每节点唯一请求／镜头绑定；反例探针验证混画幅和错误历史父位置会被拒绝。`REPORT.md`、`CURRENT_CANDIDATE.json`、`audit_agent/audit_selected.json`与`documentation_result_sync.json`为本轮结果入口。当前仅离线候选待用户采用，未改共享UE、点位、曝光或资产，未启动参考媒体、渲染或训练，不提升生产Gate，R17和唯一current父计划保持。


## 第八版：历史轴衰减0.4与动作镜头覆盖核查（2026-10-22）

本Technical拥有`%OUTPUT_ROOT%/dataset_decay04_20261022_v8/`全部离线输出，experimental、unclassified_protected。用户将全历史轴衰减从0.2改为0.4，即某轴已在完整历史出现n次时乘0.4^n；包括弃支，不改为只看当前分支。旧v6/v7的0.2记录与目录保持冻结。新规则为`RULES.json`，当前候选由`CURRENT_CANDIDATE.json`绑定，完整说明见`REPORT.md`。

实际实现复用v6 `selected_seed1`训练N/测试T节点和边，`same_graph_check.json`逐值确认图相同；保存的v68 sampler与种子train2026102261/test2026102262实际生成新链。其他既有采样参数、覆盖预热、反馈和尾期fallback保持并在`INPUTS_AND_METHODS.json`／`structural_candidate/SAMPLER_CODE.json`披露，不能宣称纯概率采样。实验脚本为`finish_candidate.py`、`compare_decay.py`、`analyze_action_camera.py`与`sync_documentation.py`；sampler副本与来源由机器方法清单拥有。重建会覆盖本实验输出，复算应先复制到新运行根；不覆盖历史输入。

结构候选保留3,752／800个内容状态，生成12,000／2,400条新链与43,800／8,760次编辑；双画幅物化后为5,256／1,183个实际used主视频请求，共6,439。每条新链及历史／分支固定同一画幅，分配完整保留的是本轮新链，不是v7原链。横／竖链训练6,013／5,987、测试1,200／1,200；整体六非身份轴偏差训练3.63%、测试4.60%，分画幅训练3.02%／4.23%、测试4.59%／5.37%。初始21镜头整数配额、训练全单项真实编辑目标、239核心衣物真正换入、原子合法性、完整历史、配额及去画幅跨split隔离检查通过。具体边最高训练3次、测试4次，测试4次边3条占已用不同具体边0.06494%。

同图单种子对比较显示：训练／测试重复轴步骤占比由11.58%／18.28%升至15.97%／22.19%；训练L5不同轴均值linear3.954、fork3.945，测试3.620／3.5429。该变化符合较弱重复抑制的方向，不写成链内轴多样性全面改善。仅核验一个新采样种子对和一次画幅分配，未执行0.4三seed稳定性或全局最优搜索，旧0.2三seed证据不继承为新候选稳定性。

动作覆盖单独核查：`baseline_action_camera.json/.md`统计v7；`selected_action_camera.json/.md`统计本轮。主视频按唯一渲染请求计数，镜头种类合并男女与画幅；参考只统计实际action编辑需求，不等于全部主视频组合。v7训练25动作中13个各只有1个主视频／1种镜头，前10动作占训练主视频92.63%；全体合并仅86个动作×镜头组合、9动作只有1镜头。v8保持同一内容图，动作×镜头支持仍为86，动作参考支持78；训练单独为55个动作×镜头组合，平均每动作2.2种、最多4种镜头，测试只含6动作。训练仍有13动作各仅1个内容状态，其中12动作各1个渲染请求，另1动作的同一内容有横竖两个版本。调整衰减没有解决该稀疏性。单项25动作／21镜头全覆盖和七轴总次数平衡不能作为动作镜头充分覆盖或各动作频次均衡的证据。覆盖不足进入下一步讨论，本轮未获授权重构图或新增覆盖门槛。

条件single训练48.70%、测试51.59%，正式合法部位条件分布TV为0.00259／0.00097；训练仍有约5.89%正式部位机会未在保存图内安排，且分画幅小量残差未宣称全面均衡。参考按最终候选重算：1,002图片与153动作视频，共1,155项需求，52,560步骤链接检查通过；最终媒体规格、动作参考载体、场景精确初帧仍未冻结。独立证据为`structural_audit.json`、`aspect_audit.json`、`reference_binding_check.json`和本轮`documentation_result_sync.json`。限定核验不包括全树审计、目录重建、UE/像素或训练收益；未启动媒体、渲染或训练，不晋升生产Gate，R17与唯一current父计划保持。


## 第十版：从生成阶段分配频率与上下文（2026-10-22）

本Technical拥有`%OUTPUT_ROOT%/dataset_distributed_graph_20261022_v10/`全部实验输出，包含构造、采样、整链画幅、参考与独立审计；当前为experimental、unclassified_protected，不晋升生产。精确规则由根`RULES.json`、`PLAN.md`拥有，正式语义见试构建契约第十轮。旧v6/7/8的单项覆盖与真实换入检查保留其原范围，不能改称新频率和分散要求通过；v9为未采用补覆盖路线，诊断见该根`wardrobe_diversity_review.json`。

独立入口`audit_work/check_wardrobe_binding.py`枚举正式解析的core与upper可见集合并保存完整非负权重正例；`wardrobe_binding_feasibility.json`、`wardrobe_binding_witness.json`表明239core在服装域可达到同一均值0.5–1.5范围，未发现必须自动豁免的固定绑定矛盾。这只是合法服装连续混合的正例，不证明整数图、完整链、节点预算或动作镜头联立可行。

`audit_work/audit_distributed.py`独立读取实际nodes／edges／sessions，不信任构造汇总；通过正式Rules解析固定绑定衣物，检查节点与链合法性、完整父历史、配额、cap4和去画幅跨split隔离。频率分别按真实被主链用到的唯一完整内容状态（合并画幅）和每条链全部history位置逐次计数，含初始／弃支／回访。训练完整目录包含零计数；测试只按被选值。head不计core或动作有效镜头，upper取正式upper与core交集，其余计core；不推断像素遮挡。逐值频率、每动作内部镜头频率、动作镜头下限与训练core上下文门槛分别判定；反向的每镜头动作分布只作诊断。约2.5复用是软目标，不为凑平均值复制数据。

调用方式：`python -B audit_work/audit_distributed.py --candidate <含train/test的候选根> --output <新审计JSON>`。旧v8负对照`audit_work/v8_negative_control.json`硬语义通过且新分布检查失败，验证审计没有用画幅副本或“出现过”代替分布。构造／采样与画幅实现分别在根与`aspect_work/`，候选的最终结果见下节，授权时快照为`documentation_authorization_sync.json`，最终同步为`documentation_result_sync.json`。不扩展全仓审计、目录重建、UE或媒体接受；R17与父计划状态保持。


### 第十版执行回填：实际节点、完整历史和画幅独立通过

唯一主选择由根`CURRENT_CANDIDATE.json`绑定`aspect_work/selected_candidate`，图链来源由`structural_candidate/SOURCES.json`拥有。训练采用`trial12/candidate4`，其`SELECTION.json`保存35,621不同候选链的来源／sampler哈希、673次同kind／length／起始镜头整链交换及最终绑定；测试采用`test_work/trial12/candidate3`，`repair_trace.json`保存其明确整链选择过程。基础采样为全历史0.4衰减与频率反馈，最终另做显式约束选择；原kind／length配额、完整父历史、原子合法性、自然重复和回访允许性保持。不能宣称独立无条件随机样本或把多次候选生成当三seed稳定性。

训练5,980／测试1,223个内容状态全部被真实主链使用，结构链12,000／2,400、编辑43,800／8,760。`structural_frequency_audit.json`与`structural_inherited_audit.json`分别证明新节点／history频率与旧真实target／起始镜头／单件机会约定，包含注册边、provenance、父历史和跨split检查；旧5,000／800节点上限仅作为已被用户替代的历史限制披露，不重新启用。训练40身份、25动作、28发型、7色、21点和239可见core在唯一内容及完整history计数均落在各自均值0.5–1.5；每动作内部有效镜头频率同样通过。训练每动作至少15有效镜头、443个组合，core各至少3动作／3镜头；head只从有效动作镜头和core可见计数排除，仍计全局动作频率，并输出逐动作head集中度。测试只选值范围通过，不强求全目录。

训练各轴真实编辑target全目录与239core source→target真正新换入保持，两split起始21镜头1.5／1最大余数整数配额精确通过；正式有single机会的分母独立解析，不以图内是否安排该slot替代正式合法性。条件single训练48.01%、测试47.39%，部位TV 0.01408／0.09178，保存图缺少正式slot机会的比例见独立审计；这些是允许局部候选的支持缺口，不是非法slot，也不能宣称全部部位机会均已安排。具体内容有向边cap4通过，4次边占比0.49766%／0.16876%；全边平均reuse2.137／2.112、服装较低，约2.5保持软目标，不复制数据凑平均。

`aspect_work/component_partition.py`按完整连通分量分配画幅，`aspect_work/selected_assignment/SOURCES.json`保存选择。最终实际请求仍5,980／1,223，共7,203，内容无横竖重复副本，比v8实际6,439增11.87%。横／竖链训练6,388／5,612，测试1,252／1,148；分画幅六轴偏差训练6.26%／9.17%、测试9.68%／8.50%，不另设分画幅各值频率硬要求。`aspect_work/aspect_audit.json`、`projected_frequency_audit.json`和`projected_inherited_audit.json`独立确认源新链恰好保留一次、画幅固定、请求绑定及原频率／target不失效。该固定内容集的画幅成本已无额外副本，不是全局最少图节点的证明。

链内多样性是明确代价：五步链平均不同轴训练3.177353（linear3.161／fork3.200714），测试3.150（linear3.1725／fork3.117857），低于v8约3.950294／3.588235。新覆盖与频率通过不写成各维度全面提高；没有新增链内最少不同轴、禁止回访或生产Gate。未选candidate5保留作实验，不混入主候选。

参考需求从最终候选重算，共1,609张图片和789段动作视频（2,398项需求），52,560个步骤链接检查通过；只是未渲染需求。精确需求按`aspect_work/selected_candidate/reference_summary.json`／`reference_manifest.json`及`aspect_work/reference_binding_check.json`读取；动作／场景区分画幅，身份／发型／衣物图按原规则共享。最终媒体规格、参考载体及场景精确初帧仍待确认，camera模板绑定不是最终场景世界轨迹接受。

本Technical还拥有`audit_work/audit_inherited_contract.py`、`audit_work/sync_authorization_docs.py`、`audit_work/sync_final_result_docs.py`及其回执。构图、采样、整链选择和画幅脚本的精确来源／版本由各候选SELECTION／SAMPLER_CODE、根方法清单及`aspect_work/INPUTS_AND_METHODS.json`保存。只做本次合同、证据、哈希和本地链接定向检查，不扩展全仓审计或目录重建；UE、媒体、训练及多seed稳定性未验收，R17／唯一current父计划保持。

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

复现先查`trial2/{train,test}_optimization.json`来源、seed、sampler哈希和实际尝试数；以根`optimize_returns.py`同source／seed及`--max-attempts`重放，训练450,000、测试150,000尝试，再执行`finalize_candidate.py`和`audit_returns.py`。本次文档同步由`sync_documentation.py`及`documentation_result_sync.json`拥有，只核验本轮7个所有者、证据pin与本地链接，不重建全树catalog或运行全库审计。剩余回换集中长链，隐式分叉恢复可能增加且另列诊断；未证明全局最优、多seed稳定性或媒体质量。用户已采用本候选配置与内容；媒体规格／动作参考载体／精确场景初帧仍未冻结；未操作UE、媒体、渲染或训练，R17及唯一current父计划保持。

### 第十一版采用与配置／内容复审（2026-10-22）

用户确认“没关系，现在这样就可以了”，采用的是现有v11配置与内容；随后要求重新审计各方面数据、内容和待修改项。[本轮审计报告](../../../../../../00_engine/outputs/dataset_return_control_20261022_v11/review_20261022/AUDIT_REPORT.md)是本次复审入口，`review_20261022/fresh_frequency_audit.json`／`fresh_inherited_audit.json`独立重算既有约定，`structure_findings.json`、`reference_findings.json`、`distribution_diagnostics.json`和`coverage_and_edits.json`补充结构、请求、参考与分布诊断。未发现需要重采样节点或链的内容错误；这是限定离线检查结论，不是像素、媒体质量、正式渲染或训练收益接受。

本Technical拥有`review_20261022/`全部实验输出、`audit_reference_semantics.py`、`audit_structure_supplement.py`及`sync_adoption_docs.py`。初始抽样名义男女50/50、分叉时点／父位置均匀是提议规则，不能写成约束选择后最终数据精确服从这些分布：最终训练起始链男女44.03%／55.97%，已披露为采用候选的诊断；不新增精确男女平衡门槛。整体六轴±10%仍通过；逐画幅最大偏差训练横8.41%／竖13.45%，测试横11.29%／竖12.09%，现契约没有每画幅六轴±10%硬门槛，故另列诊断而不追溯制造新失败。

复审发现`selected_candidate/REFERENCES.md`仍把画幅列为未定；本次仅修正文案为横竖双画幅已确定、具体分辨率／帧率／时长及制作实现待冻结。原扫描`reference_findings.json`保留观察事实，后续修正记录在`REFERENCE_REVIEW.md`及`documentation_sync.json`，不把原扫描改写成从未发现问题。历史源planner和已绑定finalizer不修改；未来重建参考说明时应保留此澄清。节点／边／会话／渲染请求／参考清单和CURRENT／RULES／旧交付绑定均未修改。

媒体参数、参考制作与文字模板、动作载体及相位／速度／时长对齐、场景精确初始世界相机／帧签名仍是正式渲染前的待办；当前符号场景键不证明真实初帧可复用。UE二进制与全像素可见性未在本轮重验。R17、唯一current父计划与其他分支保持，不启动UE／媒体／渲染／训练、不晋升生产Gate；本次只做受影响文件链接与哈希核对，不扩展全库审计或catalog重建。

### 渲染准备：视频规格确认（2026-10-22）

用户已确认主视频和动作参考视频统一10秒、30帧/秒、300个输出帧；横屏1920×1080，竖屏1080×1920。本Technical拥有后续媒体配置目录`render_preparation/`，当前部分配置为[VIDEO_PROFILE.json](../../../../../../00_engine/outputs/dataset_return_control_20261022_v11/render_preparation/VIDEO_PROFILE.json)。此配置补充已采用的v11内容，不重写候选、原审计快照或输入绑定。参考图片尺寸、输出编码、渲染质量与动作时钟／相位对齐继续逐项确定；尚未启动渲染。前文媒体参数未定是对应审计时的历史状态，以本条确认覆盖视频时长、帧率与分辨率三项。

补充确认（2026-10-22）：场景参考图与对应视频尺寸一致，横屏1920×1080、竖屏1080×1920；仍按当前镜头提供无人物的目标场景背景图。已记录在`render_preparation/VIDEO_PROFILE.json`的`scene_reference_images`字段；人物身份、发型、服装单件参考图尺寸继续待定。

补充确认（2026-10-22，其他参考图）：人物身份、发型和服装单件参考图统一1024×1024，每个视角单独一张、不拼图；调整取景使目标面部、发型或服装完整且尽量占满画面。记录在`render_preparation/VIDEO_PROFILE.json`的`canonical_reference_images`字段，覆盖前文这三类尺寸待定状态；已有参考视角数量及内容规则保持。下一项讨论保存格式，尚未开始渲染。

补充确认（2026-10-22，保存格式）：用户接受参考图PNG、主视频与动作参考视频MP4/H.264。先输出PNG序列后编码，CRF16作为小样起点，细节质量尚未实测。长期保留成品MP4及参考图片；临时序列仅在成功编码并确认视频可用后清理，另保留少量原帧对比样本。本次仅记录到`render_preparation/VIDEO_PROFILE.json`的`output_format`，不执行渲染或删除。每段体积和总存储量待小样测定，不能由CRF直接推算固定文件大小。

### 动作既有完成状态纠正（2026-10-22）

正式动作统一10秒已经完成，不是本轮新增待办。依据[场景与相机Technical §22](../unreal/SCENE_CAMERA_SEQUENCE.md#22-正式拍摄工作流整合2026-10-17实现完成用户视觉审查待确认)、`00_engine/assets/character_creator/production_motion_library_20261017_v1.json`及正式runtime active指针：10月17日已生成26动作×男女52份production10；后移除“四周张望”，现数据集25动作×男女50版。原始合同中的assets_pending是生成前快照，不能覆盖后续complete=true的正式运行目录。

本次只读核对规范化目录25动作全部clock为10秒／30fps／300输出帧，各有男女正式Production引用；最终训练5980、测试1223请求均绑定production10相机轨迹。正式动作已有逐动作截取、变速、端点停留及重复过渡，例如向前行走前6秒以0.6倍播放、挥手前5秒重复两次并作0.2秒衔接。新主视频与动作参考直接复用已烘焙production10资产和同一时间规则，不再重复施加这些源动作处理。

此前本分支“相位／速度／时长对齐待办”只应指新媒体生成器接入既有动作与相机时钟，不表示动作库尚未标准化；上一回复提出重新设计10秒规则撤回。当前VIDEO_PROFILE.json已删除含混的motion_clock_and_phase_alignment待办，明确保留新渲染接入。未操作UE或重验动画像素，未重写候选／旧审计证据。曝光继承、预热和本机纹理预算亦已有[原分支交接](../../../../../../00_engine/outputs/render_readiness_20261021_v1/HANDOFF.md)，后续应复用。

### 本地测试到服务器批渲计划（2026-10-22）

本Technical拥有`render_preparation/VIDEO_PROFILE.json`、`MACHINE_LOCAL.json`、`MACHINE_SERVER.template.json`及[RENDER_EXECUTION_PLAN.md](../../../../../../00_engine/outputs/dataset_return_control_20261022_v11/render_preparation/RENDER_EXECUTION_PLAN.md)。用户要求按已渲染样片规范参数、统一脚本本地测试后迁往Linux服务器。现已归并1×1采样、运动模糊关闭、1080P、CRF16及120／32预热、关卡曝光继承；机器纹理池和并行单列。本地精确版本5.8.1已读，服务器仅系列5.8有历史记录，用户确认Linux，当前补丁号尚未核实。优先同5.8.1，不假定旧引擎兼容新版资产。参考制作布置、最终实际画质／颜色转换参数、新执行器及本地／服务器测试尚未完成；旧资产、节点／链、历史回执保持。
## 2026-10-23：v11本地参数化渲染与迁移准备


本Technical拥有`00_engine/outputs/dataset_render_pilot_20261023_v1/`（本地pilot，非正式生产）及以下现用实现：

- `00_engine/scripts/dataset/render_plan_v11.py`：当前候选→7203主任务及12代表任务；不修改节点、边、链、参考需求。
- `00_engine/scripts/unreal/ue_dataset_render_v11.py`：正式40人槽位、production10、世界相机、关卡曝光、MRQ；只保存独立capture副本。睫毛从审查临时actor转为可保存的正式跟随actor，保证PIE仍存在。
- `00_engine/scripts/unreal/run_dataset_render_v11.py`：连接已有UE、串行队列、错误回执、续跑与分片。未知运行状态停止队列；不无限重试。
- `00_engine/scripts/dataset/encode_render_v11.py`：300帧→MP4、完整解码与输入／成片签名；接受UE实际不透明RGBA并丢弃alpha后进行BT.709有限范围转换。
- `00_engine/scripts/dataset/schedule_render_v11.py`：场景→点位→性别→人物→服装→发型→发色→动作→镜头→画幅；整场景分片。只排序，不改内容。
- `00_engine/scripts/unreal/dataset_runtime_paths_v11.py`：私有导入图内重定位Windows绝对路径及JSON读取值，不改原文件；`--portable-runtime`。Windows实机状态查询通过，Linux未测。
- `00_engine/scripts/unreal/ue_dataset_reference_pilot_v11.py`：6张独立参考原型；背景严格取对应主片sequence首帧相机后移除人物，身份／头发／单件另建中性布光场。
- `00_engine/scripts/dataset/build_render_transfer_manifest_v11.py`、`report_render_pilot_v11.py`：只读传输清单及耗时／媒体报告。

运行命令由[OPERATIONS](../../../../../../00_engine/outputs/dataset_render_pilot_20261023_v1/OPERATIONS.md)拥有；结果由[PILOT_REPORT](../../../../../../00_engine/outputs/dataset_render_pilot_20261023_v1/PILOT_REPORT.md)拥有；本地审查从[REVIEW](../../../../../../00_engine/outputs/dataset_render_pilot_20261023_v1/REVIEW.md)进入。运行目录内`run_reference_pilots.py`、`sync_pilot_docs.py`仅为本次有界执行辅助，生命周期prototype，不作通用全量入口。

实际输出与限制：12主片全解码通过，11条另有PIE可见网格／睫毛leader核对，首条未采集该快照；6参考图成功但布置未获用户确认。专用动作参考未拍。测试断开外部driver于192帧、UE继续到300，下次直接编码成功。代表图片观察不替代逐视频人工审查。

固定1×1采样、TSR、100%屏幕比例、关闭动态分辨率和运动模糊、120／32预热、画质组3、流送10240MiB本机预算、CRF16 medium。保留用户曝光和原相机；不强制全部纹理驻留。预算属于机器参数。量化设置与界限见VIDEO_PROFILE；相同设置不保证Linux逐像素相等。

排序将场景切换2181→20、人物947→332、服装4134→1174，代价是便宜属性切换增加。样片仍逐任务复制／加载capture地图，中位约9秒，尚未实现完全常驻世界的单次队列；编码4–6秒，当前串行，不声明已有编码流水重叠。冷启动／首次着色器未独立测量，阶段差异不能当严格单轴基准。

迁移保留完整Content与读取依赖，排除本地缓存和历史媒体。Linux UE5.8.1、插件、实际GPU与画面待现场核对；不把Windows路径适配通过写成服务器可运行。原始PNG当前保留供审查，正式批次确认媒体可用后按VIDEO_PROFILE策略清理，不在本次删除。仅运行本次直接相关测试，不开展全树重建／审计。
## 2026-10-23：纹理冷缓存修正与新媒体审查

本Technical拥有`00_engine/outputs/dataset_texture_quality_20261023_v1/`，包括`probe.py`、`sample_gpu.py`、`rerender_references.py`与`finalize_quality_docs.py`（本Run有界prototype辅助）；通用现用helper `00_engine/scripts/unreal/dataset_persistent_materials_v1.py`（v2）冻结临时MID到owned MIC。`ue_dataset_render_v11.py` VERSION2与reference VERSION5使用FULLY_LOAD；驱动以当前render_signature、成功MRQ回执来源及视频hash拒绝复用旧质量媒体。旧12技术证据保留，但画面质量拒绝。本节取代此前“继承纹理流送足够”的本地质量结论。

同1024、同相机、同黑发、两组均StreamOut4096的A/B实际驻留由64×64恢复脸/发2048与裙4096；六binding地图磁盘重载匹配。新12视频＋6参考图技术结果、精确回执和限制见[报告](../../../../../../00_engine/outputs/dataset_texture_quality_20261023_v1/REPORT.md)与[汇总](../../../../../../00_engine/outputs/dataset_texture_quality_20261023_v1/FINALIZATION.json)。仅20项相关测试由主会话报告通过；不宣称全库审计或服务器通过。没有修改候选/源场景；用户于2026-10-23确认修正后视频及图片清晰度足够；参考布置仍待确定，动作reference暂无专用样片。确认记录为该Run的USER_ACCEPTANCE.json。

## 2026-10-23 动作参考展示方案确认

用户确认：现有人物库固定一男一女，按动作性别使用；固定轮廓清楚的上衣、裤子、鞋子和短发；统一中性灰背景、简单地面、柔和照明。每个实际需要的动作与镜头组合独立拍摄，使用对应横竖屏，沿用production10的10秒/30fps、速度1、起始0，与主视频时钟一致。具体合法资产ID由实施时选择，专用动作参考小样尚未渲染。静态参考图布置是下一讨论项。该决定只确定参考展示，不改变数据图节点和编辑链。

## 2026-10-23 静态参考展示方案确认

用户确认沿用修正后样图的拍摄方式：身份、发型、服装使用中性灰背景与柔和照明，1024方图；身份为清楚完整的正面照片；每个发型由两名不同现有人物按既定视角和统一发色分别展示，引用时随机选一组；服装每件单拍且不含人体，换整套提供全部目标单件及鞋子；场景参考为对应镜头在目标场景中的首帧背景，不含人物，尺寸与对应视频一致。保持已有参考数量与视角规则，不改节点和链。至此展示设计已确认，下一步实施动作参考小样和全量参考执行入口，服务器试跑随后进行。
## 2026-10-23：全量参考绑定与11任务小样交接

本Technical拥有`00_engine/outputs/dataset_reference_production_20261023_v1/`。`00_engine/scripts/dataset/reference_plan_v11.py`产生2080 main-schema兼容carrier与2418原ID参考任务、hair完整组/步骤绑定和4motion pilot；`00_engine/scripts/unreal/ue_dataset_reference_v11.py`拥有canonical静态PNG与灰棚动作参考执行。`run_dataset_render_v11.py`分流PNG/MP4，校验当前worker/载体/成功MRQ provenance；`encode_render_v11.py`支持safe ref_*并对动作300帧全解码。Run内`select_static_pilot.py`及`finalize_reference_pilot.py`为本次有界prototype辅助，不是全量完成证明。

当前4motion＋7static按现行版本技术通过；全量2418入口ready，其余2407未由本脚本验证。展示方案及之前clear12/6已接受，本轮新增素材人工审查pending。最新男女selection直接读取motion_carriers，女Workout_BlueOutfit取代首轮宽裤；旧草稿媒体同目录替代，仅日志保留。鞋前/后相机抬高25°，shoe_framing_version=1只使鞋重渲染，其他6图可续用。主会话31项focused tests通过；不改动作烘焙或相机规则。正式绑定与精确回执见[执行结果](../../../../../../00_engine/outputs/dataset_reference_production_20261023_v1/EXECUTION_RESULT.json)／[报告](../../../../../../00_engine/outputs/dataset_reference_production_20261023_v1/REPORT.md)。本次仅校验这条任务链，未改候选、job文件或其他状态分支，未执行UE、全库审计、Linux或服务器验证。

## 2026-10-23：身份双白发、有效绑定与去衣物6图

本Technical拥有`00_engine/outputs/dataset_reference_portraits_20261023_v2/`及Run内`finalize_portraits.py`（有界prototype）。`reference_plan_v11.py --identity-portrait-variants`生成2458参考任务、2120载体，40逻辑身份池各两种silver_white发型，新增40参考ID；原reference_links保留来源，effective_reference_links记录每条身份步骤单图选择及selection_seed。非身份绑定、发型双载体组与809动作任务保持，不修改已采用图或主作业。

worker消费garments_present=false隐藏身份／发型衣物；身份framing_policy=tight_face_no_neck_or_shoulders采用固定脸部锚点，允许极细下缘保留下巴。signature的portrait_presentation_version与identity_framing_version使相关旧图失效，保留其他类别续跑兼容。两人4身份图＋同载体黑发前后2图当前签名、成功MRQ和完整PNG检查回执通过，16＋5＋5共26项直接测试通过；仅技术通过、人工待审，不保证其余38人构图。此前其他8项沿用用户接受，旧身份／发型和2418计数保留历史。驱动默认参考目录为v2；旧v1迁移清单不含v2，上传时用新--run-root重建，本轮延后大目录统计。证据与命令见[本轮报告](../../../../../../00_engine/outputs/dataset_reference_portraits_20261023_v2/REPORT.md)及[PLAN_README](../../../../../../00_engine/outputs/dataset_reference_portraits_20261023_v2/PLAN_README.md)。本次只同步当前绑定、展示和证据指针，不运行全树审计、catalog重建、UE或服务器验证。

## 2026-10-23：男女统一发型相机与灰衣物v3

本Technical拥有`00_engine/outputs/dataset_reference_hair_framing_20261023_v3/`及`finalize_hair_framing.py`（有界prototype，复用v2收尾脚本的纯签名／读写helper）。`reference_plan_v11.py --identity-portrait-variants --shared-hair-framing --hair-carrier-clothing <config>`保持2458任务及80身份／809动作，112发型任务设置framing_policy=shared_head_shoulders、garments_present=true、neutral_garment_color=true；carrier服装、hair_id与appearance/hash一致。

worker固定男女头部相对距离110cm、中心Z+3cm、FOV28°、1024方图，展示大部分发型，最长可裁切；仅owned stage的衣物材质改灰。shared_hair_framing_version=1使相关旧图失效。4图当前签名／成功MRQ／PNG完整检查回执通过，16＋6＋5共27直接测试通过，人工待审；不保证112图全验。身份v2规则及其他8样片接受保持，原图、链接和主任务不改。当前[报告](../../../../../../00_engine/outputs/dataset_reference_hair_framing_20261023_v3/REPORT.md)与[命令](../../../../../../00_engine/outputs/dataset_reference_hair_framing_20261023_v3/PLAN_README.md)替代旧发型入口，旧报告保留历史。上传时以v3重建迁移清单，本轮不重复大目录扫描／catalog或全库审计。

## 2026-10-23：发型自适应完整取景与灰衣物v4

本Technical拥有`00_engine/outputs/dataset_reference_hair_adaptive_20261023_v4/`及`finalize_hair_adaptive.py`（有界prototype，复用v2收尾脚本的纯签名／读写helper）。`reference_plan_v11.py --identity-portrait-variants --adaptive-hair-framing --hair-carrier-clothing <config>`保持2458任务及80身份／809动作，112发型任务设置framing_policy=adaptive_complete_hair、garments_present=true、neutral_garment_color=true；carrier服装、hair_id与appearance/hash一致。

worker按实际头发边界＋紧凑头部代理计算中心和距离，短发近拍、长发后退完整展示，FOV28°、边距1.12、1024方图，无100cm距离下限；仅owned stage的衣物材质改灰。adaptive_hair_framing_version=1使相关旧图失效。4图当前签名／成功MRQ／PNG完整检查回执通过，16＋6＋5＋1共28直接测试通过，用户于2026-10-23确认构图与4张样图；其余发型仍待生成。身份v2规则及其他8样片接受保持，原图、链接和主任务不改。当前[报告](../../../../../../00_engine/outputs/dataset_reference_hair_adaptive_20261023_v4/REPORT.md)与[命令](../../../../../../00_engine/outputs/dataset_reference_hair_adaptive_20261023_v4/PLAN_README.md)替代旧发型入口，旧报告保留历史。上传时以v4重建迁移清单，本轮不重复大目录扫描／catalog或全库审计。
## 2026-10-23：服务器渲染配置包v1

本Technical拥有 `00_engine/outputs/dataset_server_bundle_20261023_v1/`，以及production脚本 `00_engine/scripts/dataset/build_render_bundle_v11.py`、`00_engine/scripts/dataset/run_render_bundle_v11.py` 和对应定向测试。构建器在新目录冻结已确认VIDEO_PROFILE，重新生成主任务并逐项确认7203条定义不变；参考2458条、载体、effective_reference_links等保留v4原字节。队列按场景等排序，不改变节点与链。

入口 `00_engine/outputs/dataset_server_bundle_20261023_v1/README.md`；RENDER_CONFIG.json列出8个队列，config/CONTENT_CONFIG.json列内容与点位，config/VIDEO_PROFILE.json保存参数快照，MACHINE_SERVER.template.json分离目标机器路径与显存预算。启动器默认只预览；--execute连接已有UE，显式携带--portable-runtime和--pool-mb，参考输出按原字节播种carrier_jobs.json。续跑与错误处理复用现有驱动，无新增自动重试。画质JSON是与worker配套的参数快照，修改它本身不会覆盖worker常量。

本地7项启动器测试及8队列离线检查通过，LOCAL_VALIDATION.json记录具体命令。主任务排序将场景切换2181降到20，人物947降到332；这是配置切换次数，不是服务器耗时测量。新包仅整理配置与上传清单，不复制工程、不上传、不渲染。源关卡曝光仍随地图二进制上传；Linux5.8.1实际插件/RHI/GPU与小样待验证。R17继续进行，不将配置包就绪视作生产完成。

同范围交付归档 `00_engine/outputs/dataset_server_bundle_20261023_v1_configs.zip` 为该配置目录的可重建ZIP副本（Python zipfile，DEFLATE，保留workspace相对目录，排除transfer_build.log）；不含UE资产和完整运行依赖，上传仍按TRANSFER_PLAN执行。

## 2026-10-23：最终流程清理、目录整理与渲染入口恢复

本Technical拥有本次最终流程依赖、产物位置、运行入口修复和配置包刷新；Run为 [final_pipeline_cleanup_20261023_v1](../../../../../../00_engine/outputs/final_pipeline_cleanup_20261023_v1/)，保留/删除边界见[输出盘点与保留](../output/INVENTORY_AND_RETENTION.md)。文件及已审查UE包清理已经执行，最终主片10秒渲染小样已成功完成；配置包刷新已完成，见本Run的BUNDLE_REFRESH_RECEIPT.json。最终汇总入口为本Run [REPORT.md（最终汇总）](../../../../../../00_engine/outputs/final_pipeline_cleanup_20261023_v1/REPORT.md)；各项事实优先读取其原始执行/验证回执，不能把一次清理写成全库已无旧内容或正式渲染完成。

文件执行回执approved_file_cleanup_result.json记录删除28,287文件、100,478,999,260字节、0失败，1项原已不存在，1条目录联接别名路径跳过。UE离线执行删除10,631文件、32,175,664,623字节、0失败；另有原生接口已移除的683个科幻资产。physical_preservation_check.json核对全部11,314候选包均不存在、24,403保留包均存在，28份保留MP4哈希不变。文件字节不是磁盘净空闲增长；不重复叠加候选或原生/离线重试。

现用配置包、v11节点/边/会话/渲染请求、effective参考绑定、点位与排除组合、最终40人可编辑CC项目、现用衣服/头发/角色导出源、已接受媒体和frame_0000保留。dataset_trial_build_20261021_v1/catalog.json仍承担任务重建的目录与排除来源；night交接中AF_001、AM_001审计仍读取pair导入目录。兼容快照和场景迁移证明不能按旧日期或history/before命名删除。另发现的6.834 GiB旧皮肤比较PNG未纳入此次约94 GiB确认范围，暂保留；来源不确定的CC文件同样保留，详见remaining_large_scoped_review.json。

新主片地图/序列/持久材质写入 /Game/DataMake/Render/Main，参考写入 /Game/DataMake/Render/References；启动地图为 /Game/DataMake/Render/Workspace/L_RenderWorkspace。冻结任务中的源UE路径继续保留。Content Browser根集合DM_Final_Render已建立：40人物身体、300衣服/鞋网格、117发型部件、52男女动作资产、21场景和1工作区地图。这些是集合成员数，不是独立发型或语义动作数。当前使用LOCAL集合；共享集合要求source control，不能标作已建立共享集合。项目实物位于Saved/Collections，config/UE_LIBRARY.json与7个collection文件已打包进入服务器配置目录，供迁移恢复浏览分类。

清理后发布asset_inventory_formal_runtime_catalog_20261023_cleanup_v1.json，退役520条旧资产pin，保留1,219条当前pin；旧catalog原字节不变，证据为runtime_catalog_cleanup_publication.json。asset_inventory_formal_runtime_v1.py对wardrobe_component_corrections的原publication绑定，仅经校验存档及等价catalogs内容后兼容新目录，不无条件放松摘要。主片/动作参考通过ue_dataset_render_v11.spawn_slot_actor直接实例化现用固定槽位Blueprint，解除对已删除旧试验地图的依赖。dataset_persistent_materials_v1允许owned Render根；参考dirty guard和renderer接受其自己的ROOT。动作帧、颜色、相机和曝光规则没有因此重新设计。

主片10秒小样已成功：main_smoke/driver_summary.json及jobs/train_node_000000/media_receipt.json记录300帧、1920×1080、30fps，成片27,456,881字节；复用已准备结果，渲染26.56秒、编码12.73秒、合计40.64秒，首帧已实际查看。reference_smoke中的男性发型1024×1024 PNG也已实际渲染、校验并查看成功，1,274,566字节。targeted_tests.log记录14项衣柜修正绑定测试通过，render_tests.log记录13项渲染/参考/配置包定向测试通过。证据位于[主片执行回执](../../../../../../00_engine/outputs/final_pipeline_cleanup_20261023_v1/main_smoke/driver_summary.json)及[媒体回执](../../../../../../00_engine/outputs/final_pipeline_cleanup_20261023_v1/main_smoke/jobs/train_node_000000/media_receipt.json)。这是清理后代表小样通过，不声明全量7203主片、全库或Linux验证通过；配置包刷新已完成，见本Run的BUNDLE_REFRESH_RECEIPT.json。

本Run的refresh_final_bundle.py及[BUNDLE_REFRESH_PROCEDURE.md](../../../../../../00_engine/outputs/final_pipeline_cleanup_20261023_v1/BUNDLE_REFRESH_PROCEDURE.md)为本次有界utility：默认仅检查现用catalog/contract和任务引用；显式--refresh更新SOURCE_SNAPSHOT、PACKAGE_FILES、TRANSFER_PLAN与配置ZIP。须在最终小样、保存和文档收尾后按实际结果刷新；本节不替代刷新回执。已删PNG/CC几何快照不能按旧检查点继续编码/恢复，应使用保留成品或现用源重新生成；JSON保留不表示旧二进制仍存在。

本次最终刷新回执：`final_pipeline_cleanup_20261023_v1/BUNDLE_REFRESH_RECEIPT.json`。TRANSFER_PLAN包含58,207个文件、77,117,337,301字节；配置ZIP为15,870,744字节。现用来源摘要、PACKAGE_FILES及上传清单已同步，Linux渲染仍待服务器验证。
