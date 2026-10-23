# 脚本导航

2026-10-22源码已整理。当前入口：GT为 `run_datamake_ddp_training.py`，整链为 `run_datamake_chain_pred_x0_ddp_training.py`，推理为 `run_datamake_lora_visual_sanity.py`/`run_datamake_cfg4.py`；公共环境和参数映射为 `datamake_runtime.py`。源码核验/重建使用 [rebuild_lance_checkout.py](rebuild_lance_checkout.py)，见[迁移报告](../reports/datamake_source_migration_20261022.md)。

旧全参、Stage5、Stage6 FSDP入口归入 [legacy](legacy/README.md)，原路径只保留退役提示。下方9–10月导航是历史来源；不代表这些旧训练器仍能启动。参考图、数据构建、展示及诊断工具继续保留。

最近核验：2026-10-11。脚本实现与输出的唯一 Technical owner 为[训练接入](../training_integration.md)。当前 GT fresh 和整链 pred_x0 v2 已实际训练并超时停止；精确状态见[进度](../reports/datamake_progress_20261011.md)，下方9月阶段描述仅作历史。

## 可选单张参考图：active 入口

| 脚本 | 职责 |
| --- | --- |
| [build_multiturn_conversation.py](build_multiturn_conversation.py) | 构建直链推理 JSON，每轮可选单张图，`-` 表示无图 |
| [prepare_datamake_reference_training.py](prepare_datamake_reference_training.py) | 审计新参考图数据与路径/hash，准备独立 GT profile；不制作数据、不提交作业 |
| [verify_datamake_reference_gpu.py](verify_datamake_reference_gpu.py) | 小尺寸真实模型、参考图输入及 CFG 推理工程验证 |
| [verify_datamake_reference_training_gpu.py](verify_datamake_reference_training_gpu.py) | 正式 Mixed/Packed/VAE 通路的 forward/backward 与单步更新验证，不写训练 checkpoint |

字段、准确命令与局限见[参考图实现报告](../reports/datamake_optional_reference_image_20261011.md)。证据归既有 optimization_diagnostics；旧模型可加载不表示参考编辑质量已通过，新实现也不自动兼容旧严格续训合同。

## 既有入口与历史来源

新增：[run_datamake_pred_x0_ddp_training.py](./run_datamake_pred_x0_ddp_training.py) 为 detached pred_x0 八卡入口，复用原DDP启动/恢复Gate；技术所有者为[训练接入](../training_integration.md)，行为与命令见[报告](../reports/datamake_pred_x0_ddp8_training_20260912.md)。

新增[完整链选例](./prepare_datamake_chain_review.py)、[两种回填的四行展示](./build_datamake_chain_review.py)；现有推理runner通过`--suite`使用新清单；[真实样例采样helper](./datamake_coinve_review_media.py)复用训练共同窗口，服务推理与浏览预览。准确命令及输出边界见[准备报告](../reports/datamake_complete_chain_review_preparation_20260911.md)。

混合数据新增[构建器](./build_datamake_coinve_mixed_data.py)和[全量/真实媒体检查器](./inspect_datamake_coinve_mixed_data.py)，均为active，所有者及运行方式见[混合数据报告](../reports/datamake_coinve_mixed_dataset_20260911.md)。

既有 [PEFT/DDP launcher](./run_datamake_ddp_training.py)、[完整状态转换](./convert_datamake_fsdp_to_peft.py)、[检查点层与batch配置](./prepare_datamake_ddp_variant.py)和[基准分析](./analyze_datamake_ddp_benchmark.py)。生命周期与输出所有者为[训练接入的 PEFT/DDP 章节](../training_integration.md#peftddp-性能优化2026-09-09)；既有优化 Gate 已完成，不能替代新增参考图数据的正式训练验收。

原 Stage5/Stage6 属历史实现，其目录与恢复点按当前 Status 核对；本文是阅读导航，不是启动授权。

| 类别 | 主要文件 |
| --- | --- |
| Stage6两臂启动 | [run_datamake_stage2_lora_training.py](./run_datamake_stage2_lora_training.py)：同任务GPU Gate后正式训练；[CPU检查](./inspect_datamake_stage6_runtime.py) |
| Stage5旧LoRA启动 | [run_datamake_online_rollout_lora_training.py](./run_datamake_online_rollout_lora_training.py)，当前仍暂停 |
| 当前视觉检查 | [run_datamake_lora_visual_sanity.py](./run_datamake_lora_visual_sanity.py)、[build_datamake_visual_sanity_review.py](./build_datamake_visual_sanity_review.py) |
| 数据构建 | [build_datamake_dialogue_splits.py](./build_datamake_dialogue_splits.py)、[build_datamake_chain_training_data.py](./build_datamake_chain_training_data.py)、[build_datamake_multiturn_training_data.py](./build_datamake_multiturn_training_data.py) |
| 数据/LoRA/恢复审计 | [inspect_datamake_online_rollout_pack.py](./inspect_datamake_online_rollout_pack.py)、[inspect_datamake_multiturn_training_data.py](./inspect_datamake_multiturn_training_data.py)、[inspect_datamake_generation_lora.py](./inspect_datamake_generation_lora.py)、[verify_datamake_online_rollout_resume.py](./verify_datamake_online_rollout_resume.py) |
| 数据视图与对照 | [build_datamake_history_views.py](./build_datamake_history_views.py)、[build_datamake_teacher_forced_conversation.py](./build_datamake_teacher_forced_conversation.py) |
| 日志/像素诊断 | [analyze_datamake_training_log.py](./analyze_datamake_training_log.py)、[compare_videos_framewise.py](./compare_videos_framewise.py) |
| Stage2全参历史 | [run_datamake_formal_training.py](./run_datamake_formal_training.py)、[build_datamake_round_weighted_train.py](./build_datamake_round_weighted_train.py)、[run_datamake_stage2_local_smoke.py](./run_datamake_stage2_local_smoke.py) |
| 通用全参smoke兼容 | [run_datamake_training.sh](./run_datamake_training.sh)，仅smoke/resume；tiny预设和subset builder已删除 |
| 早期推理原型 | [run_multiturn_chat.sh](./run_multiturn_chat.sh)、[build_multiturn_conversation.py](./build_multiturn_conversation.py)、[contextual_video_edit.py](./contextual_video_edit.py)、[run_video_edit.sh](./run_video_edit.sh) |

早期原型的验证边界见[报告索引](../reports/README.md)。Stage6新加独立LoRA/索引数据入口，旧Stage5实现保持不变；共享补丁与小型mock测试不能按名称含tiny一并删除。

早期原型的示例`inputs/`与既有`logs/generated_configs/`已按用户要求清理。旧脚本需自行提供视频/prompt路径，运行时可能重建生成配置目录；当前LoRA视觉脚本直接消费正式validation和released媒体，不依赖这两个目录。
