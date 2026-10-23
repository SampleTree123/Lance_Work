# 当前训练实现与官方代码对照审查

核验日期：2026-10-12。Technical owner：[训练接入](../training_integration.md)。本轮是代码审查与数值验证，没有改训练实现、profile、checkpoint，也没有提交正式训练。

## 1. 结论与范围

**在当前实际配置下，没有发现选择性梯度检查点破坏梯度，或核心 flow-matching 计算偏离官方的问题。**真实 H200 小尺寸测试中，关闭、全部开启和当前部分开启检查点的 MSE 与全部 LoRA 梯度逐位相同。但“当前路径通过检查”不等于全部可选配置、正式八卡规模和所有恢复路径都已证明正确。

同时确认四项必须区分的事项：

1. 当前工作树与旧 GT1150、chain850 的恢复合同不同，不能直接原样续训。这是代码版本兼容问题，不是旧训练已经算错。
2. GT 与整链 pred_x0 除历史来源外，还改变了采样及 loss 归约；变长 latent 下不是严格单变量对照。
3. VAE 条件 dropout 非零时存在官方模板 packer 的边界问题；当前值为0，不触发。
4. 使用符号链接作为 `media_root` 并配合相对媒体路径时，审计与运行时路径解析不一致；当前正式数据根为规范路径，不触发。

比较基线是本地 Git 中的官方微调发布提交 **`9717d9160ed16fedfdad5ce39ccbc6c9d69695e0`**，remote 为 `https://github.com/bytedance/Lance.git`。本轮使用 `git show`、`git diff` 对比该不可变提交，**没有检查或声称对比2026-10-12线上最新版本**。当前新增训练器与适配器有很多是上游 Git 未追踪文件，因此不能仅凭 `git diff --stat` 判断改动范围；本轮也单独阅读了这些入口。

证据目录：[official_training_audit_20261012](../outputs/optimization_diagnostics/official_training_audit_20261012/)。其中保留官方关键源码快照、AST对比、恢复合同差异、CPU回归及GPU结果。历史报告仅用于定位，本次判断重新依据实际代码。

## 2. 实际调用路径

官方：

```text
train/unified_train.py
  → 官方模型初始化 / checkpoint加载
  → FSDP + PyTorch NO_REENTRANT activation checkpoint
  → PackedDataset → VAE编码 → Lance.forward
  → compute_training_loss → backward → clip → AdamW → scheduler
```

当前 GT：

```text
jobs/datamake_coinve_mixed_ddp8_lora64_both_no_region_v1.sbatch
  → scripts/run_datamake_ddp_training.py
  → torchrun train/datamake_ddp_train.py
  → 官方基座 → PEFT → 部分层checkpoint wrapper → DDP
  → IndexedPrefixDataset → DataMakeMixed → 官方PackedDataset
  → 官方VAE / Lance.forward → 官方口径MSE归约
  → 四次microbatch累计 → clip → AdamW → scheduler
```

整链路径为独立的 `run_datamake_chain_pred_x0_ddp_training.py → train/datamake_chain_pred_x0_ddp_train.py`，以整链窗口调度目标。GT入口调用旧 `build_torchrun_command` 是复用参数映射，不代表实际运行了 `unified_train.py`。

当前GT配方：八卡DDP、每卡batch1、累计4、global32；双分支r64 LoRA；基座BF16、adapter FP32；区域加权关闭；0–25层开启检查点，26–35层关闭；VAE cache retain、attention padding minimal；每50个optimizer update保存，保留最近4份。profile里残留的FSDP sharding字段不是当前实际后端选择。

## 3. 与官方相比，哪些部分相同，哪些部分改变

