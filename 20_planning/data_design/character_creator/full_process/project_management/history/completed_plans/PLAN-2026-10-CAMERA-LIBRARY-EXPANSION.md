# 共用镜头库与未覆盖组合补测

> 文档 ID：`PLAN-2026-10-CAMERA-LIBRARY-EXPANSION`
> 文档类型：`plan`
> 生命周期：`completed`
> 计划状态：`completed`
> 影响阶段：`WF-60`；关联 `WF-50/WF-80`
> 最近核验：2026-10-11（147样片技术交付完成，待人工筛选）

## 目标与授权

用户认可将相机拆为朝向、景别和移动方式的共用库，授权保留合理结果、补测未覆盖的动作/镜头组合，并改进原推进与拉远幅度。前序34条不是完整支持清单；未提及的组合属于候选待验证，不默认为不支持。本计划承接新授权，不重开已归档相机pilot，不自动开展正式数据生产或严格像素确定性修复。

## 已取得的人工反馈

针对原34条审查样片，明确排除04、11、16、24、27；05、09、30、31需要修改推进/拉远幅度后重新审查；其余25条在用户所看范围内认可。32/33慢放自然；180°环绕保留该样片认可，但是否成为常规默认镜头库仍未定。原视频与原交付时pending回执保持原字节，新反馈独立记录。

“前侧全身”等镜头在一个动作中被排除不意味着其他动作全部排除；认可的共用库设计也不等于全部组合已通过。所有新样片最终自然度和镜头偏好仍由用户判断。

## 需求与验收

| 需求 ID | 目标 | 影响 Workflow | 验收条件 | 当前落实状态 | 证据与缺口 |
| --- | --- | --- | --- | --- | --- |
| `PLAN-2026-10-CAMERA-LIBRARY-EXPANSION/R01` | 保留原审查结果 | `WF-60` | 原34条逐项关联反馈，保留认可、排除和需修改，来源可追溯；不修改旧媒体 | `completed` | human_camera_feedback_v1.json；原34来源清单SHA及逐条反馈已记录 |
| `PLAN-2026-10-CAMERA-LIBRARY-EXPANSION/R02` | 建立共用镜头库与补测矩阵 | `WF-60` | 朝向/景别/运动分别配置；七代表动作的未覆盖候选有明确测试或延期理由，不机械穷举，不以未覆盖等同排除 | `completed` | composable_camera_library_v1.json、camera_coverage_candidates_v1.json、expansion_plan_v1.json与expansion_geometry_audit_v1.json；16候选中14渲染、2保留几何拒绝 |
| `PLAN-2026-10-CAMERA-LIBRARY-EXPANSION/R03` | 改进推近拉远并完成补测 | `WF-60/WF-80` | 保持统一10秒；新版本起止构图差异明确；实际场景/Sequence、媒体解码和代表帧验证；失败保留 | `completed` | 原14候选技术补测完成；后续稳定跟拍与完整147矩阵替代本项旧候选决策，2026-10-11用户与师兄接受最终147；不代签旧14人工接受 |
| `PLAN-2026-10-CAMERA-LIBRARY-EXPANSION/R04` | 交付可理解的审查入口 | `WF-60` | 原认可、新候选、需改进结果可区分；用户可比较新旧幅度和未覆盖组合；浏览器实际验证 | `completed` | review_delivery_manifest_v1.json共43条；browser_verification_v1.json与入口截图通过；新增用户偏好pending |
| `PLAN-2026-10-CAMERA-LIBRARY-EXPANSION/R05` | 文档与验证闭环 | `WF-60/WF-50/WF-80` | Technical/Registry/Status/Plan一致，必要回归、Catalog/Inventory与独立子系统/跨层审计通过，人工待办明确 | `completed` | full_regression_v2.xml 1081通过；Catalog/Inventory重建；documentation_audit_v1.json独立16子系统及跨层通过，0错误0警告 |

