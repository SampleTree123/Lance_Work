# v11 服务器上传清单

本文件由只读目录统计生成，没有复制、上传、删除或大文件哈希操作。

合计 **58,207 个文件，71.82 GiB**。逐文件可执行清单见 `TRANSFER_PLAN.json` 的 `files`：每项含源路径、目标相对路径、大小和修改时间。

目标路径以 `project/`、`workspace/` 两个逻辑根表示，上传工具将其分别映射到服务器工程目录和 Lance_Work 目录。保留相对布局；仅传 scripts 不足以运行正式角色/服装目录。

## 纳入范围

- `project_config`：0.000 GiB
- `project_content`：65.253 GiB
- `project_plugins`：0.139 GiB
- `project_descriptor`：0.000 GiB
- `workspace_runtime_authority_evidence`：4.536 GiB
- `workspace_referenced_metadata`：1.887 GiB
- `workspace_code`：0.006 GiB

包含完整 Content、Config、uproject，存在时包含 Source 和插件描述/Source/资源；工作区包含 unreal、dataset 代码以及当前依赖指向的 runtime、authority、evidence 元数据。历史 PNG/视频/FBX 和缓存不作为工作区上传项。

## 已启动编辑器证据

- `LogInit: Build: ++UE5+Release-5.8-CL-56057345`
- `LogInit: Engine Version: 5.8.1-56057345+++UE5+Release-5.8`
- `LogInit: Compatible Engine Version: 5.8.0-55116800+++UE5+Release-5.8`
- `LogInit: Command Line: /Game/Scenes/Hong_Kong_Street/Maps/Demo`

## 插件

- RLPlugin 2.03，标记引擎 5.8.0；Source存在：True。模块平台限制：`[{"Name": "RLPlugin", "Type": "Editor", "LoadingPhase": "PreDefault", "PlatformAllowList": ["Win64"]}]`。Linux未验证。

## 未确定项与服务器进入条件

- 服务器使用用户同步的 UE 5.8.1；尚需核实 Linux GPU/RHI、插件、字体、着色器及一个完整10秒样本的解码和画面一致性。
- 在抽查的已选元数据中发现 18,370 个 Windows绝对路径引用。服务器命令须显式带 `--portable-runtime`，由隔离入口在内存中重定位正式路径和pin字典，保留源JSON bytes及其SHA。只有请求前缀映射不足以处理内部引用；目标Linux读取分支仍需实测。
- RLPlugin模块仅声明Win64，Windows二进制已排除。Source随清单保留，但这不代表可直接编译Linux。先验证已导入资产是否无需加载该编辑器导入插件；如仍需则评估源码兼容和Linux重编译。
- 服务器UE必须具备工程启用和日志加载的对应Engine插件；本清单不上传Windows引擎。Win64专用插件需在服务器工程副本上作平台适配，不能直接认定全部可用。
- Content完整保留以避免漏掉贴图/材质/地图依赖；工作区元数据来自当前worker静态依赖和有限JSON引用追踪。动态生成路径仍需服务器预检，不宣称完整运行依赖验证。
- 统计时本地UE可能继续保存资产；上传前在渲染停止后重新生成清单。当前仅stat大小和mtime，无数十GB内容哈希。
- 服务器需Python3及可用libx264的FFmpeg或imageio-ffmpeg；本机Windows Python环境不在清单中。
- Windows本机 `00_engine/outputs/local_render_profile_v1/profile.json` 已从清单排除，原文件未改写。它绑定machine_name；服务器应不带它，用 `--pool-mb` 明确传入按服务器GPU实测选择的MRQ纹理池预算。
- 元数据路径抽查上限 400 个JSON，本次读取 400 个；未逐份审计全部历史证据。可通过 `--metadata-probe-limit` 调整抽查规模。

## 重新生成

```text
python 00_engine/scripts/dataset/build_render_transfer_manifest_v11.py --project-root <工程目录> --engine-root <引擎目录> --workspace <Lance_Work目录> --run-root <本次运行目录>
```

本脚本只生成清单，实际上传方式和服务器目的目录由后续明确设置。
