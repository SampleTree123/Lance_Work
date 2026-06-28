# BAGEL 来源登记

> 登记日期：2026-06-28。
> 状态：只找到并登记来源；暂未深读论文。

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

## 暂定用途

- 先作为统一多模态/图像编辑方向的参考模型。
- 暂不作为视频编辑优先验证对象；本轮先看 Lance。
- 深读时重点关注：统一预训练数据配比、图像编辑任务组织、是否能给我们的多来源 schema 提供借鉴。
