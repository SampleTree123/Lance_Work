# 多轮编辑链采样规范 V1

> 文档角色：`technical_specification`
> 状态：`current`
> 规范状态：`accepted`
> 实现状态：`implemented_local`
> 适用阶段：`WF-70/WF-90`
> 权威范围：配置图兼容域、原子编辑边、3–5 轮编辑链、采样配额、事实标签、去重与验收规则
> 上级入口：[`README.md`](./README.md)
> 上游：[`CONFIG_GRAPH_SCHEMA_V1.md`](../schema/CONFIG_GRAPH_SCHEMA_V1.md)、[`PLAN-2026-08-FIRST-DATA-BATCH.md`](../character_creator/full_process/project_management/plans/active/PLAN-2026-08-FIRST-DATA-BATCH.md)
> 架构决定：[`ADR-0014-COMPATIBILITY-DOMAINS-AND-CHAIN-POLICIES.md`](../character_creator/full_process/project_management/decisions/ADR-0014-COMPATIBILITY-DOMAINS-AND-CHAIN-POLICIES.md)
> 文本派生：[`MULTI_ROUND_VIDEO_EDIT_TEXT_SCHEMA_V1.md`](../schema/MULTI_ROUND_VIDEO_EDIT_TEXT_SCHEMA_V1.md)
> 下游：链采样器、指令生成器、渲染任务生成器和数据集验收器
> 最近核验：2026-08-25

## 1. 目的与边界

本规范定义如何从已冻结的角色视频配置图生成多轮编辑数据。配置路径是权威事实，文本指令和媒体引用均由配置路径派生，不允许先写文本再反推配置。

本规范负责：

- 定义哪些节点可处于同一兼容域；
- 定义合法原子编辑边；
- 生成 3–5 次编辑的链；
- 固定首批 4,000 条链的策略、长度和兼容域配额；
- 为每条链计算可验证的结构事实标签；
- 规定全量节点生产与未来稀疏节点生产的共同约束。

本规范不负责：

- 在 CC 中生产角色资产；
- 在 UE 中决定材质、灯光或镜头参数；
- 把多个编辑压缩为一条边；
- 用文本差异代替语义配置差异；
- 要求男女两个不兼容域组成一个全局连通分量。

## 2. 图模型与术语

### 2.1 节点

一个节点表示一条可渲染视频的完整语义状态。首批数据的可编辑向量为：

```text
(identity_id, outfit_id, action_id, camera_id)
```

以下字段也是节点契约的一部分，但首批中固定不变：

```text
expression_id = happy
fps = 30
frame_count = 150
duration_seconds = 5
```

节点结构、ID 规范和媒体字段由 [`CONFIG_GRAPH_SCHEMA_V1.md`](../schema/CONFIG_GRAPH_SCHEMA_V1.md) 定义。

### 2.2 兼容域

`compatibility_domain_id` 表示允许通过原子编辑边互相到达的一组节点。首批数据只有两个域：

| compatibility_domain_id | 性别约束 | 身份数 | 服装数 | 动作数 | 相机数 | 节点数 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `female_v1` | female | 4 | 4 | 5 | 4 | 320 |
| `male_v1` | male | 4 | 4 | 5 | 4 | 320 |

禁止跨域边和跨域链。每个域必须单独连通；不要求两个域之间连通。

未来可把骨架世代、服装适配族、年龄能力或其他硬兼容条件加入域定义，但不得把不兼容状态靠特殊边强行连接。

### 2.3 原子边

一条合法有向边必须：

1. 起点和终点属于同一兼容域；
2. 恰好改变一个可编辑轴；
3. 其余语义字段完全一致；
4. 起点和终点均已登记；
5. 不能是 `A→A`。

首批只允许四类边：

| edge_type | 轴 | 含义 |
| --- | --- | --- |
| `E1` | `identity_id` | 更换身份，保持服装、动作和相机不变 |
| `E2` | `outfit_id` | 更换服装，保持身份、动作和相机不变 |
| `E3` | `action_id` | 更换身体动作，保持身份、服装和相机不变 |
| `E7` | `camera_id` | 更换相机，保持身份、服装和动作不变 |

首批不包含 `E11` 表情编辑。`expression_id=happy` 是冻结条件，不是当前图的可编辑轴。

### 2.4 距离

