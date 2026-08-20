# CC 完整角色装配 Runbook

> 文档角色：`operational_runbook`
> 状态：`validated_pilot`
> 上级入口：[`../CHARACTER_FACTORY_MASTER_SPEC.md`](../CHARACTER_FACTORY_MASTER_SPEC.md)
> 最近核验：2026-08-06

## 1. 能力边界

当前系统可以从 reviewed 请求编译确定性 manifest，并通过 Bridge 的 `validate-bodies` 命令让 CC 执行完整装配、验证和截图。命令名来自早期 BodyFit 验证，实际执行器已经支持完整角色，但尚未有语义明确的 `assemble-character` API。

普通编译器当前不提供 `save_character_projects` 参数；已验证的十体型 showcase manifest 包含该字段。任意新角色的自动保存入口仍需后续专门化，禁止在文档中假装已经一键完成。

## 2. 前置条件

```powershell
$LANCE_ROOT = 'D:\UE\Lance_Work'
$scriptRoot = "$LANCE_ROOT\00_engine\scripts\character_creator"
$bridgeRoot = "$LANCE_ROOT\00_engine\character_creator_bridge"
$client = "$bridgeRoot\cc_bridge_client.py"
```

- CC5 必须由用户在离线许可证条件下启动。
- Bridge 插件已经安装并随 CC 启动。
- 当前 CC 场景允许被替换；无关工作已保存。
- CC private memory 低于 24 GB。
- 所有输入位于 Bridge allowlist 内。
- 输出目录使用新 run ID，不能覆盖旧证据。

## 3. ASSEMBLE-01：健康检查

- 成熟度：`production`
- 模式：`BRIDGE_CLI`

```powershell
python $client health
python $client ping
python $client scene-summary
```

通过条件：heartbeat 新鲜、`busy=false`，ping 和 RLPy scene summary 成功。失败时不得继续提交装配。

## 4. ASSEMBLE-02：建立运行目录和请求

- 成熟度：`production`
- 模式：`SYSTEM_PYTHON` 生成输入；请求本身可由 Agent 使用结构化编辑创建。

```powershell
$runId = Get-Date -Format 'yyyyMMdd_HHmmss'
$runRoot = "$LANCE_ROOT\00_engine\outputs\character_creator_bridge\artifacts\character_build_$runId"
$staging = "$scriptRoot\runtime_staging\$runId"
$request = "$staging\request.json"
$manifest = "$staging\manifest.json"
$ccOut = "$runRoot\cc"
$reviewOut = "$runRoot\review"
New-Item -ItemType Directory -Path $runRoot,$staging | Out-Null
```

Bridge 当前只允许读取 `bridge_config.json` 中的输入根；`SCRIPT_ROOT` 在 allowlist 内，artifacts 只允许作为输出。因此请求和 manifest 先放入 `runtime_staging`，完成后再复制到证据目录。该暂存目录不得提交 Git。

最小请求：

```json
{
  "schema_version": 1,
  "manifest_id": "cc_character_request_<run-id>",
  "seed": 20260806,
  "characters": [
    {
      "character_id": "CC_<unique-id>",
      "bodyfit_id": "M02_Average",
      "face_recipe_id": "MFACEV3_0006"
    }
  ]
}
```

`face_recipe_id` 可省略，由 `seed + character_id` 确定性选择。需要固定已验证 Look 时添加：

```json
"appearance": {
  "appearance_recipe_id": "<reviewed-look-id>",
  "validation_preset_id": "<matching-reviewed-preset-id>",
  "require_complete": true
}
```

禁止直接填写本地资产路径；请求只引用已登记 ID。

## 5. ASSEMBLE-03：编译 manifest

- 成熟度：`production`
- 模式：`SYSTEM_PYTHON`

```powershell
python "$scriptRoot\cc_compile_character_manifest.py" `
  --requests $request `
  --body-library "$scriptRoot\cc_body_preset_library_v2.json" `
  --face-library "$scriptRoot\cc_face_recipes_v3_200.json" `
  --compatibility "$scriptRoot\cc_appearance_compatibility_v1.json" `
  --catalog "$scriptRoot\cc_appearance_asset_catalog_v1.json" `
  --facial-registry "$scriptRoot\cc_facial_production_registry_v1.json" `
  --bodyfit-proportion-decisions "$scriptRoot\cc_head_bodyfit_scale_decisions_v1.json" `
  --output $manifest
```

