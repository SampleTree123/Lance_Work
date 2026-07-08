# UE 5.8 无头批渲集群部署 + MVP 启动计划

> 目标：在当前 DataMake 工作目录内安装 UE 5.8，跑通 `UnrealEditor-Cmd` 无头渲染，并产出第一对 before/after 编辑配对。
> 状态：2026-07-07 更新。管理员确认不能使用 `/local`，本文件采用 DataMake 单目录方案；UE 下载入口和账号要求已按 Epic 官方文档复核；UE 5.8 Installed Build 已解压、完成用户态缺库处理，并在 H200 节点完成 GPU/Python smoke。

## 0. 当前路径决策

当前工作根目录：

```bash
cd /scratch/prj0000000275/jcy/xks/DataMake
export DATAMAKE_ROOT="$PWD"
```

固定布局：

```text
DataMake/
  00_engine/
    unreal/
      downloads/        # UE zip 临时下载；解压确认后删除
      UE_5.8/           # UE 解压目录
    runtime/
      downloads/        # 用户态 .deb 等运行库包；不进 Git
      ubuntu2204-libs/  # 解包后的本地运行库；不进 Git
    cache/
      ddc/              # DDC / shader cache
      tmp/              # 临时目录
      ue_home/          # 只给 UE 进程使用的 HOME，避免写真实 home
    projects/
      MVPProject/       # MVP UE 工程
    outputs/
      mvp/              # 少量验证输出
    logs/
```

2026-07-06 本地 `df -h .` 显示 `/scratch` 约 307G 可用；UE zip 下载完成后约 270G 可用；UE 解压后约 196G 可用。单个 UE 5.8 Installed Build + MVP 仍可做，但必须避免长期保留 UE zip、多个引擎版本或大量输出。注意这是 WekaFS/网络盘，小文件 I/O 可能慢；先控制规模完成 MVP，不在这里直接启动正式大规模生产。

当前下载状态（2026-07-06）：

```text
00_engine/unreal/downloads/Linux_Unreal_Engine_5.8.0.zip
size: 38G
check: unzip -tq passed
```

当前解压状态（2026-07-06）：

```text
00_engine/unreal/UE_5.8/
size: 73G
version: UE 5.8.0, changelist 55116800, branch ++UE5+Release-5.8
unzip log: 00_engine/logs/ue58_unzip_20260706_162420.log
```

登录节点 `ldd` 曾显示缺少运行库：

```text
libgbm.so.1 => not found
```

2026-07-07 已用无 sudo 方式处理：从 Ubuntu 22.04 `jammy/main` 下载 `libgbm1_22.0.1-1ubuntu2_amd64.deb`，解包到 `00_engine/runtime/ubuntu2204-libs/`，由 `00_engine/scripts/ue_env.sh` 注入 `LD_LIBRARY_PATH`。`ldd` 已无 `not found` 输出。

后续 UE 命令不要直接裸跑 `UnrealEditor-Cmd`，使用包装脚本：

```bash
00_engine/scripts/run_ue_cmd.sh <UE arguments>
```

该脚本会设置项目内 `HOME`、`TMPDIR`、`UE_LocalDataCachePath`、本地运行库路径，并默认追加 `-ddc=NoZenLocalFallback`，避免 UE 5.8 在集群环境里反复启动本地 Zen DDC 服务。

GPU 节点 smoke 结果（2026-07-07，Slurm job `99943`，node `8FS9B74`）：

```text
GPU: NVIDIA H200
driver: 565.57.01
CUDA_VISIBLE_DEVICES: 0
vulkaninfo: not installed on node
ldd UnrealEditor-Cmd: no "not found"
```

`vulkaninfo` 不是必需条件；该节点缺少该诊断命令，但 UE 日志已确认 Vulkan/H200 初始化：

```text
rhiname="Vulkan"
gpu="NVIDIA H200"
driverInfo: 565.57.01
Texture pool is 100639 MB (70% of 143771 MB)
```

