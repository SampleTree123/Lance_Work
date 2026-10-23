# v11 本地与服务器运行说明

> 2026-10-23纹理修正：旧画面已弃用，新样片与输入副本在 `../dataset_texture_quality_20261023_v1/corrected/`，审查见[新入口](../dataset_texture_quality_20261023_v1/REVIEW.md)。再次使用以下命令时请显式指定 `--run-root D:/UE/Lance_Work/00_engine/outputs/dataset_texture_quality_20261023_v1/corrected`，不要把旧模糊视频当成现行结果。当前worker使用FULLY_LOAD和可保存的发色材质；默认编辑器发现等待已从12秒增为120秒，以容纳高清贴图加载时短暂无响应，超过时限仍报错而非无限重试。服务器继续使用独立运行目录。

日期：2026-10-23。此文件说明当前脚本用法；具体本地渲染结果以本目录回执为准。服务器 GPU、插件、精确引擎版本、帧率和画面一致性仍待服务器实测。

## 入口与目录

外部入口是 `00_engine/scripts/unreal/run_dataset_render_v11.py`。它连接已经打开的 UE 编辑器，不启动 UE。启动前需要让对应工程启用 Python 远程执行，并保持当前机器只存在一个可匹配的工程实例；多实例时显式传 `--node-id`。

默认工作区为脚本所在的 `Lance_Work`，Windows 工程为 `D:/UE/projects/datatry_02`，引擎为 `D:/UE/UE_5.8`，运行目录为本目录。全部可以用参数覆盖。

作业清单采用 `{ "jobs": [...] }`，默认 `pilot_jobs.json`；主作业使用 `--jobs <main_jobs.json绝对路径>`。媒体路径为：

```text
jobs/<job_id>/prepared.json
jobs/<job_id>/frames/frame_0000.png ... frame_0299.png
jobs/<job_id>/video.mp4
jobs/<job_id>/media_receipt.json
jobs/<job_id>/media_attempt.json
jobs/<job_id>/driver_attempt.json
```

`remote/` 保存每次 UE 请求、返回值、错误与耗时；`render_receipts/` 保存异步渲染回执；`driver_summary.json` 保存最近一次队列结果。再次运行会更新最近一次的 driver 回执，远程请求记录仍以唯一文件名保留。

## 本地命令

以下示例在 `D:/UE/Lance_Work` 中运行，先查看编辑器状态：

```powershell
python 00_engine/scripts/unreal/run_dataset_render_v11.py --command-only status
```

只准备一个作业，检查场景与镜头：

```powershell
python 00_engine/scripts/unreal/run_dataset_render_v11.py --job-id train_node_000000 --command-only prepare
```

单独提交渲染时，需要已有该作业的 `prepared.json`：

```powershell
python 00_engine/scripts/unreal/run_dataset_render_v11.py --job-id train_node_000000 --command-only render
python 00_engine/scripts/unreal/run_dataset_render_v11.py --command-only status
```

`--command-only render` 返回后渲染仍在进行。应持续查询状态，直到 `receipt.status` 为 `completed` 或 `failed`，且 `subsystem_rendering`、`owned_executor_active` 都为 false、`active_executor_path` 为空，才能准备下一条。

完整队列自动执行准备、提交、等待渲染结束、编码和校验：

```powershell
python 00_engine/scripts/unreal/run_dataset_render_v11.py --limit 10
```

可以重复 `--job-id` 只运行选定作业，也可指定 `--jobs`、`--ffmpeg`、`--render-timeout`（秒，默认 3600）、`--command-timeout`（秒，默认 180）和 `--poll-interval`（秒，默认 3）。`--pool-mb` 是本次MRQ纹理池预算，当前默认10240MiB；迁移时必须按服务器GPU实测选择。退出码 0 表示本次选定作业全部成功或经过校验后复用；1 表示存在失败。

## 续跑与失败处理

原命令再次运行即可续跑。成功回执必须同时匹配当前作业、编码配置、成片 SHA256；保留的原始 PNG 也会重新校验完整帧序列与 SHA256。原始帧已被另行清理时，只有具备成功回执和对应成片哈希的作业才可直接复用。本脚本不删除原始帧。

如果UE已经完成渲染、外部驱动却在编码前中断，下次会先核实编辑器空闲，再校验 `prepared.json` 与当前worker的作业签名、该作业最新渲染回执的 `job_signature`、成功终止状态及帧目录。全部一致时直接进入独立编码，避免重复渲染。较新的失败/部分渲染会使旧成功回执失效；没有签名字段的历史回执不复用。帧数、PNG格式与输入哈希仍由编码器检查。

`--force` 强制重新准备/渲染/编码；已有准备资产在 UE 端可能继续复用。修改后的作业定义会改变签名，不能误复用之前的成片。

单个作业发生明确的准备错误、终止渲染失败或编码失败时，记录错误后继续。编辑器异常必须先通过状态查询证明渲染已经停止。网络中断、未知状态、不同渲染任务接管或超时会立即停止后续队列，防止上一条仍在渲染时修改世界。超时不会自动取消 UE 渲染；恢复前先检查状态。

队列持有本运行目录的 `driver.lock`，每次远程请求另持有现有审查桥的 `command_lock`。运行期间不要用其他面板修改同一编辑器世界。

## 分片与服务器

同一清单可通过 `--shard-count N --shard-index I` 分片，`I` 从 0 开始。分片按清单中选定作业的顺序确定；`--limit` 在分片之后应用。每个分片应连接不同服务器/编辑器。同一编辑器仍按串行队列运行。

