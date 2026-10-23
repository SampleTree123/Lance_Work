# 输出盘点与保留

> 文档 ID：`TECH-OUTPUT-02`
> 文档类型：`technical`
> 生命周期：`current`
> 适用阶段：全部 Workflow
> 实现所有权：输出所有权规则、保留策略、Inventory Builder 和非破坏性清理前置条件
> 验证所有权：`VAL-DOC-01`
> 输出契约：`OUT-GLOBAL-OUTPUT-INVENTORY`
> 最近核验：2026-10-11（追加独立工作区深度清理）

## 1. 能力与边界

本能力回答：某个 `%OUTPUT_ROOT%` 路径由谁生产、属于哪个 Workflow/`OUT-*`、当前保留级别是什么、是否允许进入清理候选。它不生成业务产物、不自动删除文件，也不替代生产它的领域 Technical 文档。

机器权威：

```text
00_engine/outputs/README.md
00_engine/outputs/RETENTION_POLICY.json
00_engine/outputs/OUTPUT_INVENTORY.json
```

## 2. 实现组成与环境

| 文件 | 生命周期 | 作用 |
| --- | --- | --- |
| `00_engine/scripts/documentation/build_output_inventory.py` | `utility` | 非破坏性扫描输出作用域并应用最长前缀规则 |
| `00_engine/scripts/documentation/check_character_factory_docs.py` | `utility` | 检查 owner、保留规则、输出契约和物理路径一致性 |
| `00_engine/outputs/RETENTION_POLICY.json` | `authoritative` | 人工审查的所有权与保留规则 |
| `00_engine/outputs/OUTPUT_INVENTORY.json` | `authoritative` | 当前盘点生成物 |

在 `%LANCE_ROOT%` 的系统 Python 环境执行，不需要 CC/UE：

```powershell
python 00_engine/scripts/documentation/build_output_inventory.py
python 00_engine/scripts/documentation/check_character_factory_docs.py --json
```

## 3. Policy 契约

`ownership_rules` 只决定领域 owner 和 Workflow；`rules` 决定经过人工审查的保留级别，并可用更长路径覆盖 owner。二者与 `output_contract_id` 共同形成反向查询，但所有权和保留必须保持独立：一个输出有 owner 不代表它值得长期保留，一个输出未分类也不代表可以删除。

保留级别：

| 级别 | 含义 | 清理资格 |
| --- | --- | --- |
| `authoritative` | 当前生产输入、正式媒体/数据或不可替代 Manifest | 未迁移验收前禁止 |
| `retained_evidence` | 支撑 Gate、事故结论或人工接受 | 替代证据通过后再审查 |
| `superseded` | 已由映射后的新版本完整取代 | 可进入人工清理候选 |
| `disposable` | 可重建缓存、临时日志或失败中间帧 | 不影响追溯时可清理 |
| `unclassified` | 尚未完成保留审查 | 默认禁止 |

## 4. Inventory 契约

盘点记录至少包含：相对路径、作用域级别、文件数、字节数、最后修改时间、`retention`、`workflow`、`owner_document`、`output_contract_id`、匹配规则和原因。默认枚举每个输出根的直接子作用域；Retention Policy 点名的深层路径额外单列，避免递归展开巨大历史树。

Inventory 是可重建元数据，不替代正式发布媒体哈希。`WF-90` 的 Delivery Manifest/Checksums 才负责交付内容完整性。

## 5. 新输出登记

1. 在生产它的领域 Technical 文档中写清 `OUT-*`、路径模式、目录结构、验证和建议保留级别。
2. 若为新逻辑产物，在 [输出契约目录](./OUTPUT_CONTRACTS.md) 登记稳定 ID。
3. 在 `ownership_rules` 增加大类 owner；需要长期保留时再在 `rules` 增加精确路径、`output_contract_id` 和理由。
4. 重建 `OUTPUT_INVENTORY.json`，确认物理路径、owner、Workflow、契约和保留级别。
5. 执行 `VAL-DOC-01`，并在对应 Workflow/Batch Status 登记当前接受版本。

## 6. 清理前置条件

