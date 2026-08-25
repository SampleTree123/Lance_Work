# CC 角色组装与验收

> 文档 ID：`TECH-CC-04`
> 文档类型：`technical`
> 生命周期：`current`
> 适用阶段：`WF-30`
> 实现所有权：首批 Look 生成器、Bridge staging、RLPy 执行器、聚合审计和视觉证据
> 验证所有权：`VAL-CC-01`、`VAL-CC-02`
> 输出契约：`OUT-WF30-CC-ASSETS`
> 最近核验：2026-08-25

## 1. 能力与边界

当前实现可以按第一批机器清单分阶段构建 32 个烘焙 Look并在 CC 中保存项目；其中共享 RLPy 执行器还可由 `WF-40` 调用来产生 UE 导出 Bundle。规范 CC 项目与 CC 验收属于 `OUT-WF30-CC-ASSETS`，最终 FBX/JSON/纹理 Bundle 及其 Transfer Gate 属于 `OUT-WF40-TRANSFER-BUNDLE`。它是首批特化自动化，不是任意 BodyFit/Identity/Outfit 的通用一键产品。

## 2. 当前实现组成

| 文件 | 角色 | 运行环境 |
| --- | --- | --- |
| `cc_build_first_batch_full_reference_looks_v3.py` | 编译 32 Look、缺失工作单和状态清单 | 系统 Python |
| `cc_first_batch_full_reference_looks_20260822_v3.json` | 32 Look 权威定义 | 机器配置 |
| `cc_first_batch_full_reference_missing_looks_20260822_v1.json` | 补齐 16 Look 工作单 | 机器配置 |
| `run_first_batch_missing_looks_export.ps1` | 为 `WF-40` 分阶段提交当前批次缺失 16 Look；不是全量重建器 | PowerShell/Bridge |
| `cc_validate_body_reconstruction.py` | CC 内加载、装配、截图、保存和导出 | CC/RLPy |
| `cc_audit_first_batch_full_reference_matrix_v1.py` | 合并 CC 结果并验证 32/32 | 系统 Python |

## 3. 输入契约

- BodyFit、Identity、Appearance 和 Outfit Registry 哈希一致。
- 每个 Look ID 在完整矩阵中唯一。
- CC 源项目和资产路径位于 Bridge allowlist。
- 输出使用新 `run_id`，不覆盖已接受项目。

## 4. 执行方式

首先用生成器重新编译工作单并运行其测试：

```powershell
$CCRoot = 'D:\UE\Lance_Work\00_engine\scripts\character_creator'
python "$CCRoot\cc_build_first_batch_full_reference_looks_v3.py"
python -m pytest "$CCRoot\tests\test_cc_build_first_batch_full_reference_looks_v3.py" -q
```

需要 CC 作业时先执行 Bridge 健康检查。查看当前增量入口的参数：

```powershell
Get-Help "$CCRoot\run_first_batch_missing_looks_export.ps1" -Detailed
```

真实执行命令、唯一 Run ID、前置应用状态和 Transfer 输出见 [CC FullReference 到 UE](../transfer/CC_TO_UE_FULLREFERENCE.md#6-cc-导出执行与当前边界)。不得再次执行已完成的 missing-16 作业来“证明”通用性；新矩阵需要新计划、新 Manifest 和新的全量包装器。

## 5. 组装顺序

```text
load canonical BodyFit/source project
  -> apply identity and supported head state
  -> apply proportion/head-neck decisions
  -> apply skin/eyes/teeth/brows/lashes/hair/beard
  -> apply outfit family and footwear
  -> normalize pose/camera/light
  -> machine inspection
  -> visual acceptance
  -> save project and export bundle
```

## 6. 验收

每个生产 Look 至少需要：

- 项目可重载，Inventory、BodyFit、Identity、Outfit 和哈希一致。
- 中性正面/侧面/三分之四取景。
- 眨眼、闭眼、微笑和张嘴无眼球/牙齿/嘴唇硬错误。
- 服装在静态与代表动作中无未接受的严重穿模。
- 材质接缝、皮肤/头部颜色和头发遮挡可接受。

## 7. 输出与保留

规范 `.ccProject`、Look Manifest 和 CC 聚合验收属于 `OUT-WF30-CC-ASSETS`；动态联系表、用户决定和失败根因是其 `retained_evidence`。最终 FBX/JSON/纹理 Bundle、源到 UE 映射与导入 Gate 属于 `OUT-WF40-TRANSFER-BUNDLE`，由 [Transfer Technical](../transfer/CC_TO_UE_FULLREFERENCE.md) 解释。Bridge staging、重复截图和已合并 partial 结果可在最终审计后标为 `superseded/disposable`。

## 8. 恢复

CC 出现未知弹窗、Undo 错误或内存增长时停止当前 Look，保留作业结果，由用户重启后从未完成 ID 恢复。不得把未完成目录晋升为成功 Bundle。
