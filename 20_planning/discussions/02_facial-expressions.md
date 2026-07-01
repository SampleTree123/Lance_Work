# 话题 02 —— 面部表情（跨风格域 + 是否作为编辑因子）

> ↑ [话题索引](./README.md) ｜ 关联：[`01_character-and-outfit-sources.md`](./01_character-and-outfit-sources.md)、[`../data_design/`](../data_design/README.md)（edit taxonomy）

**状态**：已细化（2026-06-19 深度调研 + 对抗式核查）

---

## 背景 / 问题

作者担心：面部表情除了 MetaHuman，真的能解决吗？（尤其动漫/卡通等非 MetaHuman 角色）

## 结论：能，机制是 blendshape，且有行业标准

- 表情通用机制 = **blendshape（变形目标）**，几乎所有角色格式都支持。
- 两套事实标准：
  - **ARKit 52 blendshape**（苹果定义，已成事实标准）——角色带它即可被任意面捕/音频/程序化驱动。
  - **VRM 标准表情**——**动漫 VRM 角色出厂自带表情+口型**（VRoid 自动生成）→ **动漫域的脸开箱即用，不需要 MetaHuman**。

## 驱动/生成工具（非 MetaHuman）

- **NVIDIA Audio2Face**（已开源）：音频→面部动画，输出 ARKit 兼容 blendshape。
- **Character Creator**：自动生成 ARKit 表情+口型，导出 UE（许可证暂缓）。
- **Live Link Face**（iPhone ARKit 捕捉）、**FACEIT**（Blender 给角色补 ARKit blendshape）。
- **做数据集最省**：程序化生成 → **直接脚本设 blendshape 权重**采样表情，连捕捉都不用。

## 各域现状

| 域 | 面部表情可用性 |
|----|----------------|
| 动漫(VRM/VRoid) | 出厂自带表情+口型，开箱即用 |
| 卡通(Ready Player Me) | 带 ARKit 表情 |
| 卡通(Synty 等低多边形) | 可能无面部 blendshape，需补或接受弱表情 |
| 写实(非 MetaHuman) | CC 自动加 ARKit；或任何带 ARKit 的角色 + Audio2Face |
| 写实(MetaHuman) | 最高写实 + MetaHuman Animator（视频驱动脸），但版权后账 |

**唯一要求**：角色需带一套标准 blendshape（VRM 自带 / CC 能加 / 随机网络·Meshy 模型可能没有需补）→ 又一个"**优先用标准化来源**"的理由。

## 重要引申：表情可作为一个"编辑因子"

- 改表情 = 只动几个 blendshape 权重、**不换任何资产** → **最容易做到完美对齐的编辑之一**（前后帧除脸部表情外逐像素一致）。
- 可控性 + 对齐性都极佳，且 GT（blendshape 权重）天然已知 → 自动指令好生成（"让她微笑"）。
- 建议纳入 edit taxonomy，暂记作 **E11 表情**。

## 详细规范（深度调研 + 核查 · 2026-06-19）

### 各域来源 / 做法

**写实（MetaHuman / CC4）**
- **MetaHuman（5.6+ 为混合 rig：面部关节 + 700+ blendshape**，Full Rig 或 Joints-Only，**非"纯 blendshape 无骨"**）。由 ARKit-52 控制层驱动（Live Link Face / `Face_AnimBP` 监听 ARKit 名），或 key 面部 Control Board 的 `CTRL_` 曲线。
- ⚠️ **命名纠正**：MetaHuman 的 `CTRL_` 曲线用 Epic 自有命名（`CTRL_C_jaw_open` 等），**不是** `eyeBlinkLeft` 这类 ARKit 名 → 维护一张每 archetype 的 **ARKit↔CTRL_ 映射表**，并在你的 5.8 archetype 上核实确切名。
- **CC4**：原生 **52 ARKit + 11 tongue（63）** 一对一映射。

**动漫（VRM/VRoid，经 VRM4U）**
- VRM 1.0 **标准预设是小集**：5 情绪（happy/angry/sad/relaxed/surprised）+ 5 视位（aa/ih/ou/ee/oh）+ blink + 4 look——**远粗于 ARKit-52**。
- 补全 ARKit-52：VRoid 用 **HANA_Tool** 自动生成 52 ARKit（Perfect Sync）；非 VRoid 的 VRM 在 Blender 手建 → 定一张冻结的 **ARKit-52 → VRM Perfect Sync** 映射表。

