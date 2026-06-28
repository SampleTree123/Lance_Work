# 30_engine_synth —— 引擎合成（Unreal Engine，当前目标 UE5.8）★当前主攻（Level 1）

> ↑ 父层：[`../README.md`](../README.md)（项目总览）。本层负责**用 Unreal Engine + 相关软件合成视频数据**，产出"像素级/语义对齐的前后编辑配对"。
> 📄 技术细节详见同目录 [`pipeline_research_memo.md`](./pipeline_research_memo.md)（UE5.6 起步的历史调研综合稿）和 [`33_render/cluster_deploy_and_mvp.md`](./33_render/cluster_deploy_and_mvp.md)（UE5.8 部署/MVP 计划）。⚠️ 许可证合规见 [`../90_meta/licensing_compliance.md`](../90_meta/licensing_compliance.md)。

---

## 📂 内容说明

把"造合成数据"拆成四步，对应四个子文件夹（**尚未创建，等资产策略定了再建**）：

| 子文件夹 | 职责 | 状态 |
|----------|------|------|
| `31_assets/` | **资产库**：角色 / 服装 / 动作 / 场景 / 道具配饰 的来源、获取、入库、规格统一 | 待建 |
| `32_config/` | **配置空间**：组合成"配置 C"，定义多样性采样、编辑转移（C→C'）与随机游走 | 待建 |
| `33_render/` | **渲染与自动化**：UE Python + MoviePipeline 批渲染、GT passes、保证前后配对对齐 | ★进行中（当前主线） |
| `34_output/` | **产出**：渲染视频、配对元数据、多轮编辑链、统一导出 | 待建 |

---

## 工作流（概念）

```
资产库(31)  →  配置空间(32)  →  批量渲染(33)  →  配对/链产出(34)
角色/服装/      组合成配置 C，沿       UE Python 程序化改       (视频_in, 改动因子,
动作/场景/      随机游走生成 C→C'       一个因子并重渲，          视频_out, GT passes)
道具/配饰       的"边"（只改一因子）    同步导出 GT，种子对齐      → 多轮链
```

## ✅ 关键技术结论（调研已完成 2026-06-19，详见 `pipeline_research_memo.md`）

> 注意：`pipeline_research_memo.md` 以 UE5.6 为起点，后续环境决策转向 UE5.8。执行前以现场 UE 版本、官方文档和 `33_render/cluster_deploy_and_mvp.md` 的复核结果为准。

- **渲染/自动化**：用 **UE Python + MoviePipeline 子系统**驱动；无头渲染 `UnrealEditor-Cmd Proj.uproject Map -game -RenderOffscreen -unattended ...`。渲染系统：UE5.8 目标优先验证 **MRG**，同时保留 **MRQ** 作成熟回退。
- **前后对齐（端点复用的实现保障）**：AA 设 **None + 仅空间采样**（去掉 TAA/TSR 抖动），锁定时间轴/帧率/随机种子/相机/console vars/warm-up 帧（让 Lumen 收敛一致），Python 只改一个因子再重渲。
- **GT passes**：多层 **EXR** —— Final Color + **World Depth** + **Motion Vectors（=光流GT）** + **Object IDs/Cryptomatte**（实验性、仅编辑器）+ **Stencil Layers**（语义掩码）。AO/SSS/法线非原生（需自定义后期材质）。相机内外参 + 每-actor 标签需**自写 Python sidecar**（每次渲染输出 JSON 记录"改了哪个因子"=自动指令）。
- **角色×100**：**MetaHuman**（5.6 已全整合入编辑器）技术上最强——所有身份**共享同一骨架+面部 rig**，一个 IK Retargeter 驱动全部、Outfit 自动适配任意体型 = 正好满足"只改一因子其余对齐"。多样性靠 preset 混合 + 参数化体型滑杆 + 肤色材质。⚠️ 但**批量生成 100+ 身份的 Python/BP API 是 5.7（2025-11）才有**，纯 5.6 批处理受限 → 需装 5.7。⚠️ **MetaHuman 有许可证不确定性，见合规文档。**
- **服装×100**：5.6 参数化体型 + **Chaos Outfit Asset 自动适配** = 换衣只改一因子。来源：Fab 成品 outfit 包（最快）/ Marvelous Designer 2025.2 / CC4。坑：Chaos Cloth 在 MRQ 不稳 → spawnable + settle 帧 + cloth cache（注意 5.6 cache 回放 regression）。
- **动作×20**：全部归一到 **UE5 Manny/Quinn 骨架**（=MetaHuman 体骨架）→ IK Rig/Retargeter 让同一动作在 100+ 角色上一致播放。来源：Fab 动作包 / Mixamo* / Rokoko / ActorCore* / MetaHuman Animator（*有许可证问题）。坑：root motion 批量导出在 5.5/5.6 有 bug → 优先 **in-place 循环动作**由 Sequencer 驱动。
- **场景×50**：三档来源——Epic 免费示例工程（City Sample 等）+ **Fab**（Megascans/环境包）+ **PCG** 程序化扩展。换背景：角色/相机/光照常驻 persistent level，环境用 **level streaming / Level Instance / World Partition Data Layer** 作流式单元换入（皆可脚本化）。光照/时段是独立因子（Movable Directional Light + Sky Atmosphere），可与场景组合成多轮轨迹。
- **道具/配饰**：植被 = Foliage / **PCG**（GPU 加速、seed 确定性）；车辆 = ChaosVehicles + Fab 包；配饰 = 角色 **socket 挂载**（Attach Actor To Component，可运行时增删）。**增删编辑的关键技巧：用 toggle visibility（`SetActorHiddenInGame` / Sequencer Visibility track）而非 spawn/destroy**，确定性时间轴不被打乱。
- **前人工作（支撑论文立意）**：指令编辑数据集传统是 `(source, instruction, target)` 三元组——图像有 InstructPix2Pix / **MagicBrush（含多轮编辑会话）** / AnyEdit（25 类编辑）；视频有 InsViE-1M / Senorita-2M / Ditto-1M（都靠生成式管线 + VLM 过滤）。**关键立意点**：2025 有论文指出**纯生成式合成视频编辑数据有"AI 味"/伪影/标签噪声**——而游戏引擎前后帧都是真实渲染、只差一个受控因子，正好规避这些失败模式；且引擎独有的 GT 让我们能用 **PSNR/LPIPS 对"真值编辑渲染"评测**（远强于无 GT 常规做法）。