服务器先打开目标工程的UE编辑器，启用Python远程执行。以下路径需要按服务器实际目录设置；`PROJECT_ROOT` 传含唯一 `.uproject` 的目录。先用新的服务器运行目录保存验证结果，避免将Windows已有回执当成Linux验收。

```bash
WORKSPACE_ROOT=/scratch/DataMake
PROJECT_ROOT=/scratch/projects/datatry_02
ENGINE_ROOT=/scratch/UE_5.8.1
MANIFEST_ROOT="$WORKSPACE_ROOT/00_engine/outputs/dataset_render_pilot_20261023_v1"
SERVER_RUN="$WORKSPACE_ROOT/00_engine/outputs/dataset_render_server_validation_v1"
# 先 export POOL_MB=<按服务器GPU实测选择的MiB>；不沿用Windows机器记录。
: "${POOL_MB:?Set POOL_MB to the measured server texture-pool MiB}"
DRIVER="$WORKSPACE_ROOT/00_engine/scripts/unreal/run_dataset_render_v11.py"
SERVER_ARGS=(--workspace "$WORKSPACE_ROOT" --engine-root "$ENGINE_ROOT"
  --project-root "$PROJECT_ROOT" --run-root "$SERVER_RUN"
  --portable-runtime --pool-mb "$POOL_MB")

# 只查询状态。
python "$DRIVER" "${SERVER_ARGS[@]}" \
  --jobs "$MANIFEST_ROOT/pilot_jobs.json" --command-only status

# 一个实际节点：准备、渲染300帧、编码、全解码校验。
python "$DRIVER" "${SERVER_ARGS[@]}" \
  --jobs "$MANIFEST_ROOT/pilot_jobs.json" --job-id train_node_000000

# 首条服务器画面核对后，运行同一12节点小样；已成功项按签名续跑。
python "$DRIVER" "${SERVER_ARGS[@]}" --jobs "$MANIFEST_ROOT/pilot_jobs.json"

# 正式主视频分片示例：每台机器/分片使用独立运行目录与编辑器。
python "$DRIVER" "${SERVER_ARGS[@]}" --run-root "${SERVER_RUN}_shard_0" \
  --jobs "$MANIFEST_ROOT/main_jobs.json" --shard-count 4 --shard-index 0
```

`--portable-runtime` 显式启用隔离模块图，在内存中映射正式runtime内的Windows路径与pin字典；原JSON文件及其哈希保持。上传清单会**排除**绑定Windows machine_name的 `00_engine/outputs/local_render_profile_v1/profile.json`，不会改写它。MRQ预算由上面的 `--pool-mb` 传入，服务器会话/浏览预算在没有本机profile时继承会话设置。

也可配置 `DM_WORKSPACE`、`DM_UE_PROJECT_ROOT`、`DM_UE_ENGINE_ROOT`、`DM_RENDER_RUN_ROOT`。外部 Python 与编辑器对同一共享目录使用不同挂载路径时，`DM_UE_PATH_MAP` 接受 JSON 前缀映射，如 `{"D:/UE/Lance_Work":"/scratch/DataMake"}`。按最长前缀替换发送给编辑器的路径，外部编码与回执校验仍使用外部 Python 可访问的本地路径。

`DM_UE_PATH_MAP` 负责请求路径，`--portable-runtime` 负责正式runtime内部路径；二者作用不同。优先让服务器外部Python与编辑器使用相同目标挂载路径。工程资产依赖、远程发现网络、大小写路径与插件配置仍须在目标服务器核实。

工程RLPlugin 2.03的模块仅声明Win64，上传清单保留其描述/Source/资源，排除Win64二进制。该声明本身不能判断已导入角色资产在Linux能否渲染；先用真实样本验证是否需要该编辑器导入插件，确需模块时再确认Linux适配/重编译。不要因为这项未确定就认定服务器渲染已经被阻断。

## 参考PNG在服务器复验

六个静态参考原型使用 `reference_pilot_jobs.json`，每项只输出一张PNG。先在同一 `SERVER_RUN` 完成其源主节点0和3775，并按原字节将 `main_jobs.json` 放到该目录；参考worker按这里的相对路径读取源作业定义。以下命令只是服务器操作示例，本地文档维护没有执行复制或UE调用。

```bash
mkdir -p "$SERVER_RUN"
cp "$MANIFEST_ROOT/main_jobs.json" "$SERVER_RUN/main_jobs.json"
REF_ARGS=("${SERVER_ARGS[@]}" --jobs "$MANIFEST_ROOT/reference_pilot_jobs.json"
  --worker-module ue_dataset_reference_pilot_v11)
python "$DRIVER" "${REF_ARGS[@]}" \
  --job-id ref_scene_train_node_000000 --command-only prepare
python "$DRIVER" "${REF_ARGS[@]}" \
  --job-id ref_scene_train_node_000000 --command-only render
python "$DRIVER" "${REF_ARGS[@]}" --command-only status
```

每次render都是异步提交；应重复status直到成功终止且executor已退出，再处理下一参考任务。其余五个job_id见 `REFERENCE_PILOT_README.md`；不要将这些单帧PNG送入300帧视频编码器。参考布置仍是原型，服务器技术成功也不自动冻结正式参考方案。

## 当前轻量验证范围

已完成不连接 UE 的 10 项测试：串行队列、单条终止失败后继续、超时停止、未知状态停止、命令选择与分片、新实例发现、远程请求独占锁、等待 executor 结束、成功回执与媒体哈希校验、明确 UE 异常后的空闲核验、渲染结束后中断的续跑及较新失败回执保护（部分在同一测试中覆盖）。未以这些测试代替真实 UE 渲染或服务器验证。
