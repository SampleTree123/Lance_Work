# 自然面部动画调研：现成片段、视频捕捉与身体动作组合

> 调研日期：2026-10-05。范围：本机素材、现有代码与 Reallusion／Epic 官方资料。
> 状态：研究建议。没有播放候选素材，也没有操作 CC／UE、调用 Bridge、导入导出、安装插件或修改生产脚本。
> 本文补充[角色与动画衔接核查](./cc_ue_transfer_review_20261005.md)，不改变角色工厂当前 Plan、Status 或验收结论。

## 1. 结论：先挑现成表演，不从手工表情重新做起

我们的目标是让角色在站立、走动、等待时会自然眨眼，眼神和嘴部有少量变化；暂不做丰富情绪、说话口型或新的表情编辑轴。

**推荐先检查本机已有的中性 `.iTalk` 面部片段，挑出 2–3 条适用片段。效果不足，再考虑 Digital Soul；需要自己录制时，再研究视频捕捉。**这比立即建立完整面捕工具链更符合当前目标。

这里要分开两件事：

- **表演从哪里来**：完整的现成动画或真人录制，可以减少手工调眨眼、嘴角和眉毛的工作。
- **脸怎样动起来**：这些表演进入 CC／UE 后，仍可能同时依赖面部骨骼和 Morph（控制眼睑、嘴唇等形状的变形数据）。换表演来源，不代表可以关闭 Morph。

当前已经确认素材与接口存在；**自然程度、不同身份上的效果、与新身体动作组合后的表现，都还没有实测。**

## 2. 本机已有候选：无需先购买素材

以下文件均已做只读存在性与大小核查。目录和文件名帮助筛选，但不能证明片段自然、没有说话口型、没有头部动作或可无缝循环。

| 顺序 | 本地候选 | 本次确认 | 下次检查目的 |
| --- | --- | --- | --- |
| 第一组 | [01_Neutral_Lo.italk](<D:/CharacterCreator_sucai/Reallusion Templates/Animation/Expression/Expression_Loop/Neutral/01_Neutral_Lo.italk>) | 1,393,582 字节 | 优先寻找轻微、中性的动态表现 |
| 第一组对照 | [Gentle_Female.iTalk](<D:/CharacterCreator_sucai/Reallusion Templates/Animation/Expression/Expression Wrinkles/Sample Animation/Gentle_Female.iTalk>) | 16,506,329 字节；位于 Sample Animation | 比较较完整的面部表演，判断是否过强 |
| 中性备选 | [02_Neutral_Med.italk](<D:/CharacterCreator_sucai/Reallusion Templates/Animation/Expression/Expression_Loop/Neutral/02_Neutral_Med.italk>)／[05_Neutral_Short.italk](<D:/CharacterCreator_sucai/Reallusion Templates/Animation/Expression/Expression_Loop/Neutral/05_Neutral_Short.italk>) | 1,395,124／434,090 字节 | 比较变化幅度、时长和衔接 |
| 第二组 | [HD Idle_M.iMotionPlus](<D:/CharacterCreator_sucai/Reallusion Templates/Animation/Motion Plus/1.Acting/01_Male/CC5 HD/HD Idle_M.iMotionPlus>) | 3,666,173 字节 | 检查 CC5 HD 男性完整表演 |
| 第二组 | [HD Idle 01_F.iMotionPlus](<D:/CharacterCreator_sucai/Reallusion Templates/Animation/Motion Plus/1.Acting/02_Female/CC5 HD/HD Idle 01_F.iMotionPlus>) | 4,682,829 字节 | 检查 CC5 HD 女性完整表演 |

