# 固定头型发型人工适配审查

> 文档 ID：`PLAN-2026-10-FIXED-HEAD-HAIR-VISUAL-REVIEW`
> 文档类型：`plan`
> 生命周期：`completed`
> 计划状态：`completed`
> 影响阶段：`WF-50`
> 完成条件：交付可切换的 UE 双角色审查界面，记录用户人工结论，并完成本轮两个材质异常的定向原因核查与处理建议；机器加载不替代人工判断
> 最近核验：2026-10-05（R01 界面交付、R02 人工静态贴合、R03 两项原因核查及建议已交付；材质修复未实施）

## 目标与范围

复用已经完成转移的固定男女参考角色与保留的 40 款发型，建立独立 UE 审查关卡及控制面板。同一发型的男女适配版本同时展示，用户逐款观察位置、发丝材质和头皮接触情况。本次允许同时展示两性几何版本，不改变正式 `male/female/both` 使用许可。

不拍照、不建立图片图库，不重新导出/导入，不修改正式角色或发型资产；已有 UE 会话继续使用、不关闭或重启，不操作 CC。基础外观装配保持 queued，原双版本转换计划保留完整 History，不重开，不创建数据生产 Batch。

## 需求与落实

| 需求 ID | 要求 | 影响 Workflow | 状态 | 验收条件 | 证据入口 |
| --- | --- | --- | --- | --- | --- |
| `R01` | 交付独立关卡、逐款切换面板和双性同时加载入口 | `WF-50` | `completed` | 代表款式实际加载到对应固定参考角色；明确启动和使用方法，无自动拍照 | [Runtime 3.10](../../../technical/unreal/CHARACTER_RUNTIME.md#310-固定头型发型的双角色人工审查2026-10-05)；新 Run Root 的 `worker_smoke_check.json` / `cli_smoke_check.json` / `machine_handoff.json`，交付文档与回归见 `documentation_audit_final.json` / `regression_tests.json` |
| `R02` | 用户逐款审查并说明需要保留或调整的问题 | `WF-50` | `completed` | 用户已完成固定男女参考人物上的全部保留发型静态贴合审查，确认未见穿模；两个材质异常另行记录，不写整体材质通过 | [WF-50 状态](../../status/workflows/WF-50.md)；新 Run Root 的 `human_review_summary.json`（直接用户文字来源） |
| `R03` | 核查发辫偏深与男女 Body 接缝的原因，并给出定向处理建议 | `WF-50` | `completed` | 已用源 JSON/贴图、UE 材质与纹理属性及源 FBX 接缝数据确定缺陷和范围，提供最小代表 A/B 修复建议；本轮仅检查原因，未实施修复 | [Runtime 3.10](../../../technical/unreal/CHARACTER_RUNTIME.md#310-固定头型发型的双角色人工审查2026-10-05)；新 Run Root 的 `hair_braid_material_diagnosis.json`、`body_seam_diagnosis.json`、`ue_material_readback.json` |

## 交付文档验证

新审查 Run Root 的 `documentation_audit_final.json` 已实际全 16 独立检查与跨层检查通过，零错误、零警告；`regression_tests.json` 为完整要求回归 301 passed（80.36 秒）。这些为界面交付版本证据；本轮新人工结论与诊断文档的独立最终审计已通过，16 项独立检查与跨层全通过，零错误警告；本轮 `material_diagnosis_regression.json` 已记录完整要求回归 301 passed（33.50 秒）。

## 执行与停止条件

界面与代表加载已经交付，用户完成逐款检查并直接确认全部发型在固定男女参考人物上正确贴合、没有明显穿模。R02 completed，只关闭这一静态几何范围。人工汇总保存到 `human_review_summary.json`；不伪造控制面板逐项点击记录，不改正式性别许可、原 Registry 或转换批次报告。

用户同时报告 HB2-05、HB2-06、HB2-12 发辫偏深及男女 Body 材质接缝。R03 原因核查和处理建议 completed：发辫确认为源 `RLHair` 语义遗漏导致的混合 Shader 分支；Body 存在六张 Normal 纹理分类错误、源头/体 Diffuse 接缝色差和通用材质缺少皮肤响应。两项修复尚未实施，未做因果 A/B，不把颜色/材质接受并入几何通过。无需重新审查全库静态贴合，也不增加全动作、任意身份、服装组合或照片生成验证。原约束仍适用：不覆盖规范源，不重启或关闭用户 UE，不自动启动导出/导入批处理或基础装配。本轮授权只要求原因检查，所有 R01–R03 已交付，计划迁入 History；项目显式空闲，定向材质修复作为待执行建议，等待用户启动，不扩成新必需需求或自动执行基础装配。

## 最终证据与未纳入范围

人工几何汇总、发辫与身体材质只读诊断均保存在本审查 Run Root。发辫涉及五款、12 个源槽/24 个双性绑定；真实 39 个发饰槽维持保留。两性的 Body/Arm/Leg 共六 Normal 以 sRGB/default 类别错误导入，Head Normal 正常；16 个源颜色/法线图与既有导出字节一致，但源 Head/Body 接缝色差本来存在。未做材质 A/B、正式资产修改、网格重导或生产画质验收。最终文档审计由本轮收尾报告 `documentation_audit_diagnosis_closeout.json` 记录，本轮已独立通过，不继承界面交付审计状态。

## 后续诊断更正指针（2026-10-05）

本计划关闭时的源Head/Body显著色差判断后来被证明是UV采样错误：诊断脚本clamp了UDIM整数偏移，正确按每材质UV modulo1采样后仅约1–1.7RGB/255，不支持修改源肤色色调。原报告与本关闭快照保留；更正权威为新修复Run Root的`skin_source_seam_corrected_diagnosis.json`及[Runtime3.11](../../../technical/unreal/CHARACTER_RUNTIME.md#311-固定参考头型人物与发辫的定向材质修复2026-10-05)。前序静态几何人工接受和发辫Shader诊断不因此失效；实际新修复不采用颜色Delta。
