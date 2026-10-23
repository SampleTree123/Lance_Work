# Render Job 与本地渲染执行

> 文档 ID：`TECH-RENDER-01`
> 文档类型：`technical`
> 生命周期：`current`
> 适用阶段：`WF-80`
> 实现所有权：正式 Render Job 执行器、UE 舞台、MRQ、节点状态、恢复与本地 Smoke
> 验证所有权：`VAL-RENDER-01`
> 输出契约：`OUT-WF80-NODE-MEDIA`
> 运行环境：系统 Python、UE 5.8 Editor/MRQ
> 最近核验：2026-08-29

## 1. 当前能力边界

正式生产入口是 `00_engine/scripts/unreal/run_first_batch_render_jobs.py`。它逐条读取冻结的 `render_jobs.jsonl`，把节点配置映射到已验证的 UE Sequence/MRQ 管线，并负责输入锁、Lease、attempt、Sidecar、媒体哈希、原子晋升与断点续跑。

`run_first_batch_render_matrix.py` 仍是底层矩阵/代表样例执行能力，也是正式执行器调用的 UE 舞台与 MRQ 实现；它不单独拥有正式节点状态。H200/580 已完成正式 Tokyo 样例链、独立确定性复验、10 节点基准及中断恢复。`v003` 在 61 个媒体时因动画 section 起点首帧错误整体失效；section-0/evaluation-preroll 修复先由同一 UE PID 6/6 高风险节点验证，随后正式 `v004` 由 `run_first_batch_server_production.py` 和 `run_first_batch_server_render_batches.py` 按 50 节点批次完成 640/640 accepted。13 个 Editor invocation 均 exit 0，累计媒体、Sidecar、哈希、规格、首帧、Pose Driver 和时间运动审计通过。准确状态见 [服务器执行](./SERVER_EXECUTION.md)。

## 2. 正式输入与入口

默认冻结输入：

```text
00_engine/outputs/first_batch_dataset/graph_20260824_v1/
  source_manifest.json
  nodes.jsonl
  render_jobs.jsonl
  required_exports.json
```

只检查完整 640 作业契约，不连接 UE：

```powershell
python .\00_engine\scripts\unreal\run_first_batch_render_jobs.py `
  --run-root .\00_engine\outputs\unreal_render\first_batch_formal_run_<run_id> `
  --dry-run `
  --confirm-full-run
```

渲染确定性小批次；UE Editor 必须已经打开目标项目并启用 Remote Execution：

```powershell
python .\00_engine\scripts\unreal\run_first_batch_render_jobs.py `
  --run-root .\00_engine\outputs\unreal_render\first_batch_formal_run_<run_id> `
  --uproject D:\UE\projects\datatry_02\datatry_02.uproject `
  --project-name datatry_02 `
  --engine-root D:\UE\UE_5.8 `
  --start-index 1 `
  --limit 10
```

对同一个 Run Root 重复相同命令会验证 Sidecar、配置哈希、媒体字节数和 SHA-256；有效节点记为 `reused`，不会调用 UE 重渲染。只审计已有节点：

Linux/H200 服务器不要求操作员手动拼接 Editor 与正式执行器命令。`run_first_batch_server_render_jobs.py` 负责一次长驻无头 Editor invocation；`run_first_batch_server_render_batches.py` 按已验证的 50 节点批次调用它，并在失败时按预算重启 invocation。`run_first_batch_server_production.py` 所有权覆盖 50 节点 Gate、640 节点累计审计和发布封装，Slurm job body 为 `run_first_batch_server_production_slurm.sh`。服务器启动 profile 会作为 `runtime-profile://<profile_id>` 进入输入锁，并写入 Run Manifest 和节点 Sidecar；调度器 job ID 只保存在 session 证据中，不属于像素输入指纹。冻结生产 profile 为 `h200_vulkan_sm6_580_tokyo_v1`；它已在 H200、NVIDIA 580.126.20、Tokyo 第一批 640 节点范围通过，但不能外推到其他驱动、GPU、场景或项目版本。

