# 配置导航

2026-10-22源码迁移后，现行训练配方及W&B/run身份原样保留；源码合同已更新，旧checkpoint仍需严格恢复检查。当前入口以[工作区README](../README.md)和[迁移报告](../reports/datamake_source_migration_20261022.md)为准，以下阶段配置用于配方追溯。

最近核验：2026-10-11。GT fresh 与整链 pred_x0 v2 已实际训练并超时停止，当前恢复点由[进度快照](../reports/datamake_progress_20261011.md)维护。以下9月配置保留作来源配方，不把历史“运行中/待提交”视为当前状态。

新增[可选单张 ViT 参考图](../reports/datamake_optional_reference_image_20261011.md)已完成工程验证。配置准备使用 [prepare_datamake_reference_training.py](../scripts/prepare_datamake_reference_training.py)：要求显式提供完整新数据绑定，审计图像和 parquet，生成独立 run/W&B 身份以及关闭正式启动授权的 profile。现有训练数据没有参考图样本，不能仅复制旧 profile 就声称在训练参考能力。旧训练 profile 保持不变，代码 hash 改变后不能直接严格续训旧 checkpoint。

## 历史配置与配方来源

2026-09-12记录：[整链pred_x0复用v2](../reports/datamake_chain_pred_x0_ddp8_20260912.md)采用固定32目标整链窗口及全局token归约，保留R5×3、不额外添加后轮loss权重；当日提交前状态已被10月进度快照取代。

新增：[八卡 detached pred_x0 历史配置](./datamake_coinve_mixed_ddp8_lora64_both_pred_x0_no_region_v1.json)，仅改变GT八卡对照的历史来源；recipe为合同依赖。见[实现与启动](../reports/datamake_pred_x0_ddp8_training_20260912.md)。

推理专用：[完整链展示清单](./datamake_mixed_complete_chain_review_20260911.json)，用于新UE validation链的双回填对照及CoinVE单轮例子；它不是训练profile。见[准备报告](../reports/datamake_complete_chain_review_preparation_20260911.md)。

当前新增：[八卡混合双分支LoRA](./datamake_coinve_mixed_ddp8_lora64_both_no_region_v1.json)，关闭区域loss加权，每50步保存/keep4；[配置与验证](../reports/datamake_coinve_ddp8_training_config_20260911.md)。其recipe文件仅作合同依赖。

2026-09-11按用户要求精简。两个主配置可供后续使用；其余文件仅作为冻结合同、配方或共享回归依赖。完整修改位置见[训练模板与混合数据接入](../reports/lance_training_templates_20260911.md)。

| 历史模板 | 用途 |
| --- | --- |
| [Stage5 B](./datamake_dialogue_one_step_x0_lora_r64_stage2base_v1.json) | Stage2基座、生成侧LoRA、one-step历史的来源配方；B350结果已不在当前保留范围 |
| [双分支优化版](./datamake_stage6_padding_both_20260910.json) | 下一轮混合数据推荐模板：PEFT/DDP，理解＋生成LoRA，每100步保存，off10/retain/minimal padding |

## 依赖参考，不作为新实验入口

| 文件 | 保留原因 |
| --- | --- |
| [双分支原配方](./datamake_dialogue_stage2_recipe_lora_r64_both_branches_v1.json) | DDP的source_profile，加载器实际读取并比较训练语义 |
| [双分支DDP基线](./datamake_stage6_ddp_peft_both_branches_v1.json) | 优化实现回归输入 |
| [Stage2配方](./datamake_dialogue_stage2_r5x3_region_v1.json) | 双分支配方继承和B基座来源 |
| [Stage5 A配方](./datamake_dialogue_one_step_x0_lora_r64_v3.json) | B冻结合同及对照回归依赖；A结果已删除 |
| [共享formal配方](./datamake_dialogue_first_batch_v1.json) | 共用launcher回归依赖；无Stage1结果 |
| [PEFT依赖](./requirements_ddp_peft.txt) | 官方PEFT0.15.2环境依赖 |

新实验必须同步数据路径/哈希与 source_profile 语义，使用独立 run/W&B 身份。参考图实验遵循上方专用准备入口；旧 Stage6 恢复点已删除，当前 GT fresh/整链恢复必须另核实现合同。本轮只完成新能力的代码与工程验证，未启动正式训练。
