# DataMake 多轮数据接入 Lance 训练

> 创建日期：2026-08-29；当前源码核验：2026-10-22。上游基线：bytedance/Lance@4baeee0，加单一当前补丁。
> 本文件拥有下游训练实现与证据导航。当前行为优先读[训练架构详解](reports/datamake_current_architecture_20261011.md)，当前run/恢复点读[进度核对](reports/datamake_progress_20261011.md)。
> 下文按阶段保留历史设计、命令与验收；旧阶段标题中的“当前”指当时，不能据此判断现存目录或提交作业。

## 2026-10-22 源码迁移与重建

2026-10-23新增[分阶段媒体规格与张量形状](reports/datamake_stage_specific_media_specs_20261023.md)，由本文件拥有：记录用户的统一生成ViT/标准理解ViT提议，数值为候选算例，不修改现行运行配置或源码锁。

新的目标架构由[多参考VAE与分支方案](reports/datamake_vae_references_branch_plan_20261022.md)记录：用户已确定属性参考输入及VAE方向，2026-10-23已确认生成参考只属于当前轮、不重复输入旧参考；历史ViT压缩保留已为首选、具体压缩与尺寸仍待讨论；ViT完整/压缩/删除及历史prompt保留/移除消融只登记，暂不执行。该设计由本Technical拥有；尚未修改运行代码或当前源码锁。

实现、筛选理由、命令和验证归[源码迁移报告](reports/datamake_source_migration_20261022.md)。当前GT/整链PEFT/DDP、数据合同、部分检查点、padding、CFG及可选单图保留；旧FSDP训练循环退役，旧格式读取/转换作为兼容库。`scripts/datamake_runtime.py`拥有当前公共环境及参数映射，`scripts/rebuild_lance_checkout.py`拥有固定官方提交＋单一补丁的重建和哈希校验。两者均为active，由本文件拥有。

`patches/current/source_lock.json`是当前源码安装权威；`patches/legacy/`仅为来源记录。`scripts/legacy/`和`tests/legacy/`不属于当前训练/回归入口，旧命令显式拒绝启动。新诊断归既有 `outputs/optimization_diagnostics/source_migration_20261022/`，包含旧源码可校验归档；归档保护手工批注，不自动授予清理模型、数据或实验结果的权限。Lance主路径仍为外层目录下的`lance/`。

旧checkpoint仍受严格实现合同保护；本次未授权或实施绕过合同的续训。正式八卡启动继续执行既有连续/恢复Gate。

## 2026-10-18 设计讨论入口

2026-10-22补充[官方上游与LoRA生态核查](reports/datamake_lance_upstream_lora_survey_20261022.md)：当前官方main为4baeee0，比本地9717d91基线多一项安全修订；未发现训练核心/官方LoRA更新。未升级代码、依赖或执行实验。

2026-10-21补充[多图/参考视频与五轮序列预算](reports/datamake_multi_reference_token_budget_20261021.md)：用户提出未来放宽单图限制，本轮仅做代码/配置核对与长度估算。单图实现合同不变，多参考及分角色采样尚未接入；65K输入预算不等于显存/质量已验收的长度。

补充[Tool Calling训练方法调研与本地接入核对](reports/datamake_source_routing_tool_call_research_20261018.md)：官方理解CE可复用，当前模板/LoRA范围/视频trainer不能直接当作纯理解工具调用入口；结构化SFT及独立adapter仍是待讨论方案，本轮未改训练代码。

[参考图与历史起点选择总记录](reports/datamake_architecture_decisions_20261018.md)由本文件拥有，稳定语义见[ADR-0019](../../../20_planning/data_design/character_creator/full_process/project_management/decisions/ADR-0019-EXPLICIT-HISTORY-SOURCE-ROUTING.md)。参考图代码保留，因缺合适数据暂不继续实际测试；当前讨论显式source_video_id选择、祖先路径、理解/生成分别训练及推理非法输出回退。该记录不代表已实现分支或已选定两套adapter，不改变下面的现有训练入口。

## 2026-10-11 当前实现入口

2026-10-12补充：[官方训练代码对照审查](reports/datamake_official_training_comparison_20261012.md)核验当前训练主干与部分检查点。GPU小尺寸三种checkpoint模式梯度一致；GT/整链归约差异及旧checkpoint合同不兼容需分别处理，不能从adapter可推理推导可直接续训。审查产物归既有 `outputs/optimization_diagnostics/official_training_audit_20261012/`，由本文件拥有；未修改训练实现或配置。

当前使用混合UE＋CoinVE、八卡PEFT/DDP、理解＋生成r64 LoRA、无区域MSE加权；有效检查点为0–25层开启、26–35层关闭，VAE cache retain，attention padding minimal。GT前缀每卡batch1/累计4；整链pred_x0按32目标窗口归约，生成历史detach，不跨轮反传。两种采样与归约合同有差异。

GT fresh与整链v2均已运行并超时停止，不是“待首次GPU验证”。旧GT1650快照已用于完成CFG和prompt拆分推理，快照不能完整续训。训练仍为FlexAttention，推理原有FlashAttention路径；原训练 profile 未改写。

当前技术说明由本文件拥有：[架构报告](reports/datamake_current_architecture_20261011.md)、同名HTML阅读版及其 `reports/figures/lance_*_20261011.svg` 是轻量版本化文档，不是新的训练输出类别。Markdown为正文源，HTML是其内嵌SVG的阅读副本，更新正文时需同步。运行产物仍归既有 training_runs / multiturn_chat / optimization_diagnostics。

## 可选单张 ViT 参考图扩展（2026-10-11）

稳定决定见 [ADR-0018](../../../20_planning/data_design/character_creator/full_process/project_management/decisions/ADR-0018-OPTIONAL-SINGLE-VIT-REFERENCE.md)。详细字段、命令、问题回答、已知限制与验证记录由本文件所属的[参考图实现报告](reports/datamake_optional_reference_image_20261011.md)维护；本节拥有其脚本生命周期和输出归属。

- 训练前缀增加可选 `reference_images` 列，与 prompts 对齐；推理 user turn 使用单个 `reference_image`。图片仅进入冻结 ViT，按每轮最多一张处理，保留其所属历史轮次。无图轮次保持原输入，不增加空图片或新词表。
- 参考图不得成为源 VAE、目标 VAE 或 MSE 目标。沿用静态时间网格和 video placeholder，避免混合 image/video 网格游标；现有 ViT CFG 同时控制历史视频和参考图，没有独立 reference CFG。
- `scripts/build_multiturn_conversation.py` 为 active 推理输入构建器；`scripts/prepare_datamake_reference_training.py` 为 active 数据审计/独立 GT 配置准备工具，必须显式绑定新数据，准备过程不提交作业。
- `scripts/verify_datamake_reference_gpu.py`、`scripts/verify_datamake_reference_training_gpu.py` 为 active 工程验证工具，输出归 `outputs/optimization_diagnostics/reference_image_20261011/`；证据和夹具不是正式训练数据，不修改既有 checkpoint。本输出仍由本文件拥有，沿用现有诊断输出类别，不授予自动清理权限。
- 小尺寸真实推理以及正式 Mixed Dataset/Packed/VAE 的 forward、backward 和 AdamW 更新已通过；没有正式尺度吞吐、八卡参考图恢复或学习后效果结论。当前数据无参考图监督，下一步需先提供真实参考图样例再建立独立训练实验。新增实现 hash 改变旧恢复合同，adapter 加载兼容不等于完整续训兼容。

以下历史章节按原阶段读取；其中“当前”不覆盖本节与项目 Status。

## 1. 目标与边界

本接入把 DataMake 发布包的多轮编辑链转换为 Lance 可训练样本，同时保护三条数据语义：

1. 完整历史文本保留为独立的 `user/assistant` 回合，不把所有指令拼成一个当前 prompt。
2. 历史节点只作为 ViT 语义上下文；最新 `video_in` 是唯一 clean VAE source。
3. 当前 `video_out` 是唯一 VAE target，MSE 不落到历史视频。

当前保留Stage2全参模型和暂停的Stage5 A/B（恢复点A800/B350）。Stage6采用Stage2配方的两臂LoRA（§6.12），共同官方基座、GT前缀；restart1已完整保存到800，用户已提交800续训，同时执行[两臂800步独立视觉检查](./reports/datamake_stage6_step800_visual_sanity_20260909.md)。精确训练状态由[恢复记录](./reports/datamake_stage6_checkpoint_rescue_20260907.md)维护；tiny/Stage1结果已退役，不作为当前入口。

## 2. 输入权威