- **语义 Hamming 距离**：起终节点在四个可编辑轴上取值不同的轴数量，范围为 0–4。
- **链长度**：链中边的数量；长度 3–5 对应 4–6 个节点。
- **图距离**：在已登记边图中，从一个节点到另一个节点的最短路径长度。

本项目只要求每条交付链由合法原子边组成，不要求任意两个已渲染节点之间的图距离都等于语义 Hamming 距离。后者属于全局等距约束，会显著增加稀疏图的桥接成本，且不是训练样本成立的必要条件。

## 3. 首批节点池

首批采用完整笛卡尔积节点池：

```text
8 identities × 4 outfits × 5 same-sex actions × 4 cameras × 1 expression
= 640 unique semantic nodes
```

等价地，每个兼容域为：

```text
4 identities × 4 outfits × 5 actions × 4 cameras = 320 nodes
```

四个生产相机固定为：

```text
near, far, high, side
```

每个节点只渲染一次，媒体可被任意数量的链复用。首批必须让全部 640 个节点至少被一条链引用一次。

## 4. 所有链的共同不变量

无论采样策略如何，每条链都必须满足：

1. `edit_length ∈ {3,4,5}`；
2. `len(node_ids) = edit_length + 1`；
3. `len(edge_ids) = len(edge_axes) = len(instructions) = edit_length`；
4. 相邻节点之间存在已登记的有向原子边；
5. 全链只属于一个 `compatibility_domain_id`；
6. 不包含 no-op、悬空节点、悬空边或未登记轴；
7. 每条指令只描述对应边上的一个变化；
8. 相同规范化配置必须复用同一个 `node_id`；
9. 相同 `node_id` 不得对应不同配置或不同权威媒体；
10. 完全相同的有序节点/边路径不得作为两条独立配置链重复交付。

允许不同链复用节点、媒体、有向边、起点或终点。文本改写属于语言增强层，不增加配置链数量。

## 5. 两种采样策略

`chain_policy` 只允许以下两个值。

### 5.1 `progressive_shortest`

该策略生成无回退的语义最短链：

- 每个可编辑轴最多出现一次；
- 不重复访问节点；
- 不回到任一轴的历史值；
- `edit_length` 必须等于起终节点的语义 Hamming 距离；
- 首批只生成长度 3 或 4，不生成长度 5。

因此该策略的事实标签必须满足：

```text
is_semantic_shortest = true
has_repeated_axis = false
has_consecutive_same_axis = false
has_rollback = false
returns_to_start = false
```

生成器不能仅按策略名写入这些值；验收器仍须从路径重新计算。

### 5.2 `freeform_walk`

该策略用于覆盖自然回退、反复修改和闭环行为：

- 可以多次修改同一轴；
- 可以连续两次修改同一轴；
- 可以重复访问节点或有向边；
- 可以回到某一轴之前使用过的值；
- 可以最终回到起点；
- 可以偶然生成语义最短链。

`freeform_walk` 描述的是采样过程，不是结果标签。因此不能强制所有 freeform 链都具有回退、重复轴或闭环，也不能因为某条 freeform 链恰好最短就把它改标为 `progressive_shortest`。

## 6. 结构事实标签

每条链必须保存以下五个布尔字段，并由验收器根据 `node_ids` 与 `edge_axes` 独立重算。

### 6.1 `is_semantic_shortest`

```text
edit_length == hamming(start_node, end_node)
```

这里的 shortest 指四个可编辑轴上的语义最短，不是对完整边图执行全点对最短路后的图距离结论。

### 6.2 `has_repeated_axis`

某一 `edge_axis` 在链中出现两次或以上。

示例：

```text
outfit → camera → outfit
```

### 6.3 `has_consecutive_same_axis`

任意两条相邻边修改同一轴。

示例：

```text
outfit A → outfit B → outfit C
```

### 6.4 `has_rollback`

对某个轴执行编辑时，该步目标值已经在该轴更早的状态历史中出现。

示例：

```text
outfit A → outfit B → outfit A
```

回退必须通过真实边完成，不能只修改链标签。

### 6.5 `returns_to_start`

末节点的完整规范化配置与首节点完全一致。

### 6.6 必然关系

验收器至少检查：

```text
has_consecutive_same_axis => has_repeated_axis
has_rollback => has_repeated_axis
returns_to_start => has_rollback
```

违反任一关系说明标签算法、路径或配置解析存在错误。

## 7. 首批 4,000 条链配额

