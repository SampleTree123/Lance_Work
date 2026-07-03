# Lance 能力验证计划

> 创建日期：2026-06-28；模型文件树复核日期：2026-07-01；执行状态更新：2026-07-03。
> 状态：视频分支权重、`xks_lance` 环境和 `video_edit` 脚本已可用；batch8 连续单轮测试已跑完。真多轮编辑逻辑尚未实现。

## 目标

验证 Lance 在视频编辑上的实际能力，作为 DataMake 数据构建的外部基线：

- 单轮视频编辑是否能稳定遵循指令。
- 编辑后主体身份、动作、背景和时序是否保持。
- 真多轮编辑是否会漂移，需要先实现正确的多轮调用逻辑后再测试。
- 如后续真多轮测试仍有价值，再判断其失败模式是否能反推 UE 合成数据优先级。

## 来源

- GitHub: https://github.com/bytedance/Lance
- Paper: https://arxiv.org/abs/2605.18678
- Model: https://huggingface.co/bytedance-research/Lance
- 阅读笔记：[`../../papers/lance.md`](../../papers/lance.md)

## 本地路径方案

可运行权重、输入、输出和日志都在当前 DataMake 目录下，且相关大文件路径都被 `.gitignore` 排除：

```text
10_research/model_experiments/lance/lance/          # Lance 代码
10_research/model_experiments/lance/models/Lance/   # Lance 权重
10_research/model_experiments/lance/inputs/         # 自测输入和 prompt
10_research/model_experiments/lance/outputs/        # 生成结果
10_research/model_experiments/lance/logs/           # 运行日志和自动生成 config
```

当前实际使用的 Hugging Face cache 是用户已配置的 scratch 全局路径：

```text
/scratch/prj0000000275/jcy/.cache/huggingface
```

可运行权重仍放在项目内：

```text
10_research/model_experiments/lance/models/Lance/
10_research/model_experiments/lance/lance/downloads -> ../models/Lance
```

这样避免重复下载已有 HF cache，同时 Lance 官方脚本仍可使用 `downloads/Lance_3B_Video`。

环境名按项目约定使用 `xks_` 前缀：

```text
xks_lance
```

## 下载范围

不建议整仓库下载 HF demo assets。优先只下载视频编辑验证需要的权重和配置：

| 路径 | 用途 | 约大小 |
|------|------|--------|
| `Lance_3B_Video/model.safetensors` + tokenizer/config | 视频生成/编辑主模型；支持 `t2v`、`i2v`、`video_edit`、`x2t_video` | 约 14.2GB |
| `Qwen2.5-VL-ViT/vit.safetensors` + config | 视频/图片理解侧 ViT | 约 1.34GB |
| `Wan2.2_VAE.pth` | 视频 VAE | 约 2.82GB |
| `*.json` / tokenizer files | 推理配置 | 很小 |

实际落盘预算建议按 **25-30GB** 预留，因为还会有 git repo、HF cache、conda env、日志和少量输出。

`Lance_3B/` 是图片分支，主要用于 `t2i`、`image_edit`、`x2t_image`。本项目第一轮不下载它，避免多占约 12.37GB。

## 已执行摘要（2026-07-03）

- `xks_lance` 环境已创建并验证：Python 3.11、PyTorch `2.8.0+cu126`、CUDA `12.6`、`flash-attn 2.8.3`。
- Lance 代码位于 `10_research/model_experiments/lance/lance/`，commit `9717d91`。
- 视频分支最小权重已下载到 `10_research/model_experiments/lance/models/Lance/`，约 18GB：
  - `Lance_3B_Video/model.safetensors`
  - `Qwen2.5-VL-ViT/vit.safetensors`
  - `Wan2.2_VAE.pth`
