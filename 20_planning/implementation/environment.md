# UE5 合成视频数据集 — 环境搭建调研备忘录

> 项目：基于 Unreal Engine 渲染「精确对齐的 before/after 配对 + 真值通道（depth / motion-vector / segmentation）」的多轮视频编辑训练数据集。
> 本机 Windows 交互作业 + 无头 Linux GPU 服务器批量渲染。
> 撰写日期：2026-06-19。
> 状态：历史调研稿。UE 版本、hotfix、许可证和服务器事实在执行前必须重新核实。

---

## 1. UE 版本推荐

**结论：在 Windows 作者机和 Linux 渲染服务器上统一安装 Unreal Engine 5.8，但大规模批渲染不要钉死在 5.8.0。**

理由（两根承重梁都落在 5.7→5.8 窗口）：

| 能力 | 5.6 | 5.7 | 5.8 |
|---|---|---|---|
| MetaHuman 批量 Python/Blueprint API（雕刻/适配/衣橱/绑定/贴图，可在 farm 上离线跑） | ✗ | ✓ | ✓ |
| Movie Render Graph (MRG) | Beta/Quick Render | 成熟中 | **Production-Ready** |
| MRG 单灯隔离 (Light Modifier) + Accumulation DoF | ✗ | ✗ | ✓ |
| MetaHuman 在 Linux 编辑器内运行 | ✗ | Creator 支持 | Creator+Animator 支持 |

- **5.8 是 mid-2026 最新稳定版**（2026-06-17 State of Unreal 发布），也是 **UE5 世代最后一个标准大版本**（UE6 early access 预计 2027 年底）。把多周数据生成项目标准化在 UE5 终点版上，可避免项目中途被迫迁移引擎。
- **5.8 的 MRG「单灯隔离」直接命中你的 single-factor「只改灯光」配对需求**——可在同一镜头里 override 任一灯的强度/颜色/任意属性输出为独立 render layer，是干净生成灯光变体配对的利器。
- **MetaHuman 批量 API（5.7 引入、5.8 延续）是 100 角色 / 100 套装目标的 make-or-break 能力**；5.6 没有它，**直接淘汰 5.6**。

**.0 还是 hotfix？**
- 已核实：**截至 2026-06-19 尚无 5.8.1 发布**（5.8.0 仅数天大，无现场 hotfix）。「数周内出 5.8.1」纯属基于历史节奏的推断（5.6.1、5.7.1 均已存在），**不是确定日期**。
- **执行策略**：
  1. **现在**用 5.8.0 搭建 MetaHuman 程序化造人管线 + MRG 渲染图、跑通原型。
  2. **多周正式渲染战役**等第一个 5.8.x hotfix 出现后再锁版本，并把精确 build 钉死以保证可复现（关注 Epic 公告，不要假设时间线）。
  3. **保留 5.7 最新 hotfix 作为已测试 Plan B**：万一 5.8.0 在 Linux/MRG 上有阻塞性回归，5.7 仍满足 MetaHuman 批量 API 这条承重梁。
- **平台分工**：MetaHuman **造人/装配/校验在 Windows 上做**（5.8 仍有部分 MetaHuman **身体动画**特性是 Windows-only），Linux **只跑 Sequencer + MRG 批渲染**。

**真值通道可行性（已核实，闭环原 open question）**：MRG 原生输出多层 EXR——World Depth（世界单位深度）、Motion Vectors（归一化 [0,1]，需 rescale）、Object IDs（Cryptomatte 规范分割）。**但 Object IDs / 分割是 Experimental 且仅编辑器可用（"can not be used in shipping builds"）**——因此 Linux farm 必须以**编辑器命令行模式 `UnrealEditor-Cmd`** 跑，**不能用打包 Shipping build**；建议同时准备一套自定义 Stencil/Object-ID 导出作为分割兜底。

---

## 2. 本机 vs 服务器分工 + 工程同步

**分工**

| 阶段 | 在哪做 |
|---|---|
| MetaHuman / CC5 造人、衣橱、IK 重定向、镜头/Sequencer 编排、look-dev、MRG 图编辑 | **Windows 本机**（交互、GUI、全部 MetaHuman 特性可用） |
| 大规模 before/after 矩阵 + 真值通道批渲染 | **Linux 服务器**（`UnrealEditor-Cmd -RenderOffscreen` 无头） |

**工程同步方案（取舍）**