注意：裸 `-version` 不是可靠的短生命周期 smoke；它能初始化 Vulkan，但退出/收尾可能卡住。曾尝试的 `-NoShaderCompile` 会触发 `AllowShaderCompiling()` 断言，不应作为 smoke 参数。当前稳定 smoke 入口是 `00_engine/scripts/run_mvp_python_smoke.sh`：

```text
nullrhi: status=0, DATAMAKE_UE_PYTHON_SMOKE_OK
renderoffscreen commandlet: status=0, DATAMAKE_UE_PYTHON_SMOKE_OK
```

`-run=pythonscript` commandlet 会短生命周期退出；它通常选择 Null RHI，因此不能替代真实渲染 smoke。真实渲染能力下一步用 MRQ/MRG 或 map/game render 验证。

补充实测（2026-07-07，同一 job `99943`）：`MVPProject -game -RenderOffscreen -ExecCmds="quit"` 可初始化真实 Vulkan/H200，但没有在 300 秒内稳定退出，已手动取消 step。不要把这条命令作为默认 smoke；后续真实像素渲染应走明确生命周期的 MRQ/MRG 或自定义 Python executor。

zip 现在已满足删除条件；删除 `00_engine/unreal/downloads/Linux_Unreal_Engine_5.8.0.zip` 可释放约 38G。执行删除前先向用户确认。

## 1. 安装路线

优先使用 **UE 5.8 Linux Installed Build zip**。2026-07-06 按 Epic 官方文档复核：

- Linux 支持预编译 Installed Build 和源码构建两条路线。
- Installed Build 下载入口是 `https://www.unrealengine.com/en-US/linux`，访问时需要 Epic Games account 登录。
- 下载预编译 Installed Build 不需要 GitHub。
- 只有源码路线 `https://github.com/EpicGames/UnrealEngine` 需要 Epic Games account + GitHub account 绑定，并接受 EpicGames 组织邀请。

选择 Installed Build 的原因：

- 无需 root。
- 无需源码编译。
- 自带 editor、Python 和 MoviePipeline 相关能力。
- 下载和解压体积以 Epic 页面实际文件为准；解压成功后删除 zip。

源码编译、容器、Apptainer 暂时都不是主路径。只有当 Installed Build 缺必要能力或依赖无法解决时再回头讨论。

## 2. 下载与解压

```bash
cd /scratch/prj0000000275/jcy/xks/DataMake
export DATAMAKE_ROOT="$PWD"
export UE_ROOT="$DATAMAKE_ROOT/00_engine/unreal/UE_5.8"
export UE_ZIP="$DATAMAKE_ROOT/00_engine/unreal/downloads/Linux_Unreal_Engine_5.8.0.zip"
export UE_LocalDataCachePath="$DATAMAKE_ROOT/00_engine/cache/ddc"
export TMPDIR="$DATAMAKE_ROOT/00_engine/cache/tmp"

mkdir -p "$DATAMAKE_ROOT/00_engine/unreal/downloads" \
         "$UE_ROOT" \
         "$UE_LocalDataCachePath" \
         "$TMPDIR" \
         "$DATAMAKE_ROOT/00_engine/projects" \
         "$DATAMAKE_ROOT/00_engine/outputs/mvp" \
         "$DATAMAKE_ROOT/00_engine/logs"
```

下载 UE zip 后放到：

```text
00_engine/unreal/downloads/Linux_Unreal_Engine_5.8.0.zip
```

解压：

```bash
unzip -q "$UE_ZIP" -d "$UE_ROOT"
chmod -R u+rwX "$UE_ROOT"
```

如果 `unzip` 对大文件失败，用 `bsdtar` 或 `7z`。

解压并通过 GPU/project smoke 验证后，删除 zip 节省空间：

```bash
rm "$UE_ZIP"
```

当前已完成解压、`libgbm.so.1` 用户态补库、H200 Vulkan 初始化验证和 MVPProject Python smoke。下一步进入 MVP 渲染脚本。

## 3. 启动前自检

每次换节点或环境变动后先跑：