```powershell
python .\00_engine\scripts\unreal\run_first_batch_render_jobs.py `
  --run-root .\00_engine\outputs\unreal_render\first_batch_formal_run_<run_id> `
  --start-index 1 `
  --limit 10 `
  --audit-existing
```

执行全部 640 个节点必须显式增加 `--confirm-full-run`。可用 `--node-id` 精确选择节点；`--continue-on-error` 允许同一调用继续处理其他节点，但不会把失败节点静默当作完成。

## 3. 节点执行顺序

每个选中节点按以下顺序执行：

1. 校验冻结 source manifest、640 Node/Job 一一对应、节点配置 SHA、Look/Action/Camera 和 Happy 表情约束；
2. 校验或创建 `inputs.lock.json`，锁定图源、项目、执行器和传递调用脚本；JSON/JSONL 使用规范化语义哈希，文本脚本统一为 LF 后哈希，二进制媒体仍使用原始字节 SHA-256；已验收的 v1 图源未声明 `hash_mode` 时，执行器仅对其文本哈希兼容 LF/CRLF；
3. 验证已有 accepted 输出；哈希完整则直接复用；
4. 获取 `leases/<node_id>.lock`；超龄 Lease 或同主机已退出 PID 的 orphan Lease 会分别归档为 `stale`/`orphaned`，不会静默覆盖；
5. 创建节点 attempt 状态和 JSONL 日志，设置 Look、Composite、Camera 与 150 帧 Sequence；
6. 在 `staging/render/<node_id>/<attempt>/` 调用 MRQ，验证规格、Pose Driver 和时间变化；
7. 生成包含 GT、实际 UE 绑定、媒体、attempt、QA 与运行环境的 Sidecar；
8. 校验复制哈希后原子晋升到 `media/nodes/<node_id>/`；
9. 重建媒体 Manifest 和 Run 状态。进程中断遗留的 `running` attempt 在恢复时保留并改记为 `interrupted`；新 attempt 仍使用相同 Node Config。失败分类为 `retryable_failed` 或 `permanent_failed`。

同一节点重试不得改变 Node Config。需要修改像素、时序、场景、相机或资产绑定时，必须生成新 Render Profile/图源和新 Node ID。

## 4. Run Root 契约

```text
<run_root>/
  manifest.json
  inputs.lock.json
  status.json
  result.json
  media_manifest.json
  media_manifest.jsonl
  state/nodes/<node_id>.json
  logs/render/<node_id>/attempt_<NNN>.jsonl
  leases/
  staging/render/
  media/nodes/<node_id>/video.mp4
  media/nodes/<node_id>/sidecar.json
  runtime/server_editor/profile.json
  runtime/server_editor/sessions/invocation_<NNN>/session.json
  runtime/server_editor/supervisors/supervision_<NNN>.json
```

- `manifest.json` 描述整批 640 节点目标；小批调用完成时，Run Root 仍可合理保持 `running/partial`。
- `result.json` 描述最近一次调用；本次选择节点全部 accepted 时为 `passed`。
- `state/nodes/` 与 attempt 日志保存首次渲染和失败历史；`result.json` 的后续恢复结果不会抹掉这些证据。
- `media_manifest.*` 只登记当前哈希有效的 accepted 媒体。
- accepted 媒体和 Sidecar 是同一节点目录中的不可分割单元。

最终正式媒体与 Manifest 通过完整 Gate 后为 `authoritative`；本地 Smoke 为 `retained_evidence`；失败 attempt 中间帧通常为 `disposable`，但未解决事故期间不得清理。

## 5. 本地正式执行器验收

本地正式执行器验收结论已被 640 节点正式生产结果覆盖。2026-08-30 清理后，原始 Smoke 和正式 Run Root 均不再保留；当前紧凑证据为：

```text
%OUTPUT_ROOT%/delivery/first_batch_candidate_20260830_v002/release_evidence/render_run/
```

验收范围：

