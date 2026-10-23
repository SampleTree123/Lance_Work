# BodyFit、身份与年龄

> 文档 ID：`TECH-CC-01`
> 文档类型：`technical`
> 生命周期：`current`
> 适用阶段：`WF-20/WF-30`
> 实现所有权：BodyFit Library、Face V3 Registry、Headshot Registry、年龄策略与CC统一创建/修正pipeline
> 验证所有权：`VAL-MATRIX-01`（BodyFit/Identity 子项）、`VAL-CC-01`
> 输出契约：`OUT-WF20-ASSET-MATRIX`、`OUT-WF30-CC-ASSETS`
> 最近核验：2026-10-05（统一CC创建两入口机器pilot与恢复完成；归档16独立/跨层终验通过）

## 1. 能力与边界

身体、面部身份和年龄是三个独立概念。BodyFit 从哈希锁定的规范 `.ccProject` 加载；其初始脸只作为加载状态，随后由身份流程替换。不能把几条大 Morph 权重视为完整项目的唯一可逆存储。

## 2. 当前机器入口

| 文件 | 作用 | 状态 |
| --- | --- | --- |
| `cc_body_preset_library_v2.json` | 10 个成人 BodyFit、源项目、Body/Junction 指纹和验证 | `production` |
| `cc_build_body_preset_library_v2.py` | 从已接受项目生成/迁移 Library | `utility` |
| `cc_face_seed_library_v1.json` | 原始 Face Seed | `validated_reference` |
| `cc_face_recipes_v3_200.json` | Face V3 配方池 | `production` |
| `cc_generate_face_recipes_v3.py` | Face V3 确定性生成器 | `utility` |
| `cc_build_first_batch_identity_library_v1.py` | 从集成 Manifest、BodyFit 和头身决定冻结第一批 8 个 Identity | `production` |
| `cc_headshot_face_prototype_registry_v1.json` | Headshot 烘焙原型候选 | `validated_pilot`，未进入第一批生产 |
| `cc_headshot_skull_profile_library_v1.json` | 四个已选头型 Profile | `validated_pilot` |

所有路径相对于 `%CC_SCRIPT_ROOT%`。

## 3. BodyFit 规则

- 当前成人库为女性/男性各五个，包括 lean、average、athletic、heavy 和 short-average。
- 规范源是 `.ccProject`，运行时先校验字节数、SHA-256 和 Body/Junction Fingerprint。
- Body/Junction 向量用于漂移检测和审计，不替代源项目加载。
- Head Scale、Neck 和短体型修正已被烘焙或登记在 Library；生产不重新猜测滑块。
- 新增体型必须通过静态比例、身高、头身、眼口、服装和动作兼容验证。

## 4. Face V3 规则

Face V3 使用已接受 Seed 和受控局部 Morph 生成身份变化：

1. 加载主原型的完整面部支持状态。
2. 只修改允许随机化的局部 Morph。
3. 不把未知眼口支持参数批量清零。
4. 口部 Macro、牙齿/口腔和极端眼形需要成对验证。
5. 配方保存 Seed、局部权重、随机种子和版本，不保存模糊的“长得像某人”描述。

## 5. Headshot 边界

Headshot 项目需要保留烘焙身份项目、CC5 HD Facial Profile、来源照片、头型 Profile、哈希和动态检查。当前已验证从 CC3+ 项目升级和 project-seed + BodyFit 路线，但生产启用数仍为 0；第一批继续使用 Face V3。

四个头型候选为 Base、Long Deep、Low Flat、Narrow Shallow。它们是低频头骨 Profile，不应覆盖身份局部 Morph。

## 6. 年龄

- 年龄是可选变体，不要求每个身份都生成老年版本。
- 静态年龄 Morph、皮肤年龄和动态皱纹是不同通道。
- 青年皮肤可通过受控面部年龄 Morph 生成中/老年变体；本身老年皮肤不再叠加强老化层。
- 正式年龄编辑还需身体年龄、毛发、服装和动态表情共同验收；第一批不启用。

## 7. 验证与输出

当前权威输入本身属于 `authoritative`；配方生成结果和动态门禁为 `retained_evidence`；轴扫描中未入选图为 `superseded/disposable`。新身份至少检查中性、闭眼、微笑、张嘴、左右侧和重载一致性。

历史及当前 BodyFit/Face 运行输出统一归本能力解释，当前盘点根为：

```text
%OUTPUT_ROOT%/character_creator_body_preset_validation/
%OUTPUT_ROOT%/character_creator_face_recipes/
%OUTPUT_ROOT%/character_creator_face_recipes_v2_1/
%OUTPUT_ROOT%/character_creator_face_recipes_v3/
%OUTPUT_ROOT%/character_creator_face_seed_validation/
```

这些根当前只完成 owner 登记；除 Retention Policy 精确列出的路径外，不得从目录名推断可删除性。

执行器由 [CC 组装与验收](./ASSEMBLY_AND_ACCEPTANCE.md) 调用，历史实验细节保存在重构快照中，不作为生产入口。

## 8. 失败与恢复

源项目哈希、Body/Junction 指纹或身份支持状态不一致时停止该角色，不自动重算“接近”的滑块值。先恢复被锁定的源项目或为调整结果创建新 BodyFit/Identity 版本，再从干净项目重建并重复动态门禁。Headshot、年龄或实验 Morph 失败不得回写当前 Face V3/BodyFit 生产 Registry。

## 9. 固定头皮实验与照片自动生成

2026-10-02 核验本机 CC `5.02.0923.1`、界面 Headshot v2。用户在完成女性 B 后授权独立比较女性 A/B、自动生成两名 Male + Clean Soft 男性，并在发现头型差异时探索修正。该授权替代此前“等待 B、禁止继续生成”的临时状态。原始项目保留，所有修改仅在独立候选中执行；不重启离线 CC、不修改正式 UE 库。

### 9.1 实现、配置和来源

执行器 `%CC_SCRIPT_ROOT%/cc_validate_body_reconstruction.py` 经 Bridge 的 `validate-bodies` 进入，支持 `headshot_api_probe`、`headshot_photo_generation_probe`、`headshot_mesh_level_probe`、`headshot_current_measurement`、`headshot_mesh_replace_probe`。本轮实验模式跳过旧原生 Undo 辅助器；出现弹窗或观察超时先读取结果和现存作业，不重复提交。

后续统一 **Clean Soft**。本机 `Resource/CCHeadshot/TexturePresetG3Plus.ini` 的 `Preset2` 是实际映射依据：`Name=Clean Soft`、`Base0=Soft Skin`、`Mask0=Default Even`、`Mask1=Minimum Eyelid Rim`。SHA256 为 `d3db9a43de2dbd9e0861ac74264fa1d853422d51e18087d62fdec3a980a44943`。API 设置 `strSkin=Soft Skin`、`strFaceMask=Default Even`、`strEyelidMask=Minimum Eyelid Rim`，其余保持 None；`strBread` 是本机 API 的实际拼写。代码校验本机预设映射并拒绝没有 `skin_preset=Clean Soft` 的旧工单。

`RHeadshot.CreateHeadFromPhoto(photo, EHSMode_Pro, option)` 已实际工作。`eBodyType` 按工单设 Female/Male/Current；Male/Female 使用 Headshot 标准身体，**不等于项目 F02/M02 Average 已验证保持**。此前 Soft Skin + No Mask 的早期样本仅为历史实验，不能充当 Clean Soft 对照。Current 在早期 Average 项目上的异常求值也不能外推成整个 API 不可用。

当前实验 Run Root 为 `%OUTPUT_ROOT%/character_creator_bridge/artifacts/headshot_fixed_scalp_20261002_v1/`（下文 `R/`），输入工单为 `%CC_SCRIPT_ROOT%/runtime_staging/headshot_fixed_scalp_20261002_v1/`。输出归 `OUT-WF30-CC-ASSETS`，本文为 owner，Inventory 默认保护，未晋升到生产资产。

女性 `R/manual_clean_soft_A/`、`R/manual_clean_soft_B/` 保存用户手动生成的原始项目副本、OBJ、网格、Morph（含零值）、骨骼和世界变换；Clean Soft 来源为用户操作确认，并非 API 反读。男性 `R/male_clean_soft_01/`、`R/male_clean_soft_02/` 保存自动生成及重载报告，照片分别为 CFD 的 `WM-252/CFD-WM-252-224-N.jpg`、`BM-001/CFD-BM-001-014-N.jpg`，路径和 SHA 在各自报告中。

### 9.2 测量方法与结论

离线工具 `cc_compare_headshot_geometry_v1.py` 检查 14164 顶点的 CC3+ Body、相同面拓扑与 UV；本机 `CreateHead.ini` 的 `G3Plus_HeadVertices` 为一基索引，转换后得到 4563 个头部顶点。`Mask_Even_High_Features.png` 是 LA 图，使用 alpha 而不是全白的 L 通道分区：零区 2741、完整面部区 1343、过渡区 479。零区包含头皮、耳朵及部分颈部，**不是最终解剖头皮掩码**。

不得混用 `GetVertices(False)`、`GetVertices(True)` 与 OBJ 导出的不同坐标/姿态。`False` 为局部网格；`True` 为当前世界姿态；本次 BodyPart OBJ 是另一组求值/姿态坐标。世界坐标比较仅校正角色根平移，不用头部最佳拟合隐藏实际大小差异。可选变换 `d_error` 字段不参与比较。

| 测量（OBJ 同口径，最大顶点位移） | 女性 A/B | 男性 A/B |
| --- | --- | --- |
| 完整头部 | 5.116 mm | 19.477 mm |
| 零遮罩头部区域（含耳/颈） | 3.892 mm | 18.936 mm |
| 头顶向下 10 cm 内的零遮罩区域 | 3.892 mm | 9.935 mm |

因此同一 Body Type + Clean Soft **不锁定头皮几何**。头部 Morph 为零或相同也不能证明烘焙几何相同。测量报告及交互几何图在 `R/female_clean_soft_comparison/`、`R/male_clean_soft_comparison/`。

### 9.3 修正实验及失败边界

`cc_build_headshot_scalp_target_v1.py` 从 A/B 的 `before_world_mesh.json` 与 `before_body.obj` 构造目标：零遮罩头部顶点使用 A，完整面部顶点保留 B，过渡区按 alpha 混合，其余身体顶点保留 B。只矫正根平移，要求根旋转/比例和拓扑相同。工具保留 OBJ 分组、UV、面索引并输出输入 SHA；复现目标的顶点、UV、面拓扑已与实际工单一致核验。

`headshot_mesh_replace_probe` 从 SHA 锁定的实验项目副本加载，模式包括 `capture_only`、`hair_capture`、`world_identity`、`normalized` 及保留的失败诊断模式。`RIMesh.ReplaceMesh(path, EReplaceMeshOption_ZUp, False)` 要求当前姿态世界坐标：直接使用 BodyPart OBJ 或局部顶点虽然可能返回成功，却曾导致约 1 米/0.8 米错误，**API success 不是几何通过**。这些失败项目不应复用。

世界坐标原样替换消除了大幅形变，但逆蒙皮重建仍有约 1 mm 误差。`refinement_iterations` 限定为 0..3：每次保存重载后，计算目标世界顶点减实际顶点的残差，加回提交顶点，再替换、保存重载；当前两性各一次修正即小于 0.005 mm 的停止阈值。

实际候选 `R/female_fixed_scalp_v2/replacement_candidate.ccProject` 与 `R/male_fixed_scalp_v2/replacement_candidate.ccProject` 已保存重载。相对指定世界目标的最大误差分别约 0.00123/0.00077 mm。另以导出 OBJ 独立核验：女性/男性完整面部相对 B 的误差分别约 0.00046/0.00061 mm，保留了原有五官差异；非头部相对 B 均小于 0.002 mm。零遮罩头部相对 A 的导出误差约 0.0073/0.0406 mm，男性残余主要在颈部；上部头皮分别约 0.00231/0.00015 mm。世界目标与导出误差是不同口径，不能混称全部完全相同。

### 9.4 同一发型的几何证据

`cc_assess_headshot_hair_clearance_v1.py` 对 HB3-17 Sleek Deep Side Part 进行固定发型检查：只在 A 上加载一次发型，读取当前世界网格，然后对 A、B 和修正 B 计算同一批发型顶点的最近头部三角面间隙，不在 B 上重新加载自动贴合后冒充通用资产验证。

上部零遮罩区、在 A 外侧 0.1..5 mm 的候选点中，女性/男性分别有 57/102 个点在 B 上新进入头皮至少 0.5 mm；最深约 1.09/2.10 mm，修正后新增相交点均为 0。示例点及原始数组、SHA、可旋转几何图在 `R/female_hair_clearance_v2/`、`R/male_hair_clearance_v2/`。距离算法的平面内、边、顶点和正负侧解析用例通过；对新相交点扩大三角面候选搜索也一致。

这是**网格层证据**，采样包含 Hair/Scalp 发片，不计算材质透明度；不能声称 57/102 处都是肉眼可见穿模，也不证明全 40 款发型、表情或动态已通过。CC 窗口当时最小化且 Computer Use 无法激活，本轮没有新增带材质的视觉验收图；几何 HTML 不冒充渲染图。

### 9.5 复现、输出和下一 Gate

离线三个工具只依赖本机 NumPy、Pillow、Plotly；间隙计算用 NumPy，避免当前 SciPy/NumPy ABI 不兼容。先用 `capture_only` 从原始保存项目生成世界网格与 OBJ，再运行目标生成器，记录目标文件 SHA，把 `source_project`、`replacement_obj` 和 `refinement_iterations=3` 写入 `headshot_mesh_replace` 工单，按以下入口提交到新的空输出目录：

```powershell
python 00_engine/character_creator_bridge/cc_bridge_client.py validate-bodies --library-file 00_engine/scripts/character_creator/runtime_staging/headshot_fixed_scalp_20261002_v1/female_fixed_scalp_v2.json --output-dir <新的空运行目录> --confirm-scene-replace --job-id <唯一作业ID> --no-wait
```

离线工具参数：`cc_compare_headshot_geometry_v1.py --a <OBJ-A> --b <OBJ-B> --output <目录>`；`cc_build_headshot_scalp_target_v1.py --a-dir <A捕获目录> --b-dir <B捕获目录> --output <目标OBJ>`；`cc_assess_headshot_hair_clearance_v1.py --root <R> --sex female --fixed-dir female_fixed_scalp_v2 --output <新目录>`。男性将 sex 与目录前缀改为 male。汇总入口 `R/overnight_geometry_summary.json`，不是生产 Registry。

人类审查入口为 `R/review.html`，其链接均为本地交互网格图。`R/completion_audit.json` 按本次调查要求核对证据，并检查四个原始样本及两个修正项目 SHA；`R/documentation_audit.json` 记录独立子系统/跨层审计，`R/regression_tests.json` 记录必要回归测试及排除的视觉/动态边界。

本轮完成“正确配置的男女对比 + 修正方案探索”。正式 Plan R02/R03 仍未完成：需要将临时纹理分区收敛成解剖头皮接触区，核验 Average 身体、头颈骨骼/表情动态、带透明材质的视觉效果，再晋升规范源。尚未导出新的 80 套发型，也没有修改正式 UE 资产。

