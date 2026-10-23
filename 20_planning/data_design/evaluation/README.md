# 多轮视频编辑评测方案（初稿）

> 文档 ID：`DESIGN-MULTITURN-VIDEO-EDIT-EVAL-DRAFT`
> 文档类型：`design`
> 生命周期：`current`
> 权威范围：多轮视频编辑模型评测的候选 benchmark、参考数据、评测维度和后续收敛方向
> 成熟度：`initial_draft`
> 最近核验：2026-08-31
> 父层：[`../README.md`](../README.md)

## 1. 文档目的

本文记录 DataMake 多轮视频编辑模型的第一版评测方案，供后续实现、校准和冻结正式 Gate 使用。当前只形成评测框架，不代表以下内容已经确定：

- benchmark 已在当前 Lance 环境中跑通；
- 模型、权重、阈值和硬件成本已经验收；
- 各指标权重或最终总分已经冻结；
- 自动指标已经通过 DataMake 样本上的人工相关性验证；
- 当前训练计划的 held-out Gate 已经被本文替换。

当前目标不是尽快得到一个总分，而是建立能区分以下失败模式的评测结构：

1. 当前编辑没有完成；
2. 输出视频质量下降；
3. 未要求修改的源内容发生漂移；
4. 前序轮次已经完成的编辑被遗忘或回退；
5. 误差随编辑轮次持续累积。

## 2. 已核对的背景

外部资料核验范围为截至 2026-08-31 可访问的论文、项目页和官方代码。

- Lance 明确支持 `video_edit`，并展示单轮与四轮一致性视频编辑案例，但公开论文和仓库没有提供可复现的单轮或多轮视频编辑定量 benchmark。
- Lance 报告的 GEdit-Bench 是单轮图像编辑评测；VBench 是文本到视频生成评测，二者都不能直接回答 DataMake 的多轮视频编辑问题。
- 视频编辑领域尚无一个被普遍接受的单项总指标。较稳定的共同结构是同时评价：
  - 指令遵循（Instruction Compliance）；
  - 视频质量（Video Quality）；
  - 源视频保真（Video Fidelity）。
- 较早的视频编辑工作广泛使用 LOVEU-TGVE；较新的方案开始增加视频级语义、源视频保真、MLLM 判断和更细的诊断维度。

## 3. 当前候选：三套外部评测共同作用

当前预案采用一套较新的综合 benchmark、一套较成熟的历史 benchmark，以及一个人类偏好代理分。三者分工不同，不在初稿阶段直接加权为单一总分。

| 组件 | 当前角色 | 主要输入 | 主要输出 | 当前定位 |
| --- | --- | --- | --- | --- |
| IVEBench | 新的主诊断框架 | 源视频、编辑视频、源/目标描述、编辑指令 | 视频质量、指令遵循、视频保真及细分项 | 主指标候选 |
| LOVEU-TGVE / TGVE+ | 成熟历史基线 | 源视频、编辑视频、目标文本 | CLIP/PickScore/ViCLIP 和人工评测维度 | 外部横向可比性 |
| VE-Bench QA | 人类偏好代理 | 源视频、编辑视频、编辑指令 | 学习式综合质量分 | 辅助总分与交叉检查 |

### 3.1 IVEBench：新的主诊断框架

IVEBench 于 ICLR 2026 接收，公开方案包含 600 个源视频、8 个编辑大类、35 个子类，并区分短视频与长视频子集。其指标结构与 DataMake 最接近：

**视频质量**：

- Subject Consistency；
- Background Consistency；
- Temporal Flickering；
- Motion Smoothness；
- VTSS。

**指令遵循**：

- Overall Semantic Consistency；
- Phrase Semantic Consistency；
- Instruction Satisfaction；
- Quantity Accuracy。

**视频保真**：

- Semantic Fidelity；
- Motion Fidelity；
- Content Fidelity。

当前建议把 IVEBench 作为主要诊断骨架，而不是因为其发表较新就直接接受其总分。正式采用前需要验证代码、权重、许可证、运行成本，以及这些指标在 DataMake 动画人物和 UE 合成视频上的人类相关性。

### 3.2 LOVEU-TGVE / TGVE+：成熟历史基线

LOVEU-TGVE 来自 CVPR 2023 Text-Guided Video Editing Competition。它是较早的标准化视频编辑 benchmark，并被后续视频编辑工作继续采用。原始自动指标包括：

- `CLIPFrame`：输出视频帧间 CLIP 相似度；
- `CLIPText`：输出帧与目标文本的 CLIP 相似度；
- `PickScore`：输出帧相对目标文本的人类偏好代理。