| `PLAN-2026-10-CAMERA-LIBRARY-EXPANSION/R06` | 稳定跟拍规则与15镜头配方 | `WF-60` | 小摆动不敏感，大位移平稳跟随；7基础+2环绕+6推拉，动作替换保配方而非相同轨迹 | `completed` | 45轨迹冻结，stable_geometry_audit_v1.json独立复核13545端点帧通过；42适用严格代理检查+3诊断例外，真实观感pending |
| `PLAN-2026-10-CAMERA-LIBRARY-EXPANSION/R07` | 三动作完整45组合实际补测 | `WF-60/WF-80` | 伸展/跳舞/行走各15镜头，真实渲染/完整解码及抽样观察 | `completed` | camera_stable_follow_20261010_v1/technical_delivery_v1.json；45视频及900实际采样帧，保留近景限制 |
| `PLAN-2026-10-CAMERA-LIBRARY-EXPANSION/R08` | 新审查网页交付 | `WF-60` | 可按动作和同镜头跨动作比较45候选；全部待用户选择，明确边缘取景问题 | `completed` | review_delivery_manifest_v1.json 45可播放；browser_verification_v1.json实际切换/联播/暂停/循环/新视频末尾定位通过，Range修复定向6项通过 |
| `PLAN-2026-10-CAMERA-LIBRARY-EXPANSION/R09` | 本次文档与验证闭环 | `WF-60/WF-50/WF-80` | 新所有权/ADR/状态/计划一致，实际代码回归和独立文档审计完成 | `completed` | full_regression_v1.xml 1091通过（启动器修正前）；修正后range_regression_v1.xml定向6通过；Catalog718与Inventory149重建；documentation_audit_v1.json 16独立子系统及跨层通过、0错误0警告 |

| `PLAN-2026-10-CAMERA-LIBRARY-EXPANSION/R10` | 补全全身/上半身五角镜头 | `WF-60` | 全身5角+上半身5角+正面近景1+俯仰2+环绕2+推拉6，共21配方；保持原稳定跟随及初始朝向，不增加追逐转身 | `completed` | expansion_plan_v1.json冻结21×7；complete_angles_geometry_audit_v1.json独立复核通过，保留13诊断例外 |
| `PLAN-2026-10-CAMERA-LIBRARY-EXPANSION/R11` | 首七动作147组合补测 | `WF-60/WF-80` | 21×7完整矩阵有逐项结果；10秒、推拉第7秒结束距离变化；真实媒体与近景诊断 | `completed` | technical_delivery_20261011_v1.json；147真实10秒媒体完整验证，五份实际观察覆盖全矩阵并绑定最终媒体；人工筛选pending |
| `PLAN-2026-10-CAMERA-LIBRARY-EXPANSION/R12` | 扩充审查页面交付 | `WF-60` | 可按7动作与21配方筛选/对照，保留问题提示、原输出和接受边界；实际浏览器核验 | `completed` | review_delivery_manifest_v1.json 147可播放；browser_verification_20261011_v1.json验证七动作联播/暂停/循环、筛选、全屏及定位；截图已保存 |
| `PLAN-2026-10-CAMERA-LIBRARY-EXPANSION/R13` | 扩充文档与验证闭环 | `WF-60/WF-50/WF-80` | 当前计划/状态/Technical/Registry及输出所有权一致；本轮代码验证与独立文档审计通过 | `completed` | 冻结源码full_regression_v1.xml 1101通过；最终Catalog/Inventory重建与documentation_audit_20261011_v1.json记录独立检查，人工接受pending |

## 时间、输入与保护边界

暂定统一10秒：身体源长≥10秒取连续10秒@1倍；7至不足10秒匀速慢放；不足7秒排除；禁止身体循环/冻结补时。表情保持原速5秒重复。相机按最终身体时间轴预规划；外观编辑对共享冻结轨迹，不随外观单侧重算。用户新授权的动作替换允许同配方按各自动作生成不同平滑轨迹，限定语义见ADR-0018。前序严格像素复现失败仍有效，技术补测不自动取得确定性生产Gate。

仅使用独立新Run及版本化UE资产，保护原审查关卡、原34视频、源动作、角色衣发和用户全局MRQ队列。共享UE由root串行操作，离线矩阵与文档可并行。

## 实现与证据入口

