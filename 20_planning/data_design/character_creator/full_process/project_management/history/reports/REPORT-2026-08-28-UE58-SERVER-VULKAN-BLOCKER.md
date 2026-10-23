# UE 5.8 服务器 Vulkan 像素渲染阻塞报告

> 文档 ID：`REPORT-2026-08-28-UE58-SERVER-VULKAN-BLOCKER`
> 文档类型：`history_report`
> 生命周期：`completed`
> 报告日期：2026-08-28
> 影响范围：`WF-00/WF-80`、`PLAN-2026-08-FIRST-DATA-BATCH/R08`
> 原始证据：`%OUTPUT_ROOT%/server_preflight/job117396_ue58_vulkan_pixel_smoke_manifest_20260828.json`；`%OUTPUT_ROOT%/server_preflight/ue58_vulkan_cube_smoke/job117538_20260828_live01/`；同层 `job117538_20260828_source_patch_ab01/` 与 `job117593_driver580_v28_point_three_capture/`；真实工程 `job117593_datatry02_preflight_v05/` 与 `job117593_datatry02_pixel_v09_rt_off/` 至 `v13_cloud_off_b/`
> 最近核验：2026-08-28

## 结论

`H64Y574/job117396` 和 `GDS9B74/job117538` 两个独立节点上的 UE 5.8 均可启动、Cook 和 Package，但 NVIDIA H200/565.57.01 环境无法稳定完成可见 Vulkan 像素输出。原始独立工程 9/9 探针和 3/3 运行参数消融失败；后续 source compatibility build 虽曾完成一次 no-capture 运行并写出一张全黑 PNG，仍会在图形 `BasePass -> BasicShapeMaterial Cube` 停滞。565.57.01 作用域的 `VAL-SERVER-01` 保持 `failed`。

新增的跨驱动控制提供了更强结论：相同 H200 型号、相同 source-patched package 和相同 Vulkan 配置在 `8GS9B74/job117593/NVIDIA 580.126.20` 上可以完成渲染。点光源地图连续三次独立启动均推进 20 帧、保存可见 `640x360` PNG 并 `EXIT_CODE=0`；三张图哈希完全一致，且没有 GPU hang 或 RenderThread timeout。这三次稳定性运行关闭了 Validation；后续 Validation 专项运行仍成功截图和退出，但保留三类 UE 规范问题。

因此“服务器 H200 不能渲染”已被否定，驱动版本/节点图形栈是 565 失败的强边界因素。后续真实工程控制进一步证明 `datatry_02` 可在 580.126.20 上完成两次启动和五次 SM6 截图；“只能渲染最小 Harness”也被否定。

580.126.20 的诊断步骤已成功，但完整 `VAL-SERVER-01` 仍记为 `pending`：旧 `Main` 诊断地图引用未随清单传输的可选模块化 Pilot，当前截图没有角色且重复哈希不一致；正式 MRQ/MRG、真实项目 Vulkan Validation 和 10 节点基准尚未验收。后续检查已确认第一批正式资产闭包完整，因此不再把该 Pilot 记录为生产内容 blocker。

## 环境

| 项目 | 值 |
| --- | --- |
| Slurm | `job117396`，节点 `H64Y574`，1 张 H200，14 CPU |
| GPU/驱动 | NVIDIA H200 / `565.57.01` |
| CUDA | `nvidia-smi` 报告 12.7 |
| UE | `%LANCE_ROOT%/00_engine/unreal/UE_5.8` |
| 项目 | `%LANCE_ROOT%/00_engine/projects/datatry_02/datatry_02.uproject` |
| 源地图 SHA-256 | `e45167092fb3d213b68481803daa14a0bcacdeef7a31e9a9ff2f7a1ed118e987`，诊断前后相同 |