### 7.1 策略与兼容域

| compatibility_domain_id | progressive_shortest | freeform_walk | 合计 |
| --- | ---: | ---: | ---: |
| `female_v1` | 1,000 | 1,000 | 2,000 |
| `male_v1` | 1,000 | 1,000 | 2,000 |
| 合计 | 2,000 | 2,000 | 4,000 |

策略比例固定为 50% / 50%。男女域同样各占 50%。

### 7.2 链长度

| compatibility_domain_id | chain_policy | 长度 3 | 长度 4 | 长度 5 | 合计 |
| --- | --- | ---: | ---: | ---: | ---: |
| `female_v1` | `progressive_shortest` | 500 | 500 | 0 | 1,000 |
| `male_v1` | `progressive_shortest` | 500 | 500 | 0 | 1,000 |
| `female_v1` | `freeform_walk` | 334 | 333 | 333 | 1,000 |
| `male_v1` | `freeform_walk` | 333 | 333 | 334 | 1,000 |
| 合计 |  | 1,667 | 1,666 | 667 | 4,000 |

这些是首批精确计数，不是近似比例。

### 7.3 编辑轴分布

全体链边数中，`E1/E2/E3/E7` 的目标占比各为 25%。默认验收容差为每个轴 `±2` 个百分点；冻结的源清单可进一步收紧，但不得静默放宽。

采样器应按当前欠额对合法出边加权，不应在链生成完毕后直接改写轴标签以伪造比例。

### 7.4 节点覆盖

- 640 个节点全部至少出现一次；
- 覆盖可发生于起点、中间节点或终点；
- 不设 freeform 五个事实标签的目标比例，只报告真实分布；
- 任何后续策略比例调整只需重建链清单，不要求重渲染未变化的节点媒体。

## 8. 确定性采样流程

推荐实现顺序：

1. 读取并验证冻结的 `nodes`、`edges`、兼容域和配额清单；
2. 按兼容域、策略和长度建立精确 quota buckets；
3. 用固定 `sampler_seed` 初始化确定性随机源；
4. 优先覆盖尚未被引用的节点；
5. 再按编辑轴欠额、身份/服装/动作/相机覆盖欠额选择起点和出边；
6. 对 `progressive_shortest` 维护已使用轴集合；
7. 对 `freeform_walk` 不预设事实标签，但在候选完成后计算标签；
8. 对候选链执行原子性、域、长度、配额、引用和去重验证；
9. 使用规范化路径生成稳定 `chain_id`；
10. 达成精确 bucket 配额后执行全局覆盖、比例和连通性检查；
11. 生成指令与渲染任务引用；
12. 写出机器可读验收报告。

随机种子、采样器版本、源清单哈希和规范版本必须进入产物，确保同一输入可复现同一条链集合。

## 9. 链记录最小字段

每条链至少包含：

```json
{
  "chain_id": "chain_...",
  "schema_version": "config_graph_v1",
  "sampling_spec_version": "multi_round_v1_20260824",
  "sampler_version": "...",
  "sampler_seed": 0,
  "source_manifest_id": "...",
  "compatibility_domain_id": "female_v1",
  "chain_policy": "progressive_shortest",
  "edit_length": 4,
  "start_node_id": "node_...",
  "end_node_id": "node_...",
  "node_ids": ["node_..."],
  "edge_ids": ["edge_..."],
  "edge_axes": ["identity_id", "outfit_id", "action_id", "camera_id"],
  "instructions": ["..."],
  "is_semantic_shortest": true,
  "has_repeated_axis": false,
  "has_consecutive_same_axis": false,
  "has_rollback": false,
  "returns_to_start": false
}
```

`node_ids`、`edge_ids`、`edge_axes` 和 `instructions` 在真实记录中必须写出完整长度；上例仅展示字段形状。

## 10. 指令生成

每条指令只描述一条边上的唯一变化。指令可采用：

- 显式目标值，如“把服装换成 O03”；
- 历史指代，如“换回第一轮使用的服装”；
- 相对表达，如“恢复之前的侧面镜头”。

历史指代必须能由链状态唯一解析。若同一值多次出现，必须使用轮次或显式目标消除歧义。指令不得暗示未变化的身份、服装、动作或相机。

指令生成失败不能通过删除语义边规避；应修复模板或把该链标记为语言层失败后重新生成文本。

## 11. 去重、媒体复用与数据划分