- 未下载 `Lance_3B/` 图片分支，未下载 HF demo assets。
- 官方 `video_edit` smoke test 已在 H200 上跑通，能加载模型、读取官方样例、输出 MP4 和 `prompt.json`。
- 已新增快速脚本：`10_research/model_experiments/lance/scripts/run_video_edit.sh`，支持单轮和“上一轮输出回灌下一轮”的连续单轮 prompt。
- Batch8 公开视频测试已完成 8 个领域的三次连续单轮调用；`6.mp4`、`7.mp4` 原始文件损坏，已用 clean 版在 `94644` allocation 上补跑完成。
- 重要校正：batch8 不是 Lance 真多轮编辑验证。当前脚本没有把多轮 prompt、原始视频和历史上下文一起交给模型，只是多次独立调用单轮 `video_edit`。

详细记录见 [`reports/video_edit_batch8_report.md`](./reports/video_edit_batch8_report.md)。

## 环境要求

官方 README 给出的要求：

- Python 3.10+；示例用 Python 3.11。
- CUDA 12.4+。
- PyTorch 2.8.0 + cu126 或 PyTorch 2.5.1 + cu124。
- `flash-attn` 版本必须匹配 PyTorch/CUDA/Python。
- 至少 40GB VRAM。

H200 显存足够，但执行前要重新确认：

```bash
nvidia-smi
python --version
nvcc --version
```

集群上如果没有系统 CUDA toolkit，也可以只依赖 PyTorch wheel 的 CUDA runtime；但 `flash-attn` 安装仍可能需要编译链或匹配 wheel。

## 执行阶段

### 阶段 0：不下载权重的预检查

- 克隆 Lance 代码到 `10_research/model_experiments/lance/lance/`。
- 读 `inference_lance.sh`、`config/examples/video_edit_example.json`。
- 确认自定义 `CONFIG_PATH` 的格式。
- 确认是否使用 SLURM 跑推理，避免在登录节点长时间占 GPU。

### 阶段 1：最小权重下载

只下载上文列出的文件。建议用 `huggingface_hub.snapshot_download` 并指定 `allow_patterns`，避免把 demo 视频和网页资产拉下来。

### 阶段 2：官方样例 smoke test

先跑官方 `video_edit` 默认样例：

```bash
cd 10_research/model_experiments/lance/lance
bash inference_lance.sh \
  --TASK_NAME video_edit \
  --MODEL_PATH downloads/Lance_3B_Video \
  --RESOLUTION video_480p \
  --SAVE_PATH_GEN ../outputs/smoke_video_edit
```

验收：

- 能完整加载模型；
- 能输出视频；
- `prompt.json` 写出；
- 日志里没有 CUDA OOM、缺依赖、解码失败。

### 阶段 3：DataMake 任务样例

在还没有 UE MVP 输出前，先用公开视频或官方样例测以下 prompt 类型：

- 增加/去除道具。
- 改衣服颜色或材质。
- 改背景/天气/光照。
- 让主体保持动作不变，只改局部属性。

等 UE MVP 有样本后，再用我们的 `video_in` 做同样编辑，与 UE ground truth 对比。

### 阶段 4：真多轮一致性（待实现）

当前还没有实现真多轮编辑调用。目标形式应当让模型在一次任务上下文中看到原始视频和多步编辑意图，而不是只把上一轮输出视频作为下一次独立输入。

需要先研究 Lance 官方 `video_edit` 配置和 interleave 数据格式，确认是否支持类似下面的上下文组织：

```text
C0: 原视频
C1: 加一个道具
C2: 改变道具颜色
C3: 移除道具，要求回到 C0 的主体和背景状态
```

记录：

- 主体身份是否漂移；
- 动作节奏是否改变；
- 背景是否积累幻觉；
- 回退是否真的回到旧状态；
- 每轮画质是否退化。

## 后续待办

1. 先实现或接入 Lance 真多轮编辑调用逻辑，避免把连续单轮误当成多轮。
2. 用少量样例验证真多轮脚本能正常生成，再决定是否扩展 batch。
3. 如需图片任务，再单独决定是否下载 `Lance_3B/` 图片分支。
