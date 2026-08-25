# 脚本生命周期与所有权

> 文档 ID：`TECH-IMPLEMENTATION-01`
> 文档类型：`technical`
> 生命周期：`current`
> 适用阶段：全部 Workflow
> 实现所有权：Script Catalog Builder、扫描边界、生命周期分类和 Technical owner 规则
> 验证所有权：`VAL-DOC-01`
> 输出契约：`OUT-GLOBAL-SCRIPT-CATALOG`
> 最近核验：2026-08-25

## 1. 能力与边界

本能力保证 Character Factory 每个脚本都有稳定路径、内容哈希、生命周期和 Technical owner。它不替代领域运行手册，也不根据文件名自动把实验脚本晋升为生产入口。

机器权威：

```text
00_engine/scripts/SCRIPT_CATALOG.json
```

## 2. 调用位置

- `WF-00`：确认当前代码目录与文档一致。
- 任一 Workflow 的实现、路径或生命周期改变后：重建 Catalog。
- `WF-90`：确认正式交付可回溯到锁定实现版本。
- 文档维护：执行 `VAL-DOC-01` 前先重建 Catalog。

## 3. 实现组成

| 文件 | 生命周期 | 作用 |
| --- | --- | --- |
| `00_engine/scripts/documentation/build_script_lifecycle_catalog.py` | `utility` | 扫描代码、计算 SHA-256、推断 domain/owner 并生成 Catalog |
| `00_engine/scripts/documentation/check_character_factory_docs.py` | `utility` | 分别检查文档子系统，再检查显式跨层契约、Catalog/Inventory 与哈希新鲜度 |
| `00_engine/scripts/documentation/tests/test_build_output_inventory.py` | `utility` | 覆盖 Catalog 扫描与 owner 规则 |
| `00_engine/scripts/documentation/tests/test_check_character_factory_docs.py` | `utility` | 覆盖最小完整文档树、子系统契约和跨层失败分类 |

当前扫描根固定为：

```text
00_engine/
20_planning/implementation/
```

`10_research/model_experiments/` 是下游模型研究，不属于角色工厂生产实现。`outputs`、缓存、构建目录和第三方二进制不进入脚本目录。

## 4. 生命周期契约

| 生命周期 | 允许用途 |
| --- | --- |
| `production` | 当前默认生产入口，必须被 owner Technical 直接点名并有适用验证 |
| `validated_pilot` | 只在登记范围内使用，不可外推为通用生产能力 |
| `utility` | Builder、审计、迁移、可视化或维护工具 |
| `experimental` | 探索性实现，不作为生产入口 |
| `deprecated` | 已有替代者，等待审查归档/删除 |
| `archived` | 仅为历史复现保留 |

一个 Workflow 可以由多个入口共同完成，不要求虚假的“唯一主脚本”。但所有 `production` 入口必须在同一领域 Technical 中说明调用顺序、输入、输出和验证。

## 5. 生成命令

在 `%LANCE_ROOT%` 使用系统 Python：

```powershell
python 00_engine/scripts/documentation/build_script_lifecycle_catalog.py
python 00_engine/scripts/documentation/check_character_factory_docs.py --json
```

Catalog 每条记录至少包含：仓库相对路径、扫描根、domain、生命周期、是否属于活动批次、owner 文档、文档直接提及位置、字节数和 SHA-256。

## 6. 输出与保留

`00_engine/scripts/SCRIPT_CATALOG.json` 属于 `OUT-GLOBAL-SCRIPT-CATALOG` 和 `authoritative`。它是生成物，但被当前审计和跨机器移交依赖；更新时原子覆盖，不手工维护单条哈希。

## 7. 验证

`VAL-DOC-01` 中的代码检查要求：扫描根无漏项/陈旧项；每个 owner 文档存在；每个 `production` 脚本被其 owner 直接提及；记录大小和 SHA-256 与工作树一致；生命周期值合法。

## 8. 恢复与限制

Catalog 过期时先重建，不通过手改哈希消除错误。owner 规则错误时先修正领域归属和 Technical 文档，再生成 Catalog。生命周期分类仍包含保守启发式；旧 Pilot 未逐项审查前不得批量升级或删除。
