# WF-09 渲染与数据集交付包

> 文档角色：`workflow_runbook`
> 状态：`in_progress`
> 适用阶段：`WF-09`
> 权威范围：短视频、配置图、编辑链、sidecar、哈希和证据包的最终交付契约；当前第一批受限范围
> 上级入口：[`README.md`](./README.md)
> 上游：[`WF-08-SCENE-CAMERA-SEQUENCE.md`](./WF-08-SCENE-CAMERA-SEQUENCE.md)
> 下游：无，生产主线终点
> 最近核验：2026-08-24

## 1. 目的与使用时机

把通过场景门禁的 Sequence 渲染为可训练、可复查、可追溯的数据包，并验证媒体、GT、配置和证据彼此一致。

## 2. 当前范围与非目标

本阶段已有可断点续跑的本地 32-Look 代表矩阵执行器，以及符合当前契约的正式 640 节点配置图、8,320 条同域原子边、4,000 条编辑链、640 个 render job 和 15,000 回合双语 prompt；尚无正式 640 节点媒体执行器。第一批冻结目标为服务器完整渲染 640 个 Happy-only 唯一节点；节点只渲染一次，链和文本回合只引用媒体。正式节点使用 `near/far/high/side` 四台相机，并分为 female/male 两个各 320 节点的兼容域。历史本地 32 例覆盖全部 Look、10 个生产动作、4 台相机和 3 种表情，用于验证装配与渲染链路，不等于正式 640 节点内容契约。完整范围见 [Sprint](../planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md)，结构图、采样和模型文本分别见 [Config Graph Schema V1](../../../schema/CONFIG_GRAPH_SCHEMA_V1.md)、[Sampling V1](../../../sampling/MULTI_ROUND_CHAIN_SAMPLING_V1.md) 与 [Text Schema V1](../../../schema/MULTI_ROUND_VIDEO_EDIT_TEXT_SCHEMA_V1.md)。

## 3. 进入条件

- `GATE-08 SCENE_READY` 通过。
- Sequence、角色、场景、相机、动画、随机种子和资产版本全部冻结。
- 输出根和唯一 dataset/run ID 已确定，旧结果不会被覆盖。

## 4. 输入与输出

第一批输入：通过 Gate 的单节点 Sequence 模板、`source_manifest.json`、`assets.json`、`compatibility_domains.json`、`nodes.jsonl`、`edges.jsonl`、`chains.jsonl`、`render_jobs.jsonl`、`prompt_catalog_first_batch_v1.json` 和 render profile。本地代表矩阵由 `first_batch_local_render_matrix_20260824_v1.json` 冻结 32 个历史样例；每例输出 150 张无损 PNG 主帧、H.264 MP4、帧数/尺寸报告、视频 SHA-256 和自动化契约。正式输出还必须包括 `turns.jsonl`、`dialogs.jsonl`、`prompt_manifest.json`、节点 sidecar、`media_manifest.jsonl`、失败/重试记录、软件与资产版本和验收报告。

## 5. 执行环境

本地 Pilot 使用已打开的 UE 5.8 Editor、Remote Execution 和 MRQ PIE executor，`offscreen=false`。服务器阶段才切换到命令行离屏运行，并必须先完成 10 节点基准；同步、预检、降级和重试边界见 [Server Runbook](../../../../implementation/FIRST_BATCH_SERVER_RUNBOOK.md)。

## 6. 执行步骤

当前本地单节点入口：

```powershell
python "D:\UE\Lance_Work\00_engine\scripts\unreal\run_first_batch_render_profile.py"
python "D:\UE\Lance_Work\00_engine\scripts\unreal\run_first_batch_local_sample_render.py"
```

第一条命令创建或审计 MRQ Preset，第二条提交 0–150 帧、等待完成、校验 150 张 PNG，并编码 MP4。当前默认 Preset 为 `/Game/DataMake/Render/Presets/MRQ_DM_FirstBatch_1440p30_PNG_v001`：`2560×1440`、30 fps、5 秒。`MRQ_DM_FirstBatch_720p30_PNG_v001` 仅作为低显存回退，不是默认生产清晰度。

