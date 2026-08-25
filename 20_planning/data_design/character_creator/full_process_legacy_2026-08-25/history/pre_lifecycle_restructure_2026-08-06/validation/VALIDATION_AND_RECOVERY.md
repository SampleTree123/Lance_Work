# 角色工厂验证与恢复 Runbook

> 文档角色：`cross_system_runbook`
> 状态：`current`
> 上级入口：[`README.md`](./README.md)
> 最近核验：2026-08-06

## 1. 本文解决什么问题

本文同时回答四个问题：

1. 当前哪一项验证已经有可执行代码。
2. 应在什么环境运行哪一个外层入口。
3. 运行会产生什么报告，哪些字段决定自动通过。
4. 自动报告通过后，人工还必须检查什么，以及失败后如何恢复。

API 返回成功只证明调用完成，不证明角色视觉正确。每个阶段必须同时保留机器报告、输入配置、输出路径和人工视觉判定。失败运行不覆盖旧证据，也不从中间状态直接继续生产。

## 2. 环境、变量与执行边界

在 PowerShell 中定义当前本机路径：

```powershell
$LANCE_ROOT = 'D:\UE\Lance_Work'
$ccScriptRoot = "$LANCE_ROOT\00_engine\scripts\character_creator"
$bridgeRoot = "$LANCE_ROOT\00_engine\character_creator_bridge"
$bridgeClient = "$bridgeRoot\cc_bridge_client.py"
$ueScriptRoot = "$LANCE_ROOT\00_engine\scripts\unreal"
$outputRoot = "$LANCE_ROOT\00_engine\outputs"
$ueProject = 'datatry_02'
```

| 模式 | 外层调用位置 | 约束 |
| --- | --- | --- |
| `SYSTEM_PYTHON` | PowerShell 中的系统 Python | 不得导入 `RLPy` 或 `unreal` |
| `BRIDGE_CLI` | PowerShell 调用 `cc_bridge_client.py` | CC 必须由用户离线启动，Bridge heartbeat 新鲜 |
| `CC_RLPY` | CC5 内部 | 当前由 Bridge 插件加载执行器，不直接用系统 Python 运行 |
| `UE_REMOTE` | 系统 Python 调用 `ue_remote_exec.py` 或专用 wrapper | UE 已打开 `datatry_02`，Python Remote Execution 能发现唯一节点 |
| `UE_UI` | Unreal 编辑器 | 用于导入选项、视觉审核、保存和恢复确认 |

`UE_REMOTE` 与 `UE_MCP` 是两条独立通道。下面列出的 UE wrapper 使用 UE 自带 Python Remote Execution；MCP 在线不是它们的直接前置条件。

## 3. 统一运行前门禁

### 3.1 Character Creator

- CC 由用户在离线条件下启动；Agent 不擅自重启。
- 当前场景没有需要保留的未保存编辑，或已明确保存。
- Bridge 插件已加载并持续更新 heartbeat。
- 没有 `Replace/Material Only`、Undo manager 或 Save 等模态弹窗。
- CC private memory 低于 24 GB；接近阈值时先结束批次并人工重启。
- 请求、manifest 和输出目录使用新的 `run_id`。

### 3.2 Unreal Engine

- 当前工程是 `D:\UE\projects\datatry_02`。
- 当前打开关卡、PIE 状态和待保存脏包明确；运行 wrapper 前不处于 PIE/Simulate。
- Reallusion Auto Setup 2.03 与 `/Game/CC_Shaders` 可用。
- 目标 Skeleton、Blueprint 和动画资产路径存在。
- 使用 `UE_REMOTE` 时，UE Project Settings 中 Python Remote Execution 已启用且当前节点可被发现。
- 使用 `UE_MCP` 做编辑器自动化时另行实时确认 MCP 在线，不能用旧会话状态代替。

## 4. 当前可执行验证

### VAL-CODE-01 System Python unit tests