## ⚠️ 许可证（gating 风险，详见 `../90_meta/licensing_compliance.md`）

一句话：**能否把"含某资产的渲染帧"用于训练+发布，取决于画面里每个资产的许可证。** Mixamo/Synty/Reallusion 标准许可**明确禁** AI 训练；MetaHuman、Fab/Megascans **不确定**（未正面授予）；**安全主路径 = CC0 / 自制几何 / 自采 mocap / 企业授权**，并仍统一绑 UE5 骨架以保留对齐优势。**当前阶段（2026-06-19）：版权暂缓、优先打通流水线**——原型阶段可用临时资产做内部验证，但必须标 `prototype-only`；规模化/发布前再换安全资产并收口（详见合规文档）。

---

## Agent 备忘（30_engine_synth）

- **本层是主攻**。技术路径调研已完成、可行（见 `pipeline_research_memo.md`）；当前卡点不是技术而是**许可证 + 资产策略**。
- **岔路已定但当前不纠结（2026-06-19）**：最终走安全资产、公开发布；但作者要求**先打通流水线、版权暂缓**。→ 原型阶段可用最省力资产做内部验证（MetaHuman 共享 rig 最契合"配置图/对齐"模型，CC0 场景等），但全部标 `prototype-only`，发布/训练前再换安全资产。
- **当前主线 = `33_render/` 打通 MVP 最小闭环**：脚本化 render→改一因子→render，前后对齐 + GT + sidecar。
- **服装适配后账（发布阶段关键工程，2026-06-19）**：MetaHuman"一件衣服自动适配任意体型"是**绑定 MetaHuman 参数化身体**的引擎便利（Chaos Outfit Asset 本身是引擎功能、非版权禁区）；换成自制/CC0 身体后会**丢失自动贴合**。解决**不是**手工配 100×100：而是把身体做成**参数化形状空间（如 SMPL-X）**，每件衣服在基础身体上做一次，用 morph/包裹变形/蒙皮迁移**自动跟随**体型 → 成本 O(衣服)≈100 而非 O(衣服×体型)=1万；再加**自动穿模检测**只挑失败项人工抽检；且只渲**采样到的**组合（配置图/随机游走，不枚举）。Marvelous Designer 用来**做衣服**，非逐组合贴合。静态贴合(参数化变形) 与 动态飘动(Chaos Cloth 渲染时模拟) 分开处理。Outfit Asset 能否改造适配自制身体 = 待验证。→ 将来归 `31_assets/`。
- **建子文件夹顺序**：资产策略定 → 建 `31_assets/`（先解决"东西从哪来、能不能用"）→ `33_render/`（打通管线、跑出第一对样例）→ `32_config/`（规模化采样）→ `34_output/`。
- **打样建议**：先从 **E8 光照、E5 道具可见性、E6 配饰可见性或 E11 表情** 做第一个对齐配对；E2 服装受 cloth/cache/适配影响，放到基础闭环之后。
- **落地要点速记**：对齐=AA None+空间采样+锁种子/时间轴/相机+warm-up；增删道具用 visibility toggle；动作用 in-place 循环避 root-motion 导出 bug；GT 走多层 EXR + 自写相机/标签 sidecar。