**卡通**
- **Ready Player Me**：原生 **ARKit-52 + Oculus 视位**，开箱，与写实同一 driver（确认下载勾选 ARKit morph）。
- **Synty / Quaternius CC0 / 多数低模头**：常**完全没有面部 blendshape**（刚性脸）→ 用 **FACEIT（Blender，半自动 landmark→52 ARKit）** 或 **Character Creator** 补；或对缺 morph 的头用 **Control Rig 驱动面部骨**（此时 GT = 控件值）。

### 工具与流程
1. **规范向量 = ARKit-52**，维护"ARKit-52 → 各域"映射表作为契约。
2. **入库前预检**：自动检查 52 个 ARKit morph 能否解析；不过者走 FACEIT/CC 补料。
3. **命名归一化表**（`eyeBlinkLeft` vs `eyeBlink_L` …），否则曲线静默绑定失败。
4. **确定性驱动**：一个 Python driver，输入 `{name: weight}` → 写面部动画曲线 key → 触发 MRQ。
5. **说话（视位）作独立子因子**：用开源 **NVIDIA Audio2Face-3D（MIT）** 或脚本化 phoneme→视位曲线（完全确定性）。**避开 OVR LipSync（已 EOL）**。

### 对齐 / GT / 采样
- **对齐**：重渲完全相同 Sequencer 状态两次、**只换面部字典**；面部轨与身体轨完全独立；**烘焙/禁用所有过程化面部逻辑**（程序化眨眼、look-at、抖动）。
- **GT**：离散情绪标签（干净分类）+ 逐帧 `{ARKit name: weight}` 向量 + intensity + seed。**跨域可比性用"情绪标签"**（同一 `mouthSmileLeft=0.7` 在不同脸上观感不同，原始权重为域内特有）。
- **采样**：① 离散标签情绪集；② 连续强度（微表情 s≈0.1–0.3）；③ 有界随机多 blendshape 组合（限激活数 + 排除对立对）；④ talking 视位作可独立/共变子因子。

### 坑（结合核查）
- **VRM 开箱预设远粗于 ARKit-52**——精细表情必须补 Perfect Sync。
- **低模卡通头零 blendshape**——逐个 FACEIT/CC 补料，预算逐角色工时。
- **命名/大小写跨导出器不一**——需归一化表。
- **捕捉非确定性**——前后对必须烘固定权重曲线，渲染时不捕捉。
- **视线泄漏进表情**——`eyeLook*` 别烘进情绪 clip，视线放单独控件、跨对固定。
- ✅ **Audio2Face-3D（重要纠正）**：**原生输出 ARKit blendshape 权重——52 面部（开舌头则 68 = 52 + 16 tongue），本身就是 ARKit-52，不需再 solve**。它对约 10 个头/视线通道输出 0、无头动/视线——正好把口/颌/颊填给表情，视线/头留给独立控件。⚠️ 真正待定：**插件能否对 UE 5.8 直接构建**（官方列 5.4–5.6 / v2.5），可能需从 MIT SDK 源码 rebuild。舌头数勿混：CC4 +11、A2F-3D +16。
- **权重可加 → 多高权重叠加过形变破网格**（mouthSmile+jawOpen+mouthFunnel 同时 1.0）：限每形上限 + 激活数 + 排除对立对。
- **VRM4U 运行时 `Load VRMFile` 打包可能丢 morph（#152）**——数据集用**编辑期导入资产**，勿运行时加载。

### 落地建议（MVP 第一步）
**先做卡通侧 RPM（开箱 ARKit-52）+ 写实侧 MetaHuman，跑通一条 Python driver**（`{ARKit name: weight}` → 写曲线 key → MRQ），在固定 Sequencer 状态上做出第一组 **neutral→smile** 对齐前后对（身体/相机/光照/种子全锁），导出 `{name:weight}+intensity+seed` 作 GT 验证"仅脸变化"；同时建好 ARKit↔MetaHuman `CTRL_` remap 表与命名归一化表。动漫(HANA_Tool 补 Perfect Sync)、低模卡通(FACEIT 补 52 形)作第二批，复用同 driver 与 GT schema。

## 待定与下一步

- ✅ **已定（2026-06-19）**：表情独立为 **E11**，与 E3 肢体动作分列（已回写 `20_planning/data_design` taxonomy + 决策日志）。肢体动作另见话题 03。
- 🔜 在"角色归一化前处理"里加一步：**确保角色带标准 blendshape 集（ARKit/VRM）**，缺则用 CC/FACEIT 补。
- 🔜 数据集表情采样策略（离散几类 vs 连续权重）后续在 `32_config/` 细化。
