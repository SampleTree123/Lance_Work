# Linux/NVIDIA 服务器执行

2026-10-29新增修复展示导出：`00_engine/render_pipeline/showcase/repair_examples_20261029/`由本文负责，用户明确授权网页及24份正式production视频副本入Git。媒体范围仅限此展示目录；全量运行证据保留服务器，用户视觉验收及整体dataset替换仍待确认。目录和校验说明见[发布记录](../../../../../../00_engine/render_pipeline/docs/REPAIR_SHOWCASE_PUBLICATION_20261029.md)。

2026-10-28展示工具追加 `00_engine/render_pipeline/tools/server/build_branch_showcase.py`，生命周期production、归属本文。复用build_chain_showcase.py的属性解释和复制校验；冻结8个分叉会话，验证真实父子关系、单轴变化与图边，再输出branch_examples.json和branch_data.js并合并媒体SHA256清单。branches.html用SVG与两条root-to-leaf路径呈现，共享前缀重复引用同一份媒体。输出仍在获准的同一showcase目录，不创建运行outputs类别；[记录](../../../../../../00_engine/render_pipeline/docs/BRANCH_SHOWCASE_20261028.md)。

2026-10-28新增离线展示工具：`00_engine/render_pipeline/tools/server/build_chain_showcase.py` 由本文负责，生命周期为production（数据展示导出，不执行UE渲染）。从服务器已整理的节点/会话JSON及motion catalog读取属性，冻结selection后验证完整直链与单轴变化，再用 `--copy-media` 创建真实MP4副本；不改源数据。输出范围为 `00_engine/render_pipeline/showcase/chain_examples_20261028/`，属于用户特许保留并入Git的展示包，不在运行outputs中，禁止扩展此例外到其他媒体。临时抽帧/浏览器证据在该目录validation内忽略入Git；正式选例与校验摘要见[展示归档](../../../../../../00_engine/render_pipeline/docs/CHAIN_SHOWCASE_20261028.md)。网页源码与离线字体一并保存，正式训练prompt未上传时只写真实属性差异，不冒充训练指令。

> 文档 ID：`TECH-RENDER-02`
> 文档类型：`technical`
> 生命周期：`current`
> 适用阶段：`WF-00/WF-80`
> 实现所有权：服务器预检、项目同步、10 节点基准、并发和重试
> 验证所有权：`VAL-SERVER-01`
> 输出契约：`OUT-WF00-SESSION`、`OUT-WF80-NODE-MEDIA`
> 运行环境：Linux、NVIDIA、Vulkan、Unreal Engine 5.8
> 最近核验：2026-10-23文档与路径；渲染Gate证据为2026-08，未重跑UE

## 1. 当前状态

2026-10-23接手修正：第一批已完成发布；下文保留当时的诊断/生产配方，不是当前运行中的作业。历史生产profile记录的source compatibility引擎现已不在原路径，Installed Build不能自动替代；实时准备项见[服务器同步状态](../../project_management/status/SERVER_SYNC_STATUS.md)。文档同步按[DOCUMENT_SYNC](DOCUMENT_SYNC.md)处理。

预检、正式 Render Job 执行器、长驻 Editor wrapper 和多节点 batch supervisor 均已存在。`H64Y574/job117396` 与 `GDS9B74/job117538` 仍证明 H200/565.57.01 不能作为 UE 5.8 生产环境；source compatibility build 在该驱动上至多写出过一张全黑 PNG，随后仍稳定停在 `BasePass`。

跨驱动控制已改变总体结论：同一 H200 型号和同一 source-patched package 在 `8GS9B74/job117593/580.126.20` 上通过最小像素和真实工程像素诊断。正式 Tokyo MRQ 随后完成样例链、同节点独立确定性复验、10 节点基准与中断恢复。`v003` 证明单个 UE invocation 的 50 节点资源边界，但其 61 个媒体因动画 section 起点首帧错误全部禁止交付和复用。section-0/evaluation-preroll 修复通过 6/6 高风险动作/机位回归后，正式 Run Root `first_batch_server_production_20260829_v004` 以 50 节点/Editor 完成 640/640 accepted；13 个 invocation 全部 exit 0，累计媒体、Sidecar、哈希、规格、首帧、Pose Driver 和时间运动审计通过。服务器 H200/580 和真实项目生产路径已证明可行；剩余边界是最终 profile 的 Vulkan Validation 补测，而不是媒体完整性。

