# PLAN-2026-10 Headshot 固定头皮与男女双套发型

> 文档 ID：`PLAN-2026-10-HEADSHOT-FIXED-SCALP`
> 文档类型：`plan`
> 生命周期：`completed`
> 计划状态：`completed`
> 影响阶段：`WF-20/WF-30/WF-40/WF-50`
> 完成条件：保留已认可的男女参考形状，完成保留发型的男女适配导出、UE 导入整理、索引消费和文档同步
> 最近核验：2026-10-05（R01–R05 完成，运行与终态文档审计证据齐备）

## 目标与授权范围

用户已认可路线 1 的 CC 角色创建范式，并明确接受 female01、male01 作为后续男女角色各自的参考头皮形状。2026-10-04 的活动 Goal 授权基于这两份来源完成全部保留发型的男女版本，沿用已跑通的导出、导入和去冗余流程；发型原有性别使用许可不因此改变。

用户要求赶投稿进度：脚本完成后用一个代表发型验证男女分支的位置、发丝材质和头皮覆盖层，随后批量轻量核对文件、引用与结果；不要求逐款人工审查、全动作穿模验证或重新研究 Headshot/细分问题。旧 UE 同表情绝对位姿残差保留为技术限制，不再阻塞本次规范源与发型任务。原路线对照、失败实验及数值证据由 [BodyFit Technical 第10节](../../../technical/character_creator/BODYFIT_IDENTITY_AGE.md#10-headshot-正式路线对照验证) 保留，不宣称严格旧 Average UE 位姿相等已通过。

CC 保持当前离线环境，不擅自重启或联网。必要时短暂使用 Computer Use，优先 Bridge/API 与已有弹窗处理。全部处理使用独立副本和新 UE 版本目录，完成前保留旧接受资产；不建立新的数据生产 Batch。

## 需求与验收

| ID | 要求与验收条件 | 影响阶段 | 状态 | 证据入口 |
| --- | --- | --- | --- | --- |
| `R01` | 核验本机 Headshot 照片生成及输入来源 | `WF-30` | `completed` | [BodyFit/Headshot Technical](../../../technical/character_creator/BODYFIT_IDENTITY_AGE.md) 的已有实验及人工新照片复现 |
| `R02` | 采用路线1及男女各自固定参考头皮，明确保留面部差异与已接受范围 | `WF-30` | `completed` | 用户认可 female01/male01；已有几何、CC 新照片及 UE 人工审查；旧严格位姿残差作为范围限制保留 |
| `R03` | 整理男女无发型源副本、记录来源 SHA，并用代表发型核对源可用 | `WF-30` | `completed` | 两份源及 Body 摘要见 `sources/source_manifest.json`；HB3-17 男女导入/挂载与六张实际查看结果见新 UE Run Root 的 `pilot_review.json` |
| `R04` | 40款保留发型各导出男女版本，共80套；导出检查后导入 UE；保留头发必要网格/材质/纹理、共享骨架，更新双版本索引 | `WF-40/WF-50` | `completed` | `export_completion_check.json` 完整来源与纹理核对；`import_report.json` 80/80；`registry_publication_report.json`、`consumer_completion_check.json` 与 `final_runtime_audit.json` 实际加载/清理闭包通过 |
| `R05` | 同步复现入口、可续跑状态、输出所有权与文档审计 | `WF-30/WF-40/WF-50` | `completed` | Catalog/Inventory 已重建；`documentation_audit_preclosure_v2.json` 全部 16 子系统与跨层通过、零错误警告，`regression_tests_final.json` 299 passed；归档后的 `documentation_audit_final.json` 实际全 16 子系统及跨层通过、零错误警告；独立文档状态回归 25 passed（9.78 秒） |

## 固定输入与执行入口

- 女性来源：`headshot_route_compare_20261002_v1/female01_baked_final_capture_v1/morph_bake_checkpoint.ccProject`。
- 男性来源：`headshot_route_compare_20261002_v1/male01_average_inverse_roundtrip_v1/roundtrip_subd0.ccProject`。
- 来源哈希和整理副本以 `%OUTPUT_ROOT%/character_creator_bridge/artifacts/fixed_head_hair_20261004_v1/sources/source_manifest.json` 为准。不得把早期烘焙、临时头皮原型或人工新照片角色替代本次已认可的参考形状。
- 保留发型及 `male/female/both` 使用许可来自现有正式 UE 索引；每个保留发型仍导出男女两个几何版本。
- CC、UE 与索引脚本、目录、恢复步骤由 [Transfer 第11.5节](../../../technical/transfer/CC_TO_UE_MODULAR_OUTFIT_PILOT.md#115-固定男女参考头型的双版本发型转换2026-10-04) 拥有；小样与消费由 [Runtime 第3.9节](../../../technical/unreal/CHARACTER_RUNTIME.md#39-固定头型双版本发型的代表小样与索引消费2026-10-04) 拥有。

## 执行顺序与停止条件

先整理源，再完成一个代表发型的男女导出/导入与挂载检查。小样通过后导出全库，核对 FBX/JSON/纹理闭包，再执行全库 UE 导入和精简；同一发型记录男女网格及对应共享 Skeleton。批次报告记录每项完成状态、源哈希及失败，不重复提交已确认在运行的工单。2026-10-05 已检查 HB3-17 男女正面、侧面和背面六张图，位置、发丝透明效果和隐藏覆盖层在该小样范围通过。恢复时读取 `live.json`、Bridge 心跳/队列及目标结果，不照抄历史 job ID。

全库发布条件为所有目标对均有成功导出和导入记录，索引可按性别解析，代表小样检查通过，正式索引及引用完成对应版本切换。重复人物中间包仅在本批次新目录内、依赖核对通过后清理，原始源和旧接受库保留；不得将目录存在当成完成。

遇到真实导出失败、阻塞弹窗或绑定/材质异常，只处理该具体问题并续跑；不扩大为旧路线全面验证。细分与 Headshot 基础外观装配的进一步研究不属于本次任务。

## 完成记录与范围

2026-10-05 已完成男女源副本、40款×2 的 CC 导出与 UE 导入、新索引及默认消费、一次全量实际加载与临时人物包清理。完整来源、导出、导入、发布、消费者、实际加载及保护哈希证据见新批次 CC/UE Run Root 的相应报告；代表视觉只覆盖 HB3-17 男女六图。

必要回归 299 passed，preclosure_v2 的 16 独立子系统及跨层检查均通过、零错误警告。本计划 R01–R05 关闭并进入 History；归档与显式空闲状态的 `documentation_audit_final.json` 已实际全 16 独立子系统及跨层通过、零错误警告，覆盖 535 脚本、128 输出作用域和 124 文档。另有 `documentation_state_regression_final.json` 的 25 项测试通过（9.78 秒）；与 299 项回归为独立运行。

GPU 故障通过 NullRHI 导入/结构审计绕行，驱动根因未修复。HB1-01 男女两处缺省 Diffuse 回退及实体/装饰/V2 parent 有旧支持依赖，旧 accepted 资产/索引继续保留。未验证全部款式视觉、任意身份或全动作合身，没有新数据生产 Batch，基础外观装配仍 queued、等待用户启动。
