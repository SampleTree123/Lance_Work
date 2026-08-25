# 第一批数据配置图 Schema V1

> 文档角色：`technical_specification`
> 状态：`planned`
> 适用阶段：`WF-08..WF-09`
> 权威范围：第一批数据的资产、节点、原子边、链、渲染作业和可追溯字段
> 上级入口：[`README.md`](./README.md)
> 上游：[`FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`](../character_creator/full_process/planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md)
> 下游：节点图生成器、链采样器、UE 渲染调度器和数据集验证器
> 最近核验：2026-08-20

## 1. 设计目标

Schema 必须同时满足：确定性重建、原子编辑、节点复用、失败重试、跨机器路径可移植和最终媒体追溯。显示名不能充当主键；本地绝对路径不能成为跨机器身份。

## 2. 文件集合

| 文件 | 单位 | 作用 |
| --- | --- | --- |
| `assets.json` | 单个 JSON | 冻结身份、BodyFit、服装、动作、表情、场景、相机、灯光、锚点和渲染档案资产 |
| `required_exports.json` | 单个 JSON | 本轮 CC→UE 必需 Look 与动作清单 |
| `nodes.jsonl` | 每行一个节点 | 每个唯一可渲染状态 |
| `edges.jsonl` | 每行一条有向边 | 只改变一个编辑轴的合法转换 |
| `chains.jsonl` | 每行一条链 | 3–5 次编辑的有序节点/边路径 |
| `render_jobs.jsonl` | 每行一个作业 | node_id 到 UE Sequence、输出和重试状态的映射 |
| `media_manifest.jsonl` | 每行一个媒体项 | 视频、sidecar、校验和、帧数和渲染版本 |
| `failures.jsonl` | 每行一次失败 | 可重试失败及其诊断，不覆盖旧记录 |

## 3. ID 规则

- ID 使用 ASCII、小写 snake/kebab 组合，不能包含显示名空格或本地盘符。
- `asset_id` 在同一资产类型内唯一且版本稳定。
- `node_id` 由完整规范化配置的 SHA-256 派生，建议格式 `n_<前16位>`。
- `edge_id` 由 `source_node_id + target_node_id + edit_axis` 派生。
- `chain_id` 由有序 node/edge 路径、采样策略版本和 seed 派生。
- 任何影响像素或 GT 的参数变化都必须产生新 node_id。

## 4. Asset 记录

每个资产至少包含：

| 字段 | 含义 |
| --- | --- |
| `asset_id` | 稳定逻辑 ID |
| `asset_type` | `identity/bodyfit/outfit/action/expression/scene/camera/lighting/anchor/render_profile` |
| `sex_compatibility` | `female/male/unisex` |
| `source_ref` | 当前机器注册表或 UE 软对象路径 |
| `content_sha256` | 源文件或规范配置哈希 |
| `version` | 资产版本 |
| `status` | `frozen/validated/rejected` |
| `constraints` | Skeleton、BodyFit、服装、面部通道或镜头约束 |

## 5. Node 记录

节点是一次视频渲染的最小去重单位。必需字段：

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| `schema_version` | string | 固定 `config_graph_v1` |
| `node_id` | string | 由规范化 `config` 派生 |
| `config.sex` | enum | `female/male` |
| `config.bodyfit_id` | string | 本轮只允许 `F02_Average/M02_Average` |
| `config.identity_id` | string | 每性别 4 个 |
| `config.outfit_id` | string | 属于同性完整 `4 identity × 4 outfit` FullReference 矩阵 |
| `config.action_id` | string | 角色同性兼容的 5 条之一；当前生产池共 10 个动作 |
| `config.expression_id` | enum | `happy/angry/sad`；影响渲染和 node ID，但本批不可编辑 |
| `config.scene_id` | string | 本轮单场景 |
| `config.camera_id` | enum | `medium/full_body` |
| `config.lighting_id` | string | 本轮固定 |
| `config.anchor_id` | string | 本轮固定安全站位 |
| `config.duration_frames` | integer | 首批默认 150（5 秒）；降级档允许 90（3 秒）或 60（2 秒） |
| `config.fps` | integer | 30 |
| `config.resolution` | object | 基准前默认 1280×720 |
| `config.seed` | integer | 确定性；无运行时随机 |
| `render_profile_id` | string | 渲染设置版本 |
| `expected_media_uri` | string | 相对数据集根的路径 |

