# 固定头型角色与发辫材质定向修复

> 文档 ID：`PLAN-2026-10-FIXED-HEAD-MATERIAL-REPAIR`
> 文档类型：`plan`
> 生命周期：`completed`
> 计划状态：`completed`
> 影响阶段：`WF-40`、`WF-50`
> 完成条件：修复已定位的发辫及男女参考身体材质问题，完成代表对照与准确映射核对，接入既有人工审查入口，并避免后续相同导入复发
> 最近核验：2026-10-05（R01发辫/R02身体保存及代表通过，新材质索引已发布；R03防复发验证完成，R01–R04完成；307回归及16独立子系统/跨层审计通过）

## 目标与范围

前序[人工审查与原因核查](../../history/completed_plans/PLAN-2026-10-FIXED-HEAD-HAIR-VISUAL-REVIEW.md)已经完成。用户确认所有保留发型在固定男女参考人物上正确贴合、没有明显穿模；本计划仅修两个已定位的材质问题，不重开前序计划，不撤销原静态几何结论。

发辫目标为 HB1-18、HB2-02、HB2-05、HB2-06、HB2-12 五款中明确标为 `RLHair` 的12个源槽、24个双性绑定；真实发饰和已批准隐藏的 Scalp/Hairline 槽保持。身体目标为六张Body/Arm/Leg Normal分类缺陷和复制女性Head Normal的GPU数据异常，采用16张原始PNG独立物理导入与统一皮肤响应。正确UDIM采样已排除显著源头身色差，最终不改肤色色调、不使用Delta。使用代表对照定位有效修复后应用准确范围，不要求重新拍摄全部发型、全动作或逐身份验证。

## 需求与落实

