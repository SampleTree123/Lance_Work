# Lance 阅读笔记

> 来源登记与初读日期：2026-06-28；模型文件树复核与 PDF 下载日期：2026-07-01；实测状态更新：2026-07-03。
> 状态：已读 GitHub README、Hugging Face 文件清单、arXiv 论文文本；PDF 已本地下载；视频分支权重已下载并完成 `video_edit` 初轮验证。

## 来源

- GitHub: https://github.com/bytedance/Lance
- Project page: https://lance-project.github.io/
- Paper: https://arxiv.org/abs/2605.18678
- Model: https://huggingface.co/bytedance-research/Lance
- HF Space: https://huggingface.co/spaces/bytedance-research/Lance
- Local PDF: `10_research/papers/pdfs/lance_2605.18678.pdf`（本地忽略目录，不进 Git）

## 它是什么

Lance 是 ByteDance 发布的 3B active parameter 原生统一多模态模型，覆盖图片/视频的理解、生成和编辑。官方 README 明确支持：

- `t2i` / `t2v`
- `i2v`
- `image_edit` / `video_edit`
- `x2t_image` / `x2t_video`

官方也强调它是 research artifact，不是成熟产品模型。发布 checkpoint 的训练覆盖 768x768 图片生成和 480p、12 FPS 视频生成；推理要求至少 40GB 显存。

## 方法要点

论文核心不是单纯扩大模型，而是“多任务协同”：

- 统一上下文建模：文本、图片、视频、语义 token、生成 latent token 被组织到 interleaved multimodal sequence。
- 解耦能力路径：理解走语义视觉 token + 自回归语言建模；生成/编辑走 VAE latent + flow matching。
- 双专家架构：理解 expert 与生成 expert 共享上下文但分开处理，降低理解/生成目标冲突。
- 视觉表示分两类：
  - Qwen2.5-VL ViT 语义 token 用于理解；
  - Wan2.2 3D causal VAE latent 用于生成和编辑。
- MaPE（modality-aware rotary positional encoding）用于减少不同视觉 token 群之间的位置干扰。

## 训练数据与任务

论文把编辑数据作为训练主成分，而不是下游补丁：

- PT：约 1B image-text 与 140M video-text pair。
- CT：加入多任务数据，包括约 2.8M image editing、2.6M video editing、3.6M subject-driven image generation、1M subject-driven video generation。
- SFT：加入高质量任务数据，包括约 84K image editing、9K video editing、5.5K subject-driven video generation。
- 论文消融显示，加入理解数据和多任务生成数据会同时提升生成、编辑和理解表现。

这点对本项目很关键：它支持我们把 UE 精确编辑数据、真实视频数据、大模型生成数据放到统一 schema，而不是把它们当成互不相干的来源。

## 与 DataMake 的关系

Lance 对我们有两类价值：

1. **作为外部能力基线**：先测 `video_edit` 和多轮一致性，判断现有开放模型在“多轮视频编辑”上差到什么程度。
2. **反推数据需求**：如果 Lance 在回退编辑、身份保持、服装/道具一致性上失败，这些失败样例可以转成我们 UE 合成数据的优先编辑类型。

建议优先验证：

- 单轮 `video_edit`：低风险局部编辑、服装/道具/背景/光照指令。
- 多轮一致性：A→B→C，再要求部分回退到 B 或 A；执行前必须先确认是真多轮上下文调用，而不是连续单轮回灌。
- 身份/动作保持：编辑外观或场景时，动作轨迹和主体身份是否稳定。
- 文本渲染不要作为第一优先级；论文和 README 都显示文字相关能力不是它的强项。

## 权重与环境

官方推理环境：

- Python 3.10+；README 示例用 Python 3.11。
- CUDA 12.4+。
- PyTorch 2.8.0 + cu126 或 PyTorch 2.5.1 + cu124。
- `flash-attn` 需要与 PyTorch/CUDA/Python 匹配。
- 至少 40GB VRAM。

只做视频编辑验证时，不建议下载 HF 仓库里的 demo assets。最小有用下载范围应是：

- `Lance_3B_Video/*`
- `Qwen2.5-VL-ViT/*`
- `Wan2.2_VAE.pth`
- 必要的 `*.json`、tokenizer 和 config 文件

详见 [`../model_experiments/lance/validation_plan.md`](../model_experiments/lance/validation_plan.md)。

## HF 模型目录复核（2026-07-01）

Hugging Face 仓库当前不是一堆同级 checkpoint，而是两个主 Lance 权重目录加两个共享组件：

| 路径 | 作用 | 文件大小 |
|------|------|----------|
| `Lance_3B/` | 图片相关任务：`t2i`、`image_edit`、`x2t_image` | `model.safetensors` 约 12.37GB |
| `Lance_3B_Video/` | 视频相关任务：`t2v`、`i2v`、`video_edit`、`x2t_video` | `model.safetensors` 约 14.21GB |
| `Qwen2.5-VL-ViT/` | 语义视觉编码器，用于理解侧视觉 token | `vit.safetensors` 约 1.34GB |
| `Wan2.2_VAE.pth` | 视频 VAE，用于生成/编辑侧 latent | 约 2.82GB |
| `assets/` | 官方 demo 图片、视频、网页素材 | 不建议下载 |

当前 DataMake 优先验证的是视频编辑和后续真多轮一致性，因此第一轮只选 `Lance_3B_Video`。`Lance_3B` 暂不下载，除非后续要专门测图片编辑或图片理解。

## 实测后暂定判断（2026-07-03）

- Lance 值得优先验证，因为它明确支持视频编辑，并且论文里直接讨论 multi-turn consistency editing。
- 它不替代我们的 UE 数据管线；当前更适合作为“现有模型单轮调用能力探针”。
- `video_edit` 单轮路径已跑通，说明它可以作为外部基线；batch8 只是连续单轮回灌测试，不是真多轮验证。下一步重点是先实现真多轮编辑调用逻辑。
- 当前只下载视频分支。图片分支 `Lance_3B/` 仍未下载，除非后续要测图片编辑或图片理解。
