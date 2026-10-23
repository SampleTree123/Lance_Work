# Stage 5 最新检查点视觉复核（2026-09-06）

> 状态：`A_user_review_below_expectation; B_generated_media_passed_visual_partial_pending_user_review`；A800/A650已完成，用户认为A800仍不尽人意；用户重新要求测试B后，B350在step123858.4完整完成六例。
> 实现所有者：[训练接入 §6.9](../training_integration.md#69-当前-lora-checkpoint-独立视觉检查)
> 范围：L06/L08 少量固定 validation 样例，不是完整 benchmark 或泛化 Gate。

## 目的与对照

用户要求查看更多训练后最新 checkpoint 的视觉效果。准备时 A 最新完整检查点为800，B为350；额外使用仍保留的 A650，隔离继续训练与预处理修复的变化。

| Run | 基座 / checkpoint | 作用 |
| --- | --- | --- |
| `stage5_a_step800_trainres_20260906` | 官方 Lance + A LoRA800 | 当前 A 最新结果 |
| `stage5_b_step350_trainres_review_20260906_1623` | Stage 2 step3669 + B LoRA350 | 本次完整 B 结果；与 A800 同推理条件比较 |
| `stage5_b_step350_trainres_20260906_retry1` | Stage 2 step3669 + B LoRA350 | 被取消，未产生完整结果；不纳入比较 |
| `stage5_a_step650_trainres_20260906` | 官方 Lance + A LoRA650 | 同条件650→800继续训练对照 |
| `stage5_v3_step400_visual_sanity_20260905` | 官方 Lance + A LoRA400 | 已保留旧结果，分辨率不同，仅作历史参考 |

上述 Run 均位于 `outputs/multiturn_chat/`。A800/A650与本次B350各生成6个视频：同一三轮链的真实自回灌3例，外加 R2 action、R3 outfit、R5 outfit 的真值历史诊断。原视频、完整 prompt、GT 和实际 source 映射随 manifest 保存。早先B350首次仅完成R1、retry1未完成任何视频，两次中断输出继续只作故障证据，不混入新的完整结果。

## 固定推理参数

- 30 diffusion steps、CFG1、validation/noise seed42、global seed2025、推理 timestep shift3.5、KV cache。
- 使用 checkpoint 对应训练 YAML：VAE480/ViT448，实际624×352/588×336（宽×高），12fps、57帧。
- 与旧 step400 的848×480输出不同；不把旧/新差异全部归因于训练步数。
- 每次先加载本 checkpoint 指定基座，再加载512个 LoRA tensor，并逐 tensor 验证 BF16加载值；不加载 optimizer，不修改训练/W&B。
- 使用当前独立交互 allocation `123858/8GS9B74/testqueue` 的一张已确认空闲 H200；该 allocation 18小时内，截止2026-09-07 08:50:37。不使用 B 的训练 GPU，不新增或取消任何 Slurm 任务。

## 运行与输出

A800 日志：`outputs/slurm_logs/dm_lance_a_step800_trainres_123858_20260906.log`；A650同规则命名。B重试日志为`outputs/slurm_logs/dm_lance_b_step350_trainres_retry1_123858_20260906.log`。最终可下载目录为 [`outputs/multiturn_chat/stage5_a_step800_trainres_20260906/`](../outputs/multiturn_chat/stage5_a_step800_trainres_20260906/)，约58MiB；[index.html](../outputs/multiturn_chat/stage5_a_step800_trainres_20260906/index.html) 已包含SOURCE / GT / 旧A400 / A650 / A800、三时点抽帧和参考manifest副本。63个本地页面引用全部存在，下载整个目录即可离线播放；B中断输出不在页面中。

```bash
python 10_research/model_experiments/lance/scripts/build_datamake_visual_sanity_review.py \
  --run-dir 10_research/model_experiments/lance/outputs/multiturn_chat/stage5_a_step800_trainres_20260906 \
  --label 'A step800' \
  --compare-run 'A step400 (old resolution)=10_research/model_experiments/lance/outputs/multiturn_chat/stage5_v3_step400_visual_sanity_20260905' \
  --compare-run 'A step650=10_research/model_experiments/lance/outputs/multiturn_chat/stage5_a_step650_trainres_20260906'
```

## 验证与结论

A800在15:29:37～15:35:21完成，整组约5分44秒；自回灌三轮114.36秒，TF R2/R3/R5分别47.13/50.20/69.11秒，峰值allocated显存22.04GiB。512/512 adapter tensor与BF16加载值一致，256/256个LoRA B非零。六个视频完整解码均为624×352、57帧、12fps、4.75秒；首尾缩略帧平均绝对像素差31.14/29.84/31.59/30.85/31.76/37.72，证明存在时间变化，不代表动作或时序质量通过。

A800的10%/50%/90%抽帧相较旧A400少见额外人物，动作有明显响应，R5换装生成粉色裙装并更接近GT机位；但动作轮仍转动机位/改变背景构图，AR R3有衣物/身体局部异常，TF R3仍保留橙衣绿短裤并漂移到正面站姿，男装目标跟随仍弱。R5 prompt只要求女式裙装，不指定GT的白色款式，因此不能把颜色不同单独判为指令失败。旧A400分辨率不同，上述观察不能全部归因于训练步数。

首次CPU后处理收到SIGTERM/exit143，已在当前allocation的CPU上重跑成功，不重新生成A800。B350首次尝试完成自回灌R1后也收到SIGTERM/exit143，无Python异常栈，allocation123858仍为RUNNING且GPU已释放；原因未确定，部分输出与manifest保留并标记interrupted。A650改由同一allocation的显式Slurm step运行，时限30分钟，不额外申请GPU。

A650显式step `123858.2` 正常 `COMPLETED/0:0`，在15:40:14～15:45:44完成，整组5分30秒；自回灌110.63秒、TF R2/R3/R5为42.12/49.84/70.02秒，峰值allocated显存22.04GiB，512/512加载核验与256/256非零LoRA B通过。六个视频均完整解码为624×352、57帧、12fps。

B350随后通过step `123858.3` 重试一次，15:46:16启动、15:48:16被取消；`sacct` 明确记录 `CANCELLED by 128993`、ExitCode `0:9`，即本账户发起取消，而不是30分钟时限退出。无法据此确定是哪个终端/进程发起，也没有OOM或模型Python异常栈。512/512加载核验已通过，但尚未完成首个视频。两次中断manifest已标记`interrupted`，保留轻量故障证据，不继续重试；已询问用户是否有其他终端结束推理，尚未收到确认。

15:49核验当前GPU显存占用0MiB，交互allocation仍有效；A训练Job123860仍等待资源，B训练Job123681仍RUNNING，均未被本次操作修改。89项Lance与132项核心CPU测试通过，A/B frozen profile/source hashes不变。review新增3项测试覆盖多Run同名视频不碰撞、完成态输入与便携页面标签/引用；技术通过不代替质量验收。

### 同条件 A650→A800

两组复用相同基座、训练YAML、prompt、初始视频、CFG/steps/seed；只更换adapter检查点。基于10%/50%/90%抽帧：

- 自回灌R1：A650明显近景化，头部/躯干比例失真，旁边出现橙色异常物体；A800保留原始远景街道与全身人物。此项有明显改善，但不能凭缩略图确认细粒度身份属性均正确。
- 自回灌R2/R3：A650继承首轮严重失真，动作与换装响应弱；A800能产生较明显舞蹈姿态，但R2改变了机位/构图，R3仍有衣物和身体局部异常。
- 真值历史R2：两组都产生动作，也都改变机位；没有证据说明该非目标漂移已经解决。
- 真值历史R3：两组都未切换到GT男装，仍偏橙衣绿短裤，并改变动作/构图；没有明确的目标换装改善。
- 真值历史R5：A650偏粉色短裤式连体造型，A800更接近粉色裙装，对“women's dress”的响应有改善；并非精确复现GT白裙。

结论是“继续训练带来了局部可见改善，但不均衡，核心男装响应与非目标保持仍未达预期”，不是整体收敛或泛化通过。自回灌各模型会使用自身上一轮输出，R2以后输入自然不同；这里比较的是整条轨迹，而非固定同一个生成source的单轮消融。

L06/L08 保持 `in_progress`，不得从文件生成成功直接宣称视觉质量通过。损失归一化按用户确认保留；one-step历史方法和数据划分均未改动。

## B350 完整复测（用户重新授权，16:21～16:28）

用户查看A800后认为依然不尽人意，明确要求测试B最新checkpoint。16:20重新读取B目录，最新完整保存仍为`0000350`；当前交互allocation123858的单H200空闲。新的独立step `123858.4` 于16:21:09～16:26:45正常`COMPLETED/0:0`，耗时5分36秒；没有重现此前中断，不推断旧取消的具体来源。未新增allocation或改动A/B训练。

当前下载入口为 [B350与A800便携对照目录](../outputs/multiturn_chat/stage5_b_step350_trainres_review_20260906_1623/)，约51.2MiB，下载整个目录后打开[index.html](../outputs/multiturn_chat/stage5_b_step350_trainres_review_20260906_1623/index.html)。页面四列为B实际SOURCE / rendered GT / A800 / B350；自回灌第二轮后A与B的生成source自然不同。51个本地HTML引用全部存在，原视频、GT、A800视频与manifest副本均已物化，原始A800目录未修改。

运行命令（在本次已确认空闲的交互GPU中执行；输出目录已存在，不要原样重复覆盖）：

```bash
python 10_research/model_experiments/lance/scripts/run_datamake_lora_visual_sanity.py \
  --checkpoint 10_research/model_experiments/lance/outputs/training_runs/datamake_dialogue_one_step_x0_lora_r64_4xh200_stage2base_v1/checkpoints/0000350 \
  --output-dir 10_research/model_experiments/lance/outputs/multiturn_chat/stage5_b_step350_trainres_review_20260906_1623

python 10_research/model_experiments/lance/scripts/build_datamake_visual_sanity_review.py \
  --run-dir 10_research/model_experiments/lance/outputs/multiturn_chat/stage5_b_step350_trainres_review_20260906_1623 \
  --label 'B step350 (Stage2 base)' \
  --compare-run 'A step800 (official base)=10_research/model_experiments/lance/outputs/multiturn_chat/stage5_a_step800_trainres_20260906'
```

日志为`outputs/slurm_logs/dm_lance_b_step350_trainres_review_123858_20260906_1623.log`。标准sampler、30steps/CFG1/seed42/shift3.5和训练匹配预处理未改；A800与B350的preprocessing、完整inference arguments、case/prompt/GT映射逐字段相同。B正确加载Stage2基座`ae9c4aba...99075e`和adapter `974466af...3f0703`；512/512加载值与checkpoint的BF16转换一致，256/256个LoRA B非零。三轮自回灌耗时109.61秒，TF R2/R3/R5分别41.98/50.27/69.30秒，峰值allocated显存22.04GiB。全部六个视频完整解码为624×352、57帧、12fps、4.75秒；这只证明媒体有效，不作为语义评分。

### 三时点视觉初查

基于10%/50%/90%抽帧，而非完整人工播放：

- R1身份：B保持原始远景、人物比例和橙衣绿短裤，人物外观更接近GT；缩略图不能确认痣、眼睛等细粒度属性全部正确。
- 自回灌/TF R2动作：B维持原机位和街道布局并生成下蹲/舞蹈姿态；A800则明显改变机位并放大人物。B动作轮仍有局部模糊、重影/半透明感，未宣称时序质量通过。
- 自回灌/TF R3换装：B确实从橙衣绿短裤转为棕色上衣和深色长裤，同时保持原街景和较接近原动作；A800这两例仍主要保留原衣服且有较大构图漂移。B自回灌R3仍见肩部/衣物局部异常。
- TF R5换装：B输出白色裙装，更接近渲染GT并保留动作/背景；A800为粉色裙装。prompt只要求女式裙装，不能单凭颜色不同判A失败。

本组证据支持“B350的换装响应与非目标保持明显优于当前A800样例”，不支持整体泛化或已收敛。A800与B350既不同基座又不同训练步数，且B继承Stage2既往全参训练；本轮没有训练匹配分辨率下的Stage2无adapter对照，因此不能把B的优势全部归因于新增350步LoRA或声称等训练预算胜出。L06/L08继续`in_progress`，等待用户下载播放。

16:26:57核验：推理GPU占用0MiB；A Job123860仍PENDING(Resources)，B Job123681仍RUNNING、剩余1:42:11，未被本轮修改。全部89项Lance与132项核心CPU unittest通过；训练profile哈希保持A `315a8ef1...37f7d`、B `793d8a4d...a0b9c`，未改训练、推理代码或配置。

本轮文档技能仅同步本报告、训练接入、Handoff、当前Plan与人类/机器Status，并重建既有catalog/inventory；WF-90发布结论和数据不变。独立子系统及跨层文档审计通过：114文档全部可达、673链接、404脚本、5个output scopes，零错误、零警告。当前环境未安装pytest，三组核心目录沿用unittest discovery完成22+30+80项；不涉及CC/UE运行时验证。GPU技术与文档通过均不替代用户视觉验收。
