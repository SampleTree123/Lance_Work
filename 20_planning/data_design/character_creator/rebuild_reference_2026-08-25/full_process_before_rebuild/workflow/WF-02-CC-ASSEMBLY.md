# WF-02 Character Creator 角色装配

> 文档角色：`workflow_runbook`
> 状态：`validated_pilot`
> 适用阶段：`WF-02`
> 权威范围：把已编译 Manifest 应用到 CC 场景的生产执行顺序
> 上级入口：[`README.md`](./README.md)
> 上游：[`WF-01-CHARACTER-DEFINITION.md`](./WF-01-CHARACTER-DEFINITION.md)
> 下游：[`WF-03-CC-ACCEPTANCE.md`](./WF-03-CC-ACCEPTANCE.md)
> 最近核验：2026-08-06

## 1. 目的与使用时机

使用通过 `GATE-01` 的 Manifest，在 CC/RLPy 中加载 BodyFit 并按唯一顺序组装面部、年龄和外观。本阶段改变当前 CC 场景。

## 2. 当前范围与非目标

当前真实入口仍名为 `validate-bodies`，但执行器支持完整兼容 Manifest。尚无语义明确的 `assemble-character` API，也没有任意角色通用自动保存开关。

## 3. 进入条件

- `GATE-01 MANIFEST_READY` 通过。
- CC 场景允许被替换，无未知弹窗。
- Bridge `busy=false`，private memory 低于 24 GB。
- `$ccOut` 是新的 artifacts 子目录。

## 4. 输入与输出

输入是已编译 `manifest.json`。输出是每角色 `result.json`、结构/眼球/指纹报告、静态和动态截图，以及批次 `validation_result.json`。

## 5. 执行环境

外层使用 `BRIDGE_CLI`，内部由 CC 插件在 UI 线程加载 `cc_validate_body_reconstruction.py`。禁止在系统 Python 中直接运行该 RLPy 文件。

## 6. 执行步骤

1. 单角色直接提交；多角色按 preset 分块，减少内存和弹窗风险。
2. 执行：

```powershell
python $bridgeClient validate-bodies `
  --library-file $manifest `
  --output-dir $ccOut `
  --confirm-scene-replace `
  --auto-dismiss-undo-warning
```

3. 执行器内部固定顺序为：BodyFit 与哈希 → Head/Facial Profile → 安全局部 Morph → Head Scale/Neck Height → skin/age/wrinkle → teeth/brows/lashes/eyes material → beard/hair/pigment → 材质质量档案 → 结构和动作检查。
4. `--auto-dismiss-undo-warning` 只允许精确处理已知 Undo 警告；其他弹窗停止等待人工。
5. 多角色失败时只用新 job ID 和新输出目录重跑失败 preset，不重复提交相同 job ID。

## 7. 退出门禁

执行 [`GATE-02 ASSEMBLY_COMPLETE`](../validation/README.md)。要求 Bridge 终态成功、`failure_count=0`、单项 `error=null`、Body/Junction 未漂移、Facial Profile 和眼球完整性检查无错误。本门禁只证明装配结构完整，不证明角色视觉可接受。

## 8. 失败与恢复

内存达到 24 GB、CC 关闭、未知弹窗或作业长时间 busy 时立即停止，保留 request/result/log/artifacts，按 `REC-CC-01`、`REC-BRIDGE-01` 或 `REC-DIALOG-01` 恢复。重启后从本阶段开头使用新 job ID 重跑。

## 9. 技术依据与下一阶段

Bridge 安全边界见 [`BRIDGE_OPERATIONS.md`](../bridge_details/BRIDGE_OPERATIONS.md)，组装域规则见 `cc_details/`。结构完成后进入 [`WF-03`](./WF-03-CC-ACCEPTANCE.md)，不得跳过人工视觉验收。

