# 话题 03 —— 肢体动作（E3，编辑因子）

> ↑ [话题索引](./README.md) ｜ 关联：[`02_facial-expressions.md`](./02_facial-expressions.md)、[`../../01_data_design/`](../../01_data_design/README.md)（taxonomy E3）、[`../../10_sources/unreal_engine/pipeline_research_memo.md`](../../10_sources/unreal_engine/pipeline_research_memo.md)

**状态**：已细化（2026-06-19 深度调研 + 对抗式核查）

---

## 背景

将原"动作"拆为 **E3 肢体动作（骨骼动画）** 与 **E11 面部表情（blendshape）**。本话题专讲肢体动作：整身/四肢动作（走/跑/挥手/拾取/踢腿…），**不含面部曲线**（归 E11）。

## 1. 机制

- **统一管线**：`IK Rig`（每角色一个，定义重定向链 + IK 目标）+ `IK Retargeter`（每对"源→目标"骨架一个），在 UE 5.8 的**模块化 Op Stack** 中求值。
- **作者一条规范动画 → 批量铺到全域角色**：在该域"公共骨架"上烘一条 `AnimSequence`，经各角色 Retargeter 批量导出。
- **UE 5.8 关键能力**（已核查命名）：
  - **Root Motion 模式**：`Copy From Source Root`（按身高比缩放复制源 root）与 `Generate From Target Pelvis`（从重定向后骨盆**合成** root）。Mixamo/学术 mocap 缺干净 root 轨 → **优先 Generate From Target Pelvis**。
  - **Foot Definition / Stride Warp / Speed Plant / Floor Constraint**：消脚滑、防穿地（Speed Plant 依一条命名 Speed Curve 在足速低于阈值时"钉地"）。
  - **矮个角色骨盆控制**（5.8 新增）：利好短肢动漫/卡通角色。
  - **Retarget Override Sets / Variables**：单个 Retargeter 资产按角色微调，不必每角色新建。
  - **Spatially Aware Retargeting**：⚠️ 5.7 引入的**实验**特性，5.8 状态未在 release notes 核实——**别当稳定能力**；自穿插靠"校正 Control Rig 叠加层"为可靠手段。

## 2. 各风格域来源

**写实（公共骨架 = UE5 Mannequin / MetaHuman，共骨架）— 最易**
- **GASP（Game Animation Sample Project）**：500+ 已在 Mannequin 上的动画，免费(Fab)，运行时重定向+运动匹配，**零转换、首选起步池**。
- **Mixamo**（FBX，需 Retargeter 到 Manny；导入勾 30Hz 烘焙）、**ActorCore/iClone**、**Rokoko**（补充）。
- **学术多样性**：CMU MoCap（~2500，用 cgspeed 2010 BVH 版）、AMASS（SMPL-H，经 Blender addon 导 FBX）。

**动漫（公共骨架 = VRM/VRoid Humanoid）— 最难、E3 主要风险点**
- **最大免费动作池 = MMD `.vmd`**（千计；右手 Y-up + IK + center/groove 根骨）。两条路线：
  1. **Blender**：`blender_mmd_tools`（Chaos192 UE4 命名分支）导入 `.pmx`+`.vmd` → **把 IK/center/groove 烘成 FK + 坐标转换** → 经 `VRM_Addon_for_Blender` 重定向 → 导出。
  2. **直入 UE**：`IM4U-UE5` / `IM-for-UE5` 拖拽生成 AnimSequence；`UeMmdHelper` 加速；noname0310 VMD 相机导入做确定性镜头。
- 补充：VRChat/VRCMods（Unity Humanoid → VRM 近 1:1）、Quaternius Universal Animation Library。
- **可行性结论（核查提为头条）**：locomotion **可接受**；但**自接触/扭转类（攻击、叉腰、手摸脸）可能完全崩**（VRM4U #309 试遍方案仍无可用解）。→ **动漫必须按角色 QA + 手动校正层，绝非一键批处理。**

**卡通/风格化（公共骨架 = 选定一个：RPM / Quaternius / Mixamo 类）— 中等**
- **Quaternius Universal Animation Library**（CC0；v2.0 起 UE 导出改 GLB，需 UE5+；v3.0/2026-06 全 locomotion 加 root motion）。
- **Synty ANIMATION 包**（FBX，重定向到 Mannequin 即可）、Mixamo + GASP 重定向到风格化比例。

