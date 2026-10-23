# 报告导航

最近核验：2026-10-11。当前作业、保留结果和唯一下一步由项目 Status 与下列进度报告维护；后续历史分类不代表当前仍在运行或仍保留对应 checkpoint。

## 当前阅读入口

- [2026-10-23分阶段媒体规格：形状与长度算例](datamake_stage_specific_media_specs_20261023.md)：理解标准ViT、生成统一低规格ViT、参考VAE分规格的候选方案；5候选视觉39060 token，具体参数未冻结、未实施。

- [多参考VAE、分支编辑与上下文预算方案](datamake_vae_references_branch_plan_20261022.md)：2026-10-22用户确定属性参考规则及VAE方向；2026-10-23确认只输入当前轮参考；历史ViT压缩保留为首选、参数未定；ViT三组和历史prompt两组消融登记待后续，暂不执行，尚未实施。

- [2026-10-22官方基线迁移、必要修改与验证](datamake_source_migration_20261022.md)：当前代码/重建合同入口；历史训练器与补丁已分区。

- [官方更新与公开LoRA实现核查](datamake_lance_upstream_lora_survey_20261022.md)：2026-10-22官方main较基线多一项7月安全修订；未找到可核实的Lance专用公开LoRA训练入口，第三方推理/量化与训练支持分开记录。

- [官方与当前实现的文件路径地图（HTML）](datamake_code_reading_map_20261021.html)：内嵌SVG、可放大，并附PNG版本；用于按训练/推理入口阅读，不依赖Mermaid渲染。

- [多图、参考视频与五轮编辑：序列预算分析](datamake_multi_reference_token_budget_20261021.md)：2026-10-21新需求讨论；ViT/VAE token估算、65K预算与分角色采样建议，尚未实施多参考支持或做GPU测试。

- [历史起点选择：Tool Calling、视觉指代与训练方法调研](datamake_source_routing_tool_call_research_20261018.md)：2026-10-18补充，推荐单工具结构化SFT，记录直接ID/指针选择对照及本地接入边界；仅建议，未实施。

- [架构讨论总记录：参考图、历史起点选择、分开训练与推理回退](datamake_architecture_decisions_20261018.md)：2026-10-18当前讨论入口，明确已确定规则与待选细节；参考图等待数据，分支尚未实现。

- [2026-10-12当前训练与官方代码对照审查](datamake_official_training_comparison_20261012.md)：部分检查点真实GPU梯度对照、loss目标差异、旧checkpoint恢复合同及配置边界。

- [可选单张 ViT 参考图：三个问题回答、代码合同、对抗修复与 GPU 验证](datamake_optional_reference_image_20261011.md)。已实现工程通路，真实参考图监督与质量仍待后续；未提交正式训练。
- [2026-10-11项目进度与checkpoint边界](datamake_progress_20261011.md)。
- [当前训练架构详解：输入输出、注意力、LoRA、loss、历史与优化](datamake_current_architecture_20261011.md)，含3张SVG；[浏览器阅读版](datamake_current_architecture_20261011.html)内嵌全部图示。
- [CFG四卡任务及完成状态](datamake_cfg4_submission_20260922.md)。
- [真实数据整句与拆分prompt对照](datamake_coinve_prompt_split_gt1650_20260922.md)。
- [混合数据组织与共同5秒窗口](datamake_coinve_mixed_dataset_20260911.md)。
- [整链pred_x0实现与验证](datamake_chain_pred_x0_ddp8_20260912.md)。
- [性能优化及证据范围](datamake_padding_optimization_20260910.md)。

## 历史实现与实验记录

以下配置、保存周期、checkpoint和执行状态按各报告日期理解。旧GT、Stage5、Stage6目录的历史恢复命令不能未经核对直接使用。

## Stage5 B

- [B基座与配置](./datamake_stage2base_lora_preparation_20260905.md)、[B350视觉结果](./datamake_stage5_latest_visual_sanity_20260906.md)。
- [Stage2基座结果](./datamake_dialogue_stage2_results_20260903.md)、[来源配方](./datamake_dialogue_stage2_preparation_20260901.md)。
- [one-step历史实现](./datamake_stage5_one_step_x0_history_20260904.md)、[恢复审计](./datamake_stage5_one_step_x0_resume_smoke_audit_20260904.json)。
- [共享链训练与checkpoint-v5实现](./datamake_stage4_online_rollout_lora_implementation_20260904.md)、[底层恢复证据](./datamake_stage4_lora_resume_smoke_audit_20260904.json)：B复用的实现依据，不是保留旧full-rollout训练入口。

## 理解＋生成LoRA，每100步保存

- [最终优化实现与效果](./datamake_padding_optimization_20260910.md)、[双分支配方](./datamake_stage6_stage2_lora_preparation_20260907.md)。
- [PEFT/DDP](./datamake_ddp_peft_optimization_20260909.md)、[位置归约](./datamake_position_sum_optimization_20260910.md)、[VAE缓存](./datamake_vae_cache_integration_20260910.md)。
- [速度短测](./datamake_lora_short_speed_20260909.md)、[算子定位](./datamake_lora_operator_profile_20260909.md)、[四卡检查点/batch实验](./datamake_four_gpu_optimization_20260910.md)、[显存实验](./datamake_high_memory_sweep_20260910.md)：保留优化取舍与数值边界，短测配置已精简。
- [每100步保存与历史恢复事故](./datamake_stage6_checkpoint_rescue_20260907.md)、[双分支800视觉对照](./datamake_stage6_step800_visual_sanity_20260909.md)：原始checkpoint已删除，结论及视频保留。
- [训练代码路径](./lance_training_code_map_20260903.md)、[相关消融登记](./datamake_lora_ablation_registry_20260904.md)。

## 清理与恢复边界

- [仅保留B训练结果](./lance_keep_stage5b_cleanup_20260911.md)、[逐文件清单](./lance_keep_stage5b_cleanup_20260911.json)。
- [前一轮验证大文件清理](./lance_storage_cleanup_20260911.md)、[清单](./lance_storage_cleanup_20260911.json)。
- [本轮配置/报告清理清单](./lance_training_templates_cleanup_20260911.json)。
- [09-06存储清理](./datamake_lance_storage_cleanup_20260906.md)、[清单](./datamake_lance_cleanup_manifest_20260906.json)、[09-04迁移记录](./datamake_lance_storage_cleanup_20260904.md)：保留基座来源和历史文件去向。
