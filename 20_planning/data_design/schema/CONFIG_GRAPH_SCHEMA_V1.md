# 第一批数据配置图 Schema V1

> 文档角色：`technical_specification`
> 状态：`current`
> 规范状态：`accepted`
> 实现状态：`implemented_local`
> 适用阶段：`WF-70/WF-80/WF-90`
> 权威范围：第一批数据的资产、兼容域、节点、原子边、链、渲染作业、媒体和追溯字段
> 上级入口：[`README.md`](./README.md)
> 采样规则：[`MULTI_ROUND_CHAIN_SAMPLING_V1.md`](../sampling/MULTI_ROUND_CHAIN_SAMPLING_V1.md)
> 文本规则：[`MULTI_ROUND_VIDEO_EDIT_TEXT_SCHEMA_V1.md`](./MULTI_ROUND_VIDEO_EDIT_TEXT_SCHEMA_V1.md)
> 上游：[`PLAN-2026-08-FIRST-DATA-BATCH.md`](../character_creator/full_process/project_management/history/completed_plans/PLAN-2026-08-FIRST-DATA-BATCH.md)
> 架构决定：[`ADR-0014-COMPATIBILITY-DOMAINS-AND-CHAIN-POLICIES.md`](../character_creator/full_process/project_management/decisions/ADR-0014-COMPATIBILITY-DOMAINS-AND-CHAIN-POLICIES.md)
> 下游：配置图生成器、链采样器、UE 渲染调度器和数据集验证器
> 最近核验：2026-08-24

## 1. 设计目标

Schema 必须同时满足：确定性重建、原子编辑、兼容域隔离、节点媒体复用、失败重试、跨机器路径可移植和最终媒体追溯。

核心原则：

- 显示名不能充当主键；
- 本地绝对路径不能成为跨机器身份；
- 配置、ID、媒体和链之间必须可双向追溯；
- 任何影响像素、时序或 Ground Truth 的参数变化都产生新 `node_id`；
- 同一 `node_id` 只能有一套规范化配置和一份权威媒体；
- 文本指令从合法边派生，不能反向决定图结构。

## 2. 首批冻结契约

| 项目 | 冻结值 |
| --- | --- |
| 身份 | female 4 + male 4 |
| 同性服装 | 每性别 4 套 |
| 动作 | 每性别 5 条，共 10 条 |
| 相机 | `near/far/high/side` |
| 表情 | 固定 `happy`，本批不可编辑 |
| BodyFit | female=`F02_Average`，male=`M02_Average` |
| 场景、灯光、锚点 | 每批冻结一个版本 |
| 帧率 | 30 fps |
| 时长 | 150 帧 / 5 秒 |
| 默认分辨率 | 2560×1440 |
| 节点数 | 640，两个兼容域各 320 |
| 链数 | 4,000，规则见采样规范 |

首批节点公式：

```text
8 identities × 4 same-sex outfits × 5 same-sex actions × 4 cameras × 1 expression
= 640 nodes
```

历史本地 32-Look 代表矩阵覆盖过三种表情，但它是技术验证证据，不属于本 Schema 的首批正式节点清单。

## 3. 文件集合

| 文件 | 单位 | 作用 |
| --- | --- | --- |
| `source_manifest.json` | 单个 JSON | 冻结规范版本、输入清单哈希、随机种子、期望计数和生产模式 |
| `assets.json` | 单个 JSON | 冻结身份、BodyFit、服装、动作、表情、场景、相机、灯光、锚点和渲染档案 |
| `compatibility_domains.json` | 单个 JSON | 定义域成员、硬兼容条件与期望节点数 |
| `required_exports.json` | 单个 JSON | 本轮 CC→UE 必需 Look 与动作清单；属于资产准备输入 |
| `nodes.jsonl` | 每行一个节点 | 每个唯一可渲染语义状态 |
| `edges.jsonl` | 每行一条有向边 | 同域内只改变一个编辑轴的合法转换 |
| `chains.jsonl` | 每行一条链 | 3–5 次编辑的有序节点/边路径及事实标签 |
| `render_jobs.jsonl` | 每行一个作业 | `node_id` 到 UE Sequence、输出和重试状态的映射 |
| `media_manifest.jsonl` | 每行一个媒体项 | 视频、sidecar、校验和、帧数和渲染版本 |
| `failures.jsonl` | 每行一次失败 | 可重试或永久失败及诊断；只追加，不覆盖旧记录 |
| `reports/*.json` | 每份一类报告 | 图、链、渲染和最终发布门禁结果 |

