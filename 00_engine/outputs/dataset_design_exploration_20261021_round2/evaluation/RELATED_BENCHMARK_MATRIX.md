# 直接相关工作差异矩阵

检索核验日期：2026-10-21。重点核对原论文、作者页面和作者代码；“未见明确协议”不表示穷尽证明该能力不存在，不据此作首次宣称。这里的多模态 reference 指任务给出的目标/条件参考，须与源媒体、记忆视频区分；paired GT 指评测目标媒体，不等于训练样本有图像对。

| 原始工作 | 输出视频？ | 多轮？ | 显式选历史父 occurrence 后分叉并继承整版？ | 参考条件 | 评测成对目标 GT |
| --- | --- | --- | --- | --- | --- |
| [MagicBrush，2023 作者页](https://osu-nlp-group.github.io/MagicBrush/) | 否，图像 | 是 | 所核对公开说明主要是连续编辑，未见此父指针协议 | 源图、文本，部分 mask；不是本项目的目标视频参考契约 | 有人工 source/instruction/target 三元组 |
| [Memory-V2V，2026 v3 原文](https://arxiv.org/html/2601.16296v3) | 是 | 是，迭代 NVS/长视频编辑 | 有历史视频检索与约束；未找到 whole-parent occurrence、弃支不合并的分叉评测协议 | 源/用户输入视频、历史记忆、相机或文本；不要混称任意目标资产 ref | 同步多相机 NVS 子实验有目标视角 GT；不推广为所有文本编辑都有逐轮 GT |
| [OmniEdit-Bench，2026 v2 原文](https://arxiv.org/html/2608.05049v2) | 是 | 核验的任务/评测章节未见显式多轮协议 | 未见该历史分叉协议 | 明确有 image/video ref；动态运动/相机参考采用 video | 核验框架为 VLM/人工 accuracy/preservation 等评价，未见全面逐目标 paired GT 声明 |
| [AnchorEdit，2026 v2 原文](https://arxiv.org/html/2606.11751v2) | 否，输出是多轮图像；使用 video prior | 是，长链 | 初始图锚点与历史窗口；未见任意历史父指针分叉的评测 | 初始图与上一图作一致性参照；额外目标 ref 契约未核实 | 训练有目标；所核验 benchmark 使用 VLM judge，未见每轮人工 paired GT 声明 |
| [EdiVal 官方实现](https://github.com/TianyuCodings/EdiVal) | 否，图像 | 是，3-turn sequential | 未见 whole-parent 分叉协议 | 源图与指令，评测分执行/一致/质量 | 不把其自动工具评价当本项目确定性视频 GT |
| [MT-OPSD / LME-Bench，2026 原文](https://arxiv.org/html/2609.35611v1) | 否，图像 | 是，十轮递归编辑 | 主要是 latest 输出递归与退化；未见显式历史父指针分叉评测 | previous-turn 条件为主；全文还区分 full-history 对照 | 强调指令与退化判断；不据摘要推断逐轮人工目标图可用 |
| 本项目候选 | 计划视频；本轮只有符号图/历史媒体引用 | 2–5 次编辑 + 单次 historical fork | 明确 parent occurrence、整版继承、单属性 edit、不合并弃支 | 文本/图/视频目标 ref 分条件设计，尚未冻结最终公共输入 | 计划确定性渲染端点；当前未把配置图通过宣称媒体已完成 |

Memory-V2V 直接说明“多轮视频 + memory”已有先例，不能拿这两点宣称差异；它在 NVS 附录用同步多视角 GT 评价重建一致性，也提醒“有 paired GT”必须限定具体子任务。OmniEdit-Bench 明确覆盖视频特有的空间、时间、音频和 reference，并把正确编辑放到其他质量评分之前；本项目不应把缩小任务范围包装成更全面。[Memory-V2V 附录 E/F](https://arxiv.org/html/2601.16296v3)、[OmniEdit-Bench §3](https://arxiv.org/html/2608.05049v2)。

AnchorEdit 的“temporal/causal memory”和 video prior 不代表它输出视频；其 benchmark 用初始图和上一张图分别约束身份/局部一致，并在链失败时统计稳定性。它支持我们把身份漂移与连续可用性分别报告，却不能直接代替 whole-parent 版本选择的真值。[AnchorEdit §4 与附录 A.3](https://arxiv.org/html/2606.11751v2)。

当前最清晰的差异路线是：**把版本语义做成可审计 GT，并用成对历史干预证明何种信息确实需要，再把选源、属性继承、当前可见输入契约和 nominal 路径成功分开评测。**这是一组可检验的设计承诺，不是已被模型结果证明的优势，也不构成“此前无人做过”的结论。