| 部分 | 官方发布代码 | 当前实现 | 审查判断 |
| --- | --- | --- | --- |
| Transformer训练主干 | MoT理解/生成路由、训练attention与decoder | 继续调用官方训练路径 | `qwen2_navit.py`本地改动位于推理归一化dtype转换，不是训练attention算法重写 |
| Flow matching | 混合干净latent与噪声，预测速度，目标为noise−clean | 公式与MSE不变；可选返回detach后的中间量 | 去掉新增返回接口后，`Lance.forward` AST与官方一致 |
| 条件/目标组织 | 通用多模态序列与packer | DataMake明确历史、最近source与唯一当前target | 有意任务适配；目标loss不落在历史或参考图片上 |
| 视觉编码 | 官方ViT与VAE | 冻结编码器，沿用变换与编码路径 | ViT特征及VAE编码不构建参数梯度图 |
| LoRA | 官方通用训练入口不是当前定制双分支PEFT入口 | PEFT0.15.2，冻结基座，只训练指定A/B | 实际可训练范围受检查；不是给全部基座算参数梯度再丢弃 |
| 分布式 | FSDP参数/梯度分片 | DDP复制冻结基座，同步adapter梯度 | 有意后端替换，world-size补偿和累计经检查 |
| 梯度检查点 | PyTorch非重入wrapper，按模块类型选择 | 同一wrapper，加层号选择 | GPU小尺寸数值及梯度一致，见下节 |
| 注意力 | 官方Flex mask与noise/sample隔离 | mask函数不变；缩小独立尾部pad文档 | 保留真实token、样本边界、loss索引和尾部sentinel |
| 位置编码 | Python逐元素sum比较modality数量 | tensor sum，缓存不变数量比较结果 | 位置更新顺序不变；不是重设计RoPE |
| VAE缓存 | 编码后empty_cache | 可配置retain | 只改变缓存释放，编码数学不变 |
| 损失权重 | 每个训练批次跨rank按目标token归约 | GT沿用该口径后累计；chain整窗口归约 | 两种当前方案目标不完全相同，见第5节 |
| 保存/恢复 | 官方通用checkpoint机制 | adapter、具名Adam状态、scheduler、各rank RNG与消费游标；完整标记后发布 | 当前专用机制；不能用“官方load成功”替代自己的恢复合同 |

[AST与文件对比收据](../outputs/optimization_diagnostics/official_training_audit_20261012/official_comparison.json)还确认 `data/data_utils.py` 和 `data/transforms.py` 与该官方提交逐文件一致。注意：推理CFG有本地修改，所以不能把“训练forward一致”扩大成整个模型文件没有修改。

源VAE的 `full_noise` 会在 `Lance.forward` 第267行转为 `full` 后传给mask函数；因此源VAE块、ViT块内部双向，目标noise块内部双向，跨sample隔离。不能只看mask helper不认识 `full_noise` 就判断源块内部因果。

## 4. 梯度检查点：不是手写反向算法

官方 `train/unified_train.py` 第173–176行已经调用：

```python
apply_activation_checkpointing(
    model,
    checkpoint_wrapper_fn=partial(
        checkpoint_wrapper, checkpoint_impl=CheckpointImpl.NO_REENTRANT
    ),
    check_fn=grad_checkpoint_check_fn,
)
```

当前 [GT训练器](../lance/train/datamake_ddp_train.py) 第174–186行、[整链训练器](../lance/train/datamake_chain_pred_x0_ddp_train.py) 第191–203行仍调用这个PyTorch实现，自定义部分只决定哪些层被包裹。当前实际选择0–25层，后10层保存正常激活并照常参与反传。**关闭某层的检查点不等于关闭该层梯度；开启也不等于只更新其中一部分参数。**

非重入实现不要求我们手工把冻结embedding的输入设置成 `requires_grad=True`。LoRA参数是否训练由 `requires_grad` 和优化器参数集决定，与是否重算激活是两件事。

本轮在真实GT1150模型上做了6次forward/backward：无图、有图各比较三种模式。固定权重、输入和随机种子，使用正式Mixed/Packed/VAE路径，人工64×64短视频；不执行optimizer、不保存权重。

| 输入 | 检查点关闭 | 全部36层 | 当前0–25层 |
| --- | ---: | ---: | ---: |
| 无参考图MSE | 0.07666388899 | 相同 | 相同 |
| 有参考图MSE | 0.07432297617 | 相同 | 相同 |
| 对关闭模式的LoRA梯度最大绝对差 | 基准 | 0 | 0 |

两组输入的每token MSE以及**全部1016个LoRA梯度张量逐位相同**，冻结基座均没有梯度。实际包装层号也与配置一致。证据：[checkpoint_modes/evidence.json](../outputs/optimization_diagnostics/official_training_audit_20261012/checkpoint_modes/evidence.json)，复现脚本同目录 `reproduce.py`。

这直接支持当前选择性重算没有改变该验证样本的训练梯度，但不是正式分辨率、长链、多卡通信的全部数值证明。计时含首次编译，不能拿这些秒数重新宣称训练提速。

## 5. 正常训练中的重要差异：GT与整链loss不完全相同

设第k次microbatch、rank r上的目标token损失和为S，数量为N，累计次数为K。省略固定MSE系数：

```text
GT：    L = (1/K) × Σ_k [ Σ_r S(r,k) / Σ_r N(r,k) ]
整链：  L = Σ_整个窗口 S / Σ_整个窗口 N
```

GT对应 `train_utils.py` 第529–530行及 `datamake_ddp_train.py` 第302行；整链对应 `datamake_chain_pred_x0_ddp_train.py` 第309–333行。DDP会平均各rank梯度，因此两者在各自分子上乘world-size抵消这次平均，当前实现没有发现漏乘或多除累计的问题。整链不能再除一次accumulation。

