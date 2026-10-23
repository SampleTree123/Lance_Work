# Lance / DataMake 训练工作区

最近核验：2026-10-22。当前源码已迁至官方 `4baeee0`，详见[迁移清单与验证](reports/datamake_source_migration_20261022.md)。日常使用只需看下面的当前入口；旧阶段启动器、测试、补丁分别归入 `scripts/legacy/`、`tests/legacy/`、`patches/legacy/`。

源码唯一安装合同是 [patches/current/source_lock.json](patches/current/source_lock.json) 和同目录的一份完整补丁；[重建/核验工具](scripts/rebuild_lance_checkout.py)支持 `--verify-only`，也支持 `--official-only` 创建未经本地修改的官方实验目录。不要重新叠加旧的26份补丁。当前训练不再导入旧训练器或手写LoRA实现，旧adapter读取/转换库保留作兼容。

已有模型/数据/输出路径保留。训练结果快照见[2026-10-11进度](reports/datamake_progress_20261011.md)，模型语义见[训练架构详解及SVG图](reports/datamake_current_architecture_20261011.md)。旧完整checkpoint需核对实现合同才能续训；本轮不自动启动正式训练。

2026-10-11已完成[可选单张 ViT 参考图实现](reports/datamake_optional_reference_image_20261011.md)：纯文本轮次与有参考图轮次共存，小尺寸 GPU 推理和训练工程验证通过。现有数据仍无参考图监督，新正式训练未启动；分支编辑未实施。

本目录维护 DataMake 专用 Dataset、patch、profile、测试和训练/推理入口；上游 clone、大型权重与数据不进入 Git。

## 当前入口

| 用途 | 配置 | 作业入口 |
| --- | --- | --- |
| GT历史混合双分支LoRA | [GT profile](configs/datamake_coinve_mixed_ddp8_lora64_both_no_region_v1.json)，当前run为gtfresh_v1 | [GT八卡](jobs/datamake_coinve_mixed_ddp8_lora64_both_no_region_v1.sbatch) |
| 整链pred_x0混合双分支LoRA | [chain v2 profile](configs/datamake_coinve_mixed_ddp8_lora64_both_chain_pred_x0_no_region_v2.json) | [整链启动器](scripts/run_datamake_chain_pred_x0_ddp_training.py) |
| 旧GT1650快照CFG对照 | [执行报告](reports/datamake_cfg4_submission_20260922.md) | [四卡CFG](jobs/datamake_cfg4_gt1650.sbatch) |
| 可选单张参考图实验准备 | [输入合同与验证边界](reports/datamake_optional_reference_image_20261011.md) | [数据审计与独立配置准备](scripts/prepare_datamake_reference_training.py)，需显式绑定含参考图的数据 |

两组训练均每50步保留最近4份。源配方、实现合同、run/W&B身份和恢复点必须一起核对；本页列入口不表示自动提交授权。旧Stage5 B和Stage6是历史实现参考，其训练目录已不在当前保留范围。

## 导航

- [训练接入与实现所有权](training_integration.md)、[配置](configs/README.md)、[Slurm](jobs/README.md)、[报告索引](reports/README.md)。
- [脚本](scripts/README.md)、[补丁链](patches/README.md)、[源码地图（历史）](reports/lance_training_code_map_20260903.md)。
- [项目Status](../../../20_planning/data_design/character_creator/full_process/project_management/status/PROJECT_STATUS.md)。

## 目录职责与保留边界

| 目录 | 内容 |
| --- | --- |
| lance | 最新官方基线加当前适配；内部导航为 `DATAMAKE.md` |
| scripts、tests | 当前启动/工具与回归；legacy子目录仅供历史追溯 |
| patches/current、patches/legacy | 唯一可重建源码合同 / 已退役历史补丁链 |
| runtime | 固定PEFT依赖，不存放训练数据或权重 |
| models | 官方视频基座/ViT；HF cache用用户指定scratch位置 |
| outputs/model_bases | 历史Stage2 base-only模型，不包含完整全参恢复状态 |
| outputs/training_runs | GT fresh、整链pred_x0 v2两个现存run；详情见进度报告 |
| outputs/training_data | 派生parquet/YAML引用原媒体，不复制视频 |
| outputs/multiturn_chat | 推理视频、媒体审计和展示页面；GT1650快照仅供推理 |
| outputs/optimization_diagnostics、outputs/slurm_logs | 性能/工程证据与日志；不把诊断快照当作完整checkpoint |

本次参考图扩展未删除、移动既有结果，也未改写旧训练 profile。代码实现合同已变化，旧 adapter 可加载不等于旧完整 checkpoint 可按新合同严格续训。历史清理记录描述当时动作；当前存储事实以进度报告和目录核对为准。