旧 `/Game/Main` 缺少可选 `BP_DM_M02_ModularPilot_v002`，但它不是第一批正式依赖；`checksums.sha256` 的 8277 项和 65 个关键正式文件均已核验。正式运行使用 Tokyo staging map，人物、服装、动作和四相机均已出现在 accepted 视频中。当前冻结 50 节点/Editor，并强制 section 0、帧 `-1` evaluation preroll 和 Sidecar Gate；仍禁止一次性把单 Editor 节点数扩到 640，也不能把资源压力证据写成完整媒体 Gate。

### 1.1 当前目标环境证据

2026-08-28 核验范围：

| 项目 | 实际值 |
| --- | --- |
| Slurm | 565 失败：`job117396/H64Y574`、`job117538/GDS9B74`；580 候选：`job117593/8GS9B74` |
| NVIDIA | 均为 H200；失败驱动 `565.57.01`，成功候选驱动 `580.126.20` |
| UE | 初期Installed Build在`%LANCE_ROOT%/00_engine/unreal/UE_5.8`；最终生产使用发布profile中的外部source compatibility build，二者不可混称 |
| 项目 | `datatry_02` 与独立 `UE58VulkanCubeSmoke` |
| 证据 | [服务器 Vulkan 阻塞报告](../../project_management/history/reports/REPORT-2026-08-28-UE58-SERVER-VULKAN-BLOCKER.md)；正式节点为 `first_batch_server_tokyo_chains_20260829_v002`、`first_batch_server_tokyo_benchmark10_20260829_v001` 和 `first_batch_server_tokyo_supervisor_smoke_20260829_v001` |

已排除的上层原因：