- 成熟度：`production` 级代码回归入口。
- 模式：`SYSTEM_PYTHON`。
- 破坏性：无；不启动 CC 或 UE。

```powershell
python -m unittest discover `
  -s "$ccScriptRoot\tests" `
  -p 'test_*.py'

python -m unittest discover `
  -s "$bridgeRoot\tests" `
  -p 'test_*.py'
```

通过条件：两个命令退出码均为 0，没有 `FAILED` 或 `ERROR`。这些测试只覆盖纯 Python 编译、汇总和 Bridge 客户端逻辑，不能证明 CC/RLPy 或 UE 视觉正确。

### VAL-BRIDGE-01 Bridge health and RLPy access

- 成熟度：`validated_pilot`。
- 模式：`BRIDGE_CLI`。
- 代码：[`cc_bridge_client.py`](../../../../../00_engine/character_creator_bridge/cc_bridge_client.py)。

```powershell
python $bridgeClient health
python $bridgeClient ping
python $bridgeClient scene-summary
```

通过条件：

- heartbeat 可解析，协议版本匹配，状态为 `idle` 或可解释的 `busy`。
- heartbeat `updated_at` 未超过 5 秒 lease。
- `ping` 产生成功终态结果。
- `scene-summary` 通过 RLPy 返回当前场景和 avatar 信息。

只看到 CC UI、插件文件或 `/mcp` 列表不算通过。队列、结果和恢复细节见 [`BRIDGE_OPERATIONS.md`](../bridge_details/BRIDGE_OPERATIONS.md)。

### VAL-CC-01 BodyFit reconstruction smoke

- 成熟度：`validated_pilot`。
- 模式：外层 `BRIDGE_CLI`，内部 `CC_RLPY`。
- 外层代码：[`cc_bridge_client.py`](../../../../../00_engine/character_creator_bridge/cc_bridge_client.py)。
- 内部代码：[`cc_validate_body_reconstruction.py`](../../../../../00_engine/scripts/character_creator/cc_validate_body_reconstruction.py)。
- 破坏性：会替换当前 CC 场景。

下面示例只验证 `M02_Average`，每次修改 `jobId`：

```powershell
$jobId = 'bodyfit_smoke_20260806_001'
$library = "$ccScriptRoot\cc_body_preset_library_v2.json"
$ccOut = "$outputRoot\character_creator_bridge\artifacts\$jobId"

python $bridgeClient validate-bodies `
  --library-file $library `
  --preset-id M02_Average `
  --output-dir $ccOut `
  --confirm-scene-replace `
  --auto-dismiss-undo-warning `
  --job-id $jobId `
  --no-wait

