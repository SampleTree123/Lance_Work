# Lance_Work / DataMake

用于构建可追溯的 Unreal Engine 多轮视频编辑数据集。系统把角色与场景资产、确定性配置图、原子编辑链、文本指令和节点媒体连接为可复现的生产流水线。第一批数据已通过 WF-90 并发布；下游 Lance 已接入 UE＋CoinVE 混合数据、双分支 LoRA 与两种历史策略。2026-10-11 已整理架构，并完成可选单张 ViT 参考图的代码与工程验证；参考图训练数据及质量验收仍待后续，实时状态由项目 Status 维护。

新会话先读 [`HANDOFF.md`](./HANDOFF.md)。角色工厂与数据生产的唯一主入口是 [`full_process/README.md`](./20_planning/data_design/character_creator/full_process/README.md)，当前事实与唯一下一步见 [`PROJECT_STATUS.md`](./20_planning/data_design/character_creator/full_process/project_management/status/PROJECT_STATUS.md)。

## 数据模型

一个节点由全部受控因素唯一确定：

```text
C = {identity, body_fit, outfit, action, expression, scene, camera, lighting}
render(C) -> media(node_id)
```

一条原子边只改变一个允许编辑轴。多轮样本沿图中的连续原子边构成，上一轮的真实输出节点直接成为下一轮输入，不重新渲染伪造端点。

配置图、兼容域、链策略与文本 Schema 分别由：

- [`CONFIG_GRAPH_SCHEMA_V1.md`](./20_planning/data_design/schema/CONFIG_GRAPH_SCHEMA_V1.md)
- [`MULTI_ROUND_CHAIN_SAMPLING_V1.md`](./20_planning/data_design/sampling/MULTI_ROUND_CHAIN_SAMPLING_V1.md)
- [`MULTI_ROUND_VIDEO_EDIT_TEXT_SCHEMA_V1.md`](./20_planning/data_design/schema/MULTI_ROUND_VIDEO_EDIT_TEXT_SCHEMA_V1.md)

定义。当前批次的精确数量和冻结资产不在本页重复维护。

## 执行入口

| 目标 | 入口 |
| --- | --- |
| 理解完整生产流程 | [`full_process/README.md`](./20_planning/data_design/character_creator/full_process/README.md) |
| 查看当前状态、计划和下一步 | [`PROJECT_STATUS.md`](./20_planning/data_design/character_creator/full_process/project_management/status/PROJECT_STATUS.md) |
| 定位十个生产阶段 | [`workflow/README.md`](./20_planning/data_design/character_creator/full_process/workflow/README.md) |
| 查找准确脚本、命令和输出 | [`technical/README.md`](./20_planning/data_design/character_creator/full_process/technical/README.md) |
| 查看代码目录 | [`00_engine/scripts/README.md`](./00_engine/scripts/README.md) |
| 两端文档同步与UE执行接手 | [同步状态](./20_planning/data_design/character_creator/full_process/project_management/status/SERVER_SYNC_STATUS.md) · [同步说明](./20_planning/data_design/character_creator/full_process/technical/rendering_release/DOCUMENT_SYNC.md) |
| 服务器预检 | [`FIRST_BATCH_SERVER_PREFLIGHT.sh`](./20_planning/implementation/FIRST_BATCH_SERVER_PREFLIGHT.sh) |
| 查看 Lance 多轮训练接入 | [`training_integration.md`](./10_research/model_experiments/lance/training_integration.md) |

不要从旧计划、历史截图或名字相近的脚本推断当前生产方式。先由 Workflow 定位 Technical，再执行 Technical 声明的代码和 Registry。

## 决策日志

- 2026-10-23：用户确认通过公开GitHub同步服务器差异；16份UE引擎源码补丁及根目录临时文件保留服务器并忽略，独立robotdata仓库已由用户删除。已通过登录节点HTTPS认证推送内容提交e0dd61c至main；遗留LFS钩子已备份停用，本地Windows合并待完成。见[上传审查](20_planning/data_design/character_creator/full_process/project_management/status/GITHUB_SYNC_REVIEW.md)与[认证和同步](20_planning/data_design/character_creator/full_process/technical/rendering_release/DOCUMENT_SYNC.md)。

- 2026-10-23讨论记录：按阶段/任务定义ViT和VAE规格，评估生成source/history统一低规格、理解标准ViT和独立参考VAE预算。已复核张量形状及长度算例，参数未冻结，见[规格分析](10_research/model_experiments/lance/reports/datamake_stage_specific_media_specs_20261023.md)。