32-Look 本地代表矩阵的一键入口：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "D:\UE\Lance_Work\00_engine\scripts\unreal\run_first_batch_32_video_matrix.ps1"
```

入口依次完成：复制/确认 DataMake staging map、替换当前 Look、按 JSON 构建 5 秒 Sequence、校验角色原生绑定和四段动画 Section、提交 MRQ、检查媒体并更新 `matrix_state.json`。默认输出为 `OUTPUT_ROOT\unreal_render\first_batch_32look_matrix_20260824_v002`。重复运行会只跳过自动化契约与当前样例完全匹配且媒体有效的案例；可把 `--start-index`、`--limit`、`--prepare-only` 和 `--dry-run` 直接追加到 PowerShell 命令末尾控制范围。

批处理在提交 MRQ 前执行防 T-pose 结构硬门禁：四个 CC5 动画 Section 必须全部显式 `force_custom_mode=true`，并且必须记录原生 Actor binding 与目标 Actor。渲染后还会比较第 `0/37/75/112/149` 帧，要求存在可见时间变化；旧输出只有在 pose-driver 与 temporal-motion 两个 contract 都通过时才可断点复用。无需 UE 即可用同一入口追加 `--audit-existing` 重验已有矩阵并生成 `matrix_motion_audit.json`。

正式配置图与代表链审查包的本地入口不需要 UE：

```powershell
python "D:\UE\Lance_Work\00_engine\scripts\dataset\build_first_batch_graph_source_v1.py"
python "D:\UE\Lance_Work\00_engine\scripts\dataset\build_first_batch_config_graph_v1.py" `
  --source "D:\UE\Lance_Work\00_engine\scripts\dataset\first_batch_graph_source_20260824_v1.json" `
  --output-dir "D:\UE\Lance_Work\00_engine\outputs\first_batch_dataset\graph_20260824_v1"
python "D:\UE\Lance_Work\00_engine\scripts\dataset\build_first_batch_chain_review_v1.py"
python "D:\UE\Lance_Work\00_engine\scripts\dataset\build_first_batch_prompt_layer_v1.py" `
  --graph-dir "D:\UE\Lance_Work\00_engine\outputs\first_batch_dataset\graph_20260824_v1" `
  --output-dir "D:\UE\Lance_Work\00_engine\outputs\first_batch_dataset\graph_20260824_v1\text_first_batch_20260824_v1"