| 方案 | 适用 | 取舍 |
|---|---|---|
| **Perforce Helix Core（推荐为单一真相源）** | 二进制重的 UE 工程（.uasset/.umap） | Epic 官方推荐；独占签出/加锁，杜绝二进制资产被覆盖（不可恢复冲突）；规模化最佳。代价：托管/许可比 Git 重。 |
| Git-LFS | 预算紧、单人/小团队 | 可用，但加锁弱、自动解锁麻烦、每次 clone 拉全部历史二进制导致 repo 膨胀。 |
| rsync / rclone | **渲染产物回传**（EXR/MP4/真值通道） | **正确用法**：派生大数据用 rsync/rclone 回本地或对象存储，**绝不**把工程树或数据集产物提交进 VCS。 |

**推荐组合**：
- **工程（.uproject / Content / Config / C++/插件源码）→ Perforce**。Windows 提交，Linux 服务器跑 P4 client `p4 sync` 同一 depot，**字节级一致，无需 rsync 工程树**。把 .uasset/.umap 设为独占签出（lockable，或 binary+w）。
- **渲染产物 → rsync/rclone** 回存储。
- **代码/脚本/配置**（dispatcher、Python executor 等纯文本）可另用 git-LFS 或直接进 Perforce。

**跨平台卫生（Day 1 就强制）**：
- **Linux 大小写敏感、Windows 不敏感**——`/Game/Char_A` 与 `/Game/char_a` 在 Linux 上是两个不同路径，引用会断。**统一 CamelCase/snake_case、无空格、无仅大小写区别**的资产/文件夹命名。
- UE 拒绝从大小写敏感文件系统运行——保证引擎/工程位于大小写不敏感（或命名正确）的卷上。
- **逐个核实**每个依赖插件（MetaHuman、IK Rig/Retargeter、PCG、MovieRenderGraph）有 Linux 二进制并能无头 cook/run。

**共享 DDC（关键，省冷启动）**：搭建自托管 UnrealCloudDDC，或设 Global Shared DDC Path 指向网络位置，由 Windows 编译预热——Linux 节点跳过逐节点 shader 重编译。注：Epic 的 Azure 版 Unreal Cloud DDC 已于 2024 下线，现在共享/云 DDC 意味着自托管（AWS cloud-game-dev-toolkit）或联系 Epic rep。

**编排**：一变体一进程（`UnrealEditor-Cmd ... per variation`）做崩溃隔离 + 多 GPU 并行；用轻量 Python dispatcher（Flask/REST，参考 unrealRenderFarm；或简单 SQLite/Redis 工作队列）枚举「只改一个因子」矩阵，worker 用自定义 Python executor 按变体注入设置与 depth/motion/segmentation 通道。**AWS Deadline Cloud 的官方 UE submitter 目前仅 Windows（UE 5.4–5.7），Linux farm 用不上**——除非另加 Windows 渲染节点。

---

## 3. 服务器渲染能力自检清单

**要满足的硬件/驱动/系统条件（Epic UE 5.8 Linux 要求 + 项目实际）**

| 项 | 最低（Epic dev floor） | 本项目推荐 |
|---|---|---|
| GPU | NVIDIA RTX 2000 系或更新（GeForce 2080 级、8GB VRAM） | **RTX 4090 / L40S / A6000-Ada 级，24–48GB VRAM**（MetaHuman+Lumen+多通道高分辨率） |
| NVIDIA 驱动 | **专有驱动 570+**（非 nouveau） | 570.169 / 575+ 已验证可用 |
| glibc | 2.28+ | **2.35+**（低于则 dlopen 启动极慢） |
| 内核 | 4.18+ | 4.18+ |
| 系统 RAM | 32GB | **64GB+** |
| 发行版 | Ubuntu 22.04 推荐 / Rocky-RHEL 8+ | Ubuntu 22.04 |
| 存储 | — | 快速 NVMe scratch（视频+depth/flow/seg 极占空间） |
| 编译器（仅源码构建） | clang 18.1.0 (5.6) / **clang 20.1.8 (5.7)** | 按目标版本 |

**逐条检查命令 + 判断标准**