官方参考（2026-10-02）：[图像模式 Body Types](https://manual.reallusion.com/Headshot_for_CC/ENU/1.0/ID_GC_BT_Pro.html)、[Skin Types](https://manual.reallusion.com/Headshot_for_CC/ENU/1.0/ID_TA_ST_Pro.html)、[CC5 Replace Mesh](https://manual.reallusion.com/Character-Creator-5/Content/ENU/5.0/09-Pipeline/Replacing-Mesh.htm)。API 实际参数以本机 SDK、预设 INI 和作业报告为证据。

## 10. Headshot 正式路线对照验证

2026-10-02 用户授权优先验证 CC5 Average → 生成前 SubD 0 → Current + Clean Soft；另用相同照片独立验证默认 CC3+ Male/Female → Clean Soft → CC5 面部动画配置 → Average BodyFit/头颈比例。男女各两张照片，共八个独立实验，不覆盖规范资产，不重启或联网，不执行 80 套发型导出。两条路线均通过时优先步骤更少且稳定保留身体的路线 1。

本轮 Run Root 为 `%OUTPUT_ROOT%/character_creator_bridge/artifacts/headshot_route_compare_20261002_v1/`，下称 `R2/`。`route_matrix.json` 保存照片、SHA、路线和工单入口。工单位于 `%CC_SCRIPT_ROOT%/runtime_staging/headshot_route_compare_20261002_v1/`；每个 `r{路线}_{性别}_{照片序号}` 独立保存 `generate/`、`validate/` 及后续几何、头皮和发型证据。输出 owner 为本文，映射 `OUT-WF30-CC-ASSETS`，默认保护。

执行器仍为 `cc_validate_body_reconstruction.py`。生成模式新增 `pre_generation_subdiv_level=0`，先切换、强制求值并反读，再调用 Headshot；保留生成前 Average OBJ、生成后和重载网格、原始项目、选项、预设及照片 SHA。不能把生成后才设为 0 当成同一测试。

`headshot_route_validation` 调用 `cc_headshot_route_validation_v1.py`：记录源和最终身体 OBJ、眼睛部件与骨骼、材质指纹、CC5 配置、细分、保存重载；路线 2 先加载相应 HD Neutral Facial Profile，再应用历史 BodyFit 和头颈设置；输出闭眼、三级微笑、张嘴和恢复中性的证据。代码成功只表示证据采集完成，几何和图像必须另外审查。

当前验证进行中，尚无正式路线接受结论。路线 1 四次生成均保存重载成功；首个女性样本的 CC5 MetaHuman 379 项配置和五种表情响应已采集。Current 保留 Average 灰模中的眼睛/牙齿外观，因此试验副本另加载既有 Eyes_01 与 HD Teeth 2K，弹窗选择 Material Only，不据灰眼睛现象推断部件丢失。原始灰模、补材质前后均保留。RenderImage 的旧方形视口设置与实际原生画幅不一致，会压缩人物比例；本轮新增 `render_image_native_aspect`，保留实际视口尺寸并按原比例归一化图片。`R2/capture_calibration_v1/native_aspect_front.png` 已完成颜色与比例复核。此前 pixel_stream 试验产生颜色通道疑点，且 CC 在 18:52:45 的预览阶段崩溃，事件记录指向 d3d11.dll；仅凭模块与时间不能确定根因。该模式本轮停用，崩溃转储和事件保留在 `R2/incidents/cc_d3d11_20261002_185245/`。用户于 18:54 重新打开离线 CC 后恢复，未由代理重启。

复现提交沿用第 9.5 节的 `validate-bodies`，工单选 `R2` 对应 generate/validate JSON，输出必须使用新的空目录和唯一 job ID。提交前检查 heartbeat 和已有 results，不能因耗时重投。2026-10-03 用户先停止 Computer Use，随后明确重新授权“必要时使用，用完停止”；当前优先 CC API/后台脚本，界面核验或必须处理的弹窗才短暂使用 Computer Use，完成即停止输入。固定头皮实验允许的输入根仅为第 9 节根和本节 `R2`，输入仍由 SHA 限定。

`cc_summarize_headshot_routes_v1.py --root <R2>` 从已有报告和源文件 SHA 重建 `route_progress_summary.json` 与 `route_matrix.json` 的证据采集状态。它对生成、保存重载、细分往返和材质补全分别比较实际网格；高度分段只用于定位差异，不冒充解剖身体验收掩码。中断于预览但已保存的候选先核对 SHA，再使用独立验证工单，不重复生成或回写原报告成功标记。

`headshot_route_validation` 的 `operation=eye_snapshot_probe` 已在 `R2/eye_snapshot_probe_v1/` 实测：两个眼骨骼的 `Update` 即时返回，前后变换相同；分别调用 `GetBoneTPosePosition` 时均切入 Adjust Bones 并弹出精确 Undo Manager 警告，人工确认后才返回。探针前后 Body OBJ 最大差异约 0.0190 mm，不能把该查询视为完全无副作用的读取。这定位了本次重复警告的触发调用，不等于已修复 CC 的所有 Undo 故障。

本轮实验工单可显式设置 `eye_snapshot_mode=transforms_only`：继续读取眼睛部件、Eyeball Move、local/basis/world 变换、动画状态和实际网格，但不调用该 T Pose getter；报告标记 `not_sampled_sdk_modal_side_effect`，不伪造 T Pose 值。仅两个输入都明确采用该模式时比较器才排除该字段，缺失字段或模式不一致仍失败，位置/旋转/尺度检查保持。此模式限于路线和网格修正实验，其他流程默认保留旧检查。`R2/eye_transform_validation_v1/` 在同一 CC 实例中连续状态采样、渲染和重载于约 32 秒内完成，无需处理弹窗；针对眼部检查的 54 项回归通过。后续完整样本仍需验证。

本轮已遇到精确文本 `Failed to record undo/redo step. Undo manager will restart.`，在骨骼检查附近可重复出现；Computer Use 每次读取后仅确认该提示，再检查日志阶段。眼睛/牙齿素材加载使用 Material Only。锁屏时停止界面输入，由用户解锁后重新定位 CC。不能用盲按回车覆盖未知弹窗，也不能把处理弹窗计为角色验收通过。

后续路线 2 首名男性在 `upgrade_cc5_facial_profile` 阶段、明确使用 transforms-only 时仍出现一次相同 Undo 警告。确认后升级继续，事件记录在 `R2/ui_incidents.json`。因此眼骨骼 getter 是已复现的一个触发点，不能把避开该 getter 描述为全流程消除警告。

路线 2 的默认角色未包含可切换的细分 1。`operation=prepare_subdivision` 加载 SHA 锁定的生成副本，保存基础 OBJ 和独立 `subdivision_preparation.ccProject`；随后在 CC 中执行 Subdivide，`operation=capture_ui_subdivision` 反读层级、另存 `subdivision_ready.ccProject`、切回 0 测量并重载。此操作只接受当前单角色且实际为 SubD 1 的场景，不自动把按钮点击当作完成。随后 validate 工单显式引用新副本及 SHA，保留原始生成项目作为 lineage。

八例主验证证据现已采集。路线 2 面部配置可从 CC4 Extended 160 项升级到 CC5 MetaHuman 379 项，保存重载、细分 1 和五种表情均已运行；但应用相同 BodyFit 数值后，身体并不等于现有 Average。两例女性相对 F02 规范 OBJ 的非 Headshot 头部区域最大位移均约 85.59 mm，两例男性相对 M02 均约 56.55 mm，躯干和四肢均有差异；报告为各自 `validate/average_body_comparison.json`。因此该实现的 Average 门禁未通过，不能凭滑块值相同接受。路线 2 女性第二例原生成报告保留预览中断的失败标记；已保存项目经 SHA 核验后独立完成验证，不回写原始失败历史。

路线 1 四例完整验证均已采集。`subdivision_roundtrip_localization.json` 进一步显示细分往返的实际世界网格/OBJ 存在毫米级差异；路线 2 的世界网格与 OBJ 差异幅度也不一致。`operation=subdivision_roundtrip_probe` 在独立副本中分开测量两轮 0→1→0、保存为 0 后重载、保存为 1 后重载再切 0，以定位切换、保存和导出的影响。问题未收敛前，不宣称细分一致性通过。

`operation=material_probe` 只读材质颜色、Shader 参数和可选的 `texture_probe_materials` 纹理。纹理通过 SDK `RIImage.SaveFile` 保存，避免把 `GetQImage` 返回的未绑定指针当作 Qt 图像；每通道记录尺寸、文件 SHA 或实际错误。`material_texture_probe_v1` 发现路线 1 睫毛 Diffuse 实际是 616×616 的缺图提示；路线 2 的对应贴图为有效 2048×2048 深色图，两者 Opacity SHA 相同。`eyelash_diffuse_repair` 仅替换 Diffuse，不改透明度或几何，并强制核验 Opacity SHA 不变。`appearance_repair/` 保存独立项目、修复前后网格、原生比例中性及表情图。已完成的女性两例和男性第一例修复前后 Body OBJ 位移为 0；所检查闭眼、张嘴图没有原白色睫毛，最终视觉范围以审查记录为准。[官方材质 API](https://wiki.reallusion.com/IC_Python_API%3ARLPy_RIMaterialComponent) 与本机 SDK 用于核对参数，最终以当前 CC 实测为准（2026-10-02）。

细分探针新增原始 F02/M02 控制组。控制组重复设置当前细分也会出现世界坐标/导出差异，但局部基网格变化不足 0.001 mm；不能将其统一解释为 Headshot 改坏形状。路线 1 男性第一例则在首轮 0→1→0 出现约 2.886 mm 的局部网格变化，第二轮不再累积。这两种现象必须分开。`operation=measurement_side_effect_probe` 不经通用强制 Morph 刷新加载项目，依次隔离只读采样、SetTime、ObjectModified、OBJ 导出、重复当前细分及 1/0 切换，保存每步 local/world 顶点和骨骼变换；`operation_deltas.json` 是离线逐步差值。该诊断尚未给出正式细分一致性通过结论。

`operation=representative_export_probe` 对 SHA 锁定的最终副本独立加载两次，沿用 UE5 骨架、原始纹理及 JSON 的既有 FBX 配置，不导出动作，调用 `EnableBakeSubdivision(False)`。**该开关不证明 CC5 输出为 SubD 0**：当前从细分 1 项目导出的 Body 实测为 56,412 顶点，而非基础 14,164；必须检查文件实际拓扑，不能按开关值填验收表。为避免 CC 长纹理路径故障，Bundle 保存到 `%CC_EXPORT_ROOT%/headshot_routes_20261002_v1/<case_id>/reload_0|1/`；本节是该实验目录的 Technical owner，导出报告中的 `files` 为含 SHA 的清单，未晋升正式资产。原始输入、失败尝试和日志均保护保留。独立 FBX 检查复用 `wardrobe_fbx_geometry_probe.exe`，派生检查文件写回 R2，不能覆盖导出原件；UE5 重命名后的实际节点为小写 `cc_base_body`，不根据 JSON 中的 Geometry 名字猜测节点名。

离线 `cc_audit_headshot_fbx_v1.py --fbx <原始FBX> --output <新JSON>` 只读解析二进制 FBX 的网格、Shape、通道、蒙皮、纹理引用和连接；`--compare <第二份FBX>` 按语义对象身份重映射连接并比较数组，避免把导出对象顺序或数字 ID 差异误认为损坏。四个男女/路线代表的两次导出均完成：基础顶点、Shape 顶点、蒙皮权重、绑定矩阵差值为 0，语义对象集合和连接一致，证据为各自 `representative_export/binary_semantic_comparison_v2.json`。但 Shape Normals 有差异，不能宣称完整导出一致性通过。

`--normals-only` 保存网格/Shape 法线数组的尺寸、非有限数和绝对分量大于 16 的定位；该宽松界限只识别明显异常，不是法线质量验收标准。`normal_sanity_summary.json` 对八份导出核验：路线 1 女性第一例 `reload_1` 的 `V_Lip_Open` Shape 有 42 个异常分量，最大约 `4.438e304`，其余七份未出现这种量级。原件保持不变，需确认导出器来源与实际渲染影响。两份路线 1 独立 Autodesk SDK 检查的原始严格比较返回不等；`sdk_roundtrip_numeric_review.json` 进一步证明基础顶点、拓扑、骨架和蒙皮权重相同，绑定矩阵差异仅约 `5.68e-14/4.26e-14`。该结果不覆盖 Shape 法线，也不覆盖后续固定头皮项目。

`normalize_subdivision_before_save=true` 是本轮局部实验：在最终头颈设置后先完成 0→1→0，再保存目标项目和重复既有验证。四例均完成；两名女性再次往返的 OBJ 最大差异约 0.00061 mm，两名男性约 0.00034 mm，证据为 `normalized_roundtrip_summary.json`。此处仅证明稳定性改善，不能豁免最终 Average、头颈或头皮门禁；首次变化后的身体仍须与规范比较。女性局部低于颈部的顶点仍测得约 2.497 mm 的最大规范偏差，不能自行设容差宣布 Average 通过。

代表导出必须显式设置 `eye_snapshot_mode=transforms_only`，执行器现已加前置拒绝检查。首个女性导出工单遗漏该字段，因默认 SDK T Pose 查询再次触发 Undo 对话框；该次实际配置保存在 `r1_female_01/representative_export/submitted_config_original.json`，后续工单已补齐，不能把该次作为无弹窗运行证据。其他未知弹窗仍须读取后处理，不批量盲按。

用户指出 SubD 0 的颈部异常，且手动切到 SubD 1 后立即消失。**此前 `neck_probe_v1` 的“渲染未见异常”判定已被否定**：拍摄没有完整覆盖下颈部，而且当时实际配置为 Viewport 0 / Render 1，RenderImage 文件名写 SubD 0 不证明渲染用了 0。三份 OBJ 指定颈部区域无开放边仅是拓扑证据，不能推翻用户观察或视作外观通过。扩大取景后观察到 Viewport 0 的颈部条带及三角形明暗异常；后续真正 Render 0 的隔离实验见下文。

`neck_wide_0_v2/`、`neck_wide_1_v2/` 和 `skin_subd1_probe_v1/` 保存了后续诊断。头部/身体的 Bump 通道提取到 616×616 缺图占位内容：身体为缺图三角图标，头部为脸部法线与该占位图混合；0/1 提取 SHA 一致。Normal 通道未取得图像，不能混同于实际 Bump 槽。`neck_flat_normal_v1/`、`neck_flat_bump_v1/` 是此前尚无视觉因果确认的平坦法线诊断，没有保存为正式修复。不能由 SubD 1 外观较好推断坏纹理已修复。

2026-10-03 用户重新允许必要时使用 Computer Use 后，短暂核对男性第二例独立发型副本的 Viewport 0 / Render 1，并仅把 Render 降为 0；确认 0/0 后停止界面输入。`operation=current_neck_material_contrast` 不重新加载场景，先保存该观察状态为新 `ui_render0_baseline.ccProject`，再通过后台 API 以相同灯光/相机分别渲染原始 Bump 与平坦 Bump。`male_render0_material_contrast_v1/visual_material_isolation_review.json` 记录：原始图复现颈部深色多边形及横带，只替换 Head/Body 两张 Bump 后它们消失，BodyPart OBJ 的 14,473 顶点前后位移为 0。该样本已直接证明 Bump 内容对异常的因果作用；两张图一起替换，尚未分离各自贡献。平坦图会丢失皮肤细节，因此不是正式修复。下一步恢复有效法线纹理并重新验证细分、保存重载和导出，不能把单例诊断扩大为八例全修好。作业结束重载原始 Render 0 诊断副本，正式资产未改。

弹窗处理并非必须依赖 Computer Use：现有执行器含 Qt `ExactUndoWarningGuard` 与定向素材加载处理，Bridge 另有外部精确匹配守卫。当前 Headshot diagnostic 分支提前返回，跳过了通用守卫；这是本轮与旧流程的实际差异。旧实现已静态核对，但未将其重新启用或声明适配全部 Headshot 弹窗。用户最新允许必要时短暂使用 Computer Use，完成后停止；不长期占用前台或盲按未知窗口。入口及边界见 [Bridge 弹窗守卫](../bridge/CC_BRIDGE_OPERATIONS.md#6-弹窗守卫)。

2026-10-03 的 `female|male_A_world_capture`、`B_world_capture` 基于完成头颈设置及首次细分归一化后的候选。`female|male_scalp_target` 由 `cc_build_headshot_scalp_target_v1.py` 生成，`female|male_fixed_scalp/replacement_candidate.ccProject` 已保存重载；相对指定世界目标最大误差约 0.00107 mm。`final_setting_scalp_geometry_comparison.json` 证明修正后完整面部相对 B 的最大偏差约 0.00061 mm，非头部约 0.00092/0.00122 mm。这个“非头部不变”是相对 B，不是相对原规范 Average；临时分区仍包含耳和部分颈部，尚非最终解剖掩码。

代表发型固定为 `CCAPP_SCALP_HAIR_9a8e0a32aa17`（HB3-17 Sleek Deep Side Part）。`female|male_hair_reference_v2/hair_world_meshes.json` 保存 A 适配的同一组发型顶点。`cc_assess_headshot_hair_clearance_v1.py --root <R2> --sex female|male --fixed-dir <sex>_fixed_scalp --hair-reference-dir <sex>_hair_reference_v2 --output <新目录>` 对同一 A 发型测量头顶 10 cm、零遮罩三角区。原 B 新增低于 -0.5 mm 的穿入顶点女性 2219、男性 105，修正后这批顶点均为 0；间隙相对 A 的最大变化小于 0.00028 mm。它不考虑透明贴图、不覆盖全部 40 发型，也不证明动态或材质视觉通过。

`operation=fixed_scalp_hair_visual_probe` 继续在固定 B 副本上检查带材质外观、完整头颈取景和代表表情。直接生成 OBJ 的 ReplaceMesh 与发型对象原生 OBJ 导出分别失败，原失败证据保留在 `female_fixed_hair_visual_v1/v2`。后续 `transfer_hair_geometry=false` 明确只检查 CC 自动适配的同一来源发型，并报告相对 A 的顶点差异；不得将该图作为未经适配的 A 固定网格复用验收。图片使用原生比例，不借助 Computer Use。最终视觉状态及作业结果应从对应报告核对。

`female_fixed_autofit_visual_v2/` 与 `male_fixed_autofit_visual_v2/` 已完成四视角及闭眼/三级微笑/张嘴采集，返回中性后的眼部变换检查通过，加载发型和保存重载前后身体局部顶点差值为 0。自动适配发型相对 A 的最大差异分别约 15.454/9.913 mm，因此不能代替固定 A 网格复用验收。女性 v1 曾因最后背视角后的眼骨世界变换尚未求值而失败；v2 在表情矩阵前先渲染正面中性帧，保留原严格眼部比较，未放宽阈值。`offline_assembly_review.json` 记录该限定结果；全体八例的眼口/牙齿/皮肤仍未完成最终视觉接受。

官方补充参考（2026-10-02）：[CC5 细分层级](https://manual.reallusion.com/Character-Creator-5/Content/ENU/5.0/05-HD-Character/Increasing-Mesh-Level.htm)、[RFileIO 导出接口](https://wiki.reallusion.com/IC8_Python_API%3ARLPy_RFileIO)。当前层级、是否烘焙及实际导出拓扑均以本机报告核验。

### 10.1 颈部异常的输入溯源与修复试验

`R2/skin_source_diagnosis_20261003_v1.json` 汇总本次隔离结果。`canonical_male_skin_source_v1` 从原始 M02 灰模提取的 Head/Body/Arm/Leg Bump 均为 616×616 缺图占位内容；相同照片的 `r2_male_02_skin_source_v1` 提取到有效法线。这证明异常内容已存在于 Current 的灰模输入阶段，不等于资源文件被删除。空 Opacity 通道也可能返回相同占位图，不能仅凭提取结果判断该通道实际参与渲染。

`operation=prepare_headshot_skin_source` 只在 SHA 锁定的 Average 副本中准备有效皮肤。第一种方式加载官方 `Skin/Overall/CC5 Human 2K/HD Neutral M_2K.ccSkin`，通过既有 Qt 定向处理确认皮肤设置，核验身体局部顶点变化、八张 Diffuse/Bump 图像尺寸，再保存重载新副本。`r1_male_skin_preparation_v1` 实测身体变化为 0、八张图均为 2K。随后 `r1_male_02_skin_regenerate_v2` 使用同一照片、Current、Clean Soft、生成前 SubD 0 重新生成。

该整套皮肤方式**未通过**：虽然法线占位图消失，`r1_male_02_valid_skin_render0_v1` 在实际 Viewport 0 / Render 0 下的完整颈部视图没有原横带，但头/身体肤色边界明显，头部 Diffuse 仍主要保留预设皮肤内容。生成前后该图像素最大差 7、平均绝对差约 0.278（8 位范围），所有四张 Bump SHA 不变。照片纹理没有正确保留，不能用有效贴图尺寸或 API 成功替代身份外观验收。其五种表情、重载和细分证据保留于 `r1_male_02_valid_skin_validation_v1`；这些执行结果不使该候选通过。

第二种方式显式配置 `skin_texture_assets`，只载入锁定的四个皮肤材质各 Diffuse/Bump 共八张图，不加载整套 `.ccSkin` 的其他状态。输入必须在 R2 内且 SHA 匹配。`r1_male_skin_texture_preparation_v1` 同样实测身体变化为 0；`r1_male_02_texture_regenerate_v1` 已生成并重载成功，Head Diffuse 从预设的 2K 变为带照片五官内容的 4K，生成后保存前与重载后 SHA 完全相同，四张 Bump 保持有效。该结果支持将整套皮肤状态与直接贴图初始化分开，但还未定位其中具体内部机制，不能把 SkinGen 宣称为已确认根因。新的完整验证入口为 `r1_male_02_texture_validation_v1`，结果以报告与诊断汇总为准。

该直接补图候选仍有夸张凹凸和头身肤色边界。`operation=skin_shader_calibration_probe` 在独立副本中，仅将四个皮肤材质的 `MicroNormal Strength`、`Cavity Strength`、`_Specular` 对齐到 SHA 锁定的官方皮肤材质读数，记录前后及重载的参数、八张图 SHA、局部网格和相同机位对照。`r1_male_02_skin_scalar_calibration_v1` 身体变化为 0、贴图 SHA 保持，但粗糙外观仍在，因此仅降低这些参数不是完整修复。

`operation=skin_normal_channel_probe` 进一步将完全相同的四张 RGB 法线图，通过本机 SDK 的 `EMaterialTextureChannel_Normal` 重新载入；不改变上述参数、Diffuse 或几何。`r1_male_02_skin_normal_channel_v1` 已观察到夸张凹凸明显减轻，网格变化为 0，八图 SHA 在保存重载后不变。**读取 `GetImage(..., Bump)` 得到法线图，不代表写入时也应选择 Bump**；本机 Normal 与 Bump 的载入语义不可互换。准备工单现可显式写 `channel=Bump, load_channel=Normal`，前者标识提取证据，后者指定正确载入方式；旧工单不追改。`r1_male_02_skin_normal_channel_v2` 已补重载后的正面图并确认外观改善保留，终态、图像差值和未通过的肤色接缝见 `skin_channel_visual_review_20261003_v1.json`。

以上参数/通道对照未确认实际 Render 层级，不作为真正 Render 0 的颈部验收。02:40 左右尝试提交 Render 数值时 Computer Use 返回 `failed to activate captured window`，重新定位后仍失败，已停止界面输入；没有将输入框中未确认提交的 0 当作生效证据。实验开始前的当前场景另存为 `pre_probe_current_unverified.ccProject`。照片纹理保留与法线载入问题已有局部进展，但头身肤色边界仍明显；[官方 Headshot Skin Color 说明](https://manual.reallusion.com/Headshot_for_CC/ENU/1.0/ID_TA_SC_Pro.html) 提供头身颜色更新机制，尚未在本机该候选中验证，不以手册代替修复结果。

生成工单新增 `headshot_photo_probe.prepared_source_project`：原 `presets[0].source_project` 仍保留规范源及 SHA，派生源必须位于 R2 且另验 SHA；报告同时记录 canonical/generation source。首次把派生源直接替换为 preset.source_project 的 `skin_regenerate_v1` 被 Bridge 在执行前拒绝，未改变 CC 场景，拒绝记录保留；后续没有扩大 Bridge 全局允许目录。可选 `capture_skin_texture_stages=true` 保存生成前、生成后保存前、重载 SubD 0 后的八通道图像及 SHA，用于区分生成与重载时发生的问题。

`operation=current_verified_neck_capture` 只接受已经观察到 Viewport/Render 同为 0 或 1 的当前实验副本，先另存，再通过 API 拍完整下颈部正/侧/四分之三视图，最后重载该观察副本。当前 Render 0 证据由必要的 Computer Use 确认实际数值并提交后采集，不能从文件名推断。素材支持加载现改用已有 `load_file_with_material_only_dialog`，仅接受 `.ccEye/.ccTeeth`，保存精确弹窗记录；此前本轮两次确认由 Computer Use 完成，r1_male_02_texture_validation_v1 已实测两次精确匹配自动确认。每次界面步骤完成即停止输入。

后续 `operation=skin_preserve_head_material_probe` 在已生成照片的独立副本中加载官方 CC5 整套皮肤，显式保留头部 Diffuse/Normal。它通过既有 `load_file_with_known_cc_dialogs(..., preserve_head_textures=True)` 将精确皮肤对话框的两项 Ignore Head 开关设为 true；默认加载行为不变。`r1_male_02_preserve_head_skin_v1` 保留了照片外观，但肤色接缝仍存在，严格 SHA 校验失败。逐像素复核的 Head Diffuse 最大差仅为 1/255，Head Bump SHA 相同，不能将此描述为照片身份丢失。对话框中的 Apply Head Color to Body 控件在该整体皮肤加载模式中不可见，设置其隐藏值不能证明执行了肤色匹配；失败原报告保留，不晋升该副本。

另一个独立对照改用官方 `Skin/Overall/Normal/CC3+_Neutral_M.ccSkin` 初始化现有 CC5 M02，仍是路线 1，不替换身体。`r1_male_cc3skin_preparation_v1` 身体局部网格变化为 0；`r1_male_02_cc3skin_regenerate_v1/generate` 的同照片 Current + Clean Soft 生成保留了照片脸，头部和身体 Diffuse 均更新。但 `r1_male_02_cc3skin_neck_v1` 的正面、四分之三和侧面完整下颈部图仍有明显色差边界。Render 层级未由界面确认，这些图不作为真实 Render 0 通过证据。当前证据汇总为 `R2/skin_cc3_preparation_visual_review_20261003_v1.json`。

`material_probe` 现额外记录 `GetImageColor` 的 `texture_color_adjustments`，SDK 错误单独保存；`r1_male_02_cc3skin_material_v2` 读得头身 Diffuse 基础倍率相同，图像颜色调整均为七个 0，明显色差在提取的 Diffuse 图中已存在。该范围排除了基础倍率与已读取颜色调整的差异，未证明所有 Shader 状态相同，也未解决 Headshot 的肤色匹配。当时下一步为验证官方 Skin Color/Update 控件；仅在桌面可见且需要时短暂使用 Computer Use，完成即停止。此前窗口激活失败后的捕获仅有背景，未继续界面输入，也没有猜测控件状态。

`R2/canonical_common_subdivision_diagnostic_20261003_v1.json` 对规范原始/首次往返和路线 1 归一化 OBJ 作高度分段对照：规范 F02 自身在该分段的最大变化约 6.607 mm（手指附近），M02 约 1.307 mm。路线 1 相对原始规范的残差并非单一根位移；改以首次往返规范为参考也未消除。高度分段不是最终解剖掩码，这些数字用于排除“共享一次细分就自动一致”的假设，不设新容差、不宣布 Average 验收通过。

下一步：按下述新对照继续定位 Current 皮肤输入问题，再完成八个样本的实际 Average 网格、部件外观、动态与细分/重载对照，最后接入固定头皮和代表发型检查；本节结果不能提前晋升规范源。

#### 2026-10-03 重启恢复、肤色更新与同照片贴图隔离

用户手动重启 CC 后，Bridge PID 27256 / instance `4074e2a85b09406483fa167f1d646841` 已恢复；Computer Use 能正常观察控件。仅必要控件操作使用界面，完成后停止。旧窗口阻塞报告保留为历史，不再是当前执行条件。

`r1_male_02_cc3skin_verified_render0_before_update_v1` 和 `...after_update_v1` 在已观察的 Viewport 0 / Render 0 下，分别保存、拍摄完整正面/斜侧/侧面颈肩并重载。Skin Color 初始 RGB 为 133/93/60；开启 Auto Update，将红色临时改为 134 后点击 Reset，最终 Reset 数值没有读回。不能把它写成精确恢复原 RGB。`skin_autoupdate_before_material_probe_20261003_v1` / `...after...` 提取四个皮肤材质。`skin_autoupdate_material_comparison_20261003_v1.json` 证明更新确实改动了头部 Diffuse/Bump，以及身体、手臂、腿部的 Diffuse；后三者 Bump 不变，所读材质属性和 Shader 参数相同。肤色接缝仍在，不是按钮未执行。

随后通过 Content > Custom > Actor > Head Morph & Skin 新建 `DIAGNOSTIC_Headshot_M02_ColorBlend_20261003_v1.ccAvatarPreset`，仅用于材质诊断，不是规范身份预设。原文件位于 Custom/Avatar Preset/Head Morph Skin，同 SHA 副本保存在 R2。保存时 CC 提示未建 Morph Slider 不能保留形态；应用时明确取消 Morphs/Eye Elements/Teeth，仅选 Materials/Textures/Expression Wrinkles 和 **Apply Head Color to Body**。首次及保存重载后第二次应用分别由 `r1_male_02_headpreset_colorblend_render0_v1/v2` 留证，明显接缝均未消除，不能据此认定匹配已修复。

[CC5 官方说明](https://manual.reallusion.com/Character-Creator-5/Content/ENU/5.0/04-Introducing-the-User-Interface/Content_Section.htm) 确认该颜色选项用于 Head Morph & Skin；[官方预设技术说明](https://wiki.reallusion.com/Content_Dev:CC_Avatar_Head_Preset) 限定自动匹配处理 Base Color，并提示非标准肤色纹理的限制（2026-10-03 查阅）。这些只解释试验选择，不能代替本机结果，也未证明本机具体失败机制。

为区分输入贴图和几何问题，`r1_male_02_matched_r2_skin_transfer_v1` 复用 `operation=prepare_headshot_skin_source` 的八通道模式，将**同照片、默认 Male 路线** `r2_male_02_skin_source_v1` 提取的 Head/Body/Arm/Leg Diffuse 与有效法线原图加载到独立路线 1 副本。法线指定 `load_channel=Normal`；没有编辑图片，也没有替换身体几何。替换前后完整基础 Body 局部顶点最大差为 0。保存重载后，`r1_male_02_matched_r2_skin_render0_v1` 再次核实 0/0 并拍摄完整三视图：原多边形状头身色界在这三张图中消失，照片面部仍可见。该诊断尚未加载眼部支持材质，灰色眼睛不属于通过结果。

汇总证据为 `R2/skin_color_update_and_transfer_review_20261003_v1.json`。这只支持“同照片默认路线贴图在路线 1 网格上能改善接缝”的限定结论，没有选定双次生成的混合正式路线，也未解除 Average/细分/全样本动态/固定发型验收。后续 `r1_male_02_matched_r2_skin_validation_v1` 复用原验证器补眼睛牙齿材质、表情、保存重载和细分；其执行结果仍需独立看图和几何比较。

`r1_male_02_matched_r2_skin_validation_v1` 已于 10:51 完成：CC5 MetaHuman 379 项、五种表情活性及返回中性眼部变换检查通过；眼睛/牙齿 Material Only 弹窗由既有定向处理各执行一次。中性、闭眼、大微笑、张嘴正面图已看，虹膜和牙齿可见、原白色睫毛消失；口腔深处与侧面部件贴合未充分显示，不扩大为完整外观通过。贴图、睫毛及眼牙材质阶段 Body OBJ 差均为 0；首次细分归一化的整 Body（含头部）最大差约 3.014 mm，后续再次往返约 0.000483 mm。保存重载的未对齐世界 OBJ 差约 0.012208 mm，不能未排除根变换就称为身体变形。`matched_skin_validation_review_20261003_v1.json` 和该作业的 `independent_mesh_comparison.json` 保存限定结果；Average 与最终导出仍待解决。

复现：使用 S2 下同名 JSON，按第 10 节的 `validate-bodies` 入口写入新的输出目录和 job ID；配置冻结来源 SHA，不重投已有作业。`current_verified_neck_capture` 必须先观察实际 Viewport/Render 0，其 UI 证据不能从 API 的 Viewport 读数推断。检查当前项目及运行终态以实时 Bridge 和恢复检查点为准。

#### 2026-10-03 Headshot 内置基础皮肤的四例复验

通用 `CC3+_Neutral_M.ccSkin` 与 Headshot 自带 `Resource/CCHeadshot/ccAvatarBodyType/RL_CC3_Plus Male.ccAvatar` 的贴图并不相同。新的 `headshot_internal_{male|female}_base_material_probe_v1` 从安装目录的对应 Male/Female 基础角色提取皮肤图，锁定源文件和输出 SHA；不修改安装文件。`r1_{male|female}_internal_skin_preparation_v1` 使用既有八通道 `prepare_headshot_skin_source`，只向对应 F02/M02 独立副本加载 Head/Body/Arm/Leg Diffuse 与法线，后者必须指定 `load_channel=Normal`。

两性贴图应用前后的基础 Body 局部顶点变化均为 0；保存重载后的准备网格与原始规范生成前 OBJ 最大差约女性 0.000464 mm、男性 0.000432 mm。随后四份 `r1_{female|male}_{01|02}_internal_skin_regenerate_v1.json` 复用原四张照片，使用 Current + Clean Soft、生成前 SubD 0。每性别只准备一套基础输入，每照片只生成一次，没有借用路线 2 生成后的照片皮肤。

四例均保存重载成功，32 张生成后/重载后皮肤图 SHA 全部相同；头部 Diffuse 为 4K，其余检查通道为 2K。每例重载后通过短暂 Computer Use 观察 Viewport 0 / Render 1，数值控件将 Render 调为 0，确认后停止界面输入；`r1_{female|male}_{01|02}_internal_skin_render0_v1` 通过 `current_verified_neck_capture` 保存观察状态并采集完整颈肩正面、斜侧面和侧面。12 张图已独立看图，原明显多边形色界与占位 Bump 条带均未再出现；不同照片的面部外观仍有区别。此范围不包含尚未补齐的灰色眼睛、白色睫毛，也不证明完整皮肤真实感或最终角色验收。

权威汇总为 `R2/headshot_internal_skin_review_20261003_v2.json`，包含精确输入、报告/项目/图像 SHA、32 个重载比较和四例生成几何；`v1` 保留最早男性单例。准备、生成和 Render 0 工单均在本节 staging 根，以第 9.5 节 `validate-bodies` 提交方式复现；不得覆盖原输出或把旧 UI 观察直接复制给新作业。四例新生成网格与此前原始生成网格存在差异，不能直接继承旧固定头皮、细分或动态接受范围；`internal_skin_vs_original_geometry_20261003_v1.json` 是前三例辅助比较，四例完整值以 v2 汇总为准。实际 Average、首次细分和最终发型/导出门禁仍未通过。`canonical_source_recheck_20261003_v8.json` 确认原 F02/M02 项目 SHA 未变。

`r1_{female|male}_{01|02}_internal_skin_validation_v1` 四例均已补做支持材质、五种表情及细分保存重载，权威汇总为 `internal_skin_validation_review_20261003_v2.json`，v1 保留男性第二例的初始检查。四例均保留 CC5 MetaHuman 379 项，20 项表情图活性与返回中性的眼部变换检查通过。中性、闭眼、大微笑及张嘴正面图已逐例查看：虹膜/眼白可见，白色睫毛已消失，照片面部仍有明显差异；暗色眼睑、口腔内部/舌头和侧面部件贴合尚未完整验收。材质阶段 Body OBJ 变化均为 0；首次细分整 Body（含头部）最大差按女性 01/02、男性 01/02 依次约 3.3720/4.4370/3.1869/3.0137 mm，后续往返最大约 0.000611 mm。保存重载的原始世界坐标差仍完整保留，另外减去全网格的诊断性常量平移后，残差最大约 0.000611 mm；这不证明平移的内部原因，也不替代 Average 检查。图片名只说明 Viewport 步骤，不能证明逐图 Render 1；真正 Render 0 证据仍以四例独立三视图为准。新输入方案没有消除首次细分问题，全部最终导出待补。

`internal_skin_cross_photo_body_20261003_v1.json` 对这四例同性交色作同拓扑/UV 比较：在排除安装 Headshot 头部集合且 Z<130 cm 的诊断分段，最终重载的女性两例最大差约 0.000611 mm，男性为 0。该分段之外仍有上颈部差异；它不是最终解剖掩码，也不是相对规范 Average 的通过证据。该结果区分了照片间身体一致性与对规范身体的一致性，不能互相替代。

#### Render 1 眼口多视角及舌头底色修复（2026-10-03）

`cc_headshot_route_validation_v1.py` 新增 `current_verified_face_multiview`：在刚刚通过 Computer Use 观察并记录 Viewport 1 / Render 1 后，对当前独立候选保存 `observed_render1.ccProject`，使用既有表情别名解析器拍摄中性、闭眼、大微笑、张嘴各四视角（正面、左右斜侧面、纯侧面），记录实际表情权重、图片 SHA，最后重载独立基线恢复中性。仅有文件名 `subd1` 或 SDK Viewport 读数不满足进入条件。CC 窗口太窄会让 native-aspect 图裁去后脑；女性第二例首版 `r1_female_02_face_multiview_v1` 保留为局部诊断，不作为完整侧面验收，最大化窗口后的 v2 才是新检查入口。

女性第二例首版张嘴图显示灰色舌面；`r1_female_02_oral_material_probe_v1` 导出的 `Std_Tongue_Diffuse.png` 三个 RGB 通道逐像素相同。Headshot 内置 `RL_CC3_Plus Female.ccAvatar` 的只读材质对照 `headshot_female_base_oral_material_probe_v1` 提供有颜色的同名舌头底图。原眼睛/牙齿 Material Only 步骤未修复这个通道，不能将“牙齿可见”扩大为口腔材质完整。

新增 `tongue_diffuse_only` 仅允许从 R2 独立项目加载，锁定 R2 舌头底色图片的 SHA，只修改 `CC_Base_Tongue/Std_Tongue` 的 Diffuse，记录修改前、修改后和保存重载后的全部已读取局部网格，保存 `tongue_repaired_subd1.ccProject`，核对重载贴图 SHA；不改几何、骨骼、表情配置或其他贴图。女性第二例的应用及重载局部顶点逐项相同、纹理 SHA 相同，v2 多视角已显示舌面恢复颜色；另外三例也已完成相同修复，四例全部局部顶点逐项相同，原舌头底图全部为灰度，重载新贴图 SHA 相同，见 `tongue_diffuse_review_20261003_v1.json`。

复现使用 S2 同名 `r1_<sex>_<01|02>_tongue_diffuse_repair_v1.json`，按第 9.5 节提交新的 case/job/output ID；随后观察真实 Render 值，再建立 `r1_<sex>_<01|02>_face_multiview_*` 工单。不能自动复用其他候选的 UI 观察。该步骤只补眼口材质与代表表情视角证据，不解除 Average/首次细分、固定 A 发型及最终导出 Gate。

四例 Render 1 共 64 张图已检查，逐例结论、原图 SHA 和 UI 观察汇总在 `face_multiview_review_20261003_v1.json`。中性眼睛与微笑/张嘴可见，牙齿未见明显穿出嘴唇，舌面不再灰色；口腔深处仍受阴影遮挡。女性第一例闭眼有深色竖/弧线，两名男性有较重眼睑暗线或细亮缝，尚不接受完整闭眼外观。实际权重检查发现四例 `C_BlinkL/R` 请求 1、读回 0，其他基础闭眼及睫毛项符合请求；这仅证明读数不一致，尚不能判定自动修正驱动的内部行为。后续从保存的 Render 1 副本做睫毛可见性及基础闭眼/修正项隔离，不重复整套照片生成。

#### 闭眼暗纹与闭合不足的分离及单例修复（2026-10-03）

男性第二例的 `r1_male_02_eyelid_isolation_v1` 以基础闭眼、基础加睫毛、基础加 C_Blink、完整闭眼各配睫毛显示/隐藏拍三视图，共 24 图。`current_verified_face_multiview` 的 `eyelid_isolation=true` 使用官方 `AddOpacityKey` 临时调整 `CC_Base_Body/Std_Eyelash`，读回为 100/0；结束重载保存的独立基线，不持久化隐藏。主要暗纹仍在，不能将它诊断成睫毛本身。各组 `GetVertices(False)` 局部数组相同只说明该查询结果，不能当作实际动态顶点完全相同的证明。

`eyelid_material_isolation` 另锁定 R2 内纯色 Diffuse/平坦 Normal 诊断图，对睫毛隐藏后的原材质、纯色底图、再平坦法线、再隐藏 EyeOcclusion/TearLine 作 12 图对照。只换头部底图后主要拉伸暗纹消失，但蓝色眼球细缝仍在，另两步不消除细缝。v1 因 Normal 通道 getter 返回 None，在材质/表情改动之前失败；v2 将缺失通道显式记录，Bump getter 可导出相应图像。该故障不能被描述成角色没有法线。作业结束恢复原材质副本。证据为 `eyelid_component_isolation_review_20261003_v1.json`，视觉结论限定已查看正面及修复四视角，不将采集数量等同于全部视觉验收。

根据本机 Headshot 2 设置与[官方眼睑蒙版说明](https://manual.reallusion.com/Headshot_for_CC/ENU/1.0/ID_Eyelid_Mask_Dropdown_List.htm)（核验 2026-10-03），短暂 Computer Use 将独立 male_02 的 Skin Settings / Eyelid Mask 从 Minimum Eyelid Rim 改为 **Medium Upper Eyelid Fill**。保留 Clean Soft 的其他设置。进度结束后，`r1_male_02_eyelid_fill_review_v1` 保存新副本、采集 16 图；暗纹减轻但闭合不足仍在。随后按 [CC5 Correct Eyeblink 说明](https://manual.reallusion.com/Character-Creator-5/Content/ENU/5.0/09_Transformer/Fixing-Blinking-Issues-for-Characters.htm) 执行 Character > Correct Eyeblink，`r1_male_02_correct_eyeblink_review_v1` 再保存/采集；四个闭眼视角不再看到蓝色眼缝，睫毛随闭合贴合。`r1_male_02_correct_eyeblink_reload_v1` 从前作业重载后的中性基线复拍闭眼四视角，改善保持。Computer Use 完成控件操作后停止，采集与保存均使用既有 Bridge。

这些工单沿用 S2 同名 JSON 和第 9.5 节提交方法；复现须使用新 case/job/output ID，先加载对应独立候选并观察 Viewport/Render，再操作控件，不复用其他角色的 UI 观察。`record_neutral_meshes=true` 保存修改后及重载的局部数组，`capture_poses=["blink"]` 仅用于重载后的针对性复验。快照证据覆盖 SDK 暴露的 Body（14,164/56,412 顶点）及 Tongue 两层，不能扩大为所有眼部零件不变。与舌头修复基线相比，以及两次修正和重载之间，上述中性网格最大位移均为 0。

`eyelid_fix_pilot_review_20261003_v1.json` 汇总 male_02 单例输入/结果 SHA、界面操作、限定视觉结论、重载图差和几何检查。头部 Diffuse 有约 52.9% 像素变化，最大通道差 120；大于 10 的变化集中在眼睑区，眼区外存在小幅全图重算，不能声明仅眼睑像素变化。该单例随后扩展到四例，当前范围以下段为准。

四例修复与复查汇总为 `R2/eyelid_fix_four_case_review_20261003_v2.json`。每例沿用 `r1_{female|male}_{01|02}_correct_eyeblink_review_v1`、`_correct_eyeblink_reload_v1` 和 `_eyelid_fix_render0_v1` 三个工单；同名 S2 配置记录来源 SHA 与各自界面观察，复现仍使用第 9.5 节提交方法和新的工单 ID。男女各两例均完成 Medium Upper Eyelid Fill + Correct Eyeblink、保存重载闭眼四视角，以及贴图重算后的真实 Viewport 0 / Render 0 完整颈肩三视图。每例修复后的 16 张中性/表情图现已逐图检查，共 64 张，另含全部 4 张重载闭眼图和 3 张 Render 0 颈肩图。v2 补齐每例中性双斜面/侧面、微笑右斜面/侧面和张嘴右斜面共 24 张，保留 v1 及其 SHA；图像审查完成不等于所有表情幅度、全部部件或连续动画验收。

已检查的闭眼视角未见此前露出的蓝色眼缝，暗纹改善，正常皮肤褶皱与照片眼妆仍保留；12 张完整颈肩图未见原明显多边形色界/占位条带。微笑和张嘴的正面、双斜面及侧面，在可见范围未见明显牙齿穿出嘴唇；补查的中性双斜面/侧面未见新眼球外露或缺图占位内容。深口腔仍受阴影与遮挡影响，完整牙龈/舌面及运动过程未验证，口腔验收仍 pending。蓝色虹膜来自支持材质预设，不代表已匹配照片虹膜颜色。四例与舌头修复基线及两次重载的已读取 Body/Tongue 中性数组最大差均为 0 mm；这不证明所有眼部或动态网格不变。闭眼重载 RGB 平均通道差约 0.030–0.061/255，非逐像素相同。最新界面操作止于 `2026-10-03T07:05:03.625Z`；最后 `male_02` Render 0 作业成功并恢复其 `observed_subd0.ccProject`。C_Blink API 读数语义、实际 Average/首次细分、最终固定发型及修复后导出仍未通过，不晋升正式路线。

### 10.2 最终导出身体与表情法线的独立复核

本节新增的只读实现为 `%CC_SCRIPT_ROOT%/cc_headshot_fbx_sdk_probe_v1.cpp` 与构建入口 `build_headshot_fbx_sdk_probe_v1.ps1`，均为本节拥有的实验工具。构建复用本机 UE 5.8.1 附带的 Autodesk FBX SDK 2020.2、Boost 和已安装 MSVC，不安装外部软件。构建与报告放在 R2，原 FBX 不修改。

```powershell
$projectRoot = 'D:\UE\Lance_Work'
$runRoot = Join-Path $projectRoot '00_engine/outputs/character_creator_bridge/artifacts/headshot_route_compare_20261002_v1'
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$probeBuild = Join-Path $runRoot "sdk_normal_probe_build_$stamp"
& "$projectRoot/00_engine/scripts/character_creator/build_headshot_fbx_sdk_probe_v1.ps1" -OutputDirectory $probeBuild
& "$probeBuild/cc_headshot_fbx_sdk_probe_v1.exe" 'D:\UE\exports\character_creator\headshot_routes_20261002_v1\r1_female_01_representative_export\reload_1\character.fbx' "$runRoot/sdk_shape_probe_$stamp.json" 'cc_base_eyeocclusion' 'V_Lip_Open'
```

以上是本机路径；迁移机器时先核对 project、Engine 与原始 FBX 路径。探针拒绝已存在的报告；后两个参数可省略，提供时在全文件法线统计之外保存该网格和该 Shape 的精确 XYZ 法线数组。它仅导入和读取，不导出、不修复、不启动 UE。输出映射本节 R2 的 `OUT-WF30-CC-ASSETS` 诊断证据，正式导出 Bundle 仍由 WF-40 契约定义；新文件默认保护。

`normal_anomaly_semantic_localization_v1.json` 将原始异常定位为 `CC_Base_EyeOcclusion / V_Lip_Open` 的 Shape Normals，原始数组 42 个分量超过 16；不能笼统描述为全身体法线损坏。历史文本曾指向 `sdk_normal_probe_execution_v2.json`，本轮在 R2 根未找到该文件，因此不将此指针作为已核验闭包；现存数值汇总为下述 `sdk_shape_normal_review_20261003_v2.json`，其历史 source-unchanged 字段仍需原始执行凭据复核。SDK 导入后的 2,461 组法线没有非有限或大于 16 的分量，但进一步对照不能通过：基础眼遮挡网格的 3,456 个法线向量完全相同，该 Shape 在异常文件中出现 73 个零向量；非零配对中 1,336 个方向相差大于 1 度，最大约 173.462 度。`sdk_shape_normal_review_20261003_v2.json` 是当前数值汇总，零向量排除在角度计算之外。仅检查 finite 或极大值会漏掉这一问题。

同份汇总锁定本机 UE 5.8.1 的 `Engine/Plugins/Interchange/Runtime/Source/Parsers/Fbx/Private/FbxMesh.cpp` SHA：`FillMeshDescriptionFromFbxShape` 仅提取 Shape 控制点位置，没有读取该 Shape 法线层。此源码观察支持后续做隔离 UE 导入/表情对照，但不能代替实际导入和渲染验收，也不能把原 FBX 的法线重复一致性改判通过。当前没有修改原件或正式 UE 资产。

另用同一 `representative_export_probe` 设置对原 F02/M02 各加载并导出两次，工单与报告为 `canonical_female|male_average_export_v1`。导出落在既有短路径根下同名独立目录，不另存或覆盖规范项目。`canonical_export_body_comparison_20261003_v1.json` 记录每个 FBX 的 SHA：规范两次导出的 Body 位置差为 0，且与男女各路线第一名代表均为 56,412 顶点、拓扑一致。在规范 Z<130 cm 的诊断分段中，路线 1 女性/男性最大偏差约 2.641/3.746 mm，路线 2 约 85.958/46.889 mm；路线 1 两者平均偏差约 0.334/0.333 mm。该分段不能代替最终解剖掩码，也不是新容差；它确认最终导出仍存在规范身体残差，不能只归因于基础网格查询方式。此组代表导出早于最终材质/头皮修复，不冒充修复后完整样本验收。

#### 反向补偿后代表导出（2026-10-03，未完成验收）

`female02_inverse_representative_export_v1`、`male02_inverse_representative_export_v1` 分别从归一化 SubD 0 副本两次重新加载并导出；配置仍在 S2，同名结果在 R2，FBX 在既有短导出根同名目录的 `reload_0|1/character.fbx`。沿用 UE5 骨架、原始纹理、不烘焙细分、不导出动画的诊断设置。

离线只读复算入口 `R2/review_inverse_exports_20261003_v1.py`，汇总为 `inverse_exports_review_20261003_v1.json`。两性基础/Shape 顶点、蒙皮权重、绑定矩阵、语义关联的重复差均为 0。但男性原始 Shape Normals 仍出现极大分量及不一致，不能声明完整 FBX 通过。旧规范导出 Body 为 56,412 顶点，本轮低层导出为 14,164 顶点，拓扑不同，因此逐点/高度比较未执行；需要同层级规范导出，不能用重复性替代 Average 匹配。SDK 探针的完整统计已保存；本轮详细向量过滤误用了 Geometry 大小写而非小写 scene node，未得到指定向量数组，不据此宣布方向一致或外观正常。后续需精确小写 node 和 shape 名或引擎表情验证。

#### 同层级规范导出与绑定姿态诊断（2026-10-03）

`canonical_female_subd0_export_v1` / `canonical_male_subd0_export_v1` 复用已验证为工作 0 的规范独立副本，各重新加载两次导出；未覆盖规范源。与本轮男女第二例的 FBX 均为 14,164 顶点，原始拓扑一致；原生 OBJ 四边形经扇形三角化后逐顶点索引拓扑一致，才应用 Headshot 非头部索引。初版离线检查直接比较四边形/三角形而中止，没有产生报告；修正后报告为 `same_level_export_body_review_20261003_v1.json`，复算脚本 `review_same_level_export_body_20261003_v1.py`。

规范与候选各自重复顶点差均为 0；非头部 9,601 顶点的原始绑定姿态差最大女性 9.846 mm、男性 3.608 mm。该数值不能直接归因于体型：`review_export_bind_diagnostic_20261003_v1.py` 使用文件内 Cluster Transform/TransformLink 和权重做只读坐标诊断，同文件映射误差不足 0.000102 mm；映射到规范绑定空间后最大差降至 1.761/0.852 mm，平均 0.022/0.058 mm。结果为 `export_bind_diagnostic_20261003_v1.json`，保留全部骨骼差异与权重比较。仍有残差，部分 Cluster 权重列表不逐项相等，且这是离线诊断而非修复、正式重定向或同动作动态验收；不得据此宣布导出体型通过。下一步要在相同姿态/动作验证，原始 Shape 法线问题仍独立保留。

#### 四个最终候选的重复导出与非法法线复现（2026-10-04）

使用既有 `representative_export_probe`，S2/R2 新工单为 `{female01,female02,male01,male02}_final_representative_export_v1`。源分别为最终视觉副本的 `observed_render1.ccProject`，全部配置 SHA 锁定；每例独立重载两次再导出。FBX/JSON/纹理位于 `D:/UE/exports/character_creator/headshot_routes_20261002_v1/<job>/reload_{0,1}/`。仍使用 UE5 骨架、原贴图、不烘焙细分、不导出动作的相同设置；未覆盖原文件。工单复现沿用 9.5 节入口和新 ID，规范源不变。导出后 `final_export_restore_male01_v1` 恢复独立中性源。

`review_final_exports_20261004_v1.py` 汇总为 `final_exports_review_20261004_v1.json`，包含四个工单/源/配置及八份 FBX 哈希、四份 `*_final_export_compare_v2.json` 和八份 `*_final_raw_normals_reload{0,1}_v1.json`。四组比较到的网格/表情顶点、蒙皮权重和绑定矩阵最大差均为 0；它只证明重复导出的这些数值一致，不证明规范 Average 的同动作形变一致。四组变化数组均为 Normals。female01/male01/male02 的最大有限分量差约 1.287/1.247/1.360；female02 第二次牙齿 `V_None` 出现 4 个非有限分量、1841 个绝对值超过 16 的分量，最大有限绝对值约 1.571e308。其余七份只通过宽松 finite/range 筛查，不能称法线方向已合格。

独立只读 SDK 探针 `sdk_normal_probe_build_v2/cc_headshot_fbx_sdk_probe_v1.exe` 对 female02 两份文件分别输出 `female02_final_sdk_reload{0,1}_v1.json`，每份读取 2498 个 Shape；导入约 557/564 秒，轮询确认进程在运行，没有因慢而重启。第一份未检出非有限/极大值，第二份的 `cc_base_teeth` / `V_None` 仍有 66 个非有限法线分量。原始4与SDK66分别属于稀疏控制点/导入展开后的统计，不能直接等同；两种独立读取均支持同一 Shape 无效。`female02_final_invalid_shape_probe_20261004_v1.json` 记录该 Shape 顶点增量本身 finite、最大绝对值约 4.58e-5 cm，不构成删除 Shape 或官方内部原因的证明。

每组还有 42 个 Material/Texture/Video 语义标识随 Hair/Scalp 自动编号变化，导致语义对象和重映射连接不全等；未归一化抹去。此变化与法线损坏分别记录，后续按网格材质槽和实际纹理内容核对。不能把零顶点差作为完整 Bundle 一致性通过。

拥有的只读审计器 `%CC_SCRIPT_ROOT%/cc_audit_headshot_fbx_v1.py` 已补 `semantic_keys_only_a/b`、`nonfinite_arrays`、有限相减溢出标记及严格 `numeric_repeatability_passed`。旧 female02 compare v1 含 NaN，已由 v2 报告替代；不删除旧证据。非法顶点/蒙皮/绑定矩阵直接报错，法线异常明确留在报告；非有限输入不再输出含糊的 NaN 最大差。当前实现快照为 `fbx_auditor_final_exports_20261004_v1.py`。新增回归 `%CC_SCRIPT_ROOT%/tests/test_headshot_fbx_comparison.py` 覆盖相同 NaN、有限数相减溢出、材质改名和正常精确重复四种情况。命令为 `python -m pytest 00_engine/scripts/character_creator/tests/test_headshot_fbx_comparison.py -q`。

以上是失败定位，尚未修复任何源 FBX，也不授权生产跳过 Normals。下一步在派生副本验证确定性法线重建/导入及渲染，再完成同动作身体和侧脸对照。所有新产物归本节既有 R2 实验范围，默认保护。R02 保持 in_progress，R03/R04 不启动。

### 10.3 身体残差定位与未接受的替换试验

补充局部坐标/骨骼复核见 `R2/measurement_local_bone_review_20261003_v1.json`：旧男性第一例在相同 SubD 0 的首次往返前后，局部基网格最大变化约 2.88597 mm，而采样的蒙皮骨骼数值变换不变，排除了“仅角色整体位移或这些骨骼变换改变”的解释。附带女性规范记录从 SubD 1 开始、到 0 结束，不属于同层级往返，不能混用其结果。此复核没有证明 CC 内部校正机制，也不能替新生成四例作验收。

生成前先让规范副本完成细分往返的单例对照也未解决问题：`r1_male_prenormalized_skin_preparation_v1` 以已有 `canonical_male_subdivision_probe/roundtrip_subd0.ccProject` 为源，仍只初始化内置基础皮肤；`r1_male_02_prenormalized_regenerate_v1` 使用同一男性第二张照片；`r1_male_02_prenormalized_validation_v1` 使用相同支持材质和头颈设置，三份工单均在 S2、复现仍用第 9.5 节入口。`prenormalized_source_review_20261003_v1.json` 记录首次生成后细分的整 Body 最大差约 3.01333 mm，排除安装头部且 Z<130 cm 的诊断分段约 2.39043 mm。因此不把这项预处理加入推荐路线，不扩展到全部样本；未执行删除或重建细分层。

2026-10-03 的 `R2/body_drift_stage_localization_20261003_v1.json` 对路线 1 四例的原始阶段 OBJ 作同源比较，并锁定源文件 SHA。在规范 Z<130 cm、排除安装 Headshot 头部集合的诊断区域中，Headshot 刚生成时最大偏差约 0.0020–0.0026 mm；女性头颈设置及保存重载后约 0.053 mm，男性仍约 0.0026 mm；首次细分往返后女性约 2.643 mm、男性约 2.360 mm。该结果将主要偏差定位到首次细分往返，不能推导为照片生成完全没有改变颈部或全身体，也不等于厂商已确认的缺陷。

#### 同时读取高低细分层的对照（2026-10-03）

`cc_headshot_route_validation_v1.py` 新增 `subdivision_level_mesh_probe`，在锁定输入副本上读取全部 `GetMeshes(False)` 局部顶点，以 mesh 名称和顶点数区分层级，记录加载及 0→1→0→1→0 各阶段。该诊断不导出或替换网格、不删除层级、不保存输入；`finally` 重载配置中 SHA 锁定且位于 R2 的 `restore_project`。四个工单为 `canonical_{female|male}_all_mesh_level_probe_v1` 与 `r1_{female|male}_01_all_mesh_level_probe_v1`，配置位于 S2，仍按第 9.5 节以新的 ID 复现。

`R2/subdivision_all_levels_review_20261003_v1.json` 保存每层数组 SHA、阶段差异及局部 Z 分段诊断。男女规范对照在 initial0→first1 及后续往返的 Body/Tongue 两层数组均精确不变。新皮肤输入的 female_01/male_01 则在首次切换时同时变化：低层 Body（含头）最大约 3.010/2.886 mm，高层约 22.686/24.112 mm；舌头两层也变化，后续往返数组不再变化。规范低层数组等于高层相同索引前缀，Headshot 候选切换前不相等、切换后相等。这只是读回数组的对应现象，不构成官方拓扑合同或内部故障原因证明；高层大值主要在头部，不能误报为躯干整体移动两厘米。Z 分段只作定位，不替代解剖或 Average 验收。

该证据使高低层数据重新计算成为需验证的原因之一。下一项独立重建试验改用尚未首次切换的 male_01 `headshot_photo_candidate.ccProject`，准备工单为 `r1_male_01_fresh_subdivision_rebuild_prepare_v1`；旧 male_02 准备副本保留，不作为新试验输入。必须先核对删除前后低层几何，再重建高层、保存重载并比较规范身体及照片面部。当时等待界面删除确认；后续授权试验已完成但未采用，见本节删除/重建结果。规范源 SHA 复核见 `canonical_source_recheck_20261003_v14.json`。

新增只读目标构建器 `%CC_SCRIPT_ROOT%/cc_build_headshot_body_restore_target_v1.py` 由本节拥有，生命周期为 `experimental`。它要求两个 14,164 顶点 Body 的拓扑/UV、根旋转和缩放一致，只补偿已记录的根平移差；将安装头部集合外的 9,601 个顶点恢复到测得的规范参考，在头部一侧按六圈拓扑邻接渐变，并锁定 Clean Soft 全权重面部顶点。渐变会触及部分下颈区域，并非已接受的解剖分区。发现渐变进入完整面部区域时拒绝生成；输出目录已存在时拒绝覆盖。

```powershell
$projectRoot = 'D:\UE\Lance_Work'
$runRoot = Join-Path $projectRoot '00_engine/outputs/character_creator_bridge/artifacts/headshot_route_compare_20261002_v1'
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
& 'C:\ProgramData\anaconda3\python.exe' "$projectRoot/00_engine/scripts/character_creator/cc_build_headshot_body_restore_target_v1.py" `
  --reference-world "$runRoot/r1_female_01/validate/average_reference_world_mesh.json" `
  --reference-obj "$runRoot/r1_female_01/validate/average_reference_body.obj" `
  --candidate-world "$runRoot/female_B_world_capture/before_world_mesh.json" `
  --candidate-obj "$runRoot/female_B_world_capture/before_body.obj" `
  --output "$runRoot/female_body_restore_target_$stamp"
```

输出为 `target_world.obj`、`target_geometry.npz` 和含输入/实现 SHA 的 `target_report.json`，属于本节 R2 的 `OUT-WF30-CC-ASSETS` 实验证据，默认保护。CC 执行仍复用 `cc_validate_body_reconstruction.py` 的 `headshot_mesh_replace_probe`；配置源在 S2 的 `route_female_body_restore_v1|v2|v3.json`。新复现必须新建配置、作业 ID 与输出目录，不覆盖已执行尝试。配置中的 `subdivision_roundtrip_after_replace=true` 仅对该诊断分支生效，要求已有 SubD 1、当前为 0；每次替换后确认 1→0 再保存重载。`refinement_strategy` 默认 `accumulate_residual`，另可显式选择 `resubmit_target`；补偿仍限制为最多三次，报告保存实际层级序列和实现 SHA。默认路径不增加细分切换。

`R2/body_restore_review_20261003_v1.json` 是本组结果汇总：

- `female_body_restore_v1`：女性第二张照片的单次替换/重载后，身体对目标约 0.00099 mm、完整面部变化约 0.00046 mm。但独立 `female_body_restore_roundtrip_v1` 在首次 1→0 后又出现约 1.144 mm 目标残差，之后重复和重载保持该残差；采样的骨骼平移/旋转/缩放数值未变，局部基网格变化约 1.165 mm。
- `female_body_restore_v2`：将细分纳入每次残差补偿，最大目标误差依次约 1.130、0.389、0.520 mm，最终约 0.425 mm；未稳定收敛。
- `female_body_restore_v3`：每次重新提交固定目标，最终身体残差约 0.209 mm，但完整面部偏差约 0.544 mm；不能用身体数值改善代替面部保真。

三种尝试均未晋升。报告 `success=true` 仅代表作业执行完成，不能视作 Average、面部、细分或完整路线通过。男性 `male_body_restore_target_v1` 只生成了离线目标，没有执行替换；没有扩展到其他样本。下一步仍优先解决可见界面上的 Headshot 肤色更新和真实 Render 0 验证，同时保留 Average 一致性缺口；本组结果不支持继续增加补偿次数或直接开始规范角色/发型批量导出。

#### 原生 Morph 的限定对照（2026-10-03）

该对照只使用女性第二例，不是新增正式路线。`cc_headshot_route_validation_v1.py` 的 `native_morph_export` 在独立目录导出 ZUp、绑定姿势的 FullBodyPart OBJ 和 CC 原生 OBJ Key，并保存独立输入副本；工单为 S2 的 `canonical_female_native_morph_source_v1.json`、`r1_female_02_native_morph_source_v1.json`。OBJ Key 原样使用，不编辑或伪造。

`cc_build_headshot_body_restore_target_v1.py --native-obj-space --reference-obj <规范原生 OBJ> --candidate-obj <候选原生 OBJ> --output <新目录>` 可生成 `target_native.obj`。该模式禁止混入 SDK 世界坐标输入，要求 Body 拓扑/UV 一致，保持完整文件的其他部件、拓扑和 UV 行；目标中规范身体区域精确恢复，1343 个完整面部顶点不变，头侧六圈过渡仍是实验分区。既有世界坐标调用保持不变，旧女性目标数组的回归比较逐项相同。离线证据为 `native_morph_offline_validation_20261003_v2.json`，目标位于 `female_native_morph_target_v1/`。

原生执行使用 `native_morph_probe`，核心接口为本机 `RIAvatarShapingComponent.CreateSlider` 与 `RMorphSliderSetting`。本机返回值实测为 `[RStatus, 实际注册路径]`，不是单个状态或所传参数指定的输出文件；初次 `r1_female_02_native_morph_probe_v1` 因错误假设输出路径而停止，创建的滑块权重为 0，原失败报告保留。当前实现检查返回状态和实际路径，将注册文件复制到实验目录，并显式设置权重 1.0，不依赖 AutoApply。`native_morph_apply_existing` 可复用已注册且 SHA 锁定的诊断滑块，缺失时明确停止、不隐式重复创建。Morph Slider 的 Source Current/Target File 概念参见 [CC5 官方说明](https://manual.reallusion.com/Character-Creator-5/Content/ENU/5.0/06_Customizing_Morphing_Sliders/Morphing_Current_Character.htm)；具体返回合同以本机报告为准。

| 对照 | 结果与证据 |
| --- | --- |
| 已生成角色上添加 Body 修正，`r1_female_02_native_morph_apply_v1` | 保存重载后仍接近修正结果，但细分往返后的身体对规范最大残差约 1.144 mm；完整面部相对修正前最大约 0.00705 mm。未通过，见 `native_body_morph_review_20261003_v1.json`。 |
| 规范身体副本上添加 Head Morph，开启骨骼适配，`r1_female_02_head_to_canonical_morph_v1` | 首次细分整 Body（含头部）变化约 4.174 mm，后续仍不满足身体、面部与细分联合要求。 |
| 相同 Head Morph 目标关闭骨骼适配，`r1_female_02_head_to_canonical_no_bonefit_v1` | 首次细分整 Body 变化约 5.122 mm，仍未通过。两项 Head 对照见 `native_head_transfer_review_20261003_v1.json`。 |

上述运行测量使用同一姿势的 BodyPart OBJ；原生绑定姿势 OBJ 与其不能直接混比。Head 对照另报告常量平移诊断，扣除后仍有明显残差；不把原始世界坐标差全部解释为形变，也不以平移拟合放宽验收。没有扩展到其他照片，没有晋升规范源，也未继续增加补偿次数。

CC 自动注册了三个 `DM_Diagnostic_*` 实验滑块到 `%CC_ASSET_ROOT%/Reallusion Custom/Actor/Avatar Control/`，实际绝对路径与 SHA 记录在初次作业的 `native_registration_location.json`、两份 Head 作业的 `registered_morph_file`。三份二进制证据副本均在 R2；它们属于本节 `OUT-WF30-CC-ASSETS` 实验证据，未加入正式身份或 BodyFit 资产名单，默认保护。外部注册文件不属于 `%OUTPUT_ROOT%` Inventory 扫描范围，不能误报已由该 Inventory 管理或已清理。未覆盖原规范项目、既有资产或正式 UE 内容。

恢复工单 `r1_female_02_restore_after_native_morph_v1.json` 使用 `restore_source_only` 重载四例主验证中的女性第二例 `final_subd1.ccProject`，检查全部 `dm_diagnostic_*` 滑块权重为 0；不保存或覆盖输入。复现所有工单仍使用第 9.5 节 Bridge 入口，必须使用新的 case/job/output ID。原生修正和头部转移均未接受；接下来补眼口/侧面外观验证，实际 Average 和待确认的细分层重建缺口保持。

#### 顶点读取交叉核查与同性交色位移（2026-10-03）

`subdivision_level_mesh_probe` 可配置 `verify_vertex_queries=true`，每层在整组 `GetVertices(False)` 之外抽取均匀分布索引及可选 `vertex_probe_indices`，用 `GetVertex(index, False)` 逐点复核，再反向枚举全部网格重复整组读取。脚本检查数量、有限值与唯一 `(name, vertex_count)`，保存逐点差及反向读取最大差；`False` 是本机 SDK 的 `bWorld` 参数，不是细分级别。[官方 RIObject 文档](https://wiki.reallusion.com/IC8_Python_API%3ARLPy_RIObject) 的 `GetMeshes(bAll)` 参数控制子节点包含范围（2026-10-03 核验）；两种顶点数仍分别比较，不把跨拓扑前缀对应当作验收依据。

四个原始生成候选及男女规范对照的六个 `<stem>_vertex_query_probe_v1` 工单完成，配置仍在 S2，沿用第 9.5 节提交入口。每次结束恢复 SHA 锁定的 `r1_male_01_fresh_subdivision_rebuild_prepare_v1/subdivision_preparation.ccProject`，不保存源文件，不删除或重建层级。`R2/vertex_query_consistency_review_20261003_v1.json` 与同根 `vertex_query_probe_implementation_20261003_v1.py` 保存实现快照和六例证据：36 次捕获共 19,752 次逐点查询均与整组坐标精确一致，完整反向读取也相同。这排除了已测试的查询路径/顺序差异，不能证明全部 SDK 内部机制。候选首次变化仍存在，后续捕获的两轮往返中基础 Body 局部数组不再累积变化。

`cross_photo_switch_displacement_review_20261003_v1.json` 比较同性交色的**位移向量场**，同时保留切换前/后差异及相对规范残差。在排除安装 Headshot 头部索引且规范局部 Z<130 cm 的区域，女性/男性切换后相对规范最大差约 2.497/2.201 mm、平均约 0.190/0.202 mm；两张照片的切换位移向量最大不一致约 0.000382/0 mm。两侧 `abs(X)>=10 cm` 的诊断区域也近乎相同。上部中央区域的切换位移不一致最大约 0.426/0.289 mm；切换前两照片已有约 6.809/3.394 mm 差异，切换后为约 6.510/3.146 mm，不能把这些差异全部归因于细分，也不能宣称整个身体相同。

这些空间区域只是诊断范围；原始生成候选尚未应用最终头颈设置。本结果支持继续评估用户允许的稳定小偏差方案，不是正式解剖分区、实际穿戴影响、容差批准或路线接受。证据哈希闭包见 `vertex_query_evidence_integrity_20261003_v1.json`。

#### 修正后四例头颈与固定头皮细分复验（2026-10-03）

`r1_<sex>_<01|02>_corrected_world_capture_v1` 四个工单使用既有 `headshot_mesh_replace_probe` / `capture_only`，输入锁定各自 `eyelid_fix_render0_v1/observed_subd0.ccProject`，输出基础 Body 的局部、世界坐标与 OBJ；没有保存或覆盖输入。S2 中同名 JSON 是复现配置。四份局部数组与此前 Correct Eyeblink 重载记录逐点相同，说明该次捕获没有额外改变中性 Body。

离线复现入口为 `R2/review_corrected_geometry_20261003_v1.py`，报告与交互散点图在 `R2/corrected_headneck_review_20261003_v2/`。相同身体区域采用安装 Headshot 的 4,563 个头部索引及 Clean Soft alpha，空间 Z/X 范围仍只用于诊断。最终头颈设置及眼睑修正后，头部索引之外两照片最大局部差异女性 6.510 mm、男性 3.146 mm，集中在上部中央区域；Z<130 cm 的非头部区域女性最大差 0.000496 mm、男性 0 mm，相对原 Average 的最大差仍为约 2.497/2.201 mm。**现有固定头皮算法只改安装头部索引，不能消除索引之外的这批差异。** 女性最终 Head Scale=0.1 为既定设置，不能把相对原规范头颈的全部变化归为细分故障。

四例的局部坐标可直接比较，但男性第二例保存了不同的角色整体旋转/位置，细微尺度读数也不同。当前 target builder 严格拒绝仅平移对齐时的旋转/尺度不一致；未绕过该检查，也没有执行男性目标替换。女性根变换一致，可继续独立固定实验。离线图生成最初遇到本地 matplotlib/NumPy 不兼容，改用已有 Plotly；没有安装或修改环境。`corrected_headneck_review_20261003_v1/` 是被根变换检查中止的部分输出，保留但不作为完整结果。

`female_corrected_scalp_target_v1/target_world.obj` 由既有 target builder 从女性修正后 01/02 捕获构建。`female_corrected_fixed_scalp_v1` 使用独立女性 02 副本执行原有 ReplaceMesh 与有限重载补偿，保存重载后相对目标最大误差 0.000840 mm；固定区 0.000458 mm，完整面部区相对 B 0.000610 mm。这只是静态精度，不是层级一致性通过。

随后 `female_corrected_fixed_scalp_roundtrip_v1` 使用 `subdivision_roundtrip_probe` 检查两轮往返、保存为 0 后重载，以及保存为 1 后重载切回 0。结果见 `R2/corrected_scalp_roundtrip_review_20261003_v1.json`：重复当前 0 不改局部网格，但首次 0→1→0 后固定区最大局部变化 **3.560 mm**、应保留面部区 **2.555 mm**、非头部 **1.865 mm**；第二轮局部数组不再改变。OBJ 相对初始最大约 3.624 mm，保存重载保留了变化后的结果。该证据否定将“已修正头皮可直接安全切换细分”列为正式能力，也证明不能只检查 ReplaceMesh 后一次保存重载。尚未定位 CC 内部重算根因；不扩展此未通过方法到男性或全库，不将两轮稳定代替头皮/面部保持要求。

输入、输出与源项目的 52 项路径/SHA 核查通过，记录为 `corrected_geometry_evidence_integrity_20261003_v1.json`。

本轮全部六个 CC 工单终态成功仅指证据采集成功；固定头皮的细分保持 Gate 未通过。优先诊断层级与网格替换的交互，该阶段删除/重建尚待确认；后续执行未修复几何保持，见下文。R02 保持 in_progress，R03/R04 不变，最终固定发型视觉/动态及修复后导出仍待完成。

#### 层级同步对照与世界坐标输入检查（2026-10-03）

`female_corrected_prefixed_levels_v1` 与 `female_corrected_postfixed_levels_v1` 分别读取修正前、修正后两层网格；另以 `female_corrected_identity_replace_v1` 将完全相同的世界网格原样写回，再由 `female_corrected_identity_levels_v1` 检查层级切换。三个层级工单均逐点交叉读取，恢复同一 SHA 锁定的女性固定头皮实验副本。离线复现脚本为 `R2/review_level_sync_20261003_v1.py`，结果为 `level_sync_review_20261003_v1.json`。

原样写回对照首次切换后两层 Body 最大局部变化分别约 0.000460/0.000459 mm；未替换对照也低于 0.001 mm。真正固定头皮后，保存重载的低层 Body 已改变约 20.555 mm，高层 Body 相对修正前仍逐点相同。首次切换后低层再变化约 3.560 mm，高层变化约 20.273 mm。**高层的 20.273 mm 包含应有的目标形状更新，不能单独叫作错误幅度；低层额外变化及保留面部改变才是未通过项。** 原样替换没有产生相当的毫米级漂移，证据将本例限制到形状更改后的层级同步/重新求值交互，未证明 CC 内部算法、具体缺陷或修复方案。

[官方细分说明](https://manual.reallusion.com/Character-Creator-5/Content/ENU/5.0/05-HD-Character/Increasing-Mesh-Level.htm)（2026-10-03 再核验）区分层级切换、Subdivide 和 Delete Highest SubD；它没有说明本例 ReplaceMesh 后的内部求值顺序。当时删除/重建尚未执行；后续独立副本结果见下文。在线 ReplaceMesh API 页面本次未能取得，不能据此补写未经核验的 SDK 能力。

另准备在工作层级 1 替换低层网格的对照时，`female_corrected_render1_capture_v1` 的低层局部坐标与工作层级 0 逐点一致、角色根变换相同，但 `GetVertices(True)` 最大相差约 805.259 mm。工作层级 1 时该低层世界数组近似未蒙皮局部坐标。因此已在提交替换前中止该路线，**未执行工作层级 1 下的目标替换**；该读数不能作为真实身体变形。证据与输入 SHA 为 `inactive_world_query_guard_review_20261003_v1.json`。

执行器 `probe_headshot_mesh_replace` 现在读取并记录 `working_subdivision_level` 和 `world_target_eligible`。`capture_only` 允许保留非 0 层诊断，但其他替换/发型捕获模式要求实际工作层级为 0，否则在网格写入前拒绝。目标构建器 `cc_build_headshot_scalp_target_v1.py` 同时要求 A/B 世界捕获显式带 `working_subdivision_level=0`、`world_target_eligible=true`；旧缺字段证据仍保留，但重新构建时必须重新捕获，不能手补元数据充当实测。

`female_inactive_world_guard_probe_v1` 实际以明确 `ReconstructionError` 终止，属于预期拒绝，不记为成功导出或应用崩溃。两份 `r1_female_<01|02>_level_verified_capture_v1` 正向捕获完成，生成 `female_level_verified_scalp_target_v1/target_world.obj`，与此前目标的 Body 顶点逐点相同。以未验证的高层捕获输入运行 target builder 也在写出文件前拒绝。此次修复的是输入校验边界，不是首次细分漂移；R02 仍未通过。

本次层级对照及输入检查的 29 项路径/SHA 核验通过，记录于 `level_sync_evidence_integrity_20261003_v1.json`。更改前执行器已按报告 SHA 精确保留为 `mesh_probe_before_world_guard_20261003_v1.py`，新执行器及 target builder 分别冻结为 `mesh_probe_world_guard_implementation_20261003_v1.py`、`scalp_target_world_guard_implementation_20261003_v1.py`；历史报告不因当前代码变更而改写。

#### 独立副本删除并重建最高层（2026-10-03，未采用）

用户明确同意后，已在锁定的 fresh male_01 副本上实际执行 Delete Highest SubD 和 Subdivide；授权与执行时点为 `R2/subdivision_rebuild_authorization_20261003_v1.json`。初始网格与此前 male_01 查询对照逐点相同，规范项目、原生成输入和旧候选均未覆盖。

新增 `cc_headshot_route_validation_v1.py` 的 `current_subdivision_checkpoint` 仅捕获当前场景，不先 Load/切换。必须提供独立来源 SHA、界面观察与预期 working/max 层级，且 working=0；读取各层局部数组、低层世界坐标/OBJ，保存新副本并重载复测。删除前预期 0/1，删除后预期 0/0；不得跳过中间检查点直接重建。`capture_ui_subdivision` 另在首次切回 0 前保存重建后全部局部层数组，避免把后续切换混入重建效应。

S2 工单按 `r1_male_01_` 前缀依次为 `rebuild_restore_v1`、`before_delete_checkpoint_v1`、`after_delete_checkpoint_v1`、`rebuilt_capture_v1`、`rebuilt_levels_v1`、`rebuilt_roundtrip_v1`、`restore_after_rebuild_v1`，均沿用第 9.5 节 Bridge 入口且已终态成功；成功仅指采集完成。界面操作分别位于两个 checkpoint 之间及 after_delete/capture 之间。复现需新 job/config/output ID，不重放已执行 ID；必要界面操作完成即停止 Computer Use。

离线复现入口 `R2/review_subdivision_rebuild_20261003_v1.py`，结论为 `subdivision_rebuild_review_20261003_v1.json`：

| 比较 | 实测结果 |
| --- | --- |
| 删除最高层，尚未重建 | Body 低层最大变化 0.793 mm，临时面部保留区 0.074 mm；Z<130 cm 的非头部区域不变。删除后保存重载全部已读取低层数组完全一致。 |
| 从删除后状态重建高层 | Body 低层最大变化 5.119 mm，面部保留区 1.428 mm；不是仅增加高层顶点。 |
| 同一诊断身体区域相对 Average | 原始首次切换最大/平均 2.201/0.202 mm；重建后 2.695/0.481 mm，超过 1 mm 的顶点由 38 增至 703。该空间分区不是正式解剖容差。 |
| 重建后的两轮细分往返 | 两层 Body/Tongue 相对重建初值最大约 0.000306 mm；逐点与反向读数误差均为 0。 |
| 保存为 0 重载、保存为 1 重载再切回 0 | 原生 OBJ 对初始低层最大差不足 0.000613 mm，保留的是已改变的形状。 |

CC5 MetaHuman 配置名称和 379 项表情名单数量仍在，但本次没有补验重建后表情动态。材料总指纹随可枚举层数改变；重建后总指纹与删除前一致，但原纹理读取存在 `SwigPyObject.isNull` 观察错误，不能把该指纹当作完整纹理验收。由于几何保持已失败，没有将此候选扩展到男女全组、固定发型视觉或最终导出。

**该方法未修复 Average/面部保持，不采用。** 稳定性来自改变后的形状，不能据此宣布消除原始偏移，也尚未证明 CC 内部算法根因。原流程首次稳定化后的偏差小于本次重建，可继续按用户允许的“小幅、一致、不累积”方向评估；最终头皮修正后的漂移仍需单独解决，不能沿用其静态成功。

38 项来源/产物 SHA 核查通过，男女 Average 原规范未改，记录于 `subdivision_rebuild_integrity_20261003_v1.json`。两版执行器保存于同根 `subdivision_checkpoint_before_capture_enhancement_20261003_v1.py` 与 `subdivision_checkpoint_implementation_20261003_v1.py`；来源/报告/中间副本均为本节已保护的 R2 实验证据，不晋升为规范源。最后恢复 `r1_male_01_eyelid_fix_render0_v1/observed_subd0.ccProject`，恢复工单检查诊断滑块权重为 0。

#### 反向细分补偿的女性单例验证（2026-10-03，部分通过）

最高层重建失败后，改为从实际低层拓扑和实测位移求逆补偿。`R2/review_subdivision_stencil_20261003_v1.py` 构建 14,164 个低层顶点、14,046 个四边形的 Catmull–Clark 基点更新算子 S；`review_subdivision_affine_20261003_v1.py` 加入实测偏置 c。四个原始候选的跨样本预测较接近，但已修改头皮的预测最大误差仍为约 1.618 mm，不能把单一偏置当作通用 CC 内部模型。

`build_subdivision_inverse_target_20261003_v1.py` 使用女性第二例固定头皮写入前后的真实局部数组，解 S*d=目标−首次切换结果。另从相同锁定源分别写入原样世界网格及 X/Y/Z 各平移 1 mm，标定每个顶点从输入世界坐标到存储局部坐标的仿射映射。必须保留原 OBJ 多组、UV、面顺序；单组无 UV 输入在本机 RIMesh 路径返回失败。没有更改 Python 环境，数值求解用 NumPy。

S2 工单依次为 `female_skin_affine_<zero|x|y|z>_v2`、`female_inverse_subdivision_apply_v2`、`female_inverse_subdivision_roundtrip_v2`、`female_inverse_subdivision_final_capture_v1`；沿用第 9.5 节 Bridge 入口并使用独立 ID/输出。v2 固定 `replacement_backend=mesh`、`refinement_iterations=0`，旧多轮写入细化会破坏本次标定的单次写入假设：v1 最终误差约 0.508 mm，v2 降至约 0.021 mm。当前执行器的诊断 `avatar` 后端仅用于原样写回对照，三个坐标输入的局部误差均超过 2 m；接口返回成功不代表输入契约正确，不得用于正式目标。

实测聚合为 `R2/inverse_subdivision_review_20261003_v1.json`，可由 `review_inverse_subdivision_20261003_v1.py` 复算；证据与脚本闭包为 `inverse_subdivision_integrity_20261003_v1.json`。首次细分往返后的局部误差：固定区 0.021203 mm、保留面部 0.000611 mm、非头部 0.000308 mm；保存重载后活动 0 层世界坐标相对原目标最大分别为 0.021494/0.000916/0.000944 mm。第二轮对第一轮最大差 0.000305 mm，保存为 0 重载及保存为 1 重载再回 0 的原生 OBJ 误差均低于 0.000535 mm。未补偿时固定区和面部误差分别约 3.560/2.555 mm。

这些是相对本次期望形状的保持误差，**不是与原规范 Average 的偏差，也不是正式容差已批准**。临时固定区含耳/颈；男性、其余照片、解剖分区和最终发型/表情/FBX 均待验证。原始预补偿最多约 8.487 mm，是算法中间态，不能直接用于外观/导出。只使用完成 0→1→0 后保存的 `female_inverse_subdivision_roundtrip_v2/roundtrip_subd0.ccProject`（SHA `628cc032733ae35620b57e185502bd638dc81720b41c2c2471435aa6737a8d65`）作为进一步验证候选。

视觉限制独立记录于 `inverse_subdivision_visual_review_20261003_v1.json`：native v1 前方可见颈部未见原明显条带，但侧/斜视裁切后脑；强制方形视口 v2 发生比例压缩，不能验收；临时焦距接口 v3 返回错误，代码已撤回并冻结为 `neck_focal_probe_failed_implementation_20261003_v1.py`。当前执行器已恢复 SHA `f5606cd84415ec7fd35079e07a0b1cb8e7da1abe5644d16bf1a62055aac77ce3`。网格执行器本次版本冻结于 `mesh_probe_inverse_pilot_implementation_20261003_v1.py`，SHA `124d27099a3495e518aabfdcf2a8cff8e0a142489ec3065ce96bf0f9007a43cb`。

最后 `female_inverse_restore_candidate_v1` 成功恢复拍摄前保存的独立女性归一化候选，实际来源/SHA 与诊断滑块状态见该作业报告。没有覆盖男女规范、没有重新启动或联网 CC，没有写入正式 UE 或启动 80 套导出。下一步验证补偿对实际 Average 目标及其他角色的适用性，R02 继续进行。

#### 反向补偿恢复实际 Average：男女各一例（2026-10-03）

上一项固定头皮单例只证明相对实验目标保持。本项改用对应规范副本的实际活动 0 层世界网格恢复身体。规范原文件直接输入 mesh probe 被实验目录白名单拒绝；同 SHA 原字节副本加载后实际为 SubD 1，`world_target_eligible=false`，未用于目标。最终复用此前规范的 SubD 0 保存副本并重新捕获，`canonical_female_level_verified_capture_v4` / `canonical_male_level_verified_capture_v1` 均明确 working=0、eligible=true，没有修改原规范。

`R2/build_average_inverse_target_20261003_v1.py` 使用既有 `cc_build_headshot_body_restore_target_v1.py`：Headshot head set 外 9,601 顶点恢复对应 Average，头部侧六圈拓扑过渡，照片面部 1,343 顶点锁定。女性输入为上项归一化固定头皮候选，身体最大修正约 14.209 mm。此过渡分区仍是实验定义，不能称作最终解剖区。目标转换使用女性独立标定矩阵，并从已测固定头皮输入/首次切换输出求逆；`female_average_inverse_apply_v1`、`female_average_inverse_roundtrip_v1`、`female_average_inverse_restore_v1` 均完成。

男性第一例使用 `male01_inverse_source_capture_v1` 的修正源，重新运行 `male01_skin_affine_<zero|x|y|z>_v1` 四个单次写入标定。男女基础拓扑和 UV 逐项一致后复用拓扑算子，不复用女性的坐标矩阵。`male01_identity_roundtrip_v1` 给出男性自身层级响应；`build_male_average_inverse_target_20261003_v1.py` 生成目标，随后 `male01_average_inverse_apply_v1` / `male01_average_inverse_roundtrip_v1` / `male01_average_inverse_restore_v1` 完成。男性本次保留自己的头部，并未宣称跨男性照片固定头皮完成。

| 实际测量（最大毫米差） | 女性第二例 | 男性第一例 |
| --- | --- | --- |
| 首次切换后非头部对实际 Average | 0.001073 | 0.000765 |
| 保存 SubD 0 后重载对 Average | 0.000921 | 0.000765 |
| 保存 SubD 1 后重载再回 0 对 Average | 0.001073 | 0.000765 |
| 面部对本次保留照片候选 | 0.000764 | 0.000458 |
| 全 Body 对混合目标 | 0.030416 | 0.013259 |
| 第二次切换对第一次局部网格 | 0.000305 | 0 |

聚合与复算入口分别为 `average_inverse_review_20261003_v1.json` / `review_average_inverse_20261003_v1.py`、`male_average_inverse_review_20261003_v1.json` / `review_male_average_inverse_20261003_v1.py`；目标、预补偿、归一化副本与 config/result SHA 闭包为 `average_inverse_integrity_20261003_v1.json`。只使用 roundtrip 报告中的 `roundtrip_subd0_project`，不使用 apply 输出的预补偿中间项目。

上述证据证明两个样本在所测中性姿态/活动低层的数值保持，不证明骨骼或蒙皮在动作下等同原规范，也不证明高层表面、材质、表情或 FBX 已通过。完整头颈取景仍待补：曾观察女性归一化副本 Viewport 0 / Render 1，调整前工具检测到用户桌面输入，随即停止界面控制；未采集或宣称本轮 Render 0 外观通过。拟用于更远取景的可选参数未实际运行，已从活动执行器撤回；中间报告对应源码按 SHA 精确保存在 `route_owner_unused_framing_option_snapshot_20261003_v1.py`（`82ed6f06c792611c55c096fe28a12bf95977c209c792fecf252b5f64a35b2bc8`），活动 owner 恢复为 `f5606cd84415ec7fd35079e07a0b1cb8e7da1abe5644d16bf1a62055aac77ce3`。

下一步补女性第一例及男性第二例，后者存在根旋转差异，需要正确坐标变换及实测，不能删除守卫硬凑一致。男女各两例、共同接触头皮、固定代表发型、完整外观/表情/最终导出联合通过前，R02 仍 in_progress，R03/R04 不执行。本轮最后恢复男性归一化独立副本，诊断 Morph 权重为零；未重启或联网 CC，未改正式 UE。

#### 四例实际 Average 与同性头部补偿（2026-10-03，静态子范围）

`root_alignment_probe` 在男性第二例独立源上调用既有 yaw/position 接口，保存为新副本并重载。立即读取的世界变换存在滞后，不能直接用于目标；重载后 Body 局部顶点完全不变，世界坐标与刚体变换预测最大差 0.000688 mm。根旋转/尺度检查保留，没有绕过。工单及证据为 `male02_root_alignment_v1`、`male02_root_alignment_review_20261003_v1.json`。执行器本轮精确版本冻结为 `route_owner_root_alignment_implementation_20261003_v1.py`，SHA 见 `four_inverse_integrity_20261003_v1.json`。

`R2/run_remaining_average_inverse_20261003_v1.py` 完成女性第一例、男性第二例各自 source capture、zero/X/Y/Z 单次写入标定、identity roundtrip、inverse apply、inverse roundtrip、final capture；S2 作业以 `<female01|male02>_remaining_` 命名，配置/结果闭包见上述 integrity。男性第二例在身体恢复目标之后最后应用男性第一例规范化候选的固定区，避免再次叠加已过渡的颈部目标。复现必须使用新 ID/目录；不得重新执行旧作业或覆盖中间证据。

| 最大误差，mm | 女性第一例 | 男性第二例 |
| --- | --- | --- |
| 非 Head 区对对应 Average | 0.000916 | 0.000614 |
| 保留照片面部对输入 | 0.000458 | 0.000611 |
| 完整 Body 对混合目标 | 0.013458 | 0.112768 |

单例报告为 `female01_remaining_inverse_review_20261003_v1.json`、`male02_remaining_inverse_review_20261003_v1.json`。`review_four_inverse_cases_20261003_v1.py` 汇总 `four_inverse_cases_review_20261003_v1.json`：同性固定区最大差女性 0.049981 mm、男性 0.112768 mm；非 Head 区同性差最大 0.001380/0.000917 mm。照片面部最大差仍为 24.316/19.410 mm，说明并未把不同照片的面部一并固定。这里只证明已测中性姿态、活动低层的数值结果；临时固定区含耳/颈，不能替代高层、解剖分区、表情和固定发型验证。

所有候选只使用各自 roundtrip 保存重载的 `roundtrip_subd0.ccProject`，不使用 apply 的预补偿中间态。当前恢复工单为 `male02_inverse_restore_after_export_v1`，未修改源，未重启/联网 CC，未写正式 UE 或启动批量发型导出。后续通过范围仍按 R02 判断。

#### 固定代表发型装配与细分对照（2026-10-03，女性未通过）

重新从归一化女性第一例、男性第一例载入 HB3-17 Sleek Deep Side Part，工单 `<sex>01_inverse_hair_reference_v1` 保存 A 适配后的三个部件。旧 `ExportObjFile(RIHair)` 在本机返回 7；`hair_obj_template_probe` 改从拥有该头发的 Avatar 导出 `AllClothes | FullBodyPart`，女性单例 `female01_hair_obj_template_v1` 成功，三个发型组的连续顶点数与 API 一致，完整 UV/组信息保留。此行为以本机 RLPy/运行结果为准；[官方 RFileIO 页面](https://wiki.reallusion.com/IC8_Python_API%3ARLPy_RFileIO) 将 OBJ 接口标记为 experimental，其历史版本文字不能代替 CC5 实测（2026-10-03）。

`fixed_scalp_hair_visual_probe` 现从 Avatar 导出完整 OBJ 模板，逐个发型网格 ReplaceMesh；只改相应组的顶点，保留其他组/UV。`capture_visuals=false` 是显式几何采集分支，报告不得作为视觉通过。作业 `<sex>02_inverse_fixed_hair_geometry_v1` 将同性交色 A 的固定网格装到 B，保存重载后 Body 局部顶点变化为 0，三个发型部件相对 A 的最大世界误差女性 0.000921 mm、男性 0.001070 mm。

`review_inverse_hair_geometry_20261003_v1.py` 输出 `inverse_hair_geometry_review_20261003_v1.json` 与两份 clearance NPZ。沿用头顶 10 cm、零面部掩码三角面、参考距离 0.1–5 mm 的限定采样，女性 3,491/男性 3,708 个点中，没有新增低于 -0.5 mm 的穿入；最大距离变化约 0.002499/0.000296 mm，扩大近邻搜索复核为 0 差异。该结论不覆盖透明贴图后的发丝、全部头部、动态或所有发型。

新增 `fixed_hair_subdivision_probe` 捕获 Body 两层局部数组及发型局部/世界坐标，执行 0→1→0 两次、保存 0 重载、保存 1 重载再回 0。`<sex>02_inverse_fixed_hair_roundtrip_v1` 为固定 B，`<sex>01_autofit_hair_roundtrip_control_v1` 为直接加载、未经替换的 A 对照。复算入口 `review_hair_subdivision_20261003_v1.py`，聚合 `hair_subdivision_review_20261003_v1.json`：

| 对照 | 实际结果 |
| --- | --- |
| 男性固定 B 与直接加载 A | 两层 Body 无变化；全部发型捕获相对初值最大世界差分别约 0.000614/0.000764 mm。 |
| 女性固定 B | 两层 Body 最大差约 0.000305 mm，但第一次回 0 后发型最大变动 15.421 mm；局部数组也变，不能解释为仅世界坐标查询失真。 |
| 女性直接加载 A | 主头发回 0 后基本稳定；Side Clip 第一次回 0 变化 2.166 mm，第二次 4.332 mm，保存 1 重载再回 0 为 6.498 mm；另一部件也逐轮变化。高层时 Side Clip 相对初值约 45–50 mm。 |

两组女性的根变换一致。因此问题不只发生在固定替换步骤，尚未证明 CC 内部原因；头部比例/适配联动是待隔离假设。当前不能推广固定发型在女性上的细分稳定性，也不通过最终视觉。官方 [Conforming Hair on Head](https://manual.reallusion.com/Character-Creator-5/Content/ENU/5.0/08-Hair/Conforming-Hair-on-Head.htm) 描述发际随表情的适配功能，但不能用它证明上述细分变化的原因。本机 `RIHair` 未暴露 `RICloth.SetClothConformingEnable`，未强行类型转换或伪称已关闭自动贴合。

本轮仅尝试一次 CC 窗口观察，截图实际被其他前台程序遮挡；没有发送界面输入，立即停止 Computer Use。未把该截图用于 CC 外观验收。最后 `male02_restore_after_hair_diagnostics_v1` 恢复不带发型的男性归一化实验副本。来源/配置/结果/SHA 闭包为 `hair_subdivision_integrity_20261003_v1.json`，执行器各阶段精确快照分别为 `route_owner_hair_obj_probe_implementation_20261003_v1.py`、`route_owner_fixed_hair_assembly_implementation_20261003_v1.py`、`route_owner_hair_subdivision_implementation_20261003_v1.py`。R02 仍 in_progress，未改规范/正式 UE、未重启或联网 CC、未启动 80 套导出。

#### Head Scale 与发型细分漂移的单变量对照（2026-10-03）

`fixed_hair_subdivision_probe` 新增仅用于实验的 `diagnostic_head_scale`，只接受 0 或 0.1。先记录原网格，再调用已存在的 `apply_single_morph_weight` 修改 `cc embed morphs/embed_full_head9`，读取实际权重并刷新；保留原发型。两轮 0→1→0、保存 0 重载、保存 1 重载再回 0 与此前对照一致。字段不代表新的规范头部设置，也不修改规范项目。

S2 工单 `female01_hair_headscale_00_roundtrip_v1`、`male01_hair_headscale_10_roundtrip_v1`、`female02_fixed_hair_headscale_00_roundtrip_v1` 分别复用原女性 A、男性 A 和女性固定 B 的相同保存输入。全部通过 API 执行，无 Computer Use。离线复算为 `R2/review_hair_head_scale_20261003_v1.py`，输出 `hair_head_scale_review_20261003_v1.json`，输入/配置/结果/规范源完整性为 `hair_head_scale_integrity_20261003_v1.json`，精确实现快照为 `route_owner_head_scale_diagnostic_20261003_v1.py`。新复现必须换 case/job/output ID。

| 对照 | Head Scale | 细分/重载结果 |
| --- | --- | --- |
| 女性 A 原输入 | 0.1→0 | 三个发型部件全部捕获相对调整后初值最大 0.000880 mm；此前 Side Clip 回 0 累积至 6.498 mm。 |
| 男性 A 原输入 | 0→0.1 | 复现 Side Clip 回 0 的 2.259→4.518→6.778 mm 累积；高层最大 54.083 mm；另一发型部件也累积。 |
| 女性固定 B 原输入 | 0.1→0 | 全部捕获相对调整后初值最大 0.000954 mm；此前首次回 0 后最大 15.421 mm。 |

这是同源单变量与反向对照证据，支持 Head Scale 非零状态参与本机代表发型的细分异常；没有证明厂商内部算法原因或全部发型都受影响。两组女性细分期间 Body 两层局部差低于 0.000306 mm，根变换一致。**稳定性比较的初值是改权重之后，不能把它称为原形状保持。** 改权重本身使低层 Body 局部顶点最大变化约 0.793 mm，女性 A/B 的头发世界坐标最大变化约 10.593/13.021 mm；身体世界坐标和骨骼变化需另行核对，不能用局部数组代替。女性原定 Head Scale=0.1 没有被静默改成新的规范设置。

下一步验证消除该联动时如何保留既定目标头型、照片五官与固定发型，同时完成表情/导出检查。当前不能采用“归零即可”的修复，也不因稳定性数字通过而接受路线 1。最后 `male02_restore_after_headscale_diagnostics_v1` 恢复此前不带发型的男性归一化独立副本；CC 未重启、未联网，R02 保持 in_progress，R03/R04 不启动。

#### 原生 Bake Morph Slider 的双女性保持形状复验（2026-10-03 至 10-04）

CC5 [Character 菜单](https://manual.reallusion.com/Character-Creator-5/Content/ENU/5.0/03-Main-Menu/Menu-Character.htm)和[形状烘焙说明](https://manual.reallusion.com/Character-Creator-5/Content/ENU/5.0/06_Body/Baking_Morphing_Results.htm)（2026-10-03 查阅）描述 Bake Morph Slider 会保留形状并把当前滑块归零。它不同于直接设置 Head Scale=0。本机 RLPy 包装器未发现直接烘焙接口；本次经短暂 Computer Use 执行 Character > Bake Morph Slider，随后停止界面控制，采集由离线 Bridge 完成。第一次窗口最小化，经激活恢复；一次点击被用户输入检测阻止后重新观察再执行，没有使用旧坐标重试。

`morph_bake_checkpoint` 是独立副本的证据采集操作，不自行触发烘焙。普通模式载入哈希锁定实验源，记录两层 Body/Tongue 局部网格、活动 0 层世界坐标、三个发型网格、非零滑块及配置/骨骼状态，保存到新路径并重载。`capture_current_after_ui=true` 必须带 `ui_observation`，只捕获当前场景，避免重新加载覆盖刚完成的界面结果。高层非活动世界坐标不作为目标。输入路径和 SHA、当前工作层级 0 均验证，拒绝覆盖已有项目。

S2 配置及 R2 输出：女性 A 使用 `female01_hair_bake_prepare_v1` / `female01_hair_bake_capture_v1`，女性固定 B 使用 `female02_fixed_hair_bake_prepare_v1` / `female02_fixed_hair_bake_capture_v1`；之后为 `<female01|female02>_baked_hair_roundtrip_v1` 与 `<female01|female02>_baked_final_capture_v1`。全部 8 个工单终态成功仅表示执行成功。快照为 `route_owner_morph_bake_checkpoint_20261003_v1.py`。复现必须使用新 case/job/output ID，界面烘焙应在 prepare 成功后、capture 之前；不要在采集前加载别的项目。

复算脚本 `review_morph_bake_20261003_v1.py` / `review_morph_bake_pair_20261003_v1.py` / `review_baked_final_geometry_20261004_v1.py`，对应报告为 `morph_bake_review_20261003_v1.json` / `morph_bake_pair_review_20261003_v1.json` / `baked_final_geometry_review_20261004_v1.json`。闭包 `morph_bake_integrity_20261004_v1.json` 核对输入和规范源哈希。这些属于本节 R2 现有实验输出所有权，默认保护，未晋升为正式角色。

| 检查 | 女性 A / 女性固定 B |
| --- | --- |
| 立即烘焙前后 | Body/Tongue 两层局部网格及三个头发局部/世界坐标逐点差 0；Head Scale 0.1→0，Edge_Left/Edge_Upper_B 也归零。 |
| 保存重载 | 被采集的局部网格仍逐点差 0；世界坐标最大约 0.000764 / 0.000613 mm。骨骼世界位置/缩放不变，四元数换算角差不超过 0.000003 度。 |
| 发型两轮细分、两种层级保存重载 | 对烘焙前目标的三个发型最大世界差约 0.000764 / 0.000613 mm，原先的大幅逐轮漂移消失。 |
| Body 首次细分 | 两层最大局部变化约 0.100456 / 0.100425 mm；后续捕获不再累积。不能称为所有顶点全程严格不变。 |
| 最终实际世界坐标 | 非头部对 Average 最大 0.061379 / 0.061003 mm；保留面部对烘焙前最大 0.006481 / 0.006362 mm；固定区最大变化 0.102229 / 0.102225 mm。 |
| 双照片一致性 | 固定区最终差仍约 0.049981 mm，面部照片差异最大 24.315567 mm；烘焙后位移场在两照片间最大不同约 0.000698 mm。 |

上述细小偏差与用户允许评估“小幅、一致且不累积”方向相符，但没有伪称用户已批准某数值阈值。分区仍使用安装 Headshot 索引及临时面部掩码。眼部状态整体字符串不等包括重新载入对象 ID，不能据此判损坏；本次未采集眼球/牙齿所有子对象逐点网格，也未重新完成表情视觉。材质指纹与 CC5 profile UID/count 保持，仅证明记录字段一致，不能代替贴图和表情渲染验收。烘焙同时涉及眼睑形状滑块，须重点复查闭眼。

一个离线汇总曾在工单尚未终态时触发 success 断言，未生成报告；等待同一工单真正成功后重新汇总，无重复提交或重启。最终 CC 保持女性第二例烘焙后独立副本（`female02_baked_final_capture_v1/morph_bake_checkpoint.ccProject`），工作层级 0；未修改规范/UE、未联网 CC。

这一步提供了可继续验证的保持形状候选修复，R02 仍 in_progress。下一步除最终表情、完整视觉、同动作身体/骨架及导出外，还需用原流程首次细分前副本检验较早的原生烘焙能否简化反向补偿；不得丢弃现有稳定候选或先行启动 80 套导出。

#### 早期烘焙反例、侧脸归因及最终女性表情补验（2026-10-04）

男性原始 `r1_male_01/validate/final_subd0.ccProject` 是第一次细分前副本。依次执行 S2/R2 的 `male01_early_bake_prepare_v1`、短暂界面 Character > Bake Morph Slider、`male01_early_bake_capture_v1`、`male01_early_baked_roundtrip_v1`，未重启 CC。原场景 Viewport0/Render1 的颈部异常仍可见。无非零滑块时，烘焙本身仍改变 Body 低/高层局部网格约 2.886/24.112 mm，低层世界约 3.187 mm；Tongue 也改变。随后两轮切换及两层级保存重载世界差约 0.000382 mm。该行为支持“提前更新了形状”的描述，不证明内部机制，也不构成无损修复；停止把此早期操作当作简化反向补偿的方案。它与已修正的两女性最终候选前后逐点不变的结果属于不同输入条件。

女性第二例历史网格在统一根旋转/单位缩放、仅去除平移后，Headshot 头部包围前后跨度 222.882 mm，比例设置后 233.997 mm，固定头皮阶段 224.920 mm，最终 224.919 mm。宽和面部高度随比例设置也约增 5%；固定头皮未把面部核心区整体向前拉长。该头部索引含耳/颈，不能作为人体测量或真人形态结论；截图与项目的关联未通过图像元数据证明。侧脸观感、外围过渡及头身比例仍须视觉验收。

恢复 `female02_baked_final_capture_v1/morph_bake_checkpoint.ccProject` 后，界面确认 Viewport1/Render1，停止 Computer Use。`female02_baked_visual_prepare_v1` / `female02_baked_face_multiview_v1` 使用现有 `restore_source_only` / `current_verified_face_multiview`，拍摄 neutral/blink/smile/jaw_open 各四视图并重载独立基线。查看 neutral_front、blink_front、smile_front、jaw_open_front、jaw_open_side、blink_quarter_right 六张：表情有响应，未见明显眼球/牙齿错位；闭眼细缝仍可见，不据此承诺所有眼睑细节合格。部分头顶/后脑出画，不能冒称完整发型视觉通过。其余视图、其他最终候选、完整头颈轮廓与动态/导出 Gate 保留。当前 CC 留在此次保存的 `observed_render1.ccProject`，并非规范源。

离线复算 `review_early_bake_and_profile_20261004_v1.py` 写出 `early_bake_and_profile_review_20261004_v1.json` 与 `female02_baked_visual_review_20261004_v1.json`；后者的 neutral restore 初始字段为空，准确复算在 `early_bake_visual_integrity_20261004_v1.json`，同时记录五个工单、规范哈希和重载逐点比较。报告范围保持 partial，R02 未通过。这些输出归本节既有 R2 实验范围、默认保护；复现应使用新 job/output ID，禁止重跑覆盖证据。原工单等待曾超时一次，继续查询同一工单确认成功，没有因观测超时重启或重复提交。

#### 最终四例完整头颈和近景检查（2026-10-04）

`cc_headshot_route_validation_v1.py` 的 `current_verified_face_multiview` 增加可选 `full_head_neck_views` 和 `capture_views`。前者使用远一些的角色位置，并在转向后按 `CC_Base_Head` 世界位置补偿根平移；只改变独立拍摄场景的摆放，不修改顶点形状。骨骼位置在渲染更新后读取；控制位置须独立累计，不能混用含原始 pivot 偏移的 WorldTransform 平移。每次最终拍摄检查头部中心误差不超过 0.02 mm，实测四组均低于 0.0001 mm。后者可选择 front/quarter_right 等已有视角，默认行为不变。实现快照为 R2 的 `route_owner_final_visual_20261004_v1.py`，当前实现 SHA 锁在汇总报告。

女性第二例取景 v1–v3 存在裁切、骨骼更新滞后或根控制坐标混用，保留为失败取景证据，不用于完整外观验收。有效配置为 S2/R2 的 `female02_baked_full_views_v4`、`female01_final_full_views_v1`、`male01_final_full_views_v1`、`male02_final_full_views_v1`；后三例近景各用同前缀 `final_close_views_v1`，女性第二例近景复用 `female02_baked_face_multiview_v1`。女性最终烘焙副本、男性稳定 hair_roundtrip_subd1 副本分别通过对应 prepare 工单恢复；界面观察 Viewport1/Render1，必要时仅切工作层级，随后停止 Computer Use。重放仍使用第 9.5 节 validate-bodies 入口、相应 F02_Average/M02_Average preset、全新 job/output ID；现有配置中的 source SHA 和 UI 观察不是可跨会话伪复用的授权，重放必须重新确认当前源和层级。

`review_final_visual_20261004_v1.py` 汇总八个成功采集工单、配置/源/图片哈希、CC5 MetaHuman/379 项和拍摄前后中性局部网格。有效采集共 100 张，视觉查看 63 张，精确名单在 `final_visual_review_20261004_v1.json`，本地图片入口为同名 `.html`。四例全部六个中性完整视图已检查；女性第一例及两男性各检查八个正面/斜面近景，女性第二例检查此前列出的六张代表近景。未查看图片不冒记通过。拍摄结束重载独立中性基线，所有已读取网格最大局部差为 0 mm；这不取代眼口所有纹理 API 读回或连续动态验收。

已查看范围未见明显颈部断层、代表发型脱离或眼球外露；闭眼、微笑和张嘴有可见响应，牙齿无明显错位。细眼缝仍可见，口腔深部被遮挡或照明不足，不能据此宣布深口腔、全部表情、Render0 或所有发型通过。侧脸比例仍独立保留，不以发型适配替代。后续检查同动作 Average 身体/骨架和最终导出 Shape 法线；R02 未完成，不晋升规范源。当前中性恢复副本为 `male02_final_close_views_v1/observed_render1.ccProject`。新报告/页面归本节既有 R2 实验范围，默认保护；不新增删除或生产授权。

#### 女性第二例侧脸阶段的同坐标复算（2026-10-04）

`review_profile_stages_20261004_v1.py`使用保存的五阶段网格，在单位缩放/相同根旋转下仅去除根平移；复用既有Headshot head索引与临时保留面部/固定区权重。报告`female02_profile_stages_20261004_v1.json`和独立Plotly图`female02_profile_stages_20261004_v1.html`归R2现有实验输出。图为Y-Z点云投影，含背侧顶点，使用相同轴范围；不是带皮肤的正交渲染、解剖测量或用户截图身份确认。数字已复算，HTML未作为人工审美接受证据。

生成→比例设置的面部核心最佳等比拟合为1.050007倍，拟合残差RMS约0.00399mm，支持整体约5%放大而非只拉长前后。首次细分仍改变局部形状（核心最大约0.86556mm），不得从总包围尺寸稳定掩盖它。首次细分→固定阶段的面部核心平均Y变化约-0.001290mm、最大三维变化约0.076319mm；固定→最终最大约0.006475mm。因此不支持“固定头皮把面部整体向前拉长”，但过渡区/头身比例和生成侧脸自然度仍需视觉判断。此处不调整用户规范Head Scale，不晋升源项目。

本机基础Python的旧Matplotlib与NumPy2不兼容，尝试未生成图；改用已经安装的Plotly5.24.1生成无需网络的HTML，未安装/降级依赖。桌面运行库查询未返回而终止等待，未作为可用环境证据。

### 10.4 原始 FBX 异常的隔离 UE 导入对照

`%UE_SCRIPT_ROOT%/ue_headshot_normal_probe_v1.py` 是本节拥有的 `experimental` 工具，只允许在 `R2/ue_normal_probe_project_v1/HeadshotNormalProbe.uproject` 中执行。该空白工程使用本机 UE 5.8.1，仅开启 Python、Editor Scripting、Interchange 和 Geometry Scripting；没有加载或修改正式 UE 工程。工单、冻结脚本、启动器 `run_probe.py`、日志、输入锁和数值数组位于 `R2/ue_normal_probe_v1/`。它们沿用 R2 的实验输出所有权，属于 `OUT-WF30-CC-ASSETS` 路线诊断证据，默认保护；不能晋升为正式角色或转移验收。

`inputs.json` 锁定路线 1 女性第一例原始 `reload_0`、`reload_1` FBX。导入采用现有分离管线的设置：`DO_NOT_COMBINE`、保留 Morph、重算法线/切线、位移阈值约 0.015 cm，不导入材质、纹理或动画，不复用正式 Skeleton。首个尝试因空工程命令行资产注册表未找到引擎管线而失败；改用直接加载引擎对象后通过 AssetTools 复制，两个 `v2` 尝试均成功并正常退出。保留失败记录，不能把第一次失败记作 FBX 内容失败。

准确启动入口如下；`--attempt` 决定隔离资产及导入报告命名，必须为未使用的字母数字串。每条命令等待真实子进程终态；完成前不得再次启动同一工程。

```powershell
$runRoot = 'D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\headshot_route_compare_20261002_v1'
$probeRoot = Join-Path $runRoot 'ue_normal_probe_v1'
$attempt = 'r' + (Get-Date -Format 'yyyyMMddHHmmss')
& 'C:\ProgramData\anaconda3\python.exe' "$probeRoot/run_probe.py" --mode import --case reload_0 --attempt $attempt --tag "import0_$attempt"
& 'C:\ProgramData\anaconda3\python.exe' "$probeRoot/run_probe.py" --mode import --case reload_1 --attempt $attempt --tag "import1_$attempt"
& 'C:\ProgramData\anaconda3\python.exe' "$probeRoot/run_probe.py" --mode geometry --attempt $attempt --tag "geometry_$attempt"
```

仅复核现有导入资产时可直接使用最后一条命令，将 `--attempt` 改为 `v2`，保留新的 `--tag`。`run_probe.py` 每次冻结当前实现并记录 SHA，使用工作区内 UAT 日志目录与 `-nullrhi`。脚本不覆盖已有尝试。`geometry` 从新进程重载保存的资产，通过 Geometry Scripting 提取 **LOD 0 RenderData** 的基础位置、拓扑和分裂法线；数组以带 SHA 的 little-endian gzip 二进制保存。该步骤不进行 GPU、材质或表情姿态渲染。

`R2/ue_normal_import_review_20261003_v1.json` 汇总 `reload_0_v2_import.json`、`reload_1_v2_import.json` 与 `geometry_v1_geometry.json`：六个网格的基础 RenderData 位置、拓扑、法线逐项相等，位置差和法线向量差均为 0；没有零法线或非有限值。保存重载后的 Morph 名单也相同。两份 EyeOcclusion 均未保留 `V_Lip_Open`，Body 同名 Morph 保留，其他 Morph 也未被整体禁用。异常原始 Shape 的微小位置量级低于导入阈值，与该目标被过滤相符，但阈值因果没有单独改变参数验证，不能作为已独立证实的机制。

因此该异常未造成**本组导入设置下的基础 UE 网格差异**，原始 FBX 的 Shape 法线不一致仍然成立。两次导入均有绑定姿势回退和平滑组缺失警告，不能写成无警告验收；隔离工程关闭 ACL 插件产生的默认压缩设置告警也保留。完整表情渲染、绑定姿势影响、修复后最终候选重新导出仍未通过，本结果不能替代 Average、材质或整条路线 Gate。

#### 最终 female02 九网格导入与实际表情诊断（2026-10-04）

旧六网格试验不是最终候选。本轮 `ue_normal_probe_final_female02_v1/inputs.json` 锁定最终 `female02_final_representative_export_v1/reload_{0,1}/character.fbx` 的 SHA，期望九个骨骼网格，明确 recompute_normals/recompute_tangents=true。`%UE_SCRIPT_ROOT%/ue_headshot_normal_probe_v1.py` 增加受 R2 根约束的独立运行目录、可配置网格数量及导入重算法线选项，旧默认保持。复制的 `run_probe.py` 保存每次执行器快照、参数、PID、日志与退出码；对同一隔离工程严格逐进程执行。复现命令为 `python R2/ue_normal_probe_final_female02_v1/run_probe.py --mode import --case reload_0 --attempt finalv1 --tag <new_tag>`，reload_1同理；已有目标不可重导覆盖，应同时使用新attempt和对应报告。之后 `--mode geometry --attempt finalv1 --tag <new_tag>` 读取已有导入，新进程核验保存后的 RenderData。

`import0_finalv1` / `import1_finalv1` / `geometry_finalv1` 均真实退出0，后者九网格逐点/拓扑/基础法线完全一致，Morph名单一致。Body保留293项，Eye4、EyeOcclusion74、Tearline74、Teeth0、Tongue28、三个发型21/13/9；计数不是完整表情通过标准。牙齿V_None原始位移小于默认0.015cm阈值，但此处仅记录未保留现象，不把阈值归因冒作单变量验证。Body `V_Lip_Open` 保留。

复算 `review_final_ue_base_20261004_v1.py` 输出 `final_ue_base_review_20261004_v1.json`：身体与眼口基础法线无零值；Shoulder_length_Hair有203个零法线角点、涉及86个三角形，其中46个面积小于1e-10cm²；Sleek_Deep_Side_Part_R有29个、涉及11个三角形，其中9个近零面积。其余受影响三角形也很小但不能一概叫退化。两份完全一致只证明重复性，发型实际法线质量仍待。

本节拥有实验源码 `%UE_SCRIPT_ROOT%/ue_headshot_morph_probe_v1/`（含 `HeadshotMorphProbe.uplugin`、`Source/HeadshotMorphProbe/HeadshotMorphProbe.Build.cs`、Public头文件和Private实现）。该只读原生模块设计用于读取已保存LOD0全部Morph位置/法线增量、索引合法性及哈希；当前 **未编译、未加载、无运行证据**。`ue_morph_probe_build_v1` 因UBT备份用户级Trace日志权限失败，终止已确认异常的该编译子进程；`ue_morph_probe_build_v2` 在正常日志权限下明确失败于本机仅有MSVC14.43，处于UE5.8禁用区间。没有改引擎或绕过禁用，没有安装依赖。`build_morph_probe_v2.py` 保留精确命令；`--mode morphs` 当前仅为未验证候选入口，缺模块会明确失败，禁止把它当作已可用能力。

现有接口的替代诊断为本节拥有的 `%UE_SCRIPT_ROOT%/ue_headshot_pose_probe_v1.py`。`run_probe.py --mode poses --tag <new_tag>` 在同一隔离工程启动真实RHI的后台编辑器，使用临时组件、Slate帧等待和keep-python-alive，逐个设置中性/闭眼/微笑/张嘴。读取GeometryScript的LOD0 RenderData组件网格（引擎实现调用GetCPUSkinnedVertices），保留位置/拓扑/法线数组与PNG。实际位置是否响应、两份是否一致及图片是否有效仍须检查，设置权重成功不能代表表情生效。当前仅诊断灰模身体/眼球/牙齿/舌头；无生产贴图，不用灰模图替代皮肤材质验收；毛发/眼遮挡片/泪线不在本轮表情画面中。启动 `poses_v1` 的PID与实时状态见同目录 `poses_v1_process.json`，脚本状态见 `poses_v1/result.json`；检查真实进程后续接，禁止因等待超时重投。

以上归既有R2实验所有权与默认保护规则，不触碰正式UE资产。原FBX非法Shape法线仍未修复。路线1完整接受仍待，R02 in_progress，R03/R04不启动。

#### 实际 Morph 变形结果、取景修正和张嘴边界（2026-10-04）

上述 `poses_v1` 已终态退出，不再是运行中。v1使用CC骨骼名`CC_Base_Head`在UE5命名骨架上取到零定位，实际拍到脚；v2改为`head`但负Y相机看到后脑，且诊断灰材质缺少骨骼/Morph使用标记，早期回退为默认网格材质。这两组图片不用于面部视觉验收；已保存数值不删除。v3用`head/r_eye/l_eye`读取世界位置，以双眼中点相对head的水平向量确定正面，验证骨骼存在与合理高度；显式启用SkeletalMesh和MorphTargets材质用途、首个中性状态延长暖机。八张900×900正面图已逐张检查，头顶、下颈和双肩均入画。

`review_final_ue_poses_20261004_v1.py --tag poses_v3`读取哈希锁定的CPU蒙皮数组，输出`final_ue_poses_v3_review_20261004_v1.json`；v1/v2也各保留对应报告。每轮两份导出×四种状态×Body/Eye/Teeth/Tongue，共32组网格；位置、拓扑、分裂法线全部finite且两份逐项完全一致。Body相对中性在blink/smile/jawOpen的最大变形约15.561/11.619/10.814mm，证明实际变形而非仅设置权重成功。GeometryScript的RenderData组件读取在UE源码中调用`GetCPUSkinnedVertices`，其内部刷新骨骼、临时切CPU蒙皮后恢复模式；这里不声称读取了全部存储Morph增量。

`review_pose_visual_20261004_v1.py`将实际检查名单、哈希及图片写入`final_ue_pose_visual_review_20261004_v1.json`和同名HTML。八图中闭眼和微笑有可见响应，未见明显异常法线尖刺。**jawOpen单目标的图中嘴巴仍闭合**，只体现下脸变形；因此它不是完整张嘴、牙齿联动或口腔验收。CC原有`profile_upgrade_pose_specs`使用实际表情名称和多项权重组合，本简化UE目标不能等同；下一步须验证CC生成并包含骨骼轨道的真实表情导出，不能直接把数值一致升格为完成。灰模眼角/眼睑小片与边界仍可见，未使用生产透明、眼遮挡/泪线或发型材质，不根据此图接受或重改CC眼部。两份图片并非逐像素相同，平均RGB绝对差约0.275–0.277/255；网格/法线精确相同是独立的数值结论。

三轮编辑器均正常退出0。日志另有新Viewport移除不存在的realtime override所致handled ensure；源码确认`editor_set_viewport_realtime(True)`只是移除指定override。当前检查器删除这一无必要调用，仍显式SceneCapture渲染；保留旧日志，不声称修复整个引擎。当前源码与v3冻结快照仅在这个后续清理处不同，图像证据按快照哈希归属。未修改正式UE项目、未重启/联网CC。

#### 完整表情动画导出：姿势模式与静态导出选项对照（2026-10-04）

`cc_headshot_route_validation_v1.py`新增实验操作`representative_expression_motion_export`，锁定独立源项目、恢复副本与本机`_Full Face.iMotionPlus`哈希。加载校准动画后检查`IsCurrentPoseMode=false`；保留载入的动画片段，在0/30/60/90/120/150/180帧写中性/闭眼/中性/大微笑/中性/张嘴/中性，使用既有`profile_upgrade_pose_specs`。每帧先求值，再记录全部骨骼变换和权重；禁用会跳回起点的通用刷新。非C_输入权重必须在1e-4以内读回；自动corrective单独保留读数。CC的RTime是tick，180帧为18000tick、3秒，不能直接当毫秒。

女性第二例v1因不存在的GetValue失败；v2无实际表情；v3/v4证明当前姿势模式下该时间轴写法未保持关键帧（读回全零），即便保留并延长原片段也未解决。v5加载本机校准动画后切换为动画模式，CC闭眼/微笑/张嘴均有响应；但沿用静态TPoseForCreateMorphTargetMesh选项，原始FBX1152条曲线全部只有第0帧，没有连续变化；UE仍将它导入为标称3秒的AnimSequence，不能只用时长判定有效。v6改用既有动作导出组合AutoSkinRigidMesh+ExportRootMotion、去掉上述静态T-pose选项，3秒FBX包含3565条曲线和2413个DeformPercent目标连接，1784条曲线变化。此为设置组合的对照，不声称分别隔离两个标志的因果。

复现配置为`runtime_staging/headshot_route_compare_20261002_v1/{female01_full_expression_export_v1,female02_full_expression_export_v6,male01_full_expression_export_v1,male02_full_expression_export_v1}.json`，仍通过既有validate-bodies桥执行，必须换新case_id/输出目录，禁止覆盖旧记录。CC源/帧记录/截图/动画项目在R2同名目录；FBX与原纹理在`D:/UE/exports/character_creator/headshot_routes_20261002_v1/`对应case_id。`review_full_expression_export_20261004_v1.py <case_id>`只读解析真实FBX时间/变形曲线和CC骨骼变化；聚合证据为`full_expression_export_review_20261004_v1.json`，四例16张图已实际查看（前三例12张正面全身图，男性第二例4张侧脸近景），三种表情可见。低面部像素覆盖不能替代眼睑、口腔近景或连续UE验收。规范源哈希保持，作业finally恢复male01独立副本；无CC重启、联网或Computer Use。

UE诊断器`ue_headshot_normal_probe_v1.py`新增显式`import_animations`选项和AnimSequence骨架/时长记录；`ue_headshot_pose_probe_v1.py`新增锁定manifest驱动的动画播放分支，按每个网格的同一Skeleton选择唯一动画，0/0.5/1.5/2.5秒取样，不再用手工Morph代替。`ue_normal_probe_full_expression_female02_v1`是已知无连续动画的v5对照，v2是v6正确时间轴候选；两个目录及run_probe.py/日志归本节R2实验所有权、默认保护。运行状态由对应process.json和实际进程共同验证；本段不声明UE动画通过。旧导出Shape法线异常、同动作Average身体/骨架及其他最终视觉Gate仍待，R02 in_progress，R03/R04 pending。

本机API包装器与2026-10-04查阅的[官方iClone8 API文档](https://wiki.reallusion.com/IC8_Python_API:RLPy_RIFaceComponent)帮助确认关键帧参数；该网页属于iClone且标明实验接口，不能直接证明CC5行为。当前姿势/动画模式差别以上述本机对照为准。


#### 完整动画导入的参考姿势污染与同骨架分离导入（2026-10-04）

女性第二例完整动画的首次UE播放并未通过：闭眼时非头部也发生米级变形，眼球、牙齿和舌头异常前移。`ue_normal_probe_full_expression_female02_v2/motion_curves_v1_animation.json`确认曲线通常在0–1范围，闭眼时只有六项有效权重，不能归因于100倍权重。逐项驱动eyeBlinkL、eyelashesDownINL和mouthCornerPullL时，三者都让中性Z<130cm的身体点移动约578.100848mm；六项闭眼叠加时达3473.991975mm。该高度筛选只是本诊断身体范围，不替代解剖分区或Average标准。

`motion_shape_raw_comparison_20261004_v2.json`确认静态与完整动画FBX的这三项原始Shape数组及索引完全一致。旧`motion_shape_rest_pose_comparison_20261004_v1.json`在未验证存储语义时将原始Shape数组当绝对位置再减基础点，推理无效，保留但不可用于证明源FBX被拉坏。当前证据支持UE导入参考姿势污染：含动画的网格被重绑到时间零A姿势，而Morph中混入了向原T姿势回归的共同位移。UE5.8.1本机Interchange代码有无效BindPose时自动使用TimeZero、基础网格重绑与Morph载荷分开处理的路径；精确文件、行段和哈希记入汇总。这是本文件/设置的诊断，不是所有FBX的通用结论，也未修改引擎。

处理对照分三层：

1. 复用独立静态导入的网格，直接播放原动画，并仅在内存声明骨架兼容：118骨骼名称/层级相同，身体巨变消失，但闭眼仍有眼球穿出；**只核对层级不能接受绑定姿势**。该对照没有保存兼容设置。
2. 保留同一静态网格，在`ue_headshot_normal_probe_v1.py`设置`animation_only=true`及隔离工程内明确的`target_skeleton`。导入只产生一个AnimSequence、零网格，且其Skeleton必须等于目标。再用新进程播放这段动画，已查看的四张近景中闭眼眼球穿出消失，微笑与张嘴有响应，牙齿/舌头随下颌移动。Z<130cm区域三种表情相对中性最大位移均低于0.000767mm；这只是片段内身体稳定，不是同动作Average比较通过。
3. 静态网格单独驱动两项闭眼与六项闭眼作对照，两者眼睑均闭合；六项会出现更多下眼睑睫毛片轮廓。诊断使用不透明灰材质、隐藏眼遮挡/泪线和头发，不能把这些线条定性为最终材质缺陷，也不能宣布正式眼部验收。

精确证据：R2下`ue_motion_reference_pose_review_20261004_v2.json`及同名HTML，聚合器`review_ue_motion_reference_pose_20261004_v2.py`核验数组哈希、有限性、输入及两份规范源哈希；本轮实际查看11张新图，HTML仅汇集它们，未独立验证HTML页面排版。较早的v1汇总保留兼容骨架失败阶段。全部新目录仍归本节既有R2实验输出所有权、默认保护，没有新增生产输出类别。

可复现入口（必须新建实验目录/标签，不覆盖已存在运行）：

```powershell
python <R2>/ue_normal_probe_animation_only_female02_v1/run_probe.py --mode import --case reload_0 --attempt <NEW_ALNUM_ATTEMPT> --tag <NEW_TAG>
python <R2>/ue_normal_probe_animation_only_pose_female02_v1/run_probe.py --mode poses --tag <NEW_TAG>
```

第一条读取该目录`inputs.json`，锁定动画FBX哈希和静态Skeleton；第二条读取自身`inputs.json`中的静态`pose_import_attempt`及`pose_animation.source_import_report`，后者需指向新导入报告。测试器支持`pose_cases`逐项诊断，禁止与动画模式混用，权重必须有限且在[-1,1]。兼容骨架分支只作失败对照，不是推荐入口。`ue_headshot_normal_probe_v1.py`的`animation`模式保存实际曲线；运行仍必须检查process.json及真实进程后续接。

本轮所有UE子进程均已退出0，CC原实例保持空闲、无重启联网或Computer Use。下一步验证女性第二例正式眼/睫毛/口腔材质，扩展分离导入到其他三例及重复导出，再完成同动作Average等联合Gate。路线仍未接受；R02 in_progress，R03/R04 pending。

### 10.5 当前路线判断与界面阻塞

截至 2026-10-03，两条路线各有男女各两张相同照片的主验证证据，但尚无正式路线通过。当前建议继续修复路线 1；这只是技术方向建议，不是生产启用决定。

| 项目 | 路线 1：规范 CC5 Average + Current | 路线 2：默认 CC3+ + 升级/应用 BodyFit |
| --- | --- | --- |
| 身体来源 | 直接继承锁定的 F02/M02；生成阶段低于颈部的诊断区域接近原规范 | 相同 BodyFit 滑块不能还原规范网格 |
| 已证实问题 | 首次细分后仍有毫米级身体残差；直接替换补偿未同时保持身体、面部与细分稳定 | 非 Headshot 头部区域的 OBJ 最大差异约女性 85.59 mm、男性 56.55 mm，Average 未通过 |
| 保存/细分与表情 | 首次归一化后的重复往返稳定；已有 CC5 配置和代表表情采集，但最终材质/身体修复后需复验 | 已完成 CC5 面部配置升级及代表表情采集，不能弥补身体不匹配 |
| 当前取舍 | 优先修复，尚未接受 | 当前实现不具备更可靠的 Average 证据，不能作为已通过的回退路线 |

原 `cc_body_preset_library_v2.json` 没有预设的毫米级容差。2026-10-03 用户后续明确调整本次路线选择：优先查因修复路线 1；若无法消除，允许评估小幅、同一性别不同照片间一致且不累积的偏差。该授权尚未指定数值阈值，不能直接把当前残差改判通过；需逐点位移、受影响部位、最终外观/穿戴及重载导出证据。路线 1 完整通过后暂停目标，不继续扩展路线 2。精确范围记录为 `R2/route1_acceptance_direction_20261003_v1.json`，原规范源不改写。

[CC5 官方细分说明](https://manual.reallusion.com/Character-Creator-5/Content/ENU/5.0/05-HD-Character/Increasing-Mesh-Level.htm) 区分了切换显示/渲染层级与删除最高细分层（2026-10-03 查阅）。本机 `Bin64/RLPy.py` 包装器仅公开 `GetSubdivMeshLevel`、`GetMaxSubdivMeshLevel`、`SwitchSubdivMeshLevel`，没有发现对应的删除最高层接口。重新建立高层细分已按用户授权在独立副本完成诊断，结果未改善残差，见 10.3；规范项目未修改。

2026-10-03 再核对程序文件，本机仍为 `5.02.0923.1`、界面 Headshot v2。[Reallusion 的 5.07.1705.1 官方公告](https://discussions.reallusion.com/t/character-creator-v5-07-update-headshot-3-subdivision-distortion-issues-fixed-before-after-included/17155)（2026-05-06）说明修复了 Headshot 3 发布后报告的细分角色动画、睫毛/眼睛控制变形，并要求重建已受影响文件。但本机 Headshot 2 的中性身体残差尚不能归因于同一缺陷，不能据此宣布升级可解决。[较早的 Current 建议](https://discussions.reallusion.com/t/official-character-creator-5-issues-thread/15102/51)要求生成前细分为 0，现有路线 1 已执行。版本与范围证据为 `R2/subdivision_version_scope_review_20261003_v1.json`；未下载、升级、重启或让 CC 联网。

此前窗口捕获/激活阻塞已由用户手动重启后的新会话恢复，旧 `R2/execution_blocker_review_20261003_v1.json` 仅保留历史。当前已能核实 Render 0、执行肤色更新和头部预设选项，见 10.1 的重启恢复对照；助手未重启或联网。界面操作结束即停止 Computer Use。

Current 输入皮肤、舌头底色及四例 Fill + Correct Eyeblink 修复已有保存重载与限定视觉证据，贴图重算后的 12 张真实 Render 0 完整颈肩图已复查，见 10.1。下一步集中解决实际 Average 与首次细分残差，再完成最终固定 A 发型视觉/动态及修复后导出；C_Blink 读数语义与深口腔完整检查仍待。10.3 的生成前预先往返、原生 Body 修正和 Head 转移对照未解决联合要求，不扩展这些方法。最高层删除与重建已在用户授权的 male_01 独立副本执行：后续稳定但身体与保留面部变化增大，未采用。确认阻塞已解除，后续继续评估原流程稳定残差及最终固定头皮的细分保持。**现在还不足以进入男女规范源建立阶段**，R03/R04 保持 pending，不启动 80 套发型导出。

#### 直接 UE 审查入口与晚间材质进展（2026-10-04）

本节拥有实验脚本 `%UE_SCRIPT_ROOT%/ue_headshot_material_probe_v1.py`：只在 R2 下的 `ue_material_probe_project_v1` 使用复制的 RLPlugin/CC_Shaders，以 CC FBX Factory 导入代表源并获取 Auto Setup 材质。含人物的见证导入仅提供材质，实际组装仍使用静态拆分网格及单独导入其实际 Skeleton 的完整表情动画，避免参考姿势污染。`ue_headshot_pose_probe_v1.py` 支持受限独立材质工程、明确材质报告绑定、隐藏头皮覆盖层、多视角、贴图流送对照和时间抗锯齿；原始网格及材质不写回。执行器保存源码快照、命令和退出证据；旧失败/中断目录保留。CC `current_scene_backup` 支持零角色场景，代表表情导出可在 finally 重载哈希锁定的空场景副本，不能把零角色误作规范角色加载成功。

晚间三例材质队列及男女重复几何/动画队列均已成功终态，female02 材质见证此前完成；这是执行完成，不代表全部图片与逐点比较已验收。female02 `material_poses_v2` 禁用进程内 TextureStreaming 后细节恢复，前一轮可见的颈肩多边形色界消失，支持捕获时低 mip 加载问题；不能据暖机前 32×32 的运行时尺寸认定源贴图仅 32×32。原始姿态图片为 900×900、两盏方向光，没有环境与背景，因此画面周围黑、皮肤明暗偏硬，不能作为最终材质外观。用户在该组未发现明显结构问题，但指出画质及材质不自然；此反馈不扩大为皮肤/头发正式验收。

用户选择直接在 UE 查看，已停止尚未开始的 `hair_temporal_capture_queue_20261004_v1`，三个补拍子任务均未启动，没有删旧结果。保存的关卡为 `/Game/HeadshotInteractiveReview/L_Route1_FourCharacters_v001`，位于 R2 的 `ue_material_probe_project_v1/HeadshotMaterialProbe.uproject`。`interactive_review_v1/build_review.py` 仅在独立项目创建四例角色的关卡组件材质覆盖、代表动画中性位置、隐藏头皮材质、灰色背景、环境光/矩形灯和固定曝光；不修改源网格/材质。`verify_review.py` 在新进程重载后验证 36 个骨骼组件的全部材质覆盖和序列化动画仍保留，不能当作视觉通过。`run_build.py` 保存 PID、日志、源码 SHA；`open_review.ps1` 检查重载证据后打开关卡，`view_startup.py` 仅设置运行时 TSR、禁用贴图流送和面向 F02 的视口。没有补拍或规范资产变动。新灯光场景尚待人类检查；日志仍有 `T_lacrimal_n` 依赖缺失，不能宣称材质无警告。

复现入口为 `R2/interactive_review_v1/open_review.ps1`；Outliner 的 `Characters/F01`、`F02`、`M01`、`M02` 可逐个选择 `cc_base_body` 并按 F 聚焦，鼠标右键配合 WASD 移动。精确当前证据为 `interactive_review_state_20261004_v1.json`，构建与重载为同子目录 `build_result.json`、`reload_verification.json`。男女规范同一面部校准片导出已完成，Average 对照 UE 队列已启动，尚待逐点汇总；该动作只代表面部校准片，不扩大为任意身体动作。R02 继续 in_progress，R03/R04 pending，无 80 套导出。



直接审查启动修正（2026-10-04）：首次 `open_review.ps1` 实际已启动项目并执行视口设置，但 `-ExecutePythonScript` 在脚本返回后默认触发 `QUIT_EDITOR`，不能当作地图损坏或 Python 异常。`view_startup.py` 已增加 `EditorPythonScripting.set_keep_python_script_alive(True)`，并改用 UnrealEditorSubsystem 的视口接口；PS 仅在构建记录仍为 running 时检查 PID，避免 PID 复用误报。Python 编译及 PS 语法检查通过，未擅自重新打开用户编辑器，交互重试尚待。证据为 R2/interactive_review_v1/startup_exit_fix_20261004_v1.json。也可直接打开独立项目和 `/Game/HeadshotInteractiveReview/L_Route1_FourCharacters_v001`。


#### 四例完整表情重复与人工审查收尾（2026-10-04）

2026-10-04 最终晚间核验：用户四角色 UE 材质审查通过，代表头发穿模按用户说明的正式流程条件接受。男女同表情 Average 及女性重复导出的采集均已完成；本轮补验没有新增图片。女性完整代表表情重复位置/法线/拓扑逐项一致，男性绝对位置重复最大差约0.400mm、相对中性表情变形差约0.0163mm，全部拓扑一致且数组有限。主要躯干/四肢骨段长度相对Average最大差约0.000524mm，表情间Z<130cm身体网格变化约0.00275mm；但与旧Average同表情的绝对位置采样差仍约女性6.88mm/男性10.11mm，严格位姿一致性不能写通过。推荐继续路线1，正式Gate仍保留该残差，R02 in_progress、R03/R04 pending；未晋升规范项目。精确指标及限制见Technical10.4和 `route1_numeric_closeout_20261004_v1.json`。

`ue_headshot_pose_probe_v1.py` 新增布尔 `pose_capture_images`，默认 true 保持旧行为；false 时仍等待骨骼评估并读取实际组件数组，但不调用 SceneCapture 捕获或 PNG 导出，行内 image 为 null。女性两例各两份静态网格×四个完整表情共16状态验证该路径，实际无PNG。只在 P1 独立工程补验，不改用户打开的 P2 审查关卡。F01补验首轮把runner的animation诊断模式误用于动画导入而失败，原证据保留；v2改回import模式加animation_only=true后完成，不能拿早期失败报告作成功。

本节拥有R2下只读 `review_ue_route1_numeric_20261004_v1.py` 和 `route1_validation_summary_20261004_v1.md`。读取GZip数组并核验解压SHA，比较四例×四状态×四身体/眼口网格的两份结果，共64组；不同RenderData重复顶点数量时采用双向最近采样距离，禁止假定索引对应。使用空间桶的精确最近点查询；超出相邻桶距离保证时穷举回退，避免本机SciPy/NumPy二进制不兼容。骨段长度或采样距离不替代整个连续表面、骨骼唯一根因或行走验证。材质视审、数值报告、源保护和结束的队列清单见上述closeout；严格UE位姿残差仍开放。


人工照片生成入口（2026-10-04）：R2/manual_photo_generation_20261004_v1/ 保存经 SHA 校验的 `START_female_Average_SubD0.ccProject` 与 `START_male_Average_SubD0.ccProject`；逐字节复制对应 r1_*_internal_skin_preparation_v1 的 prepared_average_skin_subd0，未重新加载或改变当前 CC 场景。规范 CC5 Average 网格保留，Headshot 内部基础皮肤已准备；其用途为 Current + Clean Soft 新照片生成之前的工作副本，不是已固定头皮或已生成新面部的规范角色。lineage、SHA 和建议另存路径见starter_manifest.json。用户人工生成后先保留 SubD0 原始副本，后续部件材质、Medium Upper Eyelid Fill/Correct Eyeblink、头颈比例、固定头皮/身体补偿和必要的女性最终烘焙分别在独立派生副本处理；不要把新照片生成成功视作 R02 整体或新规范源通过。


### 10.6 人工照片角色的独立副本后处理（2026-10-04）

本轮只处理用户人工生成的女性新照片角色，不晋升规范源或写正式 UE。用户指定原始 `R2/manual_photo_generation_20261004_v1/GENERATED_female_photo_01_subd0.ccProject` 不得修改；SHA 为 `294994799902af30aeaf28fbccd3498167c8f375259175412007d0ce9885e111`。处理根为同目录的 `female_photo_01_processing_v1/`，原字节工作副本与来源锁定在 `processing_manifest.json`。照片由用户确认是 `%LANCE_ROOT%/CFD Version 3.0/Images/CFD-MR/CFD-MF-302-027-N.jpg`，实际文件 SHA 也存于该 Manifest。

本节拥有处理根中的实验编排器 `process_manual_female_photo01_v1.py` 与 `finish_cc_manual_female_photo01_v1.py`；它们复用离线 Bridge 和现有替换/细分/头发接口，只使用独立源/输出。每个作业使用唯一的 `manual_female_photo01_*` ID；已提交作业查询同一终态，不超时重投，不覆盖不同输入/OBJ/数组。输入原项目在每次提交及完成后重新核对 SHA。准确执行入口为 `python <处理根>/process_manual_female_photo01_v1.py prepare`、随后 `geometry`；它们用于本次已冻结工单的恢复，不能照抄旧 ID 生成另一位角色。新角色应建立新根、新前缀和新输入锁。

原始角色实际 SubD0、CC5 MetaHuman/379 项配置已读回。支持材料使用已验 Eyes_01、HD Teeth 2K、睫毛 Diffuse 和舌头 Diffuse；眼睛/牙齿加载各由精确匹配的 Material Only 控件解决，未占用 Computer Use。规范比例设置后进行首次细分归一化；身体目标复用实际女性 Average SubD0 捕获，固定区域复用已归一化女性第一例，照片面部全权重区保持。每个新角色独立执行 zero/X/Y/Z 坐标标定和 identity roundtrip，复用经过拓扑/UV 一致性检查的细分算子，不复用其他角色的皮肤坐标矩阵。`geometry_review_v1.json` 记录身体非 Head 区最大误差 0.000924 mm、保留面部对已设置规范比例的输入 0.000610 mm、固定区对女性参考 0.103751 mm；固定区仍含耳/颈的临时定义，不能把全头固定写成已验。

`cc_headshot_route_validation_v1.py` 新增本节拥有的实验操作 `native_control_inventory` 和 `late_bake_native_control`。前者只记录 CC 内部 Qt 控件与 API 状态；后者要求同一个已完成补偿的 candidate/source SHA、活动 SubD0 和 Head Scale0.1。菜单搜索 v1/v2、过期 QAction v3、无有效菜单 v4 均在真正烘焙前失败；记录保留。v5 精确匹配唯一启用的 `qtBakeToolButton`、文字 Bake、提示 Bake Slider 及 AvatarCreatorShaping 祖先，直接调用 Qt 按钮，不启用禁用控件，不激活前台或移动鼠标。该控件所在标签当时隐藏，不能声称是可见菜单点击；当前 native 操作属于已知控件的单例验证，不是任意 UI 自动确认。

`late_bake_v5/route_validation_report.json` 验证 Head Scale0.1→0，立即烘焙前后所有已读取局部网格逐点完全一致，并另存重载。source 实现哈希保留于报告及处理根的冻结版本。较早的原生烘焙反例仍有效，不能把最终烘焙移动到 Headshot 生成后立即执行。烘焙后细分/发型/最终视觉与导出结果以本节后续处理报告为准；仅脚本成功或文件存在不构成完整 R02 接受。

#### 本次 CC 后处理收尾与交付副本

`cc_numeric_final_review_v1.json` 是烘焙后重复细分/保存重载及代表发型的精确测量：非 Head 区对女性 Average 最大差 0.061568 mm；面部全保留区对**已设置规范头颈比例的输入**最大差 0.006487 mm；临时固定区对女性参考最大差 0.103751 mm。后续第二轮与第一轮 Body 局部网格逐点一致；发型组装不改变 Body 局部网格，三个发型部件跨两轮细分及 0/1 保存重载最大差低于 0.000618 mm。不是相对人工生成原始面部完全不变：Head Scale 规范比例仍会整体改变面部尺寸。

`final_neck_views_v1/` 的两工作层级各正面/斜面/侧面共六张完整颈肩图已查看，未见明显断层。`final_expression_v1` 首次表情序列部分取景无效，空微笑图和全身侧面张嘴图明确排除；它的脚本成功和图像差异检测不构成视觉通过，视角变化的具体来源没有确定。保留失败图，不将其混入已审查图集。

本节另拥有 `cc_headshot_route_validation_v1.py` 的实验操作 `sdk_face_preview`：与要求真人观察 Viewport1/Render1 的 `current_verified_face_multiview` 分开；只允许实验根中锁 SHA 的独立 SubD1 源，每个表情重新加载相机并设置正面，采集目标/读回权重，finally 重载原候选并核对全部局部网格摘要。不得据此伪造 Render 级别观察。`final_face_preview_v1` 在中性空权重读回时失败，finally 恢复源；v2 修正空权重调用后成功。四张中性/闭眼/微笑/张嘴正面近景全部已查看，闭眼闭合、微笑与张嘴响应可见，未见明显眼球外露或牙齿错位，深口腔仍受遮挡。本例没有额外使用 Medium Upper Eyelid Fill / Correct Eyeblink，不能把历史四例修正假写成新例执行。

汇总为 `final_cc_review_v1.json`，列出11张有效已审查图片的 SHA、排除图、测量报告和边界。交付副本 `RESULT_female_photo_01_subd0.ccProject`、`RESULT_female_photo_01_subd1.ccProject`（无发型）以及 `PREVIEW_female_photo_01_with_hair_subd1.ccProject`（HB3-17 代表固定发型）均逐字节复制已验候选并再次校验 SHA，准确来源见 `delivery_manifest_v1.json`。`delivery_preview_v1` 已在原 CC 实例加载预览副本，恢复中性 SubD1；原始项目 SHA 未变，本轮无 Computer Use、无 CC 重启/联网、无 UE 操作。

复现补拍须读取本次冻结 `manual_female_photo01_final_face_preview_v2.json`，用新 output/job ID，`source_project` 指向已验 hair_subd1，operation 为 `sdk_face_preview`；恢复入口用同根 `delivery_preview_v1/route_validation_report.json` 锁定的源加 `restore_source_only`。禁止对已完成 ID 重投或覆盖已存在候选。冻结实现为处理根 `route_owner_sdk_face_preview_v2.py`，配置/Bridge 结果和日志全部保留。回归 `final_regression_tests_v3.log` 为295 passed、无跳过；v2 因错误测试文件名未运行测试，不能算通过。

本例状态是 **CC 后处理候选已就绪，等待用户审查**；尚未做本例代表 FBX 导出/UE 验证，未把一个代表发型扩成全库或连续动态通过。旧四例的严格 UE 位姿残差仍开放，R02 in_progress、R03/R04 pending。所有本节输出沿用既有 R2 实验/OUT-WF30-CC-ASSETS 所有权与默认保护保留，不新建生产输出类别、Milestone 或 ADR。


### 10.7 已认可参考头型与双版本发型接续（2026-10-04）

用户在完成路线1、新照片后处理及参考项目检查后，已明确认可female01/male01作为后续各性别参考头皮形状，并授权固定源与双版本发型转换。女性采用完成最终烘焙的 `female01_baked_final_capture_v1/morph_bake_checkpoint.ccProject`，男性采用 `male01_average_inverse_roundtrip_v1/roundtrip_subd0.ccProject`；整理后的独立无发型源与SHA由新批次 `sources/source_manifest.json` 登记。

这是用户认可的实用角色创建与发型参考范围，不宣称旧Average严格UE同表情绝对位姿等同已通过。前述女性约6.88mm/男性约10.11mm绝对位姿采样差与男性重复残差仍保留为技术事实，不作为本次R03/R04自动阻塞，也不重新开展Headshot/细分研究。批次通过一个代表发型核对男女分支后轻量检查全库产物，具体执行归[Transfer11.5](../transfer/CC_TO_UE_MODULAR_OUTFIT_PILOT.md#115-固定男女参考头型的双版本发型转换2026-10-04)，最新状态从[项目状态](../../project_management/status/PROJECT_STATUS.md)读取。

## 11. CC角色创建统一自动化（2026-10-05）

本节拥有[已完成统一自动化计划](../../project_management/history/completed_plans/PLAN-2026-10-CC-CHARACTER-CREATION-AUTOMATION.md)的照片/原始Headshot项目统一入口、生成/修正编排、每角色离线求解与系统CLI。新实现为validated_pilot，准确范围为女性照片入口早版完整机器代表、男性raw入口当前v2完整tail/完成跳过，以及用户独立运行的当前v2女性照片TEST_FEMALE_002；不是production、全池或真实batch。已有[Assembly9](./ASSEMBLY_AND_ACCEPTANCE.md#9-headshot基础外观精简装配2026-10-05)继续独占外观编译、CC装配、颜色、capture/invariants及R06具名policy；新pipeline调用它们，不复制或重新归属。

### 11.1 实现所有权与输入

| 本节实现/配置 | 职责 | 当前范围 |
| --- | --- | --- |
| `cc_run_character_creation_v1.py` | CC内runtime adapter：照片、准备、捕获、替换、细分归一、烘焙和装配操作 | validated_pilot，按11.4实跑边界 |
| `cc_character_creation_pipeline_v1.py` | 两入口共用的修正/装配tail，参数、阶段与来源闭包 | validated_pilot |
| `cc_character_creation_job_state_v1.py` | 串行Bridge step、持久化状态及结果SHA核验 | validated_pilot |
| `run_cc_character_creation_v1.py` | 系统Python CLI，默认准备，显式执行 | validated_pilot |
| `cc_headshot_geometry_solver_v1.py` | 每角色标定、目标构造与稀疏反向细分补偿；无RLPy/CC操作 | validated_pilot |
| `cc_headshot_creation_references_v1.json` | 男女starter、Average/头皮网格、mask/operator、CC5 profile、支持资产及SHA | 本入口固定引用契约；不是新规范项目晋升 |
| `tests/test_cc_run_character_creation_v1.py`、`tests/test_cc_character_creation_pipeline_v1.py`、`tests/test_run_cc_character_creation_v1.py`、`tests/test_cc_character_creation_job_state_v1.py`、`tests/test_cc_headshot_geometry_solver_v1.py` | 本入口/CC adapter/pipeline/控制器/离线求解器的针对性测试 | 不替代实际CC或两性视觉 |

上述文件位于`%CC_SCRIPT_ROOT%/`；Script Catalog主Owner为本文，不与Assembly9双重拥有。准确源码/配置哈希由准备状态绑定及Catalog重建，不在本文人工复制。

请求必须有`character_id`（安全ASCII、批内唯一）、`sex`（male/female）、整数`seed`，以及互斥的`photo`或`source_project`。`photo`支持jpg/jpeg/png/bmp；`source_project`为用户保存的原始Headshot `.ccProject`。可选`facial_components`复用Assembly9字段：`skin_asset_id`、`eyebrow_asset_id`、`eyelash_asset_id`、`eye_asset_id`及`hair_color_id`/`hair_color_mode`/`visible_gray_fraction`。颜色仍只用于眉毛；本阶段没有头发。默认睫毛固定已实测Lush_Extended资产`CCAPP_EYELASHES_284c3a142668`，其他明确请求的资产没有自动豁免。

`cc_headshot_creation_references_v1.json`绑定既有男女CC5 Average SubD0 starter与14,164顶点参考，逐引用核验SHA。female proportion为Head Scale 0.1/UI10、Neck Height0；male两项均0，沿用已选头颈方案。照片入口先复制starter，以Current + Clean Soft、生成前SubD0执行SDK；原始项目入口复制输入并跳过照片生成。原始照片/项目、规范参考不修改，Bridge只消费独立runtime_staging副本。

### 11.2 固定阶段及几何边界

执行顺序为：照片生成（raw入口跳过）→准备CC5面部配置/头颈及眼口支持→当前角色SubD0捕获→zero/x/y/z四次标定→identity细分往返→离线目标与反向补偿→应用目标/归一→female必要late Bake Morph及再次往返（male引用关闭该步骤）→最终几何捕获→既有基础装配→独立保存。

每次标定与identity roundtrip都从当前角色本次prepared项目开始，不能复用其他身份的仿射矩阵。x/y/z探针是CC厘米坐标+0.1cm（1mm），zero为基准；检查root旋转/缩放一致，仅做明确的平移对齐。目标采用既有Average颈部六环过渡，完整照片面部锁定；最后按面部mask混合固定头皮/耳/颈参考，避免重复颈部过渡。稀疏反向求解复用已有细分operator，但输入标定必须属于本角色。

修正阶段最终SubD0世界网格采用三个范围：非头部对Average最大0.1mm，完整照片面部对本次source最大0.01mm，固定区对选定头皮参考最大0.2mm。阈值来源是既有已接受女性photo01最终实测，不是男女新入口已通过；首个男性执行仍须实际测量。该修正容差与随后装配R06分开：装配仍对自身修正后原点保护各区0.002mm，只有Assembly9证据SHA绑定的具名Lush_Extended原生睫毛片704点可选v2性别规则（female8.2mm、male14.0mm），不放宽皮肤/头皮、其他资产或整个角色。装配配置、颜色契约及同眼睛资产的opt-in材质no-op证明归Assembly9。

### 11.3 系统CLI与串行恢复

在`%LANCE_ROOT%`使用现有系统Python。以下示例默认只准备独立输入/状态，不提交CC：

```powershell
python 00_engine/scripts/character_creator/run_cc_character_creation_v1.py --photo "D:/UE/Lance_Work/CFD Version 3.0/Images/CFD-MR/CFD-MF-302-027-N.jpg" --sex female --character-id NEW_FEMALE_001 --seed 20261005 --prepare-only
python 00_engine/scripts/character_creator/run_cc_character_creation_v1.py --source-project "D:/path/rawHeadshot.ccProject" --sex male --character-id NEW_MALE_001 --seed 20261005 --prepare-only
```

第二行的输入路径需换成真实原始项目。确认配置后对同一请求增加`--execute`；CC须已在现有离线会话打开，由root串行操作。`--request request.json`读取单对象，`--batch requests.json`读取非空JSON对象列表，两者不得混用行内sex/id/seed。`--wait-seconds`为每阶段等待秒数，默认600，要求有限且非负；超时不是失败或重新提交授权。准备/代码/命令成功不等于CC/视觉通过，本轮只执行独立代表请求，未执行真实batch。

控制器独占`controller.lock`，不自动删除未知陈旧锁。准备状态为prepared；实际阶段先持久化pending和固定job_id再调用Bridge，不确定提交/无终态只查询同job，不重发。Bridge succeeded必须再核验报告、source_unchanged及SHA绑定阶段输出才能成为completed。恢复完成阶段逐项核验输入、绑定实现/配置、回执和输出后跳过；新版代码/policy与旧SHA不匹配时必须拒绝，不能用旧completed冒称新版可恢复。女性attempt_002属于male policy扩展前的已完成版本，保留其证据，不以当前代码重新续跑它；failed保留原attempt，新请求从原输入另建attempt；同character_id非failed时请求指纹不同则拒绝，必须用新id。批列表串行，pending/failed立即停止后续角色。

### 11.4 输出与已验证范围

Run Root为`%OUTPUT_ROOT%/character_creator_bridge/artifacts/headshot_character_creation_20261005_v1/<character_id>/attempt_NNN/`，归本文与`OUT-WF30-CC-ASSETS`，默认unclassified保护。runtime_staging位于`%CC_SCRIPT_ROOT%/runtime_staging/headshot_character_creation_20261005_v1/`，只保存独立输入与Bridge配置。主要输出为`request.json`、`creation_state.json`、逐阶段`creation_report.json`及项目/捕获、`06_geometry_target/geometry_report.json`/`target_geometry.npz`/`target_world.obj`、`final_geometry_review.json`、`assembly_manifest.json`、`12_assemble/CHARACTER_<id>.ccProject`与R06回执、最终`creation_result.json`；来源、实现、参考、配方和结果绑定SHA，不是Transfer Bundle。

| 本轮实际证据 | 已验证范围 |
| --- | --- |
| `creation_validation_summary_v1.json` | 读取两入口实际source/结果SHA、三个修正范围和各8装配gate；原input保持，独立保存成功 |
| `PHOTO_FEMALE_001/attempt_002/creation_result.json`与`final_geometry_review.json` | 官方Current + Clean Soft照片入口完整机器流程，female必要lateBake；非头部/面部/固定区最大0.0609244773/0.0064822991/0.1033347438mm；冻结早版v1policy，保存SHA`9e23d42f84fc6199a7a77fc69cab98d2fd626e68f356bfce3e4c802f573d5c99` |
| `PROJECT_MALE_001/attempt_002/creation_result.json`与`final_geometry_review.json` | male原始Headshot项目共用tail当前v2完整机器流程；三个范围最大0.0006139741/0.0006105006/0.1127677240mm，保存SHA`3e7e0b2418ce39a15fbd4602b4308ed83efdbda7fbb235d6b6940d2bc53a41ca` |
| 两角色`12_assemble/assembly_report.json`及`assembly_geometry_invariants.json` | 各8项R06及source_unchanged通过、仅眉毛调色、牙齿口腔沿输入支持；不是新人工视觉/表情审查 |
| `completed_resume_check_v1.json` | 当前male完成状态实际advance禁止submit，0新增提交，state SHA前后一致，同请求CLI完成跳过；旧female代码/policy SHA不同，不宣称当前版本恢复它成功 |
| `user_cli_TEST_FEMALE_002_confirmation_v1.json`、`TEST_FEMALE_002/attempt_001/creation_result.json` | 用户独立运行female照片CLI，seed42、CFD-MF-347-001-N.jpg，当前v2政策完整机器流程及8项装配gate通过；用户随后确认流程成功，未具体声明表情/UE渲染检查 |
| `male_native_lash_diagnosis_v1.json` | 旧male attempt001仅native704睫毛片变动，其他13,460点及Skin0；支持Assembly9独立v2male具名14mm规则，female8.2mm/其他Skin .002不变 |

完整character_creator回归622项实际通过（94.01秒），已包含此前115针对性以及policy新增覆盖，不重复相加；必要doc/dataset/unreal307项为独立运行（25.35秒）。新实现生命周期validated_pilot；Catalog/Inventory已最终重建，`documentation_audit_final_v1.json`实际16独立子系统及cross-layer全部通过，0error/0warning；审计不扩大机器证据的准确范围。

两个新成品未新增人工视觉接受；复用前序单女性装配人工/表情检查只作为被调用模块依据，本轮不重复逐角色全人审。最新用户独立female照片入口已在当前v2完成；未实跑male照片SDK、全部外观池或真实batch；不导出、不做UE导入/渲染，也没有覆盖规范参考/正式UE。前序结项时CC留在男性装配后独立项目；本次只读取用户新运行的已有结果，不操作或重新观察CC。该CC创建计划已归档，结项时显式idle/current=null；随后独立UE/Skeleton试点已获授权，当前对象见PROJECT_STATE，不自动启动批量CC或新导出。

2026-10-05后续独立CLI确认：用户以`TEST_FEMALE_002`、female、seed42和`CFD-MF-347-001-N.jpg`运行当前照片入口，`attempt_001`completed。原输入保持，当前v2三个修正范围最大0.0606400646/0.0063213088/0.1022265448mm，8装配gate通过，项目106,560,413bytes/SHA`10c9b3cebe547c3c50b54e7e129a444ca2741720180dbf0dbe83173a0b2214d2`已独立核对。用户确认该次流程成功；结果与人工结论分开写入新增confirmation回执，原creation/assembly的visual pending字段不改写，不推断具体闭眼/微笑/张嘴或渲染检查。已关闭计划作为当时快照保留，无新current/批量执行授权。

本次确认同步的Catalog/Inventory已重建，`user_cli_confirmation_documentation_audit_v1.json`16独立子系统/cross-layer全通过、0错误警告；必要doc/dataset/unreal回归`user_cli_confirmation_regression_v1.txt`为307 passed（25.33秒）。没有重复角色全功能测试、执行新CC/UE工作或更改既有通过范围。

### 11.5 保留Headshot原生外观的几何修正入口

本节唯一拥有`%CC_SCRIPT_ROOT%/run_cc_headshot_geometry_only_v1.py`、`cc_repair_headshot_support_materials_v1.py`及`tests/test_cc_repair_headshot_support_materials_v1.py`。薄CLI复用11.1的adapter/pipeline/controller/solver，固定`appearance_mode=headshot_native`，旧入口缺省`assembled`不变。native不随机更换皮肤/眉毛/睫毛/虹膜、不染眉毛、不执行12_assemble；`facial_components`被拒绝，薄CLI不能通过`--appearance-mode`改为其他模式。seed用于请求记录/指纹，本分支不以它随机选择外观。

#### 输入与固定过程

照片和原始Headshot项目仍二选一，照片使用对应CC5 Average SubD0 starter、Current + Clean Soft。按11.2逐角色四轴标定/反向补偿修正身体与固定头皮，female必要lateBake；最终身体/照片面部/固定区容差分别0.1/0.01/0.2mm，与外观装配R06的.002mm分开。native没有替换Lush睫毛，不调用该具名豁免或8项装配Gate。

历史START的眼睛/牙齿/舌头为灰材质、睫毛含缺失占位，原native省去了成熟流程的必要support修复，这是实现遗漏。现在独立修复过的男女starter已通过`cc_headshot_creation_references_v1.json`中的`sexes.<sex>.native_starter_project`及`native_starter_evidence`供native照片入口选择；旧`starter_project`及所有旧字段/规范文件保持，assembled继续使用旧路径。当前references SHA为`817941d45a3dfea388f3bc0e2c1d4b2ba9ac0ec329c666a238d810ecc71e679f`，激活/旧快照反查同Run Root`native_starter_reference_activation_v1.json`，新旧状态不能跨SHA冒称完成恢复。

support repair是独立副本受限的眼睛/牙齿材质、睫毛/舌头Diffuse修复，不是随机装配；不改皮肤/眉毛、比例或细分。它递归检查Body及眼睛/牙齿等附属网格、拓扑、部件和owner局部/世界Transform，原文件不覆盖。raw项目入口保留用户提供外观；本次两个generated副本的显式repair与尾段恢复有独立回执，不把材料健康自动外推到任意raw输入。

#### 使用与恢复

从%LANCE_ROOT%准备新ID的独立请求：

```powershell
python 00_engine/scripts/character_creator/run_cc_headshot_geometry_only_v1.py --photo "D:/UE/Lance_Work/CFD Version 3.0/Images/CFD-MR/Female/CFD-MF-341-018-N.jpg" --sex female --character-id NEW_NATIVE_FEMALE_001 --seed 42 --prepare-only
python 00_engine/scripts/character_creator/run_cc_headshot_geometry_only_v1.py --source-project "D:/path/rawHeadshot.ccProject" --sex male --character-id NEW_NATIVE_MALE_PROJECT_001 --seed 42 --prepare-only
```

第二行替换真实原始项目。默认prepare-only；同请求改`--execute`才提交已打开离线CC，pending只查询同job、完成只在来源/实现/配置/结果SHA一致时跳过，失败保留attempt后独立恢复，详11.3。不要用历史completed ID演示新refs/代码恢复。batch语法继承，但本次没有执行角色batch。

正常native分支在11_final_capture/最终几何检查后结束，`creation_result.json.result_project`为实际独立corrected保存项目，不能假设存在12_assemble/CHARACTER_<id>.ccProject。本次异常恢复分别由`repair_result.json`/`recovery_result.json`定位交付，入口汇总为同Run Root`native_creation_delivery_v1.json`。Run Root及输出归本节/OUT-WF30-CC-ASSETS，默认unclassified保护；一次性Run内pilot/tail helper为保留复现工具，不混成通用生产入口。

#### 实际范围与证据

| 当前证据 | 已通过范围 |
| --- | --- |
| `NATIVE_MALE_001/attempt_001`及`native_geometry_only_real_run_interruption_v1.json` | 指定男性照片Current/Clean Soft实际生成/保存；03加载崩溃，原failed保留，用户重开后消费孤儿终态而未重提原job |
| `NATIVE_MALE_001_RECOVERY/attempt_001/final_geometry_review.json`、`native_male_photo_recovery_appearance_v1.json` | 从原照片已保存项目完整raw修正成功；body/face/fixed最大0.000612073/0.000457863/0.038839555mm，均通过；原照片生成后→恢复最终native元数据保持，恢复03→11 UV布局另通过 |
| 四个`NATIVE_SUPPORT_REPAIR_<SEX>_<STARTER/GENERATED>/attempt_001/repair_support/support_repair_report.json` | 独立四副本success/source_unchanged，保存及重载各12网格局部最大0mm/owner Transform保持，睫毛opacity SHA不变；lash/tongue直接RGBA与donor一致 |
| `native_support_photo_retention_result_v1.json` | female修复starter再用指定照片Current/Clean Soft生成，双眼实际2048纹理含棕色虹膜并被查看；睫毛2048/舌头1024 Diffuse完整SHA等于donor。仅此female生成保持probe，不外推male同新starter的完整重跑 |
| `NATIVE_FEMALE_001_TAIL_RECOVERY/attempt_002/recovery_result.json`与`final_geometry_review.json` | 原female01–08生成/标定/修正已保存，09首次模块路径失败；独立修复checkpoint后只补08b/09–11，不重做照片/标定，不改旧failed；body/face/fixed最大0.061278965/0.006487264/0.115707174mm，均通过，metadata/部件/拓扑/UV保持 |
| `native_starter_reference_activation_v1.json` | 男女native starter字段真实激活，旧字段全部保持，逐SHA加载通过；不是把新refs回写进旧已完成状态 |

男性最终交付是`NATIVE_SUPPORT_REPAIR_MALE_GENERATED/attempt_001/repair_support/support_materials_repaired_subd0.ccProject`，SHA`6b1415fbc0594921223367c168597147e071a509249501297744fa363094e056`；女性为`NATIVE_FEMALE_001_TAIL_RECOVERY/attempt_002/10_post_bake_roundtrip/roundtrip_subd0.ccProject`，SHA`7a94d962fa533d2244d3c1d0971c14b47269c542cad59dfeb653c960c05e028a`。不声称两次原photo attempt连续无中断完成，也不声称新refs版本已完整CLI批量执行。

native completion guard以照片01生成后（raw以02之前）与11最终的可采材质名称/参数、部件/拓扑为基线；Body OBJ vt/usemtl/f比较03与11。通用snapshot纹理getter仍0样本/272观测错误（SwigPyObject.isNull），不能由guard passed宣称纹理逐像素保持。专项support repair/reload与female照片保持probe另有实际Diffuse file/RGBA SHA证据，不能扩成所有纹理/所有角度；当前女性CC代表外观已获用户直接验收，见下段；男性单独人工外观与新的表情测试未取得，无UE/导出/batch接受。

用户于2026-10-06检查当前CC女性代表后直接说“检查完毕。所以到现在我们的角色创建流程可以看作完成了是吗？接下来先完成UE各项设置，固定导出导入配置再批量对吗”。`native_user_visual_acceptance_20261006_v1.json`绑定原delivery/当前女性项目及恢复回执SHA，记录该女性代表静态可见外观人工通过，native CC创建阶段在此代表范围accepted；不捏造男性单独视觉或新的闭眼/微笑/张嘴检查。 下一阶段先完成UE相关设置及导出/导入配置冻结，再按另行授权进入批量；此顺序是讨论确认，未新增UE/配置冻结/batch接受或执行。

最终当前源码针对测试`native_starter_final_targeted_tests_v1.log`66 passed（runtime53、repair10、selection3）；此前controller/pipeline/CLI86和各版runtime46/50为对应版本证据，不重复相加为新完整套件。必需documentation/dataset/unreal的`native_geometry_only_required_regression_v1.txt`342 passed/42.66s独立运行，未为每次CC阶段重复。Catalog/Inventory已重建，`native_geometry_only_documentation_audit_v1.json`实际16独立子系统及cross-layer全通过、0错误/0警告；未重复342必要回归。共享项目的其他会话主计划不被本可选入口替换，不创建第二current或启动动作/UE任务。

本次人工验收同步已重建Catalog/Inventory；同Run Root`native_user_visual_acceptance_documentation_audit_20261006_v1.json`实际16独立子系统及cross-layer全通过，0错误/0警告。代码未改，沿用66针对测试与342必要回归，不重复执行CC或UE。


#### 正式照片来源与双人转移小样（2026-10-06）

用户已确定后续正式照片只取`%LANCE_ROOT%/CFD Version 3.0/Images/CFD-Combined/{female,male}/cfd`，排除`cfd-india`与`cfd-mr`。未来A/B/L/W四族群等量抽样，40人例子为各10；这条规则不另行确定男女比例。本轮两人例外为男女各1，分别均匀抽族群再均匀抽组内照片，允许同族群。实际seed、候选计数/顺序及选中来源SHA由`%OUTPUT_ROOT%/unreal_character_import/cfd_native_pair_20261006_v1/sampling_manifest.json`固定；不是只在全部照片里直接随机，从而令大族群更易入选。

本轮选中`CFD_NATIVE_MALE_001`（W/CFD-WM-230）和`CFD_NATIVE_FEMALE_001`（A/CFD-AF-200），两张源照片SHA已核对，两人native创建/修正已机器完成，完整导出/UE审查双人试点也获用户直接验证通过。源来源规范替代后续选图范围，不改写本节历史CFD-MR照片实验。新创建/恢复仍在既有headshot_character_creation_20261005_v1的独立ID下，完整转移小样与本次授权边界见[Transfer13](../transfer/CC_TO_UE_MODULAR_OUTFIT_PILOT.md#13-cfd原生男女双人完整转移试点2026-10-06)。本次新两人通过依据runtime/user_final_validation_v1.json的独立用户验证，不复用旧女性静态结论；流程可进入以后获授权的批量创建，当前仍未授权启动正式batch，等待用户明确通知。


#### 已授权40人native创建批次（2026-10-06）

用户授权A/B/L/W每族5男5女40人，只取CFD-Combined/{female,male}/cfd、不含india/mr；sampling_manifest(seed20261006)、40creation_requests与准备审计保持。复用Current+CleanSoft、对应修复starter、身体/固定头皮修正和独立保存，不随机重装外观。初次40prepared/步骤0记录为启动前历史。

用户批准的R00男女同性交享Skeleton有限root_visual_smoke已通过，R01准备完成，R02实际机器创建已全部完成；R03完整导出已通过文件/贴图闭包与40份离线导入清单核验，后续40人UE导入与5页静态审查机器交付已完成，人工视觉验收pending。AF002独立恢复与AF003新照片角色全程通过属于历史route SHA9e88be…fb156范围，旧失败、阶段来源与几何/native appearance回执保留，不能视为新修复验证。历史执行由root串行操作CC/UE，监视子agent曾每30分钟只读检查。当前CC已正常退出，全部机器交付控制器正常结束；monitor已确认停止、automation PAUSED，AutoSave已恢复原True。另一会话唯一current服装诊断保持，精确进度由独立PROJECT_STATE/execution_record拥有。


40人Run内run_complete_exports_v1.py和test_complete_exports_v1.py由本节拥有，作为该批次一次性完整FBX导出恢复工具，不扩全局Script Catalog生产入口。complete_export_entry_readiness_v1.json实际ready_for_root=true/actual_export_not_started=true，最新收据为10项测试通过（早期9项历史保留）。只在40个latest CC attempt全部completed后读取实际creation_result.result_project，独立一次/人完整FBX/JSON/纹理SHA收据；pending同job续查不重提、failed保留、completed恢复校验纹理SHA。route_validation仅追加固定batch40导出root白名单，准备审计历史SHA978ec7a094467e69d86f4d5ef24927144be493034413457d4d9a394613ae18f2；该收据描述导出准备时历史，不代表当前创建进度。正式CC40已在Transfer14/R00有限代表smoke通过后启动并全部机器完成。run_complete_exports_v1.py已在实际40完成后prepare、执行并全部完成；终态文件/贴图引用与40份离线导入清单通过证据为complete_export_handoff_v1.json，当前UE及人工接受范围由execution_record拥有。


Run内共享probe审查工具ue_shared_probe_review_v1.py、ue_shared_probe_bone_clip_v1/v2.py、ue_probe_shared_face_retargeting_v1.py及test_shared_probe_review_v1.py由本节拥有，不扩全局生产Catalog。shared_review_helper_readiness_v1最新离线收据7passed/0.19秒（早4项为历史）；root实跑头部/代表动作结果与剩余TranslationRetargeting设置由Transfer14.2及executionrecord记录。Morph权重可读不等于闭眼/完整张嘴通过，v1横扭不接受，v2与双方Skeleton平移模式完成后root有限五项smoke已通过，R02正式启动；不等于穷尽表情或用户整批视觉接受。

Run内`recover_af001_late_bake_v1.py`及`test_recover_af001_late_bake_v1.py`由§11.5拥有CC尾段修正/几何语义，Transfer14拥有标准状态晋升/批次resume收据；一次性run工具不扩全局生产Catalog。真实3针对测试通过，仅重试09并续行10/11、独立保留原失败，冻结核心SHA不变。

2026-10-07，BF001原09及v2/v3恢复三次均在Bake调用前失败：采集后的候选动作消失或最终Qt包装对象失效，缓存ready=true不能代替可调用性。%OUTPUT_ROOT%/unreal_character_import/cfd_native_batch40_20261006_v1/BF001_qt_lifetime_diagnosis_v1.json保留三次失败及只读对照；实际CC中保留窗口/父子包装引用后，同C++指针在observer返回前后均有效，证明引用保留相关性，不宣称底层C++析构机制已确定。当前本批次执行源码SHA9b1dbb…c905f保留allWidgets和匹配动作父链引用到invoke结束，维持精确唯一选择、两轮稳定及invalid拒绝，原HeadScale/局部几何/保存重载代码未改；13项针对测试通过，历史06b/4b36版本分别11/12项不得混写。Run内cc_bake_control_lifetime_probe_v1.py/v2.py和两组readiness tests由本节拥有，属本次诊断与恢复实现，不扩通用生产入口。

%OUTPUT_ROOT%/unreal_character_import/cfd_native_batch40_20261006_v1/bake_control_lifetime_probe_v2.json已在CC真实通过。BF001 v4随后完成限定尾段恢复：%OUTPUT_ROOT%/character_creator_bridge/artifacts/headshot_character_creation_20261005_v1/CFD40_BF_001/attempt_001/creation_result.json为completed，最终项目SHA cb3b24ec…bd4484；09真实trigger为1.984秒/2poll，route回执local_meshes_exactly_preserved=true，10保存重载与11捕获完成，final_geometry_review与native_appearance_review均passed。native_appearance_review按既定结构/材质摘要边界passed，但before/after各保留272项SDK观察错误（SwigPyObject缺isNull）；不升级为完整纹理像素、视觉或UE接受。 三次原失败及分阶段来源保持，recover_female_late_bake_v2.py及其helper tests由本节拥有；归档/pin迁移与标准result晋升由Transfer14拥有。这段证据描述BF001有界恢复时的历史检查点；后续创建阶段已整批机器完成，完整导出和人工验收仍分别待判定，实时进度由独立执行记录拥有。


#### CFD40创建完成阶段记录（2026-10-07，创建后历史检查点）

`%OUTPUT_ROOT%/unreal_character_import/cfd_native_batch40_20261006_v1/creation_complete_checkpoint_20261007_v1.json`由本节拥有。它只读核对冻结请求对应的全部最新canonical state/result均completed、最终项目记录一致且文件存在、geometry/native review文件SHA及passed标记；保存每个实际回执引用。source二进制闭包由完整导出controller核对，本阶段不重复读取所有大文件或重跑已通过回归。native检查仍受已记录SDK材质观察范围限制；创建机器完成不等于逐人视觉或新的表情、UE验收。

原创建controller PID4044已正常结束，creation_resume_20261007_0027.log在07:23以WF005 completed结束，07:27:58创建终态检查保持历史。完整导出controller PID17868于07:31启动，日志标签0735不是开始时间，现已正常结束。complete_export_handoff_v1.json记录40/40、1,560文件、4,587,479,631字节的SHA/贴图引用闭包及40份离线import manifests核验通过；每人6部件、118骨、2455跨网格Morph通道是源统计，不等于动态或视觉接受。root正常关闭CC并拒绝保存导出后临时场景，08:41复核PID39816已不存在。新误启动sandbox UE41312在导入前终止；正确可见Macheniek候选UE25256仍启动中，待身份readback。Computer Use已停用；UE导入0，最终5×8交付和人工审查pending。

BF001三次pre-invoke失败、AF001/AF002恢复、历史源码及pin迁移证据原样保留；没有改creation state/result/source/helper或任何输入哈希依赖。独立scope同步到PROJECT_STATE与execution_record，不改变另一会话唯一current服装诊断计划。本次只做阶段一致性核对，最终Catalog/Inventory与全审计待真实导出导入完成后统一执行。

#### CFD40后续机器交付终态（2026-10-07）

本CFD40独立scope已完成创建、完整导出、完整UE导入与静态审查机器交付。40人导入/来源完整性见final_import_summary_v2.json；review_pages_verification_v1.json确认单关卡5页×8覆盖40unique，代表focus/side/head/nohair控制及最终第1页full/front/hair保存通过。AutoSave原值True已恢复，monitor停止、automation PAUSED。后续用户有限静态审查已通过（Runtime3.15.3），不推断全动画/服装或最终渲染接受；若UE重启需重新绑定当前实例。旧故障及恢复pending段落保持历史，当前以execution_record/final_delivery_checkpoint_v1为准。 创建source及失败/恢复证据原字节保持；末端UE数据由Transfer14、审查操作由Runtime3.15拥有，final_import_summary_v1中的review pending属于创建/导入阶段历史，由v2交付终态补足。548规定回归已实际通过，不因纯文档闭合再次运行。


#### CFD40校准检查点退役（2026-10-11）

用户授权的独立工作区深度清理见 [Output 清理说明](../output/INVENTORY_AND_RETENTION.md#2026-10-11-工作区深度清理独立补充)及 `%OUTPUT_ROOT%/asset_cleanup/cleanup_20261011_deep_v1/`。逐角色删除决定和替代文件 SHA 在 `reviewed_plan.json.character_retirement`，实际是否删除以 `execution_receipt.json` 为准。普通成功案例的 02/04/05/07/08/09 阶段 `.ccProject` 校准副本退役；40 人最终 `result_project`、`01_photo` 原始照片生成项目、输入/参考、数值几何证据及原始 state/result 保留。AF001、AF002、BF001 特殊恢复链整体保留。

因此旧 CFD40 完成任务的逐步骤输出重验/断点重放不再是受支持入口：当前 driver 会校验历史各阶段文件，退役文件必然导致该旧任务校验失败。后续装配应消费保留的最终项目；确需重跑创建时使用保留输入和新的任务 ID。该变化不代表旧角色创建失败，不改写原完成回执，也不通过修改生产代码绕过校验。保留结果及当前素材的哈希核验由本次 `verification.json` 记录。

#### 原生睫毛被固定头皮目标覆盖：CC修复交接（2026-10-17）

本节拥有 `%OUTPUT_ROOT%/hair_only_review_20261017_v1/diagnosis/eyelash_source_audit.md` 的CC源几何诊断与后续修复建议；它沿用现有审查Run的run_evidence、默认unclassified保护，不新增生产入口。完整证据、源项目/FBX哈希、当前材质探针与最少UE对照见[睫毛源审查](../../../../../../00_engine/outputs/hair_only_review_20261017_v1/diagnosis/eyelash_source_audit.md)。本次只读定位及文档交接，未修复pipeline、重建CC、重导入或改变任何Gate/计划/状态；已验证数值限于CFD40_WF_003，不外推全部40人的位移大小或两张未绑定人物身份的用户截图。

`cc_headshot_geometry_solver_v1.py::build_desired_world` 最终按面部遮罩对整个 `head` 集合混合 `scalp_reference`。当前原生Body拓扑的具名 `Std_Eyelash` 704点（局部索引13411–14114）全部落入head，但面部权重全0，因此被替换为参考角色的睫毛位置；照片眼皮仍按照片面部保留。704索引已与本机资源材质面提取结果及WF003顶点面集合核对，不是按高度或包围盒推测出的眼部区域。WF003现存 `06_geometry_target/target_geometry.npz` 中这704点的desired_world精确等于scalp_reference，相对本次照片source_world位移最大6.698737607mm、平均5.928999081mm；最终 `11_final_capture/before_world_mesh.json` 相对照片源最大6.708343559mm、平均5.928970674mm，相对scalp目标仅最大0.044789648mm、平均0.000934417mm。final capture、creation_result及UE import_manifest绑定同一最终CC项目SHA，说明该目标实际进入保存源，而非只存在于未执行计算。

这解释了为何旧几何检查会通过：睫毛被纳入固定区域后，靠近参考睫毛反而满足固定区要求，不能证明睫毛仍贴合该人物眼皮。当前UE回读为Body材质槽5的睫毛，无独立睫毛组件，基础眼支持件同属WF003；探针未报告非零Morph，UV平铺/偏移为默认值。因此目前优先处理源几何分区错误。透明材质局部排序、原照片阶段睫毛是否已错位，以及其他人物仍需按各自证据判断；本段不代替root的隐藏睫毛对照或正式视觉验收。

**后续源修复建议，尚未实施：**在最终scalp混合之后，将经过当前拓扑校验的704个原生睫毛点 `desired_world` 显式恢复为该人物本次照片的 `source_world`，或实现等价的互斥区域规则。只从head集合删去睫毛不够：现函数会把outside-head点恢复成Average，仍会误移动。固定头皮皮肤必须与原生睫毛分区不相交；新增检查应直接验证原生睫毛相对本次照片源的保留，并维持原身体/照片面部/头皮要求，不使用另一条Lush_Extended装配路线的位移容差豁免本错误。先检查照片生成后的睫毛本身是否贴合；若已错位，还需该人物的独立CC眼睑/睫毛校正，单纯保留原始坐标不能宣布修好。

先在新ID的WF003派生候选中沿用逐角色坐标标定、逆细分补偿、CC应用/规范化、女性必要lateBake与保存重载，再完整导出骨骼、Morph、FBX/JSON/纹理，独立UE导入对照；旧completed任务因检查点退役不能直接续跑。不要只在UE推回中性睫毛顶点：Body有395项形变，旧形变delta、蒙皮及眨眼支持不能由中性外观自动保证。候选需检查中性正面/侧面、双眼完整闭合、左右单眼眨眼、上下视线，确认无悬空/穿眼球及新闭眼缝，才决定正式替换与后续批量范围。当前没有执行上述修复、男女代表新验证或40人回溯。

## 12. CFD照片形态选样与CC多样性候选研究（2026-10-07）

本节拥有`analyze_cfd_face_diversity_v1.py`及`tests/test_cfd_face_diversity_v1.py`，输出根`%OUTPUT_ROOT%/character_creator_analysis/cfd_face_diversity_20261007_v1/`，沿用OUT-WF30-CC-ASSETS的身份研究run_evidence、默认unclassified保护。仅离线读取照片与官方测量表，不驱动CC/UE、不修改既有角色或正式Identity Registry，不另立current计划。

### 方法、输入及边界

只取CFD-Combined/{female,male}/cfd，按已有AF/AM/BF/BM/LF/LM/WF/WM标签分组；元数据标签逐项匹配，并非从脸推断性别或族群。使用CFD 3.0 Norming Data and Codebook.xlsx的CFD U.S. Norming Data客观测量构造9个比例，覆盖眼裂/眼宽、鼻宽/鼻长、唇厚、中脸长度、下巴长度与下脸轮廓。眼和鼻各0.25、唇0.20、中脸0.15、轮廓0.15；各组独立median与1.4826×MAD标准化，MAD为零回退std、常量置0，裁剪±3后算weighted RMS。缺测/非有限或非正测量直接拒绝，不填0。每人输出最近/最远5个同组样本及组内对称距离矩阵。

它是官方二维形态差异的选样辅助，不是人脸识别embedding、完整容貌相似度或相似百分比；不用主观评分、肤色、头发或FaceLength发际线字段。组间尺度不同，不能据此比较男性和女性谁更多样。权重、裁剪与贪心maximin是启发式，既非人口代表抽样也非全局最优；照片差异不预测Headshot及固定头皮修正后的保留差异。

### 复现与输出

`python 00_engine/scripts/character_creator/analyze_cfd_face_diversity_v1.py analyze`默认写本Run。`python 00_engine/scripts/character_creator/analyze_cfd_face_diversity_v1.py select --groups AF AM BF BM LF LM WF WM --k 5 --seed 20261007 --exclude-used --output <new_candidate.json>`只产生候选，seed首样本后逐步最大化最小组内距离，ties按ID；--exclude显式排除subject ID，参数/候选不足直接报错，不启动角色创建。

analysis.json绑定源码/输入SHA、特征、组内标准化、每人照片与邻居；photo_features.csv与8份矩阵用于离线复查；selection_example_k5.json为40个未授权生成的候选示例；index.html及597缩略图便于人工选样。analysis_check.json记录照片可读/唯一、测量有限、元数据匹配、矩阵对称零对角等内部一致性，不冒称感知或Headshot验收。HTML仅静态检查，未在浏览器交互实测：Computer Use仅导入弹窗的现有授权不覆盖打开网页，自动审批拒绝后未绕过。

cc_diversity_options_research.md由本节拥有，基于官方资料与本地既有能力讨论局部皮肤细节、贴图胡茬/立体短须、轻量表面年龄、虹膜和后置动态皱纹。全部新效果仍是候选；不将同一人的纹理状态计作不同身份。暂不改变固定身体/头皮、照片脸几何、骨架或native默认保留眉睫的契约。后续若另获授权，按CVPR时间约束只试一名代表/一项变化，复用保存重载和UE对照；不扩全矩阵，也不要求先新建不变量模块。

CFD40用户已完成静态审查，无明显问题、男女面部差异可见而女性主观变化小；用户回执归Runtime3.15，不由本照片分析反向代替该人工结论。实际analysis_check确认597照片、8组23,705组内pair、无缺测/不可读/重复身份或照片；此前40人全部匹配。offline_delivery_check.json确认代码SHA、select CLI两次字节一致、8组各5共40unique，排除旧40及双人pilot共42人；selection_new_candidates_k5.json绑定最新analysis SHA。HTML597缩略图引用全存在，Node --check通过且无fetch/external runtime，但未交互实测。575规定/新增回归实际通过（548+27、0失败/跳过），只运行本轮一次；错误测试路径的0收集失败另保留，不混入通过结果。Run内README.md、verify_offline_delivery.py、offline_delivery_check.json、execution_record_v1.json、documentation_required_regression_v1.xml/.txt及documentation_audit_final_v1.json由本节拥有；准确SHA/状态在独立scope和执行记录，候选未授权生成或新增外观实施。

本次最终documentation_closure_v1.json由§12拥有；615脚本/136输出范围目录重建，16独立子系统及cross_layer检查均0错误/0警告。研究含局部唇色/淡妆这一额外可选候选，保护原皮肤基础及眉睫、不改几何、不算新身份，也未实施。研究和README最终SHA由closure绑定，575回归不重复。

### 后续选样策略确认：平均两两差异（2026-10-07）

用户确认后续新人物选样可采用多起点局部搜索：保持8组及指定配额，复用已有距离矩阵，以所选k人全部两两距离的平均值为主要目标（5人为10对）；多次随机起始、逐人替换到无改进，再取最佳组合。固定种子并记录起点数、停止条件、输入版本与排除名单；同分稳定按ID排序。不承诺全局最优或人口代表性。另报告组合中最接近的一对及距离，但不把它设成未经确认的硬约束。

本节拥有Run内`FUTURE_SELECTION_POLICY.md`。该设计已确认、实现待后续选样/创建授权时进行；当前select CLI仍是贪心maximin，既有示例结果不重标、不重算，本次不改代码或创建角色。CC新增外观候选由用户明确暂缓，不执行。此处是未来选样决策，不改变另一会话current计划，也不把旧完成分析的哈希回执覆盖成新算法证据。


### 2026-10-18 独立原生几何修复候选（验证进行中）

本节拥有`cc_native_geometry_repair_candidate_v1.py`和`run_cc_fresh_final_geometry_repair_v1.py`及对应离线tests，状态experimental。输出汇总位于`%OUTPUT_ROOT%/character_refresh_20261018_v1/`，CC实跑沿用Bridge允许的headshot_character_creation_20261005_v1根并使用REFRESH新ID，源原件不改。当前40份01_photo保存路径实际缺失，不能按旧已完成任务resume；40最终项目仍在。候选使用保留照片source_world及最终项目新副本，704睫毛源坐标保留与下颌局部拓扑过渡分别验证，不能把固定头皮保护自动扩到睫毛。

男女离线候选已有，WF003正在真实CC新标定、逆细分补偿、应用及两轮保存重载；未通过视觉和表情前不宣布修复完成。不重复prepare或女性比例烘焙。准确输入和SHA、各job及阶段结果由Run执行记录与REFRESH候选repair_state.json拥有。新helper使用既有VAL-CC-01/VAL-CC-02与OUT-WF30-CC-ASSETS限定证据，不晋升40人。
