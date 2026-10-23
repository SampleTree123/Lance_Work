# GT历史训练 step1650：同条件推理复测

2026-09-12，用户要求用真实历史训练的最新完整checkpoint重跑原测试，检查增加训练是否改善效果。已完成同一套28段推理视频；工程验证通过，视觉质量仍待用户检查，不据此关闭L06/L08。

- [600步／1650步切换对照](../outputs/multiturn_chat/mixed_step600_vs_step1650_20260912/index.html)
- [1650步完整结果](../outputs/multiturn_chat/mixed_step1650_complete_review_20260912/index.html)
- [600步原结果](../outputs/multiturn_chat/mixed_step600_complete_review_20260911_1643/index.html)
- [完整检查证据](../outputs/multiturn_chat/mixed_step1650_complete_review_20260912/completion_verification.json)、[同条件验证](../outputs/multiturn_chat/mixed_step1650_complete_review_20260912/comparability.json)
- [运行日志与有限验证脚本](../outputs/optimization_diagnostics/mixed_step1650_inference_20260912/)、[原套件与命令](./datamake_complete_chain_review_preparation_20260911.md)

## 范围与结果

选用 GT对照 `datamake_coinve_mixed_ddp8_lora64_both_no_region_v1/checkpoints/0001650`，它是本次开始检查时最新的完整checkpoint；比原600步增加1050次optimizer更新。合同明确为dataset_ground_truth历史，online_rollout=false；没有选用pred_x0模型。GT训练133604继续运行，本次没有改训练参数、提交额外训练或停止训练。用户提交的整链pred_x0作业133706单独记录运行状态，不作为本次权重来源。

使用现有单H200交互allocation133654/8GS9B74，CPU affinity限制在该step分配的14个CPU。生成开始 2026-09-12T11:23:33.562065+08:00，完成 2026-09-12T11:41:57.064399+08:00；含模型加载共 **18.39分钟**，19会话的生成累计 **17.30分钟**，峰值allocated **22.23GiB**。进程退出0。这是本套件的运行记录，不是普遍推理速度估计。

当前Run保留经过哈希核验的inference_adapter快照，adapter SHA256为 `72b41d12dd6e50bfe59926793189e21700248002ffef6ad21b4c146e8e057e67`；原训练keep4轮换不会使该快照丢失。快照不含optimizer/RNG，不是可续训checkpoint。

## 比较条件与正确性

- 600步与1650步的训练合同完全相同；官方基座哈希、推理脚本哈希、案例清单哈希、parquet哈希、预处理以及全部model/data/inference参数逐字段一致，仅adapter权重变化。
- 仍是3/4/5轮UE链各一条，分别进行真值回填和自回填，共24段；4个CoinVE单轮样例共4段。全部使用30 diffusion steps、CFG1、shift3.5、global/noise seed42和KV cache，未改prompt或重新选例。
- 加载后1016个LoRA tensor全部与快照在推理dtype下一致，503个LoRA B非零；checkpoint来源、快照adapter哈希及当前22份生产训练源码哈希验证通过。
- 28个输出全部全帧解码通过：UE57帧、CoinVE61帧，均624×352/12fps。51个网页媒体引用通过检查。
- 19个transcript逐一检查原始source、所有prompt、完整GT历史或自身生成历史的路径一致性；当前GT target没有作为单轮输入。三条UE链的两种回填模式首轮视频SHA256各自完全相同。
- 4个CoinVE输入的共同窗口、浮点FPS及实际帧号与600步记录逐字段一致，并与本次网页预览的采样窗口一致。

这些检查证明测试按预期运行，不能单凭更多训练步数、媒体有效或loss推断视觉效果改善。请对照编辑指令遵循、非目标内容保持、人物动作和后轮累计漂移进行播放检查。原600步页面及原始输出保留，新页面没有覆盖旧结果。

## 输出与生命周期

Technical owner为[training_integration.md](../training_integration.md)。本次复用现有生产推理/网页脚本，没有改其源码。诊断目录的run.py与verify_and_publish.py仅属于本次已完成实验；新增切换网页为静态研究产物，通过相对链接引用两次Run，没有额外复制视频。新Run仅保存生成视频、推理权重快照、会话/参数/验证证据和浏览代理，GT按原有规则引用。

输出沿用outputs/multiturn_chat与optimization_diagnostics研究类别，不晋升为发布数据，也未授权删除。WF90已发布边界不变，L06/L08质量验收保持未完成。页面JavaScript语法、媒体链接、报告链接、目录/输出清单及文档独立和跨层检查通过；完整结果见[最终审计](../outputs/optimization_diagnostics/mixed_step1650_inference_20260912/audit.json)。生产源码未改变，未重复本会话先前已通过的153项Lance和132项核心单测。没有浏览器视觉验收，页面播放与编辑效果由用户复核。
