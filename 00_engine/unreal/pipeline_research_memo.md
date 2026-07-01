# UE5.6 合成多轮视频编辑数据集 · 技术设计备忘录

> 面向：用 Unreal Engine 5.6 渲染"逐因子可控"的前后配对视频，训练多轮文本指令视频编辑模型。
> 角色：本备忘录为**总集成稿**，整合 7 份子研究 + 2 份对抗性核查结论，给出可执行、有立场的方案。
> 状态：历史调研稿。当前执行目标已转向 UE5.8；本文件中的 5.6 结论用于理解技术路径和风险，不应直接覆盖后续部署决策。

---

## 1. 一句话结论 + 管线总览

**一句话结论：** 用 UE5.6 把"角色/服装/动作/场景/道具/配饰/相机/光照"做成八个**独立可脚本切换的因子**，固定时间轴/相机/种子、每次只改一个因子、用 Movie Render Graph 离线渲染并导出 EXR 多层 GT，即可批量产出"像素级对齐 + 标签零噪声"的前后配对与多轮链——这是相对生成式管线（Ditto-1M/InsViE）的核心数据质量优势；**但 MetaHuman / Mixamo / Reallusion-标准 / Synty 的资产几乎全部禁止用于训练或发布，合规性是本路线的头号风险，必须用"CC0/自制/已授权"资产策略从源头规避。**

**整条管线总览（文字版）：**

```
[资产层 · 合规优先]
  角色(CC0/自制几何) · 服装(自制MD garment) · 动作(自采/CC0 mocap)
  场景(Fab-Std/Megascans*) · 道具/配饰(CC0/自制)
        │  (每个资产登记 license + NoAI 标志 → 准入闸门)
        ▼
[标准化层]  统一到 UE5 Manny/Quinn 骨架 (= MetaHuman 体骨架)
        │  IK Rig + IK Retargeter 一次性烘焙；in-place 循环动画
        ▼
[场景装配层]  一个 persistent level (相机/灯光/角色固定)
        │  环境 = 可流式切换单元 (Level Instance / Data Layer)
        │  道具 = 独立 actor (Tag 标记)；配饰 = socket 挂载
        ▼
[因子变更引擎 · Python]  EditorActorSubsystem / 属性切换
        │  规则：固定 timeline+camera+seed+warmup，只改 1 个因子
        │  优先 visibility-toggle，而非 destroy/respawn
        ▼
[渲染层]  Movie Render Graph (主) / MRQ (回退)
        │  AA=None + SpatialSamples≥8 (杀掉 TAA/TSR 抖动)
        │  cloth 预缓存 (Chaos Cache) ；warmup 帧拉满
        ▼
[GT 导出]  多层 EXR: Final / WorldDepth / MotionVectors / ObjectID(Cryptomatte)
        │  + Stencil Layer 语义分割 + 自写 JSON sidecar(相机内外参/改动因子/指令文本)
        ▼
[配对/链构造]  (source, instruction, target) 三元组
        │  多轮：turn≥2 时 source = 上一轮 target (MagicBrush schema)
        ▼
[数据集]  + 逐资产 license ledger (随数据集发布，保证可审计)
```

---

## 2. 按因子的推荐工具链（如何高效达到 100/100/20/50+）

> **关键合规前提（见 §5）：** 下表"首选工具"按**技术效率**排序，但 MetaHuman/Mixamo/Reallusion/Synty 的**渲染帧不能进入发布训练集**。因此每个因子都给出"技术高效路径"与"合规可发布路径"两栏。生产中应以**合规路径为准**，MetaHuman 仅用于**内部打样/验证管线**。

### 2.1 角色 → 目标 ≥100 身份

