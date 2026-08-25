# 多轮视频编辑文本 Schema V1

> 文档角色：`technical_specification`
> 状态：`current`
> 规范状态：`accepted`
> 实现状态：`implemented_local`
> 适用阶段：`WF-70/WF-90`
> 权威范围：多轮视频编辑的 prompt 词表、回合、对话、语言版本、历史引用和 `video_in + prompt + video_out` 训练记录
> 上级入口：[`README.md`](./README.md)
> 上游：[`CONFIG_GRAPH_SCHEMA_V1.md`](./CONFIG_GRAPH_SCHEMA_V1.md)、[`MULTI_ROUND_CHAIN_SAMPLING_V1.md`](../sampling/MULTI_ROUND_CHAIN_SAMPLING_V1.md)
> 下游：训练样本封装器、语言质量门禁和数据集发布器
> 最近核验：2026-08-24

## 1. 目的

配置图决定“哪个状态变成哪个状态”，文本层负责把合法原子边表达为训练模型可读的自然语言。两者必须分离：修改措辞不能改变节点、边、链、渲染作业或媒体哈希；修改语义配置则必须重新生成图，不能靠改 prompt 伪造编辑。

每个训练回合的最小契约是：

```text
video_in + prompt + video_out
```

第一批配置图已经包含 4,000 条 3–5 轮路径，共 15,000 次编辑。旧 `chains.jsonl.instructions` 是生成时的技术审计占位文本，可能包含内部 ID，**不得直接作为模型输入**。模型输入只读取本 Schema 的文本层产物。

## 2. 第一批冻结范围

| 项目 | 值 |
| --- | --- |
| 对话数 | 4,000 |
| 编辑回合数 | 15,000 |
| 语言 | `zh-CN`、`en` |
| 主语言 | `zh-CN` |
| 编辑轴 | E1 身份、E2 服装、E3 动作、E7 镜头，各 3,750 回合 |
| 文本模式 | `dialogue` 与 `standalone` |
| 身份目标约束 | `paired_target_video`，文字只描述“另一位同性人物” |
| 内部 ID 泄漏 | 必须为 0 |

首批身份尚未完成人工外貌描述标注。因此 E1 的精确目标身份由配对 `video_out` 约束，prompt 只提出同性身份替换。该方案可用于首批闭环，但目标特异性弱于带人工外貌描述或参考图的正式身份编辑；必须在 manifest 中保留此限制，不能宣称文本唯一确定目标身份。

## 3. 文件集合

文本层位于配置图目录下的独立版本目录，不覆盖结构图：

```text
graph_<version>/
  nodes.jsonl
  edges.jsonl
  chains.jsonl
  text_<version>/
    prompt_manifest.json
    prompt_catalog.json
    turns.jsonl
    dialogs.jsonl
    prompt_report.json
    prompt_review.json
    PROMPT_REVIEW.md
```

| 文件 | 作用 |
| --- | --- |
| `prompt_manifest.json` | 冻结语言版本、输入图哈希、词表哈希、计数、文件哈希和已知限制 |
| `prompt_catalog.json` | 资产语义标签、双语模板、身份 grounding 策略 |
| `turns.jsonl` | 每行一个完整 `video_in + prompt + video_out` 训练回合 |
| `dialogs.jsonl` | 每行一条完整多轮链，按顺序引用或内嵌各回合 |
| `prompt_report.json` | 数量、轴分布、历史引用、模板使用和语言质量门禁 |
| `prompt_review.*` | 确定性抽取的渐进、回退和返回起点文本审查样本 |

## 4. Turn 记录

`turns.jsonl` 每行至少包含：

| 字段 | 含义 |
| --- | --- |
| `turn_id` / `prompt_id` | 由语言版本、chain、round、edge 和最终文本稳定派生 |
| `chain_id` / `round` | 所属多轮链及轮次，轮次从 1 开始 |
| `source_node_id` / `target_node_id` | 本轮输入和目标节点 |
| `edge_id` / `edge_type` / `edit_axis` | 权威原子编辑边 |
| `video_in_uri` / `video_out_uri` | 两个节点的相对媒体 URI；不得复制视频字节 |
| `history_turn_ids` | 当前轮之前的有序回合 ID |
| `history_reference` | `new_target/initial_state/prior_round` 及被引用轮次 |
| `prompt.dialogue` | 依赖完整多轮历史的中英文指令 |
| `prompt.standalone` | 把历史回退展开为直接目标、可单轮训练的中英文指令 |
| `prompt.template_ids` | 每个文本采用的稳定模板 ID |
| `grounding` | 目标资产元数据和文本目标特异性；不属于模型输入文本 |
| `atomic_edit_contract` | 唯一变化字段、保持不变的编辑轴和固定字段 |
| `quality_flags` | 原子性、语言完整性、ID 泄漏和媒体配对要求 |

