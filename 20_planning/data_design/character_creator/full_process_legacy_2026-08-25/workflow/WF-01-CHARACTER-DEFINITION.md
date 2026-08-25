# WF-01 角色定义与 Manifest 编译

> 文档角色：`workflow_runbook`
> 状态：`validated_pilot`
> 适用阶段：`WF-01`
> 权威范围：角色请求、确定性选择和生产 Manifest 编译
> 上级入口：[`README.md`](./README.md)
> 上游：[`WF-00-SESSION-PREFLIGHT.md`](./WF-00-SESSION-PREFLIGHT.md)
> 下游：[`WF-02-CC-ASSEMBLY.md`](./WF-02-CC-ASSEMBLY.md)
> 最近核验：2026-08-06

## 1. 目的与使用时机

在 CC 装配前，把 BodyFit、面部身份、年龄和外观选择固化为可复现的 `request.json` 与编译后 `manifest.json`。本阶段决定“要创建谁”，不修改 CC 场景。

## 2. 当前范围与非目标

当前支持审核池内的成人 BodyFit、Face V3 和已登记面部外观。服装 Look、三发型正式导出、儿童体型和 Headshot 扩展尚未纳入通用生产 Manifest。

## 3. 进入条件

- `GATE-00 SESSION_READY` 通过。
- 使用新 `run_id`；不得覆盖旧证据。
- 只引用注册表 ID，不把本地资产绝对路径写入角色请求。

## 4. 输入与输出

输入为角色 ID、BodyFit ID、可选 Face recipe ID、随机种子和可选 reviewed appearance recipe。输出为暂存目录中的请求与确定性 Manifest；两者在完成后复制到证据目录。

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

## 5. 执行环境

本阶段使用 PowerShell 中的 `SYSTEM_PYTHON`，不得导入 `RLPy`。

```powershell
$runId = Get-Date -Format 'yyyyMMdd_HHmmss'
$runRoot = "$outputRoot\character_creator_bridge\artifacts\character_build_$runId"
$staging = "$ccScriptRoot\runtime_staging\$runId"
$request = "$staging\request.json"
$manifest = "$staging\manifest.json"
$ccOut = "$runRoot\cc"
$reviewOut = "$runRoot\review"
New-Item -ItemType Directory -Path $runRoot,$staging | Out-Null
```

## 6. 执行步骤

1. 建立请求；省略 `face_recipe_id` 时，由 `seed + character_id` 确定性选择。
2. 需要固定 Look 时加入 `appearance_recipe_id`、匹配的 `validation_preset_id` 和 `require_complete=true`。
3. 编译 Manifest：

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

4. 不手工修补编译后的资产路径或状态；编译失败应修请求或注册表。

## 7. 退出门禁

执行 [`GATE-01 MANIFEST_READY`](../validation/README.md) 中的 `VAL-MANIFEST-01`。要求 `success=true`、请求数等于角色数、全部 request result 为 `compiled`，且无性别、资产审核或组合拒绝。

## 8. 失败与恢复

编译失败不进入 CC。保留请求和编译输出，用同一角色意图、新版本 Manifest 修复；不得把 rejected combination 改写成成功。路径或 schema 问题按 `REC-MANIFEST-01`。

## 9. 技术依据与下一阶段

BodyFit、Face 和外观规则分别见 [`BODYFIT_PIPELINE.md`](../cc_details/BODYFIT_PIPELINE.md)、[`FACE_IDENTITY_AND_AGE.md`](../cc_details/FACE_IDENTITY_AND_AGE.md) 和 [`APPEARANCE_PIPELINE.md`](../cc_details/APPEARANCE_PIPELINE.md)。通过后进入 [`WF-02`](./WF-02-CC-ASSEMBLY.md)。