python $bridgeClient wait $jobId --timeout 3600
python $bridgeClient result $jobId
```

预期输出：

```text
<ccOut>\validation_result.json
<ccOut>\M02_Average\result.json
<ccOut>\M02_Average\source_vectors.json
<ccOut>\M02_Average\reconstructed_vectors.json
<ccOut>\M02_Average\morph_delta.json
<ccOut>\M02_Average\eye_integrity.json
<ccOut>\M02_Average\source_preview.png
<ccOut>\M02_Average\reconstructed_preview.png
```

自动通过条件：批次 `failure_count=0`，单项 `error=null`，源项目路径和 `expected_fingerprint` 与 BodyFit library 一致；Body/Junction 未发生未登记漂移。截图仍需人工比较头身比、脖子、肩胸腹和眼球位置。

禁止直接运行 `python cc_validate_body_reconstruction.py`：该文件导入 `RLPy`，必须由 Bridge worker 在 CC 内加载。

### VAL-CC-02 Complete character validation and contact sheets

- 成熟度：`validated_pilot`。
- 模式：manifest 编译与汇总为 `SYSTEM_PYTHON`；装配为 `BRIDGE_CLI + CC_RLPY`。
- 详细字段：[`CHARACTER_ASSEMBLY_RUNBOOK.md`](../cc_details/CHARACTER_ASSEMBLY_RUNBOOK.md)。
- 破坏性：会替换当前 CC 场景。

建立唯一运行目录并准备 `request.json`：

```powershell
$runId = Get-Date -Format 'yyyyMMdd_HHmmss'
$staging = "$ccScriptRoot\runtime_staging\$runId"
$runRoot = "$outputRoot\character_creator_bridge\artifacts\character_build_$runId"
$request = "$staging\request.json"
$manifest = "$staging\manifest.json"
$ccOut = "$runRoot\cc"
$summary = "$runRoot\summary.json"
$reviewOut = "$runRoot\review"
New-Item -ItemType Directory -Path $staging,$runRoot | Out-Null
```

请求至少包含一个 `character_id`、`bodyfit_id` 和可选 `face_recipe_id`。完整请求 schema 见装配 Runbook。编译：

```powershell
python "$ccScriptRoot\cc_compile_character_manifest.py" `
  --requests $request `
  --body-library "$ccScriptRoot\cc_body_preset_library_v2.json" `
  --face-library "$ccScriptRoot\cc_face_recipes_v3_200.json" `
  --compatibility "$ccScriptRoot\cc_appearance_compatibility_v1.json" `
  --catalog "$ccScriptRoot\cc_appearance_asset_catalog_v1.json" `
  --facial-registry "$ccScriptRoot\cc_facial_production_registry_v1.json" `
  --bodyfit-proportion-decisions "$ccScriptRoot\cc_head_bodyfit_scale_decisions_v1.json" `
  --output $manifest
```

提交 CC 并生成审核材料：

```powershell
python $bridgeClient validate-bodies `
  --library-file $manifest `
  --output-dir $ccOut `
  --confirm-scene-replace `
  --auto-dismiss-undo-warning

python "$ccScriptRoot\cc_summarize_character_integration_v1.py" `
  --artifact-root $ccOut `
  --batch $manifest `
  --output $summary

python "$ccScriptRoot\cc_make_character_integration_contact_sheets_v1.py" `
  --summary $summary `
  --output-dir $reviewOut
```

自动通过条件：manifest `success=true`；请求数等于编译角色数；执行 `failure_count=0`；Body/Junction 隔离、Facial Profile、眼球完整性、中性恢复、必需静态视角和动态姿态均无缺项。人工必须逐图检查第 6 节；自动成功不能直接晋级生产。

### VAL-XFER-01 M02 full-reference import

- 成熟度：`validated_pilot`。
- 模式：`CC_UI + UE_UI`。
- 当前自动代码：无通用导入验收器。
- 操作入口：[`EXPORT_IMPORT_RUNBOOK.md`](../cc_ue_transfer/EXPORT_IMPORT_RUNBOOK.md)。

当前已验证 bundle：

```text
D:\UE\exports\character_creator\pilot_m02_ue58_v001
```

必须从同一 bundle 导入 FBX、同名 JSON、`.fbm` 和 textures，并先生成完整参考角色。自动化缺口必须明确保留：UE Interchange 导入窗口、Auto Setup 结果和首次视觉验收目前仍需要人工完成。

### VAL-UE-01 M02 v002 face Morph broadcaster

- 成熟度：`validated_pilot`。
- 模式：`UE_REMOTE`。
- 外层代码：[`ue_remote_exec.py`](../../../../../00_engine/scripts/unreal/ue_remote_exec.py)。
- UE 内部代码：[`ue_validate_m02_face_morph_broadcaster.py`](../../../../../00_engine/scripts/unreal/ue_validate_m02_face_morph_broadcaster.py)。
- 前置：UE 已打开 `datatry_02`，不在 PIE，Remote Execution 可发现唯一节点。

```powershell
python "$ueScriptRoot\ue_remote_exec.py" `
  --project $ueProject `
  --script "$ueScriptRoot\ue_validate_m02_face_morph_broadcaster.py"
```

输出：