编译后必须检查：

```powershell
$compiled = Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json
$compiled.success
$compiled.status
$compiled.requested_character_count
$compiled.character_count
$compiled.request_results | Select-Object character_id,status
```

通过条件：`success=true`，请求数等于角色数，所有 request result 为 `compiled`，没有 rejected combination、未验证资产或性别不匹配。

## 6. ASSEMBLE-04：提交 CC 执行

- 成熟度：`validated_pilot`
- 模式：`BRIDGE_CLI`
- 破坏性：替换当前 CC 场景。

```powershell
python $client validate-bodies `
  --library-file $manifest `
  --output-dir $ccOut `
  --confirm-scene-replace `
  --auto-dismiss-undo-warning
```

单角色 manifest 不需要 `--preset-id`。多角色 manifest 可用 `--preset-id <compiled-preset-id>` 逐条运行，降低内存和弹窗风险。

Undo 守卫只会处理已知精确警告。Replace/Material、角色预设或其他弹窗没有匹配策略时作业必须停止等待用户。

## 7. ASSEMBLE-05：执行器内部顺序

`cc_validate_body_reconstruction.py` 在 CC/RLPy 内执行：

1. 加载 BodyFit `.ccProject` 并核对哈希。
2. 应用主 Head Preset、支撑对象和 Facial Profile。
3. 写入配方局部 Morph。
4. 写入 Head Scale/Neck Height。
5. 应用 skin、age、dynamic wrinkle。
6. 应用 teeth、eyebrows、eyelashes 和 eyes material only。
7. 应用 beard、hair 和共享色素。
8. 应用面部材质质量档案并回读。
9. 执行结构、静态和动态门禁。
10. 写出每角色 `result.json`、截图和总 `validation_result.json`。

不得在系统 Python 中直接运行 `cc_validate_body_reconstruction.py`；它导入 `RLPy`，应由 Bridge 插件加载。

## 8. ASSEMBLE-06：结果汇总

- 模式：`SYSTEM_PYTHON`

```powershell
$summary = "$runRoot\summary.json"
python "$scriptRoot\cc_summarize_character_integration_v1.py" `
  --artifact-root $ccOut `
  --batch $manifest `
  --output $summary

python "$scriptRoot\cc_make_character_integration_contact_sheets_v1.py" `
  --summary $summary `
  --output-dir $reviewOut

Copy-Item -LiteralPath $request -Destination "$runRoot\request.json"
Copy-Item -LiteralPath $manifest -Destination "$runRoot\manifest.json"
```

通过条件：

- 总结果 `success=true`、失败数为 0。
- Body/Junction、面部配方、Facial Profile 和眼球完整性门禁通过。
- 必需 15 个动态姿态和静态视图完整。
- 中性恢复和图像活性门禁通过。
- 用户逐图审核并给出明确接受/拒绝。

确认两个输入副本与 staging 文件哈希一致后，才允许清理该 run 的 staging 目录。Bridge 输入 allowlist 和长期 staging 位置应在新增完整角色命令时重新设计。

## 9. 保存 `.ccProject`

当前已验证的十体型 showcase manifest：

```text
cc_character_showcase_10_20260803_v1.json
save_character_projects = true
```

可以逐个提交其中的 `CCSHOW_*` preset，从而保存一个规范化项目。普通 `cc_compile_character_manifest.py` 输出不自动打开该开关；任意角色保存专用接口仍为 Roadmap 中的 Bridge/编译器改进项。

禁止未审查地手工给生产 manifest 增加保存字段。临时人工保存可以验证视觉结果，但状态只能记为 `manual_verified`。

## 10. 停止和恢复

- `health` 失败：按 [`../bridge_details/BRIDGE_OPERATIONS.md` 第 8 节](../bridge_details/BRIDGE_OPERATIONS.md#8-恢复)恢复，不重复提交同一 job ID。
- CC private memory 达到 24 GB：停止批次，保留已完成结果，由用户决定离线重启。
- 未知弹窗：不要自动点击，保存截图和 job ID。
- 单项失败：使用同一 manifest、新 job ID 和新输出目录只重跑失败 preset。
- 视觉拒绝：写入 review/compatibility，不把自动成功改成生产通过。

完整恢复树见 [`../validation/VALIDATION_AND_RECOVERY.md`](../validation/VALIDATION_AND_RECOVERY.md)。