| 路径 | 工具与做法 | 工作量 | 合规 |
|---|---|---|---|
| 技术高效（仅内部） | MetaHuman in-UE5.6（Creator 6 面板；Influence Circle 三人混合 + 参数化体型滑条 + 肤色/雀斑材质）；Mesh-to-MetaHuman 导入扫描/雕刻。所有 MetaHuman 共用一套骨架 + 一个 IK Retargeter（`RTG_metahuman`/`IK_MetaHuman`），一套动画驱动全员 | 预设身份每个几分钟 UI；扫描"数字替身"因 likeness drift 需手工雕刻，慢 | ❌ 禁止进训练集 |
| **合规可发布（首选）** | **基于 CC0/自制几何构建 base mesh**（避开 MetaHuman/Reallusion DNA）：CC0 头/身扫描 + 自制材质 + 程序化变体（肤色/比例/发型）。MakeHuman（开源、参数化年龄/性别/族裔）作儿童/族裔补充。统一 retarget 到 UE5 骨架 | 手工做 20-40 个"hero"身份，再用材质/比例脚本扇出到 100+ | ✅ |

**达成 100 的策略：** 20-40 个精修基底身份 → 脚本化变体（肤色×体型×发型×族裔）程序化扩展。**注意：** MetaHuman 5.7 的 Python/Blueprint 批量身份 API **不在 5.6**——若要程序化生成大量身份，需评估升级 5.7（但 5.7 MetaHuman 帧同样受 AI 训练条款约束，对发布无帮助）。**最干净的对齐保证来自全 MetaHuman roster（共用骨架），但因合规不可发布——这是本项目最尖锐的工程/法务矛盾。** 结论：发布集走 CC0/自制 + IK 重定向（接受微小比例残差），MetaHuman 仅用于验证"逐因子对齐"管线是否跑通。

### 2.2 服装 → 目标 ≥100 套

| 路径 | 工具与做法 | 工作量 | 合规 |
|---|---|---|---|
| 技术高效（仅内部） | UE5.6 **Chaos Outfit Asset**（参数化，自动 resize 适配任意体型）+ MetaHuman Wardrobe；Fab 参数化 outfit packs 快速堆量 | Fab 包即取即用，最快 | ⚠️ Fab 看 NoAI；MetaHuman wardrobe ❌ |
| **合规可发布（首选）** | **Marvelous Designer 2025.2 自制 garment**（USD + Export Simulation Data → Chaos Cloth；MD2025.2 兼容 UE5.6，UE5.5 不兼容）。自己做 UV/版型，绕开第三方服装 EULA。组合分层（衬衫+外套+配饰）做组合式扩展 | 自制每件需 QA（5.6 有"转 Wardrobe Item 后炸开"已知问题），慢但可发布 | ✅ |

**达成 100 的策略：** 自制 ~30-50 基础 garment → 分层组合 + 颜色/材质变体扩展到 100+。**渲染陷阱（必须处理）：** Chaos Cloth 在 MRQ 中会因 sub-sampling/首帧归位而崩坏 → 必须**预缓存**（Chaos Cache Manager 或 Take Recorder），且**注意 UE5.6 已知回归：Cache Manager 可录制但回放时物体可能归位到原点**——在你的精确 5.6.x build 上验证，留好 fallback（settle 帧 + spawnable）。参数化 resize 会用基础 skin-weight transfer 覆盖自定义蒙皮/control rig；刚性结构件（盔甲）改用固定 Skeletal Mesh。

### 2.3 动作 → 目标 ≥20

| 路径 | 工具与做法 | 工作量 | 合规 |
|---|---|---|---|
| 技术高效（仅内部） | Mixamo（免费、量大）retarget 到 Manny/Quinn | 快 | ❌ Adobe 明确禁 ML 训练 |
| **合规可发布（首选）** | **自采 mocap**（Rokoko/Xsens/Move.ai markerless）+ **CC0/Truebones 可再分发 clip**；统一到 UE5 Manny/Quinn 骨架（= MetaHuman 体骨架），用 IK Rig + IK Retargeter（5.6 中 "Set Pelvis"，旧称 Set Retarget Root；Auto Retarget Chains 加速）一次烘焙、全员复用 | 自采需设备/演员；20 个动作（idle/walk/run/jump/sit/wave/dance/fight/pick-up…）可控 | ✅ |

