# Lance 源码整理与官方基线迁移

> 日期：2026-10-22，Asia/Singapore。实现所有者：[训练接入](../training_integration.md)。本记录只涉及源码迁移与工程验证，不代表新模型训练或质量验收。

## 目标与目录边界

用户要求重新拉取最新官方代码，筛选必要本地修改，并在迁移验证后删除旧源码仓库。迁移对象是外层工作区内的 `lance/` 上游 clone；外层 DataMake Git、`models/`、`outputs/training_runs/`、媒体、数据集、推理网页及现存 checkpoint 不是删除对象。

官方远端 HEAD 与 main 在本轮查询均为 `4baeee086648996f6ab12e673cbe461b0b149997`。新目录从该提交创建，旧目录基线为 `9717d9160ed16fedfdad5ce39ccbc6c9d69695e0`。官方新增安全修订被保留，本地差异通过 `git apply` 应用，未整文件覆盖官方的新修订。

为了保留现有作业、媒体与文档路径，最终代码仍放在 `10_research/model_experiments/lance/lance/`。这不是在旧 clone 上继续叠补丁，而是独立下载的新 clone 经验证后接替原路径。新代码只链接现有模型目录，不复制模型或视频。

## 筛选结论

| 类别 | 处理 | 原因 |
| --- | --- | --- |
| GT历史混合数据 PEFT/DDP | 保留 | 当前正式训练主入口 |
| 整链pred_x0、固定目标窗口、detach历史 | 保留 | 当前另一训练方案；保持其原有loss归约 |
| 部分梯度检查点、retain VAE cache、minimal padding、位置求和优化 | 保留 | 已采用的训练优化，不在此次迁移中重调算法 |
| 合成链前缀、CoinVE共同时间窗口、确定性数据游标 | 保留 | 数据合同、时序对齐与恢复必需 |
| 多轮推理、显式LoRA加载、CFG修复与展示脚本 | 保留 | 当前推理评估依赖 |
| 每轮可选单张ViT参考图 | 保留 | 已实现能力；本轮工程回归不代表参考编辑效果验收 |
| 区域loss加权工具 | 保留为可选公共库 | 当前配置仍关闭，兼容既有配方/回归；不启用新目标 |
| 旧adapter格式与旧FSDP状态转换库 | 保留为兼容库 | 旧快照仍可能用于推理/显式转换，不应随训练器一起删除 |
| 前缀重生成pred_x0小型实验入口 | 兼容保留 | 可以做已有消融，不再作为默认整链入口 |
| 旧生成侧FSDP、Stage5在线训练器、Stage6 FSDP训练器 | 不迁入当前源码树 | 已由当前PEFT/DDP入口替代；原文进入归档 |
| 原官方 `unified_train.py`、`fsdp_utils.py` | 移除旧训练循环/恢复补丁 | FSDP工具完全恢复官方版；unified循环仅保留一行剥离`vae_edit_roles`元信息，避免共享packer与官方forward接口不兼容 |
| 旧全参/Stage5/Stage6外层launcher | 归入 `scripts/legacy/` | 原路径保留退役提示，不会误启动旧配方 |
| 26份阶段补丁 | 归入 `patches/legacy/` | 仅作历史来源，不再作为安装链 |
| 历史起点选择、多参考图/参考视频 | 仍为设计讨论 | 此次不实现尚未确定的新模型语义 |

## 实现结构变化

原先当前DDP训练器会为了少量函数导入旧checkpoint模块；整链训练会为了 `pred_x0` 公式导入一千多行旧在线训练器；PEFT元数据又依赖手写LoRA模块。这些依赖已拆开：

```text
scripts/datamake_runtime.py              公共路径、环境、官方参数映射
              │
run_datamake_ddp_training.py             GT入口与合同/恢复Gate
run_datamake_chain_pred_x0_ddp_training.py 整链入口与合同/调度
              │
lance/train/
  datamake_lora_config.py                纯配置、目标层选择
  datamake_peft.py                       官方PEFT实现
  datamake_prefix_data.py                数据索引与确定性预处理
  datamake_packed_batch.py               打包、padding、loss归约
  datamake_train_state.py                Adam初始状态、停止请求
  datamake_ddp_checkpoint.py             完整DDP保存与恢复
  datamake_flow_history.py               detached pred_x0
  datamake_chain_window_*.py             整链调度与逐轮打包
```

旧兼容文件不再进入当前训练的导入路径。`datamake_stage2_lora_data.py` 仅重导出新实现；旧checkpoint helper重导出公共状态函数，没有重复实现。历史FSDP速度探针分支已从两份现行DDP训练器移除，保留DDP单卡工程探针。

没有改变训练参数：当前双分支r64，0–25层开启梯度检查点、26–35层关闭，VAE cache retain、attention padding minimal；GT每卡batch1/累积4，整链固定32目标窗口；每50步保存、保留最近4份。GT与整链的既有采样及loss归约差异继续存在，本次不把它们改成单变量实验。

## 可复现安装与官方通道

唯一当前源码合同为：

- [source_lock.json](../patches/current/source_lock.json)：官方提交、补丁SHA-256、每个适配文件SHA-256、退役文件清单。
- [datamake.patch](../patches/current/datamake.patch)：基于固定官方提交的一份完整补丁。
- [rebuild_lance_checkout.py](../scripts/rebuild_lance_checkout.py)：重建/核验工具，拒绝覆盖已有目录。