2026-09-09新增的独立性能实现、命令与输出所有权见下方[PEFT/DDP优化](#peftddp-性能优化2026-09-09)；该入口不改变本节的数据权威。

合成分支的正式输入必须来自 `WF-90` 发布包；2026-09-11授权接入的外部CoinVE分支按[混合数据合同](./reports/datamake_coinve_mixed_dataset_20260911.md)单独追溯：

```text
delivery/<batch_id>/
  chains.json
  videos/*.mp4
  manifest.json
```

`chains.json` 的每个 Turn 必须保持：

```text
上一轮 video_out == 下一轮 video_in
```

构建器会检查链轮次、端点连续性、相对路径边界和所有媒体是否存在。当前正式训练输入为 `00_engine/outputs/delivery/first_batch_candidate_20260830_v002/dataset_v1/`。它包含 640 个视频、4,000 条链和 15,000 个 Turn；原始 Render Run Root 删除后通过 package-only 全量验证，并于 2026-08-31 在 `JDS9B74/job118880` 通过候选态与发布态独立全包复验。Manifest 状态为 `released`，正式训练可以在 split 和配置 Gate 完成后启动。

## 3. 链前缀编码

一条 `C0 --p1--> C1 --p2--> ... --pk--> Ck` 链产生 `k` 个监督样本。第 `r` 个样本使用前缀 `C0..Cr`：

| 内容 | Lance 分支 | 训练角色 |
| --- | --- | --- |
| `C0..C(r-2)` | ViT | 历史语义参考，不进入 clean VAE source |
| `C(r-1)` | ViT + VAE | 最新直接输入，唯一 clean VAE source |
| `p1..pr` | Qwen 多轮 chat template | 完整历史 user 文本；当前 prompt 单独定位 |
| `Cr` | VAE | 唯一带 `loss=1` 的目标视频 |

监督按轮次拆分而不是在一个超长样本中同时预测全部输出：`C1` 在第 1 个前缀中是 target，进入后续前缀后只作为 `loss=0` 的历史条件；`C2..Ck` 同理。因此一条 `k` 轮链在数据集层面提供 `k` 个当前轮视频损失，而每个训练样本仍保持 Lance 原生编辑路径的 `N_target=1` 和唯一 source-target 对齐。

Parquet 每行保存 `prompts` 和 `video_paths`，不内嵌重复 MP4 字节。媒体由 `media_root + relative path` 读取，因此 640 个端点视频不会因 15,000 个 Turn 被复制成 15,000 份二进制。`--prompt-view dialogue` 生成完整链前缀；`--prompt-view standalone` 则只编码当前 `video_in + standalone prompt + video_out`，用于严格单轮对照，不携带历史。

### 3.1 训练视图优先级

用户确定训练以 `dialogue` 为主，`standalone` 构建能力保留但暂缓训练，不与当前数据混采。WF-90 与链级 split 已关闭；当前关注 Stage5 视觉质量和下一版方案。历史 tiny 实验已退役，不再是待执行 Gate。

Schema 版本：

```text
datamake_lance_multiturn_prefix_v1
```

### 3.2 Stage 4 一行一链与在线历史

2026-09-04 用户冻结的新训练语义不再把 train 的 3,600 条链物理展开为 13,483 个前缀记录。派生 parquet 每条链仅一行；训练主循环在链内保持每轮 `N_target=1` 的原生 Lance 编辑序列，并依次累计该链所有目标损失。对第 `t` 轮：

- ViT 条件为 `v0 + g1...g(t-1)`；
- 唯一 direct VAE source 为 `g(t-1)`，第 1 轮为 `v0`；
- 文本为独立的 `p1...pt` 历史回合；
- 唯一 VAE target 仍是 released GT `vt`。

`g` 由当前正在优化的 LoRA 模型在线生成，30-step rollout 全程 no-grad/detach，并以 CPU FP16 CTHW 张量直接进入下一轮 ViT/VAE 编码，不写临时 MP4。每个 target 的原生 flow-matching latent MSE 先做 token mean，再在两个 chain group 的 accumulation window 内对全部 target 做全局等权平均；因此同一次更新内长链按目标视频数量成比例贡献监督，但不额外做 R5 过采样。这里的“全局”指跨 rank 的当前更新窗口，不是整个 Epoch：每步 8 条链对应的 target 数 N 可变，每个 target 的 loss 系数为 1/N；24-target 与 40-target 两步分别为 1/24 与 1/40，不保证跨更新窗口的固定系数。2026-09-06 已向用户解释该边界：这是可接受的归一化配置，不作为阻断性计算错误处理，当前 A/B 继续保留相同规则；固定分母可留作独立消融，不中途改变已有训练。新 schema 为 `datamake_lance_chain_dataset_v1`，详细契约见 [Stage 4 实现说明](./reports/datamake_stage4_online_rollout_lora_implementation_20260904.md)。

### 3.3 Stage 5 单步 `pred_x0` 历史

2026-09-04 用户确认训练瓶颈主要是每个中间 turn 的 30-step rollout，因此 Stage 5 只替换生成历史的方法，不改变一行一链数据、目标 loss、LoRA、梯度累计、优化器、LR、dropout 或 checkpoint。对仍有下一轮的目标，训练器从本轮正常 flow-matching forward 复用：

```text
z_t = (1 - t) * x0 + t * epsilon
pred_x0 = z_t - t * pred_velocity
```

该 `pred_x0` detach 后由冻结 VAE 解码为 CPU FP16 视频，下一轮仍将全部历史送入 ViT，并把最近历史重新 VAE encode 为唯一 direct source。它不执行额外 diffusion step、不运行 CFG 双分支，也不使用 KV cache；标准 held-out 推理仍保持 30-step sampling。由于起点 `z_t` 来自 rendered GT 加噪，这是一种 noisy-GT-conditioned 快速代理，而非模型完整推理分布。完整实现、吞吐与 Gate 见 [Stage 5 报告](./reports/datamake_stage5_one_step_x0_history_20260904.md)。

启动前复查又修正了两处代码一致性：默认 Lance `forward` 不再无条件返回三个值为 `None` 的 flow 字段，原 `unified_train` 接口保持不变；真实训练 `timestep_shift` 与 profile optimization/rollout 三处均固定为 `4.0`。这些修正不改变已通过四卡 smoke 的 one-step 数值路径，故不重复 GPU smoke。`pred_x0` 解码视频预览不再作为正式启动硬 Gate；训练后视觉结论仍必须来自标准 30-step held-out 自回灌推理。

### 3.4 数据目录导航与清理边界

[training_data/README.md](./outputs/training_data/README.md)维护三份保留派生数据的用途和消费者。未划分candidate和旧单文件split经全字段多重集合核验，被8-shard完整覆盖，已于2026-09-07按用户确认删除；现存40个数据文件、A/B配置及冻结实现哈希不变。Stage5 A/B使用chain数据，固定视觉检查读取8-shard版validation；Stage2增采样数据同时供新Stage6配置使用。现存数据、配置、checkpoint路径不移动。

用户于2026-09-06进一步授权删除旧`inputs/`、全部`logs/generated_configs/`及空`outputs/training_eval/`；其中Stage2的旧推理输入JSON一并删除，Stage2模型/报告/生成结果仍保留。当前推理Run内的`*.input.json`与`manifest.json`未动。删除记录和不可恢复边界见[清理报告后续部分](./reports/datamake_lance_storage_cleanup_20260906.md#后续授权旧输入与生成配置清理)。

## 4. 实现所有权

| 文件 | 作用 |
| --- | --- |
| [`scripts/build_datamake_multiturn_training_data.py`](./scripts/build_datamake_multiturn_training_data.py) | 校验发布链，生成路径型 parquet、Lance YAML 和 manifest |
| [`scripts/build_datamake_dialogue_splits.py`](./scripts/build_datamake_dialogue_splits.py) | 用种子哈希按完整 `chain_id` 构建 3,600/200/200 split，并固化零泄漏、计数和哈希审计 |
| [`scripts/inspect_datamake_multiturn_training_data.py`](./scripts/inspect_datamake_multiturn_training_data.py) | 使用 Lance 真实 tokenizer、视频 transform 和 `PackedDataset` 解码/打包跨多个 parquet 的全局指定行 |
| [`scripts/run_datamake_training.sh`](./scripts/run_datamake_training.sh) | 历史全参 smoke/resume 启动（tiny预设已删除）、W&B online/offline、日志、异常与检查点完整性 Gate |
| [`configs/datamake_dialogue_first_batch_v1.json`](./configs/datamake_dialogue_first_batch_v1.json) | 首轮四卡正式训练冻结 profile；记录数据、patch、优化、checkpoint、W&B 与 Slurm 契约 |
| [`scripts/run_datamake_formal_training.py`](./scripts/run_datamake_formal_training.py) | 校验 profile/hash/数据分配/完整 checkpoint/W&B/GPU，并生成唯一正式 `torchrun` 命令 |
| [`jobs/datamake_dialogue_first_batch_v1.sbatch`](./jobs/datamake_dialogue_first_batch_v1.sbatch) | `testqueue` 单节点四 H200、18 小时分段任务；清除 submit-host localhost 代理；stdout/stderr 分别落到 `outputs/slurm_logs/`；Job `119261` 已在 `8GS9B74` 完成 |
| [`scripts/analyze_datamake_training_log.py`](./scripts/analyze_datamake_training_log.py) | 去重 tqdm 指标，检查连续步、异常和首末窗口统计 |
| [`scripts/build_datamake_teacher_forced_conversation.py`](./scripts/build_datamake_teacher_forced_conversation.py) | 从一个 dialogue prefix 构建只生成最终轮的 teacher-forced conversation |
| [`scripts/run_datamake_lora_visual_sanity.py`](./scripts/run_datamake_lora_visual_sanity.py) | 单次加载 checkpoint 指定的 base + LoRA，并复用训练 YAML 的 VAE/ViT/帧采样；生成固定 validation 三轮自回灌与 R2/R3/R5 真值历史对照，不修改训练或 W&B |
| [`scripts/build_datamake_visual_sanity_review.py`](./scripts/build_datamake_visual_sanity_review.py) | 全帧解码检查、原视频/GT/指定历史 Run/当前模型便携 HTML 与三时点抽帧；`--compare-run LABEL=RUN_DIR` 可重复，省略时保留旧第二阶段对照，只属于少量视觉 sanity |
| [`tests/test_datamake_lora_visual_sanity.py`](./tests/test_datamake_lora_visual_sanity.py) | 验证自回灌/真值历史隔离、父节点映射，以及 A/B 训练 YAML、真实 builder 空间尺寸、像素归一化和历史帧采样一致性 |
| [`tests/test_build_datamake_visual_sanity_review.py`](./tests/test_build_datamake_visual_sanity_review.py) | 多检查点列标签、完成态输入、同名视频不碰撞，以及参考视频/manifest 的便携复制 |
| [`scripts/compare_videos_framewise.py`](./scripts/compare_videos_framewise.py) | 生成帧级像素诊断；不替代语义质量评估 |
| [`patches/legacy/0004-datamake-multiturn-training-dataset.patch`](./patches/legacy/0004-datamake-multiturn-training-dataset.patch) | 在被忽略的上游 clone 中注册 DataMake 多轮训练 Dataset |
| [`patches/legacy/0005-wandb-online-resume-metrics.patch`](./patches/legacy/0005-wandb-online-resume-metrics.patch) | 让 W&B 使用稳定 Run ID 续写、在 Run Root 保存本地缓冲并补充 step 吞吐指标 |
| [`patches/legacy/0006-formal-scheduler-checkpoint-resume.patch`](./patches/legacy/0006-formal-scheduler-checkpoint-resume.patch) | 单向余弦调度、completed-step checkpoint、原子完整标记、最近两份保留与正确 next-step 恢复 |
| [`patches/legacy/0007-datamake-distributed-data-resume.patch`](./patches/legacy/0007-datamake-distributed-data-resume.patch) | 将 DataMake Dataset 从 local-debug iterator 切回正式分布式、可恢复 iterator |
| [`tests/test_build_datamake_multiturn_training_data.py`](./tests/test_build_datamake_multiturn_training_data.py) | 发布链、端点复用、路径和 YAML 测试 |
| [`tests/test_build_datamake_dialogue_splits.py`](./tests/test_build_datamake_dialogue_splits.py) | split 输入顺序无关性、released 前置条件、集合互斥、前缀完整性与路径引用测试 |
| [`tests/test_datamake_multiturn_dataset.py`](./tests/test_datamake_multiturn_dataset.py) | role-aware 训练 sequence plan 测试 |
| [`scripts/build_datamake_chain_training_data.py`](./scripts/build_datamake_chain_training_data.py) | 从冻结 split 生成一行一链的 Stage 4 parquet/YAML/manifest |
| `configs/datamake_dialogue_online_rollout_lora_r64_v2.json`（历史文件已于2026-09-11清理） | Stage 4 的 4×H200、1,800-step、r64、online rollout、checkpoint-v5 profile；四卡 smoke 已通过，正式训练仍未授权 |
| [`scripts/run_datamake_online_rollout_lora_training.py`](./scripts/run_datamake_online_rollout_lora_training.py) | 校验实现/数据/基座 hash、四卡、W&B、adapter resume、Run Manifest 和双层训练授权 |
| [`scripts/inspect_datamake_online_rollout_pack.py`](./scripts/inspect_datamake_online_rollout_pack.py) | 用真实视频和内存 FP16 模拟历史审计 R1～R5 token 与 source-target 布局 |
| [`patches/legacy/0011-datamake-chain-online-rollout-lora.patch`](./patches/legacy/0011-datamake-chain-online-rollout-lora.patch) | 一行一链在线 rollout、精确 LoRA target、内存历史和 adapter-only 恢复实现 |
| [`patches/legacy/0012-fix-nested-fsdp-lora-checkpoint.patch`](./patches/legacy/0012-fix-nested-fsdp-lora-checkpoint.patch) | nested-FSDP live LoRA 导出、空 shard 恢复与 checkpoint v5 |
| [`configs/datamake_dialogue_one_step_x0_lora_r64_v3.json`](./configs/datamake_dialogue_one_step_x0_lora_r64_v3.json) | Stage 5 的 4×H200、1,800-step、single-forward `pred_x0` 历史候选 profile |
| [`patches/legacy/0013-datamake-one-step-x0-history.patch`](./patches/legacy/0013-datamake-one-step-x0-history.patch) | 从原生训练 forward 导出 detached `pred_x0` 历史，跳过独立 30-step rollout |
| [`jobs/datamake_dialogue_one_step_x0_lora_r64_v3.sbatch`](./jobs/datamake_dialogue_one_step_x0_lora_r64_v3.sbatch) | Stage 5 的 `testqueue` 单节点四 H200、18 小时分段正式入口 |
| [`configs/datamake_dialogue_one_step_x0_lora_r64_stage2base_v1.json`](./configs/datamake_dialogue_one_step_x0_lora_r64_stage2base_v1.json) | `ABL-LORA-BASE-01/B`：只替换 Stage 2 基座、其余 v3 配方不变的独立 profile |
| [`jobs/datamake_dialogue_one_step_x0_lora_r64_stage2base_v1.sbatch`](./jobs/datamake_dialogue_one_step_x0_lora_r64_stage2base_v1.sbatch) | 用户手动提交的 Stage 2 基座对照；独立输出/W&B，testqueue 4H200、18h |
| [`tests/legacy/test_datamake_stage2base_profile.py`](./tests/legacy/test_datamake_stage2base_profile.py) | 配方/CLI 合约、基座 target topology、Run 隔离与 Slurm 配置检查 |

上游 `lance/` clone 被外层 Git 忽略。可审计实现是 `0004` patch 和外层脚本，不以 clone 当前未提交状态作为唯一来源。

## 5. 构建与检查

在新 clone 应用训练 patch：

```bash
cd 10_research/model_experiments/lance/lance
git apply ../patches/legacy/0004-datamake-multiturn-training-dataset.patch
git apply ../patches/legacy/0005-wandb-online-resume-metrics.patch
git apply ../patches/legacy/0006-formal-scheduler-checkpoint-resume.patch
git apply ../patches/legacy/0007-datamake-distributed-data-resume.patch
```

从发布包构建英文 dialogue 训练视图：

```bash
/scratch/prj0000000275/jcy/.conda/envs/xks_lance/bin/python \
  10_research/model_experiments/lance/scripts/build_datamake_multiturn_training_data.py \
  --chains 00_engine/outputs/delivery/first_batch_candidate_20260830_v002/dataset_v1/chains.json \
  --output-dir 10_research/model_experiments/lance/outputs/training_data/<run_id> \
  --language en \
  --prompt-view dialogue
```

正式首轮不直接使用未划分的全量 parquet，而执行：

```bash
/scratch/prj0000000275/jcy/.conda/envs/xks_lance/bin/python \
  10_research/model_experiments/lance/scripts/build_datamake_dialogue_splits.py \
  --chains 00_engine/outputs/delivery/first_batch_candidate_20260830_v002/dataset_v1/chains.json \
  --package-root 00_engine/outputs/delivery/first_batch_candidate_20260830_v002/dataset_v1 \
  --output-dir 10_research/model_experiments/lance/outputs/training_data/datamake_dialogue_first_batch_v002_split_seed2026_sharded8_20260831 \
  --seed 2026 \
  --train-chains 3600 \
  --validation-chains 200 \
  --test-chains 200 \
  --language en \
  --train-parquet-shards 8
```

算法为 `SHA-256(seed + NUL + chain_id)` 升序取固定数量，不做分层且不依赖源 JSON 顺序。输出只包含 chain ID 清单、路径型 parquet、Lance YAML 和 Manifest；视频仍从 released 包共享读取。该派生输出可由 released 输入、脚本哈希和 seed 重建，在首轮训练及 held-out 评估关闭前保留，不作为独立发布数据集晋升。

运行无需 pytest 的单元测试：

```bash
/scratch/prj0000000275/jcy/.conda/envs/xks_lance/bin/python -m unittest discover \
  -s 10_research/model_experiments/lance/tests \
  -p 'test_*.py' -v
```

对某个真实媒体行执行 Lance CPU pack：

```bash
/scratch/prj0000000275/jcy/.conda/envs/xks_lance/bin/python \
  10_research/model_experiments/lance/scripts/inspect_datamake_multiturn_training_data.py \
  --config 10_research/model_experiments/lance/outputs/training_data/<run_id>/lance_dataset.yaml \
  --row-index 0
```

检查结果必须同时满足：

```text
within_token_limit = true
clean_vae_sources = 1
vae_targets = 1
source_target_alignment = true
```

## 6. 当前验证证据

2026-08-29 在 `xks_lance` 环境完成：

- 7 个单元测试通过。
- 2 链发布样例确定性生成 6 个英文 dialogue 链前缀样本。
- 真实三轮样例经 Lance tokenizer、decord、ViT/VAE transform 和 `PackedDataset` 打包为 47,834 tokens。
- 三轮样例得到 3 个 ViT 条件、1 个 clean VAE source、1 个 VAE target；target 使用 `loss=1`。
- 五轮 token 上限 smoke 使用同规格样例媒体构造五轮前缀，得到 62,454 tokens，小于当前 65,536 限制。该检查只证明默认 `VAE 480 / ViT 448` 编码预算，不是五轮语义质量证据。
- 非 Flex attention 路径不接受上游编辑条件的 `full_noise` 模式；正式脚本本身使用 `USE_FLEX=True`，检查器也固定走 Flex 路径。

2026-08-31 已从 released `chains.json@f28b0872...` 生成 seed `2026` 的正式链级随机划分：train 为 3,600 chains / 13,483 prefixes，validation 为 200 / 754，test 为 200 / 763；三者合计 4,000 chains / 15,000 prefixes。三组 chain/sample 集合两两零交叉，union 等于源集合，每个 split 均覆盖 Round 1..5、四个正式编辑轴、rollback 与 return-to-start 样本。第二次在 `/tmp` 独立重建得到相同 chain-ID 与每个 parquet shard 的 SHA-256。正式 train 被确定性写成 8 个 shard，使 4 ranks × 2 workers 每个 worker 都能获得 1 个文件；冻结入口为 `outputs/training_data/datamake_dialogue_first_batch_v002_split_seed2026_sharded8_20260831/split_manifest.json`。四卡 global batch 4 时单 Epoch 为 `ceil(13,483 / 4) = 3,371` 个 optimization step。

正式接入审计随后发现 DataMake Dataset 原先继承 Lance 的 local-debug iterator：该路径不按 rank/worker 做正式文件分片，也不消费 checkpoint 中的 `data_status`。`0007` 已把它切回 `BaseMMParquetDataset` 的 distributed/resume-aware iterator，并以单测验证 8 shard 在 4 ranks × 2 workers 下无空 worker、checkpoint 行位置从最后完成样本的下一行恢复。由于 13,483 不能被 4 整除，文件顺序单独使用 `data_seed=2040`；这不改变 seed `2026` 的 train/validation/test 随机划分，也不改变模型 `global_seed=2026`。该顺序把唯一训练行分配为 `[3371,3371,3371,3370]`，从而覆盖全部 13,483 个唯一前缀，只为同步 batch 补齐重复 1 条；启动器会重新计算并强制校验这一性质。

真实 CPU pack 已在正式 8-shard train YAML 上抽查 Round 1..5，并同时覆盖 `identity_id/outfit_id/action_id/camera_id`、rollback 与 return-to-start。五轮分别得到 33,136 / 40,545 / 47,877 / 55,195 / 62,539 tokens，全部小于 65,536；每个样本均为历史轮数对应的 ViT 条件、1 个 clean VAE source 和 1 个 `loss=1` VAE target。当前正式接入基线测试为 31/31 通过，patch `0004..0007` 可从 `9717d916...` 干净重放且与工作 clone 一致。

### 6.1 Stage1 / Tiny 历史退役

Stage1正式训练和tiny实验已经执行过，但用户于2026-09-06明确不再保留其结果。专用配置、数据、报告、日志、视觉媒体及此前的checkpoint均不再作为在线证据，删除清单见[本次清理记录](./reports/datamake_lance_storage_cleanup_20260906.md)。Stage1静态profile/job仅作为共用formal-launcher回归依赖保留，不提供恢复能力，也不推荐重新启动；不在本页复述旧超参和指标。

### 6.4 第二阶段 R5×3 与区域加权

用户确认第一阶段虽有改善但尚未达到预期，并因时间限制决定跳过 100～300-step A/B。第二阶段从 step3371 权重开始新 optimizer/scheduler horizon：Round 1～4 各保留一次，Round 5 的 596 条各出现三次，有效 train 从 13,483 增至 14,675 行；validation/test 不重写。8 个新 Parquet 独立重建哈希一致，`data_seed=2081` 在 4 ranks × 2 workers 下完整覆盖并只同步补齐一条，全局 batch 4 的单 Epoch 为 3,669 steps。

patch [`0009-datamake-round-region-weighted-loss.patch`](./patches/legacy/0009-datamake-round-region-weighted-loss.patch) 给唯一 direct source 与 target VAE latent 增加训练角色；冻结 VAE 下以 `mean(abs(target-source), channel)` 的 50%/90% 分位数生成 soft importance，原始 token 权重 `1 + importance`，通过四卡全局权重和归一化。所有未变 token 继续参与监督；推理阶段没有 target，也不会执行该路径。日志同时记录实际 `mse`、`mse_unweighted`、`edit_region_weight_mean/max`。

冻结 profile 为 [`configs/datamake_dialogue_stage2_r5x3_region_v1.json`](./configs/datamake_dialogue_stage2_r5x3_region_v1.json)：LR `1e-5`、101-step warmup 后单向 cosine 到 `1e-6`、三个 condition dropout 全 0、无 LoRA/EMA、600-step full-state、最近一份保留和最终 step3669 保存。此处是2026-09-01准备阶段的配方记录：当时从Stage1初始化；该Stage1权重现已删除，不能照旧profile重新启动。正式/smoke dry-run、44 项 Lance unittest、Round-5 真实 pack、patch 重放和 Slurm test-only 已通过。用户取消未启动的四卡 smoke Job `120397` 后，`scripts/run_datamake_stage2_local_smoke.py` 在 allocation `120417` 的单 H200 上复用同一模型、数据和 loss，仅把 world size 改为 1；两步正常 exit 0，`mse/mse_unweighted`、区域权重和 `total_norm` 均有限且没有 checkpoint。

Job `120425` 随后于 2026-09-01 18:05:33 至 2026-09-02 11:52:46 完成全部 3,669 steps，Slurm `COMPLETED/0:0`。加权/未加权 MSE 的前后 200-step 均值下降 29.66%/31.16%，完成时的 `0003669` 是完整 checkpoint；2026-09-04 已将它降级整理为 `outputs/model_bases/datamake_dialogue_stage2_step3669/` 的 base-only artifact，保留模型用于 fresh LoRA 消融，不再保留全参 optimizer 恢复能力。2026-09-03 的四个 teacher-forced 样例显示 identity、R3 outfit 和 R5 outfit 明显改善，action 消除双人重影但相机/背景漂移；同一三轮链的真正自回灌仍能继续执行第三轮换装，却继承第二轮构图偏移。精确运行、指标和输出见 [`reports/datamake_dialogue_stage2_results_20260903.md`](./reports/datamake_dialogue_stage2_results_20260903.md)。

### 6.5 第三阶段 LoRA/model-rollout 实现评审

2026-09-03 用户提出后续候选：r64 LoRA、只训练生成分支、LR `1e-4`，并对比 rendered GT history 与 frozen-model rollout history。patch [`0010-datamake-generation-lora-rollout-history.patch`](./patches/legacy/0010-datamake-generation-lora-rollout-history.patch) 以独立入口实现，不修改第二阶段冻结的 `unified_train.py` 等历史文件。shape-only 审计在 step3669 checkpoint 上确定 256 个生成侧目标模块与 120,412,160 个可训练 LoRA 参数；全部基座与理解分支冻结。

数据实现明确保留当前 target 为 rendered GT，并提供 `teacher_forced`、`rollout_vit_only`、`rollout_full` 三个视图。`rollout_full` 最接近部署，但其生成 direct source 不是 GT target 的精确父节点，因此新入口禁止同时使用 VAE source-target 区域加权。全量 offline rollout 粗估约 404 H200 GPU-hours，必须先做 pilot 校准。当前仅完成 Python 编译、9 项 LoRA/history 单元测试、历史 stage2 hash 复核和目标 shape 审计；未完成 GPU optimization、save-resume-inference roundtrip 或 rollout 媒体验证，也未编写/提交正式 Slurm 训练任务。详见 `reports/datamake_stage3_lora_history_design_20260903.md`（历史文件已于2026-09-11清理） 与 [`reports/lance_training_code_map_20260903.md`](./reports/lance_training_code_map_20260903.md)。

### 6.6 Stage 4 在线 Rollout LoRA 实现冻结

2026-09-04 用户确认从官方 Lance 预训练权重开始挂接 fresh LoRA，暂不继承 stage2；训练时在线生成并替换全部历史 ViT 与最新 VAE source；一条链作为一个调度记录，所有 GT target 等权；梯度累计为 2；首轮 rollout CFG 固定 1；总步数 1,800、4 Epoch、warmup 20、cosine `1e-4 → 1e-5`、checkpoint 每 50 steps 保存且最近 4 份保留。condition dropout、CE、区域加权和 EMA 均关闭。

新的 chain 数据为 3,600/200/200 条，对应每 Epoch 13,483/754/763 个 target。真实五轮内存历史 CPU pack 得到 33,191 / 40,530 / 47,868 / 55,205 / 62,542 tokens，均小于 65,536，且每轮恰有一个 VAE source 和一个 VAE target。Stage 4 的内存输入位于独立动态行适配器中，Stage 2 路径式 Dataset 的冻结哈希保持不变。快速审查后已修复 adapter-only 推理漏载 base 与 rollout noise seed 随 rank 漂移，并在 trainer 内强制绑定关键模型/FSDP 参数；29 项聚焦 unittest、71 项完整 Lance unittest、单进程 adapter/optimizer/scheduler/RNG roundtrip、含基底文件哈希的 profile dry-run 和 `0011` patch apply-check 已通过。

正式入口采用双层 fail closed：launcher 和训练主入口都会拒绝未授权的 1,800-step 正式运行。早期 Job `122546/122547` 只验证了运行和 step 标量连续性；正式 Job `122549` 的 step50 checkpoint 随后暴露阻断错误：Adam 中 256/256 个 LoRA 模块已有更新，但导出的 adapter 仅 2/256 个 `lora_B` 非零。用户已停止该 Job，其 checkpoint 禁止恢复或推理。

checkpoint v5 改用 PyTorch optimizer-state 的 canonical FQN/shard 映射携带 live LoRA 参数，并按 `use_orig_params=True` 跳过本 rank 的空占位 shard。最终 Job `122758` 连续运行 3 steps；Job `122827` 运行 2 steps 并保存；Job `122836` 从 `starting_step=2` 恢复完成 step3。512/512 个 adapter tensor、2,048/2,048 个 optimizer tensor、8/8 个 RNG tensor 全部 bitwise 一致且最大差为 0，scheduler/cursor 相同，step2 时 256/256 个 `lora_B` 均非零。72 项 Lance unittest 继续通过，v2 profile 保持 `training_authorized=false`，等待用户重新授权从官方基座和 fresh LoRA 启动；不得从 `122549` 恢复。

尚未完成真实在线历史视觉审看和 held-out 质量评估。在线 full rollout 的 generated parent 与 rendered target 不共轨，loss 同时包含当前编辑与上一轮误差修复，不能仅解释为 exposure-bias 训练。实现与运行证据见 [`reports/datamake_stage4_online_rollout_lora_implementation_20260904.md`](./reports/datamake_stage4_online_rollout_lora_implementation_20260904.md) 和 [`reports/datamake_stage4_lora_resume_smoke_audit_20260904.json`](./reports/datamake_stage4_lora_resume_smoke_audit_20260904.json)，消融计划见 [`reports/datamake_lora_ablation_registry_20260904.md`](./reports/datamake_lora_ablation_registry_20260904.md)。

### 6.7 2026-09-04 Lance 文件整理

用户授权删除现行 v3/v5 路径已取代的测试产物和代码。清理移除了旧 v1 正式/Smoke、v2/v3 重型恢复 smoke、tiny 与 Stage 2 单卡 smoke Run、第一阶段全参 checkpoint、第二阶段 optimizer 恢复状态以及 Python cache；Lance `outputs/` 从约 163 GiB 降至约 31 GiB。当时保留轻量日志与报告等；其中tiny/Stage1结果的保留决定已被[2026-09-06清理](./reports/datamake_lance_storage_cleanup_20260906.md)替代。当前v3 Run、v2 full-rollout消融、teacher-forced实现、共享回归测试和官方基座仍保留。第二阶段模型以 SHA-256 固定的 base-only artifact 留在 `outputs/model_bases/datamake_dialogue_stage2_step3669/`。完整清单、不可恢复边界和保留理由见 [`reports/datamake_lance_storage_cleanup_20260904.md`](./reports/datamake_lance_storage_cleanup_20260904.md)。

### 6.8 2026-09-05 后续实验与探索登记

用户要求把既有 LoRA/history 消融与新的训练方向集中到同一入口。[`reports/datamake_lora_ablation_registry_20260904.md`](./reports/datamake_lora_ablation_registry_20260904.md) 现分为“可执行消融”和“下一探索方向”两部分；文件名为兼容已有证据链接继续保留。新登记不修改当前 v3 profile、数据或 Job，也不表示已授权实现。

下一探索方向按建议顺序为：

1. 当前轮目标参考图片：先比较 text-only、reference ViT、reference ViT+VAE；参考图必须在推理时存在并使用独立 appearance role，不能用同构图真值帧泄漏监督答案。
2. 任意历史父节点/分支编辑：把线性 chain 扩展为显式 `node_id/parent_node_id` 的编辑图；外部 resolver 解析轮次、相对位置、结构化属性或视觉描述，选中节点是唯一完整 VAE direct source，Lance 只接收其祖先路径 ViT。
3. 压缩历史 VAE memory：只在前两项暴露 ViT/当前源无法保存细节后进入；旧历史使用关键帧、编辑区域、latent delta、resampler 或按需检索，不允许多个完整 VAE 平等充当 `ref_source`。

分支目标必须从所选父节点的 UE 配置状态重新应用原子边并渲染；同一根编辑图全部分支必须位于同一数据 split。在线训练需按 `node_id` 保存 generated-node map，而不是只维护滚动的最新视频。全局生成顺序只用于时间引用和拓扑调度，实际 packed sequence 按所选父节点的祖先路径排列；不同节点的 VAE 不得沿时间维拼成一个伪长视频。

### 6.9 当前 LoRA checkpoint 独立视觉检查

2026-09-09新增[Stage6两臂step800同条件检查](./reports/datamake_stage6_step800_visual_sanity_20260909.md)。复用本节runner与review builder，按branch adapter schema加载理解+生成或仅生成LoRA；每臂相同6个输出，使用既有单H200交互allocation顺序执行，不影响排队的正式训练。新输出仍属于`outputs/multiturn_chat/`下游研究验证，不晋升数据发布或质量Gate。该报告维护最新结果；以下Stage5记录保留历史上下文。

2026-09-05，用户要求在正式续训过程中先检查最新可用 checkpoint。选择推理准备时最新完整的 `0000400`，在独立 `testqueue` allocation `123574/BFS9B74` 的一张 H200 上执行；正式四卡续跑 Job `123628/H64Y574` 不受影响。固定验证样例和结果见 step400 视觉检查（历史文件已于2026-09-11清理）。

在已有、确认空闲的单 GPU allocation 中，以 `xks_lance` 环境运行：

```bash
python 10_research/model_experiments/lance/scripts/run_datamake_lora_visual_sanity.py \
  --checkpoint 10_research/model_experiments/lance/outputs/training_runs/datamake_dialogue_one_step_x0_lora_r64_4xh200_v3/checkpoints/0000800 \
  --output-dir 10_research/model_experiments/lance/outputs/multiturn_chat/<unique_review_run>

# 推理全部完成后：媒体检查与本地浏览页面
python 10_research/model_experiments/lance/scripts/build_datamake_visual_sanity_review.py \
  --run-dir 10_research/model_experiments/lance/outputs/multiturn_chat/<unique_review_run>
```

推理只加载一次模型，复用现有 `MultiTurnChatEngine` 和 base-first LoRA loader，不修改 upstream sampler。三轮真正自回灌从初始视频开始，不提供中间 GT；另三个独立 case 使用真值历史、只生成 R2/R3/R5 最终目标。采样参数仍沿用第二阶段视觉 sanity：30 diffusion steps、CFG1、validation/noise seed42、global seed2025、timestep shift3.5、KV cache 与 requested frames50。推理 shift3.5 与训练 shift4 是两个不同参数。示例中的 step800 为 2026-09-06 可用检查点；执行前应选择仍被 retention 保留的完整检查点。

2026-09-06 修复训练/推理预处理不一致：该独立 runner 从 checkpoint contract 的 `dataset_config` 加载实际训练 YAML，在 packing 前覆盖 inference builder 的 VAE、ViT transform 与 frame sampler。当前 A/B 共用 VAE480、ViT448、12fps/max_duration6 配置；`video_360p` 只是 builder 初始化占位，单独使用该档位仍会得到错误的 ViT476，不能代替上述覆盖。对于本批 2560×1440 原视频（宽×高）：

| 路径 | VAE 像素尺寸 | ViT 像素尺寸 |
| --- | --- | --- |
| 训练与修复后独立推理 | 624×352 | 588×336 |
| 历史 step400 推理的 `video_480p` | 848×480 | 812×448 |

回灌的 624×352 视频保持同一 VAE 尺寸；150 帧/30fps 原视频采样为57帧，57帧/12fps历史不会继续丢帧。新增4项真实 transform/builder CPU 回归通过（本模块共7项，全部 Lance 共86项）；没有重新生成 GPU 视频，因此尚不能声称修复改善了视觉质量。历史输出保留为较高分辨率测试，不作为已匹配训练预处理的基线。通用 upstream CLI 档位和 A/B 冻结训练代码、配置均未改变。

同一 Run Root 保存 `manifest.json`（checkpoint/adapter hash、完整参数、`preprocessing` 中的实际训练 YAML/hash/transform/sampler、prompt、source/target/output 映射、加载核验、运行时间）、四份 `*.input.json`、六个生成视频与对应 transcript。后处理增加 `index.html`、三张比较图、`media_audit.json`，并物化少量原始/第二阶段参考视频到 `references/`，因此复制整个目录即可离线查看。它沿用现有 `outputs/multiturn_chat/` 下游研究输出类别，不晋升发布数据、不上传 W&B、不授权清理。完整媒体解码和加载一致性不能替代用户的视觉质量验收。

2026-09-06 用户进一步要求测试最新 checkpoint。独立单 H200 allocation `123858/8GS9B74/testqueue` 已完成 A800/A650 各六例的训练匹配分辨率对照；用户认为A800仍不尽人意。早先B350两次推理中断后曾暂停；用户重新要求测试B，step `123858.4` 已在5分36秒内完整完成六例，512/512加载核验、完整解码与三时点抽帧通过。B350在本组换装和机位保持上优于A800，但仍见动作局部模糊/重影，质量等待用户播放，不关闭L06/L08。下载`outputs/multiturn_chat/stage5_b_step350_trainres_review_20260906_1623/`即可同时查看原视频、prompt、GT、A800与B350；具体证据见 [最新检查点视觉报告](./reports/datamake_stage5_latest_visual_sanity_20260906.md)。review builder 支持 `--label` 与重复的 `--compare-run LABEL=RUN_DIR`，会核对相同 prompt/GT，并把各 Run 的视频和 manifest 复制到当前结果的 `references/`；同名视频按内容哈希区分。A650→A800用于同条件继续训练比较，A400旧分辨率与不同步数A/B都不作为单变量证据。本次没有Stage2无adapter的新分辨率对照，不能把B优势全部归因于新增LoRA训练。

### 6.10 Stage 2 基座对照的手动启动与续跑

`ABL-LORA-BASE-01/B` 复用同一 Stage 5 one-step trainer，只把冻结基座换成 `outputs/model_bases/datamake_dialogue_stage2_step3669/`，挂接 fresh LoRA。独立 profile 已允许用户手动启动；本轮不由 Codex 提交。精确参数、验证和未执行边界见 [准备报告](./reports/datamake_stage2base_lora_preparation_20260905.md)。

在 DataMake 根目录执行；首次明确用 `none`，防止继承终端中的旧恢复选项：

```bash
sbatch --export=ALL,RESUME_FROM=none \
  10_research/model_experiments/lance/jobs/datamake_dialogue_one_step_x0_lora_r64_stage2base_v1.sbatch

# 后续18小时分段续跑：上一任务已退出，且 B 自己已有完整 checkpoint
sbatch --export=ALL,RESUME_FROM=latest \
  10_research/model_experiments/lance/jobs/datamake_dialogue_one_step_x0_lora_r64_stage2base_v1.sbatch
```

脚本固定 B profile、申请 testqueue 单节点4H200/56CPU/1024G/18h；不复用当前 A 的 allocation。训练 Run Root 为 `outputs/training_runs/datamake_dialogue_one_step_x0_lora_r64_4xh200_stage2base_v1/`，日志为 `outputs/slurm_logs/dm_lance_x0_s2base_<job_id>.out/.err`，W&B stable Run ID 为 `datamake-dialogue-one-step-x0-lora-r64-stage2base-v1`。共享 released 媒体和 chain parquet，无需重新准备或复制数据。

Checkpoint 使用相同 v5 契约，每50步原子保存最近4份 adapter/optimizer/scheduler/cursor/RNG及最终步，不重复保存基座；基座本体必须保留用于恢复和推理。不能把 A 的 adapter 应用到 B，不能从旧 Stage 2 全参 optimizer 或 A 的 step400 续接。不要在同一 B Run 上同时提交 fresh/resume 两个任务。

启动前完整只读 dry-run：

```bash
/scratch/prj0000000275/jcy/.conda/envs/xks_lance/bin/python \
  10_research/model_experiments/lance/scripts/run_datamake_online_rollout_lora_training.py \
  --profile 10_research/model_experiments/lance/configs/datamake_dialogue_one_step_x0_lora_r64_stage2base_v1.json \
  --resume-from none --dry-run
```

准备时数据、训练代码和21个原 A 实现哈希不变，沿用 v3 四卡恢复证据；该准备阶段尚无新基座 GPU 训练结果。该作业仅训练/记录标量，不自动生成视觉评估。后续按 §6.9 使用 B 自身 checkpoint，其 training contract 会指定 Stage 2 基座；2026-09-06 的 review builder 已支持显式 `--label`，不再把 B 标成官方基座 A。

### 6.11 用户暂停两臂训练（2026-09-06 17:09）

用户在查看B350结果后要求暂停A/B，准备讨论修改。本次先核对Job归属、入口与checkpoint，再先取消排队的A `123860`，后取消运行中的B `123681`，避免B释放资源后A抢先启动。Slurm于17:09:10将两者记为`CANCELLED by 128993`；17:09:13 B batch已退出（`0:15`），随后两者均不在队列中。交互allocation `123858` 保持运行，没有被停止。

| 臂 | 取消前状态 | 保留恢复点 | 未保存进度 |
| --- | --- | --- | --- |
| A / Job123860 | `PENDING(Resources)`，未开始 | 本臂`checkpoints/0000800` | 本次排队任务没有新step |
| B / Job123681 | 最后完成393，17:08:29写出该步日志 | 本臂`checkpoints/0000350` | 完成351～393及取消时未完成的当前步不保留 |

本次只检查两份checkpoint的complete标记、必要文件大小和trainer cursor，无缺失/尺寸差异，`next_step`分别800/350；没有重复逐tensor深审计，也未额外保存、删除权重或修改训练代码/profile。B日志的shell `exit_status=0`不代表训练完成，应以Slurm取消状态和最后完成393为准。具体证据为`outputs/slurm_logs/dm_lance_x0_s2base_123681.out/.err`及上述`sacct`记录。当前“暂停”是取消作业释放资源，不是保留显存进程的`suspend`。等待用户说明修改内容，禁止自动重新提交；未来修改确定后再判断是兼容续跑还是另建实验，不默认沿用旧optimizer。

### 6.12 Stage6：Stage2配方下理解分支LoRA对照（800续跑已提交）

用户于2026-09-07要求两臂：S6-1将Stage2改为LoRA，S6-2只冻结理解参数。两份[配置与实现说明](./reports/datamake_stage6_stage2_lora_preparation_20260907.md)保留GT历史前缀、R5×3与区域加权；按用户后续要求统一改成官方预训练基座、LR3e-4、accumulation8与3000 optimizer-step预算；不延续Stage5单步pred_x0历史。消融由[统一登记](./reports/datamake_lora_ablation_registry_20260904.md)的 `ABL-LORA-UND-01` 拥有。

两臂均冻结base/ViT/VAE/embedding/lm_head；r64/alpha64/dropout0。S6-1更新理解和生成线性层adapter，S6-2仅更新生成adapter；两臂均保持理解激活不detach，只比较参数训练范围。保存已实现adapter-only+完整optimizer/scheduler/RNG/data cursor，一份共享基座；间隔100，最近4份、结束额外保存。旧600进程已按用户决定取消；restart1随后从零训练并取得完整checkpoint，当前续跑保持同一restart1输出/W&B身份。

两臂共同初始化已确认官方 `models/Lance/Lance_3B_Video/` + fresh LoRA/optimizer，配置不再留空。每卡micro batch1 × 4卡 × 8次累计 = effective batch32；3000次更新约96,000次目标样本暴露（R5×3有效数据约6.54次遍历），不是单epoch。保留warmup101，cosine最低LR按用户后续决定改为3e-5，checkpoint仍按completed optimizer steps计数。实现需保持Stage2每microbatch区域加权loss，再平均8次累计；裁剪/优化器/调度每8次才执行一次，数据游标支持跨遍历恢复。精确定义见准备报告的梯度累计部分。新运行入口已实现：[trainer（已退役，历史补丁）](./patches/legacy/0014-datamake-stage2-prefix-branch-lora.patch)、[branch LoRA](./lance/train/datamake_branch_lora.py)、[checkpoint bridge](./lance/train/datamake_stage2_lora_checkpoint.py)、[indexed prefix](./lance/train/datamake_stage2_lora_data.py)；外层[launcher](./scripts/run_datamake_stage2_lora_training.py)和[CPU真实输入检查](./scripts/inspect_datamake_stage6_runtime.py)由本节拥有，新增clone代码以[0014 patch](./patches/legacy/0014-datamake-stage2-prefix-branch-lora.patch)记录。两个[sbatch](./jobs/README.md)由用户提交：同任务先完成连续3步与2步保存/恢复第3步对比，通过后从fresh官方基座开始正式训练；不复用smoke参数、不将smoke计入3000步。推理脚本新增branch schema分派，仍是base先加载，标准采样未改。旧Stage5冻结源不变。

数据以已消费绝对microstep恢复，与worker预取游标隔离；Stage2 rank/shard顺序保留，预处理改用逐索引确定性随机种子。保存复用checkpoint-v5 live参数DCP映射，未使用UND适配器允许Adam step0。W&B记录区域/原始MSE、loss、clip前grad_norm、本次/下次LR、step_time、吞吐与峰值显存，不上传视频/权重/源码。后续正式checkpoint100/keep4/final-save，启动检查证据单独保留。原配置Jobs124136/124137四卡Gate均已通过并正式训练，但18h内无法到达600首存。[取消与重训记录](./reports/datamake_stage6_checkpoint_rescue_20260907.md)维护抢救失败、23:47:48用户取消及restart1从头命令；旧正式进度不能恢复。新增[0015 patch](./patches/legacy/0015-stage6-save-at-optimizer-boundary.patch)由本节拥有：新trainer在optimizer边界广播rank0的SAVE_AND_STOP文件决定，成功完整保存后才消费请求并退出，不在信号中保存；CPU已验证、四卡手动退出待验证，不作用于旧进程。新profile/source合同重新做同任务GPU Gate；从官方基座新建LoRA/Adam/scheduler/cursor，不迁移旧checkpoint或跳过合同检查，之后同一restart1完整checkpoint才用于latest续跑。L06/L08不关闭。

2026-09-08两臂400恢复准备及后续实际执行均已留证；9月9日Jobs125433/125434到时退出，最新完整恢复点800。用户已提交各自800续训，命令与状态见[恢复记录](./reports/datamake_stage6_checkpoint_rescue_20260907.md)，不要重复提交。两份800与当前profile/source合同匹配，显式恢复dry-run通过，原GPU Gate可复用；仍3000总预算、100步保存/keep4、原W&B身份。与此同时在独立单GPU执行本节标准视觉检查，不改训练；手动SAVE_AND_STOP退出仍未GPU验证。

## 7. 正式微调前 Gate

1. ~~`WF-90` 发布包通过，全部 `chains.json` 引用可解析，不能使用 6 视频样例替代。~~ 2026-08-31 已由 `JDS9B74/job118880` 独立候选态/发布态复验关闭。
2. ~~对 released 链按完整 `chain_id` 做确定性随机 3,600/200/200 split；对各 split parquet 做计数、链前缀、端点、路径、SHA-256 和集合间零泄漏审计。~~ 2026-08-31 已由 seed `2026` 正式 split、独立重建哈希和 19 项 Lance unittest 关闭。
3. ~~至少抽查每个轮次、语言、编辑轴、回退和返回起点样本的真实 Lance pack。~~ 2026-08-31 已以 5 个正式 train 样本覆盖 Round 1..5、英文、四编辑轴、rollback 与 return-to-start；最大 62,539 tokens 且 source-target 对齐全部通过。
4. ~~在用户提供的 GPU allocation 上完成 1–2 个 optimization step，确认 forward、MSE、backward、optimizer 和 checkpoint 都可用。~~ 2026-08-31 已由单 H200 2-step + full-state resume 关闭。
5. ~~正式 profile、数据 manifest、Lance commit/patch hash、随机种子、输出 Run Root 与 Slurm 脚本完成静态 Gate 并经用户确认。~~ 2026-08-31 已关闭；Job `119261` 又在实际计算节点关闭了 W&B online、Run Manifest、四卡连续 optimization 与首段 steady-state Gate。
6. 当前只使用 `dialogue`；`standalone` 单轮对照延后，不混采；必须独立开展真正多轮验证。上游训练脚本当前 validation 仍禁用，不能把 training loss 当成编辑质量 Gate。

Stage 4 checkpoint v5 与 Stage 5 one-step `pred_x0` 的四卡 optimization、adapter-only FSDP 保存恢复、逐 tensor 连续性和 step time Gate 均已关闭。旧 Job `122549` checkpoint 无效且不得恢复。2026-09-04 用户授权 v3，授权态 profile SHA-256 为 `315a8ef1cec83a16e3ab6f26c01de2d85e298c6145ecf327e85ef4a588637f7d`；Job `122959` 已在 `BFS9B74` 四张 H200 上从 step0 启动，W&B online 正常。正式 `0000050` 已通过 512 adapter、512 组 Adam moments、scheduler/cursor/四 rank RNG 深审计，256/256 个 `lora_B` 非零，训练继续越过 step100。当前执行状态已被§6.11的用户暂停覆盖；后续修改确定前不继续训练。已有质量判断见§6.9，不由training loss替代。

### 7.1 W&B 实时监控契约

正式训练使用 W&B `online`，小规模本地 smoke 默认仍为 `offline`。启动器显式支持：

```bash
--wandb-mode online \
--wandb-project datamake_lance \
--wandb-entity <user-or-team> \
--wandb-run-id <stable-run-id> \
--wandb-group first-batch-dialogue \
--wandb-job-type formal-train \
--wandb-tags first-batch,dialogue,full-param,4xh200 \
--log-every 1
```

`wandb_runid` 是跨 SLURM 重排与 checkpoint resume 的稳定 ID；不得在恢复时隐式创建另一个 Run。只有 global rank 0 上传聚合训练指标，当前标量包括：

- `mse`、`ce`、学习率和梯度 `total_norm`；
- MSE/CE token 数、样本数、allocated/reserved 显存；
- `steps_per_sec`、`step_time_sec`，以及 W&B 客户端采集的 GPU/CPU/主机系统指标。

启动器设置 `WANDB_DISABLE_CODE=true`、`WANDB_CONSOLE=off`、`WANDB_LOG_MODEL=false`。当前不调用 `wandb.Artifact`，因此不会自动上传 640 个原始训练视频、完整控制台日志、源码快照或约 68 GiB 的 checkpoint；本地 W&B 缓冲保存在对应 Run Root 的 `wandb/`。W&B 仍会保存训练参数与数据配置路径，用于 Run 追溯。

上游 `train/unified_train.py` 当前会强制关闭内建 validation，因此正式第一页只能实时反映训练稳定性，不能证明 held-out 编辑质量。Validation/Test 视频推理必须由后续独立评估入口执行；是否向 W&B 上传少量评估视频需单独冻结，不能把训练媒体批量同步作为默认行为。

Stage 4 的独立主循环额外记录 `mse_round_1..5`、各轮 target 数、全局 target/rollout 数以及 rollout/train 时间；同样不上传在线历史视频。其训练 MSE 仍不替代 held-out 自回灌质量评估。

online 模式在创建 Run Root 前检查 `WANDB_API_KEY` 或本机 `wandb login` 凭据。API key 不得写入 Git、训练 YAML、SLURM 文件、launcher metadata 或命令行参数。

## 8. 当前风险

- 多轮样本会反复读取共享视频；路径型 parquet 避免存储爆炸，但 `/scratch` 网络盘小文件和重复解码可能成为吞吐瓶颈。正式长训前应测 dataloader 吞吐，再决定是否做本地 shard、缓存或离线 latent。
- 480/448 是当前五轮 token 安全档，不代表最终最佳质量。提高分辨率前必须重新检查最长链 token 数和显存。
- 当前训练编码与 role-aware 推理布局已通过工程验证；已有少量 held-out 视觉检查，但尚不足以接受多轮泛化质量，状态保持 `partial`。
- 单卡全参最长上下文实测可运行，但 cached 显存约 129.3 GiB，余量有限；分辨率、帧率或 token 上限提高前必须重新跑 max-token optimization smoke。
- full-state 检查点实测约 68 GiB，其中单卡 FSDP full model 以约 28.4GB 保存、optimizer 约 44.4GB；正式训练前必须冻结保存间隔和清理策略。
- 第一阶段只训练 `dialogue`；`standalone` 保留为后续独立消融 Run，暂不生成、不混训，启用时必须单独记录数据 manifest 和采样配置。
- 正式 entity 为 `xingkeshuo-xi-an-jiaotong-university-`、project 为 `datamake_lance`；Job `119261` 已在实际 testqueue 计算节点通过非交互认证并同步 stable online Run。后续 resume 仍必须 fail-fast，不允许静默回退到 offline 或创建新 Run ID。
- Stage2共享Dataset的distributed/resume实现及补丁0008仍保留：这是冻结源码/重放依赖，不是仍在使用tiny训练数据。
- 上游 `unified_train.py` 会关闭内建 validation；当前 200-chain validation 和 200-chain test 是冻结的独立评估输入，不会在训练中自动产生视频质量曲线。首轮训练完成后必须另跑 held-out 推理，不能把 W&B training MSE 当成泛化结论。
- Stage 4 每个 optimizer step 需要对 8 条链逐轮做训练前向并为中间轮执行 30-step 在线采样，速度不能从旧全参约 17 秒/step 外推；正式训练时长必须以四卡 smoke 的实测数据重新估算。
- online-full 的生成 direct source 与 rendered GT target 可能不在同一精确轨迹，既可能训练纠偏，也可能增加重绘压力；本轮显式关闭区域加权，并把 teacher-forced、ViT-only 与基座/CFG 对照登记为后续消融。

## PEFT/DDP 性能优化（2026-09-09）

用户已授权实现以降低 LoRA 训练时间。技术细节、命令、完整恢复迁移、实测证据及未验证边界由[优化报告](./reports/datamake_ddp_peft_optimization_20260909.md)维护。该独立实现沿用 Stage6 两臂数值/数据配方，采用官方 PEFT 0.15.2 与 PyTorch DDP。原 Stage5/Stage6 FSDP 实现不改动，不能将旧 FSDP checkpoint 直接交给新 trainer。

以下入口生命周期均为 `validation_candidate`，Technical 所有者为本节；四卡验证通过前不是已接受的正式后端：

| 入口 | 责任 |
| --- | --- |
| [run_datamake_ddp_training.py](./scripts/run_datamake_ddp_training.py) | 合同、四卡连续/恢复 Gate、验证/基准/正式执行模式、完整墙钟记录 |
| [convert_datamake_fsdp_to_peft.py](./scripts/convert_datamake_fsdp_to_peft.py) | 只读 v5 源，官方 DCP 合并，adapter 与完整 Adam/RNG/scheduler/cursor 转换 |
| [prepare_datamake_ddp_variant.py](./scripts/prepare_datamake_ddp_variant.py) | all/alternate/none 激活重算独立配置和 Run 身份 |
| [analyze_datamake_ddp_benchmark.py](./scripts/analyze_datamake_ddp_benchmark.py) | 去 warmup、核对样本安排、分阶段耗时和显存比较 |
| [run_datamake_lora_visual_sanity.py](./scripts/run_datamake_lora_visual_sanity.py) | 新 PEFT schema 的推理加载，旧 schema 保持原行为 |
| [test_datamake_ddp_peft.py](./tests/test_datamake_ddp_peft.py)、[ddp_peft_distributed_check.py](./tests/ddp_peft_distributed_check.py) | PEFT/旧实现等价、完整状态/损坏检查、真实2进程 DDP 累计梯度参考 |
| [patch0016](./patches/legacy/0016-datamake-peft-ddp-training.patch) | clone 内 train/datamake_peft.py、datamake_ddp_checkpoint.py、datamake_ddp_train.py 的可重放源码 |
| [both profile](./configs/datamake_stage6_ddp_peft_both_branches_v1.json)、gen profile（历史文件已于2026-09-11清理）、[依赖](./configs/requirements_ddp_peft.txt) | 独立 DDP 配置，官方基座/原训练语义，默认全层重算 |
| [both job](./jobs/datamake_stage6_ddp_peft_both_branches.sbatch)、gen job（历史文件已于2026-09-11清理） | testqueue 四 H200、18h 上限，默认仅 validate；显式 train 才继续训练 |

新输出范围均为下游研究产物，生产者和所有者为本节，不新增或覆盖 WF-90 的 OUT 身份：

- `outputs/checkpoint_migrations/`：转换器生成的独立 v6 checkpoint。`checkpoint_complete.json` 绑定文件哈希，`migration.json` 记录原 checkpoint；默认保留，不能替代已验证的旧 v5 源。
- `outputs/optimization_diagnostics/`：CPU/GPU 检查、样本 trace、性能汇总及临时对照 profile；只作证据，不能直接恢复训练。默认保护，不自动清理。
- 新 DDP `outputs/training_runs/<profile run_name>/`：launcher 的 startup_validation、benchmarks、metrics/launch_segments、configs、W&B 和 checkpoint；新完整正式 checkpoint 仅在自身 Run 内滚动 keep4，旧 FSDP 目录不受影响。
- `runtime/peft_0_15_2/`：隔离的可重建依赖，由 requirements pin 管理、Git 忽略；HF cache 仍沿用 scratch 全局路径。

四卡 Gate 只接受匹配完整配置/代码/数据/版本合同的连续3更新与2+恢复第3更新对照。改变激活重算模式必须独立转换与验证，不能复用其他模式的 Gate。CPU和单卡证据不能关闭四卡 NCCL、最长上下文显存、性能收益或视觉质量边界。

2026-09-09 正确性审查后，按用户决定仅修复保存中断重试及 Gate 实际更新检查：rank0 为每次保存建立独立 `.STEP.incomplete-<随机后缀>` 并广播给所有 rank，写齐文件后原子发布；旧残留目录保留，不参与恢复选择，也不阻止重试。完整同名 checkpoint 仍拒绝覆盖。Gate 要求连续与恢复两臂相对 prefix 至少一个 generation LoRA-B tensor 实际改变，避免已有非零权重导致假通过。Adam 内部状态完整性强化、启动时逐 parquet 哈希核验暂缓；固定配方不变。

本次代码修改会使旧 DDP 转换候选及 Gate 的实现合同失效，四卡验证前需从实际保留的完整 v5 源重新转换到独立目录，不手工改旧合同。详见[修复与复查记录](./reports/datamake_ddp_peft_optimization_20260909.md#保存重试与实际更新检查修复)。

2026-09-09 用户已暂停原Stage6 Job126188/126189；SAVE_AND_STOP实际四卡保存退出通过，恢复点分别900/825。当前单H200同样本短测的执行与输出由[暂停与速度报告](./reports/datamake_lora_short_speed_20260909.md)维护，归属本节的optimization_diagnostics范围；不自动恢复原训练。

2026-09-09追加[算子级短对照](./reports/datamake_lora_operator_profile_20260909.md)，输出根为 `outputs/optimization_diagnostics/operator_probe_20260909/`，归属本节，脚本仅为诊断复现材料。确认新版基座权重梯度GEMM消失，位置处理的Python sum成为新的优化候选；生产代码/profile未修改，四卡Gate仍待执行。

2026-09-10已完成[位置编码求和优化](./reports/datamake_position_sum_optimization_20260910.md)：共享data/common.py采用Tensor.sum并在单次函数调用内复用计数，patch0017和tests/test_datamake_position_ids.py由本节维护。输出根为 `outputs/optimization_diagnostics/position_sum_20260909/`，保留为诊断证据；DDP合同新增该helper哈希，旧转换/Gate需重新生成。原FSDP入口/checkpoint/profile未改，公共helper影响其调用路径；四卡性能短测见下文，完整迁移/恢复验收仍待执行。

2026-09-10已完成用户授权的[四卡三步优化验证](./reports/datamake_four_gpu_optimization_20260910.md)。新增train/datamake_packed_batch.py、tests/test_datamake_packed_batch.py、tests/packed_batch_distributed_check.py及三个perf variant配置由本节维护；数据/输出根仍属于现有下游诊断范围。四组各12更新短测完成，无明显端到端提速；新DDP候选默认保留全检查点/batch1。packed的FP32对照达到阈值，BF16梯度等价检查仍未通过，保持实验配置。完整迁移/恢复Gate另行验证，不晋升正式后端。

2026-09-10用户进一步授权[H200更高显存配置短测](./reports/datamake_high_memory_sweep_20260910.md)。现有packed helper/launcher/variant生成器支持batch1/2/4/8，保持每卡八个prefix/更新；patch0019和新增mem配置由本节拥有。输出根`outputs/optimization_diagnostics/memory_sweep_20260910/`仍为既有诊断范围；初筛、缓存对照及12更新候选复测已完成。隔离cache_probe_train.py/run_cache_probe.py及相关调度、分析、审计脚本由本节作为诊断复现材料拥有；该实验阶段官方VAE源码未修改，后续接入见下一段。batch4存在已记录的mask编译限制，batch8无GPU验收；默认与正式训练不切换。

2026-09-10继续落实[缓存策略与高显存配置接入](./reports/datamake_vae_cache_integration_20260910.md)：本节拥有patch0020、tests/test_datamake_vae_cache.py及两臂mem retain配置。官方make_padded_latent新增可选empty_cache，DDP的vae_cache_policy由launcher校验、variant CLI生成、trainer传参并记录；实现合同加入common/val/utils.py。输出根`outputs/optimization_diagnostics/cache_integration_20260910/`及其中run_probe/run_validation和分析审计材料为本节既有诊断范围。CPU/补丁与正常入口四卡复测通过：理解＋生成off10、仅生成off14为最终高显存候选，gen off10保留对照；原正式两臂仍暂停。

2026-09-10用户选择仅优化padding，取消FlashAttention升级。本节拥有[本轮padding实现与续训报告](./reports/datamake_padding_optimization_20260910.md)、patch0021、tests/test_datamake_attention_padding.py、两份padding profile及job。DDP的attention_padding由launcher校验，variant生成器支持`--attention-padding fixed|minimal`，默认fixed；minimal把末尾独立pad缩到128对齐且保留sentinel。真实mask/位置/loss语义保持，metrics新增实际attention/padding token均值及策略。`outputs/optimization_diagnostics/padding_20260910/`中的验证脚本、结果、隔离转换checkpoint为既有诊断范围；GPU与正式恢复状态由本轮报告拥有。

本轮正式转换由`outputs/checkpoint_migrations/padding_final_20260910/{both,gen}/`拥有，恢复状态与提交回执见padding报告。恢复验证器只排除trace中的peak_allocated_gib/peak_reserved_gib，仍比较全部训练字段；双分支检查器修复前执行的GPU证据经AST/19文件哈希及迁移状态一致性证明后重新验证，原执行合同与当前验证合同均保留，详见报告证据。

2026-09-10用户结束新DDP两臂时，使用上述SAVE_AND_STOP在optimizer边界保存并退出，987/893完整性检查及Slurm正常退出通过；请求与验证结果归本节padding诊断范围，精确状态由padding报告/Status维护。无新授权不得自动续训。

停止后的训练正确性复核由padding诊断目录audit_stopped_training.py执行，读取完整运行日志、源/最终adapter/Adam/scheduler/RNG及manifest，结果stopped_training_correctness_audit.json由padding报告维护；属于只读审计，不作为启动训练入口。

2026-09-22 CFG四卡推理任务：见[提交说明](reports/datamake_cfg4_submission_20260922.md)。入口`jobs/datamake_cfg4_gt1650.sbatch`，worker `scripts/run_datamake_cfg4.py`，结果审核` scripts/build_datamake_cfg4_review.py`；CPU检查完成，GPU验证待运行，未提交。
