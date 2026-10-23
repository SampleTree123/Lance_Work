# UE＋CoinVE 混合数据接入

> 日期：2026-09-11。实现与输出所有者：[训练接入](../training_integration.md)。范围：用户要求检查清理后的目录、生成引用媒体的混合数据集，优先解决成对时间窗口；时序内容筛查、复合编辑筛选和原视频分组重划分暂缓。本次不启动正式训练。

## 清理后的输入

Stage5 B训练结果、Stage2基座、三份合成数据索引、released的640个视频、外部CoinVE的8000个视频仍可访问。旧Stage5 A/Stage6结果和checkpoint_migrations已经删除，不恢复或重建这些历史结果。Stage5 B绑定的22份实现文件哈希保持一致。

合成训练输入沿用Stage2 R5×3前缀；验证/测试沿用基础split。CoinVE输入为外部`coinve_ablation_v1/coinve_4k_pool.csv`和对应`technical_probe.jsonl`，使用冻结清单的source_local/target_local绝对路径。没有引入此前搁置的另一份真实4K数据，也没有读取外部`mixed_2k2k_pool.csv`。

## 新数据组织

数据根：[datamake_coinve4k_mixed_r5x3_seed20260911_v1](../outputs/training_data/datamake_coinve4k_mixed_r5x3_seed20260911_v1/)。这是索引包，不是视频副本。

```text
datamake_coinve4k_mixed_r5x3_seed20260911_v1/
  README.md
  split_manifest.json          # 输入哈希、划分、分片哈希、裁剪策略
  sampling_manifest.json       # 重复策略、训练组成、rank/worker分配
  profile_data_binding.json    # 后续新profile应使用的数据路径/哈希和data_seed
  coinve_provenance.jsonl      # 原CSV完整字段和本次固定裁剪窗口
  validation_report.json      # 全量引用/窗口检查、真实媒体CPU pack证据
  train/
    lance_dataset.yaml
    mixed-00000-of-00008.parquet ... mixed-00007-of-00008.parquet
  validation/
    lance_dataset.yaml
    mixed-00000-of-00001.parquet
  test/
    lance_dataset.yaml
    mixed-00000-of-00001.parquet
```

| 划分 | 合成前缀记录 | CoinVE单轮记录 | 总记录 | 独立链/编辑对 |
| --- | ---: | ---: | ---: | ---: |
| train | 14,675 | 3,601 | 18,276 | 7,201 |
| validation | 754 | 195 | 949 | 395 |
| test | 763 | 204 | 967 | 404 |

合成数据共4000条链、15000个唯一前缀，CoinVE共4000个编辑对。训练中的合成R5重复规则原样保留，因此训练记录占比约80.3%合成、19.7%真实；这不是1:1重采样。全包共有19000个唯一监督样本，含R5重复后的总记录为20192。合成数据原字段的行多重集合逐split核对，不丢失历史轮次，也不改变原始提示词或路径。

每行继续使用`sample_id/chain_id/target_round/prompts/video_paths`，新增`dataset_origin/source_sample_id/split/crop_policy/crop_start_seconds/crop_duration_seconds/media_metadata_json`。合成路径仍相对于YAML的released `media_root`；CoinVE使用其原存储位置的绝对路径。索引共引用8640个唯一媒体文件，生成器没有复制、重编码或建立视频软链接。外部路径必须在训练节点可读；迁移视频存储位置后需重新生成索引和绑定哈希。

CoinVE的多个编辑要求保留在一个完整prompt内，`target_round=context_length=1`，仅最终target承担损失，不伪造中间视频和多轮真值。保留两套原有split；链/样本标识不跨split不等于同一原始长视频完全隔离，后者按用户决定暂缓。

## 成对时间窗口

策略：`paired_absolute_5s_12fps_kn1_fixed_v1`。

1. 从有效技术探测读取实际帧数和FPS，计算`min(source_duration,target_duration)-5`。
2. 用seed20260911和sample_id的SHA256确定共同起点，向下保留到纳秒，并写入Parquet和provenance。
3. source/target都截取`[start,start+5s)`。解码器用各自原生浮点FPS转换帧号，不先取整FPS，也不对完整视频分别缩放。
4. 复用项目已有`MultiClipsFrameSampler`：temporal4、12FPS、max_duration5、assert_seconds=true、kn+1。VAE为61帧；ViT重复最后一帧到62帧。空间变换、角色布局、token打包及损失逻辑沿用现有代码。