```text
$outputRoot\unreal_character_import\m02_face_morph_broadcaster_validation.json
```

自动通过条件：

```text
success = true
errors = []
blueprint = ...BP_DM_M02_ModularPilot_v002
total_skeletal_mesh_component_count = 20
face_component_count = 13
```

该脚本把三个测试 Morph 写入支持它们的面部组件，并确认非面部组件未收到权重。它不是完整模块结构回归。

旧 [`ue_validate_m02_modular_blueprint.py`](../../../../../00_engine/scripts/unreal/ue_validate_m02_modular_blueprint.py) 仍硬编码 `BP_DM_M02_ModularPilot_v001`。在它被参数化或升级前，禁止把它描述为 v002 的直接验证入口。

### VAL-UE-02 M02 v003 hybrid face matrix

- 成熟度：`validated_pilot`。
- 模式：外层 `SYSTEM_PYTHON`，内部 `UE_REMOTE` 和 PIE/Simulate。
- 外层唯一入口：[`run_m02_face_hybrid_pie_review_v003.py`](../../../../../00_engine/scripts/unreal/run_m02_face_hybrid_pie_review_v003.py)。
- 内部脚本：stage、PIE review、cleanup 由 wrapper 自动按顺序执行，不要分别手动运行。

```powershell
python "$ueScriptRoot\run_m02_face_hybrid_pie_review_v003.py"
```

wrapper 会：清除旧报告、布置四个临时 editor actor、启动 Simulate、执行 `2 body × 5 face state`、结束 PIE、清理 actor。无论成功或失败，运行后都要检查关卡脏包状态；不要自动保存 Main 关卡。

输出：

```text
$outputRoot\unreal_character_import\m02_face_hybrid_review_v003\pie_review.json
$outputRoot\unreal_character_import\m02_face_hybrid_review_v003\*.png
```

可选联系表：

```powershell
python "$ueScriptRoot\ue_make_m02_face_hybrid_review_sheet_v003.py"
```

自动通过条件：

```text
success = true
errors = []
matrix_dimensions.body = 2
matrix_dimensions.face_state = 5
case_count = 10
component_count_per_actor = 20
follower_count_per_actor = 19
followers_without_body_leader = []
```

另外检查每个 face state 的两种身体姿态保持不同，面部层未覆盖 `neck_01`、`neck_02` 和 `head`，曲线和支撑骨骼误差均在脚本容差内。

当前 wrapper 使用固定输出目录并覆盖同名 Pilot 报告/截图。需要保留旧证据时，必须在重跑前复制整个 `m02_face_hybrid_review_v003` 目录到带 run ID 的归档目录；参数化输出仍是技术债务。

### VAL-UE-03 M02 Elder Morph matrix

- 成熟度：`validated_pilot`。
- 模式：外层 `SYSTEM_PYTHON`，内部 `UE_REMOTE` 和 PIE/Simulate。
- 外层唯一入口：[`run_m02_elder_morph_pie_review.py`](../../../../../00_engine/scripts/unreal/run_m02_elder_morph_pie_review.py)。

```powershell
python "$ueScriptRoot\run_m02_elder_morph_pie_review.py"
```

输出：

```text
$outputRoot\unreal_character_import\m02_elder_morph_review_v001\request.json
$outputRoot\unreal_character_import\m02_elder_morph_review_v001\pie_review.json
$outputRoot\unreal_character_import\m02_elder_morph_review_v001\*.png
```

可选联系表：

```powershell
$elderReview = "$outputRoot\unreal_character_import\m02_elder_morph_review_v001"
python "$ueScriptRoot\ue_make_m02_elder_morph_review_sheet.py" `
  --review-dir $elderReview `
  --output "$elderReview\m02_elder_morph_pie_contact_sheet.png"
```

自动通过条件：

```text
success = true
errors = []
morph_name = Full_Face_Elder
actor_component_count = 20
case_count = 6
component_support_consistent = true
propagate_curves_to_followers = true
```

