# UE 5.8 服务器 Vulkan 像素渲染阻塞报告

> 文档 ID：`REPORT-2026-08-28-UE58-SERVER-VULKAN-BLOCKER`
> 文档类型：`history_report`
> 生命周期：`completed`
> 报告日期：2026-08-28
> 影响范围：`WF-00/WF-80`、`PLAN-2026-08-FIRST-DATA-BATCH/R08`
> 原始证据：`%OUTPUT_ROOT%/server_preflight/job117396_ue58_vulkan_pixel_smoke_manifest_20260828.json`
> 最近核验：2026-08-28

## 结论

`H64Y574/job117396` 上的 UE 5.8 可以启动、加载 `datatry_02`、Cook 和 Package，但 NVIDIA H200/565.57.01 环境无法完成最小 Vulkan 像素输出。MRQ 与不含项目插件依赖的最小 packaged runtime 均没有生成 PNG/JPG/EXR，因此问题不属于正式 Render Job 执行器、MRQ 配置或 Editor 插件层。

当前作用域的 `VAL-SERVER-01` 结果为 `failed`。不得在此环境启动 10 节点基准或正式 640 节点生产。

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

## 恢复条件

1. 首选使用满足 UE 5.8 要求的 NVIDIA 驱动节点或镜像。
2. 若集群驱动不能变化，建立独立旧版 UE 兼容分支；先验证项目和资产迁移，不覆盖当前 UE 5.8 项目。
3. 候选环境必须先生成并验证三帧最小无光照图像，再运行项目 Smoke。
4. 三帧 Smoke 通过前，不运行 10 节点基准或正式节点。

## 防回归改进

诊断完成后，`20_planning/implementation/FIRST_BATCH_SERVER_PREFLIGHT.sh` 增加 `SVR-02A`：当 `EXPECTED_UE_VERSION` 为 5.8 时，NVIDIA 驱动主版本低于 570 会硬失败，并阻止项目 Smoke。实际在同一 `job117396` 运行 environment-only 集成检查后得到：

```text
[SVR-02A] FAIL UE 5.8 requires NVIDIA driver 570+; found 565.57.01.
Final verdict: FAIL
```

该检查的原始结构化报告位于 `%OUTPUT_ROOT%/server_preflight/job117396_driver_gate_20260828_24/`。旧版 UE 分支不会继承 UE 5.8 的固定门槛，但会保留警告并要求独立兼容性验收。

本报告是一次失败诊断快照，不关闭计划需求、不构成里程碑，也不改变本地执行器已经通过的 Gate。
