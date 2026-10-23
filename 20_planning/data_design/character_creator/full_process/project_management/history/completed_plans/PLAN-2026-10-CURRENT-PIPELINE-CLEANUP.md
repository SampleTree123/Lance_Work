# 当前角色流程保留与过期产物清理

> 文档 ID：`PLAN-2026-10-CURRENT-PIPELINE-CLEANUP`
> 文档类型：`plan`
> 生命周期：`completed`
> 计划状态：`completed`
> 影响阶段：`WF-50/WF-60/WF-80`
> 最近核验：2026-10-11

## 目标与授权

用户授权同步已接受的相机成果，并清理当前流程不再使用的结果、关卡和资产。以当前完整角色、模块化服装/发型/鞋/发色、四类面部表演、身体动作及已接受相机矩阵的实际依赖闭包决定保留范围；不凭日期或文件夹名称删除。面部皮肤细节优化由另会话负责，本任务不修改皮肤或抢占其资产。

## 需求与验收

| 需求 ID | 目标 | 影响 Workflow | 验收条件 | 当前落实状态 | 证据与缺口 |
| --- | --- | --- | --- | --- | --- |
| `PLAN-2026-10-CURRENT-PIPELINE-CLEANUP/R01` | 同步相机人工接受 | WF-60 | 独立反馈绑定最终147清单；旧pending不倒写 | completed | user_camera_acceptance_v1.json |
| `PLAN-2026-10-CURRENT-PIPELINE-CLEANUP/R02` | 明确保留闭包和删除清单 | WF-50/WF-60 | 配置/代码/UE引用核查，逐路径记录原因及替代物，不能确认者保留 | completed | raw_render_candidate_files.json、UE逐包依赖闭包及保留清单已核对 |
| `PLAN-2026-10-CURRENT-PIPELINE-CLEANUP/R03` | 删除确认过期的产物和资产 | WF-50/WF-60/WF-80 | 已审查清单逐项执行并记录结果与回收空间；源资产和失败轻量证据不丢失 | completed | raw_cleanup_execution_receipt.json、ue_cleanup_offline_execution.json、cleanup_summary.json记录实际删除 |
| `PLAN-2026-10-CURRENT-PIPELINE-CLEANUP/R04` | 验证现用流程及文档收口 | WF-50/WF-60/WF-80 | 当前入口/资产依赖保持可用，更新Inventory及独立文档审计，无证据则明确边界 | completed | retained_files_verification.json、ue_post_cleanup_verification.json、147视频/ZIP/http校验及1101回归通过；最终文档审计另列 |

## 实施与证据

Run Root：`%OUTPUT_ROOT%/cleanup_current_pipeline_20261011_v1/`。所有者为 [输出盘点与保留](../../../technical/output/INVENTORY_AND_RETENTION.md)，沿用OUT-GLOBAL-OUTPUT-INVENTORY；审计VAL-DOC-01。共享UE由root串行操作。不可替代源文件、有效机器配置、已接受媒体和再生成依赖保留；旧严格pixel-exact失败不因清理变成通过。

## 最终交付（2026-10-11）

删除80375原始PNG、1417旧UE包及可重建测试文件，总计45,018,961,259字节；9479现用资产和241成品MP4哈希保持。当前147审查视频、独立分享ZIP和HTTP入口验证通过；UE重启扫描19396资产，已删目标无磁盘/registry残留、保留资产无指向已删目标的悬空依赖、dirty为空。1101回归通过。原始PNG已退休，重新编码前必须重新渲染；旧退役关卡不再可重放，旧prepared回执仅为历史证据。当前147场景、七组源场景及cam05/31/34严格失败诊断保留。本任务结项，不自动启动面部或生产任务。

## 后续范围

本次未纳入面部细节修复、正式生产或严格像素确定性修复；后续由获授权的会话分别处理，当前证据不扩展为这些范围已通过。

最终文档证据：`documentation_final_v2.json`记录16个独立子系统及跨层均通过，0错误0警告；Catalog724脚本与Inventory183作用域已重建。
