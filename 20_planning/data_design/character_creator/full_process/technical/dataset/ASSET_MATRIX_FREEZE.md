# 资产与生产矩阵冻结

> 文档 ID：`TECH-DATASET-04`
> 文档类型：`technical`
> 生命周期：`current`
> 适用阶段：`WF-20`
> 实现所有权：生产资产 ID、来源 Registry、兼容域、排除项、必需导出和矩阵完整性
> 验证所有权：`VAL-MATRIX-01`
> 输出契约：`OUT-WF20-ASSET-MATRIX`
> 运行环境：系统 Python；资产候选验证可能需要 CC/UE
> 最近核验：2026-08-25

## 1. 能力与边界

本能力把已验证候选收敛为批次允许使用的稳定 ID 和组合边界。它只冻结已存在证据，不在此阶段临时修复 CC/UE 资产，也不把外部文件夹名称当作稳定 ID。

## 2. 第一批机器输入

| 对象 | 机器权威 |
| --- | --- |
| 32 个 Look | `00_engine/scripts/character_creator/cc_first_batch_full_reference_looks_20260822_v3.json` |
| 生产动作池 | `00_engine/scripts/character_creator/cc_first_batch_action_pool_20260824_v1.json` |
| 动作来源/窗口 | `00_engine/scripts/character_creator/cc_first_batch_action_registry_20260821_v4.json` |
| 表情配置 | `00_engine/scripts/unreal/first_batch_expression_profile_20260820_v1.json` |
| 场景/相机/动作矩阵 | `00_engine/scripts/unreal/first_batch_local_render_matrix_20260824_v1.json` |
| 必需二进制导出 | `00_engine/scripts/dataset/first_batch_required_exports_20260824_v3.json` |

BodyFit、Identity、Appearance、Outfit 和来源资产的细分 Registry 由 [CC 技术索引](../character_creator/README.md) 解释；本页只拥有本批选择和兼容关系。

## 3. 生成与审计入口

在 `%LANCE_ROOT%`：

```powershell
python 00_engine/scripts/dataset/build_first_batch_required_exports_v1.py
python 00_engine/scripts/dataset/build_first_batch_local_render_matrix_v1.py
python 00_engine/scripts/character_creator/cc_audit_first_batch_full_reference_matrix_v1.py
python -m pytest 00_engine/scripts/dataset/tests 00_engine/scripts/character_creator/tests -q
```

Builder 必须从上游 Registry 读取，不允许在代码中静默补默认资产。生成文件变化后比较计数、稳定 ID、来源哈希和兼容域，再决定是否接受新版本。

## 4. 矩阵契约

每条生产记录至少包含稳定 ID、性别/兼容域、源引用、来源哈希、所需二进制/UE Object Path、允许组合、排除原因和版本。Full-body、槽位池、动作 Root Motion/InPlace、表情和相机规则必须在进入图构建前闭合。

## 5. 输出与保留

`OUT-WF20-ASSET-MATRIX` 是 Git 管理的 Registry/清单和完整性报告；外部 CC/服装/动作二进制只通过路径别名、稳定 ID 和哈希引用。候选审查媒体属于 `run_evidence`，只有支撑当前选择的决定需要 `retained_evidence`。

## 6. 验证与恢复

`VAL-MATRIX-01` 要求所有 ID 可解析、来源哈希存在、兼容域闭合、计数与 `OUT-WF10-BATCH-SPEC` 一致、排除项有原因且无隐式默认。失败时修复上游 Registry/兼容规则并生成新版本清单；禁止在 CC 组装或 UE 导入时临时换资产而不回写矩阵。

当前实现由多个首批专用 Registry/Builder 组成，不是任意资产库的通用求解器。扩展到新批次时必须重新执行，而不是复制首批计数。
