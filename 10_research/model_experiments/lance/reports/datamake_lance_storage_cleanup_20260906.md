# Lance Tiny / Stage1 清理与目录整理（2026-09-06）

> 状态：`completed`；2026-09-06完成删除与CPU/文档验证。
> 实现所有者：[训练接入](../training_integration.md)
> 授权范围：用户明确删除tiny训练配置、checkpoint、report及Stage1结果，整理其余Lance文件。

## 删除边界

删除清单与逐文件SHA-256见[清理Manifest](./datamake_lance_cleanup_manifest_20260906.json)。27个精确文件/目录目标包含73个文件或符号链接，普通文件合计21,044,968 bytes（20.07 MiB）；不跟随符号链接删除外部目标。

- tiny：派生parquet/YAML/manifest、评估training_config/日志/指标、六个推理视频及生成配置目录、两份训练/过拟合报告、专用subset builder及其测试和两份对应Python缓存。
- Stage1：Job119261训练Run外壳和本地W&B缓存、119215/119261调度日志、step3371推理视频/指标/配置、正式训练与视觉报告。
- 通用单卡全参smoke launcher移除tiny预设，不再保留tiny超参入口。
- tiny和Stage1大型checkpoint在此前清理已删除，本次没有新的大型checkpoint可删除；不能把历史释放量再次计入。

这不是归档备份：所列实验内容不再保留副本，只留删除路径/哈希和清理边界。未进入Git的文件无法由本仓库恢复；历史结果不再作为当前可复核Gate证据。W&B云端记录不在本次本地文件清理范围内，未删除或改写。

## 必须保留

| 类别 | 保留原因 |
| --- | --- |
| `outputs/model_bases/datamake_dialogue_stage2_step3669/` | B基座、后续主要已训练起点；只有模型，没有旧全参optimizer |
| `models/Lance/` 与全局HF cache | A仍是官方基座LoRA，且ViT/VAE依赖此处；不是Stage1训练结果 |
| Stage5 A/B Run、全部当前checkpoint和日志 | 已暂停，恢复点A800/B350；没有授权清理这些检查点 |
| Stage2 Run/训练profile/报告/视觉输出 | 用户要求保留的基线；不包括后续明确删除的`logs/generated_configs/`旧推理输入JSON |
| 冻结8-shard split、chain数据及Stage2数据 | 当前训练、推理和数据追溯仍引用；名字含first_batch不等于Stage1结果 |
| `patches/0001..0013`、共享Dataset/模型/LoRA/checkpoint实现与相关回归 | 当前源码和补丁重放链；0008名称含tiny，但修改的是共用Dataset，不能按名称删除 |
| Stage1静态profile/job与共用formal launcher | 小型历史配方/共用回归依赖，不是训练结果；旧Stage1权重已经不存在，不作为启动入口 |
| Stage3/4设计及逐tensor审计 | teacher-forced/full-rollout消融和checkpoint正确性的必要证据 |
| A400/A650/A800/B350视觉输出 | 当前比较与用户复核材料；两个旧B中断尝试只作事故证据 |

## 文档整理

Lance首页改为当前入口索引，不再堆叠旧实验流水账；reports/configs/jobs/scripts分别有分类导航。训练接入、Handoff、当前Status/机器状态和Plan移除已删tiny/Stage1结果引用；L04/L05仅保留历史执行完成/产物已按用户决定删除的状态，不再复制旧指标。L06/L08以Stage2及当前A/B证据为准，仍未关闭质量验收。

没有移动或改写冻结路径，没有修改当前A/B profile、LoRA/模型逻辑、数据或checkpoint格式。A/B仍停止，不提交任何训练、推理或UE任务。README中的“可用配方”不代表当前获准启动；下一步等待用户说明训练修改。

## 清理后验证

