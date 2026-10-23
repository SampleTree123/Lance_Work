# Stage6 两臂 step800 同条件视觉检查

> 日期：2026-09-09，时间为Asia/Singapore。  
> 状态：`generated_media_passed_pending_user_review`；推理与媒体检查完成，质量待用户播放验收。  
> 实现/输出所有者：[训练接入§6.9](../training_integration.md)。  
> 实验：`ABL-LORA-UND-01`，S6-1理解+生成LoRA vs S6-2仅生成LoRA；不是旧Stage5的基座A/B。

## 范围与训练状态

用户要求对两组已保存的800步参数做推理。训练Jobs125433/125434均已于9月9日14:51到18h上限结束，分别完成877/882更新；最新完整恢复点均为800，未保存的77/82步不能恢复。每臂现保留500/600/700/800四份完整checkpoint。用户已自行提交800续训Jobs126188/126189，推理开始时两者均PENDING。本次不提交、取消或修改训练任务。

推理使用当前交互allocation126170（H64Y574/testqueue）的一张H200，先经`srun`确认仅可见已分配GPU0且显存1MiB。宿主沙箱中的`nvidia-smi`无法访问驱动，allocation内检查正常；不是驱动故障，不涉及驱动/服务器配置修改。不使用同节点其他渲染作业的GPU，不取消交互allocation。两臂顺序执行，每次推理step限30分钟，均在既有18h allocation内。

## 固定检查点与推理配方

Run前缀均位于`outputs/training_runs/`：

| 臂 | Run名称 | checkpoint | 训练范围 |
| --- | --- | --- | --- |
| S6-1 | `datamake_dialogue_stage2_recipe_lora_r64_both_branches_v1_4xh200_restart1` | `0000800` | 理解+生成LoRA |
| S6-2 | `datamake_dialogue_stage2_recipe_lora_r64_freeze_und_v1_4xh200_restart1` | `0000800` | 仅生成LoRA |

两份800的complete标记、必需文件尺寸及当前profile/source合同检查通过；使用对应adapter schema安装branch loader，先加载同一官方Lance基座，再加载各自LoRA。推理不加载Adam，不修改checkpoint。

- 复用现有`run_datamake_lora_visual_sanity.py`，不修改训练代码或采样器。
- 同一validation输入、prompt与seed：30 diffusion steps、文本CFG1、validation seed42/global seed2025、推理timestep shift3.5、KV cache开启。
- 从checkpoint中的训练YAML复用VAE480/ViT448分桶与12fps采样；不是仅选择同名分辨率preset。全部生成视频完整解码为624×352、57帧、12fps、4.75秒。
- 每臂4个case/6个视频：一条三轮真正自回灌链（身份→动作→换装），以及GT历史下的R2动作、R3换装、R5换装。自回灌不预载中间GT。
- 两臂均800步、相同官方基座及输入配方，适合比较理解LoRA训练范围；少量样例仍不构成全验证集或多随机种子泛化结论。
- 不上传视频或模型到W&B，不改released数据，不生成新的训练数据。

## 输出与日志

S6-1原始输出：`outputs/multiturn_chat/stage6_s6_1_step800_visual_20260909_1553/`。

最终便携对照页：[index.html](../outputs/multiturn_chat/stage6_s6_2_step800_review_20260909/index.html)。下载整个`outputs/multiturn_chat/stage6_s6_2_step800_review_20260909/`即可；33个文件共52,807,082 bytes（约50.4MiB）。已复制S6-1输出和必要参考，页面51个本地引用（21个唯一路径）全部存在且都在目录内，不依赖另一目录。包含原始/实际输入、GT、prompt和双方输出。`manifest.json`记录S6-2，`references/comparison_0_manifest.json`记录S6-1。

页面A为UND+GEN、B为GEN-only。SOURCE列是B当轮实际输入；自回灌R2/R3时A实际输入应看A上一轮输出，不是B的SOURCE；teacher-forced两臂输入相同。

日志落于`outputs/slurm_logs/stage6_s6_1_step800_visual_20260909_1553.out/.err`及S6-2对应日志。每个Run的`manifest.json`记录实际checkpoint/adapter hash、base身份、预处理、输入、输出、参数、加载核验及运行耗时。

## 结果与验收

| 臂 | Slurm step / 结果 | 用时 | adapter加载核验 | 非零LoRA-B | 最高case峰值显存 |
| --- | --- | --- | --- | --- | --- |
| S6-1 | 126170.3 / COMPLETED 0:0 | 6m25s | 1016/1016与保存值转换BF16后一致 | 503/508 | 22.229GiB |
| S6-2 | 126170.4 / COMPLETED 0:0 | 5m34s | 512/512一致 | 256/256 | 22.006GiB |

S6-1五个仍零的B是已知末层UND无损失路径模块，不是此次保存/加载错误。两臂各六个输出及页面全部参考视频完整解码，`media_audit.json`为passed。基座、step800、预处理、输入/prompt/GT、全部推理参数逐字段一致。未出现OOM或异常退出；推理结束后allocation内GPU显存回到1MiB，交互allocation及其他任务保留。16:07两份800续训126188/126189仍PENDING(Priority)，本次没有操作它们。

### 抽帧观察（非完整播放验收）

检查10%/50%/90%三张对比图：

- 两臂均大体保留背景、场景和机位。身份轮头部/肤色有响应，但全身小图不足以判断精细身份相似度。
- 动作轮两臂都有动作变化，姿态和位置仍与GT不同；B更明显出现弯折、模糊/重影，A相对连贯但也未完全解决。
- 三轮自回灌换装中，A出现棕红上衣但长裤不完整；B更倾向保留橙黄上衣/绿色短裤，换装响应较弱。
- GT历史R3中A的棕红上衣和长裤较完整，B仍有短裤/裸腿残留；GT历史R5中两臂都能明显换为浅色连衣裙。

这些样例初步偏向S6-1的换装完整性；GT历史下优于连续生成回灌。不能据此确定总体胜者、收敛状态或关闭质量Gate，需用户完整播放，并区分随机种子/样本局限。

### 工程与文档边界

本轮105项Lance CPU测试及132项项目核心CPU测试通过；推理不改变代码/profile/source合同。媒体/页面检查通过不等于质量通过，也不是重新验证分布式optimizer恢复。文档按维护规则同步Technical、Plan、Status与消融记录；L06/L08保持in_progress，WF-90 released不变。

最终重建404项Script Catalog、5个Output Inventory范围（713文件）；文档审计114/114可达、665本地链接，各独立子系统及跨层检查全部通过，零错误/零警告；`git diff --check`通过。