1. `nvidia-smi` → 驱动 ≥ 570、GPU 在列、非 nouveau。
2. **`vulkaninfo`（来自 vulkan-tools）→ 必须看到 NVIDIA GPU + `VK_KHR_swapchain` + SM6 扩展（`VK_EXT_mesh_shader`、`VK_KHR_compute_shader_derivatives`）。**
   - ⚠️ **关键陷阱**：云/数据中心实例可能 `nvidia-smi` 列出 GPU，却装的是 **compute-only 驱动、无图形/Vulkan ICD**，导致 `-RenderOffscreen` 静默失败。**别只信 nvidia-smi**，必须 vulkaninfo 验证。
3. `ldd --version` → glibc ≥ 2.35。
4. `uname -r` → 内核 ≥ 4.18。
5. 确认加载的是专有 NVIDIA 驱动而非 nouveau（`lsmod | grep nvidia`）。
6. **跑一次完整验证渲染**（MetaHuman + Lumen + depth + motion vectors + ObjectID）在你**确切的 UE build + 驱动**上——再扩到 100×100 矩阵。

**无头渲染怎么跑（核心结论：纯批渲染不需要 Xvfb / VirtualGL / VNC / X server）**

- **正解 = 编辑器命令行二进制 + `-RenderOffscreen`（Vulkan）**：
  ```
  Engine/Binaries/Linux/UnrealEditor-Cmd "/path/Project.uproject" MapName \
    -game -RenderOffscreen -unattended -NoSplash -StdOut -allowStdOutLogVerbosity \
    -MoviePipelineConfig="/Game/.../RenderQueue"   # 或 -ExecutorPythonClass=...PythonHostExecutor
  ```
  可加 `-NoTextureStreaming -NoLoadingScreen` 提稳。
- **关键约束**：
  - **Vulkan 不会在缺 X11 时自动开启离屏，必须显式传 `-RenderOffscreen`**（OpenGL 才会自动离屏，但 OpenGL 是 legacy，UE5 需 Vulkan，不可用）。
  - **`-nullrhi` 禁用渲染、产不出帧——绝不能用于采集管线。**
  - **必须用编辑器 `-Cmd` 二进制**（ObjectID/分割是编辑器专属）——**不要** `-game` 打包 Shipping、不要 runtime build。
  - **Xvfb 与 NVIDIA GL 冲突（GLX-visual 错误），且 UE 根本不需要它**——`-RenderOffscreen` 直接处理无头。
- **多 GPU 钉定（重要修正）**：用 **UE 标志 `-graphicsadapter=N`（0 基）作为主手段**，配合 NVIDIA Container Toolkit 做 per-job 设备隔离。**不要只靠 `CUDA_VISIBLE_DEVICES`**——实测它对 Vulkan/NVIDIA-专有路径不选 GPU（仅对 OpenGL 有效）。已知怪癖：即便用了 `-graphicsadapter=N`，日志仍可能打印「GPU 0」却实际在 GPU N 上算。
- **5.6 Vulkan 启动崩溃类问题**的根因是驱动 <570 / 老 GPU 缺 SM6 mesh-shader 扩展——**装驱动 570+ + RTX 硬件本身就是修复**。应急兜底 `DefaultGraphicsRHI=SF_VULKAN_SM5` 会禁用 SM6（伤 Nanite/Lumen 质量），**不适合本数据集保真需求**——优先保证驱动+硬件。
- **安装来源**：Linux 编辑器无 Epic Launcher。要么从 **Epic GitHub releases 拉 Linux 编辑器 .zip**（需把 GitHub 关联 Epic 账号 / org 邀请），要么从 `EpicGames/UnrealEngine` **源码构建**（需自定义 C++ 通道/插件或可复现服务器 build 时）。容器化推荐从 `nvidia/vulkan` 或 `cudagl` 基镜像派生 + NVIDIA Container Toolkit。

---

## 4. 远程看画面 / 操作 UI

**先分清两种需求**：纯批渲染**完全不需要 GUI**（SSH 驱动即可）；偶尔需要在服务器上看 viewport / 调试才用远程桌面。

