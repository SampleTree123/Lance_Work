# Headshot 基础角色外观装配复用计划

> 文档 ID：`PLAN-2026-10-HEADSHOT-BASE-ASSEMBLY`
> 文档类型：`plan`
> 生命周期：`completed`
> 计划状态：`completed`
> 影响阶段：`WF-30`（CC 基础人物装配），`WF-40/WF-50`（后续导出及 UE 接入边界）
> 完成条件：实现精简装配入口并内置几何不变量检查，代表角色检查正确后可批量执行；记录可复现配置、颜色契约和失败恢复入口
> 最近核验：2026-10-05（R01–R06完成；单女性代表机器与中性/闭眼/微笑/张嘴人工接受，计划结项归档）

## 目标

复用现有皮肤、眉毛、睫毛、眼睛及材质代码，把已经完成 Headshot 面部创建、Average 身体及固定头皮修正的角色，装配成可供 UE 使用的基础人物。用户已确定路线1作为后续角色创建方向；本计划只接续第三步之后的外观装配，不重复路线对比，不将旧 UE 绝对位姿残差自动改判消失。

用户当前以赶下个月 CVPR 投稿为时间约束：优先形成可用流程，避免繁琐和重复验证。整个脚本完成后集中检查一个代表角色，正确后直接批量执行；不为每个角色重复视觉、表情、细分或重载检查。仅流程实质变化或出现实际异常时补针对性检查。批量保留轻量失败检测、日志和恢复记录。

本计划已执行完成并归档。真实CC capture self_check、独立photo01裸subd0副本代表v3机器装配/保存及用户中性/闭眼/微笑/张嘴审查均已通过，仅覆盖当前女性代表配置。wrapper及prepare-only已实测，尚未执行真实CC批量。导出、UE导入及渲染另立后续计划，本轮不执行。

## 输入与终点

输入是对应性别的第三步完成项目：CC5 Average 基线副本经 Current + Clean Soft 照片生成、最终头颈比例设置及身体/固定头皮修正。保留原始生成项目，在派生副本工作。

照片主要提供面部几何身份。用户接受用已有皮肤库替换照片生成的肤色及面部纹理，包括照片眉毛等细节；无需保留照片全部纹理。先替换完整皮肤，再接眉毛、睫毛及眼睛的标准装配。

终点是包含有效皮肤、眉毛、睫毛、眼睛、牙齿与口腔的基础人物项目；不携带头发、服装或表演动作。这三项在 UE 中装配。牙齿和口腔优先沿用输入项目的有效配置，缺图或异常时使用已有修复，不随机更换牙齿。

## 代码复用依据