- 27个目标全部不存在；剩余名字含tiny的补丁/mock是已检查的共享依赖，不是tiny实验产物。
- 两份A/B profile与8份adapter的清理前后SHA-256一致；A的21个、B的22个冻结实现哈希均匹配。Stage2 base仍在，大小28,422,373,304 bytes；本次未重新通读27 GiB基座计算哈希。
- Lance CPU unittest **87/87**通过；原89项中删除了2项tiny专用builder测试，其余未移除。核心documentation/dataset/unreal测试分别22/30/80项，共**132/132**通过。环境没有pytest，使用这些unittest测试原生支持的discover入口。
- Shell语法通过；旧 `--mode tiny` 在任何训练启动前以exit2拒绝。未进行GPU训练或推理验证，因为冻结训练计算实现未修改。
- Script Catalog/Output Inventory已重建（404脚本、5个输出scope）；完整文档审计114/114可达、657个本地链接，独立子系统与跨层检查零错误/零警告。
- 另检查23份Lance报告/索引及顶层入口中的211个本地文件链接，零缺失。保留的历史报告内纯文本旧产物路径仅作历史追溯，不表示产物仍在线。
- WF-90/released数据、当前计划与L06/L08状态保持不变；A/B仍暂停。

## 后续授权：旧输入与生成配置清理

用户随后明确授权删除三个目录，而对training_data仅询问用途和可删除性。本轮执行边界：

- 删除 `inputs/`：24文件、198,553,729 bytes，含11个早期外部视频、prompt与说明；未另留视频备份。原已进入Git的说明/prompt可以从Git历史取回，未入Git的视频不能通过本仓库恢复。
- 删除 `logs/generated_configs/`：9个Stage2推理输入/评估JSON，14,760 bytes；未留副本。Stage2权重、训练profile、输出视频、报告和现行A/B推理输入均不动。
- 删除空 `outputs/training_eval/`；同时以rmdir移除已经为空的 `logs/` 父目录。
- 本轮合计33文件、198,568,489 bytes（约189.37MiB），不计入上文第一轮20.07MiB。逐文件清单记录于同一Manifest的 `followup_cleanup` 字段。
- 未启动任务，未修改模型、训练/推理代码或冻结profile。旧通用脚本仍可按需重建生成配置目录；历史报告中的旧路径标注为已退役，不宣称还能原样重跑。
- training_data五个目录本轮均不删除、不移动，只新增[用途与清理建议导航](../outputs/training_data/README.md)。全字段对比证明candidate与旧单文件split被8-shard版覆盖，可留待用户确认后清理；chain与8-shard仍属当前依赖，Stage2增采样保留作追溯。

后续清理验证完成：三个目标目录与空logs父目录均不存在；56个已有数据文件、两份A/B profile清理前后SHA-256一致，A/B的21/22个冻结实现哈希匹配。87项Lance与132项核心unittest通过；catalog/inventory已重建，完整文档审计114/114可达、658链接、独立子系统/跨层零错误零警告；额外25份文档233个本地链接零缺失。未重新执行GPU训练/推理，因为数值实现与profile未变。

## 2026-09-07：删除已被完整替代的两份训练索引

用户明确确认保留数据能保证完整性即可执行清理。已删除 `outputs/training_data/datamake_dialogue_candidate_v002_20260831` 与 `outputs/training_data/datamake_dialogue_first_batch_v002_split_seed2026_20260831`，共16文件、3,496,025 bytes（约3.33MiB）。逐文件大小/哈希与删除结果位于本报告[机器清单](./datamake_lance_cleanup_manifest_20260906.json)的 `training_data_retirement_20260907`。

删除依据：上一节全字段Parquet行多重集合/chain-ID替代核验成立，删除前各文件哈希与该证据一致。删除后40个现存数据文件及A/B两份profile哈希不变；21/22份冻结实现哈希也全部匹配，共检查64个不同文件。两处目标目录已不存在。没有额外文件备份，但全部逻辑样本保留在sharded8索引中；不把这次删除当作释放多份视频。

保留[数据导航](../outputs/training_data/README.md)中的chain、sharded8、Stage2 R5×3三份数据，未改路径/内容。Stage2 R5×3还将供[新Stage6两臂配置草案](./datamake_stage6_stage2_lora_preparation_20260907.md)使用，不是可清理项。发布视频、基座和checkpoint均未删除；旧A/B仍暂停，没有新训练提交。
