# WF-08 场景、相机与 Level Sequence

> 文档角色：`workflow_runbook`
> 状态：`planned`
> 适用阶段：`WF-08`
> 权威范围：场景、角色、相机和序列装配的阶段契约；当前第一批受限范围
> 上级入口：[`README.md`](./README.md)
> 上游：[`WF-07-ANIMATION-AND-PROPS.md`](./WF-07-ANIMATION-AND-PROPS.md)
> 下游：[`WF-09-RENDER-DATASET-PACKAGE.md`](./WF-09-RENDER-DATASET-PACKAGE.md)
> 最近核验：2026-08-19

## 1. 目的与使用时机

在角色表演通过后，将其放入审核场景，确定地面接触、相机、灯光和 Level Sequence。本阶段是角色工厂到渲染数据管线的交接点。

## 2. 当前范围与非目标

本阶段尚未实现。第一批只承诺 1 个场景、1 个安全角色锚点、固定灯光、1 个中近景、1 个全身景和确定性 Sequence；不做道具、移动相机、场景替换、天气或灯光编辑。冻结范围见 [第一批数据 Sprint](../planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md)。

## 3. 进入条件

- 本轮使用的 16 个 FullReference Look、6 条身体动作和 3 条表情通过对应的受限 `GATE-07`。
- 角色 Blueprint、表演配置、服装/毛发状态和道具依赖均可追溯。
- 目标场景是 `/Game/DataMake` 下的项目自有入口，不直接改写 Vendor 地图。

## 4. 输入与输出

第一批输入：node config、16 个 Look、6 条动作、3 条表情、场景 ID、锚点、两台相机、24 fps 和 2–3 秒时长。计划输出：版本化 DataMake 关卡入口、Sequence 模板、两台静态相机、角色变换、固定灯光配置、碰撞/遮挡报告和场景 sidecar。

## 5. 执行环境

计划使用 UE 5.8、DataMake 资产入口、Sequencer 和后续确定的 UE 自动化通道。具体使用 MCP、Remote Execution 或编辑器工具前必须单独验证，不在本规划页预设实现。

## 6. 执行步骤

第一批计划顺序为：选择 DataMake 场景入口 → 固定安全锚点 → 放置代表男女 Look → 地面/碰撞检查 → 固定两个镜头和焦距 → 生成确定性 Sequence 模板 → 全时段可见性/穿模检查 → 固化 scene/camera/anchor ID。开始实现时必须把每一步替换为真实工具和可复现参数。

## 7. 退出门禁

计划门禁为 [`GATE-08 SCENE_READY`](../validation/README.md)。它至少需要未来的 `VAL-SCENE-01` 与 `VIS-SCENE-01`，覆盖地面接触、角色/场景/道具碰撞、全时段相机可见性、裁切、焦点和序列帧范围。

## 8. 失败与恢复

当前无可执行恢复步骤。未来实现必须支持保留角色配置、重新采样位置或相机、创建新 Sequence 版本，并禁止在来源 Vendor 地图上原地修补。

## 9. 技术依据与下一阶段

UE 资产边界见 [`ADR-0007`](../decisions/ADR-0007-UE-VENDOR-DATAMAKE-MODULARITY.md)，当前任务见 [第一批数据 Sprint](../planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md)。本阶段实现并通过后进入 [`WF-09`](./WF-09-RENDER-DATASET-PACKAGE.md)。