只有 `superseded` 或 `disposable` 可以成为清理候选。清理前逐项确认：目标绝对路径位于预期输出根、替代物存在且已验收、Manifest/哈希可追溯、当前 Status/Plan 未引用、Git 与 UE/CC 外部资产不依赖该路径。`unclassified` 不能因旧、占空间大或目录名含 `test` 被删除。

本流程只生成候选清单；递归删除仍是独立、显式审批的文件系统操作。

## 7. 验证与恢复

通过条件：所有输出作用域有存在的 Technical owner；每条保留规则目标存在、在 Inventory 中一致，并直接被 owner 文档说明；每条长期证据绑定有效 `OUT-*`。Builder 失败时保留旧 Inventory，修复策略或权限后原子重建，不手改生成统计。

路径漂移、误删或规则过期时先停止依赖该证据的 Gate。根据 Manifest 恢复路径，或创建新版本并更新 Status/替代映射；不得通过删除规则来让审计静默通过。

## 8. 当前限制

大部分历史作用域仍为 `unclassified`，在逐项确认替代关系前均受保护。Inventory 只盘点 `%OUTPUT_ROOT%`；`%CC_ASSET_ROOT%`、`%CC_EXPORT_ROOT%`、UE `/Game` 和服务器 Delivery 由其领域 Manifest/Registry 追踪，不因未出现在本文件中而失去所有权。

## 9. 2026-10-01 全面清理与目录重组

用户明确要求清理和重组 UE、CC、导出包、运行输出以及项目和文档中需要整理的内容。本次清理的输入盘点、UE 完整硬软包依赖图、替代验证、精确删除清单和执行回执保存于 `%OUTPUT_ROOT%/asset_cleanup/cleanup_20261001_v1/`，属于本能力的 `OUT-GLOBAL-OUTPUT-INVENTORY`，按精确保留规则作为 `retained_evidence`。独立审查分别位于 `ue_audit/`、`cc_audit/`、`output_audit/`；一次性程序保存在同一 Run Root，不作为生产脚本。

执行顺序为全量盘点、按当前 Registry/配置/机器验收与应用依赖复查、逐路径审查为 `superseded/disposable`、保存必要小证据或替代映射、按精确清单执行、验证保留输入和现用入口、更新引用与本次结果。本任务的明确用户授权覆盖已审查目标的清理，不另以日常文档维护推导删除权限。目标根和最终绝对路径必须在删除前核验；UE 内容包先在应用内核验包依赖、迁移现用关卡并尝试资产接口删除。本次资产接口存在返回成功但包文件残留的情况；仅在 UE 完全退出、保存态完整硬软依赖图证明删除集合无外部引用、精确路径和 SHA 已锁定后，使用原生 PowerShell 删除这些指定残留包文件。随后重新启动 UE 扫描与组装，确认没有新增缺失引用。此恢复路径不能用来删除尚有引用或未审查的 `.uasset/.umap`。

当前执行状态和剩余范围以该 Run Root 的回执及项目状态为准，不由目录存在或一次阶段完成推断全任务完成。旧 Manifest 保持原样；已移除的失败二进制或重复媒体由新清理映射说明，不把旧 Gate 报告改写为新的验收。

### 9.1 执行终态与保留核验

本轮实际清理已执行完成。分项回执为 `cache_cleanup_receipt.json`、`cc_cleanup_receipt.json`、`output_cleanup_receipt.json`、`checkpoint_cleanup_receipt.json`、`cc_custom_cleanup_receipt.json`、`ue_cleanup_receipt.json`、`cc_retired_export_cleanup_receipt.json` 和 `cc_staging_cleanup_receipt.json`；`cleanup_summary.json` 汇总这些互不重叠的成功回执，失败与续跑回执只供故障追溯，不重复计入删除量。文件删除字节合计是移除文件大小，不等于磁盘净空闲增长，新增审计证据与 UE 重建缓存会占用空间。

`final_retained_files_verification.json` 核对正式 UE 包、视频、规范身份项目及当前服装替代导出哈希，同时确认已审查删除路径确实不存在。CC 原生项目、BodyFit、Headshot、保留头发源资产与 BASE 导出闭包见 `cc_audit/final_protected_inputs_verification.json`。UE 新进程重载见 `post_cleanup_ue_reload_verification.json` 与 `post_cleanup_runtime_checks_completion.json`；保存态图见 `ue_saved_graph_verification.json`。原有可选编辑器 PreviewMesh/LiveLink 缺失引用仍有记录，本轮没有新增缺失引用，也未把这些原有缺失伪装为全部修复。

