# HANDOFF：DataMake 当前接手说明

2026-10-28追加8条分叉展示：2–5轮各2条，按真实父子关系画SVG，并分两条路径展示共享前缀。原16条直链保留，统一展示目录现含24个会话及108份视频副本。入口为branches.html，详见[追加记录](00_engine/render_pipeline/docs/BRANCH_SHOWCASE_20261028.md)。

2026-10-28展示包已完成本机验证：按用户最终要求选择2–5轮各4条完整直链，网页、原始MP4副本及属性/编辑说明统一保存；本次视频获明确Git上传例外，发布范围仅限展示包。用户已在本地定位此前服装问题并表示大部分视频无需处理，服务器尚未收到具体修复方案，本轮未改生产媒体。详见[展示归档](00_engine/render_pipeline/docs/CHAIN_SHOWCASE_20261028.md)，下一步为上传后用户查看展示、等待本地修复说明与参考图片/文本。

最近核验：2026-10-23，Asia/Singapore。当前事实的人类入口是 [PROJECT_STATUS.md](./20_planning/data_design/character_creator/full_process/project_management/status/PROJECT_STATUS.md)，机器入口是同目录的 PROJECT_STATE.json。不要将历史报告中带日期的“当前/运行中/待提交”当作实时状态。

## 新会话阅读顺序

1. [`AGENTS.md`](./AGENTS.md)：协作与仓库规则。
2. [`full_process/README.md`](./20_planning/data_design/character_creator/full_process/README.md)：项目定义、文档树和端到端 Workflow。
3. [`PROJECT_STATUS.md`](./20_planning/data_design/character_creator/full_process/project_management/status/PROJECT_STATUS.md)：当前计划、活动批次、唯一下一步和阻塞。
4. 当前状态指向的 `WF-*` 文档：确认进入条件和 Exit Gate。
5. Workflow 指向的 Technical 文档：执行准确代码、配置、验证和恢复步骤。

最短路径：

```text
Master -> Current Status -> Active Workflow -> Technical -> Validation
```

## 当前工作定位

2026-10-23起分工：模型架构由模型对话继续；服务器/本地同步与UE渲染由另一对话负责。接手同步/渲染先读[SERVER_SYNC_STATUS](./20_planning/data_design/character_creator/full_process/project_management/status/SERVER_SYNC_STATUS.md)和[文档同步说明](./20_planning/data_design/character_creator/full_process/technical/rendering_release/DOCUMENT_SYNC.md)，不要把模型分支下一步当成本执行分支任务。

当前计划和 Workflow 不在本页硬编码。接手者必须读取 `PROJECT_STATE.json` 的：

```text
current_plan_id
active_batch_id
active_workflow_id
next_action
blocking_issues
```

随后核对对应 Plan Requirement、Workflow Status 和 Batch Status。若三者冲突，停止执行并按 [`GOVERNANCE.md`](./20_planning/data_design/character_creator/full_process/GOVERNANCE.md) 的权威顺序处理。

## Lance 当前接手边界

2026-10-23最新媒体讨论：[分阶段规格与形状算例](./10_research/model_experiments/lance/reports/datamake_stage_specific_media_specs_20261023.md)。用户提议生成source/history共用低规格ViT，理解保留标准ViT且不输入VAE/参考；参考图/视频VAE各设规格。具体数字未冻结，只有CPU算术，无模型实验。

2026-10-23已确认参考只作用于当前轮，旧参考仅存档、不重复输入生成器；训练推理一致。后续已确认生成阶段首选压缩历史ViT；ViT三组及历史prompt两组消融仅登记、暂不执行。用户随后要求将各类ViT与参考视频VAE的时间采样、空间尺寸及预算合并讨论，暂不固定历史优先抽帧。见下方多参考VAE方案第5、8节；尚未修改代码。

2026-10-22最新设计讨论：[多参考VAE与分支方案](./10_research/model_experiments/lance/reports/datamake_vae_references_branch_plan_20261022.md)。用户已明确按属性提供参考图片/视频、生成参考走VAE、理解tool_call选起点。当前代码仍是单图ViT，历史压缩/删除及旧参考策略待讨论；未实施新模型或训练。

2026-10-22当前源码入口：[官方基线迁移与验证](./10_research/model_experiments/lance/reports/datamake_source_migration_20261022.md)。基线已更新至4baeee0，源码位置仍为`lance/lance/`；当前安装权威为`patches/current/source_lock.json`，不要再叠加历史26份补丁。现行GT/整链训练依赖已从旧训练器拆开；旧checkpoint继续执行严格合同检查。此次没有启动正式训练，模型/数据/现存结果保留。

2026-10-18当前讨论入口：[架构决定总记录](./10_research/model_experiments/lance/reports/datamake_architecture_decisions_20261018.md)。参考图缺合适数据，暂不继续实际测试；转为讨论历史起点选择。普通prompt为-1、显式指向才定位；生成仅用祖先路径；理解/生成分别训练；推理非法输出回退并记录。分支尚未实现，未启动训练。以下运行状态仍为有日期的历史快照。

