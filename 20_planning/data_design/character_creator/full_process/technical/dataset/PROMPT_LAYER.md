# 多轮编辑 Prompt 层

> 文档 ID：`TECH-DATASET-02`
> 文档类型：`technical`
> 生命周期：`current`
> 适用阶段：`WF-70/WF-90`
> 实现所有权：身份描述、编辑指令、Turn/Dialog 与媒体 URI 引用
> 验证所有权：`VAL-TEXT-01`
> 输出契约：`OUT-WF70-JOB-GRAPH`
> 运行环境：系统 Python 3
> 最近核验：2026-08-25

## 1. 语义边界

Prompt 层只描述 `chains.jsonl` 中已经存在的原子边。每一轮是 `video_in + prompt + video_out`，且 Prompt 只能要求对应边上的唯一变化。语言改写不产生新配置链，也不修改节点或媒体。

## 2. 权威输入

- 图根：`00_engine/outputs/first_batch_dataset/graph_20260824_v1`
- 文本 Schema：`20_planning/data_design/schema/MULTI_ROUND_VIDEO_EDIT_TEXT_SCHEMA_V1.md`
- Prompt Catalog：`00_engine/scripts/dataset/prompt_catalog_first_batch_v1.json`
- 身份参考图：`00_engine/outputs/character_creator_bridge/artifacts/first_batch_identity_references/full_20260824_v001`

身份编辑必须使用可辨识的目标描述，不只写“换成另一个人”。描述只包含当前参考图可见、跨服装稳定的面部/毛发特征，不推断敏感身份属性。

## 3. 生成命令

```powershell
python .\00_engine\scripts\dataset\build_first_batch_prompt_layer_v1.py `
  --graph-dir .\00_engine\outputs\first_batch_dataset\graph_20260824_v1 `
  --catalog .\00_engine\scripts\dataset\prompt_catalog_first_batch_v1.json `
  --output-dir .\00_engine\outputs\first_batch_dataset\graph_20260824_v1\text_first_batch_20260824_v2
```

正式首批使用 `v2` 身份 grounding 结果。`v1` 已被完整替代，并于 2026-08-25 在核对 `v2` Manifest、计数和文件哈希后清理，不作为发布输入或恢复来源。

## 4. 输出

```text
prompt_manifest.json
prompt_catalog.json
identity_descriptions.json
IDENTITY_DESCRIPTION_REVIEW.md
turns.jsonl
dialogs.jsonl
prompt_report.json
prompt_review.json
PROMPT_REVIEW.md
```

首批应有 4,000 个 Dialog 和 15,000 个 Turn。Manifest、Catalog、Turn/Dialog 和身份描述为 `authoritative`；审查页为 `retained_evidence`。

## 5. 文本验证 Gate

- 每个 Turn 的输入/输出节点与对应边一致；
- 每条 Prompt 只改变一个轴；
- 历史指代可由链状态唯一解析；
- 中英文均非空且语义同向；
- 内部 ID、盘符路径、UE Object Path 和模板占位符泄漏为 0；
- 身份、服装、动作、相机标签覆盖全部冻结值；
- 15,000 个 `video_in_uri`/`video_out_uri` 在发布时都能解析到 accepted 媒体。

媒体尚未渲染时可以先通过文本结构门禁，但不能标记 `media_resolved` 或发布完成。

## 6. 更新与恢复规则

图不变、只改语言时升级 Prompt 版本并复用节点/链；图或身份参考发生变化时必须重新生成并更新输入哈希。禁止直接编辑 `turns.jsonl` 修补单条问题而不更新 Builder/Catalog。

生成或验证失败时保留失败报告，修复 Catalog、模板或 Builder 后写入新版本目录并全量重建文本层。只有媒体 URI 解析失败时不得回写图或修改 Prompt 语义；应修复媒体 Manifest/路径映射后重新执行发布期解析。