当前发型导出 Manifest 已由代码暂存目录迁至 `%CC_EXPORT_ROOT%/scalp_hair_batch_20260924_v1/manifests/cc_export.json`；暂存元数据按字节保存到本轮 `retired_cc_metadata/` 后清除原副本。UE 现用衣柜覆盖/服装头发审查入口已迁入 `%OUTPUT_ROOT%/unreal_character_import/current_reviews_20261001_v1/`，由 [角色运行时](../unreal/CHARACTER_RUNTIME.md) 拥有并按 `authoritative` 单独登记；全库重组旧计划保持冻结，不再承担现用入口。

旧 `pilot_m02_ue58_v001` 整个导出包保留：`retained_legacy_support_import_sources.json` 证明当前保留的 M02 共享支持资产仍以该 FBX 为重新导入源，不能随已退役的独立 Pilot 启动器删除。M_BASE/F_BASE 导出、第一批动作导出的两份 P0 桥接输入、仍被已验证入口使用的 Face V2.1 小配置、用户手工 CC 项目与已购买原始内容同样保留。根目录旧探针和原始手写审核规则仅作原字节归档，见 `root_file_archive_receipt.json`；空目录清理见 `empty_directory_prune_receipt.json`。

本轮不改变男性头型适配、正式覆盖层隐藏持久化、新 Headshot 标准头皮方案、发型 ID 改名或第二批矩阵的实现状态。最终文档和测试终态由本轮审计报告及 [项目状态](../../project_management/status/PROJECT_STATUS.md) 维护。


## 10. 固定参考头型双版本发型输出（2026-10-04）