人工评测维度包括：

- Text Alignment；
- Structure Preservation；
- Visual Quality。

ECCV 2024 的 Emu Video Edit 指出 `CLIPFrame` 会偏好静止或修改较少的视频，并在 TGVE/TGVE+ 中增加视频级指标：

- `ViCLIPdir`：视频语义变化方向与文本变化方向的一致性；
- `ViCLIPout`：编辑后视频与目标描述的一致性。

当前建议保留 TGVE 作为历史横向基线，但不能用 `CLIPFrame` 或其他单一分数作为 DataMake 的主结论。实施前还需要确认 TGVE+ 数据和当前公开评测代码的完整可获得性。

### 3.3 VE-Bench QA：人类偏好代理

VE-Bench QA 发表于 AAAI 2025。其评估器同时读取源视频、编辑视频和编辑指令，目标是拟合人工 Mean Opinion Score。它补充传统指标难以覆盖的整体观感、文本对齐和源/目标相关性。

当前建议把 VE-Bench QA 作为辅助分：

- 用于检查 IVEBench/TGVE 改善是否也对应整体人类偏好改善；
- 用于发现多个细分指标都正常、但整体视觉结果仍不自然的样本；
- 不用于替代细分诊断，也不单独作为训练有效性的通过条件。

由于其输出经过训练归一化，不应在未校准时解释为绝对的 `1-10` 人工分。正式使用前需要固定 evaluator checkpoint、预处理版本和推理配置。

## 4. UE 真值视频的作用

UE 真值视频不是第四套 benchmark，而是 DataMake 特有的**参考数据层**。

对于一条长度为 `T` 的配置图路径：

```text
C0 --E1--> C1 --E2--> ... --ET--> CT
```

确定性 UE 节点视频提供每一轮的正确目标：

```text
V0*, V1*, ..., VT*
```

模型在第 `t` 轮的输出记为：

```text
V_hat_t
```

因此评测不仅可以判断 `V_hat_t` 是否符合文本，还可以比较 `V_hat_t` 与 `Vt*` 在以下方面的差异：

- 人物身份和外观；
- 服装、配饰、道具和背景状态；
- 动作、相机、光照和其他未编辑变量；
- 当前轮正确目标与模型输出之间的语义、结构和运动差距。

UE 真值的初步使用原则：

1. 不把全帧 PSNR/SSIM 作为唯一主指标；生成模型可能在语义正确时产生合理的像素差异。
2. 优先考虑 DINO/CLIP 特征、人物身份特征、目标属性检测、轨迹/姿态和分区后的结构比较。
3. 对编辑区与非编辑区分别评分，避免“编辑越少，保真分越高”的退化解。
4. UE 配置字段和原子边标签可生成明确 checklist，不需要完全依赖自由文本 judge 猜测应当改变什么。

## 5. 多轮评测扩展

外部三套评测主要提供每轮编辑的基础分。DataMake 还需要在其上增加链级协议。

### 5.1 两种推理模式必须分开

**Teacher-forced 模式**：

```text
输入 V(t-1)* + 指令 Et -> 模型输出 V_hat_t
```

它隔离单步编辑能力，避免上一轮模型错误污染当前轮输入。

**Autoregressive rollout 模式**：

```text
输入 V_hat_(t-1) + 指令 Et -> 模型输出 V_hat_t
```

它评价真实多轮使用中的误差累积和历史保持。两种模式不得混合成一个结果；训练是否有效应同时看单步能力和 rollout 稳定性。

### 5.2 候选链级指标

#### Current Edit Success

评价第 `t` 轮的新指令是否完成。其底层判断可复用 IVEBench 指令遵循项、TGVE/ViCLIP 语义项和 UE 当前边 checklist。

#### History Retention

评价第 `1..t-1` 轮已经完成的编辑在第 `t` 轮是否仍然成立。初步定义为：

```text
Retention_t = 当前输出中仍满足的历史要求数 / 历史要求总数
```

分母为零的首轮不报告该项。

#### UE Target Similarity

评价 `V_hat_t` 与 `Vt*` 的目标状态一致性。正式定义需要按编辑类型选择特征、mask 和检测器，不能先冻结为单一像素距离。

#### Strict Chain Success

只有当链上所有轮次的当前编辑和累计历史要求都通过时，该链才计为成功：

```text
StrictChainSuccess(chain) in {0, 1}
```

数据集级结果为成功链比例。它可以暴露“平均分尚可，但没有一条完整链真正成功”的情况。