CC5 官方说明，HD MotionPlus 模板用于预览身体与面部表现，可从 Animation Player 应用。这支持把 HD Idle 纳入候选，但不是这些具体文件的逐片质量证明。[HD Animations](https://manual.reallusion.com/Character-Creator-5/Content/ENU/5.0/04-HD-Contents/HD-Animations.htm)

**先试 `.iTalk`，因为它属于面部素材；MotionPlus 可能同时带身体、面部、口型和声音。**不能把完整 HD Idle 直接覆盖到用户新选的身体动作上，再误认为已实现独立组合。[CC 素材分类](https://manual.reallusion.com/content-manager/2.0/01-user-interface/category-buttons-for-cc.htm)、[MotionPlus 内容说明](https://manual.reallusion.com/iClone-8/Content/ENU/8.0/55-MotionPlus/What_is_MotionPlus.htm)

本机共享素材目录不等于已安装 iClone。本轮检查常见安装目录和安装记录后，仍未确认 iClone 的安装及版本。上述文件大小也只是源素材大小，不能用来推算 UE 动画大小或角色导入后的存储节省。

## 3. 现有素材不够时，优先看 Digital Soul

**Digital Soul 100+ 是现成面部表演库，最贴近“少量自然表现”的需求。**官方列出 146 条、约 25 分钟，包含意识／观察、情绪、说话与倾听及扩展表演。我们应优先筛观察、等待、倾听方向，不必整包采用。[官方介绍](https://www.reallusion.com/ContentStore/iClone/pack/digital-soul-100/)

官方人员确认格式是 `.iTalk`，CC4 与 iClone8 都可以应用。因此，使用单条素材不应被写成“必须先安装 iClone”。更细的片段拼接、循环和分轨编辑，才需要进一步评估编辑工具。[官方发布与答复](https://forum.reallusion.com/513998/Digital-Soul-100--for-iClone-8-CC4-Now-Available)

边界有三点：

1. 官方说明中，16 条扩展附赠片要求 140+ Extended Profile；不能把这个条件扩大成整包都必须换成 HD 配置。
2. 本机按名称搜索未发现 Digital Soul；这不证明用户没有账户授权。具体价格、账户权益与逐片文件名未确认。
3. 面部片也可能带头颈运动。iClone 的表情时间轴可分 Muscle、Eye Blink、Eyeball、Head 层，但删去头部动作后是否仍自然，要重新看效果。[表情分轨](https://manual.reallusion.com/iClone-8/Content/ENU/8.0/50-Animation/Pro_Facial_Animation/Facial_Timeline.htm)

另一个候选是 **AI Assistant Resource Pack**：官方确实列有 70 条包含待机、倾听和说话的 `.iTalk`。不过所属插件面向 iClone8 Enterprise；能否独立取得素材未核实，因此暂不作为首选，也不因页面写 free 就当作可直接使用的免费库。[资源说明](https://manual.reallusion.com/iclone-ai-assistant-plug-in/content/resource.htm)、[产品范围](https://manual.reallusion.com/iclone-ai-assistant-plug-in/content/welcome.htm)

## 4. 真人视频路线：有官方方法，但现在不必先上

### 4.1 MetaHuman Animator：优先评估动画回 CC

MetaHuman Animator 的作用是从录制素材计算面部表演。Reallusion 已提供官方转换路线：

**UE 得到面部表演 → Export CC/IC Facial Animation 导出 CSV → CC 导入 MetaHuman Facial Animation → 当前角色计算实际表情 → 导出完整面部动画。**

官方导入步骤明确允许排除录制的头部旋转。这与我们让身体动画保留转头和脖子运动的目标一致。该路线不要求替换生产角色的脸，也不要求把角色变成 MetaHuman 身体。[官方 CSV 转换流程](https://manual.reallusion.com/Metahuman-Interoperability/Content/MetaHuman-Interoperability/17-Metahuman-Interoperability/Transferring-UE-Expressions-to-CC.htm)

从项目接入成本判断，先让 CC 在当前身份上计算表情，再复用已有完整骨轨＋曲线导出方法，较容易保持现有网格和渲染组织。**这是路线判断，不是当前版本已经跑通。**Reallusion 导出的 CSV 也不能与手机原始 ARKit CSV 混为一谈。

### 4.2 也能直接在 UE 驱动 CC，但会改动角色组织

官方另一条路线是：导入含 Morph 的 CC 角色，生成 CC Control Rig，将网格拆成 Face／Body，再用普通单目视频生成面部动画。它保留 CC 身份，但引入独立的面部组件和控制结构。[官方视频到 CC 流程](https://manual.reallusion.com/Metahuman-Interoperability/Content/MetaHuman-Interoperability/17-Metahuman-Interoperability/Converting-Expressions-from-Video-to-CC-Characters.htm)

我们的现有入口是一个 Body 播放合成动画，因此这条路线还需接入面部组件、身体跟随和控制分工。它适合作为备用验证，不能直接替换当前导入流程。普通视频路线不要求先购置深度摄像设备；手机 Live Link Face 只是部分采集路线的来源，不是所有路线的前提。[Epic 插件与输入说明](https://dev.epicgames.com/documentation/metahuman/getting-started-with-metahuman-animator?lang=en-US)

### 4.3 本机版本：功能文件已有，版本组合仍需验证

| 项目 | 只读核查结果 | 含义 |
| --- | --- | --- |
| Character Creator | 5.02.0923.1 | 已安装；不等于满足最新组合要求 |
| Unreal Engine | 5.8.1 | 与当前目标版本一致 |
| 项目 RLPlugin | 2.03 All-in-One | 已含 CC Control Rig 及面部 CSV 导出相关接口 |
| CC 面部 Rig | 存在 `CC5_HD_Face_Rig.uasset` | 不能机械照抄旧教程的 `CC_HD_Face_Rig` 资产名 |
| MetaHuman 相关组件 | 找到插件／Live Link Hub 文件 | 未确认当前工程中的启用和实际运行情况 |

本地依据：[RLPlugin 配置](D:/UE/projects/datatry_02/Plugins/RLPlugin/RLPlugin.uplugin)、[Rig 名称声明](D:/UE/projects/datatry_02/Plugins/RLPlugin/Source/CC_ControlRig/Public/RLRigSetupDefine.h:27)、[拆分接口](D:/UE/projects/datatry_02/Plugins/RLPlugin/Source/CC_ControlRig/Public/RLRigSetup.h:51)、[CSV 导出接口](D:/UE/projects/datatry_02/Plugins/RLPlugin/Source/RLPlugin/Public/RLPlugin.h:151)。

官方当前 Auto Setup 2.03 的 CC5 组合要求 **CC5.11+**，本机 5.02 低于这一范围。但 CC5.0 发布记录已经列有 MetaHuman CSV 导入，不能因此断言 5.02 没有该功能。应在隔离测试时验证当前组合；本次不建议为调研中断用户操作或立即升级。[当前兼容要求](https://www.reallusion.com/auto-setup/unreal-engine/download.html)、[CC 发布记录](https://www.reallusion.com/character-creator/update.html)

### 4.4 AccuFACE 2：适合以后经常自行录制

AccuFACE 2 可以从视频或摄像头获得面部表演，但需要 iClone，不能只装到 CC 中就使用。官方当前说明要求 iClone 8.74+；本机这套工具链未确认，因此现阶段增加它会带来安装、版本与素材清理工作。[安装手册](https://manual.reallusion.com/Motion_LIVE_Plugin/Content/Motion_LIVE/AccuFACE-2/Installation-Guide-for-AccuFace.htm)、[官方版本答复](https://discussions.reallusion.com/t/accuface-2-grand-launch-professional-grade-facial-mocap-for-cc5-hd-characters/18059)

如果之后需要持续录制不同的观察、倾听或互动表现，它值得再评估。当前只需几条自然片段，优先用已有素材更合适。AccuFACE 输出仍依赖 CC 的表情系统，不是节省全部 Morph 的方法。[产品说明](https://www.reallusion.com/iclone/motion-capture/accuface.html)

## 5. 怎样与用户新选的身体动作结合

### 第一阶段：先得到一条可靠的参考动画

在独立角色副本上记录身体动作基线，再应用一条 `.iTalk`，观察身体和头颈是否被改变。若能保留身体、只增加自然脸部表现，就导出这条完整表演作为参考。**CC 直接应用面部素材的格式能力已有依据，当前新角色上是否保留全部身体通道仍需测量。**

对于 MotionPlus，iClone 的 `File → Merge MotionPlus` 有只取 Facial Animation 的过滤；Motion 轨右键 Import 会替换身体与脸。这个明确过滤属于 iClone，不能假定 CC 有相同菜单或自动化接口。[官方分离说明](https://manual.reallusion.com/iClone-8/Content/ENU/8.0/55-MotionPlus/Mergin_Partial_Motions_from_MotionPlus.htm)

CC 官方支持通过 FBX 的 Mesh and Motion＋Custom MotionPlus 导出身体与面部，并保留头部 blendshapes。已有本地脚本可参考其加载与导出方法，但其中 `preserve_profile_clip` 只跳过删除片段，后面仍会写入 Blink／Smile／Jaw 校准关键帧。**仅打开这个选项不能原样保留自然表演**；应跳过校准写键，并按源片段确定时间范围。[CC 导出说明](https://manual.reallusion.com/Character-Creator-5/Content/ENU/5.0/17-Export/Exporting_FBX_Characters_with_MotionPlus.htm)、[本地加载与保留分支](../../00_engine/scripts/character_creator/cc_headshot_route_validation_v1.py:1429)

### 第二阶段：让一条脸部表演复用到多个身体动作

建议仍先生成一个 UE 合成动画文件，以接入已有渲染方式：身体提供躯干、四肢、头和脖子；面部来源提供批准的眼、下颌、牙舌等骨轨，以及对应表情和纠正曲线。

当前[旧合成脚本](../../00_engine/scripts/unreal/ue_build_first_batch_action_expression_composites.py:216)只是复制身体、清空曲线，再写简单表情，**尚未实现完整面部片的合入**。旧 hybrid 工具有骨轨写入经验，但也不是通用自然面部片读取器。

需要补的工作应控制在以下范围：

1. **明确谁控制哪里。**保留身体的 root／head／neck 和必要身体曲线；只替换批准的面部轨道。不是清掉所有曲线，也不是只复制嘴角 Morph。眼球不能同时被新片段和另一套视线控制重复驱动。
2. **处理不同身份。**优先让 CC 在目标身份上计算表演，并导入该角色实际使用的 Skeleton。相同骨名或兼容 Skeleton 标记不保证局部参考姿势相同，不能把一个人的脸骨绝对变换直接铺到全部身份。
3. **处理时间。**记录真实采样率与有效范围，明确截取、重采样和过渡；不把任意短片直接循环。必须循环时，检查首尾的表情、眼神和变化速度是否接得上。
4. **保持数据可复现。**配对视频中固定脸部片段、起始位置和强度。换衣服或灯光时，不额外随机一次眨眼。依身体内容无法分离的完整表演保留配对，不强拆。

以上延续[现有身体／面部分工规则](../../20_planning/data_design/character_creator/full_process/technical/unreal/ANIMATION_EXPRESSION_MORPH.md)，不是新建另一套角色流水线。

## 6. 对导入时间和大小的影响

**当前代表性角色继续保留完整面部能力；后续添加表演时，优先只导入动画，复用已导入的角色网格和纹理。**不需要为了增加一条眨眼片段，就在 UE 再导入一整套角色材质和纹理。

真正的 Morph 裁减应在选定片段后，根据实际用到的表情和依赖进行。不能只留下几条肉眼熟悉的名称，也不能因为嘴角变化小就删掉修正闭眼、嘴唇接触等组合效果的 corrective。具体哪些能删，必须用裁减前后相同画面验证。[CC HD 纠正表情说明](https://manual.reallusion.com/Character-Creator-5/Content/ENU/5.0/05-HD-Character/Main-Concepts-for-Corrective-Expression-Sliders.htm)

此前约 4 MB 与近 200 MB 的角色并非同条件对照，不能据此计算 Morph 的精确成本。此次源动画文件大小也不是导入优化结果。空间与时间的正式判断仍需在同一个新角色、相同导入设置下比较。

## 7. 用户完成当前导入后，只做一个小测试

**用户现在无需暂停导出导入，也无需额外购买、录制或安装。**应用空闲后，建议按以下顺序实施：

1. 用一个新角色的独立副本，播放 `01_Neutral_Lo` 与 `Gentle_Female`；若都不合适，再看对应性别的 HD Idle。先找一段约 3–5 秒、无明显说话口型的自然窗口，不要求马上循环。
2. 保存身体单独播放的基线，再检查加入脸部后：身体和转头是否保持，眨眼是否闭合、眼神是否合适、嘴唇与牙舌是否正常。名字叫 Neutral／Gentle 不能替代这一步。
3. 把完整参考表演以 **animation-only** 导入该静态角色实际使用的 Skeleton，确认新增 Skeletal Mesh 为 0，再近景对比 CC。这样遵循[历史参考姿势故障的修复方法](../../20_planning/data_design/character_creator/full_process/technical/character_creator/BODYFIT_IDENTITY_AGE.md:677)。参考通过后，再将同一面部片与两条身体动作组合，检查脸部以外的骨轨逐帧保持。
4. 第一角色通过后，再在另一身份复核，随后才确定小型面部库和自动化合成方式。

这次测试应交付：**一段可观看的对比结果、一条可复用的合成动画、实际依赖的面部数据清单，以及一个明确的继续／换来源结论。**测试前不把任何来源写成已经适配新角色。

## 8. 研究范围与使用权

本轮只把候选作为内部原型研究，未核实用户账户授权或训练用途许可。按项目[现有授权规则](../../20_planning/compliance/licensing_compliance.md)，允许导出到 UE 与允许用于模型训练需要分别确认；Reallusion 内容许可及 Epic 对 MetaHuman 相关内容的条款都应在正式采用时核对。本文不对 CC 经 MHA 转换后输出的具体权利范围作结论，也不因此中断当前技术试验。[Reallusion 内容许可](https://www.reallusion.com/license/content.html)、[Unreal EULA](https://www.unrealengine.com/eula/unreal)

当前未完成的验证只有明确几项：候选片的实际内容与自然程度、应用时头颈归属、当前 CC／UE 版本组合、导出后完整面部通道，以及跨身份复用效果。资料存在和官方支持都不替代这些实测。