- 2026-10-23：后续将各类ViT与参考视频VAE的采样、空间尺寸和token预算合并讨论，形成分角色的统一媒体预处理方案；暂不固定历史优先抽帧。首选压缩历史及暂缓消融的既有决定不变，见[架构方案](10_research/model_experiments/lance/reports/datamake_vae_references_branch_plan_20261022.md)。

- 2026-10-23：Lance生成阶段首选压缩历史ViT；完整保留/压缩/删除ViT及保留/移除历史prompt登记为未来独立消融，目前不执行。压缩参数未定，见[方案第5节](10_research/model_experiments/lance/reports/datamake_vae_references_branch_plan_20261022.md)。

- 2026-10-23：Lance下一版生成只输入当前轮参考；旧参考保存追溯、不重复注入，避免同属性不同目标竞争。历史视频ViT策略另议，当前代码未改，见[架构方案](10_research/model_experiments/lance/reports/datamake_vae_references_branch_plan_20261022.md)。

- 2026-10-22：确定下一版Lance按属性提供多图/动作参考视频，并以VAE作为生成参考；理解tool_call先选历史起点，生成取祖先路径。历史压缩/删除与具体预算待讨论，尚未实施，见[ADR-0020](20_planning/data_design/character_creator/full_process/project_management/decisions/ADR-0020-VAE-MULTI-REFERENCE-BRANCH-DIRECTION.md)。

- 2026-10-22：Lance源码改为固定最新官方提交＋单一当前补丁/源码锁；保留现行PEFT/DDP、整链、数据与推理能力，历史训练器/补丁分区，旧clone在验证与归档后删除。模型、媒体和已有实验结果不随源码清理。见[迁移记录](10_research/model_experiments/lance/reports/datamake_source_migration_20261022.md)。

