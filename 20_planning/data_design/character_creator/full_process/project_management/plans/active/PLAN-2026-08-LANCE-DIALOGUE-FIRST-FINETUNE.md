# PLAN-2026-08 Lance Dialogue 首轮正式微调

> 文档 ID：`PLAN-2026-08-LANCE-DIALOGUE-FIRST-FINETUNE`
> 文档类型：`plan`
> 生命周期：`current`
> 计划状态：`current`
> 影响阶段：Lance 下游训练接入
> 完成条件：已执行阶段可追溯，并对当前LoRA/历史策略和理解分支对照取得可审计的 GPU 技术 Gate 与 held-out 多轮结论
> 最近核验：2026-10-23

## 目标

2026-10-12[官方对照审查](../../../../../../../10_research/model_experiments/lance/reports/datamake_official_training_comparison_20261012.md)补充L06/L08/L10/L11工程证据：当前部分检查点小尺寸梯度一致；GT/整链不是严格单变量对照，旧checkpoint需版本相容后才能续训。该审查不关闭学习后质量验收，也不授权新正式训练。

以已发布的第一批编辑链及后续CoinVE真实编辑数据验证Lance混合训练、多轮编辑和历史策略。保留冻结split和可追溯输入；已执行训练、工程Gate和少量样例不能替代视觉质量验收。

当前事实见[2026-10-11进度](../../../../../../../10_research/model_experiments/lance/reports/datamake_progress_20261011.md)。旧Stage5/Stage6和原GT训练状态仅作历史，不从旧报告自动恢复。

## 需求与落实

| ID | 需求 | 影响阶段 | 状态 | 证据入口 |
| --- | --- | --- | --- | --- |
| `L01` | 冻结并验证第一批 released 输入 | Lance 下游训练 | `completed` | [WF-90 状态](../../status/workflows/WF-90.md) |
| `L02` | 按 chain_id 确定性随机划分，并审计零泄漏、覆盖与重建一致性 | Lance 下游训练 | `completed` | [训练接入与数据契约](../../../../../../../10_research/model_experiments/lance/training_integration.md) |
| `L03` | 冻结历史四卡全参配置及 W&B、验证、checkpoint retention | Lance 下游训练 | `completed` | [配置索引](../../../../../../../10_research/model_experiments/lance/configs/README.md)；Stage1 配方仅作历史回归依赖，不是当前运行入口 |
| `L04` | 提交并完成第一阶段正式训练与工程 Gate | Lance 下游训练 | `completed` | 历史执行已完成；结果按用户决定删除，现不再提供原始结果复查，见 [清理记录](../../../../../../../10_research/model_experiments/lance/reports/datamake_lance_storage_cleanup_20260906.md) |
| `L05` | 单卡 tiny 辅助收敛诊断 | Lance 下游训练 | `completed` | 历史执行完成，实验已退役；配置、报告与产物不再保留，见 [清理记录](../../../../../../../10_research/model_experiments/lance/reports/datamake_lance_storage_cleanup_20260906.md) |
| `L06` | held-out推理、曲线与checkpoint质量复核 | Lance下游训练 | `in_progress` | [CFG与prompt拆分完成状态](../../../../../../../10_research/model_experiments/lance/reports/datamake_progress_20261011.md)；有用户定性观察，未形成完整质量验收 |
| `L07` | R5×3 与训练期 VAE latent 区域加权的第二阶段全参训练 | Lance 下游训练 | `completed` | [Stage2 结果](../../../../../../../10_research/model_experiments/lance/reports/datamake_dialogue_stage2_results_20260903.md)；只保留 step3669 base-only 权重，不能恢复已删除的全参 optimizer/scheduler |
| `L08` | r64 LoRA历史条件及理解分支训练范围验证 | Lance下游训练 | `in_progress` | 两组混合训练均通过启动恢复Gate并已运行至超时；[当前架构及比较边界](../../../../../../../10_research/model_experiments/lance/reports/datamake_current_architecture_20261011.md)；当前GT与整链存在采样/归约差异，质量待验收 |
| `L09` | 任意历史父节点/分支编辑与压缩历史 VAE memory | Lance 下游训练 | `queued_design_recorded` | [探索登记](../../../../../../../10_research/model_experiments/lance/reports/datamake_lora_ablation_registry_20260904.md)；2026-10-18已讨论显式起点/祖先路径/分开训练/推理回退，见[ADR-0019](../../decisions/ADR-0019-EXPLICIT-HISTORY-SOURCE-ROUTING.md)；分支仍未实现，参考图归L11，压缩历史memory仍暂缓 |
| `L10` | 优化LoRA训练计算与通信，官方PEFT/DDP、可选激活重算、完整状态迁移与同条件吞吐验证 | Lance下游训练 | `completed` | [最终padding与累计效果报告](../../../../../../../10_research/model_experiments/lance/reports/datamake_padding_optimization_20260910.md)：官方PEFT/DDP、位置求和、off10/off14与VAE缓存、尾部128对齐完成；126项CPU、真实梯度、四卡同样本短测、900/825完整迁移与连续/恢复验收通过，历史优化续训已执行并结束；当前混合训练状态由Status维护。padding本身没有显著额外提速证据；batch>1 BF16/编译限制保留为未采用实验，质量验收独立归L06/L08 |
| `L11` | 可选单张 ViT 参考图与无图直链编辑共存；训练/推理角色正确且有图指导有效 | Lance 下游训练与推理 | `in_progress` | [实现及验证](../../../../../../../10_research/model_experiments/lance/reports/datamake_optional_reference_image_20261011.md)、[ADR-0018](../../decisions/ADR-0018-OPTIONAL-SINGLE-VIT-REFERENCE.md)；代码、CPU回归、对抗修复、小尺寸真实GPU推理/训练工程验证完成；现有数据无参考图，正式训练与学习后质量待真实样例，不据此关闭本需求 |
| `L12` | 按属性组织多图/动作视频VAE参考，独立角色与上下文预算，历史压缩/删除消融 | Lance下游训练与推理 | `queued_design_recorded` | [2026-10-22方案](../../../../../../../10_research/model_experiments/lance/reports/datamake_vae_references_branch_plan_20261022.md)与[ADR-0020](../../decisions/ADR-0020-VAE-MULTI-REFERENCE-BRANCH-DIRECTION.md)；2026-10-23确认仅当前轮参考、旧参考不重复输入；历史ViT压缩保留为首选、参数未定；ViT三组/历史prompt两组消融只登记暂不执行，未实现；不以旧L11单图工程证据代替验收 |

