# 项目当前状态

2026-10-28服务器展示任务完成本机验证；独立展示包与服装问题的用户最新反馈见[服务器状态](SERVER_SYNC_STATUS.md)及[展示归档](../../../../../../00_engine/render_pipeline/docs/CHAIN_SHOWCASE_20261028.md)。本轮不改变Lance主计划或模型架构决定。

> 文档 ID：`STATUS-PROJECT`
> 文档类型：`status`
> 生命周期：`current`
> 状态来源：[PROJECT_STATE.json](PROJECT_STATE.json)、当前目录、Slurm与实验报告
> 当前计划：`PLAN-2026-08-LANCE-DIALOGUE-FIRST-FINETUNE`
> 最近核验：2026-10-23架构决定与文档；工程回归为2026-10-22、历史训练结果快照为2026-10-11，Asia/Singapore

## 当前结论

2026-10-23新增[分阶段媒体规格算例](../../../../../../10_research/model_experiments/lance/reports/datamake_stage_specific_media_specs_20261023.md)：用户提议生成source/history统一低规格ViT、理解只用标准ViT与文字，参考VAE分图/视频规格；已核对实际48通道VAE与2048维主干、预算公式，数字只是候选。尚未冻结或实施，消融继续暂缓。

2026-10-23讨论顺序更新：用户要求将历史ViT、其他视频ViT与参考视频VAE的采样、分辨率和预算统一讨论。保留压缩历史的首选不变；此前优先减少帧数尚未确认，不先固定该参数策略。只更新设计记录，消融继续暂缓。

2026-10-23服务器文档与UE执行工作由独立分支维护，见[同步状态](SERVER_SYNC_STATUS.md)。本轮修正文档和路径；旧生产引擎原路径当前不存在，后续渲染需重新确认构建。模型架构由另一对话继续，本页模型决策和主计划保持原有权威。