模型使用的自然语言不直接取自结构链。正式文本位于版本化子目录，包含 `prompt_manifest.json`、`turns.jsonl` 和 `dialogs.jsonl`；契约见 [多轮视频编辑文本 Schema V1](./MULTI_ROUND_VIDEO_EDIT_TEXT_SCHEMA_V1.md)。

## 4. 规范化与 ID

### 4.1 通用规则

- ID 使用 ASCII、小写 snake/kebab 组合；不能包含显示名空格、本地盘符或机器用户名。
- 对象按固定字段顺序与稳定 JSON 编码规范化后再计算 SHA-256。
- 未参与语义身份的运行状态，如 retry 次数，不得进入 `node_id`。
- 影响像素或 GT 的值，如相机、渲染档案、表达式和帧窗口，必须进入节点规范化配置。

### 4.2 ID 派生

| ID | 派生输入 | 建议格式 |
| --- | --- | --- |
| `asset_id` | 资产类型、逻辑身份和版本 | 类型前缀 + 稳定名 |
| `node_id` | 完整规范化 node config | `n_<sha256前16位>` |
| `edge_id` | source、target、edit axis | `e_<sha256前16位>` |
| `chain_id` | 有序 node/edge 路径、规范和采样器版本 | `c_<sha256前16位>` |
| `render_job_id` | node、render profile、attempt policy | `rj_<sha256前16位>` |

同一 ID 对应不同规范化内容是整批硬失败。

## 5. Asset 记录

每个资产至少包含：

| 字段 | 含义 |
| --- | --- |
| `asset_id` | 稳定逻辑 ID |
| `asset_type` | `identity/bodyfit/outfit/action/expression/scene/camera/lighting/anchor/render_profile` |
| `sex_compatibility` | `female/male/unisex` |
| `source_ref` | UE 软对象路径或跨机器 bundle URI |
| `content_sha256` | 源文件或规范配置哈希 |
| `version` | 资产版本 |
| `status` | `frozen/validated/rejected` |
| `constraints` | Skeleton、BodyFit、服装、面部通道、Root Motion 或镜头约束 |

正式清单不得依赖仅当前机器可解析的裸绝对路径。绝对路径可作为本地诊断字段，但不能成为权威 `source_ref`。

## 6. Compatibility Domain 记录

每个域至少包含：

| 字段 | 约束 |
| --- | --- |
| `compatibility_domain_id` | 首批为 `female_v1` 或 `male_v1` |
| `sex` | 与域 ID 一致 |
| `bodyfit_id` | female=`F02_Average`，male=`M02_Average` |
| `identity_ids` | 精确 4 个 |
| `outfit_ids` | 精确 4 个 |
| `action_ids` | 精确 5 个，只含同性动作 |
| `camera_ids` | 精确 `near/far/high/side` |
| `expression_ids` | 精确 `[happy]` |
| `expected_node_count` | 320 |
| `hard_constraints` | Skeleton、服装矩阵、Root Motion 与场景约束 |

任何边或链跨越 `compatibility_domain_id` 都直接失败。两个域必须分别连通，但不要求存在跨域路径。

## 7. Node 记录

节点是一次视频渲染的最小去重单位。必需字段：

