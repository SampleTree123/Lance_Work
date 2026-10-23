# Render Job 与本地渲染执行

> 文档 ID：`TECH-RENDER-01`
> 文档类型：`technical`
> 生命周期：`current`
> 适用阶段：`WF-80`
> 实现所有权：正式 Render Job 执行器、UE 舞台、MRQ、节点状态、恢复与本地 Smoke
> 验证所有权：`VAL-RENDER-01`
> 输出契约：`OUT-WF80-NODE-MEDIA`
> 运行环境：系统 Python、UE 5.8 Editor/MRQ
> 最近核验：2026-09-30（状态对齐；未重验服务器或执行器）

## 1. 当前能力边界

正式生产入口是 `00_engine/scripts/unreal/run_first_batch_render_jobs.py`。它逐条读取冻结的 `render_jobs.jsonl`，把节点配置映射到已验证的 UE Sequence/MRQ 管线，并负责输入锁、Lease、attempt、Sidecar、媒体哈希、原子晋升与断点续跑。

`run_first_batch_render_matrix.py` 仍是底层矩阵/代表样例执行能力，也是正式执行器调用的 UE 舞台与 MRQ 实现；它不单独拥有正式节点状态。当前已经通过 2 个真实节点的本地正式执行器 Smoke 和同一 Run Root 的零重渲染恢复测试。用户于 2026-09-22 确认服务器正式渲染完成；成功运行的预检/基准、正式媒体 Manifest 与 QA 尚未同步到本地，准确证据边界见 [WF-80 状态](../../project_management/status/workflows/WF-80.md)。旧像素失败只代表当时精确环境，不能作为当前阻塞。

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
4. 获取 `leases/<node_id>.lock`，过期 Lease 会归档而不是静默覆盖；
5. 创建节点 attempt 状态和 JSONL 日志，设置 Look、Composite、Camera 与 150 帧 Sequence；
6. 在 `staging/render/<node_id>/<attempt>/` 调用 MRQ，验证规格、Pose Driver 和时间变化；
7. 生成包含 GT、实际 UE 绑定、媒体、attempt、QA 与运行环境的 Sidecar；
8. 校验复制哈希后原子晋升到 `media/nodes/<node_id>/`；
9. 重建媒体 Manifest 和 Run 状态。失败分类为 `retryable_failed` 或 `permanent_failed`。

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
```

- `manifest.json` 描述整批 640 节点目标；小批调用完成时，Run Root 仍可合理保持 `running/partial`。
- `result.json` 描述最近一次调用；本次选择节点全部 accepted 时为 `passed`。
- `state/nodes/` 与 attempt 日志保存首次渲染和失败历史；`result.json` 的后续恢复结果不会抹掉这些证据。
- `media_manifest.*` 只登记当前哈希有效的 accepted 媒体。
- accepted 媒体和 Sidecar 是同一节点目录中的不可分割单元。

最终正式媒体与 Manifest 通过完整 Gate 后为 `authoritative`；本地 Smoke 为 `retained_evidence`；失败 attempt 中间帧通常为 `disposable`，但未解决事故期间不得清理。

## 5. 本地正式执行器验收

当前接受证据：

```text
%OUTPUT_ROOT%/unreal_render/first_batch_formal_executor_smoke_20260825_v003/
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

同一实验的早期目录只保留为清理治理对象，不是当前证据：

```text
unreal_render/first_batch_formal_executor_smoke_20260825_v001  -> disposable
unreal_render/first_batch_formal_executor_smoke_20260825_v002  -> superseded by v003
```

`v001` 在 attempt 目录所有权缺陷修复前终止且没有 accepted 媒体；`v002` 已由包含可迁移传递输入锁和最终恢复行为的 `v003` 完整取代。分类不等于自动删除许可，清理仍需按 Output 治理单独审批。

其余保留证据：

```text
%OUTPUT_ROOT%/unreal_render/first_batch_32look_matrix_20260824_v002/
%OUTPUT_ROOT%/unreal_render/first_batch_chain_visual_smoke_20260824_v1/
%OUTPUT_ROOT%/unreal_character_import/first_batch_render_audit_20260824_v1/
```

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
| `build_first_batch_chain_render_matrix_v1.py` | 把代表链节点编译为诊断用本地 Render Matrix |
| `run_first_batch_render_matrix.py` | Look/Sequence/MRQ 底层编排与媒体 QA |
| `run_first_batch_32_video_matrix.ps1` | 本地 32-Look 矩阵 Python 入口的 PowerShell 薄包装 |
| `run_first_batch_render_profile.py` / `ue_build_first_batch_render_profile.py` | 构建冻结 MRQ Profile |
| `ue_stage_first_batch_render_look.py` | 在 staging 关卡切换 Look、Composite 与 Camera |
| `run_first_batch_local_sample_render.py` / `ue_start_first_batch_local_sample_render.py` | 启动单个 150 帧 MRQ attempt |
| `ue_audit_first_batch_render_assets.py` | 只读审计 Look、Skeleton、Composite、相机和渲染依赖 |
| `validate_first_batch_chain_visual_smoke_v1.py` | 验证代表链媒体和视觉 Smoke 证据 |

## 7. 资源与恢复

UE 长批次内存可能持续增长。以可恢复的小批次执行，批间记录状态并按观测结果重启 UE；不要假设一个 Editor 进程稳定完成全部节点。磁盘不足、对象路径失效、同 Node 配置冲突和视觉系统性错误必须停止同类批次。服务器的预检、10 节点基准和启动方式见 [服务器执行](./SERVER_EXECUTION.md)。