2026-10-23逐项冻结架构：用户确认生成仅使用当前轮参考，旧参考只存档、不重复输入；后续已确认生成阶段首选压缩历史ViT，具体参数未定；ViT完整/压缩/删除和历史prompt保留/移除登记为未来消融，暂不执行。下一项仅讨论历史ViT压缩方式与幅度，见[方案第5节](../../../../../../10_research/model_experiments/lance/reports/datamake_vae_references_branch_plan_20261022.md#5-历史压缩持久化完整不等于每次全量输入)。本轮只更新文档，无模型实现或训练。

2026-10-22新增[多参考VAE与分支讨论方案](../../../../../../10_research/model_experiments/lance/reports/datamake_vae_references_branch_plan_20261022.md)：用户明确属性参考规则、参考VAE与先tool_call后生成。当前单图ViT实现未改；历史压缩/删除、旧参考保留及预算为待讨论建议，新增L12记录，不启动训练。

2026-10-22按用户要求完成官方4baeee0源码迁移，当前路径由新clone接替；公共配置、数据、状态与pred_x0 helper已拆离历史训练器。单一补丁/源码锁重建通过，当前CPU回归145项通过，五例真实GPU推理迁移前后latent完全相同，小尺寸GPU训练、两种真实训练入口各两个单卡诊断步、双进程Gloo检查通过。旧clone归档校验后已删除，见[迁移报告](../../../../../../10_research/model_experiments/lance/reports/datamake_source_migration_20261022.md)。原模型、媒体、训练结果与checkpoint保留，未提交正式训练；八卡运行Gate仍需实际allocation执行。

2026-10-22完成[官方上游与LoRA生态核查](../../../../../../10_research/model_experiments/lance/reports/datamake_lance_upstream_lora_survey_20261022.md)，为官方基座小实验准备。官方main比本地基线多一项7月安全修订，未发现新训练核心或可核实的公开Lance LoRA训练版本；没有修改运行环境或启动实验。

2026-10-21新增[多图/参考视频与五轮序列预算](../../../../../../10_research/model_experiments/lance/reports/datamake_multi_reference_token_budget_20261021.md)。用户提出未来放宽单图限制；已核对当前65K预算与ViT/VAE长度公式，给出累积参考和分角色采样估算。多参考尚未实现，未作GPU测试，媒体数量/采样/保留政策未定。

2026-10-18补充[Tool Calling与历史定位训练调研](../../../../../../10_research/model_experiments/lance/reports/datamake_source_routing_tool_call_research_20261018.md)：已查阅官方SFT/工具协议与多视觉指代资料，完成本地理解CE接入边界核对；推荐结构化SFT并保留直接ID对照，方案待确认，未实施或训练。

2026-10-18按用户要求保留参考图初步实现，因合适数据未就绪暂不继续实际测试；当前转为讨论显式历史起点选择。普通prompt默认-1、生成仅使用选中节点祖先路径、保存真实parent、理解与生成分别训练、推理非法输出回退留痕等设计已记录，分支仍未实现；详见[架构讨论总记录](../../../../../../10_research/model_experiments/lance/reports/datamake_architecture_decisions_20261018.md)。

2026-10-12完成[当前训练与官方代码对照](../../../../../../10_research/model_experiments/lance/reports/datamake_official_training_comparison_20261012.md)。部分检查点与关闭/全开在真实小尺寸样例中MSE及全部LoRA梯度一致。当前GT1150/chain850完整合同与工作树不同，严格恢复预检将拒绝；续训前需恢复相符代码或完成显式迁移验证。GT与整链的loss归约不同，不能当作只改变历史来源的单变量对照。另两项配置边界不在当前dropout=0、规范媒体根的正式配方中触发。没有修改训练实现、profile或提交正式训练。

第一批数据已发布，WF-90/GATE-90保持关闭。Lance已完成混合数据接入、双分支PEFT/DDP优化和两种历史方案的正式训练启动；现存GT fresh和整链pred_x0 v2均已超时停止，没有正式训练正在运行。旧报告里的“GT继续”“整链待提交”“仅保留Stage5 B”已过期。

2026-10-11 先完成架构与状态整理，随后按用户要求实现[可选单张 ViT 参考图](../../../../../../10_research/model_experiments/lance/reports/datamake_optional_reference_image_20261011.md)。CPU 回归、独立对抗审查和小尺寸真实 GPU 推理/训练通路已通过；现有训练数据没有参考图监督，尚未训练或验收参考编辑效果。原训练 profile 与保存结果未改写，未提交正式作业。精确 run、checkpoint、日志步数、W&B 身份见[进度快照](../../../../../../10_research/model_experiments/lance/reports/datamake_progress_20261011.md)。

## 活动对象

| 对象 | 当前值 |
| --- | --- |
| 当前计划 | [Lance首轮微调及后续LoRA](../plans/active/PLAN-2026-08-LANCE-DIALOGUE-FIRST-FINETUNE.md)，保持current |
| 活动批次 | [BATCH-001-FIRST-DATA](batches/BATCH-001-FIRST-DATA.md)，released不可原地改写 |
| Workflow | [WF-90](../../workflow/WF-90-QA-PACKAGE-RELEASE.md)已关闭；下游质量L06/L08仍in_progress |
| GT混合训练 | gtfresh_v1；最新完整1150，最后日志1186；job145518 TIMEOUT |
| 整链pred_x0 | chain_pred_x0 v2；最新完整850，最后日志889；job133706 TIMEOUT |
| GPU执行 | 2026-10-22查询只有交互allocation170881；本轮运行迁移诊断，无新正式训练提交 |
| 旧GT1650 | 仅推理adapter快照；非当前fresh run、非完整恢复点 |
| CFG四卡实验 | job145517 COMPLETED；五组140视频及媒体审计完成 |
| 单张参考图扩展 | L11 工程验证完成、质量待真实数据；GT 前缀支持可选单张静态 ViT 参考；未启动正式训练 |

## 当前能力与质量边界

- UE节点/原子边/编辑链发布证据由[WF-90状态](workflows/WF-90.md)拥有；本轮不重开数据生产Gate。
- UE＋CoinVE引用式合并及共同5秒裁剪已用于训练；总时长差不会被独立全视频缩放，但内容时间错位等数据风险尚未专项清洗。
- 当前双分支配置采用部分检查点、VAE缓存保留与最小padding；batch仍为每卡1。L10工程优化已完成，历史性能范围不外推成固定八卡epoch耗时。
- 整链pred_x0复用当前监督forward，生成历史detach。它是noisy-GT代理，不等同30步纯噪声在线历史；采样和loss归约也与GT前缀不同。
- CFG和prompt拆分的工程产物已齐全。用户观察text CFG增强编辑、ViT CFG更偏保持源视频；真实prompt拆分未见改善且后续指令弱。均为当前小样例的定性观察，不足以关闭L06/L08。
- 可选参考图与无图轮次共存；图片不成为源/目标 VAE，不参与额外目标 loss。复用现有 ViT CFG，尚无独立参考强度、参考图 VAE、多视角或动作视频参考。分支编辑已进入设计讨论，尚未实施；现有代码仍保持直链。
- 新参考图实现改变代码 hash。旧 adapter 的加载和小尺寸通路测试已通过，但不能推导旧完整 checkpoint 可在新合同下严格恢复；新训练需独立数据绑定和身份。

## 输出入口

- [项目进度与恢复点](../../../../../../10_research/model_experiments/lance/reports/datamake_progress_20261011.md)。
- [模型、数据与训练架构](../../../../../../10_research/model_experiments/lance/reports/datamake_current_architecture_20261011.md)。
- [参考图问题回答、实现、对抗审查及验证](../../../../../../10_research/model_experiments/lance/reports/datamake_optional_reference_image_20261011.md)。
- [CFG页面](../../../../../../10_research/model_experiments/lance/outputs/multiturn_chat/mixed_cfg_gt1650_job145517/index.html)。
- [真实prompt拆分页面](../../../../../../10_research/model_experiments/lance/outputs/multiturn_chat/coinve_prompt_split_gt1650_20260922/index.html)。
- [Lance分类导航](../../../../../../10_research/model_experiments/lance/README.md)、[训练接入](../../../../../../10_research/model_experiments/lance/training_integration.md)。

## 验证与限制

既有训练状态以 Slurm 查询及磁盘 manifest 为据。参考图扩展已执行小尺寸真实 GPU 推理和无图/有图 forward、backward、单步 AdamW 验证，证据由新报告汇总；这不是完整规模训练、学习后质量或八卡连续/恢复验收。complete 标记与文件齐全不等于任意代码可续训。旧训练被删除后保留的报告和推理视频只能支持其各自范围。

既有UE驱动565阻塞与580 Validation-layer受限风险继续保留，见[服务器执行说明](../../technical/rendering_release/SERVER_EXECUTION.md)。本次没有复核新的集群策略，不将历史队列规则写成新的管理员确认。

## 唯一下一步

逐项固定L09/L12架构：讨论按阶段/任务定义媒体规格，评估生成source/history统一低规格ViT、理解标准ViT与参考VAE独立规格；确认候选数上界和具体参数。已有形状/长度算例，参数未冻结，ViT及历史prompt消融仍暂缓；新架构尚未实施。
