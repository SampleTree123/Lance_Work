# v11 Linux 迁移准备（2026-10-23）

本页交付路径适配与交接要求，**尚未在 Linux 或服务器 UE 实跑**。当前本地样片是否通过，以本 Run 实际渲染回执为准；本页离线检查不构成媒体或画面验收。

## 新入口

新增 `00_engine/scripts/unreal/dataset_runtime_paths_v11.py`，不改旧 worker、正式 runtime helper 或冻结 JSON。现有外部驱动已经接入 `--portable-runtime`；服务器命令须显式带该参数，并以 `--pool-mb` 传入服务器实测选择的MRQ纹理池预算。可直接执行的完整步骤见 [OPERATIONS.md](./OPERATIONS.md)。

使用Python调用的集成方也可在构造worker之前显式启用，并在同一队列复用该对象：

```python
from dataset_runtime_paths_v11 import RuntimePaths

paths = RuntimePaths(
    workspace_root="/data/work/Lance_Work",
    project_file="/data/projects/datatry_02/datatry_02.uproject",
    engine_root="/opt/UnrealEngine-5.8",  # 仅用于旧脚本的引擎路径默认值
)
renderer = paths.load_renderer()
result = renderer.dispatch(request)  # request 使用目标机器的 run_root/jobs_path
path_report = paths.report()
```

已有 renderer 模块的 bootstrap 也可调用：

```python
from dataset_runtime_paths_v11 import patch_runtime

paths = patch_runtime(
    renderer_module,
    workspace_root="/data/work/Lance_Work",
    project_file="/data/projects/datatry_02/datatry_02.uproject",
)
```

`patch_runtime` 只把该入口的调用委托给隔离模块图，不调用 UE。适配器由驱动的 `--portable-runtime` 或上面Python入口显式启用，不修改已有共享审查worker。迁移后应从新进程开始；不要把旧进程中的Python对象当成迁移结果。

## 具体解决的路径问题

| 消费位置 | 原问题 | 处理方式 |
| --- | --- | --- |
| `night_character_review_v1.configuration` | `case['audit']` 是 Windows 绝对路径 | 私有模块读取 JSON 时仅在内存重定位，实际读取目标 workspace 中同一 audit 文件 |
| `ue_pair_revision_runtime_20261019_v1` | `PROJECT` 参与当前工程/PID 检查 | 显式绑定传入的目标 `.uproject`，保留检查本身 |
| 正式 `asset_inventory_formal_runtime_v1.py` | 硬编码 `SCRIPTS`、`CONTENT`，active pointer 内也有绝对路径 | 模块构造 Path 时映射，动态加载的 helper 与其私有模块使用同一策略 |
| palette 兼容证明、wardrobe correction、previous publication | 整个 pin 字典及 `source['path']` 会做直接相等比较，仅改 open 路径仍会失败 | 读取后的文件路径与路径字典键统一映射；SHA256 继续针对原文件 bytes |
| `ue_production_site_runtime_v1`、旧试拍/渲染 helper | 显式 project Content 路径及部分由 workspace 祖先推出来的 project 路径 | 私有模块的 `CONTENT`、`PROJECT_CONTENT`、`PROJECT` 显式绑定目标工程；workspace 和 project 可在不同目录 |
| `PrivateModules` 与 `spec_from_file_location` | 依赖会再创建私有模块，单改最外层 read 不够 | 仅隔离模块的 pathlib/json/importlib 接口携带同一映射，不修改系统级 pathlib/json/importlib |

默认源根只有 `D:/UE/Lance_Work`、`D:/UE/projects/datatry_02` 及其旧 `.uproject`；提供 engine_root 时增加旧 UE 5.8 引擎根。斜线与反斜线都支持。目标根可以改名且不必同级。

`/Game/...` 对象路径、动作/衣服/发型选择和节点 state 均保持。未被实际读取的旧 FBX/export 等历史路径可以留在证据中；若某条新执行分支真的打开未映射 Windows 路径，适配器明确失败，要求补充 `extra_roots={旧根:目标根}`，不猜测文件位置。包含 `..` 的映射尾路径拒绝执行。

## 迁移清单