合法性约束：

- `camera=full_body` 时 `expression=happy`。
- `expression=angry/sad` 时 `camera=medium`。
- identity/outfit 必须存在于 Sprint 的同性完整 `4 × 4` FullReference 矩阵。
- action 必须和角色 Skeleton、Root Motion 策略及 face policy 兼容。

## 6. Edge 记录

| 字段 | 含义 |
| --- | --- |
| `edge_id` | 稳定有向边 ID |
| `source_node_id` / `target_node_id` | 两个已存在节点 |
| `edit_axis` | `E1/E2/E3/E7`；本批禁止 `E11` 表情编辑 |
| `before_value` / `after_value` | 该轴前后值 |
| `changed_fields` | 规范化字段路径数组，长度必须符合轴契约 |
| `inverse_edge_id` | 若存在，指向反向边 |
| `instruction_templates` | 可用于自然语言生成的模板 ID，不保存最终随机文本 |

验证器必须比较完整节点配置，确认除该轴允许字段外全部相同。`source_node_id == target_node_id` 或 `before_value == after_value` 直接失败。

## 7. Chain 记录

| 字段 | 含义 |
| --- | --- |
| `chain_id` | 有序路径哈希 ID |
| `start_node_id` | 初始状态 |
| `edge_ids` | 长度 3–5 |
| `node_ids` | 长度为 `edge_ids + 1`，允许重复 |
| `edit_axes` | 与边一一对应 |
| `chain_class` | `progressive/rollback/closed_cycle` |
| `sampling_seed` | 可复现采样 seed |
| `sampler_version` | 采样器版本 |
| `instructions` | 每轮最终文本及语言标记 |

链可以重复节点，但不得包含无效边。`closed_cycle` 要求最后节点等于初始节点；`rollback` 至少包含一条回到历史值的边。

## 8. Render Job 与媒体

`render_jobs.jsonl` 只调度唯一节点。状态使用 `pending/running/succeeded/retryable_failed/permanent_failed`。每个作业包含 attempt、机器、UE 版本、项目 revision、Sequence、开始/结束时间、日志相对路径和输出临时路径。

成功后原子晋升到媒体目录，并写入：

- 视频 SHA-256、字节数、编码、帧数、fps、分辨率和时长。
- sidecar SHA-256 与对应 node_id。
- 可选首/中/末帧审查图。
- UE/插件/渲染档案版本。

失败重试不得改变 node config；需要改变设置时必须产生新 render_profile_id 和新 node_id。

## 9. 目录建议

```text
dataset_root/
  manifests/
  media/nodes/<node_id>/
  chains/<chain_id>.json
  logs/render/<node_id>/
  reports/
```

链目录默认只保存 JSON 引用。需要文件树兼容输出时使用硬链接或受控引用清单，不复制视频字节。

## 10. 必需验证

1. 所有 ID 唯一且可重新计算。
2. 所有本地引用存在，所有跨机器引用使用相对路径或 UE 软对象路径。
3. 每条边恰好改变一个轴。
4. 每条链有 3–5 条合法边，节点数等于边数加一。
5. 所有节点媒体和 sidecar 哈希匹配。
6. 0 个悬空 asset/node/edge/media 引用。
7. 同一 node_id 不得产生两个不同内容哈希；发现时整批停止。

本规范在首个本地完整链通过前保持 `planned`；通过后再登记实现文件和验证入口。

## 11. 当前部分实现

`00_engine/scripts/dataset/build_first_batch_config_graph_v1.py` 已实现本规范中冻结资产、32 个完整矩阵 Look、每性别 5 个动作、4 个镜头/表情渲染状态、640 节点、原子边、4,000 条 3–5 轮链和渲染作业的确定性生成，并由 `00_engine/scripts/dataset/tests/test_build_first_batch_config_graph_v1.py` 覆盖关键不变量。Happy/Angry/Sad 均保留为渲染状态，但生成器不产生 `E11` 边。

该实现当前只通过合成冻结输入测试。8 个身份、8 套服装、场景、相机、灯光、锚点和渲染档案的真实稳定 ID 尚未全部冻结，因此不得把测试输出登记为第一批正式 `assets.json` 或正式渲染队列。