| 项目 | 结果 |
| --- | --- |
| 输入锁 | `c5547a1398e7b601003c90b69743ae96bd5aab6370e08457d7cbcaa80d88969d` |
| 节点 | 女 `n_09ec591c5362fe4c`；男 `n_51c2d9f2c76ca68b` |
| 媒体 | 2/2 accepted，2560×1440、30 FPS、150 帧、5 秒 |
| 首次执行 | 2 个 attempt 均为 `accepted`，生成 GT/Sidecar、媒体 SHA 和 Manifest |
| 恢复执行 | `rendered_count=0`、`reused_count=2`，未调用 UE 重渲染 |
| 机器 QA | Pose Driver 与时间变化检查通过 |
| 人工视觉 | 男女代表帧主体可见、构图正确、非 T-pose、无已知面部白块 |

该证据只接受“正式执行器本地小规模能力”，不关闭 `GATE-80`，也不代表服务器或 640 节点已完成。

`v001/v002/v003` 本地 Smoke、本地视觉矩阵、服务器预检、失败压力运行和正式 `v004` Run Root 的原始目录已由最终候选及紧凑证据替代并删除。历史结果继续由本节、状态和清理清单追溯，不再作为物理输出入口。

### 5.1 H200/580 正式执行证据

2026-08-29 的正式 Tokyo 证据使用 `h200_vulkan_sm6_580_tokyo_v1`：

下表中的 Run ID 是历史执行标识；其原始目录已清理。完整 640 节点结果、媒体 Manifest、输入锁和 profile 保存在当前候选的 `release_evidence/render_run/`。

| 证据 | 结果 |
| --- | --- |
| `first_batch_server_tokyo_chains_20260829_v002` | 同一 UE PID 连续渲染 6 个唯一节点，2 条样例编辑链共 8 个链位置；6/6 accepted，150 帧、1440p30，near/side/far 首帧与动作人工验收通过 |
| `first_batch_server_tokyo_supervisor_smoke_20260829_v001` + `first_batch_server_tokyo_final_determinism_repeat_20260829_v001` | 最终脚本/profile 哈希下同节点独立复验；逐帧 mean MAD `0.758020`、p95 `1.277066`、max `1.779514`，changed-pixel fraction `0.004009`，通过容差 Gate |
| `first_batch_server_tokyo_benchmark10_20260829_v001` | 10/10 accepted；首个 invocation 完成 7 节点后在新 Look 冷 DDC 阶段停顿，第二 invocation 复用 7 个并完成 3 个；第三次同参调用 `rendered=0/reused=10` |
| `first_batch_server_tokyo_supervisor_smoke_20260829_v001` | 最终 supervisor/launcher 哈希下，同一 UE PID 连续 2/2 accepted，side/high 首帧 MAD `3.379549/0.770365`，graceful exit 0 |
| `first_batch_server_production_20260829_v004` | 640/640 accepted；13 个 Editor invocation 按 50 节点边界执行，全部 exit 0；所有视频为 2560x1440、30 FPS、150 帧、5 秒，evaluation preroll/Pose Driver/时间运动和累计哈希审计通过 |

首帧错误不是输出编码且包含两个边界。第一层是复用 Render Workspace 曾保留上一 Camera Cut；Sequence 构建器现在每个节点先恢复四段规范范围，再仅激活目标相机并把它覆盖完整 `0..600` 工作区。第二层是 camera-index 对应的动画 section 起点第一次求值会先输出错误 source-time 姿态；因此正式节点不再按 camera section 的 `0/150/300/450` 起点渲染，而统一从 section 0 的 `0..149` 输出，并向 MRQ 请求帧 `-1` 作为 evaluation preroll。UE 5.8 会在 playback start 裁剪该帧、不把它写成 PNG，但会在交付帧 0 前完成 binding 求值。`evaluation_preroll.passed=true`、`temporal_motion.first_frame_to_second_mean_abs_difference <= 12` 和可见时间变化均为机器硬 Gate。旧 `v003` 不能复用；修复后的 6 节点首帧 MAD 为 `0.53..2.63`。

