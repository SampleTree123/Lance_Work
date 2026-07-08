# BAGEL 来源登记

> 登记日期：2026-06-28；多图 interleave / 多轮编辑相关实现查阅日期：2026-07-05。
> 状态：已针对 BAGEL 的 interleaved generation、图片编辑推理入口和多图上下文机制做定向阅读；暂未完整深读全论文。

## 来源

- GitHub: https://github.com/ByteDance-Seed/Bagel
- Project page: https://bagel-ai.org/
- Paper: https://arxiv.org/abs/2505.14683
- Model: https://huggingface.co/ByteDance-Seed/BAGEL-7B-MoT
- Demo: https://demo.bagel-ai.org/
- HF Space: https://huggingface.co/spaces/ByteDance-Seed/BAGEL

## 初步信息

BAGEL 是 ByteDance-Seed 的统一多模态模型，README 描述为 7B active parameters / 14B total 的 MoT 模型，覆盖多模态理解、文本生成图像和图像编辑等能力。

论文题名是 `Emerging Properties in Unified Multimodal Pretraining`，arXiv 编号 `2505.14683`。模型页许可证为 Apache-2.0，HF 模型页显示不是 gated。

官方 quick start 要求：

- Python 3.10。
- `flash_attn`。
- 32GB+ VRAM 可跑 WebUI；12-32GB 建议 NF4 quantization。

HF 模型页当前显示 storage 约 29.6GB，参数统计约 14.7B parameters。后续如果要验证 BAGEL，应单独建立验证计划，不要和 Lance 权重/环境混在一起。

## 多图 / 多轮编辑机制要点（2026-07-05）

本轮只为 Lance 多轮调用问题做定向查阅，稳定结论如下：

- BAGEL 的 interleaved image generation 训练明确支持一条样本中包含多张图片和多段文本。
- 对每张图片，BAGEL 区分 `ViT tokens`、`clean VAE tokens` 和 `noised VAE tokens`。
- 后续图片生成可以 attend 到前面图片的 `ViT tokens` 和 `clean VAE tokens`；前面图片的 noised VAE 不作为历史保留。
- 推理时，生成完一张图后，它应作为 clean image context 进入后续上下文。
- 官方 `inferencer.py` 的 `InterleaveInferencer` 暴露了 `update_context_text()`、`update_context_image(..., vae=True, vit=True)` 和 `gen_image()`，说明 BAGEL 的推理接口天然按“逐步更新上下文，再生成下一张图”的方式组织。
- 这不等价于 Lance 可以直接把多个历史视频都作为 clean VAE source。Lance 当前 `video_edit` 路径有 source-target VAE 对齐假设，因此 DataMake 中的 Lance v2 采用更保守映射：历史视频只进 VIT，最新视频才作为唯一 clean VAE source。

## 暂定用途

- 先作为统一多模态/图像编辑方向的参考模型。
- 暂不作为视频编辑优先验证对象；本轮先看 Lance。
- 深读时重点关注：统一预训练数据配比、图像编辑任务组织、是否能给我们的多来源 schema 提供借鉴。