在 DataMake 根目录核验当前源码：

```bash
python 10_research/model_experiments/lance/scripts/rebuild_lance_checkout.py --verify-only
```

需要从零重建时，目标必须尚不存在：

```bash
python 10_research/model_experiments/lance/scripts/rebuild_lance_checkout.py \
  --destination /tmp/lance_rebuild_example
```

需要严格未经DataMake修改的官方实验目录时使用 `--official-only`，并显式指定外层官方模型目录；该模式不加载LoRA、不应用本地补丁。当前正常工作区仍可通过 `inference_lance.py` 只加载官方权重，但共享代码包含本地修改，两种口径需要区分。

历史26份补丁不应再叠到新目录上。未来改动需要同步当前补丁、源码锁和验证记录，不能只编辑忽略目录后遗漏外层版本化来源。

## 验证与证据

所有本轮运行证据归既有诊断类别：[source_migration_20261022](../outputs/optimization_diagnostics/source_migration_20261022/)。

- 迁移前全量历史测试：179项，1 failure、9 errors；失败集中于旧源码合同哈希，与本轮迁移无关。保留原始日志，不改写冻结配方制造“通过”。
- 五份对应退役实现的测试已归入 `tests/legacy/`；当前小模型夹具独立为 `tests/lora_toy.py`。当前测试集独立验证数据、PEFT、checkpoint、参考图、CFG、整链和配方。
- 真实H200推理：同一GT1150 adapter、固定seed与64×64/9帧夹具；无图、红图、蓝图、text CFG3、ViT CFG3五例在迁移前后输出latent逐元素相同，最大绝对差全部为0。
- 真实H200小尺寸训练：无图/有图均完成数据打包、VAE、forward/backward；1016个adapter梯度张量有限，GEN非零B梯度256个、UND247个；一次AdamW更新确认adapter变化。没有修改正式checkpoint。
- 两进程CPU/Gloo：PEFT/DDP与显式全局参考的梯度最大差 `2.9802322387695312e-08`；不等长整链归约最大差0，历史detach成立。
- 干净官方代码重建：重新fetch锁定提交，再应用唯一补丁并逐文件核验，通过；不依赖旧源码目录。

GT与整链实际训练入口均使用原八卡配方、单卡diagnostic模式完成两个优化步/窗口，包含非零学习率更新；没有创建正式checkpoint或W&B run。GT loss为0.198591/0.072141；整链loss为0.270375/0.101122，分别生成3/4轮detached历史，额外模型forward为0。峰值allocated显存约118 GiB。首轮包含编译、数据等待且样本不同，这些时间不作为新旧吞吐对比。

八卡GT/整链配置dry-run、基座与数据合同检查通过，均要求新实现的启动Gate。当前仅分配一张H200，没有执行八卡NCCL连续/恢复测试；不能把单卡/CPU检查说成八卡性能或恢复验收。

## 源码归档与检查点边界

旧工作树的236项源码/链接、迁移前外层脚本/测试/补丁、Git bundle、原始diff及逐文件哈希保存在诊断目录。归档不跟随 `downloads` 链接，不包含模型权重或训练视频。其目的为保存手工批注和可追溯来源；归档不是第二个可运行训练仓库。

旧完整checkpoint的实现合同与新代码不同，继续保持严格拒绝不匹配；本轮不修改旧checkpoint、不伪造哈希，也不自动开始新的正式训练。推理adapter兼容已实测，但不能据此宣称完整训练状态可直接续训。后续恢复训练需要单独选择相符源码或显式验证的迁移方案。

## 收尾结果

源码迁移与清理已完成：

- 当前回归 **145/145**；核心文档/数据/引擎回归 **22＋30＋80** 项通过。环境没有pytest，使用项目已有unittest执行。
- 最终补丁覆盖44个修改/新增文件；干净官方提交重放及逐文件哈希核验通过，故意篡改文件会被源码锁拒绝。
- 最后接口审查补回一行 `vae_edit_roles` 剥离，并执行真实官方循环预处理的回归，防止恢复官方训练循环后把DataMake元信息传进不接受该参数的模型。
- 文档各子系统与跨层审计通过，无errors/warnings。
- 旧源码目录 `lance_legacy_migration/` 已删除；删除前再次逐项比对归档，236项源码/链接一致，未归档内容只有84个Python缓存文件。Git bundle校验通过。
- 外层工作区、新源码、模型权重、原始媒体、现有训练checkpoint及推理网页保留。没有提交正式训练，没有改动现有训练profile的数值参数或身份。

机器证据：[validation_summary.json](../outputs/optimization_diagnostics/source_migration_20261022/validation_summary.json)、[最终重放](../outputs/optimization_diagnostics/source_migration_20261022/final_replay.json)、[删除收据](../outputs/optimization_diagnostics/source_migration_20261022/cleanup_receipt.json)、[归档与文件清单](../outputs/optimization_diagnostics/source_migration_20261022/migration_inventory.json)。源码归档保留在同一诊断目录，仅作追溯与恢复，不是另一套活动仓库。