6 个案例必须包含 0、0.5、1 三档年龄，以及 older 状态的 Blink、Smile、Jaw Open。该 Pilot 只适用于 M02 同身份、同拓扑快照，不是任意角色通用年龄生成器。它同样使用固定输出目录，重跑前按需归档。

## 5. 当前没有可执行代码的验证

以下项目只有目标和未来落点，当前不能运行：

| 验证 | 执行模式 | 当前入口 | 计划文档 |
| --- | --- | --- | --- |
| 十体型 UE 导入回归 | `PLANNED` | 无 | `UE_TEN_BODYFIT_ACCEPTANCE.md` |
| 服装 × 动作穿模矩阵 | `PLANNED` | 无 | `OUTFIT_MOTION_ACCEPTANCE.md` |
| 三发型/胡须动态回归 | `PLANNED` | 无 | `HAIR_ACCEPTANCE.md` |
| 场景、角色和相机碰撞/遮挡 | `PLANNED` | 无 | `SCENE_CAMERA_ACCEPTANCE.md` |
| 视频、GT 和 sidecar 一致性 | `PLANNED` | 无 | `DATASET_ACCEPTANCE.md` |
| 批量性能、显存、内存和耗时 | `PLANNED` | 无 | `PERFORMANCE_ACCEPTANCE.md` |

不得用 M02 单样本结果替代这些目标规模验收。

## 6. 人工视觉与结构门禁

### 6.1 CC 结构与可追溯

- BodyFit 源路径、大小和 SHA-256 与注册表一致。
- Body/Junction Morph 指纹保持不变。
- Head Scale、Neck Height、face seed、recipe、skin 和各资产 ID 被记录。
- 装配顺序与 registry 一致。
- 材质质量档案回读 10 个参数，无缺失目标。

### 6.2 CC 静态视角

至少保存：

```text
full_body_front
head_shoulders_front
head_shoulders_three_quarter_left
head_shoulders_three_quarter_right
head_shoulders_profile_left
head_shoulders_profile_right
head_back
```

检查头身比、脖子、肩胸腹、肤色接缝、耳朵、发际线、眉睫、胡须、牙齿和服装。

### 6.3 CC 动态表情

至少覆盖：

- 双眼闭合和左右单眼闭合。
- 视线上、下、左、右。
- 眯眼、睁大、抬眉。
- 轻微微笑、满幅微笑、张嘴和下颌运动。
- 动作结束后恢复中性。

检查眼球不穿出眼睑、瞳孔露出区合理、睫毛跟随、牙齿/舌头不穿唇、胡须和眉毛不漂移。

### 6.4 Morph 隔离

正式身份只修改 manifest 中列出的 Morph。加载前后比较：

- Body/Junction 不被脸部流程污染。
- 未授权面部 Morph 不被清零或改写。
- 眼球对象、LookAt、眼骨和 Facial Profile 保持一套一致状态。
- 年龄变体只改变已登记年龄参数。

### 6.5 CC→UE 完整参考

- FBX、同名 JSON、`.fbm` 和纹理来自同一 bundle。
- UE 导入目标是新目录，不覆盖参考资产。
- Skeleton、bind pose、材质和 Morph targets 成功导入。
- Auto Setup 材质可解析，无整体灰材质或错误透明。
- Neutral、Blink、Smile、Jaw Open 和全身比例通过。
- 完整参考网格通过后才进行模块拆分。

### 6.6 UE 模块化和动画

- `component_count=20`，`follower_count=19`。
- `followers_without_body_leader=[]`。
- `Body.propagate_curves_to_followers=true`。
- Body selector 确实改变身体姿态。
- 面部层不覆盖 `neck_01`、`neck_02` 和 `head`。
- 眼球只由登记的 Rig Logic 曲线驱动。

## 7. 弹窗处理

### 7.1 已知弹窗