| 字段 | 类型 | 首批约束 |
| --- | --- | --- |
| `schema_version` | string | 固定 `config_graph_v1` |
| `node_id` | string | 由规范化 `config` 派生 |
| `compatibility_domain_id` | enum | `female_v1/male_v1` |
| `node_role` | enum | 首批为 `chain_node`；未来可为 `connectivity_bridge` |
| `config.sex` | enum | `female/male`，与域一致 |
| `config.bodyfit_id` | string | `F02_Average/M02_Average` |
| `config.identity_id` | string | 域内 4 个之一 |
| `config.outfit_id` | string | 域内 4 个之一；identity/outfit Look 必须存在 |
| `config.action_id` | string | 域内 5 个之一 |
| `config.expression_id` | enum | 固定 `happy` |
| `config.scene_id` | string | 本轮冻结单场景 |
| `config.camera_id` | enum | `near/far/high/side` |
| `config.lighting_id` | string | 本轮冻结 |
| `config.anchor_id` | string | 本轮冻结安全站位 |
| `config.frame_start` | integer | 冻结窗口起点 |
| `config.duration_frames` | integer | 固定 150 |
| `config.fps` | integer | 固定 30 |
| `config.resolution` | object | 默认 `{width:2560,height:1440}` |
| `config.seed` | integer | 确定性；禁止运行时随机 |
| `render_profile_id` | string | 默认 1440p30 生产档案版本 |
| `expected_media_uri` | string | 相对数据集根路径 |
| `config_sha256` | string | 完整规范化配置哈希 |

合法性约束：

- 每性别必须形成完整 `4 identity × 4 outfit` FullReference Look 矩阵；
- action 必须兼容角色 Skeleton、Root Motion 策略和 face policy；
- camera 必须引用冻结的四台生产相机之一；
- 表情不是首批可编辑轴；
- `frame_start` 变化会改变最终动作窗口，因此参与 node ID；
- 低显存回退若改变分辨率或档案，必须生成新的 `render_profile_id` 和 `node_id`，不能覆盖生产节点。

## 8. Edge 记录

| 字段 | 含义 |
| --- | --- |
| `edge_id` | 稳定有向边 ID |
| `source_node_id` / `target_node_id` | 两个已存在节点 |
| `compatibility_domain_id` | 与两端节点相同 |
| `edge_type` | `E1/E2/E3/E7` |
| `edit_axis` | `identity_id/outfit_id/action_id/camera_id` |
| `before_value` / `after_value` | 该轴前后值，必须不同 |
| `changed_fields` | 规范化字段路径数组；精确对应一个轴 |
| `inverse_edge_id` | 若反向边已登记则引用它 |
| `instruction_template_ids` | 语言生成模板 ID，不保存随机最终文本 |

验证器必须比较完整节点配置，确认除该轴允许字段外全部相同。首批禁止 `E11`，也禁止跨性别、跨域身份替换。

## 9. Chain 记录

| 字段 | 约束 |
| --- | --- |
| `chain_id` | 有序路径哈希 ID |
| `schema_version` | `config_graph_v1` |
| `sampling_spec_version` | 本轮采样规范版本 |
| `source_manifest_id` | 冻结输入清单 |
| `compatibility_domain_id` | 全链唯一域 |
| `chain_policy` | `progressive_shortest/freeform_walk` |
| `edit_length` | 3、4 或 5 |
| `start_node_id` / `end_node_id` | 与 `node_ids` 首尾一致 |
| `edge_ids` | 长度等于 `edit_length` |
| `node_ids` | 长度为 `edit_length + 1`；freeform 允许重复 |
| `edge_axes` | 与边一一对应 |
| `sampling_seed` | 可复现采样 seed |
| `sampler_version` | 采样器版本 |
| `instructions` | 结构构建时的技术审计占位文本；可含内部 ID，不得直接作为模型输入。正式文本由独立文本 Schema 生成 |
| `is_semantic_shortest` | 从路径重算 |
| `has_repeated_axis` | 从路径重算 |
| `has_consecutive_same_axis` | 从路径重算 |
| `has_rollback` | 从路径重算 |
| `returns_to_start` | 从路径重算 |

策略定义、4,000 条精确配额和五个标签算法只由 [`MULTI_ROUND_CHAIN_SAMPLING_V1.md`](../sampling/MULTI_ROUND_CHAIN_SAMPLING_V1.md) 负责。本 Schema 只规定字段和引用完整性。

## 10. Render Job 与媒体

`render_jobs.jsonl` 只调度唯一节点。状态只允许：