例如两个microbatch分别有2和6个目标token，单token损失分别是p和3p：GT loss为2p，整窗口loss为2.5p，梯度也分别为2和2.5。变长视频会正常出现这种权重差异，不是只有异常数据才有。

整链还把原来的固定前缀调度改成整链窗口，生成历史为noisy-GT监督forward产生的detached pred_x0；这是快速代理历史，不是30步纯噪声rollout。现有代码有明确的设计合同，不能简单判成实现错误；但比较两个run时必须承认这些变量一起改变，不能把全部效果差异归因于是否使用真实历史。

GT分片内部按固定顺序循环；8个shard中4个长度2285、4个2284，同步读取到2285时会在短shard各重复1条。没有因此丢数据，但也不是每个epoch重新全局随机洗牌、每条严格只出现一次。当前“epoch”耗时只是曝光量近似口径。

## 6. 当前恢复兼容问题

[checkpoint模块](../lance/train/datamake_ddp_checkpoint.py) 第172行要求新旧合同严格相等。只读重建比较发现：

| 完整checkpoint | 原合同中已改变的实现文件 | 新增合同文件 |
| --- | --- | --- |
| GT1150 | prefix Dataset、DDP launcher | reference image helper |
| chain850 | 上述两项，online row处理器、Lance模型文件、chain schedule | reference image helper |

准确路径和新旧哈希见 [resume_contract_diff.json](../outputs/optimization_diagnostics/official_training_audit_20261012/resume_contract_diff.json)。本轮比较的是实际磁盘checkpoint记录与当前源码合同，未为此启动完整恢复训练。

结论是：当前入口的严格预检会拒绝旧合同，不能直接声称“现在能原样resume”。这不证明已保存的adapter损坏，也不妨碍受支持的推理加载。续训前应恢复旧运行对应的冻结代码，或建立显式、经过连续/恢复对照验证的迁移；不要直接改旧checkpoint里的哈希。

这与旧Stage2/online-rollout profile的 `config_factory.py` 冻结哈希测试失败是两件事。前者关系到目前保留的两组checkpoint；后者是历史入口合同已过时，不能用它们充当当前DDP路径的完整验收。

另有数据完整性边界：当前旧GT启动验证YAML和manifest哈希，但不逐一重新验证parquet内容；不能据此宣称它能防止所有数据原地替换。整链读取器和新增参考图audit有parquet验证。本轮重新读取当前全部训练分片，未发现上述引用/行数不一致；这不是已经发生数据损坏的证据。

## 7. 两项配置边界问题

### VAE条件dropout非零

真实Dataset→PackedDataset的CPU复现中，VAE dropout=1后只保留target latent形状与8个timestep，但 `packed_vae_token_indexes` 仍有16个索引。模板保留了source span而其tensor被丢弃，后续可能在RoPE或latent赋值处报形状错误。

问题位于官方模板packer分支（当前 `data/dataset_base_train.py` 第585行附近），该行为在9717d91已有，不是本次参考图或检查点优化引入。当前所有条件dropout为0，所以它不能解释已进行训练的质量问题。以后若为CFG训练打开VAE dropout，必须先修复并验证索引、grid与source删除语义。

### 符号链接作为媒体根

prefix Dataset保存 `abspath(media_root)`，但解析媒体路径后使用 `realpath` 与前者做范围比较；若根本身是symlink，相对路径可被误判越界。参考图preflight会resolve根，所以可能出现“审计接受、训练拒绝”。

当前正式 `media_root` 已核实为规范路径，不受影响。这项只需在使用symlink根的数据绑定之前处理，不应混同为所有图片或现有视频路径都有问题。

两项边界的复现结果：[data_boundary_evidence.json](../outputs/optimization_diagnostics/official_training_audit_20261012/data_boundary_evidence.json)；同目录 `reproduce_data_boundaries.py` 可重新执行。

## 8. 验证与下一步

本轮运行了真实GPU六组检查点数值对照、25项优化/PEFT/保存恢复相关CPU回归、32项数据相关CPU回归，以及数据边界复现；不同专项有重叠，不相加为独立覆盖数量。核心文档/数据/引擎回归22＋30＋80＝132项通过。CPU日志与复现结果由本轮诊断目录维护。没有重跑正式八卡训练或把旧完整测试集宣称为全绿。

建议保留当前部分检查点、PEFT/DDP、位置求和与minimal padding；本轮没有证据要求回退这些优化。续训前先解决代码版本与checkpoint合同；需要严格比较GT与自回填时，另设采样和归约一致的对照。新增参考图继续按独立数据/独立run验证，不把本次梯度一致性当成编辑效果已提升。
