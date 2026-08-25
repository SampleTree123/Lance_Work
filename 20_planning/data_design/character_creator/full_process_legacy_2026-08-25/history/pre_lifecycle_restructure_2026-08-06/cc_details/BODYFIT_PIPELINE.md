# CC BodyFit 技术流程

> 文档角色：`technical_spec_and_runbook`
> 状态：`production`
> 上级入口：[`../CHARACTER_FACTORY_MASTER_SPEC.md`](../CHARACTER_FACTORY_MASTER_SPEC.md)
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

### BF-01：Bridge 前置检查

- 成熟度：`production`
- 执行模式：`BRIDGE_CLI`
- 破坏性：后续验证会替换当前 CC 场景；先保存无关工作。

```powershell
$LANCE_ROOT = 'D:\UE\Lance_Work'
$client = "$LANCE_ROOT\00_engine\character_creator_bridge\cc_bridge_client.py"
python $client health
python $client ping
python $client scene-summary
```

通过条件：heartbeat 新鲜、`busy=false`、`ping` 成功，且 `scene-summary` 能通过 `RLPy` 返回。

### BF-02：验证一个 BodyFit

```powershell
$runId = Get-Date -Format 'yyyyMMdd_HHmmss'
$library = "$LANCE_ROOT\00_engine\scripts\character_creator\cc_body_preset_library_v2.json"
$out = "$LANCE_ROOT\00_engine\outputs\character_creator_bridge\artifacts\bodyfit_validation_$runId"
python $client validate-bodies `
  --library-file $library `
  --preset-id M02_Average `
  --output-dir $out `
  --confirm-scene-replace `
  --auto-dismiss-undo-warning
```

把 `M02_Average` 替换为任一登记 ID。输出目录必须不存在或为空。

### BF-03：验证全部十体型

省略 `--preset-id`，其余参数不变。长批次前确认 CC private memory 低于停止阈值，并在每个结果完成后观察内存。

### BF-04：通过条件

检查输出根目录的 `validation_result.json`：

```text
requested_count = 选择数量
failure_count = 0
success = true
```

每个 preset 还必须满足：

- 源项目 SHA-256 和大小匹配。
- Body/Junction 指纹匹配。
- `expected_eyeball_move_weight=0.0`。
- Head Scale/Neck Height 与决策文件一致。
- 无未知阻塞弹窗。
- 视觉比例没有明显异常。

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
9. 用 BF-03 重跑完整十体型。
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

失败恢复见 [`../validation/VALIDATION_AND_RECOVERY.md`](../validation/VALIDATION_AND_RECOVERY.md)。