1. 带走当前工作区脚本与本 Run 的 `main_jobs.json`、`pilot_jobs.json`、媒体 profile。新队列用目标机器绝对 `--run-root`、`--jobs`；job 内输出路径相对 Run，camera plan 路径相对 workspace。
2. 角色轻量依赖包括 `user_edited_night_import_20261020_v1/delivery.json`、其中40个 `case.audit`、pair review 的 retained catalog/geometry/sites，以及脚本实际读取的 palette/wardrobe 正式发布文件。
3. 保留 `production_workflow_20261017_v1` 的正式 active pointers、被选中的 catalogs、before snapshots、move receipts、palette compatibility proof 与归档代码、wardrobe correction/proof、production motion pointer/catalog，以及 `camera_library/production10` 的计划和配套 metadata。不要重写其 path 字段或重新保存 JSON，否则冻结 SHA 会改变。
4. 迁移工程本体及实际依赖的 Content、Config、Plugins。job 的衣服/头发/角色 meshes、production10 动作、镜头模板地图、源场景及其材质/纹理都必须存在；只拷 Git 和 JSON 不足。路径适配不生成或修复缺失 uasset。
5. **Windows本机 `00_engine/outputs/local_render_profile_v1/profile.json` 已由上传清单排除，原文件未改写。** `pool_profile()` 会核对machine_name。服务器不带这份本机配置以继承会话预算，MRQ通过 `--pool-mb` 明确传入按服务器GPU实测选择的预算；如另建profile，应属于服务器本机且独立保存。
6. 核对 Linux 对应引擎构建、Python/MRQ 及工程插件、RHI/GPU、字体/大小写路径。重新生成平台 DDC/着色器。编码器支持 `--ffmpeg` 或 imageio-ffmpeg fallback；需实际证明 Linux binary 包含 libx264。
7. 首先1个实际节点，随后同批12节点；核对300帧、30fps、尺寸、颜色/范围、材质/发型/睫毛、动作相位与相机，比较本地样片。用新的服务器运行目录记录结果，已有Windows prepared/render回执不是Linux验收。六张参考PNG在同一服务器运行目录的源节点准备完成后单独复验，不进入300帧视频编码器。

## 服务器命令入口

以下例子假设目标工程目录中只有一个 `.uproject`，UE已经由服务器打开并启用Python远程执行。`POOL_MB` 必须由操作者按服务器GPU预算设置；本页不提供跨机器通用值。

```bash
: "${POOL_MB:?Set POOL_MB to the measured server texture-pool MiB}"
python /scratch/DataMake/00_engine/scripts/unreal/run_dataset_render_v11.py \
  --workspace /scratch/DataMake \
  --engine-root /scratch/UE_5.8.1 \
  --project-root /scratch/projects/datatry_02 \
  --run-root /scratch/DataMake/00_engine/outputs/dataset_render_server_validation_v1 \
  --jobs /scratch/DataMake/00_engine/outputs/dataset_render_pilot_20261023_v1/pilot_jobs.json \
  --portable-runtime --pool-mb "$POOL_MB" --job-id train_node_000000
```

先验收这一个节点，再移除 `--job-id` 跑全部12个小样；正式主视频使用 `main_jobs.json` 和分片参数。不要将本Run的本地验证回执计为服务器通过。

工程插件RLPlugin 2.03的descriptor标记EngineVersion5.8.0，其编辑器模块allowlist仅Win64；本地运行日志实际引擎为5.8.1。上传保留其Source/资源，排除Windows二进制。服务器应核实已导入角色资产在未加载该导入插件时的实际渲染情况；确需模块时再评估Linux支持与重编译。平台声明是待验证项，不能据此直接认定现有资产的渲染被阻断。

`reference_manifest.json` 与 normalized catalog 仍带历史绝对路径；生成的 job 绑定已可迁移，renderer 不直接读取整份 reference manifest。正式 helper 实际消费到的 pointer/catalog/proof 路径在上述隔离读入口映射。未检查或承诺整个历史输出树都能独立重放。

## 已完成的离线验证与剩余边界

- Windows 本地读取真实40人 delivery 的全部 audit、构造正式 wardrobe/hair domain，以及 `pair.graph_and_data()` 的40人目录通过；未调用 `worker()`，未创建 UE 场景。
- 4个无 UE fake tests 通过：不同 workspace/project 根、旧反斜线路径与 pin 字典相等、动态 formal helper、真实 night configuration 消费 fake40 audit、新 `.uproject` 名称、源 JSON bytes 不变、未知根/逃逸拒绝、幂等映射与共享模块不变。
- 测试覆盖 Python 3.12 的 Path 初始化行为；实现兼容旧版 Path 在 `__new__` 保存路径的差异，但服务器实际 Python 版本仍需运行测试。
- Linux 路径大小写、Linux filesystem、完整 worker 构造、UE包加载、GPU渲染、服务器颜色和吞吐均未验证。4个 fake tests 是代码行为检查，不能替代这些步骤。
- 2026-10-22 18:22:33 UTC，主会话在实际Windows UE中通过 `--portable-runtime --command-only status`：隔离入口返回MRQ空闲状态，无错误。证据为 `remote/83f3c3f06d8b497ca0f88f0aa1cae28c.json`。该结果证明本地bootstrap可用，未证明Linux运行或服务器渲染通过。

复验命令：`python 00_engine/scripts/unreal/tests/test_dataset_runtime_paths_v11.py`。