#### Drift Slope

记录模型输出与 UE 目标之间的差距是否随轮次扩大。初稿只要求保存每轮序列，不冻结线性拟合公式；后续应按不同链长分别校准。

### 5.3 Checklist 方向

CoVEBench 的 MLLM checklist、Union Accuracy 和对未编辑区域的结构/运动保真设计，对多轮扩展有直接参考价值。DataMake 可以将每条原子边转成结构化检查项，并在第 `t` 轮累积：

```text
required_t = {E1, E2, ..., Et}
```

这样可以分别报告单项满足率和“全部同时满足”的严格成功率。CoVEBench 当前只作为设计参考，不属于已经选定的三套外部评测。

## 6. 初步报告结构

第一版评测报告建议保留原始分项，不先制造单一总分：

```text
Evaluation Report
├── run metadata
│   ├── checkpoint
│   ├── inference config
│   ├── evaluator versions
│   ├── seeds
│   └── evaluation split manifest
├── external single-turn / per-turn
│   ├── IVEBench dimensions
│   ├── TGVE / TGVE+ dimensions
│   └── VE-Bench QA
├── DataMake reference-based
│   ├── UE target similarity
│   ├── edited-region score
│   └── preserved-region score
└── multi-turn
    ├── current edit success by turn
    ├── history retention by turn
    ├── strict chain success
    └── drift by turn and chain length
```

比较基础 checkpoint 与微调 checkpoint 时必须固定：

- held-out chain split；
- 推理分辨率、帧数、采样步数和 CFG；
- 随机种子集合；
- evaluator 版本和预处理；
- teacher-forced/rollout 模式；
- 失败样本和缺失输出的计分规则。

## 7. 初步实施顺序

1. **复现性调查**：核对 IVEBench、TGVE/TGVE+ 和 VE-Bench QA 的代码、权重、许可证、依赖、显存与输入格式。
2. **最小评测集**：从 held-out 数据中按编辑类型和链长分层抽取小样本，同时运行基础 checkpoint 与微调 checkpoint。
3. **指标校准**：人工盲评同一小样本，检查自动指标排序是否与人类判断一致，重点寻找“少编辑高保真”和“当前轮成功但历史遗忘”反例。
4. **UE 参考扩展**：根据第一批实际编辑轴建立目标属性、编辑区和保留区检查。
5. **多轮协议**：分别运行 teacher-forced 与 autoregressive rollout，产生逐轮和逐链结果。
6. **冻结正式方案**：只有在指标复现、人工相关性和成本评估通过后，才确定阈值、权重、总分和训练 Gate。

## 8. 待决问题

- IVEBench 使用完整 12 项还是先采用与第一批编辑轴匹配的子集？
- 历史基线采用原始 TGVE，还是在可复现前提下同时加入 TGVE+？
- VE-Bench QA 在 UE 动画人物域是否需要额外校准？
- UE 真值比较使用哪些人物身份、姿态、光流、分割和感知特征模型？
- 编辑区和非编辑区 mask 由 UE pass、配置标签、SAM2 还是混合方法产生？
- 每轮需要几个随机种子，怎样报告均值、方差和最差结果？
- MLLM judge 使用哪个模型，怎样固定 prompt、采样和失败重试？
- 是否需要一个最终总分；若需要，怎样避免平均值掩盖严格链失败？
- 多轮评测的链长分桶和最低样本量如何确定？

## 9. 外部参考

以下链接最后核验于 2026-08-31，执行前必须重新核实版本和许可证：

- [Lance project](https://lance-project.github.io/)
- [Lance official repository](https://github.com/bytedance/Lance)
- [LOVEU-TGVE official repository](https://github.com/showlab/loveu-tgve-2023)
- [CVPR 2023 Text Guided Video Editing Competition](https://arxiv.org/abs/2310.16003)
- [Video Editing via Factorized Diffusion Distillation / TGVE+](https://www.ecva.net/papers/eccv_2024/papers_ECCV/papers/09816.pdf)
- [EditBoard](https://ojs.aaai.org/index.php/AAAI/article/download/33754/35909)
- [VE-Bench paper](https://ojs.aaai.org/index.php/AAAI/article/view/32763)
- [VE-Bench official repository](https://github.com/littlespray/VE-Bench)
- [IVEBench project](https://ryanchenyn.github.io/projects/IVEBench/)
- [IVEBench official repository](https://github.com/RyanChenYN/IVEBench)
- [CoVEBench official repository](https://github.com/NJU-LINK/CoVEBench)

