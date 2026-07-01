# UE 5.8 无头批渲集群部署 + MVP 启动计划

> 目标：在当前 DataMake 工作目录内安装 UE 5.8，跑通 `UnrealEditor-Cmd` 无头渲染，并产出第一对 before/after 编辑配对。
> 状态：2026-07-01 更新。管理员确认不能使用 `/local`，本文件采用 DataMake 单目录方案。

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
    cache/
      ddc/              # DDC / shader cache
      tmp/              # 临时目录
    projects/
      MVPProject/       # MVP UE 工程
    outputs/
      mvp/              # 少量验证输出
    logs/
```

2026-07-01 本地 `df -h .` 显示 `/scratch` 仍有 766G 可用，足够 UE 安装和 MVP。注意这是 WekaFS/网络盘，小文件 I/O 可能慢；先控制规模完成 MVP，不在这里直接启动正式大规模生产。

## 1. 安装路线

优先使用 **UE 5.8 Linux Installed Build zip**：

- 无需 root。
- 无需源码编译。
- 自带 editor、Python 和 MoviePipeline 相关能力。
- 下载约 25-30G，解压约 45-65G；解压成功后删除 zip。

源码编译、容器、Apptainer 暂时都不是主路径。只有当 Installed Build 缺必要能力或依赖无法解决时再回头讨论。

## 2. 下载与解压

```bash
cd /scratch/prj0000000275/jcy/xks/DataMake
export DATAMAKE_ROOT="$PWD"
export UE_ROOT="$DATAMAKE_ROOT/00_engine/unreal/UE_5.8"
export UE_ZIP="$DATAMAKE_ROOT/00_engine/unreal/downloads/ue58-linux.zip"
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
00_engine/unreal/downloads/ue58-linux.zip
```

解压：

```bash
unzip -q "$UE_ZIP" -d "$UE_ROOT"
chmod -R u+rwX "$UE_ROOT"
```

如果 `unzip` 对大文件失败，用 `bsdtar` 或 `7z`。

解压并通过 `-version` 验证后，删除 zip 节省空间：

```bash
rm "$UE_ZIP"
```

## 3. 启动前自检

每次换节点或环境变动后先跑：

```bash
cd /scratch/prj0000000275/jcy/xks/DataMake
export DATAMAKE_ROOT="$PWD"
export UE_ROOT="$DATAMAKE_ROOT/00_engine/unreal/UE_5.8"
export UE_LocalDataCachePath="$DATAMAKE_ROOT/00_engine/cache/ddc"
export TMPDIR="$DATAMAKE_ROOT/00_engine/cache/tmp"
export ENG="$UE_ROOT/Engine/Binaries/Linux/UnrealEditor-Cmd"

df -h "$DATAMAKE_ROOT"
nvidia-smi
vulkaninfo --summary | grep -i deviceName
ldd --version | head -n 1
uname -r
ldd "$ENG" | grep 'not found' || true
"$ENG" -version
```

期望：

- `vulkaninfo` 能看到 NVIDIA H200，而不是 llvmpipe。
- `ldd "$ENG" | grep 'not found'` 没有缺库。
- `UnrealEditor-Cmd -version` 能正常退出。

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

vulkaninfo --summary | grep -i deviceName
"$ENG" "$DATAMAKE_ROOT/00_engine/projects/MVPProject/MVPProject.uproject" MVPMap -game \
  -RenderOffscreen -unattended -NoSplash -nohmd -NoLoadingScreen \
  -graphicsadapter=0 -windowed -ResX=1280 -ResY=720 -ForceRes \
  -FixedSeed -log -stdout -allowStdOutLogVerbosity \
  2>&1 | tee "$DATAMAKE_ROOT/00_engine/logs/mvp_smoke.log"
```

先用低分辨率和少量帧验证。确认日志里没有 llvmpipe/CPU fallback，再提高设置。

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

vulkaninfo --summary | grep -qi "NVIDIA H200" || { echo "NO GPU / llvmpipe fallback"; exit 1; }

OUT="$DATAMAKE_ROOT/00_engine/outputs/mvp/job_${SLURM_JOB_ID}"
mkdir -p "$OUT"

"$ENG" "$DATAMAKE_ROOT/00_engine/projects/MVPProject/MVPProject.uproject" MVPMap -game \
  -RenderOffscreen -unattended -NoSplash -graphicsadapter=0 -log -stdout \
  -ExecutorPythonClass="/Engine/PythonTypes.RenderPairExecutor" \
  -OutputDir="$OUT"
```

先不要开大规模 job-array。网络盘小文件 I/O 会慢，MVP 通过后再重新讨论正式批量生产的存储和并发策略。

## 9. 仍需现场确认

- UE 5.8 Linux zip 的准确下载来源和文件名。
- 当前节点是否能稳定 `vulkaninfo` 看到 H200。
- `UnrealEditor-Cmd` 是否缺运行时库。
- SLURM 分区名和最大时限：`sinfo -o "%P %l %G"`。
- `00_engine/outputs/mvp/` 的实际输出规模。

## 10. 历史说明

2026-06-19 的部署稿曾推荐 `/local` 存 engine/DDC/render scratch。该方案已废弃，因为管理员确认不能使用 `/local`。旧结论只作为性能理想方案的背景，不再作为执行路径。