2026-10-12新增[官方训练代码对照审查](./10_research/model_experiments/lance/reports/datamake_official_training_comparison_20261012.md)：当前部分检查点在真实小尺寸GPU样例中与关闭/全开梯度一致；保留的GT1150/chain850合同与当前代码不匹配，直接续训前必须处理版本兼容。后续作业状态条目仍按2026-10-11快照理解，本轮未重新查询Slurm状态。

先读[2026-10-11进度](./10_research/model_experiments/lance/reports/datamake_progress_20261011.md)和[当前训练架构详解](./10_research/model_experiments/lance/reports/datamake_current_architecture_20261011.md)，再看相应 profile 与启动入口。

- 当前保留 GT fresh 与整链 pred_x0 v2 两组混合训练；都已超时停止，没有正式训练在运行。精确恢复点与作业记录由进度报告维护。
- 旧 GT1650 仅保留推理快照，不能当作完整续训 checkpoint；旧“仅保留 Stage5 B”等9月早期保留说明已过期。
- CFG 四卡消融与真实 prompt 拆分实验已完成。工程完整性不代替视觉质量；主计划 L06/L08 仍未关闭。
- 当前为双分支 PEFT/DDP、部分检查点、retain/minimal；批量、层号及 loss 细节见架构说明。没有进行训练 FlashAttention 后端迁移。
- 2026-10-11 已实现每轮可选单张 ViT 参考图，保留无图直链编辑；见[输入合同、问题回答与验证](./10_research/model_experiments/lance/reports/datamake_optional_reference_image_20261011.md)。小尺寸真实 GPU 推理与训练通路通过，现有训练集没有参考图样本，尚未训练参考图能力。
- 分支编辑、参考图 VAE、多视角和动作视频参考仍未实现；本轮未提交正式训练，也未制作新数据。新增代码改变实现合同，不能直接把旧 checkpoint 当作严格可续训状态。WF-90 数据发布状态保持不变。

## 本地、Git 与服务器边界

- 本地 Windows：CC5、UE Editor、MCP/Bridge、资产导入、视觉验收和本地 Smoke。
- Git：代码、文档、Schema、Registry、Manifest、哈希与轻量证据。
- 独立资产层：CC/UE 二进制资产、正式 UE `Content/` 和大型媒体。
- 服务器：环境/项目预检、性能基准、可续跑批量渲染和交付构建。

路径别名和服务器工作根见 [`PATH_ALIASES.md`](./20_planning/data_design/character_creator/full_process/reference/PATH_ALIASES.md) 与 [`SERVER_EXECUTION.md`](./20_planning/data_design/character_creator/full_process/technical/rendering_release/SERVER_EXECUTION.md)。

## 恢复规则

应用崩溃、会话重启或上下文中断后：

1. 不恢复 UE/CC 自动保存包，除非对应 Technical 恢复步骤明确要求。
2. 重新执行 `WF-00` 会话预检。
3. 检查 Git 工作树，不回退无法确认来源的修改。
4. 从当前 Workflow 的最后一个已验证 Gate 继续，不从对话中的“应该完成”继续。
5. 将故障、已验证恢复动作和未解决风险写回对应 Technical/Status。

通用恢复入口见 [`RECOVERY.md`](./20_planning/data_design/character_creator/full_process/technical/validation/RECOVERY.md)。

## 服务器接手

2026-10-23只读复核：历史source compatibility引擎路径缺失，工作区Installed Build未验收为替代；先确认UE_EDITOR实际路径再执行下列预检。详见服务器同步状态。

仅拉取 Git 不代表服务器具备生产资产。按 [`SERVER_EXECUTION.md`](./20_planning/data_design/character_creator/full_process/technical/rendering_release/SERVER_EXECUTION.md) 依次执行环境预检、资产/项目 Smoke 和小规模基准。环境阶段可运行：

```bash
UE_EDITOR="/absolute/path/to/verified/Engine/Binaries/Linux/UnrealEditor" \
  bash 20_planning/implementation/FIRST_BATCH_SERVER_PREFLIGHT.sh --environment-only
```

正式 Render Jobs 执行器、媒体 Sidecar/Manifest 和节点级重试的生产 Gate 结果以 `WF-80` 状态为准；第一批发布与 QA 结论以已关闭的 `WF-90` 状态为准，当前活动工作以 Lance 正式微调计划为准。

## 文档维护

完成阶段、改变计划、修改实现或新增长期输出后，调用项目级 `character-factory-doc-maintenance` Skill，再运行：

```powershell
python 00_engine/scripts/documentation/build_script_lifecycle_catalog.py
python 00_engine/scripts/documentation/build_output_inventory.py
python 00_engine/scripts/documentation/check_character_factory_docs.py --json
```

重构快照和旧文档只用于审计，不能作为当前执行入口。
