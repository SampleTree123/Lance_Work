# CC BodyFit 技术流程

> 文档角色：`technical_specification`
> 状态：`production`
> 适用阶段：`WF-01..WF-03`
> 权威范围：BodyFit 源项目、比例参数、重建不变量和资产池维护
> 上级入口：[`README.md`](./README.md)
> 上游：BodyFit 机器库和源 `.ccProject`
> 下游：[`WF-01`](../workflow/WF-01-CHARACTER-DEFINITION.md)、[`WF-02`](../workflow/WF-02-CC-ASSEMBLY.md)
> 最近核验：2026-08-06

## 1. 权威输入

```text
LANCE_ROOT = D:\UE\Lance_Work
SCRIPT_ROOT = %LANCE_ROOT%\00_engine\scripts\character_creator
```

| 文件 | 用途 |
| --- | --- |
| `cc_body_preset_library_v2.json` | 10 个 BodyFit 源项目、哈希、Body/Junction 指纹和加载模式 |
| `cc_head_bodyfit_scale_decisions_v1.json` | 固定 Head Scale 与 Neck Height |
| `cc_bodyfit_height_matrix_v2_20260803.json` | 当前测量请求 |
| `outputs/.../bodyfit_height_matrix_current_20260803_01/bodyfit_height_matrix.json` | 实际身高证据 |

`body_application_mode` 必须为 `source_project`。BodyFit 从 hash 锁定 `.ccProject` 加载；Morph 向量只做漂移检测，不从 Neutral Base 重建生产身体。

## 2. 当前十体型

| ID | 源项目 | 身高 cm | Head | Neck |
| --- | --- | ---: | ---: | ---: |
| `M01_Lean` | `M01_Lean.ccProject` | 173.42 | -10 | -20 |
| `M02_Average` | `M02_Average.ccProject` | 181.28 | 0 | 0 |
| `M03_Athletic` | `M03_Athletic.ccProject` | 187.74 | 10 | -20 |
| `M04_Heavy` | `M04_Heavy.ccProject` | 187.93 | 30 | 0 |
| `M05_Short_Average` | `M05_Short_Average.ccProject` | 159.89 | 0 | 0 |
| `F01_Lean` | `F01_Lean.ccProject` | 158.38 | -20 | -40 |
| `F02_Average` | `F02_Average.ccProject` | 172.71 | 10 | 0 |
| `F03_Athletic` | `F03_Athletic.ccProject` | 173.16 | 10 | 0 |
| `F04_Heavy` | `F04_Heavy.ccProject` | 174.85 | 30 | 0 |
| `F05_Short_Average` | `F05_Short_Average.ccProject` | 152.53 | -10 | 0 |

源项目目录：

```text
D:\CharacterCreator_sucai\Reallusion Custom\Project\CC Project\
```

Head Scale Morph 为 `cc embed morphs/embed_full_head9`；Neck Height Morph 为 `2019-08-30-20-14-55_neck height`。

## 3. 验证当前 BodyFit 库

BodyFit 回归不属于每个角色的日常步骤。修改源项目、哈希、Head Scale、Neck Height 或库构建逻辑后，先从 `WF-00` 通过 Bridge 门禁，再执行 [`VAL-CC-01`](../validation/VALIDATION_CATALOG.md)。

单 preset smoke 默认使用 `M02_Average`；全库回归使用同一验证定义覆盖十个登记 ID。机器通过要求源 SHA-256/大小、Body/Junction 指纹、眼球基准和比例决策一致；视觉比例仍按 [`VIS-CC-01`](../validation/VISUAL_ACCEPTANCE.md) 判定。测试命令只在 Validation Catalog 维护。

## 4. 修改或新增 BodyFit

这不是日常角色生成步骤。只有用户接受新体型后才能修改生产库。

1. 在 CC 中保存规范化、无服装动画干扰的 `.ccProject`。
2. 记录项目路径、字节数和 SHA-256。
3. 采集 Body、Junction 和面部隔离指纹。
4. 对 Head Scale 做候选矩阵，并由用户选择。
5. 必要时对 Neck Height 做单独候选矩阵。
6. 测量实际身高并保存证据。
7. 更新候选库和决策 JSON。
8. 用系统 Python构建生产库。
9. 用 `VAL-CC-01` 重跑完整十体型。
10. 更新 ADR、Current Status 和 Master。

构建入口：

```powershell
python "$LANCE_ROOT\00_engine\scripts\character_creator\cc_build_body_preset_library_v2.py" `
  --base-library <reviewed-base-library.json> `
  --short-library <reviewed-short-library.json> `
  --decisions <reviewed-head-neck-decisions.json> `
  --height-matrix <reviewed-height-matrix.json> `
  --output <candidate-output.json>
```

先写候选输出并比较 diff；禁止直接用脚本默认值覆盖当前生产文件。确认后才晋级为 `cc_body_preset_library_v2.json` 或新版本。

## 5. 强制不变量

- 身体性别必须与面部主原型、动态皱纹和资产池匹配。
- 加载主面部后 Body/Junction 不得变化。
- BodyFit 的头部载体不作为最终身份。
- M05/F05 不自动继承原 8 体型历史外观矩阵。
- 服装几何适配以 BodyFit 为单位，不能依靠 UE 中大幅身体 Morph 自动解决。

失败恢复见 [`RECOVERY_RUNBOOK.md`](../validation/RECOVERY_RUNBOOK.md)；准确回归入口见 [`VAL-CC-01`](../validation/VALIDATION_CATALOG.md)。