**关键陷阱（必须按此设计）：** IK Retargeter **批量导出根运动在 5.5/5.6 有确认 bug**（pelvis 悬空、骨表乱序）。**对齐数据集应优先用 in-place 循环动画（无根位移），由 Sequencer 驱动、固定 clip 长度与循环次数**，保证前后帧严格同步；若必须位移，导出后校验/修复根运动，或改用 runtime `Retarget Pose From Mesh`（不烘焙）。Control Rig 用于加 corrective/additive 变体（额外编辑轴）。

### 2.4 场景 → 目标 ≥50+

- **三级来源：** ① 免费 Epic 样例工程（City Sample 城市/室内/屋顶、Electric Dreams PCG 森林荒漠、Lyra、Valley of the Ancient → 3-4 个工程供 15-25 个场景）；② **Fab/Megascans**（Fab Standard License，注意 §5 非 CC0 + NoAI）；③ **PCG 框架 + Biome Core/Sample**（一张高度图 × 改 biome/密度/seed/palette → 多生态变体，5.6 GPU 加速、seed 决定性确保跨渲染一致）。
- **室内偏少**：样例偏外景，需主动用 Fab 室内/archviz 包 + KitBash3D 补足；目标 ~25 外 + 25 内平衡。
- **切换机制（可脚本）：** 一个 persistent level 固定角色/相机/灯光，环境做可流式单元——首选**动态 Level Instance（`Load Level Instance`/`ULevelStreamingDynamic`）**（绕开 Data Layer 的 server/authority 复杂度），或 Blueprint 子关卡 `LoadStreamLevel`/`UnloadStreamLevel`，或 World Partition Data Layer `SetDataLayerRuntimeState`。
- **达成 50 的规模化：** 任一时刻只驻留 1 个环境 → 内存与目录大小无关；Nanite + HLOD + Virtual Texture 撑高模 Megascans；离线渲染 FPS 无所谓。**5.6 注意：** 启用 NVIDIA Streamline/DLSS 插件会导致 HLOD 生成失败，构建 HLOD 时关掉它。

### 2.5 道具 / 配饰

- **植被/道具三法：** Foliage Mode（painted ISM/HISM）/ **PCG**（节点图、seed 决定性、5.6 GPU 加速，背景层固定 seed 保持不变）/ 手放 hero 道具 actor。
- **车辆：** 多数情况只需静态摆设 → 直接作 prop actor 放置；需驾驶才用 ChaosVehicles 插件（skeletal mesh + `UChaosVehicleMovementComponent` + wheel BP，需重启编辑器）。
- **配饰（帽/眼镜/包）：** 在骨架 Skeleton Tree 加 **socket**（`HatSocket`/`GlassesSocket`），静态挂（Components 面板 Parent Socket）或运行时挂（`AttachActorToComponent`）。配饰跟随骨骼 → 同动画/seed/相机下前后仅差"配饰有无"，天然对齐。
- **核心结构（务必）：** **背景批量植被走 PCG/Foliage 固定 seed（保持恒定）；可编辑前景道具/配饰做成独立 actor，用 Tag 标记，脚本按 tag 定位切换。** 切换**优先 `SetActorHiddenInGame` / Sequencer Visibility track 切可见性**，而非 destroy/respawn（后者会扰动实例顺序/光照缓存/随机化）。注意 `SetActorHiddenInGame` 不能从通用 actor track 打关键帧，须用专用 Visibility track。

---

## 3. 渲染与自动化方案（UE5.6）

### 3.1 MRG vs MRQ：用哪个