Epic 的 [UE 5.8 Linux Development Requirements](https://dev.epicgames.com/documentation/unreal-engine/linux-development-requirements-for-unreal-engine?lang=en-US) 在报告日期要求 NVIDIA 570 或更高版本；当前 565.57.01 低于该边界。

## 最小复现矩阵

| 测试 | 结果 | 关键观察 | 原始日志 SHA-256 |
| --- | --- | --- | --- |
| SM5、14 CPU、无光照最小 MRQ | `failed` | 进入渲染但无图 | `b9d36c1b37059040203dfa8b014ebebc74aa62bd5e714b875b32400f85990e3a` |
| ES3.1、14 CPU、无光照最小 MRQ | `failed` | Camera Cut 处理结束但不完成输出 | `507ff785143d4f3ff11078a9eb6e18f2fe06f9f6af3c9470c3fe63b0073bac21` |
| ES3.1、无 RHI 线程、Vulkan Validation | `failed` | 无图；报告 `VUID-vkCmdDispatch-imageLayout-00344` | `82b886158236fe5c3c69365d1ee1e71e667beb72452d53edafb18d7af698d056` |
| Lavapipe 软件 Vulkan、ES3.1 | `failed` | 加载 Media 模块时 SIGSEGV | `cf3d1ab658e6294559d4e1aab4b22917b2d603c8ccd1180064efd4c751b43189` |
| 最小 packaged SM5 HighResShot | `failed` | 60 秒后 GameThread 等待 RenderThread 超时 | `4b9c314f15e1aea33a3951a8a12454974dbcdb60d610a00ab4a6b3c318782aa2` |
| 最小 packaged SM5 单线程 HighResShot | `failed` | 180 秒仍停在像素捕获且无图 | `3426432c34241c7e2a246552c1cd95e0d15bdea7dea66ea3c852fbe5efa25e76` |
| 最小 packaged SM5 Lavapipe HighResShot | `failed` | 成功选择 llvmpipe 并加载 cooked shader，创建 GameWindow 时在 libc `0x4251f` 空指针 SIGSEGV | `9b4fcb49be955774e63addd9f1232d369d97772b2217a9a830db9bfea7eb9f0c` |

最小 packaged 工程只携带约 10 KB 的无光照地图。它在硬件 Vulkan 下复现阻塞，在 Lavapipe 下复现空指针崩溃，排除了复杂场景、角色、MRQ、Editor 插件和 Media 模块作为首要原因。所有测试合计找到的有效像素文件数量为 0。

## 第二次独立核验

`GDS9B74/job117538` 使用全新 `UE58VulkanCubeSmoke` 工程复核，未复用 `datatry_02` 的地图、插件或 Render Job：

| 项目 | 结果 |
| --- | --- |
| GPU/驱动/UE | H200 / `565.57.01` / `5.8.0-55116800` |
| Vulkan | 强制 NVIDIA ICD；loader 1.3.204；NVIDIA API 1.3.289；未选择 Mesa/Lavapipe |
| 地图 | 5 个 Actor：正方体、地面、相机、方向光、点光 |
| 渲染特性 | Vulkan Desktop SM5；关闭 Lumen、Nanite、VSM、RT、Path Tracing、AA 和后处理 |
| 构建 | NullRHI 生成地图通过；传统 Pak Cook/Package 通过，exit 0 |
| 渲染 | 9/9 探针 exit 139；`renders/` 为空 |
| GPU 采样 | 每次最高 100% utilization，峰值显存仅 847–952 MiB |

探针分别覆盖有/无 HighResShot、有/无 Validation、合法默认 Sync2/Dynamic Rendering、完整 legacy render-pass 路径、关闭 split barriers 和关闭 memory-barrier 折叠。默认合法路径反复报告：

```text
VUID-vkCmdDraw-None-09600
FBlackTextureWithSRV expected VK_IMAGE_LAYOUT_GENERAL,
current layout VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL
```

随后均出现 `GameThread timed out waiting for RenderThread after 60.00 secs`。无 HighResShot 的普通帧探针同样失败，排除 PNG 写入和像素 readback 是首要原因；关闭 Validation 后仍失败，排除 Validation layer 自身是首要原因。完整命令、逐秒 GPU CSV、UE 日志和状态表见第二个原始证据目录中的 `REPORT.md`。

两节点结果将故障收敛到 UE 5.8 Vulkan RHI、565 驱动和 H200 图形路径这一组合，但在旧版 UE 同机 A/B 完成前，不能单独断言是驱动缺陷或 H200 硬件不适用。

## 兼容性消融与源码核验

`GDS9B74/job117538` 在同一 package 上追加三个无截图、开启 Validation 的探针：

| 探针 | 唯一或组合变化 | 结果 | 解释边界 |
| --- | --- | --- | --- |
| A1 | `r.TranslucencyLightingVolume=0` | exit 139；`RWAmbient1` 消失，但保留 `ClearResource`、`FBlackTextureWithSRV`，并出现 `RWOutputTexture` 格式不匹配 | 只证明 TLV 对其中一个 invalid access 有贡献，不是渲染成功 |
| A2 | `r.Vulkan.AllowDynamicRendering=0`，Sync2 保持开启 | exit 139；`ClearResource`、`RWAmbient1`、`FBlackTextureWithSRV` 和 timeout 均保留 | Dynamic Rendering 不是当前单项修复开关 |
| A3 | TLV 与 Dynamic Rendering 同时关闭 | exit 124；记录 `ClearResource` 与 `RWOutputTexture` | 冷启动 106.57 秒后被 120 秒外层 timeout 终止，未进入完整 watchdog 周期，不能用后续 VUID 未出现证明其消失 |

源码核验确认 `VulkanUAV.cpp` 的 typed buffer 分支固定实例化 4 通道 clear shader，而失败 view 为 `PF_R32_SINT`。随后取得 source-complete UE 5.8 并完成 compatibility build；最终诊断包包含 typed buffer/texture clear channel、LUT format、Vulkan light grid/manual vertex fetch、GPU breadcrumb、translucency 和 tonemap compute intermediate 共八项 patch。由于它们是逐步收敛后的组合包，当前成功不能归因于单一 exact-channel patch。

设备阶段打印 `Enabling Vulkan Descriptor Buffers`，但 validation 对象明确为 `VkDescriptorSet`；仅凭 enable 日志不能证明失败来自 Descriptor Buffer 内存编码路径。

## Source build 与跨驱动控制

| 作用域 | 结果 | 解释 |
| --- | --- | --- |
| `GDS9B74/job117538/H200/565.57.01/source-patched v16` | no-capture 曾 exit 0；capture 写出一张有效但全黑 PNG；后续运行停在 BasePass | UE-side patch 改变了失败形态，但 565 路径未达到可见像素稳定门禁 |
| `8GS9B74/job117593/H200/580.126.20/source-patched v16` | 同一 package 推进 20 帧并 exit 0 | 跨驱动控制越过 565 的 BasePass stall |
| `8GS9B74/job117593/H200/580.126.20/point-map v28` | 三次独立启动均输出 8166-byte 可见 PNG、exit 0；初始化 2.47–3.40 秒 | 最小像素三帧门禁通过；静态图三次 SHA-256 均为 `2dec100d...45633b` |

GPU CSV 固定成功设备 UUID 为 `GPU-aa8fcb15-176d-82d6-4453-4c11a49bfb7f`。成功日志明确选择 `NVIDIA H200`、driver `580.126.20`、Vulkan API `1.4.312`。画面可见地面、几何体和点光源受光轮廓，但曝光和构图只满足诊断级可见像素检查。

开启 `-vulkanvalidation=2` 的 `job117593_driver580_v29_point_validation/` 仍写出相同 PNG 并 exit 0，但报告：`OutComputeTexture` shader `Rgba32f` 与 view `VK_FORMAT_B10G11R11_UFLOAT_PACK32` 不匹配；HighResShot 的 `FDummyViewport` descriptor 期望 `TRANSFER_SRC_OPTIMAL`、实际为 `COLOR_ATTACHMENT_OPTIMAL`；退出时 `SceneDepthZ` 未在 `vkDestroyDevice` 前销毁。它们在 580 上未造成 hang，但必须在冻结生产 compatibility build 前处理或明确接受边界。

`r.PSOPrecaching=1` 在 565 与 580 上都出现过 `PipelineStateCache.cpp:3185` 计数 ensure 和约 100 秒冷启动，580 仍能在 ensure 后渲染成功。三次复验设置 `r.PSOPrecaching=0` 后没有该 ensure，初始化降至数秒；因此 PSO ensure 是独立 UE 5.8 问题，不足以解释 565 的 GPU stall。

## 真实项目控制

`job117593_datatry02_preflight_v05/` 使用 source-patched `UnrealEditor` 对 `datatry_02` 连续运行两次离屏启动，cold/repeat 分别为 129/126 秒，均 exit 0 且无 fatal signature，最终为 `PASS_WITH_WARNINGS`。项目选择 Vulkan SM6、NVIDIA H200 和 580.126.20；唯一环境警告为没有独立 `vulkaninfo`，UE Vulkan 日志提供了设备证据。

直接像素探针先暴露一项配置冲突：Vulkan SM6 项目启用 Ray Tracing 时又传入 `-BindlessOff`，ShaderCompileWorker 在 `FPathTracingRG` 触发 `SpirVShaderCompiler.inl:1669` assertion。通过 RendererSettings override 关闭 Ray Tracing 和 Ray Tracing Proxies 后，该 assertion 消失；第一次完成 SM6 shader 冷编译约 13 分钟，后续复用 DDC 的运行约 70 秒。

`job117593_datatry02_pixel_v09_rt_off/` 至 `v13_cloud_off_b/` 五次都加载 `/Game/Main`、写出非黑 `640x360` RGBA PNG、推进到 benchmark exit 并记录 `LogExit: Exiting`。日志无 GPU hang、RenderThread timeout 或 Vulkan error。这证明真实项目渲染入口可用，但不是正式 MRQ/MRG 证据。

五张 PNG 的 SHA-256 不同。前三张可见 Volumetric Cloud 状态变化；关闭 `r.VolumetricCloud=0` 后，`v12/v13` 视觉一致，但仍有 6188/230400（2.69%）像素变化，差异位于地平线以下、单通道最大为 5。需要固定 warm-up、目标帧、种子和 temporal/dither 状态后再定义生产确定性结果。

`/Game/Main` 引用的 `/Game/DataMake/Characters/M02_Average/BP_DM_M02_ModularPilot_v002` 不存在，日志随后报告 Body、hair 和 outfit 的 `CreateExport: Failed to load Outer`；因此五张诊断图只有天空和地面，没有角色。进一步核验表明它是模块化 Pilot，不属于第一批生产依赖：项目 `checksums.sha256` 从未列出它，正式 staging map、Sequence 和 MRQ Preset 也不引用它。上传清单 8277/8277 路径均存在，正式矩阵的 32 个 Look Blueprint、30 个 Composite animation 和三个核心渲染资产共 65 项逐一重算哈希全部匹配。Engine Experimental `EditorToolset/ToolsetRegistry` 的 Python startup 还引用当前 build 不提供的 `unreal.AgentSkill`/`unreal.PythonTestRunner`，虽不致命，也应在生产 runtime profile 中禁用或修正版本。

## 恢复条件

1. 使用已核验的正式 staging map、Render Workspace、MRQ Preset 和冻结 Look/composite bindings，并清理不需要的 Experimental Toolset runtime 启动项；不需要为第一批恢复可选 Pilot。
2. 固定 H200/580.126.20、SM6 compatibility profile、warm-up、种子、目标帧和 temporal/dither 设置，连续两次渲染同一正式 MRQ/MRG 代表节点。
3. 两次都必须加载冻结资产、产生可见角色/场景像素、无 GPU hang/RenderThread timeout、正常退出并通过明确的确定性阈值；最终 profile 还需完成 Vulkan Validation 边界检查。
4. 代表节点通过后才运行 10 节点基准；10/10 accepted 后才冻结生产 compatibility profile。
5. 565.57.01 继续保留为失败边界和根因研究作用域，不再阻塞 580 生产候选，也不直接用于正式渲染。

## 防回归改进

诊断完成后，`20_planning/implementation/FIRST_BATCH_SERVER_PREFLIGHT.sh` 增加 `SVR-02A`：当 `EXPECTED_UE_VERSION` 为 5.8 时，NVIDIA 驱动主版本低于 570 会硬失败，并阻止项目 Smoke。实际在同一 `job117396` 运行 environment-only 集成检查后得到：

```text
[SVR-02A] FAIL UE 5.8 requires NVIDIA driver 570+; found 565.57.01.
Final verdict: FAIL
```

该检查的原始结构化报告位于 `%OUTPUT_ROOT%/server_preflight/job117396_driver_gate_20260828_24/`。旧版 UE 分支不会继承 UE 5.8 的固定门槛，但会保留警告并要求独立兼容性验收。

本报告记录从 565 失败到 580 最小及真实工程像素恢复的完整诊断边界，不关闭计划需求、不构成生产里程碑，也不改变本地执行器已经通过的 Gate。