```bash
cd /scratch/prj0000000275/jcy/xks/DataMake
export DATAMAKE_ROOT="$PWD"
export UE_ROOT="$DATAMAKE_ROOT/00_engine/unreal/UE_5.8"
export UE_LocalDataCachePath="$DATAMAKE_ROOT/00_engine/cache/ddc"
export TMPDIR="$DATAMAKE_ROOT/00_engine/cache/tmp"
export ENG="$UE_ROOT/Engine/Binaries/Linux/UnrealEditor-Cmd"
export UE_RUNTIME_LIB="$DATAMAKE_ROOT/00_engine/runtime/ubuntu2204-libs/usr/lib/x86_64-linux-gnu"
export LD_LIBRARY_PATH="$UE_RUNTIME_LIB:${LD_LIBRARY_PATH:-}"

df -h "$DATAMAKE_ROOT"
nvidia-smi
if command -v vulkaninfo >/dev/null 2>&1; then
  vulkaninfo --summary | grep -i deviceName
else
  echo "vulkaninfo not installed; use UE Vulkan log as fallback"
fi
ldd --version | head -n 1
uname -r
ldd "$ENG" | grep 'not found' || true
00_engine/scripts/run_mvp_python_smoke.sh nullrhi
```

期望：

- 如果 `vulkaninfo` 可用，应看到 NVIDIA H200，而不是 llvmpipe；如果不可用，用 UE 日志确认 `rhiname="Vulkan"` 和 `gpu="NVIDIA H200"`。
- `ldd "$ENG" | grep 'not found'` 没有缺库。
- `run_mvp_python_smoke.sh nullrhi` 能 `status=0` 并打印 `DATAMAKE_UE_PYTHON_SMOKE_OK`。

## 4. DDC 与临时目录

固定使用：

```bash
export UE_LocalDataCachePath="$DATAMAKE_ROOT/00_engine/cache/ddc"
export TMPDIR="$DATAMAKE_ROOT/00_engine/cache/tmp"
```

Linux 下变量名是 `UE_LocalDataCachePath`，不是 Windows 风格的 `UE-LocalDataCachePath`。

当前 DDC 在网络盘上，首次 shader/DDC 构建可能慢。MVP 阶段接受这个限制，避免频繁删除 `00_engine/cache/ddc/`。

## 5. MVP 工程位置

MVP UE 工程放在：

```text
00_engine/projects/MVPProject/
```

工程里的 `Saved/`、`Intermediate/`、`DerivedDataCache/`、`Binaries/` 已在 `.gitignore` 中排除。稳定后可以只把脚本、配置、少量源码和文档纳入 Git。

## 6. 无头渲染 smoke test

拿到 GPU 交互会话后：

```bash
salloc --gres=gpu:1 --time=02:00:00

cd /scratch/prj0000000275/jcy/xks/DataMake
export DATAMAKE_ROOT="$PWD"
export UE_ROOT="$DATAMAKE_ROOT/00_engine/unreal/UE_5.8"
export UE_LocalDataCachePath="$DATAMAKE_ROOT/00_engine/cache/ddc"
export TMPDIR="$DATAMAKE_ROOT/00_engine/cache/tmp"
export ENG="$UE_ROOT/Engine/Binaries/Linux/UnrealEditor-Cmd"

00_engine/scripts/run_mvp_python_smoke.sh nullrhi
00_engine/scripts/run_mvp_python_smoke.sh renderoffscreen
```

`renderoffscreen` 分支只验证参数路径和 commandlet 退出流程；真正的像素渲染 smoke 需要后续 map/game 或 MRQ/MRG 脚本。先用低分辨率和少量帧验证，确认日志里没有 llvmpipe/CPU fallback，再提高设置。

## 6.1 UE MCP / Codex agent 配置

2026-07-07 已按 Linux 服务器环境配置 UE 5.8 官方 MCP：

- `MVPProject.uproject` 启用 `ModelContextProtocol`、`Terminal`、`EditorToolset`。
- `DefaultEditorPerProjectUserSettings.ini` 设置 `bAutoStartServer=True`、`ServerPortNumber=8000`、`ServerUrlPath=/mcp`。
- DataMake 根目录 `.codex/config.toml` 是 Codex canonical MCP 配置；UE 自动生成的 `MVPProject/.codex/config.toml` 保留为 client config 产物。
- Terminal startup commands 改为 Linux shell 形式：