- **主用 Movie Render Graph（MRG）**，节点化、按层控制（File Output 命名/OCIO、Renderer 节点 per-layer 采样、Sampling Method 全局时间采样、专用 warm-up 节点）。MRG 是 Epic 前向路径。
- **核查修正（重要）：** MRG 直到 **UE5.8 才"production-ready"**；在 **5.6 它是 Beta（支撑 Quick Render Beta）**，应视为"可用但成熟中"。**保留 MRQ 作为已验证 fallback。**
- MRG 在 5.6 仍**缺失**若干 MRQ 功能：nDisplay、Apple ProRes、Final Cut Pro XML、32-bit 后处理材质、**Prestreaming Recorder**；**高分辨率 tiling 在 5.6 状态有歧义**（5.6 roadmap 列为目标项，但 MRG 转换文档<5.8版>仍标其不支持——须在 5.6-pinned build 上实测）。本数据集不需要 nDisplay/hi-res tiling，故影响低。

### 3.2 Python 批量改因子

- 核心：`unreal.MoviePipelineQueueSubsystem` + executor（`MoviePipelineInProcessExecutor`/`PIEExecutor`）构建队列/配置并执行；参考 `Engine/Plugins/MovieScene/MovieRenderPipeline/Content/Python/MoviePipelineEditorExample.py`。Job/Shot/Queue 完成回调用于**链式渲染 + 写元数据**。
- 因子变更：`EditorActorSubsystem.spawn_actor_from_*()` / `destroy_actor()`；属性切换（mesh/material/anim/visibility/light/wardrobe item）。**服装/配饰因 5.6 无干净的 runtime swap API**，走编辑期/构建期脚本（MetaHuman Character plugin 监控 Wardrobe 文件夹 + 脚本设定 worn item + 重 bake）。
- **headless farm：** `UnrealEditor-Cmd.exe Project.uproject MapName -game -LevelSequence=... -MoviePipelineConfig=... -windowed -Log -StdOut`。**核查修正：** Epic 官方 CLI 示例**不含** `-Unattended`/`-RenderOffscreen`，但二者是标准且广用的引擎 flag，farm 渲染建议加上（自行验证，非该文档背书）。
- **开放问题（须实测）：** MRG 在 5.6 是否有等价于 MRQ config 对象的、文档化的 per-job 变量覆盖 Python API——尚未确认。若不可靠，退回 MRQ config 操作。

### 3.3 像素级对齐（前后配对决定性）

固定不变量：FrameRate、起始帧/timecode、Sequencer 时间轴、相机 transform/内参、console variables、**warm-up 帧数**（让 Lumen/时序效果同样收敛）。**杀抖动：AA method = None + Spatial Sample Count ≥8**（去掉 TAA/TSR 子像素抖动）；除非要运动模糊，否则不用 temporal samples（会切快门、偏移动画）。然后用 Python **只改 1 个因子**。

**决定性警告（不可忽视）：** Lumen/TSR/时序累积器 + GPU 非决定性，即便输入一致也可能产生微小像素差。缓解：拉高 `EngineWarmUpCount`、关 auto-exposure、必要时用 **Path Tracer** 或固定 temporal seed CVar 换取 bit 稳定（代价更高）。**Lumen GI/反射的副作用：** 换背景会正确地改变角色身上的反射/反弹光——物理正确，但"仅背景"编辑也会微弱重打光主体；**须先决定 GT 定义**（字节级主体不变 vs 语义对齐：主体/动作/相机一致、背景及其引起的重光照可变）。建议采用**语义对齐**口径，避免与 Lumen 物理打架。

### 3.4 GT passes 导出