- 实现所有者：[场景相机 Technical §8](../../../technical/unreal/SCENE_CAMERA_SEQUENCE.md#8-共用镜头库与补测2026-10-10)。
- 当前落实：[WF-60状态](../../status/workflows/WF-60.md)。
- Run Root：`%OUTPUT_ROOT%/unreal_character_import/camera_library_expansion_20261010_v1/`。
- 输出沿用 `OUT-WF60-SEQUENCE-TEMPLATE`，默认 `unclassified` 保护；验证归 `VAL-SCENE-01`，仅本轮实验范围。

## 完成条件与交付

当前技术补测与审查入口交付后继续保持唯一current计划，等待用户检查新增镜头及修改幅度；R03在工程证据与人工审查分层记录，不代签接受。后续达到本计划完成条件时再记录最终证据、更新状态并归档。尚未测试的组合有明确候选/延期状态，不宣称全动作全镜头兼容。

## 本轮新增授权：稳定跟拍（2026-10-10）

用户要求先完成15镜头×伸展/跳舞/行走的45候选，而非穷举三轴库。相机响应整体位移、不逐帧追随头胸局部起伏；侧面/正面/背面由动作初始朝向确定，人物转身不强迫相机绕转。环绕为全身120°/360°，10秒完成；推拉正面/侧面/正后方各一，全身↔上半身，0–7秒平滑完成，7–10秒保持目标景别并继续跟随整体位移。面部/上半身配激烈动作允许暂时裁切或露出更多身体，但不得完全放弃跟随；本轮先渲染供用户选择，不提前宣布禁配。旧14样片仍人工pending，不代签接受。

新Run `%OUTPUT_ROOT%/unreal_character_import/camera_stable_follow_20261010_v1/`，实施归Technical §9；继续唯一current计划，R06–R09承接本次任务，R01–R05既有证据按历史范围保留。

前序45交付时的下一步是人工审查，现已由以下完整角度新授权承接。旧R03对应14候选人工未接受保留历史状态，不要求先返回旧14；当前稳定跟拍方向已替代旧补测的后续执行优先级。

## 最新授权：完整角度与首七动作（2026-10-10）

用户整体认可稳定跟拍试验效果，授权补全全身与上半身各五个方向（正面、前侧、侧面、后侧面、背面），面部近景只保留正面；保留俯视/仰视全身、120°/360°全身环绕、正侧背推进/拉远，合计21配方。先覆盖向前行走、舒展舞步、调整站姿、弯腰伸展、甩头转身、边走边思考、好奇探看7动作，共147候选。人物自身转身不触发相机追逐朝向，保持既有稳定跟随规则。

新Run `%OUTPUT_ROOT%/unreal_character_import/camera_complete_angles_20261010_v1/` 由Technical §10拥有，R10–R13承接当前工作；此前45的总体认可不等于全时刻/全部近景/生产Gate通过，原64/65/79/80/95等诊断及旧pixel-exact失败保持。旧45与旧14原交付回执不倒写，不要求用户先返回旧页。当时授权目标为补全147镜头矩阵并交付新审查页；现已技术交付完成，当前下一步见最终工程交付。


2026-10-11恢复过程检查点（历史）：用户已关闭UE与Codex后要求继续。保留首批42及第二批新attempt42验证媒体和原第二批失败attempt，来源恢复1194项通过；余下三个21条批次继续；唯一current计划及R10–R13范围不变。

最终工程交付（2026-10-11）：R10–R13技术范围已完成，147候选供用户筛选。当前唯一下一步为新版8879网页人工审查；当前计划不归档，不将旧R03历史pending或本轮诊断样片代签通过。

## 2026-10-11 最终接受与结项

用户与师兄审查最终21×7的147条，确认全部合理并保留。独立证据为 `cleanup_current_pipeline_20261011_v1/user_camera_acceptance_v1.json`，绑定原计划及147媒体清单哈希；原pending回执不修改。R03旧14候选的后续决策被R06–R13的新方案替代，不再等待旧页反馈，也不宣称旧14人工接受。R01–R13授权范围结项；上述阶段文字保留当时状态，当前事实以本节为准。新清理任务独立承接；面部细节由另一个会话处理，严格像素确定性失败仍未解决。