- 最小无光照地图在 SM5 和 ES3.1 下均能加载，MRQ 能推进到 Camera Cut 完成，但没有 PNG。
- 关闭 RHI 线程、改成单线程、预创建输出目录和禁用高阶渲染特性均无效。
- 仅含 10 KB 地图的 packaged runtime 在 `HighResShot` 处同样阻塞；多线程版本 60 秒后报告 RenderThread timeout，单线程版本 180 秒仍无图。因此主因不在 MRQ、Editor 插件或正式执行器。
- Vulkan Validation 报告图像布局错误 `VUID-vkCmdDispatch-imageLayout-00344`；Lavapipe 软件 Vulkan 在 Editor 和最小 packaged runtime 中均以同一 libc `0x4251f` 空指针 SIGSEGV 退出，不能作为生产降级。
- 诊断前后源地图 SHA-256 均为 `e45167092fb3d213b68481803daa14a0bcacdeef7a31e9a9ff2f7a1ed118e987`，原始关卡未被修改。
- 第二次核验的独立工程只含引擎正方体/地面/相机/基础灯光，固定 NVIDIA ICD、Vulkan SM5 并关闭 Lumen/Nanite/VSM/RT/AA/后处理；地图生成和传统 Pak Package 通过，但 9/9 渲染探针均 exit 139、零 PNG。
- 第二次 Validation 在默认合法路径稳定报告 `VUID-vkCmdDraw-None-09600`：`FBlackTextureWithSRV` 期望 `GENERAL`、实际为 `SHADER_READ_ONLY_OPTIMAL`，之后 RenderThread 超时。有/无截图、有/无 Validation、关闭 split barriers 或 memory-barrier 折叠均未修复。
- 九次采样都曾达到 100% GPU utilization，但峰值显存仅 847–952 MiB；这不是显存容量不足，100% 也不代表有效渲染吞吐。
- 后续 3 次兼容性消融证明 `r.TranslucencyLightingVolume=0` 只会移除 `RWAmbient1`，随后出现 `RWOutputTexture` 的 `Rgba32f` 对 `A2B10G10R10` 格式不匹配；单独关闭 Dynamic Rendering 不改变 `ClearResource`、`RWAmbient1`、`FBlackTextureWithSRV` 和 timeout 链。
- `ClearResource` 在地图主渲染前稳定出现：shader 为 `Rgba32i`，typed buffer view 为 `R32_SINT`。本地源码确认 `VulkanUAV.cpp` 对 typed buffer 固定选择 4 通道 clear shader；这提供 UE 侧可验证修复点，但不排除 565 驱动对错误命令更敏感。
- 后续取得 source-complete UE 5.8 并编译八项诊断/兼容 patch，覆盖 typed buffer/texture clear、LUT format、Vulkan light grid/manual vertex fetch、GPU breadcrumb、translucency 和 tonemap compute intermediate。565.57.01 上曾有一次 no-capture 正常退出和一张有效但全黑的 PNG，随后带图形 BasePass 的运行仍停在 `BasicShapeMaterial Cube`；因此 565 仍未通过可见像素门禁。
- 同一 source-patched package 在 `8GS9B74/H200/580.126.20` 首次对照中推进 20 帧并正常退出；点光源地图截图随后一次成功，并追加三次独立启动复验。三次均在 2.47–3.40 秒完成初始化、保存 PNG、推进至第 22 tick 并正常退出，没有 GPU hang 或 RenderThread timeout；这三次关闭了 Validation。
- 单独开启 `-vulkanvalidation=2` 的第四次 580 运行仍输出相同 PNG 并 exit 0，但报告 `OutComputeTexture` 的 `Rgba32f/B10G11R11` storage format 不匹配、HighResShot `FDummyViewport` 的 `TRANSFER_SRC/COLOR_ATTACHMENT` layout 不一致，以及退出时 `SceneDepthZ` 未销毁。580 驱动能完成命令不等于 UE 状态规范正确。
- 三张 PNG 均为 8166 bytes，SHA-256 均为 `2dec100ddf33431f546a5a4f63cd8a4c352e610bce670eb87a83a6eb2f45633b`。画面可见地面、几何体和受光轮廓，但曝光/构图仅满足诊断要求，不是生产视觉质量证据。
- `r.PSOPrecaching=1` 在 565 和 580 上都可能触发 `PipelineStateCache.cpp:3185` 计数 ensure，并使冷启动接近 100 秒；580 仍能在 ensure 后完成渲染。三次稳定复验使用 `r.PSOPrecaching=0`，初始化降至约 2.5–3.4 秒。该 ensure 是独立 UE 5.8 问题，不是 565 GPU hang 的充分解释。
- 正式预检对 `datatry_02` 连续执行两次 `/Game/Main` 离屏启动：cold 129 秒、repeat 126 秒，均 exit 0 且无 fatal signature，最终 `PASS_WITH_WARNINGS`。唯一环境警告是缺少 `vulkaninfo`；UE 日志本身已确认选中 H200/580.126.20 Vulkan 设备。
- `datatry_02` 项目配置目标为 Vulkan SM6。保留项目 `r.RayTracing=True` 同时传入 `-BindlessOff` 会在 `FPathTracingRG` 的 ShaderCompileWorker 触发 `SpirVShaderCompiler.inl:1669` assertion；以命令行 RendererSettings 关闭 Ray Tracing 和 Ray Tracing Proxies 后，编译、地图加载、截图和退出均完成。这是配置冲突，不是 GPU 渲染失败。
- 关闭 Ray Tracing、Translucency Lighting Volume、PSO Precaching，并启用 Vulkan compatibility CVar 后，五次运行均从 `/Game/Main` 写出 `640x360` RGBA PNG 并 exit 0。第一次 SM6 冷编译约 13 分钟，复用 DDC 后约 70 秒；成功日志没有 GPU timeout、RenderThread timeout 或 Vulkan error。
- 五张项目 PNG 哈希均不同。前三张主要受 Volumetric Cloud 异步状态影响；关闭 `r.VolumetricCloud` 后两张画面视觉一致，但仍有 6188/230400（2.69%）像素变化，差异只在地平线以下，单通道最大差值为 5。生产 profile 仍需固定 warm-up、目标帧、随机种子和 temporal/dither 状态。
- `/Game/Main` 依赖的 `/Game/DataMake/Characters/M02_Average/BP_DM_M02_ModularPilot_v002` 在服务器 Content 中不存在，导致 `CreateExport: Failed to load Outer`，所以当前诊断截图没有角色。该 Blueprint 是模块化 Pilot，不在第一批冻结资产清单或项目 `checksums.sha256` 中；正式 staging map、Sequence 和 MRQ Preset 也不引用它。Engine Experimental `EditorToolset/ToolsetRegistry` Python 启动还引用缺失的 `unreal.AgentSkill`/`unreal.PythonTestRunner`；该错误非致命，但生产 runtime 应禁用或修正版本匹配。
- 上传完整性复核读取项目 `checksums.sha256`：8277/8277 清单路径均存在；正式矩阵的 32 个 Look Blueprint、30 个 Composite animation、staging map、Render Workspace Sequence 和 MRQ Preset 共 65 个文件逐项重算 SHA-256，65/65 匹配。因此旧 Main 的 Pilot 缺失不能再归类为第一批生产内容缺失。