- 启用 **"Movie Render Queue Additional Render Passes"** 插件 → Deferred Renderer 的 Additional Post Process Materials 开 `MovieRenderQueue_WorldDepth` + `MovieRenderQueue_MotionVectors`。这些 pass 关 AA。
- **多层 EXR 强制**（PNG/JPG 无法承载浮点/元数据）：Final→RGBA，各 pass 为命名 layer；World Depth 世界单位（R 通道），Motion Vectors 给 2D 屏幕流（**注意编码/尺度约定与 CV 光流格式不同，需转换步**）。ProRes 仅用于 review 视频。
- **分割：** Object IDs/Cryptomatte（per-instance；**实验性、仅编辑器**，离线生成 OK）；**Stencil Layers / Custom Depth Stencil 给更干净的语义类掩码**（按类映射 stencil index → class 写进 sidecar）。
- **缺口：** Deferred 下无原生 AO/SSS、无原生法线 AOV → World Normal 等用自定义后处理材质采 GBuffer，或用 **EasySynth**（深度/法线/光流/语义分割 + **相机位姿与内参导出**，无 C++；历史面向 UE4/早期 5，**5.6 需自行确认/重编译**）。**UnrealCV** 为 socket 在线逐帧 GT 的备选（同样需验 5.6 build）。
- **相机内外参 + 标签 sidecar：MRQ/MRG 不原生导出，必须自写脚本**：逐帧读 `CineCameraComponent`（FocalLength/Sensor/Filmback + actor world transform）写 JSON/CSV，按渲染时刻精确采样；或用 EasySynth 自动化。
- **元数据：** Output 节点 token（`{sequence}/{shot}/{frame}/{layer}`）+ 每次渲染自写 JSON sidecar（variation id、pair id、改动的那 1 个因子、seed、相机参数、自动生成指令文本）——这份 JSON 是把渲染对变成带标签编辑样本的关键。

---

## 4. 前后编辑配对 + 多轮链（落到 edit taxonomy）

**统一三元组：** `{source_video, edit_instruction, edited_video}` + per-frame GT。
**多轮 schema（采用 MagicBrush）：** 组织成 session/turn；**turn_index≥2 时 source = 上一轮 target**；每轮记录"改动因子"元数据。这是当前图像编辑唯一成熟的多轮范式——**视频多轮在文献中基本空白，本项目的链式编辑属新颖贡献，无现成 schema 可抄。**

**自动指令文本（本路线最大数据质量优势）：** 因为改动因子**精确已知**，可模板化生成无噪声指令（"Change the character's outfit to <B>"），再用 LLM **仅做措辞 paraphrase/多样化**——而非像 InstructPix2Pix/Ditto 那样由 LLM/VLM 从近似推断（带标签噪声）。

**八类因子映射 + 打样优先级：**

| 因子 | 实现机制 | AnyEdit 域映射 | 打样优先级 |
|---|---|---|---|
| **E7 相机** | 复制 sequence，只改相机 transform/焦距 | camera-movement | ⭐ 最易（无资产/无 cloth/无重定向，纯参数） |
| **E8 光照** | 转动 Movable Directional Light pitch / 改 SkyLight（Lumen 即时重光） | global(tone) | ⭐ 最易（无资产切换、天然对齐） |
| **E5 道具** | 独立 actor visibility-toggle | local(add/remove/replace) | ⭐ 易（toggle 即可，对齐好） |
| **E6 配饰** | socket 挂载件 visibility-toggle | local(add/remove) | ⭐ 易 |
| **E4 场景** | Level Instance 切换 | global(background change) | ◯ 中（须接受 Lumen 重光照副作用） |
| **E3 动作** | Sequencer 只换 Animation track（in-place 循环） | local(action change) | ◯ 中（须避根运动 bug） |
| **E2 服装** | 切 Wardrobe/Outfit Item + 重 bake | local(appearance) | △ 较难（cloth 缓存 + 5.6 回归） |
| **E1 角色** | 切角色 BP（同 timeline/相机/光） | —（identity swap） | △ 最难（LOD/groom/材质差异引入不可控像素变化；非原生骨架有重定向残差） |

**打样建议：** 先用 **E7 相机 + E8 光照 + E5 道具 + E6 配饰**打通最小闭环（这四类纯参数/toggle、对齐最干净、无 cloth/无重定向风险），验证"固定一切只改一因子 + GT 导出 + 指令生成"全链路；再上 E4/E3，最后攻 E2/E1。

---

## 5. 许可证合规结论（含核查修正）

> **这是本路线最高风险维度（核查判定 risk=high）。原则：能进入渲染帧的每一个资产都要查 license + NoAI，默认"排除可疑源"，并维护逐资产 ledger 随数据集发布。本节非法律意见，发布前必须 IP 律师审阅。**

