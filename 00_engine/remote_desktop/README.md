# Remote Desktop Experiment

> 状态：2026-07-08 已完成用户态 TurboVNC + SSH tunnel + Windows VNC Viewer 验证；`Xvnc + xterm` 可用。完整 UE Editor GUI 可进入 H200/Vulkan 和项目 map 加载，但在纯 Xvnc 编辑器 UI 后期 SIGSEGV，不作为稳定交互编辑方案。

## 目的

本目录用于测试在没有管理员权限的 Linux 集群上，自行启动一个可连接的远程桌面，辅助 Unreal Editor 图形化预览。

这只是交互预览支线，不替代主生产管线。正式批量数据生成仍以 UE Python、MRQ/MRG 和 sidecar metadata 为准。

## 已安装内容

- TurboVNC 3.3 官方 `x86_64.rpm` 已下载并解包到 `turbovnc-3.3/`。
- `libXfont2` 已从 Ubuntu 22.04 `libxfont2` `.deb` 解包到 `runtime-libs/`。
- `xkbcomp`、`xsetroot` 已从 Ubuntu 22.04 `x11-xkb-utils`、`x11-xserver-utils` `.deb` 解包到 `runtime-tools/`。
- UE 运行时已有的 `libgbm.so.1` 复用于 TurboVNC。

## 本地验证结果

已在登录节点验证：

```bash
timeout 8s 00_engine/remote_desktop/start_xvnc_xterm_direct.sh 97
```

结果：`Xvnc` 可启动，监听 `127.0.0.1:5997`，创建 `1600x900` framebuffer，并成功启动 `xterm`。日志见 `logs/xvnc-97.log`。

`vncserver` wrapper 在 Codex 执行器中后台启动后会被外层进程清理，容易造成误判；当前推荐使用 `start_xvnc_xterm_direct.sh` 这个直接启动脚本。

已在 GPU job `101190` / node `8FS9B74` 上验证：

- H200 可见，driver `565.57.01`。
- `Xvnc` 可在 GPU 节点监听 `127.0.0.1:5997`。
- UE Editor 在 `DISPLAY=:99` 下可识别 `NVIDIA H200`，进入 `SDL_WINDOW_VULKAN` / `VULKAN_SM5`，并开始 TargetPlatform、DDC、shader 初始化。
- UE 5.8 默认会因 NVIDIA Linux driver `<580.00` 弹出 known-bad driver 对话框；集群当前 driver `565.57` 触发该检查。用临时配置 `r.WarnOfBadDrivers=0` 可跳过对话框继续启动。

2026-07-08 进一步验证：

- Windows 本地 VNC Viewer 可通过 `GPU -> login reverse tunnel -> Windows local tunnel` 连接到 GPU 节点 `Xvnc`。
- VNC 中的 `xterm` 显示正常，可作为远程终端和轻量 smoke 环境。
- UE Editor 在 `run_ue_editor_existing_display.sh` 下识别 H200/Vulkan，项目 map 加载完成后在编辑器 UI 后期 SIGSEGV。
- CrashReportClient 随后因 `GLX is not supported` 二次失败；这是 Xvnc 无 GLX 的副作用，不是最初崩溃原因。
- 结论：纯用户态 Xvnc 不适合承载完整 UE Editor GUI。服务器路线继续采用脚本化 UE、MCP/offscreen/MRQ；人工图形化编辑优先放本地或等待管理员提供 DCV/NoMachine/VirtualGL/带 NVIDIA GLX 的远程桌面。

## 在 GPU job 中启动

拿到 Slurm GPU interactive job 后，先进入对应节点，再运行：

```bash
cd /scratch/prj0000000275/jcy/xks/DataMake
GEOMETRY=1920x1080 00_engine/remote_desktop/start_xvnc_xterm_direct.sh 97
```

保持这个进程不要退出。它会启动：

- X display：`:97`
- VNC 端口：`127.0.0.1:5997`

停止方式：在运行该脚本的终端中按 `Ctrl-C`。

如果要直接启动 UE Editor 进行诊断：

```bash
cd /scratch/prj0000000275/jcy/xks/DataMake
GEOMETRY=1920x1080 00_engine/remote_desktop/start_xvnc_ue_editor.sh 97
```

该脚本会自动加入：

```text
-ini:Engine:[ConsoleVariables]:r.WarnOfBadDrivers=0
```

这是为了跳过 UE 5.8 对当前集群 NVIDIA driver `565.57` 的 warning dialog。这个绕过只用于交互预览诊断；正式无头渲染仍走脚本化 smoke/MRQ/MRG。

如果 UE Editor 崩溃，需要优先使用分离流程，避免 UE 退出时连带关闭 VNC：

```bash
cd /scratch/prj0000000275/jcy/xks/DataMake
GEOMETRY=1920x1080 00_engine/remote_desktop/start_xvnc_xterm_direct.sh 97
```

本地 VNC 连接成功后，在 VNC 里的 xterm 中运行：

```bash
export DISPLAY=:97
cd /scratch/prj0000000275/jcy/xks/DataMake
00_engine/remote_desktop/run_ue_editor_existing_display.sh
```

这样即使 UE crash，VNC 桌面仍会保留，便于继续查看日志或尝试参数。

## 本地连接

VNC 只绑定节点 localhost，不直接开放到集群网络。需要 SSH tunnel。

如果本地可以经 login node 跳到 GPU 节点：

```bash
ssh -N -J stuchengyou@orion-login01 stuchengyou@GPU_NODE -L 5997:127.0.0.1:5997
```

然后本地 VNC viewer 连接：

```text
localhost:5997
```

如果不能直接 SSH 到 GPU 节点，需要改用 Slurm/集群允许的 tunneling 方式；不要直接把 VNC 端口绑定到公网地址。

## UE Editor 测试结论

手工测试 UE Editor：

```bash
export DISPLAY=:97
/scratch/prj0000000275/jcy/xks/DataMake/00_engine/unreal/UE_5.8/Engine/Binaries/Linux/UnrealEditor \
  /scratch/prj0000000275/jcy/xks/DataMake/00_engine/projects/MVPProject/MVPProject.uproject
```

已知结论：

- 该 VNC display 已能让 UE 初始化到 H200/Vulkan，也已由 Windows VNC Viewer 目视确认 `xterm` 可交互。
- 完整 UE Editor GUI 在纯 Xvnc 下不稳定，已在编辑器 UI 后期 SIGSEGV。
- 如果只是查看日志、执行 shell、启动轻量诊断，VNC 可用。
- 如果要稳定人工操作 UE Editor，需要管理员提供 DCV、NoMachine、VirtualGL 或带 NVIDIA GLX 的远程桌面栈。
- 主路线仍应使用 UE Python/MCP + offscreen preview render/MRQ。