| 弹窗 | 当前策略 |
| --- | --- |
| `Replace / Material Only` | 眼球选 `Material Only`；牙齿、皮肤、睫毛、胡须、头发按登记策略选 `Replace` |
| `Failed to record undo/redo step` | 停止提交新动作；精确守卫或人工点击 OK；记录事件；连续出现时重启 CC |
| 保存覆盖确认 | 仅当输出路径与 manifest 完全一致时确认，否则取消 |
| UE 恢复包 | 审查包列表；只有确认属于未保存目标工作时恢复，否则跳过 |

### 7.2 未知弹窗

未知模态窗口一律停止。不要盲点默认按钮，也不要继续向 CC/UE 发送命令。保存截图、窗口标题、当前 run ID 和最后成功步骤后人工判断。

## 8. 恢复树

### 8.1 Bridge 无响应

1. 运行 `health`，检查 heartbeat、lease 和版本。
2. 若 heartbeat 过期，不重复提交同一请求。
3. 检查 CC 是否有模态弹窗或已关闭。
4. 若 CC 仍可操作，由用户关闭弹窗；重新检查健康。
5. 若需重启，先保存可恢复证据，再由用户离线重启 CC。
6. 使用新的 `run_id` 重跑完整角色，不复用半完成场景。

### 8.2 CC Undo 弹窗反复出现

1. 停止批次并关闭当前弹窗。
2. 不快速连续加载项目和资产。
3. 记录最近一次资产应用和内存。
4. 保存已完成结果；丢弃当前半完成角色。
5. 用户重启 CC 后从 manifest 开头重跑。

### 8.3 CC 内存过高或关闭

1. 将当前作业标记失败/中断，不推断保存成功。
2. 保留 Bridge request、result、日志和已生成截图。
3. 用户离线重启 CC。
4. 健康检查通过后使用新输出目录重跑。

### 8.4 UE 崩溃或恢复包

1. 重启 UE，记录崩溃前最后动作。
2. 恢复包只恢复明确属于本轮且未另存的包。
3. 打开后编译相关 Blueprint，检查脏包和引用。
4. 运行最小 smoke，不直接继续完整矩阵。
5. smoke 通过后再运行自动矩阵。

### 8.5 UE Remote Execution 或 MCP 离线

1. 先区分失败通道：`UE_REMOTE` 依赖 Python Remote Execution，`UE_MCP` 依赖 unreal-mcp 服务。
2. Remote wrapper 报 `project was not discovered` 时，确认 UE 工程名、Remote Execution 设置和唯一节点。
3. MCP 失败时确认 UE 编辑器、插件和本地服务实际监听，再刷新当前会话工具状态。
4. 任一通道未恢复时只能做文件级检查，不能宣称对应编辑器内验证完成。

## 9. 证据与命名

新 CC 验证必须创建唯一目录：

```text
%LANCE_ROOT%\00_engine\outputs\<subsystem>\<run_id>\
```

至少包含：

```text
request.json 或 manifest.json
result.json 或 pie_review.json
自动检查报告
截图或 contact sheet
错误日志（如有）
```

两个现有 UE Pilot wrapper 仍硬编码固定输出目录，这是已披露例外。保留旧结果时先复制目录，不能把新结果误认为新 run ID 下的证据。

稳定结论写入 [`../CURRENT_STATUS.md`](../CURRENT_STATUS.md)；完成事件追加到 [`../history/MILESTONE_LOG.md`](../history/MILESTONE_LOG.md)；改变架构规则时新增 ADR。原始证据不复制进文档目录。

## 10. 阶段晋级

只有满足以下全部条件才可把 `planned` 或 `validated_pilot` 晋级：

1. 可复现输入和版本已锁定。
2. 自动门禁通过。
3. 人工视觉审核通过。
4. 失败恢复已至少执行一次或有明确回滚路径。
5. 技术 Runbook、Current Status、Roadmap 和机器注册表保持一致。
6. 不存在未解释的弹窗、路径、版本或脚本目标差异。