这版每个CoinVE样本的窗口在所有epoch固定；不同于对方每epoch重新选择起点，但两侧共同时间范围的语义一致。固定窗口便于复现和断点恢复，也避免在这一轮数据合并中额外改变训练游标。未来若需要每epoch换窗，应显式升级数据/恢复合同。

合成数据使用原路径和原采样器设置，不因CoinVE而全局切换5秒/61帧。新Dataset继承旧role-aware处理器，仅在CoinVE行用局部对象替换媒体读取，source/target共享一份裁剪参数；不会把上一条真实数据的裁剪状态留给下一条合成数据。

## 实现入口与复现

- [构建器](../scripts/build_datamake_coinve_mixed_data.py)：`active`；创建新目录，验证输入哈希、全部媒体存在及CoinVE文件大小，生成索引、YAML、来源与绑定文件；拒绝覆盖已有输出。
- [审计器](../scripts/inspect_datamake_coinve_mixed_data.py)：`active`；全量检查原合成记录等价、引用、窗口边界、8分片实际索引覆盖，可执行真实CPU pack。
- 上游ignored clone适配器：`lance/data/datasets_factory/dataset_datamake_mixed_v2v_local.py`；由[patch0022](../patches/legacy/0022-coinve-paired-window-mixed-data.patch)保存。
- `train/datamake_stage2_lora_data.py`导入时注册新Dataset键`datamake_mixed_v2v_local`，供优化DDP/IndexedPrefixDataset入口构建PackedDataset。旧Stage5 registry和Dataset文件不变；其他独立读者若使用新YAML，需先显式调用`register_mixed_dataset()`，不能用旧通用入口绕过裁剪。
- [DDP launcher](../scripts/run_datamake_ddp_training.py)的实现合同加入新适配器及采样器哈希；旧DDP验证合同不可复用。Stage5 B冻结文件合同未变化。

```bash
/scratch/prj0000000275/jcy/.conda/envs/xks_lance/bin/python \
  10_research/model_experiments/lance/scripts/build_datamake_coinve_mixed_data.py

/scratch/prj0000000275/jcy/.conda/envs/xks_lance/bin/python \
  10_research/model_experiments/lance/scripts/inspect_datamake_coinve_mixed_data.py \
  --dataset-root /scratch/prj0000000275/jcy/xks/DataMake/10_research/model_experiments/lance/outputs/training_data/datamake_coinve4k_mixed_r5x3_seed20260911_v1 \
  --real-pack
```

训练分8个Parquet，4卡×2个逻辑worker，data_seed2220。每rank首次遍历4569条，两个worker分别2285/2284条，全局18276条均被访问，完整首次遍历无额外同步填充。这个计数是microstep/记录覆盖，不是optimizer step；正式训练仍需沿用累计和总步数配置。

后续复制双分支DDP模板及其source_profile，将`profile_data_binding.json`的数据字段同步合入两者，替换旧data_seed及旧数据量说明，并使用独立run/W&B身份。该绑定是配置片段，不是可执行训练profile；它没有擅自决定新实验的步数、学习率预算或提交作业。

## 验证范围

全量数据审核和CPU真实媒体结果以[validation_report.json](../outputs/training_data/datamake_coinve4k_mixed_r5x3_seed20260911_v1/validation_report.json)为准。6条真实媒体CPU pack通过（4条CoinVE含train/validation/test、合成R1/R5），CoinVE的source/target为`[3,61,352,624]`，合成样例仍为`[3,57,352,624]`；同一CoinVE索引再次读取的文本和VAE输入完全一致。全4000对窗口索引核验中，两侧采样时间差最大约0.04165秒，属于原生帧量化范围，不能由此推断内容时序同步。CPU回归130项通过；覆盖时长不等、FPS不等、5秒边界、同一窗口61/62帧、role/loss布局与跨行裁剪状态隔离。Patch逆向适用检查、隔离目录重放逐文件一致和Stage5 B全部22份冻结实现哈希检查通过。132项核心CPU测试通过；文档独立子系统及跨层检查通过，114文档/679链接，零错误和警告。

本次不运行GPU loss/backward、四卡恢复Gate或正式训练。数据准备完成不等于混合训练的GPU启动验证已完成，也不解决用户暂缓的内容时序噪声问题。主计划L06/L08质量验收保持in_progress，L10优化结论及WF-90 released不变。
