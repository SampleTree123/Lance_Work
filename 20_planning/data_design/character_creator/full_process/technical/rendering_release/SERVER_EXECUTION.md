# Linux/NVIDIA 服务器执行

> 文档 ID：`TECH-RENDER-02`
> 文档类型：`technical`
> 生命周期：`current`
> 适用阶段：`WF-00/WF-80`
> 实现所有权：服务器预检、项目同步、10 节点基准、并发和重试
> 验证所有权：`VAL-SERVER-01`
> 输出契约：`OUT-WF00-SESSION`、`OUT-WF80-NODE-MEDIA`
> 运行环境：Linux、NVIDIA、Vulkan、Unreal Engine 5.8
> 最近核验：2026-09-30（历史失败与用户确认的服务器完成分开；未重验服务器）

## 1. 当前状态

预检脚本和正式 Render Job 执行器均已存在；执行器已通过本地 2 节点真渲染与恢复。2026-08-28 的 `H64Y574/job117396` H200/565.57.01 环境曾无法完成最小 Vulkan 像素输出；该精确范围的失败保留为历史。用户于 2026-09-22 已确认服务器正式渲染完成，当前成功运行的环境、预检/基准、Run Root、Manifest 和 QA 尚未同步，本地 `VAL-SERVER-01` 保持证据待闭合，准确结果见 [WF-80 状态](../../project_management/status/workflows/WF-80.md)。服务器不能仅凭 Git 仓库生产：还需要 Batch Status 与 `required_exports.json` 指定的 UE 项目和二进制资产。

### 1.1 历史失败环境证据

2026-08-28 核验范围：

| 项目 | 实际值 |
| --- | --- |
| Slurm | `job117396`，节点 `H64Y574`，1 张 H200，14 CPU |
| NVIDIA | 驱动 `565.57.01`，`nvidia-smi` 报告 CUDA 12.7 |
| UE | `%LANCE_ROOT%/00_engine/unreal/UE_5.8` |
| 项目 | `%LANCE_ROOT%/00_engine/projects/datatry_02/datatry_02.uproject` |
| 失败证据 | [服务器 Vulkan 阻塞报告](../../project_management/history/reports/REPORT-2026-08-28-UE58-SERVER-VULKAN-BLOCKER.md)；原始 Manifest 位于 `%OUTPUT_ROOT%/server_preflight/` |

已排除的上层原因：

- 最小无光照地图在 SM5 和 ES3.1 下均能加载，MRQ 能推进到 Camera Cut 完成，但没有 PNG。
- 关闭 RHI 线程、改成单线程、预创建输出目录和禁用高阶渲染特性均无效。
- 仅含 10 KB 地图的 packaged runtime 在 `HighResShot` 处同样阻塞；多线程版本 60 秒后报告 RenderThread timeout，单线程版本 180 秒仍无图。因此主因不在 MRQ、Editor 插件或正式执行器。
- Vulkan Validation 报告图像布局错误 `VUID-vkCmdDispatch-imageLayout-00344`；Lavapipe 软件 Vulkan 在 Editor 和最小 packaged runtime 中均以同一 libc `0x4251f` 空指针 SIGSEGV 退出，不能作为生产降级。
- 诊断前后源地图 SHA-256 均为 `e45167092fb3d213b68481803daa14a0bcacdeef7a31e9a9ff2f7a1ed118e987`，原始关卡未被修改。

