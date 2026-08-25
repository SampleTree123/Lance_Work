# 配置图与编辑链

> 文档 ID：`TECH-DATASET-01`
> 文档类型：`technical`
> 生命周期：`current`
> 适用阶段：`WF-10/WF-70`
> 实现所有权：首批图源、节点、原子边、兼容域、链和 Render Job 清单
> 验证所有权：`VAL-GRAPH-01`
> 输出契约：`OUT-WF70-JOB-GRAPH`
> 运行环境：系统 Python 3
> 最近核验：2026-08-25

## 1. 权威规范

- Schema：`20_planning/data_design/schema/CONFIG_GRAPH_SCHEMA_V1.md`
- 链策略：`20_planning/data_design/sampling/MULTI_ROUND_CHAIN_SAMPLING_V1.md`
- 架构决定：`project_management/decisions/ADR-0014-COMPATIBILITY-DOMAINS-AND-CHAIN-POLICIES.md`

配置路径是语义权威。文本和视频 URI 从图派生，不能先写 Prompt 再反推节点。

## 2. 第一批冻结语义

```text
female_v1: 4 identities × 4 outfits × 5 actions × 4 cameras = 320 nodes
male_v1:   4 identities × 4 outfits × 5 actions × 4 cameras = 320 nodes
expression_id = happy (fixed)
total = 640 nodes
```

原子编辑轴为身份 `E1`、服装 `E2`、动作 `E3` 和相机 `E7`。两个性别域各自连通，不允许跨域边。当前完整图包含 8,320 条有向原子边。

链只使用：

- `progressive_shortest`：不重复轴、不回退、语义最短；
- `freeform_walk`：允许重复轴、连续同轴、回退和闭环。

首批精确生成 4,000 条 3–5 步链，并保存五个重算标签：`is_semantic_shortest`、`has_repeated_axis`、`has_consecutive_same_axis`、`has_rollback`、`returns_to_start`。

## 3. 输入与编译顺序

权威输入：

```text
00_engine/scripts/dataset/first_batch_required_exports_20260824_v3.json
00_engine/scripts/unreal/first_batch_local_render_matrix_20260824_v1.json
```

这两个输入分别由以下正式入口生成，必须先于图源编译运行：

```powershell
python .\00_engine\scripts\dataset\build_first_batch_required_exports_v1.py
python .\00_engine\scripts\dataset\build_first_batch_local_render_matrix_v1.py
```

前者把 32 Look、10 Action、窗口与 Expression Profile 冻结为必需导出 Manifest；后者从已冻结导出和动作池生成覆盖 32 Look/四相机的本地视觉验收矩阵。它们不是最终节点图，不能代替下面的 Graph Builder。

生成图源：

```powershell
python .\00_engine\scripts\dataset\build_first_batch_graph_source_v1.py `
  --output .\00_engine\scripts\dataset\first_batch_graph_source_20260824_v1.json
```

编译图：

```powershell
python .\00_engine\scripts\dataset\build_first_batch_config_graph_v1.py `
  --source .\00_engine\scripts\dataset\first_batch_graph_source_20260824_v1.json `
  --output-dir .\00_engine\outputs\first_batch_dataset\graph_20260824_v1
```

生成代表链审查包：

```powershell
python .\00_engine\scripts\dataset\build_first_batch_chain_review_v1.py `
  --graph-dir .\00_engine\outputs\first_batch_dataset\graph_20260824_v1 `
  --output-dir .\00_engine\outputs\first_batch_dataset\graph_20260824_v1\review_10
```

## 4. 输出契约

图根至少包含：

```text
source_manifest.json
assets.json
compatibility_domains.json
nodes.jsonl
edges.jsonl
chains.jsonl
render_jobs.jsonl
required_exports.json
build_report.json
```

这些文件及其输入哈希属于 `authoritative`。`review_10/` 是 `retained_evidence`；临时调试图和被新版本完全替代的图根标记为 `superseded` 后才可清理。

当前接受的图根为 `%OUTPUT_ROOT%/first_batch_dataset/graph_20260824_v1/`；Retention Policy 以去掉 `%OUTPUT_ROOT%/` 的相对前缀 `first_batch_dataset/graph_20260824_v1` 锁定它。

## 5. 机器验证与硬门禁

- 640 个唯一节点，两个域各 320；
- 每域一个连通分量，跨域边/链为 0；
- 8,320 条边均只改变一个轴；
- 4,000 条链满足精确策略/域/长度配额；
- 640 节点全部被链覆盖；
- 五个事实标签重算一致；
- no-op、悬空引用、重复完整路径和 ID 冲突均为 0；
- 5 秒、30 FPS、150 帧、2560×1440 和四相机一致。

`build_report.status=passed` 只代表结构图通过，不代表媒体已经存在或数据集可发布。

## 6. 变更与恢复

冻结输入、编辑轴、兼容域、渲染配置或采样配额改变时，生成新 `source_manifest_id` 和新输出目录。失败时不要手改 JSONL；修复上游 Registry/Builder 后确定性重建，并比较 Manifest 哈希与报告。