### 11.1 配置链去重

规范化有序 `node_ids` 与 `edge_ids` 路径相同即视为同一配置链。以下情况不算重复：

- 起终点相同但中间路径不同；
- 原路径与反向路径；
- 共享部分节点或边；
- 不同链引用同一视频。

同一路径的不同文本改写属于同一配置链的语言增强，不计入 4,000 条配置链配额。

### 11.2 媒体复用

`node_id` 是视频复用键。渲染器只为唯一节点生成一份权威媒体，链记录通过 `node_id` 引用它。

### 11.3 数据集划分

训练/验证/测试划分必须按冻结的语义实体或连通子图规则执行，不能在媒体文件层随机拆散同一节点的引用。具体 split 策略尚未冻结，首批不得自行假设。

## 12. 全量与稀疏生产模式

### 12.1 首批：`full_pool`

首批仅有 640 个节点，因此完整物化两域的全部节点。推荐顺序为：

```text
冻结节点和边
→ 生成并验证 4,000 条链
→ 生成 640 个唯一节点的渲染任务
→ 渲染与失败重试
→ 回填媒体状态并做最终链验收
```

即使链只引用了部分节点，首批仍必须渲染完整 640 节点池，以便快速验证和后续重采样。

### 12.2 正式生产：`referenced_nodes_plus_connectivity`

未来笛卡尔积过大时，先构建链，再渲染：

```text
所有链引用节点的并集
+ 为保持每个兼容域连通而加入的桥接节点
```

桥接节点必须登记 `node_role=connectivity_bridge`，并与普通链节点使用同一 schema、渲染和质量门禁。不能创建未渲染的虚拟节点或跨域捷径。

正式生产只要求每个兼容域连通和交付链逐边合法，不要求完整笛卡尔积，也不要求全点对图距离等于语义 Hamming 距离。

## 13. 验收报告与硬失败条件

采样报告至少包含：

- 节点总数、每域节点数和每域连通分量数；
- 链总数、策略 × 域 × 长度交叉表；
- 四个编辑轴的边计数与比例；
- 五个事实标签的真实数量和比例；
- 640 节点覆盖率、节点复用率、最大/最小引用次数；
- 唯一链数、重复链数、重复边和重复节点统计；
- no-op、跨域边、跨域链、悬空引用和标签重算不一致数量；
- 源清单、规范、采样器和随机种子的版本信息。

以下任一情况必须硬失败：

- 节点数不是 640，或两个域不是各 320 个节点；
- 任一兼容域不连通；
- 存在跨域边或跨域链；
- 链数、策略配额或长度配额不符合第 7 节精确值；
- 任一无效边、no-op、悬空引用或不存在的媒体引用；
- 五个事实标签与重算结果不一致；
- 同 `chain_id` 对应不同路径；
- 同 `node_id` 对应不同规范化配置；
- 640 节点未全部被链覆盖；
- 四轴任一占比超出冻结容差；
- 完整重复配置链数量大于 0。

渲染失败可先进入可重试队列，但在最终数据集发布前，任何交付链引用的节点都必须拥有通过媒体验收的权威视频。

## 14. 当前实现状态与后续变更

`build_first_batch_config_graph_v1.py` 已迁移到本规范并生成第一批权威图根 `00_engine/outputs/first_batch_dataset/graph_20260824_v1/`。当前结构结果为 640 节点、8,320 条有向原子边、4,000 条链和 640 个去重 Render Job；双策略、五个事实标签、精确配额和全节点覆盖均已通过本地机器门禁。

当前完成只代表 `GATE-70 JOB_GRAPH_ACCEPTED`。服务器媒体、GT/sidecar、失败重试和发布验收仍属于 `WF-80/WF-90`，不能因结构图通过而把整批数据标记为 accepted。

后续修改表达式、兼容域、编辑轴、链策略或配额时必须：

- 更新本规范或创建后继版本，不能静默复用 V1 名称；
- 生成新的 source manifest 与输出目录，不能原地混入旧链类别；
- 重新执行 [`VALIDATION_CATALOG.md`](../character_creator/full_process/technical/validation/VALIDATION_CATALOG.md) 中的数据集门禁；
- 在 [`CONFIG_GRAPH_AND_CHAINS.md`](../character_creator/full_process/technical/dataset/CONFIG_GRAPH_AND_CHAINS.md) 登记实际命令、输入、输出和保留等级。
