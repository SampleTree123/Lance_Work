# CC 动作到 UE

> 文档 ID：`TECH-TRANSFER-02`
> 文档类型：`technical`
> 生命周期：`current`
> 适用阶段：`WF-40/WF-50`
> 实现所有权：动作选择窗口、CC FBX 导出、标准化和 UE AnimSequence 导入
> 验证所有权：`VAL-TRANSFER-01`（动作传输子项）、`VAL-UE-01`
> 输出契约：`OUT-WF40-TRANSFER-BUNDLE`、`OUT-WF50-RUNTIME-ACCEPTANCE`
> 运行环境：CC UI/Bridge、系统 Python、UE Editor Python
> 最近核验：2026-08-25

## 1. 格式边界

`.rlMotion` 和 `.iMotion` 不能由 UE 直接读取。动作必须先应用到兼容 CC 角色并导出 FBX，再导入到已冻结同性 Skeleton。动作源文件、五秒窗口和 UE AnimSequence 是三个不同对象，不得只凭显示名关联。

## 2. 第一批权威输入

- 动作清单：`00_engine/scripts/character_creator/cc_first_batch_action_registry_20260821_v4.json`
- 生产动作池：`00_engine/scripts/character_creator/cc_first_batch_action_pool_20260824_v1.json`
- 必需导出：`00_engine/scripts/dataset/first_batch_required_exports_20260824_v3.json`
- 图源：`00_engine/scripts/dataset/first_batch_graph_source_20260824_v1.json`

首批生产动作已经收敛为女性 5 个、男性 5 个。每个动作固定五秒窗口；短动作按登记策略补齐。只有 `ACT_F02_CATCH_BREATH` 使用批准的 InPlace Override，其余保留源 Root Motion。

动作选择到 UE 导出工作单由以下正式入口顺序编译：

| 入口 | 作用 |
| --- | --- |
| `cc_ingest_first_batch_action_window_selection_v1.py` | 导入人工选择的五秒窗口并校验动作 ID |
| `cc_prepare_first_batch_action_replacements_v4.py` | 将批准替换动作合并为版本化 Registry Delta |
| `cc_build_first_batch_action_ue_export_v1.py` | 从冻结动作池、窗口和替换结果生成 CC→UE FBX 导出工作单 |
| `prepare_first_batch_motion_fbxs.py` | 规范化冻结 FBX 文件名、路径与导入清单 |
| `run_first_batch_motion_import.py` / `ue_import_first_batch_motions.py` | 编排 UE 导入并在 Editor 内创建/审计 AnimSequence |

## 3. 导出与标准化

CC 中应用动作后按 Unreal Skeleton 导出动作 FBX。导出失败、许可弹窗或缺少源动作时，不伪造空 FBX；替换动作必须产生新动作 ID/版本并重建下游图源。

导入前标准化入口：

```powershell
python .\00_engine\scripts\unreal\prepare_first_batch_motion_fbxs.py
```

该步骤只处理冻结清单中的动作，输出必须继续由必需导出清单锁定。

## 4. UE 导入

UE 已启动时运行：

```powershell
python .\00_engine\scripts\unreal\run_first_batch_motion_import.py --project datatry_02
```

单动作恢复：

```powershell
python .\00_engine\scripts\unreal\run_first_batch_motion_import.py `
  --project datatry_02 --action-id ACT_F02_CATCH_BREATH
```

内部 Payload 为 `ue_import_first_batch_motions.py`。导入时必须选择现有同性 Skeleton，不创建第三套生产 Skeleton；动作 FBX 中缺少未加权 IK/toe 骨的警告只有在姿态、Root、脚部和 Skeleton 检查通过后才可接受。

## 5. 动画通道分类

导入后必须枚举骨骼轨道和曲线：

- `none`：可作为纯身体动作搭配批准面部层；
- `curves`、`bones`、`hybrid`：必须按 [动作、表情与 Morph](../unreal/ANIMATION_EXPRESSION_MORPH.md) 的通道策略处理；
- 完整表演可登记为 `paired/locked`，不得强行拆分。

第一批使用生成后的 Happy Composite，不直接把未知面部轨道的源动作送入渲染节点。

## 6. 验证 Gate 与输出

通过条件：动作长度和窗口可解释、Skeleton 正确、非预期 T-pose 为 0、首中末帧有时间变化、Root Motion 策略与清单一致、服装压力风险已记录。导入聚合报告和代表帧为 `retained_evidence`；标准化临时 FBX 可在权威 Bundle 和哈希确认后标为 `superseded`。

当前接受的首批动作导入证据为 `%OUTPUT_ROOT%/unreal_character_import/first_batch_motions_20260822_v1/`，其策略前缀是 `unreal_character_import/first_batch_motions_20260822_v1`。

## 7. 失败与恢复

单动作导出或导入失败时按 `action_id` 隔离重跑，不重新导入已接受动作。Skeleton、窗口或 Root Motion 策略错误必须修复 Registry/Bundle 并生成新版本；不得在 UE 中手工拖动关键帧后仍沿用原动作 ID。许可或未知 CC 弹窗交由用户处理，不能以空动画或 T-pose 代替失败资产。
