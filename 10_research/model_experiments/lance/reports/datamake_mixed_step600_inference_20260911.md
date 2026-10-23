# 混合训练 step600 完整链与真实单轮推理结果

2026-09-11，用户要求使用最新checkpoint执行已准备的套件并填入原页面。启动时最新完整checkpoint为600；已完成全部28段视频，进程正常退出0，媒体与会话检查通过。质量状态仍是`pending_user_visual_review`，不关闭L06/L08。

- [原页面，现已填充生成结果](../outputs/multiturn_chat/mixed_complete_chain_preview_20260911/index.html)
- [独立推理Run](../outputs/multiturn_chat/mixed_step600_complete_review_20260911_1643/manifest.json)
- [完整验证记录](../outputs/multiturn_chat/mixed_step600_complete_review_20260911_1643/completion_verification.json)
- [选例、回填定义与准确命令](./datamake_complete_chain_review_preparation_20260911.md)
- 实现/输出所有者：[training_integration.md](../training_integration.md)。

## 执行范围

使用已分配的独立单H200交互作业133209/8GS9B74，八卡训练132170/BFS9B74继续运行，没有调整训练配置或生产实现。只将推理子进程的CPU affinity扩展到本allocation允许的14个CPU；退出后GPU显存为0 MiB。

完整checkpoint来源为`datamake_coinve_mixed_ddp8_lora64_both_no_region_v1/checkpoints/0000600`。推理启动时已校验并固定adapter、LoRA配置及训练合同到Run的`inference_adapter/`，原训练keep4轮换不会使本结果丢失权重依据。该副本仅供推理，不含训练恢复状态。

Adapter SHA256：`045b220b0d6ab59b7ae92c2c2a9401f2c9b92365a175720057e9eec7a2e8b83f`。加载后1016/1016张量与checkpoint在推理dtype下一致；503个LoRA B张量非零。完整采样参数和预处理由Run manifest保存：30 diffusion steps、CFG1、shift3.5、global/noise seed42、KV cache，训练YAML匹配的VAE/ViT处理；真实样例复用训练共同5秒窗口的原始source帧。

开始：2026-09-11T16:44:07.375603+08:00；完成：2026-09-11T17:02:12.709274+08:00。含加载共18.09分钟，19个会话累计生成耗时16.99分钟，GPU峰值allocated 22.26 GiB。该时间是本套件的实际耗时，不作为训练速度或普遍推理吞吐基准。

## 结果检查

- 原3/4/5轮UE链与4个CoinVE单轮例子全部完成，共28段输出。
- 24段UE视频各57帧，4段真实视频各61帧，均完整解码；分辨率624×352、输出12fps。61帧封装时长约5.083秒，对应原始5秒窗口的kn+1采样，不能据封装时长判成额外取了视频内容。
- 19份transcript逐一核验：GT回填完整真实历史＋当前生成；自回填严格使用自己的前序生成视频；单轮真实输入仅source与完整编辑prompt，没有把target送入模型。
- 三条UE链的两种模式第一轮输入/种子相同，对应视频SHA256完全一致。
- 四个真实样例实际送入推理的source帧号、浮点FPS及起点，与准备页展示窗口记录完全一致。
- 进程正常退出。日志最初有一次runpy包装器缺少脚本搜索路径的启动错误，发生在模型/Run创建前；修正包装器后本次推理完成，不能将该历史启动栈误判为生成中断。

已将验证过的视频、输入、transcript与结果manifest写入用户原来查看的页面目录，原prepared manifest和媒体检查保留为`prepared_manifest.json`、`prepared_media_audit.json`。模型输出区不再使用占位。原始媒体不改写，推理Run及页面仍属`outputs/multiturn_chat/`研究输出，不晋升发布数据。

工程完整性检查不是视觉效果通过。没有同条件基线对比或用户本次视觉验收，不将训练loss下降、正常解码、首轮一致性作为效果提升结论。

收尾检查：原页面和独立Run页面均完成，51个媒体引用检查通过，28个发布视频与生成Run逐文件SHA256相同，页面无推理占位。生产训练22份实现哈希保持一致；文档目录重建、114文档/683链接审计及diff检查通过。未修改推理/训练源码，未重复无关CPU回归；本次新增验收来自实际GPU生成及完整媒体/会话记录。