### 5.1 明确禁止 / 项目级致命（核查确认）

- **Mixamo（Adobe）：** 明确禁止用输出"create, train, test, or otherwise improve" ML/AI（Adobe 通用条款，2025-10-03 现行）。→ **排除 Mixamo 衍生帧。用自采/CC0 mocap 替代。**
- **Synty（标准 One Time Purchase，2025-11-13 更新）：** 禁止"inclusion in datasets utilised by Generative AI Programs"。→ **标准许可下排除；需 custom license。**
- **Reallusion（CC/iClone/ActorCore 标准 EULA）：** 不许 AI 训练/合成数据，须 Enterprise License。→ **标准许可下排除。**（核查新增：**2026-01 Reallusion 订阅/永久授权有变更**，发布前重核。）

### 5.2 不确定 / 需软化（核查修正，重要）

- **MetaHuman——从"高置信致命"降级为"未决/须律师 + Epic 澄清"：** 原判定"MetaHuman 渲染帧禁止训练、致命、高置信"**被核查推翻为过度**。逐字的 clause-(j) AI 训练禁令位于 **MetaHuman Creator EULA（云 Creator，UE5.5 及更早）**；**UE5.6 下载版 MetaHuman 受 UE EULA + MetaHuman Content Addendum 管辖**，有可信（社区、非 Epic 官方）解读认为内容侧 AI 限制随 NoAI 推出已被移除。**状态为真正"未决"，而非干净禁止。** 另需区分："MetaHuman Technology/DNA 本身禁挖训练" vs "下载角色/渲染输出"——该区分来自论坛成员而非 Epic 员工，方向相反。
  - **工程结论不变：发布训练集仍 EXCLUDE MetaHuman 帧**（最安全），但法律依据标注为"未决，须律师 + Epic 澄清"，而非"高置信致命"。MetaHuman 可正常用于**内部管线打样/验证**。
  - 另注：June-2025 起 MetaHuman 可在任意引擎渲染/出售——但**引擎可移植性 ≠ AI 训练权**，两者法律上独立，勿混淆。
- **Fab Standard / Megascans——从"默认允许"降级为 medium："** 原"非 NoAI 即默认可训练"**被核查软化**。Content EULA §17 只**有条件禁止 NoAI Content**，**并未肯定授予训练权**；且 Epic/Fab 公开表态"does not license existing assets for use training AI models"。→ 非 NoAI 的 Fab/Megascans 资产应视为**"未明确禁止但未授予 → 自担风险，待律师审阅"**，而非"已清场"。Megascans 为 Fab Standard（专有、**非 CC0**），逐资产记 NoAI（Epic 第一方内容**很可能**无 NoAI，但未在规模上验证，且第一方身份本身不授予训练权）。

### 5.3 明确安全路径（推荐合规资产策略）

✅ **CC0**（Poly Haven HDRI/纹理/模型、AmbientCG、Kenney——**确认是 CC0 而非 Fab-Standard**）；✅ **带明确 ML 训练授权的资产**；✅ **自采 mocap**（Rokoko/Xsens/Move.ai）；✅ **自制 garment/道具**（MD/Blender + 自做 UV）；✅ **从 CC0/自制几何构建角色基底**（直接绕过 MetaHuman/Reallusion 禁令，并规避"渲染帧是否算'derived'使用"这一未测法律问题）；✅ 必要时 **Reallusion/Synty Enterprise/custom 协商授权**（须确认其是否允许**公开再分发**，而非仅内部训练）。

**强制工作流：** 对每个可能出现在渲染帧的资产，登记 `source / license name+tier / NoAI 标志 / ML-training allowed Y/N`。硬排除 MetaHuman + Mixamo 帧；Reallusion/Synty 需 Enterprise 证明；默认仅放行"Fab-Standard-无NoAI（待律师）+ CC0（有 provenance）"。**ledger 随数据集发布，使权利链可审计。**

### 5.4 核查新增行动项