跨独立 Run Root 的确定性使用 `validate_first_batch_node_determinism.py`。默认通过阈值为逐帧 mean MAD `<=1.5`、p95 `<=2.0`、单帧 max MAD `<=3.0`、像素差大于 5 的比例 `<=1%`；两份 Sidecar 必须是同节点、同 GT、同媒体规格和完全相同的 Editor profile。

## 6. 底层本地矩阵入口

直接运行代表矩阵仍可用于诊断，不作为正式节点状态权威：

```powershell
python .\00_engine\scripts\unreal\run_first_batch_render_matrix.py `
  --config .\00_engine\scripts\unreal\first_batch_local_render_matrix_20260824_v1.json `
  --output-dir .\00_engine\outputs\unreal_render\first_batch_32look_matrix_20260824_v002
```

相关实现：

| 入口 | 作用 |
| --- | --- |
| `run_first_batch_render_jobs.py` | 正式 Render Job 调度、Run Root、恢复、Sidecar 和 Manifest |
| `run_first_batch_server_render_jobs.py` | 启动一个长驻 H200 Editor invocation，固定 profile 并归档独立 session/log |
| `run_first_batch_server_render_batches.py` | 按多节点批次调用长驻 Editor；失败 invocation 自动重启并复用 accepted 节点 |
| `run_first_batch_server_production.py` | 执行单 UE 50 节点 Gate、完整 640 节点、累计审计和 `dataset_v1` 封装 |
| `run_first_batch_server_production_slurm.sh` | 当前 H200 Slurm job body；固定 14 CPU、单 H200、50 节点批次和显式全量确认 |
| `build_first_batch_chain_render_matrix_v1.py` | 把代表链节点编译为诊断用本地 Render Matrix |
| `run_first_batch_render_matrix.py` | Look/Sequence/MRQ 底层编排与媒体 QA |
| `run_first_batch_32_video_matrix.ps1` | 本地 32-Look 矩阵 Python 入口的 PowerShell 薄包装 |
| `run_first_batch_render_profile.py` / `ue_build_first_batch_render_profile.py` | 构建冻结 MRQ Profile |
| `ue_stage_first_batch_render_look.py` | 在 staging 关卡切换 Look、Composite 与 Camera |
| `run_first_batch_local_sample_render.py` / `ue_start_first_batch_local_sample_render.py` | 启动单个 150 帧 MRQ attempt |
| `ue_audit_first_batch_render_assets.py` | 只读审计 Look、Skeleton、Composite、相机和渲染依赖 |
| `validate_first_batch_chain_visual_smoke_v1.py` | 验证代表链媒体和视觉 Smoke 证据 |
| `validate_first_batch_node_determinism.py` | 对同节点两份 accepted MP4 做 150 帧逐帧容差 Gate |

## 7. 资源与恢复

UE 长批次内存可能持续增长。`job117924/8GS9B74` 已将资源边界实测冻结为 `50 nodes / Editor invocation`：正式 `v004` 用 13 个 invocation 完成 640 个节点，每个完整批次最多 50 个节点，全部 exit 0；不得外推成一个 Editor 运行全部 640 节点，也不得退化为每视频重启。`v003` 运行在 25 节点时 UE RSS 约 23.8 GiB，40 节点时约 27.6 GiB，GPU 显存稳定在约 8.8–8.9 GiB，但 61 个媒体随后因首帧视觉缺陷失效，资源 Gate 不能替代媒体 Gate。修复后的正式 `v004` 首个 50 节点批次在 25 节点时 UE RSS 约 12.7 GiB、41 节点时约 15.6 GiB；全量累计审计最终通过。supervisor 在 50 节点边界正常重启，失败 invocation 最多重启 2 次；节点媒体仅在同一输入锁下按哈希复用。磁盘不足、对象路径失效、同 Node 配置冲突和视觉系统性错误必须停止同类批次。服务器的预检、基准和启动方式见 [服务器执行](./SERVER_EXECUTION.md)。