```text
export TERM=xterm-256color
cd "/scratch/prj0000000275/jcy/xks/DataMake"
codex
```

生成 client config：

```bash
00_engine/scripts/run_mcp_generate_client_config.sh
```

该脚本短生命周期运行，生成/刷新：

```text
00_engine/projects/MVPProject/.mcp.json
00_engine/projects/MVPProject/.cursor/mcp.json
00_engine/projects/MVPProject/.vscode/mcp.json
00_engine/projects/MVPProject/.gemini/settings.json
00_engine/projects/MVPProject/.codex/config.toml
```

非沙箱验证确认 auto-start listener 可绑定 `127.0.0.1:8000/mcp`；Codex tool 沙箱内启动 listener 会报 `HttpListener - Unable to allocate stream socket`，这是沙箱网络限制，不代表 UE 配置失败。详细说明见 [`mcp_agent_setup.md`](./mcp_agent_setup.md)。

## 7. 第一对 before/after

MVP 第一对建议从低风险编辑开始：

- E8 光照；
- E5 道具可见性；
- E6 配饰可见性；
- E11 表情。

输出控制在：

```text
00_engine/outputs/mvp/
```

验证要点：

- before/after 只改变一个因子；
- 相机、帧率、时间轴、随机种子固定；
- GT passes 和 sidecar JSON 一起输出；
- 输出大小受控，先不要开大规模 EXR。

## 8. SLURM 模板（小规模）

```bash
#!/bin/bash
#SBATCH --job-name=datamake_mvp
#SBATCH --partition=<PART>
#SBATCH --gres=gpu:1
#SBATCH --time=02:00:00
#SBATCH --output=00_engine/logs/%x_%j.out

set -euo pipefail

cd /scratch/prj0000000275/jcy/xks/DataMake
export DATAMAKE_ROOT="$PWD"
export UE_ROOT="$DATAMAKE_ROOT/00_engine/unreal/UE_5.8"
export UE_LocalDataCachePath="$DATAMAKE_ROOT/00_engine/cache/ddc"
export TMPDIR="$DATAMAKE_ROOT/00_engine/cache/tmp"
export ENG="$UE_ROOT/Engine/Binaries/Linux/UnrealEditor-Cmd"

if command -v vulkaninfo >/dev/null 2>&1; then
  vulkaninfo --summary | grep -qi "NVIDIA H200" || { echo "NO GPU / llvmpipe fallback"; exit 1; }
else
  echo "vulkaninfo not installed; verify GPU through nvidia-smi and UE logs"
fi

OUT="$DATAMAKE_ROOT/00_engine/outputs/mvp/job_${SLURM_JOB_ID}"
mkdir -p "$OUT"

00_engine/scripts/run_ue_cmd.sh "$DATAMAKE_ROOT/00_engine/projects/MVPProject/MVPProject.uproject" MVPMap -game \
  -RenderOffscreen -unattended -NoSplash -graphicsadapter=0 -log -stdout \
  -ExecutorPythonClass="/Engine/PythonTypes.RenderPairExecutor" \
  -OutputDir="$OUT"
```

先不要开大规模 job-array。网络盘小文件 I/O 会慢，MVP 通过后再重新讨论正式批量生产的存储和并发策略。

## 9. 仍需现场确认

- UE 5.8 Linux zip 的准确文件名和实际体积。
- 用户在 Epic 页面登录并获取 Linux Installed Build zip；如只提供签名下载 URL，要注意 URL 可能短时有效且不应公开记录。
- 当前节点是否能稳定 `vulkaninfo` 看到 H200。
- `UnrealEditor-Cmd` 是否缺新的运行时库；当前已知 `libgbm.so.1` 已由项目内 runtime 解决。
- SLURM 分区名和最大时限：`sinfo -o "%P %l %G"`。
- `00_engine/outputs/mvp/` 的实际输出规模。

## 10. 历史说明

2026-06-19 的部署稿曾推荐 `/local` 存 engine/DDC/render scratch。该方案已废弃，因为管理员确认不能使用 `/local`。旧结论只作为性能理想方案的背景，不再作为执行路径。