| 日期 | 决策 | 详细入口 |
| --- | --- | --- |
| 2026-10-18 | 参考图等待合适数据、暂不继续测试；讨论显式历史起点选择，普通prompt默认-1、生成仅用祖先路径、保存真实父节点、理解与生成分别训练、推理非法输出回退留痕；分支尚未实现。 | [ADR-0019](./20_planning/data_design/character_creator/full_process/project_management/decisions/ADR-0019-EXPLICIT-HISTORY-SOURCE-ROUTING.md)；[架构讨论总记录](./10_research/model_experiments/lance/reports/datamake_architecture_decisions_20261018.md) |
| 2026-10-11 | 保留直链，先实现每轮可选单张 ViT 参考图与纯文本编辑共存；源/目标 VAE 和 loss 角色不变。分支编辑及参考 VAE 暂缓，不自动制作数据或提交正式训练。 | [ADR-0018](./20_planning/data_design/character_creator/full_process/project_management/decisions/ADR-0018-OPTIONAL-SINGLE-VIT-REFERENCE.md)；[实现与验证](./10_research/model_experiments/lance/reports/datamake_optional_reference_image_20261011.md) |
| 2026-10-11 | 按当前代码和运行证据同步项目状态，整理模型输入输出、注意力、数据、loss、历史策略与优化边界；本次不改变模型或训练配置，不自动续训。 | [架构说明](./10_research/model_experiments/lance/reports/datamake_current_architecture_20261011.md)；[进度](./10_research/model_experiments/lance/reports/datamake_progress_20261011.md) |
| 2026-09-12 | 用户要求暂停prefix pred_x0并集中处理整链：当前监督forward复用detached pred_x0，整链处于同一更新，保留R5×3和global32；全局window token归约，额外轮次权重暂不增加。独立v2单卡验证通过，八卡Gate待提交。 | [整链实现与验证](./10_research/model_experiments/lance/reports/datamake_chain_pred_x0_ddp8_20260912.md) |
| 2026-09-12 | 新八卡混合LoRA沿用GT对照的prefix采样及全部超参数，只用在线pred_x0替换先前轮次历史；生成与解码no_grad并detach，不跨轮反传，保持当前目标GT监督。 | [配置、验证与启动](./10_research/model_experiments/lance/reports/datamake_pred_x0_ddp8_training_20260912.md) |
| 2026-09-11 | 后续推理展示新的完整验证链：真值回填与自回填分成两部分，每部分仅推理/真值两行，逐轮上下对应；CoinVE真实单轮样例在独立区域直接对照模型输出与真值。 | [完整链推理准备](./10_research/model_experiments/lance/reports/datamake_complete_chain_review_preparation_20260911.md) |
| 2026-09-11 | 新混合训练采用8卡双分支LoRA，关闭区域loss加权，每50步保存最近4份；未指定项沿用原模板，累计改4以保持global batch32。 | [八卡配置与验证](./10_research/model_experiments/lance/reports/datamake_coinve_ddp8_training_config_20260911.md) |
| 2026-09-11 | 用户同意暂缓CoinVE内容时序筛查、复合编辑筛选和同源长视频重划分，先生成UE＋CoinVE引用式混合索引并接入共同5秒窗口；保留合成R5×3及两套原split，不复制视频。 | [混合数据组织与验证](./10_research/model_experiments/lance/reports/datamake_coinve_mixed_dataset_20260911.md) |
| 2026-09-11 | 用户要求仅保留Stage5 B训练结果，并将后续训练主配置精简为Stage5 B与理解＋生成LoRA、每100步保存的优化DDP模板；旧Stage5 A/Stage6恢复点和迁移目录已删除，所需配方/冻结合同依赖保留。新混合数据另行接入验证。 | [训练模板与接入位置](./10_research/model_experiments/lance/reports/lance_training_templates_20260911.md)；[结果清理](./10_research/model_experiments/lance/reports/lance_keep_stage5b_cleanup_20260911.md) |
| 2026-09-10 | 用户要求结束优化后的两组训练，完整保存987/893步后正常退出，不自动续训 | [结束记录](./10_research/model_experiments/lance/reports/datamake_padding_optimization_20260910.md) |
| 2026-09-10 | 保留FlexAttention，完成padding缩减、数值/性能与两臂完整恢复验收，并提交Stage6下一轮续训 | [padding优化与恢复](./10_research/model_experiments/lance/reports/datamake_padding_optimization_20260910.md) |
| 2026-09-10 | 用户授权优化官方位置编码函数的求和：张量归约与计数复用，保留位置更新逻辑；当前单卡等价与速度验证不替代四卡验收 | [优化验证](./10_research/model_experiments/lance/reports/datamake_position_sum_optimization_20260910.md) |
| 2026-09-10 | 将已测VAE缓存复用接入官方函数可选参数及DDP配置，提供两臂独立高显存候选，原正式训练保持暂停 | [缓存策略接入](./10_research/model_experiments/lance/reports/datamake_vae_cache_integration_20260910.md) |
| 2026-09-10 | H200更高显存短测完成：选择性检查点配合VAE缓存复用获得收益，作为下一实现候选；保留batch4编译边界，正式训练继续暂停 | [高显存短测](./10_research/model_experiments/lance/reports/datamake_high_memory_sweep_20260910.md) |
| 2026-09-10 | 已完成四卡基线、少量关闭检查点、全检查点下扩大batch的独立短测；未获得明显提速，新DDP候选默认保留全检查点/batch1，packed保留数值限制，正式两臂继续暂停 | [三步验证](./10_research/model_experiments/lance/reports/datamake_four_gpu_optimization_20260910.md) |
| 2026-09-09 | 用户暂停Stage6两臂126188/126189；保存900/825正常退出，授权已有单H200做新旧LoRA短速度对照，不自动续训 | [暂停与短测](./10_research/model_experiments/lance/reports/datamake_lora_short_speed_20260909.md) |
| 2026-09-09 | LoRA 正确性审查后仅修复保存中断重试与 Gate 实际参数更新检查；Adam 语义完整性强化和逐 parquet 启动核验暂缓，四卡验收仍待完成 | [修复记录](./10_research/model_experiments/lance/reports/datamake_ddp_peft_optimization_20260909.md#保存重试与实际更新检查修复) |
| 2026-09-09 | 用户授权优化 Stage6 LoRA：官方 PEFT + DDP、累计同步、可选激活重算；独立完整状态迁移与验证入口，保留原 FSDP 作业，四卡性能/恢复待验证 | [优化实现](./10_research/model_experiments/lance/reports/datamake_ddp_peft_optimization_20260909.md) |
| 2026-09-08 | 用户要求停止Stage6现有训练，两臂固定从各自restart1第400步完整checkpoint恢复；保持配置、3000步总预算、本地/W&B身份及历史日志，由用户提交，不从零重启。 | [Stage6恢复记录](./10_research/model_experiments/lance/reports/datamake_stage6_checkpoint_rescue_20260907.md) |
| 2026-09-08 | Stage6 restart1两臂按用户要求改为每100个optimizer更新保存、最近4份完整checkpoint；最终保存纳入保留4份。仅增加保留数，不改训练语义、超参、运行身份或启动命令；启动前队列与输出检查确认两臂未运行。 | [Stage6保留策略与实测大小](./10_research/model_experiments/lance/reports/datamake_stage6_stage2_lora_preparation_20260907.md) |
| 2026-09-05 | 用户确认当前官方基座 v3 继续训练，同时准备 Stage 2 基座 + fresh generation LoRA 的独立对照；保持数据顺序、单步历史、loss、LR与1800-step horizon不变。对照使用独立Run/W&B，由用户手动提交；比较必须包含Stage 2未加新adapter的起点，不将基座既往训练成本忽略为等预算。 | [基座对照准备](./10_research/model_experiments/lance/reports/datamake_stage2base_lora_preparation_20260905.md)；[实验登记](./10_research/model_experiments/lance/reports/datamake_lora_ablation_registry_20260904.md) |
| 2026-09-07 | 经完整替代核验后按用户确认删除两份旧训练索引，保留三份现行数据。准备Stage2配方的r64 LoRA两臂，只比较理解侧adapter是否冻结；共同基座随后确认为官方预训练模型，并统一累计8、LR3e-4→3e-5、3000 optimizer更新；随后两臂经用户提交并通过各自四卡恢复检查开始训练；发现600步首存超出18h可达范围，抢救失败后按用户决定取消旧作业。100步保存/边界保存退出及restart1独立目录和W&B身份已准备，由用户从头提交，未自动启动。 | [Stage6实现](./10_research/model_experiments/lance/reports/datamake_stage6_stage2_lora_preparation_20260907.md)；[抢救记录](./10_research/model_experiments/lance/reports/datamake_stage6_checkpoint_rescue_20260907.md)；[数据导航](./10_research/model_experiments/lance/outputs/training_data/README.md) |
| 2026-09-06 | 用户决定删除 tiny 实验专用配置、报告与产物以及 Stage1 训练结果；保留 Stage2 base、A/B 检查点及共享实现。A 仍依赖官方 Lance 基座，不能随 Stage1 结果删除。按当前入口/历史配方/审计证据整理文件；后续又明确删除旧inputs、生成配置和空training_eval。training_data只做用途/替代核验，待确认后再清理。训练仍暂停，不自动续跑。 | [清理记录](./10_research/model_experiments/lance/reports/datamake_lance_storage_cleanup_20260906.md)；[Lance 入口](./10_research/model_experiments/lance/README.md) |
| 2026-09-04 | 为大幅缩短一行一链 LoRA 训练，用户确认只把中间 30-step rollout 替换为同一次 flow-training forward 的 `pred_x0=z_t-t*pred_velocity`，detach/VAE decode 后继续作为下一轮全部 ViT history 与最新 VAE source；其余 loss、LoRA、accumulation、LR、dropout、1,800-step 和 checkpoint-v5 配置不变。Jobs `122843/122844/122845` 通过四卡 exact-resume，前三步平均提速 1.91×；这是 noisy-GT proxy，不等价于完整 rollout。用户随后授权正式 v3，Job `122959` 已提交至 `testqueue`。 | [`Stage 5 实现与 Smoke`](./10_research/model_experiments/lance/reports/datamake_stage5_one_step_x0_history_20260904.md)；[`恢复审计`](./10_research/model_experiments/lance/reports/datamake_stage5_one_step_x0_resume_smoke_audit_20260904.json) |
| 2026-09-04 | Stage 4 checkpoint 纠错：Job `122549` 的 step50 adapter 只含 2/256 个非零 `lora_B`，故用户停止任务且旧 checkpoint 禁止恢复。checkpoint v5 通过 optimizer canonical-FQN/shard 映射保存 live LoRA，并正确跳过 `use_orig_params=True` 的空 local shard；Jobs `122758/122827/122836` 的连续 step3 与 step2-save/resume-step3 对照中，512 adapter、2,048 optimizer、8 RNG tensor 全部 bitwise 一致，256/256 个 `lora_B` 非零。正式 v2 仍为 fail-closed，等待用户重新授权。 | [`Stage 4 实现`](./10_research/model_experiments/lance/reports/datamake_stage4_online_rollout_lora_implementation_20260904.md)；[`恢复审计`](./10_research/model_experiments/lance/reports/datamake_stage4_lora_resume_smoke_audit_20260904.json) |
| 2026-09-03 | 第二阶段 Job `120425` 完成 3,669 steps；训练/检查点健康，teacher-forced 身份和换装明显改善，但真正多轮自回灌仍累积构图漂移。用户要求先实现并审阅 r64 生成分支 LoRA、LR `1e-4` 与 GT/model-rollout history 对照，本轮不得启动训练。 | [`stage2 结果`](./10_research/model_experiments/lance/reports/datamake_dialogue_stage2_results_20260903.md)；`stage3 设计`（历史文件已于2026-09-11清理） |
| 2026-09-01 | 当前视觉质量未达预期；用户决定跳过 100～300-step A/B，第二阶段采用 R5×3、三个 condition dropout=0、训练期 VAE latent soft region weighting、LR `1e-5` 和最近一个 checkpoint 保留。2-step 技术 smoke 通过后直接训练一个完整 Epoch；smoke 不构成质量有效性证据。 | [`第二阶段准备报告`](./10_research/model_experiments/lance/reports/datamake_dialogue_stage2_preparation_20260901.md) |
| 2026-08-31 | 用户确认 Lance 四卡正式 profile；首份 `.sbatch` 使用 18 小时 `testqueue`、4×H200，并将 stdout/stderr 分别写入 Lance `outputs/slurm_logs/`。任务文件通过提交前 Gate 后由用户手动提交。 | [`training_integration.md`](./10_research/model_experiments/lance/training_integration.md) |
| 2026-08-31 | Lance 首轮 seed `2026` 的链级随机 split 冻结为 3,600/200/200 chains，对应 13,483/754/763 `dialogue` prefixes；同链前缀不得跨集合，四卡单 Epoch 为 3,371 optimization steps。 | [`training_integration.md`](./10_research/model_experiments/lance/training_integration.md) |
| 2026-08-31 | Lance 正式训练使用 W&B online 实时监控标量与系统指标，以稳定 Run ID 支持 checkpoint resume；默认不上传训练视频、checkpoint、源码或完整控制台日志。 | [`training_integration.md`](./10_research/model_experiments/lance/training_integration.md#71-wb-实时监控契约) |
| 2026-08-31 | 第一批 `dataset_v1` 在 `JDS9B74/job118880` 通过候选态与发布态独立全包验证，Manifest 晋升为 `released`，`GATE-90` 关闭；下一计划转为 Lance `dialogue` 3,600/200/200 链级随机划分和四卡全参数单 Epoch 训练准备。 | [`WF-90 状态`](./20_planning/data_design/character_creator/full_process/project_management/status/workflows/WF-90.md) |
| 2026-08-31 | Lance 当时冻结第一、第二阶段为全参数路线，不允许以 LoRA 或冻结 UND 大部分参数替代既定 Gate；该历史决定不约束 2026-09-03 之后新建的独立 LoRA 对照。 | [`training_integration.md`](./10_research/model_experiments/lance/training_integration.md) |
| 2026-08-29 | Lance 首轮微调只使用 `dialogue` 多轮链前缀；`standalone` 暂缓并保留为后续独立消融基线，首轮不得混采两个视图。 | [`training_integration.md`](./10_research/model_experiments/lance/training_integration.md#31-训练视图优先级) |

## 仓库结构

```text
Lance_Work/
├── .codex/         # 可迁移的项目 Skill 权威源
├── 00_engine/      # CC/UE/数据图实现、Bridge、审查工具和运行输出
├── 10_research/    # 外部模型与工具研究，不阻塞当前数据生产
├── 20_planning/    # 数据契约、完整生产文档、计划、状态与历史
├── README.md       # GitHub 总入口
├── HANDOFF.md      # 新会话接手入口
└── AGENTS.md       # 协作和仓库维护规则
```

## 资产与输出边界

Git 保存代码、Markdown、JSON、Manifest、哈希和适合版本控制的证据。CC 二进制资产、UE `Content/`、`.uasset/.umap`、DDC 和批量媒体通过独立资产包或本地/服务器工作层管理，但必须由 Registry、Technical 文档和 Batch Manifest 追溯。

`00_engine/outputs/` 不是天然可删除的缓存。保留策略与当前盘点见：

```text
00_engine/outputs/RETENTION_POLICY.json
00_engine/outputs/OUTPUT_INVENTORY.json
```

## 快速校验

```powershell
python 00_engine/scripts/documentation/build_script_lifecycle_catalog.py
python 00_engine/scripts/documentation/build_output_inventory.py
python 00_engine/scripts/documentation/check_character_factory_docs.py --json
python -m pytest 00_engine/scripts/documentation/tests 00_engine/scripts/dataset/tests 00_engine/scripts/unreal/tests -q
```