## 3. 工具与流程

1. 每域**冻结一个公共骨架**。
2. **建 IK Rig（每角色）**：为每条臂/腿/脊柱/颈/头**显式建链**（最小化骨架→旋转对但端点错，见坑）。
3. **建 IK Retargeter（每对）**：配 Foot Definition、Root Motion Source、Stride Warp/Speed Plant/Floor Constraint。
4. **入料转换**：Mixamo/Synty FBX 直接重定向（勾 30Hz）；BVH 先过 Blender；VMD 走 blender_mmd_tools(Chaos192) 或 IM4U-UE5；AMASS 走 SMPL Blender addon。
5. **统一烘焙**：每 clip → 公共骨架上的 `AnimSequence`，**固定 30Hz**，统一 root 策略。
6. **批量铺角色**：同一 Retargeter（Override Sets 微调）导出全域。

## 4. 如何产出"对齐的前后配对"

- **一次 E3 编辑 = 仅替换 Sequencer 中 actor 骨骼动画轨绑定的那一个 `AnimSequence`**（walk→run）；其余（相机/光照/网格/服装/E11 表情轨/种子）全不变。
- **关键对齐手法：渲 in-place 循环动作，世界位移由 Sequencer transform 轨驱动，不依赖烘焙 root motion** → 前后两 take 走相同世界路径与取景，并**彻底绕开历史 root-motion 导出 bug**。
- 确定性 MRQ 渲两次，只有新姿态驱动的像素变。

## 5. Ground-truth

- 离散动作标签 = 所绑 `AnimSequence` id/名。
- 逐帧 3D 姿态 = 从 `SkeletalMeshComponent` 读 component/world-space 关节位姿 + root/pelvis 轨迹，对齐渲染帧。

## 6. 采样策略

- **5 类分类法，每类 ≥4 条 → ≥20 条/域**：locomotion / gestures-communicative / object-interaction / idle-emotive-body / sports-athletic。
- 多轮组合 = 每轮只换 E3 anim 资产并重渲，上轮 take 作下轮 before。

## 7. 坑 / 注意

- **root motion 烘焙 = 对齐陷阱** → 坚持 in-place + Sequencer 位移。
- **batch-export root-motion bug（5.5–5.7 真实）**：重排把 `root` 放到非 0 索引致 root motion 丢失；Epic 称进 5.7.2，"**5.8 已含此修复"仅推断、未在 5.8 notes 核实**——但 in-place 方案使其与管线无关。
- **最小化 IK Rig → 旋转对、端点错**（手够不到脸/道具、脚浮/陷）；T-pose 看不出，**必须用"手摸脸/脚钉地"动作验证**。
- **动漫比例 retarget 不可靠** → 校正 Control Rig 层（可靠），Spatially Aware 仅 best-effort；**按角色 QA**。
- **不同腿长 + 固定 Sequencer 平移 → 重新引入脚滑**：按角色匹配平移速度到有效步幅。
- **E3 与 E11 必须独立**：body AnimSequence **不得含面部曲线**（VMD 的 morph 轨要剔除），否则换动作扰动脸、污染单因子保证。
- Quaternius v2.0+ GLB（需 UE5+）与 v1 FBX 混用注意缩放；Synty/VRChat 常带 Unity 控制器，只取原始 clip。

## 8. 落地建议（MVP 第一步）

**先做写实：从 GASP（500+ Mannequin 原生、零转换）拉一个 in-place 动作池**，5 类各 ≥4 条，全烘 30Hz；搭一条 Sequencer 模板（相机/光照/种子固定、世界位移走 transform 轨），用"仅替换 anim 资产"做出第一组 **walk→run** 对齐前后对 + 导出逐帧关节 GT 验证确定性。卡通、动漫随后复用同模板（动漫先单角色手动 QA 跑通一条 MMD→VRM locomotion）。

## 待定与下一步

- 🔜 与 `10_sources/unreal_engine/render/` MVP 对接：E3 的"in-place + Sequencer 位移"约定写进渲染管线。
- 🔜 与 `32_config/` 对接动作采样（5 类配额、多轮编辑链中动作如何排布）。
- ❓ 各域"20 个动作"的具体清单待定（建议先定写实域 GASP 选哪 20 条）。
