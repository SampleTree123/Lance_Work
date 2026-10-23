# 保留训练模板与混合数据接入位置

2026-09-11后续更新：混合索引和成对窗口适配已经实现，见[新数据及profile绑定](./datamake_coinve_mixed_dataset_20260911.md)。下文“未接入”描述的是配置清理时点；新实验profile及GPU启动仍待准备。

> 日期：2026-09-11。范围：用户要求精简配置、作业入口和报告，保留 Stage5 B，以及理解侧＋生成侧同时训练 LoRA、每100步保存的模板。所有者：[训练接入](../training_integration.md)。本次未接入新数据、未启动训练。

## 两个主入口

| 用途 | Profile | Job |
| --- | --- | --- |
| Stage5 B，保留历史训练与恢复能力 | [stage2base_v1](../configs/datamake_dialogue_one_step_x0_lora_r64_stage2base_v1.json) | [Stage5 B](../jobs/datamake_dialogue_one_step_x0_lora_r64_stage2base_v1.sbatch) |
| 下一轮混合训练的推荐复制模板：双分支 LoRA、优化后 DDP | [padding_both](../configs/datamake_stage6_padding_both_20260910.json) | [padding both](../jobs/datamake_stage6_padding_both.sbatch) |

Stage5 B冻结基座为Stage2 step3669，只训练生成侧adapter，one-step pred_x0历史，每50步保存；保留原配置和实现文件哈希，不把它改成双分支或100步策略。其完整200/250/300/350仍在。

双分支主模板已经包含：官方PEFT0.15.2、DDP、r64/alpha64、`freeze.understanding_adapters=false`、全基座冻结；每100个optimizer step保存、结束保存、保留最近4份完整adapter/Adam/scheduler/RNG/游标；BF16基座、FP32 adapter；4卡、每卡batch1、累计8/global batch32；末10层不做梯度检查点、VAE缓存retain、attention末尾padding最小128对齐。共享位置编码归约优化由保留源码提供。使用FlexAttention，没有启用FlashAttention替换或batch>1。

## 为什么还保留依赖参考文件

- DDP加载器实际读取 `ddp.source_profile` 指向的[原双分支配方](../configs/datamake_dialogue_stage2_recipe_lora_r64_both_branches_v1.json)，逐项比较数值和数据语义；不能删除。
- [DDP初始双分支配置](../configs/datamake_stage6_ddp_peft_both_branches_v1.json)用于优化回归的基线；[Stage2配方](../configs/datamake_dialogue_stage2_r5x3_region_v1.json)用于双分支继承检查和Stage5 B基座来源说明。
- [Stage5 A原配方](../configs/datamake_dialogue_one_step_x0_lora_r64_v3.json)以及A的两个job属于Stage5 B冻结哈希/配方对照依赖；保留文件不代表保留A训练结果或建议启动A。
- [共享formal-launcher测试配方](../configs/datamake_dialogue_first_batch_v1.json)和对应job仅为共享回归依赖；不作为新训练入口。

因此`configs`保留7份JSON：2份主配置＋5份配方/回归依赖，另有PEFT requirements。源码、补丁链和运行环境全部保留。只删不相关实验文件，不通过改写Stage5 B冻结合同来规避依赖。

## 后续混合数据应改哪里

1. 复制双分支主profile和它的`ddp.source_profile`，为新实验分别命名，并让新profile引用新source_profile；原保留模板不覆盖。当前加载器会比较两者的data/model/optimization/history/lora/freeze/initialization及run训练参数，修改数据时须同步这两份配置。
2. 生成新的混合训练数据YAML、sampling manifest、split manifest及parquet，更新`data`中的路径、SHA256、条数、分片和轮次采样描述；读取清单必须与实际生成的数据一致。CoinVE共同时间窗口的适配仍须在实际Dataset入口实现，单改profile无法完成这一部分。
3. 为新profile设置独立的`profile_id`、`run.run_name`、`wandb.run_id`，以及按新数据量确定的训练步数和学习率预算；source_profile需使用不同的run/W&B身份，并保持参与语义比较的训练参数一致。保留双分支LoRA及`checkpoint.completed_step_interval=100`。
4. 复制主job并改`--profile`和日志/作业名称，profile中的`slurm.job_script`指向新job。新训练从官方基座开始，传`RESUME_FROM=none`；旧900/825/987/893已经删除，不能用历史迁移路径。
5. 先运行新profile的`--resume-from none --mode validate --dry-run`检查文件及合同，再在已分配GPU上做真实混合样本的加载、loss/backward和启动验证。主job支持显式`RESUME_FROM=none`，默认`DDP_MODE=validate`；正式训练需显式`DDP_MODE=train`，本次未提交。

启动器还保留原Stage6的数据和batch合同检查；若新混合数据改变了Dataset schema、时间裁剪参数或索引规则，应先完成适配并验证，不能通过删除合同检查来强行启动。

## 清理和验证记录

删除16份配置、5个job、6份不相关报告：仅生成侧候选、显存/batch短测配置、早期Stage3/全rollout入口、旧推理原型及A400报告等。逐文件SHA256和保留配置哈希见[清理清单](./lance_training_templates_cleanup_20260911.json)。历史文档中指向已删文件的链接改为明确的清理说明，历史训练事实不重写。

回归中的废弃freeze-und配方对照改为保留双分支原配方与最终DDP模板的一致性检查，保留checkpoint每100步等断言；底层两分支训练能力和实现代码不变。

验证结果由清理清单的`validation`字段记录：覆盖保留模板的126项Lance CPU回归、两个真实launcher的dry-run、保留job的bash语法，以及文档导航检查。dry-run不执行GPU forward/backward，不能代替后续混合数据GPU短测。