以下为2026-08-28时点要求及当时配方，执行新渲染前仍需重新核实。Epic 的 [UE 5.8 Linux Development Requirements](https://dev.epicgames.com/documentation/unreal-engine/linux-development-requirements-for-unreal-engine?lang=en-US) 在本次核验日期要求 NVIDIA 570 或更高版本。当前跨驱动结果与该边界一致：565.57.01 失败，580.126.20 通过最小和真实工程像素门禁。现阶段执行顺序为：

1. 固定 `8GS9B74/H200/580.126.20` 候选、source compatibility package 和 CVar 组合，记录 GPU UUID、package 哈希与项目输入哈希。
2. 使用已核验的 `L_DM_TokyoStylized_FirstBatchRender_v001`、`LS_DM_FirstBatch_RenderWorkspace_v001`、MRQ Preset 和冻结 Look/composite bindings；禁用不参与 runtime 的 Experimental Toolset 启动项。
3. 使用已冻结的 `h200_vulkan_sm6_580_tokyo_v1`、16/8 warm-up、目标相机全工作区隔离、section 0、帧 `-1` evaluation preroll 和首帧连续性 Gate；同节点逐帧确定性已通过容差阈值。
4. `job117924/v003` 把资源边界验证为 `50 nodes / Editor invocation`，但旧媒体已被视觉 Gate 作废；`v004` 已按该边界完成 640/640 accepted，13 个 invocation 全部 exit 0。后续同类生产继续保持 50 节点边界；最终真实项目 Vulkan Validation 仍须单独复查并限定 repeatable VUID。
5. 565.57.01 路径不再作为生产候选；其 descriptor/layout 与 BasePass 证据只用于后续 engine/driver 根因诊断。候选仍包含多项诊断 patch，不能把成功归因于单个 patch。

### 1.2 Tokyo 正式节点服务器入口

`00_engine/scripts/unreal/run_first_batch_server_render_jobs.py` 已把 `h200_vulkan_sm6_580_tokyo_v1` 接入正式 Render Job 执行器。它保留长驻 Editor 和 Remote Execution，去掉像素探针专用的 `-game`、`-BENCHMARK`、`-BENCHMARKSECONDS`、`HighResShot` 与自动退出；同时固定 `-RenderOffscreen`、Vulkan SM6、`-BindlessOff`、Ray Tracing/PSO/Translucency Lighting Volume/Volumetric Cloud 关闭及已验证的 Vulkan/compute CVar，并禁用不参与生产的 `EditorToolset`。

wrapper 在启动前要求可见 NVIDIA H200 和 580+ 驱动，固定 NVIDIA Vulkan ICD、工作区 DDC、运行时库与临时目录，并把 Python Remote Execution 的 UE/客户端两端都绑定为 Linux 可用的 `0.0.0.0`、TTL 1；项目 Remote Execution 可达后才调用 `run_first_batch_render_jobs.py`。完整启动命令、Editor/项目哈希、GPU UUID/驱动和环境记录在 `<run_root>/runtime/server_editor/`；profile 同时进入输入锁、Run Manifest 和 Sidecar，参数变化不能静默复用旧媒体。

以下是历史生产controller配方；其中engine-root截至2026-10-23不可用，须先恢复/验证实际构建，不能直接执行。生产操作使用 production controller；它先要求一个 UE 连续处理并审计 50 个节点，通过后按同一批量完成剩余节点，失败 invocation 最多自动重启一次：

```bash
python 00_engine/scripts/unreal/run_first_batch_server_production.py \
  --run-root 00_engine/outputs/unreal_render/first_batch_server_production_<run_id> \
  --delivery-root 00_engine/outputs/delivery/<release_id>/dataset_v1 \
  --batch-size 50 \
  --max-invocations-per-batch 2 \
  --engine-root /scratch/prj0000000275/jcy/sx/UnrealEngine \
  --uproject 00_engine/projects/datatry_02/datatry_02.uproject \
  --confirm-full-run
```

controller 固定当前已验证的 `batch-size=50`，底层 supervisor 仍拒绝 `batch-size=1`；全量必须显式传入 `--confirm-full-run`。Slurm wrapper 还强制显式设置 `DM_PRODUCTION_RUN_ROOT` 和 `DM_DELIVERY_ROOT`，不得默认复用或覆盖已冻结候选。每个 invocation 的 PID、命令、退出与关闭方式保存在 append-only session 中；同主机死 PID Lease 自动归档，遗留 attempt 标记为 `interrupted`。若兼容参数造成像素语义变化，须升级 Render Profile、输入锁和新 Run Root，旧媒体不能复用。

### 1.3 最小像素诊断 Harness

以下文件属于 `experimental` 诊断实现，由本文档所有，不是生产 Render Job 入口：

- `00_engine/projects/UE58VulkanCubeSmoke/Scripts/create_cube_smoke_map.py`
- `00_engine/projects/UE58VulkanCubeSmoke/Scripts/run_cube_smoke.sh`
- `00_engine/scripts/unreal/patches/ue58_vulkan_compatibility/0001-vulkan-typed-buffer-clear-channel-count.patch`

Runner 将环境取证、NullRHI 地图生成、Cook/Package 和像素渲染分成独立阶段，并为每次探针保存准确命令、UE 日志、退出码、配置快照和逐秒 GPU CSV。`PACKAGE_ROOT` 可在新 Run Root 中复用已有 package；超时直接约束 `UnrealGame`，GPU monitor 使用有界清理。`RENDER_PSO_PRECACHING` 和 `RENDER_VULKAN_FORCE_PSO_SINGLE_THREADED` 用于隔离 PSO 冷启动问题，`UE_HOME` 可指向显式缓存根。成功条件是进程 exit 0、目标 PNG 非空且人工确认非黑，不能只看 GPU utilization、文件存在或地图加载成功。

```bash
export RUN_ROOT="$PWD/00_engine/outputs/server_preflight/ue58_vulkan_cube_smoke/job${SLURM_JOB_ID}_manual"
bash 00_engine/projects/UE58VulkanCubeSmoke/Scripts/run_cube_smoke.sh environment
bash 00_engine/projects/UE58VulkanCubeSmoke/Scripts/run_cube_smoke.sh prepare
bash 00_engine/projects/UE58VulkanCubeSmoke/Scripts/run_cube_smoke.sh package
bash 00_engine/projects/UE58VulkanCubeSmoke/Scripts/run_cube_smoke.sh render
```

2026-08-28 至 2026-08-29 的 565/580 诊断 Run ID、结果和结论仍由本页与 [服务器 Vulkan 阻塞报告](../../project_management/history/reports/REPORT-2026-08-28-UE58-SERVER-VULKAN-BLOCKER.md) 追溯。原始 `server_preflight/` 输出已在第一批完成后清理；最终生产二进制 SHA、启动命令和 H200/580 profile 保存在当前候选的 `release_evidence/render_run/profile.json`，八个源码补丁保存在 `00_engine/scripts/unreal/patches/ue58_vulkan_compatibility/`。诊断结论不能替代正式 MRQ/MRG 或 10 节点基准。

历史 `%OUTPUT_ROOT%/mvp/` 已在 2026-08-30 清理，不是当前输出入口。

Slurm 交互分配内的诊断/渲染命令必须显式复用 allocation 并使用全部获配 CPU：

```bash
srun --jobid=<job_id> --overlap --nodes=1 --ntasks=1 \
  --cpus-per-task=14 --cpu-bind=verbose,cores <command>
```

SSH 会话可能先于 allocation 到期时，当前集群使用 detached `screen` 托管 `srun` 客户端；`srun` 的 stdout/stderr、controller status 和每次 UE session 均落入 Run Root。`screen` 只负责保持当前 job step，不申请新 allocation。当前 allocation 到期后必须停止，不能自动切换节点；新节点由用户提供后，对同一 Run Root 原样重跑，输入锁与 Sidecar/SHA-256 只补未接受节点。当前 job body 为 `00_engine/scripts/unreal/run_first_batch_server_production_slurm.sh`，示例：

```bash
screen -L -Logfile <run_root>/runtime/production_controller/screen.log \
  -dmS datamake_prod \
  srun --jobid=<job_id> --overlap --nodes=1 --ntasks=1 \
  --cpus-per-task=14 --cpu-bind=verbose,cores \
  --chdir=<repo_root> --input=none \
  --output=<run_root>/runtime/production_controller/slurm_stdout.log \
  --error=<run_root>/runtime/production_controller/slurm_stderr.log \
  bash <repo_root>/00_engine/scripts/unreal/run_first_batch_server_production_slurm.sh
```

## 2. 预检入口

命令从服务器repo根执行；先把UE_EDITOR占位替换为已核实构建的路径，并使用新REPORT_ROOT。脚本未指定UE_EDITOR时会默认工作区Installed Build；该默认值不表示它已通过历史生产Gate。

唯一权威脚本：`20_planning/implementation/FIRST_BATCH_SERVER_PREFLIGHT.sh`。该版本已针对当前 Slurm 集群、用户级 UE 运行库和无 `vulkaninfo` 时的 UE Vulkan 日志取证进行验证；项目启动使用 `QUIT_EDITOR`，并通过 TERM 加 15 秒 KILL 上限保证 timeout 后不会留下无界 UE 进程。

环境预检：

```bash
UE_EDITOR="/absolute/path/to/verified/Engine/Binaries/Linux/UnrealEditor" \
bash 20_planning/implementation/FIRST_BATCH_SERVER_PREFLIGHT.sh --environment-only
```

完整预检：

```bash
UE_EDITOR="/absolute/path/to/verified/Engine/Binaries/Linux/UnrealEditor" \
UPROJECT="$PWD/00_engine/projects/datatry_02/datatry_02.uproject" \
REPORT_ROOT="$PWD/00_engine/outputs/server_preflight/<new_run_id>" \
bash 20_planning/implementation/FIRST_BATCH_SERVER_PREFLIGHT.sh
```

脚本检查 Linux/GPU/Vulkan/UE、磁盘、项目、插件和两次离屏启动。Windows 绝对路径扫描要求盘符前不是字母数字或下划线，避免把 URL 片段误判为盘符。`SVR-02A` 对 UE 5.8 强制 NVIDIA 570+；低于该版本时返回失败并禁止项目 Smoke。环境模式返回码 2 表示只完成环境部分且没有硬失败，不是完整通过。2026-08-28 的 `job117593_datatry02_preflight_v05` 完整预检结果为 `PASS_WITH_WARNINGS`，两次启动均 exit 0；该结果不包含内容完整性和正式节点像素验收。

## 3. 项目同步与输入锁

上传前构建不可变输入清单，至少包含：

- `.uproject`、`Config`、本批 `Content/DataMake` 和被引用的 Vendor/Reallusion 资产；
- 服务器实际需要的项目插件及版本；
- 当前图、链、Render Jobs、Prompt Manifest、Render Profile 和执行代码；
- 每个上传文件的相对路径、字节数与 SHA-256；可迁移 JSON/JSONL 同时使用不受换行影响的规范化语义哈希；
- 本地与服务器路径映射、Git revision、UE 版本和批次 ID。

排除 `Saved`、`Intermediate`、本地 DDC、旧媒体和临时截图，除非某项被输入锁明确列入。可迁移配置出现 Windows 盘符时硬失败；路径必须转换为项目/数据集相对 URI 或 UE Object Path。

Reallusion Auto Setup 的 Win64 二进制通常只在导入期需要。Linux 是否移除插件必须由两次项目 Smoke 证明；不得因此删除已经生成的 `CC_Shaders` 或角色资产。

## 4. 服务器预检 Gate

按顺序检查：

1. Linux、NVIDIA 驱动、GPU、显存、Vulkan 和磁盘。
2. UE 精确版本、项目路径和大小写敏感引用。
3. 插件加载及两次无交互离屏启动；第一次允许 Shader 预热，第二次必须稳定。
4. `required_exports.json` 中全部 UE Object Path 可解析。
5. 场景、锚点、相机、Sequence、Look、动作、表情和 Render Profile 可加载。
6. 输出、临时和日志根可写，空间覆盖计划媒体、重试与打包。

任何失败都生成结构化 Preflight Report，并在 `WF-00/WF-80` Status 中登记；环境检查通过不等于项目 Gate 通过。

## 5. 10 节点基准

基准集合由当前 Render Jobs 中确定性选取，覆盖男女兼容域、10 个 Look、5 类动作和 near/far/high/side 四相机。先完成 Shader 预热，再对每个节点验证：

- 视频/帧存在且帧数、fps、分辨率、时长正确；
- 角色、服装、材质、动作和构图有效，无 T-pose/黑帧；
- GT、Sidecar、输入哈希、媒体哈希和状态完整；
- 启动开销、p50/p95 每帧时间、峰值显存、峰值 RAM 和单节点大小已记录。

2026-08-29 `first_batch_server_tokyo_benchmark10_20260829_v001` 已达到 10/10 accepted。首个 Editor 完成 7 个节点后在 F_ID02_O02 首次 DDC 预热后的 MRQ 启动阶段停顿；保留现场并重启 invocation 后，前 7 个媒体全部哈希复用，剩余 3 个完成。第三次同参数调用为 `rendered_count=0/reused_count=10`。该证据当时把边界冻结为 10；同日 `v003` 在预热 DDC 上由一个 UE invocation 连续完成 50 个节点并 graceful exit 0，资源批量边界更新为 50。视觉抽查随后发现 section 起点首帧错误，61 个媒体整体失效；不能把其 machine accepted 状态继续解释为媒体 Gate。修复证据为 `first_batch_server_first_frame_multiaction_preroll_20260829_v001`；正式 `v004` 随后以 13 个 invocation 完成 640/640 accepted，所有 invocation exit 0。该结果只证明 50 节点/Editor supervisor 策略，不允许外推成单 Editor 640。ETA 使用实测节点速度，不使用最佳样例。

最终生产入口会自行管理 UE Editor；从 `%LANCE_ROOT%` 对新 Run Root 执行：

```bash
python 00_engine/scripts/unreal/run_first_batch_server_render_batches.py \
  --run-root /data/runs/first_batch_benchmark_<run_id> \
  --start-index 1 \
  --limit 10 \
  --batch-size 10 \
  --uproject /data/datatry_02/datatry_02.uproject \
  --engine-root /opt/UnrealEngine-5.8
```

先用相同参数增加 `--dry-run` 检查选择集。首次 10 节点完成后，对同一 Run Root 原样重跑一次；第二次必须报告 `rendered_count=0`、`reused_count=10`。再执行 `--audit-existing`，要求 10/10 accepted。不要把本地 2 节点 Smoke 复制成服务器基准结果。

完整 640 节点只能在 10 节点基准接受后执行，并必须显式确认：

```bash
python 00_engine/scripts/unreal/run_first_batch_server_render_batches.py \
  --run-root /data/runs/first_batch_full_<run_id> \
  --start-index 1 \
  --limit 640 \
  --batch-size 50 \
  --max-invocations-per-batch 2 \
  --uproject /data/datatry_02/datatry_02.uproject \
  --engine-root /opt/UnrealEngine-5.8 \
  --confirm-full-run
```

上述 Linux 路径是服务器目标映射，不是已经验证的事实；实际路径必须由预检报告和输入清单冻结。

## 6. 批量执行状态机

- 调度只读取 `pending` 或 `retryable_failed` Render Job。
- 每个 `node_id` 使用独立 Lease，同一时间最多一个活动 attempt。
- 输出先写 attempt 临时目录，通过媒体与 Sidecar 验证后原子晋升到节点正式目录。
- attempt 记录机器、GPU、UE/Git/输入版本、开始/结束、退出码、日志与错误分类。
- 每个进程批次结束后检查 GPU 温度/显存、RAM、磁盘、失败率和速度漂移。
- 断点续跑只跳过已由当前输入哈希接受的节点，不能仅凭文件存在跳过。
- supervisor 不按视频重启 UE；正常重启只发生在 50 节点批次边界，异常重启只发生在失败 invocation。

## 7. 失败、恢复与重试

| 类型 | 状态 | 处理 |
| --- | --- | --- |
| 进程短暂退出、文件占用、瞬时 GPU 错误 | `retryable_failed` | 保持 Node Config 不变，在预算内增加 attempt |
| Shader/资产首次加载超时 | `retryable_failed` | 单独预热后重试，不计入稳定基准 |
| 资产缺失、大小写错误、插件不兼容 | `permanent_failed` | 停止受影响分组，修复输入并生成新输入版本 |
| 黑帧、空角色、错误镜头、系统性穿模 | `visual_failed` | 停止同类节点并诊断，不盲目跑完全量 |
| 同 `node_id` 出现不同媒体哈希 | `determinism_conflict` | 整批停止，审计配置、引擎和非确定性 |

重试不能修改任何像素或时序因素。若需要改变场景、相机、分辨率、动作、表达或渲染设置，必须升级 Render Profile/图源并生成新 `node_id`。

同主机 Lease 的 owner PID 已不存在时自动归档为 `orphaned`；恢复时原 `running` attempt 保留并改记 `interrupted`。每次 Editor 的 session/log 使用 `invocation_<NNN>` 追加保存。`editor_shutdown.method` 区分 `graceful`、超时 TERM 和超时 KILL，不能只根据最终媒体成功推断关闭过程正常。

## 8. 性能调整与版本化降级

优先调整并发、进程批次、缓存、Shader 预热和重试，不改变数据语义。分辨率、时长或其他像素/时序降级只能由当前 Plan 批准，并产生新 Render Profile、节点 ID 和基准；旧记录保留，不能覆盖。

## 9. 完成报告

服务器运行至少输出：

- 计划、成功、可重试失败和永久失败节点数；
- 媒体、GT、Sidecar 和哈希通过数；
- 实际总帧、总时长、总字节与节点复用率；
- p50/p95 速度、总墙钟时间、峰值资源和失败分类；
- 链与 Prompt 的零悬空媒体 URI 审计；
- 覆盖兼容域、相机、动作和 Look 的视觉抽检包。

## 10. 通过条件

H200/580 生产候选已满足两次启动、正式 Tokyo 像素、确定性、10 节点恢复和 640/640 accepted。`VAL-SERVER-01` 的生产路径记为 `passed_with_accepted_risk`：成功运行关闭了 Vulkan Validation layers，历史 Validation VUID 仍需最终 profile 补测。所有计划 Render Jobs 已进入 accepted 终态，`GATE-80` 已关闭；发布条件见 [Batch Status](../../project_management/status/batches/BATCH-001-FIRST-DATA.md) 和 [数据集封装](./DATASET_PACKAGE.md)。
