# Lance 项目进度核对：2026-10-11

核对日期：2026-10-11，Asia/Singapore。先核对当前工作区、Slurm、训练目录及推理产物；同日后续完成可选单张 ViT 参考图代码与小尺寸 GPU 工程验证。没有重新启动正式训练，不把文件存在或 smoke 成功等同于质量验收。

Technical owner：[训练接入](../training_integration.md)。架构详解：[当前训练架构](datamake_current_architecture_20261011.md)。本报告替代旧报告中的“当前运行中”“待提交”等实时状态；旧报告仍保留当时的实现和验证证据。

## 1. 当前训练与恢复点

`outputs/training_runs/` 当前只有以下两组正式训练。两者均从官方 Lance 基座开始、UE＋CoinVE 混合、八卡 DDP、理解＋生成双分支 r64 LoRA、关闭区域 loss 加权；都未达到 3000 更新预算。

| 项目 | GT 历史 | 整链 pred_x0 历史 |
| --- | --- | --- |
| run 目录 | `datamake_coinve_mixed_ddp8_lora64_both_no_region_gtfresh_v1` | `datamake_coinve_mixed_ddp8_lora64_both_chain_pred_x0_no_region_v2` |
| 作业 | 145518 | 133706 |
| Slurm 结果 | TIMEOUT，2026-09-23 18:45:04 | TIMEOUT，2026-09-13 09:27:30 |
| 最近日志 optimizer step | 1186 | 889 |
| 最新完整 checkpoint | **1150** | **850** |
| 保留完整 steps | 1000 / 1050 / 1100 / 1150 | 700 / 750 / 800 / 850 |
| W&B ID | `dm-coinve-mix-ddp8-both-noreg-gtfresh-v1` | `dm-coinve-mix-ddp8-both-chain-predx0-v2` |
| 历史来源 | GT | 当前监督 forward 产生的 detached pred_x0 |

本次核对了 complete 状态和 manifest 所列文件的存在；没有重新逐 tensor 载入并哈希全部 checkpoint。两个 run 均有已通过的启动连续/恢复 Gate。以后续训仍需由入口验证当前实现合同、数据与基座，不把历史 Gate 当成任意新代码的通行证。日志最后一步不等于可恢复步数；超时后未保存部分需要重算。

截至本次 `squeue -u stuchengyou` 查询，只有交互作业 159069 在运行，没有正式训练或 CFG 推理作业在运行。本次没有提交、取消或续训任何作业。

## 2. 旧 GT1650 与当前 GT1150 的区别

旧 GT run `datamake_coinve_mixed_ddp8_lora64_both_no_region_v1` 已被删除，旧完整 2350 checkpoint 不在当前训练目录。旧 prefix pred_x0 v1、Stage5 B 等也不再是当前保留 run；不能沿用 9 月早期“仅保留 Stage5 B”的说明。

旧 GT1650 **推理 adapter 快照**仍在：

- `outputs/multiturn_chat/mixed_step1650_complete_review_20260912/inference_adapter/`
- `outputs/optimization_diagnostics/cfg_gt1650_shared_snapshot/`

快照不包含完整 optimizer、scheduler、各 rank RNG 与数据游标，不能用来无损续训。当前 GT1150 属于重新开始的 `gtfresh_v1`，不是原 GT1650 的后续，也不能仅凭 1150/1650 这两个数字推断质量。

## 3. 已完成的推理实验

### CFG 四卡消融

作业 145517 于 2026-09-23 01:07:01 至 03:11:51 完成，`COMPLETED / 0:0`。使用旧 GT1650 推理快照。

| 分组 | text CFG | ViT CFG | 视频数 |
| --- | ---: | ---: | ---: |
| baseline | 1 | 1 | 28 |
| text3 | 3 | 1 | 28 |
| text5 | 5 | 1 | 28 |
| vit3 | 1 | 3 | 28 |
| vit5 | 1 | 5 | 28 |

每组为 3/4/5 轮合成链、各自 GT 历史与自回填模式，加 4 个 CoinVE 单轮案例。共 140 段视频、95 个 conversation；五组各四个 rank 的生成清单和媒体审计已落盘。

页面：[完整 CFG 对照](../outputs/multiturn_chat/mixed_cfg_gt1650_job145517/index.html)。执行与实现边界：[四卡任务报告](datamake_cfg4_submission_20260922.md)。运行与媒体完整性通过不等于已经证明 CFG 每个分支与独立参考实现数值等价。

用户观察：提高 text CFG 的编辑变化明显；提高 ViT CFG 时更倾向保持源视频、编辑减弱。这是当前小样例的定性观察，还未完成 text3 / text5 的逐例优劣判定或复合 CFG 消融，不能宣布全数据最佳参数。

### 真实数据 prompt 拆分

使用相同旧 GT1650；4 个真实案例，4 段整句输出与 9 段拆分后顺序输出，共 13 段。

页面：[整句与拆分对照](../outputs/multiturn_chat/coinve_prompt_split_gt1650_20260922/index.html)。用户观察为拆分并未改善，后续子指令响应弱。保留为小样例结论，不据此修改训练文本或宣称所有复合指令均应保持整句。这里不引用未经成对裁剪口径重新核验的原视频逐帧数值作为证据。

## 4. 已采用与未采用的优化

已采用：官方 PEFT 注入、DDP 仅同步可训练参数、梯度累计延后同步、位置编码求和优化、选择性梯度检查点、VAE 缓存保留、最小 attention 尾部 padding。

当前双分支配置为 **0–25 层开启检查点、26–35 层关闭**，每卡 batch1、累计4、8卡 global32；不是全层重算，也不是每卡 batch4。训练仍用 FlexAttention，没有实施讨论中的训练 FlashAttention 替换。推理原有 FlashAttention 路径另论。

历史短测收益及范围由[优化报告](datamake_padding_optimization_20260910.md)维护；不能把不同样本、单卡/四卡、局部算子的提速百分比相加，更不能当作当前八卡混合训练的精确预计耗时。

## 5. 当前计划与下一步

第一批数据 WF-90 保持 released；主计划仍为 `PLAN-2026-08-LANCE-DIALOGUE-FIRST-FINETUNE`，L10 工程优化完成，L06 / L08 质量验收未关闭。

同日后续新增 L11：[可选单张 ViT 参考图](datamake_optional_reference_image_20261011.md)。保留直链、纯文本编辑及源/目标 VAE，新增每轮可选参考图；小尺寸真实推理和正式 Mixed/Packed/VAE forward/backward、AdamW 工程通路通过，正式训练未启动。现有训练集没有参考图样本，下一步先核对输入合同、确定真实参考样例及效果对照，再建立独立 GT 数据/profile。分支编辑、参考图 VAE、多视角和动作参考仍未实施。

既有 checkpoint 与 profile 没有改写；但实现代码 hash 已变化，旧 adapter 加载成功不表示能按新代码严格恢复完整旧训练。旧续训需另行解决合同版本，不能跳过检查。参考图学习后的质量和八卡正式尺度验证仍待后续，既有 CFG 页面质量分析继续归 L06/L08。

## 6. 本次文档核验

架构整理阶段已同步 HANDOFF、根/Lance/报告导航、训练接入、PROJECT_STATUS、PROJECT_STATE、当前Plan与CFG报告，完成当时的目录重建和132项核心检查。后续参考图扩展再次同步输入合同、ADR-0018、L11及对应导航；新增代码检查、对抗修复与真实GPU证据由[参考图报告](datamake_optional_reference_image_20261011.md)汇总，不将先前文档验收冒用为新增功能验收。没有删除输出、制作新数据或提交正式训练。