| 方案 | 评价 | 推荐度 |
|---|---|---|
| **UE Editor Streaming（"Stream Full Editor"，基于 Pixel Streaming 插件）** | 浏览器经 WebRTC 推全编辑器；**支持 Linux host**（编辑器非 root，默认端口变 **8080**，URL 要带 `:8080`）；无需桌面环境；与本技术栈完全契合。**仍是 Experimental**。 | **首选（服务器调试）** |
| **NoMachine（配虚拟/dummy display）** | 远程桌面家族里**无头 Linux + NVIDIA NVENC 支持最强**；可建虚拟桌面。无头机通常需配虚拟/dummy 显示让 GLX/Vulkan surface 落地，先用 `glxinfo`/`glxgears` 验证。 | **稳健兜底** |
| Sunshine + Moonlight | 开源 NVENC，Linux host 比 Parsec 成熟；同样需可捕获的虚拟/dummy display。 | 免费替代 |
| **Parsec** | **Linux 不支持 host（仅 client）** | **排除** |
| 裸 X11 forwarding | 隧道 GLX 差、编辑器 GPU-heavy UI 基本不可用 | **排除** |
| 纯软件 VNC（TigerVNC 等） | 软件编码、延迟高 | 不推荐（用 NoMachine/VirtualGL+TurboVNC 代替） |

**推荐**：
1. **所有大规模批渲染：不用任何 GUI/远程桌面**，SSH 驱动 `-RenderOffscreen` 即可。
2. **服务器上偶尔看 viewport：首选 Editor Streaming**（记得 `:8080`，当 Experimental 用、别做生产硬依赖）。
3. **Editor Streaming 抽风时：NoMachine（虚拟 display）兜底**。
> 项目一旦脚本化，本机 Windows 作者 + 无头 `-RenderOffscreen` 基本能覆盖全部，远程桌面只留给罕见崩溃调试。

---

## 5. 配套软件下载清单

### A. 现在装（原型阶段）

| 软件 | 用途 | 价格 | 平台 |
|---|---|---|---|
| **Unreal Engine 5.8** | 引擎（作者机 + 服务器 build） | 免费（UE EULA） | Win + Linux |
| **NVIDIA 专有驱动 570+ + CUDA**（数据中心驱动） | Linux 无头 Vulkan 渲染 | 免费 | Linux |
| **vulkan-tools（vulkaninfo）** | 自检 Vulkan ICD/SM6 扩展 | 免费 | Linux |
| **NVIDIA Container Toolkit** | 容器 GPU 加速 + per-GPU 隔离 | 免费 | Linux |
| **Blender 4.5+** | DCC 枢纽：资产准备、USD 互通、mocap 清理、CC0 内容、MetaHuman rig 插件 | 免费/开源 | Win + Linux |
| **OpenImageIO / oiiotool（3.1.x）** | 读/拆多层 EXR 真值通道（`--layersplit`）、视频 I/O | 免费（ASWF） | Win + Linux |
| **ffmpeg** | EXR/PNG 序列 → mp4/ProRes | 免费 | Win + Linux |
| **Python 工具链** | UE 内嵌 Python（引擎内自动化）+ 本地 venv（编排/PySDK） | 免费 | Win + Linux |
| **Mixamo（web）** | **占位/原型**动画（入库前查再分发条款） | 免费 | web |
| **Perforce Helix Core** | 工程版本控制单一真相源 | 免费档（≤5 用户/20 工作区）/付费 | Win + Linux |

> 原型期 MetaHuman + Mixamo **仅用于验证 before/after + 真值通道管线**，不入正式数据集（见第 6 节许可风险）。

### B. 后续装（规模化 / 许可安全资产）

| 软件 | 用途 | 价格 | 平台 |
|---|---|---|---|
| **Reallusion Character Creator 5（CC5）** | **数据集真实角色源**（已兼容 MetaHuman 骨架，可与 MetaHuman 在 Sequencer 互换免重定向）；含免费 "Auto Setup for Unreal" 与 "CC UE Control Rig" 插件 | 付费（永久授权） | Win（导出供 UE） |
| **Marvelous Designer** | 服装/garment 制作 | 付费 | Win/Mac |
| **Fab / Quixel 环境与道具** | 场景/prop（遵守 Fab 许可与 NoAI 标签） | 免费/付费 | — |
| **Cryptomatte-aware mask decoder** | 把 Cryptomatte 解为实例掩码（Nuke/Blender 或 python cryptomatte 库） | 免费/付费 | — |
| **自托管 UnrealCloudDDC**（AWS cloud-game-dev-toolkit） | 共享 DDC，免逐节点重编 shader | 免费（自托管，需运维） | Linux |
| **rclone**（若用对象存储） | 产物回传 S3/MinIO | 免费 | Linux |

### C. 只需在 UE 内启用的插件（无需单独下载）