本次 `fixed_head_hair_20261004_v1` 的CC证据/源副本位于 `%OUTPUT_ROOT%/character_creator_bridge/artifacts/fixed_head_hair_20261004_v1/`，导出位于 `%CC_EXPORT_ROOT%/fixed_head_hair_20261004_v1/`，UE报告位于 `%OUTPUT_ROOT%/unreal_character_import/fixed_head_hair_20261004_v1/`。来源、字段与续跑由[Transfer11.5](../transfer/CC_TO_UE_MODULAR_OUTFIT_PILOT.md#115-固定男女参考头型的双版本发型转换2026-10-04)拥有；代表小样与一次结构加载终验由[Runtime3.9](../unreal/CHARACTER_RUNTIME.md#39-固定头型双版本发型的代表小样与索引消费2026-10-04)拥有，其精确范围为 UE Run Root 下的 `pilot_review.json`、实际 `pilot_captures/` 六图及 `final_runtime_audit.json`；保留为限定小样/结构终验依据，所有权细分不授权删除，分别映射 `OUT-WF40-TRANSFER-BUNDLE` 与 `OUT-WF50-RUNTIME-ACCEPTANCE`。

本轮先登记生产所有权，未以目录存在或小样成功晋升全库；没有声明旧库 superseded，也没有新增可删除规则。原参考项目、当前source_manifest/整理源、成功导出输入和旧接受资产保留。新UE目录内的临时人物包精简只按导入器的具体依赖检查处理，不能扩大为清理旧正式树或原始CC项目。最终当前版本、结果与审计由项目状态维护。

## 11. 固定头型发型人工审查入口（2026-10-05）

`%OUTPUT_ROOT%/unreal_character_import/fixed_head_hair_manual_review_20261005_v1/` 归 `OUT-WF50-RUNTIME-ACCEPTANCE`，生产者和领域输出所有者是 [Runtime 3.10](../unreal/CHARACTER_RUNTIME.md#310-固定头型发型的双角色人工审查2026-10-05)。本次是独立人工审查界面和代表机器加载记录，不是新发型转换批次；没有 `captures` 或图片图库。已交付 `entry_context.json`、`worker_smoke_check.json`、`cli_smoke_check.json`、`current_case.json` 和 `panel_state.json`，`machine_handoff.json` 保存该次限定交付及来源哈希；后续 `human_review_summary.json` 已记录用户静态贴合通过；两份材质原因报告为只读诊断，修复由独立新Run管理。这里只登记输出所有权，不授权删除原转换证据或支持资产。

## 12. 固定头型角色与发辫材质修复输出（2026-10-05）

`%OUTPUT_ROOT%/unreal_character_import/fixed_head_material_repair_20261005_v1/` 的生产者与领域输出所有者为 [Runtime 3.11](../unreal/CHARACTER_RUNTIME.md#311-固定参考头型人物与发辫的定向材质修复2026-10-05)，归现有 `OUT-WF50-RUNTIME-ACCEPTANCE`。保存授权/执行状态、精确前后材质映射、两类问题代表对照、保存结果及几何保护与收尾验证。`execution_state.json`记录执行进度；发辫/身体success apply及代表范围由`hair/hair_apply_latest.json`、`skin_apply.json`、`material_repair_visual_review.json`各自证明，不能由执行状态文件代替。`registry_publication_report.json`与两份`*_apply_publication.json`为新Registry发布/绑定快照，前序错误采样由`skin_source_seam_corrected_diagnosis.json`明确更正；失败/未采用试验保留，不作最终视觉通过证据。该新作用域不覆盖旧审查人类结论或原转换报告，不新增自动删除规则；具体文件以该次实际修复回执及项目状态为准。

## 2026-10-11 当前流程清理

Run `%OUTPUT_ROOT%/cleanup_current_pipeline_20261011_v1/` 由本文拥有，沿用 `OUT-GLOBAL-OUTPUT-INVENTORY`，轻量证据保留。记录相机独立人工接受、保留依赖闭包、逐路径删除决策、实际执行及清理后验证。用户明确授权清除当前流程不用的输出/关卡/资产；执行仍以已核对引用和替代证据的清单为准，不能按旧目录名直接删除。未完成审计不推断disposable，根目录和跨工作区路径不得递归删除。当前147审查媒体、独立分享包、现用角色和再生成依赖继续保护；面部会话的角色皮肤输入不修改。

### 本轮退休后的使用边界

清理结果由 `cleanup_summary.json`、`raw_cleanup_execution_receipt.json`、`ue_cleanup_offline_execution.json`及`ue_post_cleanup_verification.json`记录。旧stable/library和非选中pilot场景已按清单退休；历史prepared回执不再表示资产当前存在或可重放。已删除PNG要重新渲染才能再编码，成品视频仍可直接审查。当前147、七组来源和cam05/31/34失败诊断保持；在线删除未落盘的失败回执原样保留，最终结果以正常关闭UE后的精确离线执行及重启registry检查为准。

## 2026-10-11 工作区深度清理（独立补充）

用户在独立会话明确授权清理整个 `D:/UE`。本轮 Run 为 `%OUTPUT_ROOT%/asset_cleanup/cleanup_20261011_deep_v1/`，归本文与 `OUT-GLOBAL-OUTPUT-INVENTORY`，作为 `retained_evidence` 保留。一次性审计、执行、核验程序只存于该 Run，不是生产入口。实际完成状态和数量分别由 `execution_receipt.json`、`verification.json` 记录，未执行前不据计划宣称完成；不修改主会话计划或皮肤优化状态。

`reviewed_plan.json` 锁定逐路径分类、替代物和保留文件 SHA；`deletion_file_manifest.jsonl.gz` 记录删除前文件清单。范围限定为可重建缓存、比现存正式资产更旧的自动保存、CFD40 普通成功案例的已完成校准/修正项目副本。较新或无正式对应物的自动保存保留；引擎安装文件及打包 DDC、Python 依赖、正式 UE Content、源照片、当前完整导出、固定头型参考、40 人最终项目及原始照片生成项目保留。AF001/AF002/BF001 故障恢复案例的中间项目全部保留。旧实验库、含独有内容的压缩包和旧渲染交付不因占用大而删除。

已退役创建检查点不再支持原任务逐步骤输出重验/断点重放；可以从保留的最终项目继续装配，或以新的任务 ID 从保留输入重新生成。原创建 state/result/失败回执不改写。历史源码 SHA 与当前源码的既有差异单独记录，不混同本次删除或偷偷更新历史 pin。清理前已发现 `D:/UE/deliveries` 不存在，不能据历史分享包记录推断 ZIP 仍可用；本轮保护工作区内现有 147 个审查视频。

## 2026-10-12 全工作区清理授权

本次用户明确将范围扩为整个D:/UE，outputs只是重点。`%OUTPUT_ROOT%/workspace_cleanup_20261012_v1/`由本文件拥有，沿用OUT-GLOBAL-OUTPUT-INVENTORY；保存全盘盘点、当前依赖保护、删除/迁移回执及最终验证。用户授权agent对明确无当前用途的文件自主判定并删除，仅完全不能判定者询问。历史引用和旧retained_evidence标签不是无限保留理由：本次经当前用途与依赖核查后可重新分类，轻量摘要说明物理退役和复现限制；不把删除记录变成新功能验收。原第6节逐项外部审批要求在本次已授权清理范围内由本轮审查清单与执行回执落实，不额外要求用户逐项批准。

当前网页/有效媒体、角色与衣发鞋发色、四类表情与身体动作、相机场景配置、待验证旧男女动作来源、另一会话皮肤实验与不可替代用户输入保持。暂不以目录名或日期直接删除，UE二进制需实际依赖证明。实际结果以Run回执为准，文档历史链接不保证旧二进制仍可重放。

### 本轮已发现的依赖漏判与修复

初批删除旧动作输出目录后发现当前catalog仍读取其中轻量JSON。该漏判已单独记录，没有声称删除全程无影响，也没有重建虚假历史成功回执。当前读取改为assets下明确的现用配置与保留源/包SHA验证；详见[Runtime恢复说明](../unreal/CHARACTER_RUNTIME.md#2026-10-12-清理后的当前动作读取与依赖恢复)。后续清理必须纳入真实catalog/contract调用所读取的文件集合，不能只保护大体积UE包和视频。

`current_entry_offline_smoke_after_dependency_recovery_v1.json`为本轮现用入口离线验证及文件读取清单。最初smoke对皮肤manifest预期条数误写12而实际为16，造成测试断言失败；修正测试预期后全部八项通过，原失败记录保留，并非皮肤素材缺失或已修复皮肤资产。自动UI和UE渲染未由该smoke覆盖。

### 主体清理结果与退休边界

本轮十批主体清理已完成，精确文件数和字节见Run `cleanup_summary.json`及分批execution回执，最终验证状态另查同Run。范围包含已编码原始帧、过时第一批结果、重复场景staging、旧UE试拍/测量关卡、CC中间快照、旧诊断视觉、旧一次性脚本与job/spec/chunk配置、过时Showcase项目及顶层pytest/崩溃缓存。删除字节不是磁盘净增长。

当前201/147审查媒体、皮肤实验、CFD40成品与当前生成/转移/运行依赖保留；原帧删除后必须重渲染才能重新编码或重跑原帧审计。CC中间快照删除后不保证旧逐步resume，应使用保留成品或新建任务。旧SceneTrials/Surveys及粗糙表情脚本不再可重放，不恢复其历史命令。

`retired_retention_rules_v1.json`保存11条已删除物理范围的旧保留规则，当前RETENTION_POLICY移除这些过时目标并拥有本轮清理证据；旧规则不是当前物理存在承诺。Showcase的四个静态来源已明确退役，见 `showcase_protection_retirement_v1.json`，不是绕过未知依赖强删；`cc_face_material_quality_profile_v1.json`材质知识保留，source_project字段仅为退休的历史来源，不是运行输入。

## 2026-10-23 最终流程精确清理与目录整理

Run [final_pipeline_cleanup_20261023_v1](../../../../../../00_engine/outputs/final_pipeline_cleanup_20261023_v1/)由本文拥有，沿用OUT-GLOBAL-OUTPUT-INVENTORY；审查、执行和验证回执作为轻量证据保留。渲染依赖与修复由[数据集Technical](../dataset/DATASET_DESIGN_EXPLORATION_20261021.md)拥有。已审查文件和UE包清理已执行；完整主片10秒小样已成功，配置包刷新已完成，见本Run的BUNDLE_REFRESH_RECEIPT.json，最终汇总由本Run [REPORT.md（最终汇总）](../../../../../../00_engine/outputs/final_pipeline_cleanup_20261023_v1/REPORT.md)记录，不宣称全库旧内容全部清除。

用户确认约94 GiB文件范围后，execute_approved_files.ps1按绝对路径、批准根、大小与保护源执行。approved_file_cleanup_result.json记录成功删除28,287文件、100,478,999,260字节、0失败；1项原已不存在，1条目录联接别名路径跳过。逐文件事实由approved_file_deletions.jsonl证明。全部JSON、最终40人可编辑项目、当前衣服/头发/角色导出源、现用数据/排除组合、保留成品媒体及frame_0000不在删除集合；无关graduateue、datatry_02/1、datatry_02/robotdata继续保留。

UE保存态依赖审查保留24,403包、删除集合11,314包，ue_boundary_check.json核对集合外引用为0，含软引用与编辑器引用。原生接口删除683个科幻资产后，批删触发嵌套Slate tick循环；保存停止编辑器，execute_reviewed_ue_offline.ps1仅处理批准精确集合，离线回执ue_offline_cleanup_result.json记录删除10,631文件、32,175,664,623字节、0失败。physical_preservation_check.json确认11,314候选包均已不存在、24,403保留包均在、28份保留MP4哈希不变。原生与离线结果不能重复计算；该恢复路径不构成未核对目录的通用删除授权。

候选体积、成功删除字节、磁盘净空闲增长分别读取回执，不将原已不存在、联接跳过或重试计入本次成功删除。清理后主片完整10秒小样已成功：[driver_summary.json](../../../../../../00_engine/outputs/final_pipeline_cleanup_20261023_v1/main_smoke/driver_summary.json)及[media_receipt.json](../../../../../../00_engine/outputs/final_pipeline_cleanup_20261023_v1/main_smoke/jobs/train_node_000000/media_receipt.json)记录300帧、1920×1080、30fps、27,456,881字节；准备结果复用，渲染26.56秒、编码12.73秒、总计40.64秒，首帧已查看。男性发型1024×1024 PNG也实际渲染并查看通过，1,274,566字节。14项衣柜修正绑定及13项渲染/参考/配置包测试通过。这是清理后限定入口/代表媒体验证，不代表全量生产、全库或Linux验证；配置包刷新已完成，见本Run的BUNDLE_REFRESH_RECEIPT.json。

新产物归 /Game/DataMake/Render/Main、/Game/DataMake/Render/References，启动工作地图为 /Game/DataMake/Render/Workspace/L_RenderWorkspace；冻结任务的源UE路径保留。已建立LOCAL的DM_Final_Render根集合和六类子集合：40人物身体、300衣服/鞋网格、117发型部件、52男女动作资产、21场景及1工作区。共享集合需要source control，当前不宣称共享；项目Saved/Collections中的7个collection文件连同config/UE_LIBRARY.json已进入配置包，便于迁移。

新formal目录asset_inventory_formal_runtime_catalog_20261023_cleanup_v1.json将520条已退休旧资产pin从现用验证移出、保留1,219条当前pin，旧目录字节不变；原publication兼容仅通过经验证存档和等价catalogs，不把旧摘要改成新验收。该变更及渲染入口恢复的技术细节见数据集Technical。已删中间帧需重渲染再编码，已删CC中间项目不能原地resume。另6.834 GiB旧皮肤PNG未在已确认范围内，暂保留；来源不确定的CC源也保留，见remaining_large_scoped_review.json。实际上传清单、来源摘要和ZIP须在最终验证/保存后按BUNDLE_REFRESH_PROCEDURE.md刷新，以最终回执说明完成范围。

本次最终刷新回执：`final_pipeline_cleanup_20261023_v1/BUNDLE_REFRESH_RECEIPT.json`。TRANSFER_PLAN包含58,207个文件、77,117,337,301字节；配置ZIP为15,870,744字节。现用来源摘要、PACKAGE_FILES及上传清单已同步，Linux渲染仍待服务器验证。