- [装配执行器](../../../../../../../00_engine/scripts/character_creator/cc_validate_body_reconstruction.py)：`apply_appearance_assets()` 已接收现有 avatar 和资产列表；皮肤材质弹窗、Brow 部件替换、睫毛 Apply Morph / Apply Textures / Restore neutral lash strip、眼睛 Material Only 均已有实现。
- [随机配置编译器](../../../../../../../00_engine/scripts/character_creator/cc_compile_character_manifest.py)：复用 `stable_choice()`、`requested_component()` 和性别筛选；完整 `compile_facial_components()` 尚包含年龄、牙齿、胡须及头发，不能整段照搬。
- [基础外观池与颜色策略](../../../../../../../00_engine/scripts/character_creator/cc_facial_production_registry_v1.json)：已有皮肤、眉毛、睫毛、眼睛池及颜色配置。它仍属于旧完整装配结构，不直接改成新流程唯一机器权威。
- [外观 Technical](../../../technical/character_creator/APPEARANCE_ASSETS.md)、[Headshot Technical 10.6](../../../technical/character_creator/BODYFIT_IDENTITY_AGE.md#106-人工照片角色的独立副本后处理2026-10-04)、[组装 Technical](../../../technical/character_creator/ASSEMBLY_AND_ACCEPTANCE.md)为实施及来源所有者。
- `00_engine/scripts/character_creator/cc_assembly_geometry_invariants_v1.py`：R06 的纯离线比对层，无 RLPy 依赖，拥有全部分区阈值与通过/失败判定；复用 `cc_compare_headshot_geometry_v1.py:62` `stats()` 的统计键名以便两份报告并读。
- `00_engine/scripts/character_creator/cc_capture_assembly_geometry_v1.py`：R06 的 CC 侧捕获层，只读顶点并写元数据标记，不做任何判定；提供 `self_check()` 供接入前自检。
- 两者的离线单测为 `tests/test_cc_assembly_geometry_invariants_v1.py` 与 `tests/test_cc_capture_assembly_geometry_v1.py`。

## 需求与落实

| 需求 ID | 要求 | 影响 Workflow | 状态 | 验收条件 | 证据入口 |
| --- | --- | --- | --- | --- | --- |
| `R01` | 新入口直接接收修正完成项目，不再重建身体、旧 Face V3 身份或头颈比例 | `WF-30` | `completed` | 输入与输出独立；未重放旧身份/体型配方 | [WF-30状态](../../status/workflows/WF-30.md)；本Run Root `representative_v3/assembly_report.json`中的input lineage/source_unchanged及`representative_machine_completion.json`源/副本SHA核对 |
| `R02` | 复用皮肤、眉毛、睫毛、眼睛装配及已有材质设置；牙齿口腔沿用有效输入 | `WF-30` | `completed` | 精简顺序完整运行，不装配头发/服装/动作，不启用年龄编辑 | [装配Technical9](../../../technical/character_creator/ASSEMBLY_AND_ACCEPTANCE.md#9-headshot基础外观精简装配2026-10-05)；`representative_v3/assembly_report.json`六装配步骤、独立保存及机器终验；仅机器落实，人工pending |
| `R03` | 精简随机配置与毛发调色，支持 CC 只有眉毛而没有头发 | `WF-30/WF-50` | `completed` | 同种子可复现；不因缺少 scalp_hair 报错；颜色配置供 UE 后续消费 | `representative_v3/assembly_report.json`中的config种子/四颜色共享契约及eyebrow_pigmentation；`representative_machine_completion.json`target仅eyebrows；后续UE颜色执行未运行 |
| `R04` | 脚本完成后集中审查一个代表角色；批量不逐角色重复完整验证 | `WF-30` | `completed` | 代表角色整体装配正确；批量路径仅执行必要失败检测和保存 | representative_human_review_v2.json绑定保存SHA及本轮直接用户陈述：neutral/blink/smile/jaw_open及眉毛颜色accepted；仅当前女性代表配置，不外推男性/全池/真实batch |
| `R05` | 记录配置、资产选择、随机种子、结果与恢复入口，并同步文档 | `WF-30/WF-40` | `completed` | 可从失败角色继续，原项目不被覆盖；说明 CC 保存与后续 UE 交付边界 | [装配Technical9](../../../technical/character_creator/ASSEMBLY_AND_ACCEPTANCE.md#9-headshot基础外观精简装配2026-10-05)命令/恢复；wrapper_prepare_check.json实际prepare-only及26测试，base_assembly_regression_v1.txt完整442通过；base_assembly_documentation_audit.json实际16子系统/跨层通过零错误警告；批量未执行 |
| `R06` | 装配入口内置装配前后的网格顶点不变量检查，保护照片面部身份与固定头皮 | `WF-30` | `completed` | 代表角色与批量每个角色均产出分区偏差回执；固定头皮区、保留五官区、非头部区在阈值内；超限即停在具体装配步骤，不靠人眼兜底 | `representative_v3/assembly_geometry_invariants.json`8gate passed；`representative_machine_completion.json`13,460保护点0mm；`eyelash_geometry_diagnosis.json`及canonical exact704native lash policy，capture/invariants validated_pilot；不替代人工外观接受 |

## R06 几何不变量：为什么需要、分区与阈值

### 为什么现有保护不够

`apply_facial_assembly()` 已经对每个资产做前后检查，但它比对的是 **Morph 滑块权重**：`capture_vectors()`（`cc_validate_body_reconstruction.py:967`）读 `GetShapingMorphWeight()`，`evaluate_appearance_morph_policy()`（`:1224`）完全建立在这些权重差上。它看不见网格顶点。

这个盲区恰好落在本计划的输入上，有两重原因：

1. 本计划的输入角色经过几何修正与 Bake Morph Slider，形状存在于**烘焙后的顶点**里而非滑块值中 —— 本文「必要修改」第 1 条已经指出「形状正确却不保留旧滑块值」。
2. `capture_vectors()` 对 `abs(weight) <= 1e-8` 的滑块直接跳过。烘焙后多数滑块为零，可比对集合近乎为空，权重策略退化为近乎无效。

项目已有三次「属性正常但网格已变」的实测反例：原生烘焙在无活动滑块时改变 Body 局部网格最大 2.886 mm；固定头皮首次细分往返改变固定区 3.560 mm、保留五官区 2.555 mm；最高层删除重建同样改变低层网格。因此靠代表角色肉眼检查无法覆盖亚毫米漂移，而批量路径按本计划**不做逐角色人工审查** —— 若漏过，代价是整批角色作废。

R06 是让批量能够免除人工审查的**前提**，不是额外的审查负担：它是机器检查，秒级完成。

### 嫌疑步骤（已按代码核实，非按函数名推断）

| 装配步骤 | 几何风险 | 依据 |
| --- | --- | --- |
| 皮肤替换（含材质弹窗） | 低 | 材质域；既有同类断言为 0.002 mm 且已通过 |
| 眼睛 `Material Only` | 低 | ADR-0004 限定只用 Material Only；`apply_appearance_assets` 已校验 `material_changed_meshes == ["CC_Base_Eye"]` |
| 眉毛部件替换 | 中 | 走 `REPLACEABLE_AVATAR_PART_SLOTS`，换的是 mesh 部件 |
| 睫毛 `Apply Morph` | 待实测 | 现有 `eye_geometry_preserved` 只覆盖眼球部件签名，不覆盖头部网格 |

### 分区与阈值

分区复用 Clean Soft UV mask 划分，已落盘于 `headshot_fixed_scalp_20261002_v1/*_clean_soft_comparison/regions.json`（男女一致，CC3+ body 14164 顶点）：

| 区域 | 顶点数 | 阈值 | 依据 |
| --- | --- | --- | --- |
| `body_outside_head` | 9601 | 0.002 mm | `cc_headshot_route_validation_v1.py:949` 对「只换皮肤预设后 body 不得变化」的既有断言，同类操作 |
| `scalp_mask_zero` | 2741 | 0.002 mm | 同上；这是固定头皮修正区 |
| `face_mask_full` | 1343 | 0.002 mm | 同上；这是保留五官区 |
| `transition` | 479 | 0.002 mm | 同上 |

阈值下限为 0.001 mm：实测重复读噪声为 0.000305 mm（约 float32 在 150 cm 量级的 ULP），低于此只会产生假阳性，模块对此直接拒绝。

**坐标空间用 local（`GetVertices(False)`）作主判据。** 实测同一状态下非活动低层的 world 坐标偏 805.26 mm 而 local 差 0.0 mm、根变换相同（`inactive_world_query_guard_review_20261003_v1.json`）。world 比对仅在捕获方显式标记 SubD 0 时允许，沿用「CC 端写标记、离线端强制校验」的双向契约。

### 唯一留空的那格：眼睑带上界

睫毛 `Apply Morph` 可能**合法地**改变眼睑附近。该合法变化量只有在真角色上跑一次装配才能知道，预先拍一个数字必然导致第一个角色假失败。

因此 R06 的实施顺序是：

1. 先按上表对所有分区用 0.002 mm 跑代表角色，**不预设任何豁免**。
2. 模块输出超限顶点索引与位移（`worst_offenders`），据此判断变化是否聚集成眼睑形状的一簇。
3. 若确实聚集且由睫毛步骤引起，才以实测值 + 证据路径登记一条具名豁免（`allowances`），范围限于那组索引、带独立上界；全局放宽阈值不被接受。
4. 若未出现超限，说明装配根本不动几何，阈值表原样进入批量。

豁免机制默认为空。模块的单测覆盖了「豁免只作用于登记索引」「超出豁免自身上界仍失败」「冲突豁免被拒绝」三种情况。

### 初始离线验证与晋升边界（完整实跑进展见下文）

两个模块的离线单测为 42 项通过（`test_cc_assembly_geometry_invariants_v1.py` 22 项、`test_cc_capture_assembly_geometry_v1.py` 20 项，后者含一项端到端接缝用例）。这些测试**不在**既有 307 必要回归集合内，须显式运行：

```powershell
python -m pytest 00_engine/scripts/character_creator/tests/test_cc_assembly_geometry_invariants_v1.py 00_engine/scripts/character_creator/tests/test_cc_capture_assembly_geometry_v1.py -q
```

Script Catalog 中两个模块登记为 `experimental`，初始理由为「离线单测通过、从未在真实 CC 角色上运行」；代表v3实跑后capture/invariants现为validated_pilot，入口仍experimental。接入装配入口前先在已加载角色上运行一次 `cc_capture_assembly_geometry_v1.self_check(avatar, api=api)`：它只捕获并打印摘要、不写文件不改状态，用于在实跑前确认捕获正常。代表角色首次实跑才是该检查的真实检验，通过后方可将 lifecycle 升级并由 `ASSEMBLY_AND_ACCEPTANCE.md` 取得实现所有权。

## 颜色契约（R03 的落实细节）

R03 要求「颜色配置供 UE 后续消费」。字段现在就固定，避免 UE 侧实现时回头改 CC 输出格式导致已装配角色重跑。

### 不需要新造语义

现有 `hair_color` 就是这份共享契约的天然载体：眉毛与头发**当前取同一个值** —— `apply_shared_hair_pigmentation()` 在循环外算一次 `target_colors`，对 `scalp_hair` / `eyebrows` / `facial_hair` 三域写完全相同的四个颜色，域信息只参与计数不参与计算；registry 的 `pigmentation.shared_targets` 也明示共享语义。全仓不存在任何独立的眉毛颜色字段。

### 契约字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `hair_color.root_srgb` / `.end_srgb` / `.highlight_a_srgb` / `.highlight_b_srgb` | `#RRGGBB` 字符串，长度严格 7 | `pigmentation.palette[hair_color_id]` 的零变换深拷贝 |
| `visible_gray_fraction` | float `[0,1]` | 朝固定银灰 `#C4C7C9` 的线性插值比例 |
| `hair_color_id` | string | palette 键名（17 项），人类/审计可读溯源 |
| `hair_color_mode` | string | `natural_common` / `natural_rare` / `dyed` |

UE 侧消费时用同一公式即可得到与 CC 眉毛逐位一致的最终颜色：`lerp(color, #C4C7C9, visible_gray_fraction)`（实现见 `cc_validate_body_reconstruction.py:2826-2838`）。

两条实施注意：

- 契约存**语义字段名**（`root_srgb` 等），不存 shader 参数名。CC 侧的 `SMART_HAIR_COLOR_PARAMETERS`（`:368`）把它们映到 `RootColor` / `TipColor` / `_1st Dye Color` / `_2nd Dye Color`，这些是 `Digital_Human Hair` 专有名，UE 头发材质几乎不会同名，两侧各自做映射。
- 若 UE 侧要复现 highlight 的视觉权重，`SMART_HAIR_SCALAR_PARAMETERS`（`:374`）中的 `_1st Dye Strength = 0.35` 与 `_2nd Dye Strength = 0.35` 是硬编码常量、不在 manifest 里，需要一并进契约。

## 后续阶段（导出 / UE 导入 / 渲染闭环）的前提

导出基础人物、接入 UE 导入与小规模渲染闭环**另立新计划**，不追加进本计划，以免作用域漂移且完成条件无法判定。

该新计划的前提依赖一项尚未完成的核查：现有渲染管线消费的是第一批的**烘焙 FullReference** Look，而本路线产出的是「烘焙 combined base + UE 侧模块化发型/服装」的混合体；v003 当前仅为编辑器 JSON 读取作用域、打包运行时未验收；新参考人物的皮肤材质已更换为 `M_UnifiedSkin_PhysicalSource_v1`。待核项至少包括 Render Job 的角色引用方式、已验证动作能否用于新共享 Skeleton、Sequence 模板的绑定对象。

该核查应在**代表角色通过之后、批量之前**完成：若 UE 侧需要本装配未保留的输出内容，此时返工只影响一个角色；批量之后才发现则需重做全部。

另有一项与计划顺序无关的已知阻塞：GPU 驱动根因未修复，上一批导入是以 NullRHI 绕过 device removed 崩溃完成的，而 NullRHI 不能渲染，真实渲染必须图形编辑器可用。

## 必要修改及原因

1. **采用简化入口。** 旧主入口即使使用 source_project，也会先核对旧 BodyFit Morph 权重/指纹，并可能继续应用面部和比例；经过几何修正或烘焙的新角色可能形状正确却不保留旧滑块值。新入口只加载第三步完成项目并进入外观装配，不把旧滑块一致性作为新角色准入条件。
2. **缩减编排。** 不直接调用旧完整 `apply_facial_assembly()` 顺序；跳过年龄 Morph、动态皱纹扩展、牙齿随机替换、胡须和头发装配。不改变既有流程的默认行为，用新增入口/显式模式接续新角色。
3. **适配眉毛单独调色。** `apply_shared_hair_pigmentation()` 当前硬性要求 scalp_hair 和 eyebrows 两个材质域；新增目标域配置或眉毛专用调用。CC 只写眉毛颜色，同时保留颜色记录供 UE 头发装配使用；本计划不实现 UE 调色模块。

   精确位置与失败形态已核实：`required_domains = {"scalp_hair", "eyebrows"}` 在 `cc_validate_body_reconstruction.py:3070`。不装头发时 `avatar.GetHairs()` 为空，`domain_counts` 无 `scalp_hair` 键，抛 `ReconstructionError: No approved Smart Hair material was found for domains: ['scalp_hair']`。**该检查位于写入循环之后，因此不是原子的** —— 眉毛已被成功染色并完成回读校验，函数才在最后一刻失败，留下一个「已染色但报失败」的角色。上游 `apply_facial_assembly:6841` 还有一道：只要配置了 `eyebrow_asset_id`（新流程必配），`hair_color` 就不能为 None，必然进入该函数。所以这不是「可选的改进」，是新流程的硬阻塞，且失败后需要明确的恢复语义而非直接重试。
4. **精简选择器。** 复用稳定随机抽样及按性别过滤，只选择皮肤、眉毛、睫毛、眼睛和需要的颜色。不生成年龄、牙齿、胡须、头发和服装的执行任务。
5. **处理重复应用。** 旧代码有些分支把材质没有变化视为失败。能够确认目标资产已经应用时允许跳过；不以无变化为证据随意认定其他加载成功。
6. **分开装配与验证。** 跳过旧的大量截图、表情矩阵、细分往返和支持状态反复采集。保留资产加载返回值、必要部件存在、保存成功及错误日志；已知弹窗继续使用现有定向处理。避免不必要的 T Pose getter 与旧眼部诊断路径。

## 执行顺序

1. 本次已获执行授权，使用已验人工photo01裸subd0项目的独立runtime_staging副本作为代表输入；源项目保持，使用独立输出路径。
2. 建立精简配置生成器及装配入口，复用已有函数和资产池。
3. 接入 R06：先在已加载角色上运行一次 `cc_capture_assembly_geometry_v1.self_check(avatar, api=api)` 确认捕获正常，再在装配入口的装配前后各捕获一次，用 `compare_assembly_snapshots()` 判定，失败即停在具体装配步骤。
4. 按“皮肤 → 眉毛 → 睫毛 → 眼睛材质 → 眉毛颜色/基础材质设置 → 保存”执行。输入牙齿/口腔保持，有实际异常才调用已有修复。
5. 如装配涉及必须处理的形状状态，实施时确定一次必要的最终整理位置；不默认重做已经完成的几何修正或逐角色细分检查。
6. 集中检查一个代表角色的整体外观、五官保持、眉睫及代表表情。正确后进入批量；不预先展开所有资产交叉验证矩阵。同一代表角色的 R06 回执用于确认阈值表，必要时据实测登记眼睑带豁免。
7. 代表角色通过后、批量之前，完成「后续阶段的前提」节所列的 UE 管线核查；若需要本装配未保留的输出内容，此时补齐只影响一个角色。
8. 批量按角色保存配置和成功/失败记录，失败定位到实际步骤；按失败 ID 恢复，不重跑完成项。每个角色保留 R06 回执。
9. 记录可执行命令、配置字段与输出入口，更新拥有这些实现的 Technical、WF-30 状态及计划落实。R06 两个模块在代表角色实跑通过后方可从 `experimental` 升级并登记实现所有权。导出/UE 接入按后续任务执行，不由计划登记自动启动。

## 不包含

- 本轮已授权创建、修改并运行精简CC装配脚本；导出、UE导入和渲染另立计划，本轮不执行。
- 不重新生成照片角色，不重复两条路线对照，不重建规范头型。
- 不在 CC 装配头发、服装或表演动作，不启动80套发型导出。
- 不加入年龄/妆容/胡须多样性扩展，不覆盖正式 UE 资产。
- 不为每个角色执行完整的视觉、表情、细分、重载或导出对照，不展开旧资产池的新全量兼容矩阵。
- R06 通过不等于外观合格：它只断言所列分区在所选坐标空间内的几何未漂移，不替代代表角色的人工外观与表情判断，也不覆盖动态、任意身份或隐藏面。
- 本计划不实现 UE 侧的头发调色模块，只固定颜色契约字段；也不改动 `apply_shared_hair_pigmentation()` 之外的既有染色行为。

## 风险与停止条件

实际加载失败、未知阻塞弹窗、必要部件缺失或保存失败时，记录具体角色和步骤，处理实际异常。已完成角色不重做完整验证。代表角色发现面部/头皮被装配改动或严重外观问题时，仅定位相关装配步骤；修复后复查代表角色，不自动扩大验证规模。

代码可复用性已通过静态阅读确认；新的完整组合尚未实际运行。此前 CC/UE 验证不冒作本计划执行证据。旧严格 UE 位姿残差保留为已知交付议题，不在此计划中增加逐角色比较任务。

## 完成与迁移条件

R01–R06 必需需求完成、代表角色被接受、批量入口及恢复方法可执行并有轻量结果记录后，同步 Technical/Workflow Status。本计划执行时为唯一current，R01–R06现已完成并迁入completed history；无新任务获授权，项目显式空闲且不自动晋升其他计划。

## 本次执行入口与状态（2026-10-05）

Run Root：`%OUTPUT_ROOT%/character_creator_bridge/artifacts/headshot_base_assembly_20261005_v1/`，归[装配Technical](../../../technical/character_creator/ASSEMBLY_AND_ACCEPTANCE.md#9-headshot基础外观精简装配2026-10-05)和`OUT-WF30-CC-ASSETS`。计划中的`cc_run_headshot_base_assembly_v1.py`及`cc_compile_headshot_base_assembly_v1.py`为待实跑实验入口；捕获/不变量模块仍experimental，不凭离线42单测升级。首先真实CC self_check，再代表装配回执及集中外观审查；当前不报告任何本计划需求通过。颜色仅写眉毛，保留hair_color共享契约供后续UE阶段消费。

真实CC捕获`self_check`已通过：已加载女性photo01裸subd0，14,164顶点、128 scalar checks，numpy可用；证据为`%OUTPUT_ROOT%/character_creator_bridge/results/base_assembly_geometry_self_check_20261005_v1.json`。此自检只打印摘要并保留Bridge终态，不生成角色捕获文件，不作为R06整体验收或代表装配通过。load v1被Bridge输入allowlist拒绝，v2从runtime_staging独立副本成功加载，源SHA保持；失败尝试保留。装配执行器已创建，代表完整装配仍pending，模块继续experimental；按每一步对原始输入0.002mm、无豁免检查，失败恢复输入。

### 代表v1实际失败与恢复（2026-10-05）

`representative_v1/assembly_report.json`为真实`phase=failed`、`source_unchanged=true`、`recovery.status=restored_input`。皮肤`Age23-LorenaBuchanan_2k`及眉毛`Female_Untamed`两步的四分区均逐点0.0mm，通过对应局部几何检查。`Lush_Extended`睫毛在旧`Apply Morph`路径后的`apply_eyelashes`检查被拦截：`scalp_mask_zero`有704顶点超0.002mm、最大约8.1476mm，其他三分区仍0.0mm。此分区是Clean Soft零mask区，含头皮、耳与颈，不能仅因名称就认定为纯头皮或眼睑变化。

证据为本Run Root的`representative_v1/{assembly_report.json,assembly_geometry_invariants.json,before_geometry.json,apply_eyebrows_geometry.json,apply_eyelashes_geometry.json}`。后续眼睛材质、眉毛染色及Save未执行；没有成功基础人物输出。实际捕获/比对与失败恢复路径已有证据，R06整体仍in_progress且不变量回执passed=false，代表完整装配/外观接受未通过，所有相关新模块继续experimental。正在只读定位具体超限索引簇，眼睑合法上界未定、allowances仍为空；不得全局放宽阈值或把8mm变化当作可接受漂移。

离线新子范围实际测试：compiler22、pigment22、原R06模块42合并86通过；runner8单独通过。它们不代替真实CC完整装配通过，也不继承旧307回归为本次完整终验。

### 原生睫毛片的精确具名规则（代表v2待实跑）

`eyelash_geometry_diagnosis.json`通过CC5安装资源`Resource/CCHeadshot/BlendShape/G3Plus_Eyelash_for_Male.obj`的精确material faces证明：v1全部704超限点均属于`Std_Eyelash`，native/reference Body的面集合拓扑一致，全部Skin材料顶点位移0mm。因此它们是原生睫毛片的合法外观装配形变，不是眼睑皮肤、头皮或身体变化。v1无豁免失败及恢复原样保留；不能追溯改写为通过。

本节拥有`00_engine/scripts/character_creator/cc_base_assembly_geometry_policy_v1.json`，仅对`Lush_Extended / CCAPP_EYELASHES_284c3a142668`登记`native_lash_strip_Lush_Extended`、确切704indices及8.2mm上界（实测8.147572mm+0.05mm后向上取0.1mm）。规则绑定诊断证据SHA；执行器核对canonical policy路径、SHA、证据及准确asset匹配，编译器显式optional `geometry_policy_path`才消费。其余索引、分区、资产和所有皮肤保持0.002mm，未全局放宽或登记眼睑皮肤豁免。

代表v2计划使用同source/seed、只变规则及outputroot完整重跑；当前v2pending，捕获/比对/执行器仍experimental，完整装配与代表接受尚未通过。`future_ue_interface_review.json`只读核查认为本CC输出契约足以规划后续接口；它没有执行UE，不是导出、动画或渲染验收，本轮后续阶段操作仍不启动。

### 代表v2失败与眼睛Material Only的精确幂等证明

`representative_v2/assembly_report.json`真实failed于`apply_eyes:appearance_asset`，原因是`Eyes_01 / CCAPP_EYES_9a42ba5420b0`与输入现有眼睛资产相同，旧逻辑仍硬性要求材质fingerprint变化；源SHA保持且已`restored_input`。v2皮肤、眉毛和睫毛三步R06均passed，其中睫毛片仅在上述证据绑定704indices具名上界内通过；完整装配、眉毛染色和Save没有由此通过。v1/v2失败原样保留。

`cc_validate_body_reconstruction.py`新增独立`appearance_eye_material_noop_verified`证明及`apply_appearance_assets(..., allow_verified_material_noop=False)`显式opt-in。旧默认仍False，仅新精简入口启用True；只针对eyes/.ccEye且asset SHA核验、SDK returned=true/is_error=false、精确Material Only弹窗clicked_count=1、眼球几何/支持配置保持、两次非空材质fingerprint完全一致，才允许no-op成功。non-eyes、无效返回、漏点击、空指纹、几何/支持变化均不豁免，不能泛化为“没有变化就算成功”。实现复用Owner仍为本文与[外观Technical](../../../technical/character_creator/APPEARANCE_ASSETS.md)，新增调用边界由本节拥有。

`representative_v3/assembly_report.json`为同source/seed的真实已提交新尝试，当前运行中；未取得终态不能写完整通过或保存成功，模块仍experimental。最新定向测试compiler33、颜色22、原capture/invariants42及runner12共109项通过，后续no-op证明测试另行记录；不代替本次完整CC/视觉接受。

### 代表v3完整机器装配成功，人工审查仍待确认

Bridge终态`%OUTPUT_ROOT%/character_creator_bridge/results/base_assembly_representative_20261005_v3.json`成功；本Run Root的`representative_v3/assembly_report.json`为`success=true/phase=completed_awaiting_representative_visual_review/source_unchanged=true`，`visual_acceptance=pending`。独立保存`representative_v3/ASSEMBLED_female_photo01.ccProject`，106,531,576bytes，SHA`838f5abd083b32d239ae153e63fa94aa785e7bc5e412a0b67d88cd0baec41d70`；原输入项目不变。

`assembly_geometry_invariants.json`的8个gate（skin、brows、lashes、eyes、eyebrow_pigmentation、face_material_quality、pre_save、post_save）全部passed。所有Skin顶点0mm，仅704个native Std_Eyelash顶点约8.147572mm、在登记8.2mm具名边界内，其他阈值0.002mm不变。眼睛`material_noop_verified/material_only_verified=true`，眼球几何/支持保持；眉毛调色`target_domains/required_domains`都仅`eyebrows`，没有scalp_hair域要求。本结果只证明一个女性代表输入、这一配置的完整机器装配与保存，不自动形成用户外观/表情接受或全资产池成功。

R01/R02/R03/R06技术落实completed，R04人工代表审查pending，R05批量恢复入口、必要回归和文档审计in_progress，计划仍唯一current。实际捕获/不变量检查模块可记`validated_pilot`；编译器和装配执行器仍experimental，直到代表人工结论及剩余交付收口。批量wrapper正在编写，尚未执行批量，不覆盖原项目、不重做已完成角色。前序v1/v2失败保留；后续导出/UE导入/渲染仍未执行，futureUE只读核查未要求本CC输出变更，不能当作后续运行接受。

本次完整要求回归已实际通过442项（116.50秒），证据`%OUTPUT_ROOT%/character_creator_bridge/artifacts/headshot_base_assembly_20261005_v1/base_assembly_regression_v1.txt`；包括原必要集合及新增R06/compiler/color/runner/no-op范围，不把先前定向测试冒作完整回归。root已重建Script Catalog与Output Inventory；capture/invariants实际分类validated_pilot，compiler/CC runner/未完成wrapper仍experimental。wrapper和本次文档审计未完成、人工代表审查仍pending，R05继续in_progress，不关闭计划。

系统Python wrapper已完成，26实际测试通过（3.41s），真实prepare-only smoke两次复用同attempt/job、源SHA保持且cc_submitted=false；没有执行批量。代表终验`representative_machine_completion.json`重新核对13,460保护点0mm、704原生睫毛片、8gate零失败及原/sourcecopy/saved SHA；R04人工pending，R05恢复入口技术落实、最终文档审计仍待root，计划保持current。

调度器实现及命令/恢复边界见[装配Technical9](../../../technical/character_creator/ASSEMBLY_AND_ACCEPTANCE.md#9-headshot基础外观精简装配2026-10-05)。wrapper为`00_engine/scripts/character_creator/run_headshot_base_assembly_v1.py`，当前experimental；R05整体in_progress，不能以prepare-only成功写批量执行或结项。

### 用户中性外观部分接受，表情检查待确认

用户已在当前CC观察代表v3女性角色，直接报告大体无问题、中性各部件正常；尚未检查微笑等代表表情，因此仅登记当前单个女性代表的neutral appearance accepted。R04部分落实、表情pending，不写整个代表审查或计划completed，也不推断男性、批量、全外观池或动态接受。此结论来源为本轮直接用户陈述，不伪造表情检查或逐项按钮记录。

用户另询问眉毛是否为金色。装配回执的RootColor读回`[0.301960796, 0.113725491, 0.094117649]`对应`#4D1D18`，Tip为`#8B4430`，配置为auburn赤褐色，并非gold；眉毛目标/required域仅eyebrows。记录材质颜色写入/读回正确，暂不由参数正确推断画面显金色的原因或额外视觉结论。用户可在CC的`Modify > Motion Pose > Edit Facial > Expression`查看微笑等代表表情，操作/观察结论需用户继续确认。

本次最终文档审计`base_assembly_documentation_audit.json`实际success=true，16独立子系统及cross-layer全部通过、0error/0warning；Script Catalog及Output Inventory已实际重建。R05恢复/配置/日志/回归/文档技术交付completed，计划仍唯一current。当前仅R04代表表情人工审查pending；中性外观已直接用户接受，未执行批量、导出或UE工作，compiler/runner/wrapper继续experimental。

独立人工记录`representative_human_review_v1.json`绑定本轮直接用户陈述与已保存代表项目SHA：neutral accepted，blink/smile/jaw pending、overall partial。它作为R04当前人工来源，原`representative_machine_completion.json`机器终态历史不改写。

## 结项范围

R01–R06completed。最新人工依据为representative_human_review_v2.json，绑定保存项目SHA与用户原话；原v1 partial及v1/v2装配失败保留历史。compiler/CC runner/capture/invariants为validated_pilot的代表实跑范围；系统wrapper仍experimental，仅测试与prepare-only，未实际提交CC batch。完整442回归、wrapper26单测及16子系统/跨层文档审计通过。无男性/任意身份/全外观池/真实批量或导出UE渲染接受。无新任务获授权，current_plan_id=null、idle_after_completed_plan，下一步等待用户选择/授权独立导出及UE接入/渲染计划。

结项要求回归`closure_regression_v1.txt`实际307passed（36.06s），与前阶段442及wrapper26分开追溯，不合并虚构新总数。归档导航终验`closure_documentation_audit_v1.json`实际16独立子系统及cross-layer全部通过，0error/0warning；不重复CC/完整测试，也不扩大单女性代表接受或宣称真实batch/UE通过。