```text
pending
running
succeeded
retryable_failed
permanent_failed
```

每个作业至少包含：

- `render_job_id`、`node_id`、attempt 和最大重试策略；
- 机器 ID、UE 版本、项目 revision 和插件版本；
- Map、Sequence、角色 Blueprint、AnimSequence、Face Sequence 和 Camera 引用；
- 开始/结束时间、日志相对路径和临时输出路径；
- pose-driver、帧范围和初始化预检结果。

成功后使用原子晋升写入媒体目录，并在 `media_manifest.jsonl` 保存：

- `node_id` 和最终相对 URI；
- 视频 SHA-256、字节数、编码、帧数、fps、分辨率和时长；
- sidecar SHA-256 与 node config SHA-256；
- 可选首/中/末帧审查图；
- UE、插件、Sequence、Render Profile 和项目 revision；
- 媒体验收状态与报告引用。

失败重试不得改变 node config。需要改变任何像素相关设置时，必须生成新节点，不得静默替换原媒体。

## 11. Source Manifest

`source_manifest.json` 至少冻结：

```json
{
  "schema_version": "config_graph_v1",
  "sampling_spec_version": "multi_round_v1_20260824",
  "production_mode": "full_pool",
  "expected_domain_count": 2,
  "expected_nodes": 640,
  "expected_chains": 4000,
  "expected_render_jobs": 640,
  "fps": 30,
  "duration_frames": 150,
  "resolution": {"width": 2560, "height": 1440},
  "expression_ids": ["happy"],
  "camera_ids": ["near", "far", "high", "side"],
  "sampler_seed": 0,
  "input_manifest_sha256": "..."
}
```

正式生成时 `sampler_seed` 使用冻结值；示例中的 0 不代表最终必须为 0。

## 12. 目录建议

```text
dataset_root/
  manifests/
    source_manifest.json
    assets.json
    compatibility_domains.json
    nodes.jsonl
    edges.jsonl
    chains.jsonl
    render_jobs.jsonl
    media_manifest.jsonl
    failures.jsonl
  media/nodes/<node_id>/
  logs/render/<node_id>/
  reports/
```

链默认只保存 JSON 引用。需要文件树兼容输出时使用硬链接或受控引用清单，不重复复制视频字节。

## 13. 必需验证

1. 所有 ID 唯一且可重新计算；
2. 所有跨机器引用使用 bundle URI、相对路径或 UE 软对象路径；
3. 精确两个兼容域，各 320 节点且分别连通；
4. 节点总数 640，表达式全部为 Happy，四相机均完整覆盖；
5. 每条边同域且恰好改变一个轴；
6. 每条链有 3–5 条合法边，节点数等于边数加一；
7. 链策略、长度、域和事实标签满足采样规范；
8. 全部 640 节点至少被一条链引用；
9. 所有权威节点媒体和 sidecar 哈希匹配；
10. 0 个悬空 asset/node/edge/media 引用；
11. 同一 `node_id` 不得产生两个不同配置哈希或权威媒体内容；
12. 正式发布前所有链引用节点的媒体状态均为 accepted。
13. 正式训练包必须具有通过文本 Schema 门禁的 `video_in + prompt + video_out` 回合，模型文本中内部 ID 泄漏为 0。

具体执行入口与通过证据登记在 [`VALIDATION_CATALOG.md`](../character_creator/full_process/technical/validation/VALIDATION_CATALOG.md)。

## 14. 当前实现边界

`00_engine/scripts/dataset/build_first_batch_config_graph_v1.py` 已完成四相机 × Happy-only、双兼容域、双链策略、五事实标签、1440p30/150 帧、精确配额和全节点覆盖迁移。正式 `graph_20260824_v1/build_report.json` 已通过机器结构门禁。

`00_engine/scripts/dataset/build_first_batch_prompt_layer_v1.py` 在不改变图和媒体的前提下生成双语文本层。当前仍未完成的是服务器 640 节点媒体、GT/sidecar、失败重试和最终发布验收；结构图或文本层通过均不能单独标记整批数据集 accepted。
