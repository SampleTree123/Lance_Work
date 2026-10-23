# 可行性与风险评估（2026-06至08历史分析）

> ↑ 父层：[`./README.md`](./README.md) → [`../README.md`](../README.md)（总览）。
> 2026-10-23整理：本页下列结论为历史记录；580兼容构建后来已完成第一批生产与发布。当前旧引擎路径缺失等准备项见[服务器同步状态](../data_design/character_creator/full_process/project_management/status/SERVER_SYNC_STATUS.md)，不再把旧“待MRQ/基准”视作当前状态。
> 本文件是"项目前分析"阶段的收尾判定：项目能不能做、哪些已落实、哪些是必须验证的真实风险、刻意排除了什么。
>
> **2026-08-28 现场修正**：本页的 2026-06-19 纸面绿灯不能代表当前服务器生产能力。两个 H200/565.57.01 节点上的 UE 5.8 路径失败；随后 source compatibility build 在 H200/580.126.20 上连续完成最小像素和 `datatry_02` 工程像素输出。当前候选与剩余 Gate 以 [服务器执行](../data_design/character_creator/full_process/technical/rendering_release/SERVER_EXECUTION.md) 为准。

---

## 总体结论：架构可行，580 候选像素路径已打通

- 核心数据架构和本地渲染执行器已经有实测证据，批量自动化设计仍然成立。
- UE 5.8/H200/NVIDIA 565.57.01 仍有已复现的 BasePass 硬阻塞，不能作为生产路径。
- H200/NVIDIA 580.126.20 使用 source compatibility build 已完成最小 Vulkan 像素、两次真实项目启动和五次 SM6 工程截图；正式上传闭包已核验，下一步是直接验证正式 MRQ/MRG 代表节点和确定性。

## 已落实（高把握）

- 数据范式：配置图 / 确定性渲染 / 改一因子的对齐配对 / 端点复用 / 随机游走出多轮链。
- 引擎与基建：UE 5.8 + MRG + 无头 Linux 批渲（`-RenderOffscreen`+Vulkan）；GT（depth/motion/seg）MRG 原生多层 EXR。
- 每个编辑因子（E1 身份 / E2 服装 / E3 肢体动作 / E4 场景 / E5 道具 / E6 配饰 / E7 相机 / E8 光照 / E9 天气 / E10 风格 / E11 表情）都有具体落地路径。
- "风格域分区"把多风格一致性化解为有界问题；机器与风格无关、写一次通用。

## 必须验证的真实风险（按优先级）

| # | 风险 | 性质 | 缓解 / 验证方式 |
|---|------|------|------------------|
| ① | **确定性 / 对齐**（头号）：Lumen/时序/布料噪声可能破坏"未改区域逐像素一致"；`datatry_02` 五次截图已出现哈希差异，关闭 Volumetric Cloud 后仍有 2.69% 地面像素小幅变化 | 技术风险 | 固定 seed、warm-up、目标帧和 temporal/dither；关闭非必需随机效果；以同一正式 MRQ/MRG 节点复验并定义接受阈值 |
| ②a | **UE 5.8 Vulkan 驱动边界与 compatibility build（2026-08-28）**：H200/565.57.01 的基线、运行参数消融和 source-patched 路径仍会发生 typed format/layout 错误或 BasePass stall；H200/580.126.20 已完成最小和 `datatry_02` SM6 工程像素输出。驱动边界是强因素，但候选仍包含多项 UE 诊断 patch，尚不能归因于单一 patch。 | 候选像素路径已打通，生产 Gate 未通过 | 固定 580.126.20 候选与 package 哈希，完成正式 MRQ/MRG 代表节点和 10 节点基准；565 路径不用于生产 |
| ②c | **诊断入口与生产入口混淆**：旧 `/Game/Main` 引用不属于第一批的模块化 Pilot，导致诊断截图没有角色；正式上传闭包 8277 项完整、65 个关键文件哈希匹配 | 过程风险，不是内容缺失 | 后续服务器验证直接使用正式 staging map/Sequence/MRQ；生产 runtime 禁用或修正无关 Experimental Toolset |
| ②b | **服务器其余项曾通过检查（2026-06-19），存储方案已在 2026-06-28 修正**：H200(144G)/Ubuntu22.04/glibc2.35/内核5.15/2TB RAM。管理员确认不能使用 `/local`；当前 UE/MVP 全部放在 `/scratch/prj0000000275/jcy/xks/DataMake`，清理后约 897G 可用。 | 需执行前复核 | 安装 UE 前重新确认当前目录空间、`ldd` 依赖、`vulkaninfo` 和 `UnrealEditor-Cmd -version` |
| ③ | **资产归一化前处理**：杂源角色上骨架 + 补 blendshape + 多体型服装贴合 | 工作量（非难题） | 优先标准化来源（MetaHuman/VRoid/RPM）降本；参数化自动贴合 |
| ④ | **动漫极端比例 retarget**：穿插/脚滑 | 需逐域调 | IK Retargeter + Control Rig 修正（调研验证中） |
| ⑤ | **许可证**（发布前的非技术 gate） | 合规（已暂缓） | 发布前换安全资产并收口（见 [`../compliance/`](../compliance/README.md)） |

## 刻意排除的范围（为保持可行）

- **非人形角色**（四足/怪物）——排除或远期单列。
- **引擎内"跨风格变换"**（写实↔动漫）——非"改一因子"，交给大模型生成来源，不在引擎域做。

## 判定后的下一步

1. **正式入口**：直接使用已核验的正式 staging map、Render Workspace、MRQ Preset 和冻结 Look/composite bindings，并清理不需要的 Experimental Toolset runtime 启动项。
2. **正式代表节点**：固定 H200/580.126.20 compatibility profile、seed、warm-up 和时序状态，连续两次运行同一 MRQ/MRG 节点，检查角色、场景、相机、材质和确定性。
3. **基准与冻结**：代表节点通过后运行 10 节点基准；10/10 accepted 后才冻结 compatibility profile 并恢复完整批量。

---

## Agent 备忘（risks）

- 这是 go 判定文档。**别把"纸面可行"当成"已验证"**——MVP 渲出第一对对齐配对前，措辞用"预期可行"。
- 风险①（确定性/对齐）是整套范式的命门，MVP 必须最先打。若压不住 → 退到"近似对齐 + 光流监督"，并回来更新数据模型与本文件。
- 风险②（服务器）在 2026-06-19 只有枚举级通过记录；2026-08-28 已取得 580.126.20 最小和真实工程像素证据，但角色内容、确定性、MRQ/MRG 与 10 节点 Gate 仍未通过。不得把诊断截图当成完整生产能力。
