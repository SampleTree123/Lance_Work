# Lance 训练代码结构索引（更新至 2026-09-07）

当前优先阅读[Stage6代码入口表](./datamake_stage6_stage2_lora_preparation_20260907.md#实现入口和数据恢复)，再按需阅读第六节 Stage5 与 [配置索引](../configs/README.md)。A/B 已暂停；Stage2仅保留基座，不具备全参断点恢复状态。第三节是历史候选，不是当前主循环。tiny/Stage1结果已[退役](./datamake_lance_storage_cleanup_20260906.md)。

## 一、官方原始训练代码

上游仓库位置：`10_research/model_experiments/lance/lance/`

冻结 commit：`9717d9160ed16fedfdad5ce39ccbc6c9d69695e0`

官方入口分两层：

- `lance/scripts/sft_lance_generation.sh`：官方命令示例和参数组合。
- `lance/train/unified_train.py`：官方实际训练主循环。

当前 working clone 的 `unified_train.py` 已叠加 DataMake patch，因此不要把工作区文件误认为 pristine official。查看原始版本应使用：

```bash
git -C 10_research/model_experiments/lance/lance \
  show 9717d9160ed16fedfdad5ce39ccbc6c9d69695e0:train/unified_train.py
```

或查看官方 launch 示例：

```bash
git -C 10_research/model_experiments/lance/lance \
  show 9717d9160ed16fedfdad5ce39ccbc6c9d69695e0:scripts/sft_lance_generation.sh
```

DataMake 没有另复制一份 600 行左右的官方主循环；以固定 commit 加 patch 的方式保存来源关系，避免三份几乎相同的文件长期漂移。

## 二、第二次训练（stage2，全参）

第二次训练不是一个完全独立重写的主循环，而是“冻结 profile + DataMake launcher + patched upstream core”的组合：

```text
jobs/datamake_dialogue_stage2_r5x3_region_v1.sbatch
  -> scripts/run_datamake_formal_training.py
     -> configs/datamake_dialogue_stage2_r5x3_region_v1.json
        -> lance/train/unified_train.py
           -> lance/data/datasets_factory/dataset_datamake_multiturn_v2v_local.py
           -> lance/train/train_utils.py (region-weighted loss)
           -> lance/train/fsdp_utils.py (完整 checkpoint/resume)
```

建议阅读顺序：

1. `configs/datamake_dialogue_stage2_r5x3_region_v1.json`：完整冻结的模型、数据、优化、W&B、checkpoint 参数，也是最接近“这次到底训练了什么”的文件。
2. `jobs/datamake_dialogue_stage2_r5x3_region_v1.sbatch`：集群资源、环境和日志定向。
3. `scripts/run_datamake_formal_training.py`：profile 校验、路径/hash 检查、torchrun 命令构造与 resume 保护。
4. `lance/data/datasets_factory/dataset_datamake_multiturn_v2v_local.py`：多轮角色编码的核心。
5. `lance/train/unified_train.py`：VAE 编码、前向、loss、反向、保存主循环。
6. `lance/train/train_utils.py`：编辑区域权重与 loss reduction。
7. `lance/train/fsdp_utils.py`：FSDP full-state checkpoint、optimizer shards、complete marker 与 retention。

相对官方 commit 的改动由 `patches/0004`～`0009` 记录，第二阶段新增重点是：

- `0009-datamake-round-region-weighted-loss.patch`
- `scripts/build_datamake_round_weighted_train.py`

Stage2的配方和来源保留作历史追溯；其原始Stage1初始化权重及全参optimizer已删除，不能直接照旧脚本恢复。当前B使用Stage2 step3669 base-only模型新建LoRA。

## 三、历史评审方案（stage3 候选，LoRA）

新方案刻意使用独立入口，不把 LoRA 逻辑继续塞进历史 `unified_train.py`：

```text
train/datamake_lora_generation_train.py
  -> 解析并移除 DataMake-only LoRA/history 参数
  -> 校验 r=64、lr=1e-4、freeze 与 region-loss 契约
  -> 调用 train/datamake_generation_lora.py 挂接 LoRA
  -> 在当前进程给 unified_train 的 load/save extension point 安装 hook
  -> 调用原有 train/unified_train.py 主循环
```

核心文件：

- `lance/train/datamake_generation_lora.py`
  - `GenerationLoRAConfig`
  - `LoRALinear`
  - `generation_lora_targets`
  - `apply_generation_lora`
  - LoRA checkpoint inference loader
- `lance/train/datamake_lora_generation_train.py`
  - `parse_lora_arguments`
  - `validate_upstream_contract`
  - `build_training_contract`
  - `install_training_hooks`
- `lance/datamake_lora_multiturn_chat.py`
  - 安装 LoRA-aware loader 后复用已有 `multiturn_chat.py`

数据回灌路径：

```text
lance/datamake_rollout.py
  -> 用冻结 checkpoint 自回归生成每条链的 g1...gT
  -> 每 shard 写 manifest + 媒体/hash

scripts/build_datamake_history_views.py
  -> teacher_forced
  -> rollout_vit_only
  -> rollout_full
  -> 新 parquet + lance_dataset.yaml + manifest
```

审计与测试：

- `scripts/inspect_datamake_generation_lora.py`
- `reports/datamake_stage3_lora_target_audit_20260903.json`
- `tests/legacy/test_datamake_generation_lora.py`
- `tests/test_build_datamake_history_views.py`

参数评审文件：

- `configs/datamake_dialogue_stage3_lora_r64_review_v1.json`

设计与风险说明：

- `reports/datamake_stage3_lora_history_design_20260903.md`

## 四、三代入口的本质区别

| 版本 | 主入口 | 可训练参数 | 历史条件 | 区域损失 |
|---|---|---|---|---|
| 官方 | `train/unified_train.py` | 由官方 freeze flags 决定 | 官方 interleave 数据 | 无 DataMake region weighting |
| stage2 | 同一主循环 + DataMake patches | Lance core 全参；ViT/VAE/embedding 冻结 | 全部 rendered GT history | 开启 |
| stage3 候选 | `train/datamake_lora_generation_train.py` | 仅 generation-side LoRA A/B | 可选 GT 或 frozen-model rollout | A/B 首轮关闭；rollout full 强制关闭 |

stage3 复用 stage2 已验证的数据打包、loss 主循环、W&B 和 FSDP checkpoint 基础设施，但把新风险限制在独立文件与运行时 hook 中。这使代码审查可以集中在 LoRA target、冻结边界、history view 和 checkpoint topology 四个点。

## 五、Stage 4：一行一链的在线 Rollout LoRA

2026-09-04 冻结的新方案不再通过离线 history parquet 调用 `unified_train.py`。它保留 stage3 的 LoRA 层，但使用独立的链级主循环：

```text
jobs/datamake_dialogue_online_rollout_lora_r64_v2*.sbatch
  -> scripts/run_datamake_online_rollout_lora_training.py
     -> configs/datamake_dialogue_online_rollout_lora_r64_v2.json
        -> lance/train/datamake_online_rollout_lora_train.py
           -> lance/train/datamake_online_rollout.py
           -> lance/train/datamake_generation_lora.py
           -> lance/train/datamake_lora_checkpoint.py
           -> lance/data/datasets_factory/dataset_datamake_multiturn_v2v_local.py
           -> lance/data/datasets_factory/datamake_online_rollout_turn.py
```

阅读顺序：

1. `configs/datamake_dialogue_online_rollout_lora_r64_v2.json`：全部冻结参数、source/data/base hash、checkpoint v5 与 `training_authorized=false`。
2. `scripts/run_datamake_online_rollout_lora_training.py`：重复参数、hash、四卡、W&B、adapter resume、launch manifest 与正式授权保护。
3. `lance/train/datamake_online_rollout.py`：一行一链 schema、等长链调度、稳定 rollout seed 和每轮输入替换。
4. `lance/train/datamake_online_rollout_lora_train.py`：逐轮 MSE/backward、在线 30-step rollout、梯度累计 2、W&B 和保存调用。
5. `lance/train/datamake_lora_checkpoint.py`：只保存 adapter，另存 optimizer/scheduler/cursor/RNG 并严格恢复。
6. `lance/data/datasets_factory/dataset_datamake_multiturn_v2v_local.py`：保留 Stage 2 已冻结的路径式角色编码，不改变旧 profile 的源码哈希。
7. `lance/data/datasets_factory/datamake_online_rollout_turn.py`：Stage 4 独立适配层；`video_paths` 保留 GT 审计，`video_inputs` 接受生成的内存 FP16 视频。
8. `lance/datamake_lora_multiturn_chat.py`：推理时保持 `--model_path` 指向该 adapter 实际使用的 base（A为官方，B为Stage2），并用独立 `--datamake_lora_checkpoint` 指向 adapter；loader 严格执行 base → LoRA topology → adapter 的加载顺序。

与 stage3 的关键区别：

| 方面 | stage3 评审实现 | stage4 冻结实现 |
|---|---|---|
| 数据粒度 | 每轮一个 prefix | 每条链一行，训练主循环内顺序展开 |
| rollout 时点 | 训练前离线生成 | 训练时使用当前 LoRA 在线生成 |
| 历史传输 | MP4 + history parquet | detach 后 CPU FP16 CTHW 内存张量，无 codec roundtrip |
| loss | 每个 prefix 一次上游 loss | 每个 target 一次原生 latent MSE，window 内所有 target 等权 |
| checkpoint | 当时仍复用 full-state 保存 | adapter-only 权重 + optimizer/scheduler/cursor/RNG |
| 正式状态 | 评审候选 | checkpoint-v5 四卡逐 tensor smoke 已通过；full-rollout 正式训练未启动 |

快速审查后，rollout noise seed 已在传入 Lance 前抵消上游内部 rank offset；训练入口也会拒绝 QK norm、ViT type、latent patch/frame/latent 上限、visual path、ViT connector freeze 或 FSDP topology 漂移。rollout 另记录 full-param summon 前后与生成峰值显存，供 GPU smoke 判断该实现是否能在 H200 上安全运行。

完整实现、数学归一化和验证边界见 [`datamake_stage4_online_rollout_lora_implementation_20260904.md`](./datamake_stage4_online_rollout_lora_implementation_20260904.md)，后续对照见 [`datamake_lora_ablation_registry_20260904.md`](./datamake_lora_ablation_registry_20260904.md)。

## 六、Stage 5：复用训练 Forward 的单步 `pred_x0` 历史

Stage 5 保留 Stage 4 的一行一链主循环和 checkpoint-v5，只替换中间历史的取得方式：

```text
jobs/datamake_dialogue_one_step_x0_lora_r64_v3*.sbatch
  -> scripts/run_datamake_online_rollout_lora_training.py
     -> configs/datamake_dialogue_one_step_x0_lora_r64_v3.json
        -> lance/train/datamake_online_rollout_lora_train.py
           -> Lance.forward(..., return_flow_intermediates=True)
           -> pred_x0 = noisy_target - timestep * predicted_velocity
           -> frozen VAE decode -> detached CPU FP16 history
           -> 既有下一轮 ViT + direct-source VAE 路径
```

当前B复用同一实现，独立profile为 `configs/datamake_dialogue_one_step_x0_lora_r64_stage2base_v1.json`；其基座选择和启动方式以[准备报告](./datamake_stage2base_lora_preparation_20260905.md)为准。A/B目前不自动续跑。

重点代码：

- `lance/modeling/lance/lance.py`：在显式 opt-in 时返回同一次 MSE forward 已有的 noisy target、predicted velocity 和 timestep；默认路径仍只返回原有四个 loss 字段。
- `lance/train/datamake_online_rollout_lora_train.py`：`predict_clean_latent_patches()` 执行代数反推，`decode_one_step_x0_history()` 恢复目标 latent 网格并解码历史。
- `lance/train/datamake_online_rollout.py`：用 `one_step_x0_history` 契约固定额外 diffusion steps=0 和 KV cache=false。
- `patches/legacy/0013-datamake-one-step-x0-history.patch`：相对 Stage 4 checkpoint-v5 基线的 Lance 内部改动。

启动前复查后，训练入口还要求实际 `training_args.timestep_shift`、optimization profile 与 rollout profile 三者均为 `4.0`；这项绑定不改变已完成 smoke 的命令或数值路径。

| 方面 | Stage 4 full rollout | Stage 5 one-step `pred_x0` |
|---|---|---|
| 中间历史起点 | 独立随机 noise | rendered GT 加噪的训练 `z_t` |
| 每个历史的额外采样 | 30 diffusion steps | 0；复用已有训练 forward |
| CFG / KV cache | CFG1 / 开启 | 单 conditional forward（等价 CFG1）/ 不使用 |
| 后续 ViT/VAE 输入 | detached VAE-decoded CPU FP16 视频 | 相同 |
| target loss / LoRA / optimizer | Stage 4 冻结值 | 完全相同 |
| 结论边界 | 接近真实训练时在线推理分布 | noisy-GT-conditioned 快速代理，不等价于完整 rollout |

四卡连续 3-step Job `122843` 已完成，平均 step time 为 `141.65s`，相对同 schedule full rollout 的 `270.89s` 提速 `1.91×`。保存恢复逐 tensor Gate 与最终状态见 [`Stage 5 报告`](./datamake_stage5_one_step_x0_history_20260904.md)。
