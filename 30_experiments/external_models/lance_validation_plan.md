# Lance 能力验证计划

> 创建日期：2026-06-28。
> 状态：待用户确认下载策略和运行环境后执行。

## 目标

验证 Lance 在视频编辑和多轮一致性上的实际能力，作为 DataMake 数据构建的外部基线：

- 单轮视频编辑是否能稳定遵循指令。
- 编辑后主体身份、动作、背景和时序是否保持。
- 多轮编辑是否会漂移，是否能执行“加上再去掉 / 改动后回退”等一致性任务。
- 失败模式如何反推 UE 合成数据优先级。

## 来源

- GitHub: https://github.com/bytedance/Lance
- Paper: https://arxiv.org/abs/2605.18678
- Model: https://huggingface.co/bytedance-research/Lance
- 阅读笔记：[`../../02_research/papers/lance.md`](../../02_research/papers/lance.md)

## 本地路径方案

所有下载和输出都在当前 DataMake 目录下，且都被 `.gitignore` 排除：

```text
external/repos/Lance/                 # Lance 代码
external/models/Lance/                # Lance 权重
external/hf_cache/Lance/              # HF 下载缓存
outputs/model_validation/lance/       # 生成结果
logs/model_validation/lance/          # 小日志，可按需摘录进文档
```

环境名按项目约定使用 `xks_` 前缀：

```text
xks_lance
```

## 下载范围

不建议整仓库下载 HF demo assets。优先只下载视频编辑验证需要的权重和配置：

| 路径 | 用途 | 约大小 |
|------|------|--------|
| `Lance_3B_Video/model.safetensors` + tokenizer/config | 视频生成/编辑主模型 | 约 14.2GB |
| `Qwen2.5-VL-ViT/vit.safetensors` + config | 视频/图片理解侧 ViT | 约 1.34GB |
| `Wan2.2_VAE.pth` | 视频 VAE | 约 2.82GB |
| `*.json` / tokenizer files | 推理配置 | 很小 |

实际落盘预算建议按 **25-30GB** 预留，因为还会有 git repo、HF cache、conda env、日志和少量输出。

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

- 克隆 Lance 代码到 `external/repos/Lance/`。
- 读 `inference_lance.sh`、`config/examples/video_edit_example.json`。
- 确认自定义 `CONFIG_PATH` 的格式。
- 确认是否使用 SLURM 跑推理，避免在登录节点长时间占 GPU。

### 阶段 1：最小权重下载

只下载上文列出的文件。建议用 `huggingface_hub.snapshot_download` 并指定 `allow_patterns`，避免把 demo 视频和网页资产拉下来。

### 阶段 2：官方样例 smoke test

先跑官方 `video_edit` 默认样例：

```bash
bash inference_lance.sh \
  --TASK_NAME video_edit \
  --MODEL_PATH external/models/Lance/Lance_3B_Video \
  --RESOLUTION video_480p \
  --SAVE_PATH_GEN outputs/model_validation/lance/smoke_video_edit
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

### 阶段 4：多轮一致性

同一个输入连续编辑：

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

## 需要用户确认

1. 是否现在下载 Lance 权重，且只下载视频分支。
2. 是否在 H200 节点上创建 `xks_lance` 环境。
3. 是否接受 25-30GB 的初始落盘预算和可能较长的 `flash-attn` 环境调试时间。

确认后再执行下载和环境安装。
