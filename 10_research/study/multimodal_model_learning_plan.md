# 统一多模态视频模型学习计划

> 创建日期：2026-07-03。
> 目标：围绕 Lance 论文与代码，系统学习统一多模态视频模型、视频编辑、多轮上下文、MoT/CoT/PE/TTS 等概念，并把结论反推到 DataMake 的 UE 数据构建。

## 0. 学习主线

当前优先级：

1. **先读 Lance**：理解它如何把文本、图像、视频、理解 token 和生成 latent 放到统一上下文里，如何支持 `video_edit`。
2. **再读 Lance 代码**：从输入视频/prompt 到中间变量、模型 forward、latent 采样、视频解码，逐步记录值、类型、shape 和功能。
3. **实现/验证 multi-turn 调用**：区分“上一轮输出回灌”与“完整历史上下文 interleave”两种多轮方式。
4. **中途补概念论文**：遇到 MoT、CoT、interleave、prompt enhance、test-time scaling 等概念时，再读 BAGEL 和相关论文/代码。
5. **最后对比主流视频生成范式**：阅读 Sol Video 或其他当前视频生成代表，理解传统视频生成管线与统一多模态模型的差异。

这条线服务于 DataMake：Lance 不是最终生产管线，而是外部能力基线和失败模式收集器。最终要把模型失败转成 UE 可控编辑边与采样需求。

## 1. 第一阶段：Lance 论文

状态：已完成主体阅读，时间为 2026-07-03。后续只在读代码时回查论文细节。

目标问题：

- Lance 是传统视频生成模型，还是统一多模态模型？
- 它的输入上下文如何组织？什么是 interleaved multimodal sequence？
- 文本、图片、视频分别如何变成模型可处理的 token 或 latent？
- 理解路径和生成路径如何分工？
- `video_edit`、`x2t_video`、`t2v`、`i2v` 是否共享同一套上下文表达？
- 论文中的 multi-turn consistency editing 到底是训练/评测设定，还是推理时真正保留历史上下文？

需要产出的阅读笔记：

- Lance 总体架构图的中文解释。
- 输入/输出任务表：`t2v`、`i2v`、`video_edit`、`x2t_video`。
- 关键模块表：Qwen2.5-VL ViT、Wan2.2 VAE、understanding expert、generation expert、MaPE、flow matching。
- 对 DataMake 的直接启发：哪些 UE 编辑类型应该优先覆盖。

已确认结论：

- Lance 不是传统单一视频生成模型，而是统一多模态模型：理解、生成、编辑任务共享 interleaved multimodal context。
- 它不是简单的 MoE/MoT 标签可以概括；关键在于 ViT semantic tokens 与 VAE latent tokens 分别服务理解和生成。
- Figure 6 的核心是把 text tokens、ViT semantic tokens、clean VAE tokens、noisy VAE tokens 组织成统一序列。
- 图像理解任务一般只输出文本，不会默认走 VAE decode 生成图像；图像可视作单帧视频，但工程分支可能不同。
- MaPE 通过在时间维度给不同视觉功能组加 offset，区分 ViT、clean VAE、noisy VAE，减少位置混淆。
- 论文架构可以表达多轮上下文，但论文训练表没有明确公开大规模 multi-turn video editing trajectory 数据。
- PT/CT/SFT/RL 的区别：PT 建基础对齐，CT 扩展多任务 interleaved 能力，SFT 用高质量指令数据精修，RL 主要补图像文字渲染等弱项。
- Table 9 支持一个关键判断：理解数据与编辑/主体驱动等多任务生成数据会反向促进生成能力。
- 对 DataMake 的直接启发：高质量、可验证、带 metadata 的视频编辑数据不仅服务编辑任务，也可能促进生成和理解。

## 2. 第二阶段：Lance 代码阅读

状态：进行中，2026-07-03 开始。优先读 `video_edit` 推理路径和 true multi-turn 可行性。

阅读顺序：

1. `inference_lance.sh`：命令行参数如何进入 Python。
2. config/example JSON：`interleave_array`、`element_dtype_array`、`istarget_in_interleave` 表达什么。
3. 数据读取与预处理：视频如何解码、采样帧、resize、归一化。
4. tokenizer / processor：文本、视频、图像如何变成 token 或 latent。
5. model forward：输入字典有哪些 key，shape 分别是什么。
6. diffusion / flow sampling：steps、CFG、seed、KV cache 如何影响输出。
7. VAE decode / video save：latent 如何变回帧序列和 mp4。

每次代码阅读统一记录：

```text
入口函数:
输入变量: 名称 / 类型 / shape / dtype / 设备
关键操作:
输出变量: 名称 / 类型 / shape / dtype / 设备
作用:
和论文概念的对应关系:
```