`Edit > Plugins` 启用即可：
- **MetaHuman**
- **IK Rig + IK Retargeter**
- **Movie Render Queue + Movie Render Graph + Movie Render Queue Additional Render Passes**
- **PCG**
- **Pixel Streaming**（仅当要远程交互预览服务器时）

> 真值通道设置：启用 "Movie Render Queue Additional Render Passes"；Deferred Renderer 下启用 `MovieRenderQueue_WorldDepth` 与 `MovieRenderQueue_MotionVectors` 后处理材质；`Project Settings > Rendering` 设 Velocity Path = "Write during base pass" 以出 motion vectors。Object IDs 走 Cryptomatte 规范（Experimental、仅编辑器）。

---

## 6. 未决 / 需用户确认的点

**许可（最高优先级，可能推翻技术选型）**
1. **MetaHuman 许可（UE EULA + MetaHuman Content Addendum）明确禁止将 MetaHuman 内容用于 AI/ML 训练、构建、增强、测试。** 你的项目正是生成视频编辑模型的训练数据——**用 MetaHuman 渲染帧作为数据集主体涉嫌违约**。
   - **行动**：MetaHuman **仅作原型/管线验证**；最终数据集角色迁移到 **CC5 / CC0 / 自建资产**。**正式渲染前务必书面向 Epic licensing 确认**最终主体不源自 MetaHuman。
2. **确认 CC5 EULA 是否明文允许把渲染出的 CC5 角色用作 AI/ML 训练数据**（而非仅"商业产品用途"）——扩量前必须核实。
3. **Mixamo / Fab / Quixel 等内容**的再分发条款：「原型可用」≠「可作为已发布数据集分发」，逐源审计训练数据再分发许可。

**服务器与基础设施（需用户提供事实）**
4. **服务器具体 GPU 型号与 VRAM？** 用于精确定容（MetaHuman+Lumen+depth+motion+ObjectID 多通道在目标分辨率下的 VRAM 上限）。
5. **单台多 GPU 机 vs 多节点集群？** 单机 → 简单本地进程池；多节点 → 需 REST/队列 dispatcher + 共享/云 DDC + 共享工程存储。
6. **是否已有 Perforce？** 若无、且预算紧、单人作业，可退而用 git-LFS（接受弱加锁 + repo 膨胀）。
7. **云实例驱动是否含图形/Vulkan 栈**（非 compute-only）？用 `vulkaninfo` 实测确认。
8. **是否会有 Windows 渲染节点？** 若有，AWS Deadline Cloud 的官方 UE submitter 可用，能替代自建 dispatcher。
9. **数据集总规模与留存策略？** 决定产物走本地 NVMe+rsync 还是对象存储+rclone，以及 DDC 容量。

**技术待经验验证（扩量前做冒烟测试）**
10. **5.8.1 hotfix 何时发布、是否修 Linux/MRG/MetaHuman 批量回归**——监控 Epic 公告（截至 2026-06-19 尚无 5.8.1）。
11. **MRG 是否在 `-RenderOffscreen` 无头下与 MRQ 完全等价**，且 5.8 production MRG 暴露同样的 Additional Render Passes（depth/motion/object-id）——尚未确认，必要时关键通道留在 MRQ。
12. **Object-ID/Cryptomatte 分割在 headless `UnrealEditor-Cmd` 上能否稳定大规模跑**——准备自定义 Stencil/Object-ID 兜底。
13. **跨平台确定性**：Windows 作者 vs Linux 渲染的 before/after 配对是否逐像素对齐（RNG 种子、temporal AA/denoiser、motion-vector 生成）——需一次像素 diff 验证。
14. **Linux 不支持 Vulkan 光追**——若任何通道/观感依赖硬件 RT，Linux 渲染会与 Windows 预览有差异，尽早验证 look-parity（用 Lumen 软件回退 / Path Tracer 评估）。
15. **5.8 中哪些 MetaHuman 身体动画 / IK 重定向操作仍 Windows-only**——确认 action 变体生成能否在 Linux 端到端无头跑。

Sources: [UE 5.8 发布（80.lv）](https://80.lv/articles/unreal-engine-5-8-is-out-today-with-big-optimization-improvements-and-mesh-terrain), [5.6.1 Hotfix（Epic 论坛，节奏佐证）](https://forums.unrealengine.com/t/5-6-1-hotfix-released/2639316), [UE 5.8 Release Notes（Epic）](https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-5-8-release-notes)
