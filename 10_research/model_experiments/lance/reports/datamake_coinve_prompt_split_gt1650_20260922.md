# CoinVE真实数据：整句 Prompt 与拆分多轮 Prompt 对比（2026-09-22）

本次实验只使用4个CoinVE真实样例，比较原始复合指令和按编号拆开的连续多轮指令。推理核心复用了现有 `run_datamake_lora_visual_sanity.py`、`MultiTurnChatEngine`、训练数据预处理和官方30步采样路径；新增代码只负责构造实验case、允许读取本实验生成的历史，以及生成对比页面。

## 权重边界

原GT训练的2350步完整checkpoint已被删除。本实验使用上次推理时保存的、经过1016个LoRA张量核验的 **GT1650 inference adapter快照**。因此本结果代表GT1650，不代表2350；没有使用整链pred_x0 checkpoint。

## 实验设置

- 样例：`coinve-085619`、`coinve-192680`、`coinve-186523`、`coinve-006415`。
- 整句模式：source + 原始复合prompt，单轮生成一个结果。
- 拆分模式：按原prompt中的编号拆成2或3条单句；第一轮使用source，后续轮使用本实验上一轮生成的视频。
- 原始target只用于页面对照，从不进入模型对话。
- 两种模式共生成13段视频：4段整句结果，9段拆分多轮结果。
- 保持训练checkpoint中的VAE/ViT预处理、共同5秒窗口、30步采样、CFG1、shift3.5、seed42和KV cache不变。

## 结果页面

[打开对比网页](../outputs/multiturn_chat/coinve_prompt_split_gt1650_20260922/index.html)

页面每个样例同时显示：

1. 原始整句复合prompt的单轮输出；
2. 拆分后的每一轮prompt及其输出；
3. 最终拆分输出与真实target的对照。

[机器审计](../outputs/optimization_diagnostics/coinve_prompt_split_gt1650_20260922/audit.json)确认13段视频全部解码通过，21个媒体引用通过检查，target未进入任何用户输入。

## 解释边界

CoinVE只提供最终target，没有中间编辑轮次的真值。因此拆分结果可以评价最终效果、非目标保持和多轮漂移，但不能证明每个中间步骤都正确，也不能直接作为严格多轮监督数据。拆分prompt改变了任务定义和编辑顺序，若后续用于训练，需要重新设计中间target或接受弱监督性质。