| 需求 ID | 要求 | 影响 Workflow | 状态 | 验收条件 | 证据入口 |
| --- | --- | --- | --- | --- | --- |
| `R01` | 修复遗漏 RLHair 发辫的材质类型和对应槽纹理/参数 | `WF-50` | `completed` | 代表款对照显示发辫的异常暗/缺高光得到纠正；按源语义处理24绑定，保留真实发饰与覆盖层隐藏，不要求所有部件完全同色 | [Runtime 3.11](../../../technical/unreal/CHARACTER_RUNTIME.md#311-固定参考头型人物与发辫的定向材质修复2026-10-05)；新 Run Root `hair/hair_apply_latest.json`（success、mode=apply、24绑定）；代表 `hair_before.png` / `hair_after_preview.png` 已实际查看 |
| `R02` | 修复男女皮肤法线设置与头身接缝 | `WF-50` | `completed` | 16张原Diffuse/Normal独立物理导入、法线类型正确、统一无Delta材质；代表对照无明显颈肩/四肢边界并保存，不改源肤色/几何 | [Runtime 3.11](../../../technical/unreal/CHARACTER_RUNTIME.md#311-固定参考头型人物与发辫的定向材质修复2026-10-05)；新 Run Root `skin_build.json` / `skin_preview.json` 与纹理GPU探针；`skin_apply.json` success/apply，两性2网格8皮肤绑定；`material_repair_visual_review.json`记录实际正/背代表通过 |
| `R03` | 修正可复用导入路径，防止相同材质语义与 Normal 分类错误复发 | `WF-40`、`WF-50` | `completed` | 实际导入配置/辅助实现按 CC Shader 语义与纹理用途设置，精确映射及针对性代码检查通过；不重新导入80套 | [Transfer 11.5](../../../technical/transfer/CC_TO_UE_MODULAR_OUTFIT_PILOT.md#115-固定男女参考头型的双版本发型转换2026-10-04)；主worker接入源Shader与物理皮肤辅助；`skin_future_import_offline_check.json`男女8槽16纹理/4针对性测试，`skin_future_import_runtime_smoke.json`独立女性4槽8图及二次幂等真实UE通过 |
| `R04` | 保存修复回执、代表结果及用户可复查入口，同步当前权威 | `WF-50` | `completed` | 材质绑定/保存结果及几何保护核对；已有双角色审查入口可看修复；文档及必要回归通过，不自动声称用户已接受修复效果 | [WF-50 状态](../../status/workflows/WF-50.md)；新 Run Root `registry_publication_report.json`已生成；`material_apply_verification.json`264实际检查、0失败；307完整回归通过（74.52秒）；`material_repair_docs_audit.json`16独立子系统及跨层检查全部通过，0错误/0警告 |

## 执行顺序

1. 两个独立问题可并行准备源参数/贴图和修复方案；UE实际修改由统一入口串行协调，避免相互覆盖当前场景。
2. 先对发辫代表款和男女身体代表做最小材质对照，修复有效后应用已确定对应范围，并保留原材质与源输入的可追溯信息。
3. 将同类材质/纹理规则接入后续导入路径，核对精确绑定、保存结果和不变的几何/性别许可。
4. 更新既有审查入口与复现说明，以代表检查和机器映射完成交付，用户可随后直接在UE观察；不要求再走一轮40款×两性的手工几何审查。

## 不包含

不重新导出或导入80套发型，不修改人物头型/身体/骨架或发型几何，不重启CC、不开展Headshot流程，不自动执行 queued 基础装配或新数据Batch。原几何人工接受和原转换报告保持，不通过改历史证据伪造修复终态。

## 风险与停止条件

源辫子颜色允许保留本身差异，目标是纠正混合Shader和缺失参数，不强制所有发丝完全同色。正确wrap采样排除了显著源色差，旧clamp采样结论已更正；纹理GPU数据与材质响应仍需代表实际确认，不能仅属性正确就写通过。材质修复若影响饰品/覆盖层、几何或其他明确保留资产，停止对应修改并恢复该作用域。

## 完成与迁移条件

R01–R04全部获实际证据后，记录修复限定范围和仍存在的视觉限制，同步Workflow/Status/Technical和机器目录，完成必要回归及文档审计，再将本计划迁History。机器通过不代替用户后续视觉判断，不为结项自动启动其他计划。

## 当前进展

发辫已保存到对应五款24材质绑定，`hair/hair_apply_latest.json` 为 `success=true/mode=apply`。代表 HB2-05 前后图已实际查看，原暗黑条状的辫子改善为正常棕色、细节可见；这不是用户新增验收，也不强制原辫子与主体颜色完全一致。R01completed，不需再导出或改几何。

身体R02已完成保存：`skin_apply.json` success/apply，男女两网格8皮肤材质绑定、CorrectionStrength0；`body_final_front.png`与`body_final_back_rotated.png`已实际查看，原明显颈肩/四肢接缝和异常阴影不再出现，两张脸正常。后颈部分被发型遮挡，未做隐藏面审查；墙后黑色`body_final_back.png`明确是失败拍摄，不用于视觉接受。

正确wrap采样仅约1–1.7RGB/255，旧clamp显著色差已更正；最终16原PNG独立物理导入、统一无Delta父材质、源肤色色调保持。真实代表检查由`material_repair_visual_review.json`限定记录，不自动标记用户修复后接受。

新`wardrobe_registry_ue_v4_fixed_head_materials_20261005_v1.json`已发布为默认，`registry_publication_report.json`绑定新RegistrySHA和两份apply独立快照，旧Registry/import_report不变。R03通用物理纹理实现及源规划/4针对性测试/独立UE幂等smoke完成。`material_apply_verification.json`264只读核验、0失败；完成批次guard实际返回无重导，80records/原import_report SHA保持；本轮完整要求回归307passed（74.52秒）。`material_repair_docs_audit.json`16独立子系统及跨层审计通过、0错误警告，R04completed；计划迁History，当前显式空闲，基础装配仍queued不启动。

## 结项证据与限定范围

最终汇总为新Run Root`material_repair_closeout.json`。发辫24绑定和男女8皮肤绑定已保存，原始PNG16张独立物理导入且不改肤色/几何；新材质Registry及两份apply快照由publication锁SHA。264实际UE只读检查零失败，独立女性未来导入幂等smoke/男女源规划与针对性测试通过，完成批次guard无重导、原80record报告SHA不变。307完整回归与16独立子系统/跨层文档审计实际通过；归档导航的最后快速复核由`material_repair_docs_audit_final.json`登记，不重复UE/全pytest。

代表发辫/身体正背真实图通过限定静态范围，后颈部分被发型遮挡；失败墙后黑背图不作为接受。用户修复后视觉确认已由`user_material_acceptance.json`独立记录，不新增伪造人工按钮结论；不外推全角度/隐藏面、动态或任意身份。用户已使用原双角色审查入口检查并直接确认一切正常。无需自动启动排队装配或新数据Batch。

## 后续用户人工验收（2026-10-05）

2026-10-05用户通过现有审查界面检查后直接确认：“ok，没问题，我刚才也通过审查界面进行了检查，一切正常。” `user_material_acceptance.json`（记录时间2026-10-05T12:57:13+08:00）绑定当前正式材质Registry及SHA，关闭现有男女参考人物审查场景中的修复后发型和皮肤外观人工接受范围。来源是本轮直接文字报告，不是逐款/逐角按钮记录；不新增动态、任意身份或隐藏表面通过，原材质失败、机器代表图和失败拍摄历史保留。
