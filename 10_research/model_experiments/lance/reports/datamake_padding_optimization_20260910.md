# 打包后 attention padding 缩减与续训准备

> 存储补记（2026-09-11）：用户已授权清理部分历史验证和中间迁移大文件，范围与保留边界见[清理记录](./lance_storage_cleanup_20260911.md)。下文的历史中间迁移目录已仅保留元数据；最终 padding_final、正式恢复点与最新 DDP 原始验证产物完整保留。

> 日期：2026-09-10，Asia/Singapore。状态：padding实现、CPU/GPU数值、四卡短测和两臂完整恢复验收通过；下一轮两臂已按用户要求保存987/893步并结束。Technical所有者：[训练接入](../training_integration.md#peftddp-性能优化2026-09-09)，计划L10工程项完成。

## 本轮范围

用户取消FlashAttention后端更换，要求快速移除打包后的多余padding，验证并汇总收益，随后准备两臂下一轮训练。继续使用xks_lance（Torch2.8.0+cu126、flash-attn2.8.3）；没有安装或升级依赖。

新增`ddp.attention_padding`：`fixed`保持原行为；`minimal`在DDP微步进入模型前，把原末尾独立padding document缩到`(-sequence_length) % 128`。仅替换`sample_lens`/`split_lens`末项，保留零长度pad sentinel以满足Lance的真实sample位置编码循环。真实输入tensor、样本边界、监督位置、loss权重与RNG不变；官方FlexAttention、mask定义、VAE与MLP不重写。源Dataset仍提供原预算检查；模型实际mask/QKV长度按缩减后的元数据构造。只缩减注意力尾部补齐，不改变VAE空间/时间预处理。

候选：[理解＋生成](../configs/datamake_stage6_padding_both_20260910.json)、仅生成（历史文件已于2026-09-11清理），继承off10/off14、retain、batch1/accumulation8/global32。packed batch>1仍属于此前实验范围，不因本次padding修改自动接受为正式配置。

## 实测结果与优化汇总

同一allocation126684、8GS9B74、四H200/56CPU串行执行；每组4个真实optimizer更新、前2预热后2计时，保持相同4-rank样本顺序与global batch32。首轮新形状编译计入实际墙钟；这里不是长期稳态benchmark。

| 分支 | 固定padding 秒/更新 | minimal 秒/更新 | 耗时下降 | allocated峰值 固定→minimal GiB |
| --- | ---: | ---: | ---: | ---: |
| 理解＋生成 off10/retain | 91.41259 | 91.72943 | -0.35% | 118.20462 → 117.95594 |
| 仅生成 off14/retain | 84.48253 | 83.74140 | 0.88% | 126.82249 → 126.47646 |

仅生成参照是同allocation同节点之前的正常入口4步记录，理解＋生成参照本轮重新测量。全部4步的全局loss、MSE、梯度范数、学习率、监督token和各rank样本顺序/local loss精确相同，三组正常入口均退出0、无OOM。minimal reserved峰值分别121.00586/128.22656GiB。

每个prefix的平均padding由20,032.023降至59.023，缩减99.71%；只剩0～127的128对齐。峰值仍主要来自长样本的真实激活，因此本轮单卡峰值仅降低约0.25/0.35GiB。两组时间差都小，**不把本次padding修改计为已证明的显著额外提速**；新形状的编译与运行波动限制外推。含启动的理解＋生成本轮墙钟473.39→540.72秒，冷启动编译成本显式保留。

此前优化应按各自同条件范围解释，不能把不同范围的百分比相加：

| 改动 | 已验证效果 | 对照范围 |
| --- | --- | --- |
| 官方PEFT/DDP替代旧LoRA/FSDP | 基座权重梯度GEMM已消失；峰值80.99→41.04GiB；104.71→101.25秒/更新 | 单H200、原短测，同rank0样本，非正式四卡HYBRID_SHARD |
| 位置编码Python求和改张量归约 | 位置函数4.1597→0.0027秒，forward+backward17.6263→13.4975秒，减少23.42% | 单个真实R5，非整个训练update |
| 选择性检查点＋保留VAE缓存 | 93.6838→85.7710秒/更新，减少8.45% | 理解＋生成，四卡同12步、后10计时 |
| 上述缓存/检查点＋本轮padding | 99.9536→91.7294秒/更新，减少8.23% | 理解＋生成，位置求和已优化的全检查点/清缓存DDP基线，截取相同4步/后2计时 |

最后两行样本窗口不同，不能把85.77与91.73直接比较为退步。本轮固定padding同4步重测91.41，与上一12步实验的前4步对应均值91.25相近。完整机器比较见outputs/optimization_diagnostics/padding_20260910/results.json；各阶段原始范围见[单卡短测](./datamake_lora_short_speed_20260909.md)、[位置求和](./datamake_position_sum_optimization_20260910.md)、[缓存接入](./datamake_vae_cache_integration_20260910.md)。

## 验证证据

- 126项Lance CPU回归通过；新增4项测试覆盖1/2/4个不等长sample、整128边界、真实mask/样本隔离、FP64稠密attention输出和Q/K/V梯度、保留元数据对象、拒绝裁剪真实document及profile策略。
- patch0021在修改前的两个DDP源码上重放后逐字节匹配；outer launcher与variant生成器由DataMake直接追踪。代码合同仍为20个实现文件，内容哈希已改变，padding之前的旧DDP Gate不能复用；本轮已重新执行真实四卡恢复对照。
- 真实R5样本62,617 token、固定噪声、非零LoRA B：使用static编译后，固定65,536与缩减62,720两种长度的loss均为0.08181390911340714，1,016个LoRA梯度tensor逐元素一致，重复原长度也逐元素一致。见verify_static/summary.json。
- 首次默认自动动态编译对照未通过：切换长度后产生3.2515%梯度相对差，切回原长度仍保持同样差异；额外预热不能消除。隔离设置torch.compile(dynamic=False)后差异为零，因此正常DDP入口在minimal模式采用该官方设置；共享qwen2_navit.py保持原哈希，旧Stage4/5配置校验继续通过，按形状缓存编译，未改变注意力后端或手写kernel。首次新长度可能有编译成本，性能测量需包含/区分这一影响。初始失败证据verify与verify_warm保留，不放宽2%阈值。
- 固定padding四卡对照4更新已完成：后2步均值91.412586秒，峰值allocated118.204617GiB/reserved121.287109GiB。该组启动时使用共享位置的static编译设置，快照与合同保存在fixed_both_source；最终实现把完全相同的官方编译设置限定在DDP minimal入口，避免改变旧Stage4/5源码哈希。两者编译调用相同，本轮四步实际loss/梯度范数/trace与历史基线亦逐步精确一致。
- 缩减padding四卡短测及机器数值审计通过。
- 理解＋生成从900连续至903、900至902保存后重启至903：1,016个adapter、3,048个Adam状态tensor、scheduler、四rank RNG、游标、loss与样本顺序均精确一致；两条路径的256个生成LoRA B均实际更新。原验证器误把显存allocated/reserved峰值视为训练状态，因重启后缓存历史不同而拒绝；现仅排除这两个性能字段，126项回归再次通过，并覆盖loss、样本及新增语义字段差异仍被拒绝。
- 该验证器修复仅改变outer launcher的verify_gate函数体。both_checker_revalidation.json记录原GPU执行合同与新验证合同：AST证明其余launcher逻辑完全一致，另外19个实现文件与profile/runtime均保持原哈希；新旧900迁移的adapter/Adam/scheduler/RNG/游标文件字节一致，PEFT配置仅target_modules集合序列化顺序不同。对不可变四卡证据重新执行修正后的完整验证器通过，未改写旧checkpoint合同、未放宽数值阈值；新Gate明确声明GPU执行早于验证器修复。仅生成分支在最终合同下完成825→828连续与825→827保存后恢复至828对照，adapter/Adam/scheduler/四rank RNG/游标/trace均通过，实际生成adapter更新通过。

## 恢复准备

原Stage6的900/825 checkpoint作为不可变来源，完整adapter/Adam/scheduler/四rank RNG/游标迁移到本轮隔离目录；转换不删除或改写旧恢复点。当前代码合同转换位于outputs/checkpoint_migrations/padding_final_20260910/both/0000900与gen/0000825（Lance根目录相对路径），CPU转换/完整文件验证均通过；早期migrated_both/gen及checkpoint_migrations/padding_20260910、padding_ddp_20260910属于中间实现合同，已被替代且不可用于本轮恢复。GPU连续3步与2步保存后恢复1步的Gate通过后，方可使用新DDP profile续训。两臂新身份与原FSDP区分，训练仍从900/825起点延续原3000步学习率计划。

入口：[both job](../jobs/datamake_stage6_padding_both.sbatch)、gen job（历史文件已于2026-09-11清理），默认validate，必须显式提供RESUME_FROM；训练模式使用DDP_MODE=train。截至2026-09-10T15:18:43+08:00：both Job129047（PENDING，(Resources)），从900续训；gen Job129143（PENDING，(Priority)），从825续训。两组均4H200/18h，原3000步总计划不变；这是一次续训提交，不保证在单次18h内完成余下全部步骤，不设置自动再次提交。提交回执submission_both.json/submission_gen.json、Slurm快照slurm_final_status.json与最终Gate引用保存在诊断目录。

## 输出与所有权

`outputs/optimization_diagnostics/padding_20260910/`属于训练接入已有下游诊断范围，保存修改前源码、probe/controller、CPU/补丁证据、转换状态与独立checkpoint、GPU日志/metrics/trace、结果审计和恢复Gate引用；可用于续训的完整转换checkpoint归outputs/checkpoint_migrations/padding_final_20260910，不从诊断训练目录恢复。默认保护，不删除已有实验。训练日志和正式checkpoint仍归`outputs/training_runs/`。

## 最终工程审计

126项Lance回归、132项核心回归通过；patch重放与bash语法检查通过。两臂完整恢复验证与训练提交已完成，调度状态见上段；L06/L08模型质量仍需后续视觉检查，未由loss或工程Gate替代。

## 用户结束两组训练（2026-09-10）

2026-09-10用户要求结束两组训练；均通过SAVE_AND_STOP保存当前完整状态后正常退出。Job129047保存987步，20:03:16 COMPLETED/0:0；Job129143保存893步，20:02:04 COMPLETED/0:0。完整checkpoint文件大小/SHA256、当前实现合同、四rank状态和数据游标验证通过。不自动续训或重新提交。

证据：outputs/optimization_diagnostics/padding_20260910/stop_requests.json与stopped_checkpoints.json。恢复点分别为outputs/training_runs/datamake_stage6_ddp_pad128_both_20260910/checkpoints/0000987、datamake_stage6_ddp_pad128_gen_20260910/checkpoints/0000893。本次是用户要求提前结束，并非达到原3000步目标；L10优化工程验收不变，L06/L08模型质量仍未关闭。

## 停止后的完整日志与训练状态复查（2026-09-10）

用户要求再次核对耗时与训练正确性。本次只读检查已结束的正式运行及源/最终checkpoint，没有启动GPU训练或推理。诊断脚本audit_stopped_training.py、机器结果stopped_training_correctness_audit.json和日志stopped_training_audit.log归本报告现有padding诊断目录。

| 分支 | 旧正式训练末20步 | 新正式训练剔除启动前2步 | 秒/步 旧→新 | 耗时下降 | 新运行全部更新（含首步编译）均值 |
| --- | --- | --- | --- | --- | --- |
| 理解＋生成 | 881–900，20步 | 903–987，85步 | 132.09 → 85.17 | 35.52% | 86.47秒，901–987共87步 |
| 仅生成 | 806–825，20步 | 828–893，66步 | 135.89 → 78.94 | 41.91% | 80.69秒，826–893共68步 |

这些是训练step_time，不包含模型加载、W&B初始化、checkpoint保存和退出等整段作业开销；前后样本窗口和节点不同，属于实际运行观察，不能当作同条件因果实验，也不能归因于padding单项。旧训练为LoRA/FSDP，不是新跑的全参对照。

复查通过：

- 最终987/893与源900/825完整文件大小/SHA256、20文件当前实现合同、profile及数据配置合同、world4和数据游标匹配。
- 正式日志分别连续87/68次更新，无缺号或重复；global batch32、监督token数及累积8的配置/循环一致。正式前三步的loss、梯度范数、学习率和目标计数与原四卡恢复Gate精确一致。
- 优化器仅含LoRA参数。双分支1,016个Adam条目的step均前进87；仅生成512个条目均前进68。adapter、Adam一/二阶矩均为FP32且有限，二阶矩非负；四rank CUDA RNG均已推进。
- scheduler从900→987、825→893；逐步学习率与独立计算的原3000步cosine计划一致，源checkpoint、每步日志和最终optimizer/scheduler学习率连续。
- 双分支1,006/1,016个adapter张量实际改变；未变化的10个仅为最后第35层理解分支Q、O、MLP三投影的A/B，源/最终Adam一二阶矩均为零。生成loss不依赖最后一层这些理解输出，属于预期零梯度；该层理解K/V及全部生成adapter均有更新。仅生成512/512个adapter张量实际改变。审计脚本最初把“Adam计数前进”误作“权重一定改变”的必要条件；现分别核对计数、数值改变和这组明确的零矩例外，未修改训练或checkpoint。
- 全部记录loss/梯度等数值有限；完整Slurm日志未发现OOM、NCCL错误/超时或编译缓存上限报错。分配峰值约118.05/126.55GiB，缓存峰值约121.11/128.61GiB。

边界：正式运行没有保存每个microstep的样本ID或冻结基座的独立副本，因此本次通过源码、确定性索引/游标、checkpoint和首三步Gate一致性核查，未做87/68步GPU完整重放，也未做新的生成质量评估。当前未发现需要修改的训练正确性问题；两组仍按用户要求结束，不自动恢复。