`dialogue` 与 `standalone` 是同一语义回合的两种训练视图，不是两条独立配置链，也不增加视频渲染数量。

## 5. Dialog 记录

`dialogs.jsonl` 每行对应一条配置链，至少包含：

- `dialog_id=chain_id`、策略、兼容域和编辑长度；
- 初始/最终节点及媒体 URI；
- 有序 `turn_ids`；
- 每轮 `video_in_uri`、对话 prompt、独立 prompt 和 `video_out_uri`；
- 五个结构事实标签。

训练多轮模型时读取 `dialogue` 并提供先前回合历史；把数据扁平为单轮样本时读取 `standalone`。不得在不提供历史时使用“恢复到第 N 轮”一类 `dialogue` 文本。

## 6. 文本生成规则

1. 配置路径、节点和边先冻结，文本只能从边派生。
2. 每轮只描述当前边对应的一个轴，并明确其余视觉内容保持不变。
3. 新目标使用资产语义标签；严禁把 `f_id02`、`act_*` 等内部 ID 写入模型文本。
4. 目标节点曾在当前链出现时，`dialogue` 使用“恢复初始状态”或“恢复到第 N 轮后的状态”。
5. 同一回合的 `standalone` 始终直接描述目标语义，不依赖历史。
6. 模板选择由 prompt 版本、chain、round、模式和语言稳定哈希决定；相同输入必须字节级复现。
7. 文本表面改写不得改变 `chain_id`；文本版本变化产生新的 `prompt_layer_version`、`prompt_id` 和 `turn_id`。
8. 中英文必须表达同一原子编辑；翻译不允许新增或删除视觉变化。

## 7. 第一批生成入口

```powershell
python "D:\UE\Lance_Work\00_engine\scripts\dataset\build_first_batch_prompt_layer_v1.py" `
  --graph-dir "D:\UE\Lance_Work\00_engine\outputs\first_batch_dataset\graph_20260824_v1" `
  --output-dir "D:\UE\Lance_Work\00_engine\outputs\first_batch_dataset\graph_20260824_v1\text_first_batch_20260824_v2"
```

词表源为：

```text
00_engine/scripts/dataset/prompt_catalog_first_batch_v1.json
```

实现与词表变化后运行：

```powershell
python -m pytest "D:\UE\Lance_Work\00_engine\scripts\dataset\tests\test_build_first_batch_prompt_layer_v1.py" -q
```

## 8. 必需验证

正式第一批文本层必须同时满足：

1. 精确 4,000 个 dialog、15,000 个 turn；
2. E1/E2/E3/E7 各 3,750 回合；
3. 每个 turn 的 source/target/edge 与配置链相符且只改变一个轴；
4. `video_in_uri` 与 `video_out_uri` 均来自节点权威媒体 URI；
5. 每个 turn 同时有完整 `zh-CN` 与 `en` 的 dialogue/standalone 文本；
6. 未解析模板占位符为 0，内部 ID 泄漏为 0；
7. 回退引用指向真实先前节点，独立版不依赖对话历史；
8. `prompt_manifest` 锁定 source/nodes/edges/chains/catalog 和全部文本文件哈希；
9. 相同图与词表重复生成的 `turns.jsonl/dialogs.jsonl` 字节一致；
10. 人工抽查普通渐进、重复轴、回退和返回起点 prompt 的自然度与语义一致性。

## 9. 当前证据与后续扩展

当前文本层位于：

```text
OUTPUT_ROOT/first_batch_dataset/graph_20260824_v1/text_first_batch_20260824_v2
```

`prompt_report.json` 已通过 4,000/15,000 计数、四轴均衡、双语完整、原子编辑和零内部 ID 泄漏门禁。第一批已包含 196 个恢复初始状态回合、369 个恢复先前轮次回合。

后续正式扩展按优先级为：

1. 为身份建立人工复核的外貌描述或目标参考图契约，把 E1 从 `class_only` 升级为 `asset_specific/reference_grounded`；
2. 增加经过质量审查的自然语言改写，不改变配置链计数；
3. 根据训练任务决定主语言、双语混合比例和是否提供历史；
4. 增加 prompt 安全性、偏见和跨语言语义一致性审计。