- 关键未测法律问题——**"训练于'描绘'（而非'摄入')被禁资产的渲染帧是否构成被禁的'derived'使用"**——同时 gate MetaHuman 与 NoAI-邻近 Fab 内容；**最安全工程答案：用 CC0/自制几何构建角色，从源头绕过。**
- 发布前归档每份 EULA 的**带日期逐字副本**（核查中 unrealengine.com/eula/*、fab.com、actorcore 等多处 403/证书错误，无法逐字取证）；MetaHuman Content Addendum、UE EULA AI 条款、完整 Fab EULA、ActorCore EULA 均为**一手缺口**。
- 收入闸门（独立于 AI 条款）：MetaHuman/UE 营收 <~$1M/yr 免费，否则 ~$1,850/yr/席；Fab Personal(<$100k)/Professional(≥$100k) 按营收分级——资金充足的实验室须买 Professional。

---

## 6. 风险与未决问题 + 分阶段落地

### 6.1 主要风险

1. **合规（高）：** 见 §5。MetaHuman 法律未决、Fab 非授予、一手 EULA 取证失败。**缓解：CC0/自制资产策略 + ledger + 律师审阅 + 发布前重核（EULA 频繁变更）。**
2. **决定性（中高）：** Lumen/TSR/GPU 非决定性破坏字节级对齐。**缓解：AA=None+SpatialSamples、warmup 拉满、采用"语义对齐"GT 口径，必要时 Path Tracer。**
3. **Chaos Cloth（中）：** MRQ sub-sampling 冲突 + **5.6 Cache 回放归位回归**。**缓解：预缓存 + spawnable + settle 帧 + 在精确 build 验证。**
4. **根运动导出 bug（中）：** 5.5/5.6 IK Retarget 批量导出确认问题。**缓解：in-place 循环动画 / 导出后校验 / runtime retarget。**
5. **域差距 / "AI vibe"（中）：** 文献警告纯合成数据有伪影/标签噪声——本路线消除标签噪声、给真实对齐，但仍须投入照片级真实感（Lumen/path-tracing、高质量角色），并考虑**混入真实 clip**（参照 unpaired-clips 论文）以缩小 sim-to-real gap。
6. **5.6 版本特性（低，核查判定）：** MRG 在 5.6 是 Beta 非 production；hi-res tiling 状态歧义；多处文档为 5.7/5.8 版，节点/UI 名须在 5.6 build 上 spot-check。

### 6.2 关键未决问题（须实测）

- MRG 在 5.6 是否有文档化的 per-job 变量覆盖 Python API？（否则退 MRQ）
- 多层 EXR + Cryptomatte + 相机 JSON 能否一次渲染出齐，还是 depth/normal/seg 需分 pass（影响吞吐）？
- 单 GPU 每变体渲染吞吐？Path Tracer（换决定性/干净 AOV）下 100×100×… 组合是否预算内可行？
- E1 角色切换能否保证除角色 BP 外字节一致（LOD/groom/材质差异？）——很可能不能，故 E1 用"语义对齐"口径。
- EasySynth/UnrealCV 是否有维护中的 5.6 build，还是须从源码重编译？

### 6.3 分阶段落地计划

- **阶段 0 · 合规地基（并行先行）：** 建 license ledger；锁定 CC0/自制资产来源；启动律师审阅 MetaHuman/Fab 两个未决问题。**不产出发布数据前不放行任何受限资产帧。**
- **阶段 1 · 最小闭环（打样，可用 MetaHuman 仅内部验证）：** 一个 persistent level + 1 角色 + 1 in-place 动画 + 1 相机。打通 **E7 相机 / E8 光照 / E5 道具 / E6 配饰** 四类纯参数/toggle 编辑；跑通 MRG 渲染 + EXR 多层 GT + 相机 JSON sidecar + 模板指令生成；验证前后帧像素/语义对齐与 GT 正确性。目标：产出几十个干净配对，确认全链路。
- **阶段 2 · 加难因子：** 上 **E4 场景**（Level Instance 切换 + 确定 Lumen 重光照口径）与 **E3 动作**（in-place 循环、避根运动 bug）；解决 Chaos Cloth 缓存后上 **E2 服装**；E1 角色用语义对齐。建立多轮链（MagicBrush schema）。
- **阶段 3 · 合规化 + 规模化：** 用 CC0/自制资产重做发布集（替换打样用的 MetaHuman/Mixamo）；Python headless farm 批量化；Nanite/HLOD/VT 撑 50+ 场景；评估升级 5.7（批量身份）。
- **阶段 4 · 质量与评测：** 引入 reference-based 指标（PSNR/SSIM/LPIPS vs 真值——引擎独有优势）+ CLIP Fram-Acc/Tem-Con + 人类偏好（TGVE/EditBoard 风格）；按需混入真实数据做域适应；LLM paraphrase 多样化指令避免过拟合模板措辞。

---

## 7. 来源可信度说明

**A. Web 证据 · 高置信（官方 Epic/厂商文档或多源确认，且经核查）**
- MRG 相对 MRQ 缺失功能列表（nDisplay/ProRes/FCPXML/32-bit PP/Prestreaming）——官方 MRG transition 文档逐字确认。
- Object IDs/Cryptomatte 实验性且仅编辑器；deferred 下无 AO/SSS、无原生法线；Stencil Layers 做分割——cinematic render passes 文档确认。
- MetaHuman 5.6 in-editor 集成、共用骨架/IK Retargeter、参数化体型、Outfit 自动 resize——metahuman.com 确认。
- 多轮 schema（MagicBrush）、edit taxonomy（AnyEdit 25 类）、生成式视频数据集成本（Ditto-1M >12,000 GPU-days）、Kubric 导出 schema——论文确认。
- **合规致命项（Mixamo/Synty/Reallusion-标准禁 AI 训练；Megascans=Fab-Standard 非 CC0）——经独立核查逐字/现行确认。**

**B. Web 证据 · 中置信 / 经核查降级（须发布前重核）**
- **MetaHuman 帧训练禁令**：从"高置信致命"**降级为"未决"**——5.6 下载版受 UE EULA+Addendum，AI 限制可能已移除（社区解读，非 Epic 确认）。工程上仍排除。
- **Fab 非-NoAI"默认允许"**：从"高"**降级为 medium**——EULA 仅有条件禁 NoAI、未肯定授予，Epic 公开称不为 AI 训练授权。视为"自担风险待律师"。
- MRG 在 5.6 的成熟度（核查修正为 Beta，非 production；production 在 5.8）。
- hi-res tiling 在 5.6 的状态（roadmap vs 文档矛盾，须 5.6 build 实测）。
- EasySynth/UnrealCV 的 5.6 兼容性（未确认维护 build）。
- Chaos Cache 5.6 回放回归、IK Retarget 根运动 5.6 bug（社区报告，须在精确 build 复现）。
- MD2025.2↔UE5.6 兼容、CC4/MetaTailor 是否导入为原生 Chaos Outfit（部分二手来源）。

**C. 模型知识 · 须进一步核实**
- "背景层 PCG 固定 seed + 前景独立 actor"的工程结构、配饰 socket 对齐推论（实践经验，非官方文档背书）。
- "用 CC0/自制几何构建角色绕过禁令""ledger 工作流"——合规策略推断，须律师确认。
- 部分二手数字（骨骼数、5.6 严格 A-pose 要求、CC4 vs CC5 导出行为、Senorita-2M/EditBoard 细节）——视为近似，引用前核一手。

**D. 一手取证缺口（核查标注，发布前必须补）**
- unrealengine.com/eula/*、fab.com/eula、ActorCore EULA、MetaHuman Content Addendum、UE EULA AI 条款——核查中 403/证书错误，无法逐字取证；发布前须归档带日期逐字副本并经 IP 律师审阅。
- 多份 Epic 文档为 5.7/5.8 版页面；工作流在 5.6–5.8 稳定，但确切节点/UI 名须在 5.6-pinned build 上 spot-check。