```

机器结果位于 `OUTPUT_ROOT\first_batch_dataset\graph_20260824_v1`；10 条语义审查链和 2 条 UE 渲染候选位于其 `review_10` 子目录，模型文本位于 `text_first_batch_20260824_v1`。`chains.jsonl.instructions` 只供技术审计，训练端必须读取文本目录中的 `turns.jsonl` 或 `dialogs.jsonl`。

正式顺序为：

1. 创建唯一运行目录并冻结 `source_manifest`；**已完成**。
2. 生成 640 节点、同域原子边和精确 4,000 条链；**已完成**。
3. 验证两个域各 320 节点且连通、链配额、事实标签、轴分布和 640 节点覆盖；**机器门禁已完成**。
4. 从已验证节点池生成 640 个唯一 render job；**已完成**。
5. 从冻结边和链生成双语 `video_in + prompt + video_out` 文本层；**4,000 dialogs / 15,000 turns 机器门禁已完成**。
6. 本地完整链 smoke；**两条链的机器、assistant 预检和用户视觉签字均已完成**。
7. 服务器 10 节点基准；
8. 批量渲染唯一节点并按 `node_id` 重试；
9. 生成 sidecar、哈希并回填 `media_manifest`；
10. 对全部文本回合和链执行最终媒体引用一致性检查；
11. 人工抽检并封装交付。

首批采用 `full_pool`，所以 640 个节点全部渲染。未来大规模数据改用 `referenced_nodes_plus_connectivity` 时仍先生成链，再只渲染链引用节点并补充域连通桥接节点。32 例入口已经证明本地参数化装配、逐例渲染和断点续跑可用，但不能解释为已具备正式 640 节点队列、GT/sidecar、服务器重试或数据集验收能力。

## 7. 退出门禁

门禁为 [`GATE-09 DATASET_ACCEPTED`](../validation/README.md)。32-Look 本地证据位于 `OUTPUT_ROOT\unreal_render\first_batch_32look_matrix_20260824_v002\matrix_report.json`：32/32 案例、32 个唯一 Look、10 个动作、四台相机各 8 例、三种表情均覆盖，合计 4,800 张 PNG 与 32 个 MP4。每例均为 150 帧、2560×1440、30 fps、5 秒，32/32 pose-driver 与 temporal-motion contract 通过；后者的最小最大帧差为 `28.148507`，门槛为 `2.0`。OpenCV 独立复核 32 个 MP4 的尺寸、帧率和帧数均无异常。联系表和浏览入口分别为同目录的 `matrix_contact_sheet.png` 与 `index.html`。该结果只批准历史代表矩阵自动化，不改变正式 Happy-only 契约。

正式图、链与文本机器结构现已证明：640 节点、两个 320 节点连通域、4,000 条精确配额链、五个事实标签重算、四轴各 25%、全节点引用，以及 4,000 个双语 dialog / 15,000 个原子 turn。文本层内部 ID 泄漏为 0；E1 当前采用配对目标视频定位精确身份，文字只描述同性身份替换。完整 `VAL-DATASET-01` 仍需 GT/sidecar、资产追溯、服务器重试和媒体完整性通过。代表链视觉子门禁已经关闭，`VIS-DATASET-01` 仍需对正式节点做抽样视觉签字；既有服装极端动作穿模继续按 Look/动作兼容性警告处理。

代表链证据位于 `OUTPUT_ROOT\unreal_render\first_batch_chain_visual_smoke_20260824_v1`：男女各一条链，11 次路径节点引用去重为 9 个唯一视频；9/9 通过 150 帧、2560×1440、30 fps、Happy、视频 SHA-256、pose-driver 和 temporal-motion 门禁，最低最大帧差为 41.177483。`chain_review.html` 按路径顺序重复展示回滚/返回节点；用户已于 2026-08-24 接受，独立决定文件为 `user_visual_review_20260824_v1.json`。该决定只关闭代表链子门禁，不代替正式 640 节点抽检。

文本证据位于 `OUTPUT_ROOT\first_batch_dataset\graph_20260824_v1\text_first_batch_20260824_v1`：`prompt_report.json` 为 `passed`，精确 4,000 个 dialog、15,000 个 turn，E1/E2/E3/E7 各 3,750 回合，双语完整、原子性通过、内部 ID 泄漏为 0。`PROMPT_REVIEW.md` 固定抽取渐进、回退和返回起点样本供人工语言复核；训练多轮模型读取 `dialogue`，无历史单轮训练读取 `standalone`。

## 8. 失败与恢复

本地 32 例入口按样例目录保存状态并支持断点续跑；只有媒体规格、样例 ID 和 pose-driver contract 全部匹配时才复用旧结果。失败样例使用新的 retry 目录，不把不同来源的帧拼入一个已验收案例。正式服务器执行器仍需按失败类型支持仅重渲染缺失节点或整个节点，并保留失败报告；配置、资产或 Sequence 发生变化时必须生成新版本。

## 9. 技术依据与下一阶段

外部输出职责见 [`EXTERNAL_DIRECTORIES.md`](../reference/EXTERNAL_DIRECTORIES.md)，当前实施顺序见 [Sprint](../planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md)。本地 32 例只称为代表矩阵验收；只有 GT、sidecar、正式节点图、服务器媒体、链和引用检查全部通过 `GATE-09`，才代表一份数据集包完成。