## 当前执行顺序

2026-10-22用户新增源码整理要求已完成：从官方最新提交迁移必要修改，验证后删除旧clone；[迁移报告](../../../../../../../10_research/model_experiments/lance/reports/datamake_source_migration_20261022.md)拥有实现清单、145项回归、GPU工程验证与删除收据。该维护任务不改变训练数据、模型目标或下列质量验收顺序；八卡正式恢复Gate未由单卡诊断替代。

1. 当前先讨论L09起点选择架构，细化显式指向标签、输出格式、理解上下文及参数隔离方式；决定和例子见[总记录](../../../../../../../10_research/model_experiments/lance/reports/datamake_architecture_decisions_20261018.md)。本轮只记录，不实施分支代码。
2. L11参考图代码与既有工程证据保留；缺少符合需求的数据，按用户要求暂不继续实际测试。学习后效果、无图回归与正式训练均待后续。
3. L06/L08质量验收未关闭；旧训练续训另行安排，须解决代码/checkpoint合同兼容。参考图VAE、多视角、动作视频、历史VAE memory与多父节点合并不在当前实施范围。

## 不包含

不改 released 数据、不重新混采已暂缓的合成 standalone、不删除结果；CoinVE 单轮混入仍沿用既有合同。本轮参考图实现不包含数据制作、正式训练、分支编辑、参考图 VAE、多视角、动作视频参考和历史 VAE memory；内容时序专项清洗也未追加执行。

## 停止条件

- split泄漏、输入哈希不一致或样本/目标角色合同被破坏。
- OOM、NaN、异常loss或连续/恢复Gate不能复现。
- 模型、optimizer、RNG或游标状态不一致。
- 拟执行范围超出用户已授权工作；按实际需要澄清，不把已有授权重复作为阻塞。

历史实现与清理证据由[报告索引](../../../../../../../10_research/model_experiments/lance/reports/README.md)维护。WF-90已发布、L10完成、L06/L08未验收以及本计划current状态保持不变。
