# WF-03 CC 验收与规范项目保存

> 文档角色：`workflow_runbook`
> 状态：`validated_pilot`
> 适用阶段：`WF-03`
> 权威范围：CC 自动报告汇总、人工视觉验收、证据固化与 `.ccProject` 保存
> 上级入口：[`README.md`](./README.md)
> 上游：[`WF-02-CC-ASSEMBLY.md`](./WF-02-CC-ASSEMBLY.md)
> 下游：[`WF-04-CC-EXPORT-BUNDLE.md`](./WF-04-CC-EXPORT-BUNDLE.md)
> 最近核验：2026-08-06

## 1. 目的与使用时机

在装配完成后确认角色不仅“执行成功”，而且结构、眼球、牙齿、面部动作、毛发、皮肤和比例均可接受，并把输入、报告和视觉证据固化。

## 2. 当前范围与非目标

十体型 showcase 已验证自动保存；普通编译器尚无通用 `save_character_projects` 开关。任意新角色的人工保存只能记为 `manual_verified`，不能伪称全自动生产保存。

## 3. 进入条件

- `GATE-02 ASSEMBLY_COMPLETE` 通过。
- 当前 CC 场景仍是该 Manifest 对应角色。
- `$runRoot`、`$ccOut`、`$reviewOut` 和 `$manifest` 指向同一 run。

## 4. 输入与输出

输入为 CC artifacts、请求和 Manifest。输出为 `summary.json`、contact sheets、人工判定、输入副本，以及通过时的版本化规范 `.ccProject`。

## 5. 执行环境

报告汇总使用 `SYSTEM_PYTHON`；视觉审核和保存使用 `CC_UI`。

## 6. 执行步骤

1. 生成汇总和联系表：

```powershell
$summary = "$runRoot\summary.json"
python "$ccScriptRoot\cc_summarize_character_integration_v1.py" `
  --artifact-root $ccOut `
  --batch $manifest `
  --output $summary

python "$ccScriptRoot\cc_make_character_integration_contact_sheets_v1.py" `
  --summary $summary `
  --output-dir $reviewOut

Copy-Item -LiteralPath $request -Destination "$runRoot\request.json"
Copy-Item -LiteralPath $manifest -Destination "$runRoot\manifest.json"
```

2. 执行 `VIS-CC-01` 静态视角、`VIS-CC-02` 动态眼口动作和 `VIS-CC-03` 结构追溯检查。
3. 拒绝项写入 review/compatibility；不得把自动成功改写成人工通过。
4. 通过后清除临时测试姿势，恢复中性并保存新的版本化 `.ccProject`。
5. 核对 staging 与证据副本哈希一致后，才可清理该 run 的 staging。

## 7. 退出门禁

执行 [`GATE-03 CC_ACCEPTED`](../validation/README.md)：`VAL-CC-02` 报告通过，三项 `VIS-CC-*` 明确接受，规范项目保存状态和路径已记录。仅自动报告通过时 Gate 仍失败。

## 8. 失败与恢复

视觉拒绝时回到 `WF-01` 修配方或资产选择；运行中断但 Manifest 未变时回到 `WF-02` 新 run 重建。保存路径不明或覆盖确认不一致时取消保存，按 `REC-CC-01` 处理。

## 9. 技术依据与下一阶段

视觉检查定义见 [`VISUAL_ACCEPTANCE.md`](../validation/VISUAL_ACCEPTANCE.md)，追溯字段见 [`ASSET_TRACEABILITY.md`](../cc_ue_transfer/ASSET_TRACEABILITY.md)。只有 `GATE-03` 通过后才能进入 [`WF-04`](./WF-04-CC-EXPORT-BUNDLE.md)。