Epic 的 [UE 5.8 Linux Development Requirements](https://dev.epicgames.com/documentation/unreal-engine/linux-development-requirements-for-unreal-engine?lang=en-US) 在 2026-08-28 取证日期要求 NVIDIA 570 或更高版本。当时 565.57.01 低于该边界；此处只记录历史要求，不构成 2026-09-30 的外部规格重新核验。若重新使用该旧失败环境，恢复顺序为：

1. 首选切换到满足 UE 5.8 要求的 NVIDIA 驱动节点或镜像。
2. 若集群驱动不能变化，只能建立独立的旧版 UE 兼容分支并重新验证项目/资产兼容性；不能把 UE 5.8 项目直接降级覆盖。
3. 任一候选环境先产出并验证三帧最小无光照图像，再执行项目 Smoke；在此之前不得运行 10 节点基准或正式节点。

Slurm 交互分配内的诊断/渲染命令必须显式复用 allocation 并使用全部获配 CPU：

```bash
srun --jobid=<job_id> --overlap --nodes=1 --ntasks=1 \
  --cpus-per-task=14 --cpu-bind=verbose,cores <command>
```

## 2. 预检入口

唯一权威脚本：`20_planning/implementation/FIRST_BATCH_SERVER_PREFLIGHT.sh`。该版本曾针对报告中的 Slurm 环境、用户级 UE 运行库和无 `vulkaninfo` 时的 UE Vulkan 日志取证验证；换环境时须重新核对实际版本与脚本门槛，本次未改代码或重新执行服务器预检。

环境预检：

```bash
UE_EDITOR=/opt/UnrealEngine-5.8/Engine/Binaries/Linux/UnrealEditor \
bash 20_planning/implementation/FIRST_BATCH_SERVER_PREFLIGHT.sh --environment-only
```

完整预检：

```bash
UE_EDITOR=/opt/UnrealEngine-5.8/Engine/Binaries/Linux/UnrealEditor \
UPROJECT=/data/datatry_02/datatry_02.uproject \
REPORT_ROOT=/data/reports/first_batch_preflight_001 \
bash 20_planning/implementation/FIRST_BATCH_SERVER_PREFLIGHT.sh
```

脚本检查 Linux/GPU/Vulkan/UE、磁盘、项目、插件和两次离屏启动。`SVR-02A` 对 UE 5.8 强制 NVIDIA 570+；低于该版本时返回失败并禁止项目 Smoke。环境模式返回码 2 表示只完成环境部分且没有硬失败，不是完整通过。

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

基准集合由当前 Render Jobs 中确定性选取，覆盖全部兼容域、代表 Look、全部生产相机、Root Motion/InPlace 和活动表情。先完成 Shader 预热，再对每个节点验证：

- 视频/帧存在且帧数、fps、分辨率、时长正确；
- 角色、服装、材质、动作和构图有效，无 T-pose/黑帧；
- GT、Sidecar、输入哈希、媒体哈希和状态完整；
- 启动开销、p50/p95 每帧时间、峰值显存、峰值 RAM 和单节点大小已记录。

ETA 使用 p95，不使用最佳样例。10/10 accepted 后才冻结并发、每进程节点数和重试预算。

在服务器 UE Editor 已打开目标项目、Remote Execution 可达且 Shader 预热完成后，从 `%LANCE_ROOT%` 对一个新的、不可原地复用的 Run Root 执行：

```bash
python 00_engine/scripts/unreal/run_first_batch_render_jobs.py \
  --graph-root 00_engine/outputs/first_batch_dataset/graph_20260824_v1 \
  --run-root /data/runs/first_batch_benchmark_<run_id> \
  --uproject /data/datatry_02/datatry_02.uproject \
  --project-name datatry_02 \
  --engine-root /opt/UnrealEngine-5.8 \
  --start-index 1 \
  --limit 10
```

先用相同参数增加 `--dry-run` 检查选择集。首次 10 节点完成后，对同一 Run Root 原样重跑一次；第二次必须报告 `rendered_count=0`、`reused_count=10`。再执行 `--audit-existing`，要求 10/10 accepted。不要把本地 2 节点 Smoke 复制成服务器基准结果。

完整 640 节点只能在 10 节点基准接受后执行，并必须显式确认：

```bash
python 00_engine/scripts/unreal/run_first_batch_render_jobs.py \
  --graph-root 00_engine/outputs/first_batch_dataset/graph_20260824_v1 \
  --run-root /data/runs/first_batch_full_<run_id> \
  --uproject /data/datatry_02/datatry_02.uproject \
  --project-name datatry_02 \
  --engine-root /opt/UnrealEngine-5.8 \
  --confirm-full-run \
  --continue-on-error
```

上述 Linux 路径是服务器目标映射，不是已经验证的事实；实际路径必须由预检报告和输入清单冻结。

## 6. 批量执行状态机

- 调度只读取 `pending` 或 `retryable_failed` Render Job。
- 每个 `node_id` 使用独立 Lease，同一时间最多一个活动 attempt。
- 输出先写 attempt 临时目录，通过媒体与 Sidecar 验证后原子晋升到节点正式目录。
- attempt 记录机器、GPU、UE/Git/输入版本、开始/结束、退出码、日志与错误分类。
- 每个进程批次结束后检查 GPU 温度/显存、RAM、磁盘、失败率和速度漂移。
- 断点续跑只跳过已由当前输入哈希接受的节点，不能仅凭文件存在跳过。

## 7. 失败、恢复与重试

| 类型 | 状态 | 处理 |
| --- | --- | --- |
| 进程短暂退出、文件占用、瞬时 GPU 错误 | `retryable_failed` | 保持 Node Config 不变，在预算内增加 attempt |
| Shader/资产首次加载超时 | `retryable_failed` | 单独预热后重试，不计入稳定基准 |
| 资产缺失、大小写错误、插件不兼容 | `permanent_failed` | 停止受影响分组，修复输入并生成新输入版本 |
| 黑帧、空角色、错误镜头、系统性穿模 | `visual_failed` | 停止同类节点并诊断，不盲目跑完全量 |
| 同 `node_id` 出现不同媒体哈希 | `determinism_conflict` | 整批停止，审计配置、引擎和非确定性 |

重试不能修改任何像素或时序因素。若需要改变场景、相机、分辨率、动作、表达或渲染设置，必须升级 Render Profile/图源并生成新 `node_id`。

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

完整预检通过、两次启动稳定、10 节点 10/10 accepted、正式执行器可按 Node 续跑/重试且不改配置，所有计划 Render Jobs 进入可解释终态。批次精确数量与最终发布条件见 [Batch Status](../../project_management/status/batches/BATCH-001-FIRST-DATA.md) 和 [数据集封装](./DATASET_PACKAGE.md)。
## 2026-10-23 v11数据集本地准备交接

当前v11使用新的参数化入口，本地12真实节点完成，未连接服务器或上传。运行命令及分片见[OPERATIONS](../../../../../../00_engine/outputs/dataset_render_pilot_20261023_v1/OPERATIONS.md)；路径、Linux UE5.8.1与RLPlugin范围见[PORTABILITY](../../../../../../00_engine/outputs/dataset_render_pilot_20261023_v1/PORTABILITY.md)；传输文件清单见[TRANSFER_PLAN](../../../../../../00_engine/outputs/dataset_render_pilot_20261023_v1/TRANSFER_PLAN.md)。先把工程／脚本／数据配置迁移到独立服务器运行根，再做同任务小样；不要复制本机资源profile后绕过机器名检查，不要把历史服务器运行结论替代本批验证。多GPU按独立UE进程与整场景清单分配，显式确认Vulkan设备；本次未决定服务器并发数。