## 3. 第三阶段：多轮视频编辑

必须区分两种模式：

| 模式 | 输入形式 | 意义 |
|------|----------|------|
| 连续单轮回灌 | `V0 + p1 -> V1`，再 `V1 + p2 -> V2` | 当前 batch8 脚本采用的实用 baseline；上下文不保留，只保留上一轮视频结果 |
| 真多轮上下文 | `V0, p1, V1, p2, V2, p3 -> V3` | 更接近统一多模态上下文建模；需要代码验证 Lance 是否支持 |

目标：

- 先确认 Lance 官方推理代码是否允许多个 video/text 元素 interleave。
- 如果允许，写一个最小 multi-turn config。
- 如果不允许，记录限制，并把当前方法定义为“chain baseline”而不是“true multi-turn”。
- 比较两种方式在身份保持、动作保持、背景一致性、局部编辑和画质退化上的差异。

## 4. 需要补充学习的概念

### 4.1 MoT / MoE / Dual Expert

学习目标：

- MoT 与 MoE 的区别是什么。
- 为什么统一多模态模型需要专家分工。
- 理解任务和生成任务的目标为什么会冲突。
- Lance 的 dual expert 与 BAGEL 的 MoT 有什么相同点和不同点。

推荐时机：读完 Lance 架构后，再读 BAGEL。

### 4.2 CoT 与视觉生成

学习目标：

- 传统 CoT 是语言推理链；视觉生成里不一定直接输出文字推理。
- 视频编辑里的 CoT 可能体现为：任务分解、编辑计划、区域定位、先理解再生成。
- 判断论文里的 CoT 是模型内部能力、训练数据形式，还是推理 wrapper。

### 4.3 Prompt Enhance

学习目标：

- PE 是把短 prompt 扩写成更适合生成模型的详细描述。
- PE 可以改善 t2v/i2v/video_edit，但也可能引入不该有的细节。
- Lance 当前脚本可用 `--ENHANCE_PROMPT false` 关闭；后续需要对比开启/关闭。

### 4.4 Test-Time Scaling

学习目标：

- 测试时增加计算来提升结果，例如更多采样 steps、多候选生成、VLM 打分筛选、自我修正、多轮 prompt refine。
- 区分 TTS 和训练规模扩大；TTS 是推理阶段策略。
- 记录它对 DataMake 的启发：数据是否需要支持回退、候选比较和一致性评估。

### 4.5 工程概念

学习目标：

- 精度：fp32、fp16、bf16、fp8、int8/NF4 分别解决什么问题。
- autocast / mixed precision 如何减少显存和加速。
- 权重 dtype、激活 dtype、KV cache dtype 是否一致。
- CUDA、PyTorch wheel、flash-attn、xformers、Triton 的关系。
- batch size、num frames、resolution、diffusion steps 对显存和速度的影响。
- KV cache、gradient checkpointing、offload、quantization 在推理/训练中的区别。

记录位置：

- 与论文概念直接相关的内容写在本目录，例如本文件或后续 `model_concepts.md`。
- 与 Lance 运行、脚本、环境、显存相关的工程记录写在 `10_research/model_experiments/`。
- 如果某个工程概念会影响 DataMake 的生产设计，比如显存决定 batch 策略、精度影响输出一致性，则同步回写 `20_planning/implementation/` 或对应实验报告。

## 5. 阅读顺序建议

```text
Lance paper
  -> Lance code inference path
  -> Lance true multi-turn feasibility
  -> BAGEL paper for MoT / unified multimodal pretraining
  -> Interleaved multimodal context references
  -> CoT / Prompt Enhance / Test-Time Scaling references
  -> Sol Video or other mainstream video generation pipeline
```

## 6. 每轮学习会话模板

每次阅读或代码走读后，记录四类结论：

1. **我理解了什么**：用自己的话解释一个概念或模块。
2. **代码里对应哪里**：文件、函数、输入输出、shape。
3. **还有什么不确定**：需要查论文、跑实验或读源码验证。
4. **对 DataMake 的影响**：是否改变 UE 编辑优先级、schema、采样或评估指标。

## 7. 当前下一步

1. 从 `video_edit` 的 config 格式开始，确认一轮输入如何进入模型。
2. 阅读 `inference_lance.py` 与数据集构造代码，定位 `interleave_array`、`element_dtype_array`、`istarget_in_interleave` 的解析位置。
3. 追踪视频输入如何被采样、编码成 ViT tokens / VAE latents，以及 clean/noisy segment 如何构造。
4. 在代码层验证 batch8 当前脚本属于连续单轮回灌，而不是真多轮上下文。
5. 判断 true multi-turn config 是否能直接表达；如果不能，记录需要改哪些数据结构或 mask。
