# 正式渲染配置与上传入口

2026-10-23。当前包已整理并完成离线检查，尚未上传或在Linux执行。发型样图及自适应构图已获用户确认。无需重新构建数据图。

## 文件怎么用

| 文件 | 内容 |
|---|---|
| `RENDER_CONFIG.json` | 执行队列、输出目录、超时与续跑方式 |
| `config/VIDEO_PROFILE.json` | 已确定的视频、图片、画质、编码和参考图展示规则快照 |
| `config/CONTENT_CONFIG.json` | 实际使用的人物、发型、发色、动作、镜头、拍摄点、服装及出现次数 |
| `config/MACHINE_SERVER.template.json` | 上传后只需填写的服务器路径、Python/FFmpeg位置、纹理显存预算 |
| `queues/main/ordered_jobs.json` | 全部主视频，按场景→点位→人物→服装→发型等排序 |
| `queues/references/*_jobs.json` | 分类别参考任务和完整载体配置 |
| `queues/references/reference_bindings.json` | 每次编辑所用参考内容；使用 `effective_reference_links` |
| `TRANSFER_PLAN.json` / `.md` | UE工程、代码及运行依赖的上传清单；生成后以其中实际体积为准 |
| `SOURCE_SNAPSHOT.json` / `PACKAGE_FILES.json` | 配置来源与文件摘要，供上传核对 |

任务记录含具体人物、衣服部件、鞋子、头发、动作资产、镜头轨迹、拍摄点位置、画幅与输出位置。这里只重新整理执行顺序，主视频7203条定义和参考2458条定义均保持原内容。

## 本次规模与参数

- 主视频7203段：训练5980、测试1223。
- 动作参考809段；合计8012段视频。
- 图片1649张：场景893、身份80、发型112、服装564。
- 视频10秒、30帧/秒、300帧；横1920×1080，竖1080×1920。
- 身份/发型/服装图片1024×1024；场景图片与对应视频画幅一致。
- TSR、100%屏幕百分比、关闭动态分辨率与运动模糊；空间/时间采样1/1，预热120+32。
- 完整加载使用中的高清贴图；输出PNG序列，再编码H.264、CRF16、medium、yuv420p、BT.709有限范围MP4。
- 场景曝光使用已保存关卡的后期处理体积。**曝光存于UE地图资产中，不能只上传JSON。**
- 身份双白发紧脸图；发型黑色、两名载体、正背面、自适应取景、灰色衣物遮挡。衣物参考只显示目标单件。动作使用现有production10，不再次改变速度或循环。

`VIDEO_PROFILE.json`是已确认参数的快照；执行器中的画质与编码实现和它配套。它不是任意参数实时覆盖器：修改画质时需同步执行器并重建相应计划。每条任务的尺寸、帧率、时长、外观与镜头由任务文件直接驱动。

## 上传布局

保留两个根目录：`workspace/` 对应服务器的 Lance_Work，`project/` 对应服务器UE工程目录。

本配置包保留在 `workspace/00_engine/outputs/dataset_server_bundle_20261023_v1/`。`TRANSFER_PLAN.json`逐文件给出源路径和目标相对路径。按清单上传完整现用Content、Config、项目描述、插件源码/资源、执行代码及所引用的运行元数据。无需上传Windows引擎、历史视频、PNG帧、DDC、Saved和Intermediate。

**本文件夹是配置入口，不是UE资产的替代品。** 工作区运行依赖须按清单保留原相对位置。源文件中的历史Windows路径由 `--portable-runtime` 隔离映射，不能全局字符串替换后破坏原始摘要。

## 服务器填写与启动

1. 安装匹配的Linux UE5.8.1，准备Python3和支持libx264的FFmpeg。
2. 把 `config/MACHINE_SERVER.template.json` 复制为 `config/MACHINE_SERVER.json`，填写 `workspace_root`、`project_root`、`engine_root`、`output_root` 和 `texture_pool_mb`。显存预算按服务器GPU设置，不套用本地10240MB。其他空值可保留；使用当前Python及PATH中的FFmpeg。
3. 启动该工程的UE编辑器并启用Python远程执行。同一worker只运行一个编辑器。无桌面的Linux可以尝试以下启动方式，实际GPU/RHI和插件仍须在服务器验证：

```bash
"/your/UE5.8.1/Engine/Binaries/Linux/UnrealEditor" \
  "/your/project/datatry_02.uproject" -unattended -RenderOffscreen -graphicsadapter=0
```

不得使用 `-nullrhi` 做图像渲染。RLPlugin包含Win64平台限制；服务器先验证已导入资产能否无需加载该导入插件，不修改本地工程来适应服务器。

4. 在服务器工作区根目录先预览命令（不连接UE、不创建输出）：

```bash
python3 00_engine/scripts/dataset/run_render_bundle_v11.py \
  --bundle 00_engine/outputs/dataset_server_bundle_20261023_v1 \
  --machine 00_engine/outputs/dataset_server_bundle_20261023_v1/config/MACHINE_SERVER.json \
  --queue smoke_main
```

5. 在同一命令末尾加 `--execute` 才会开始渲染。先跑 `smoke_main`（12个本地同节点），再跑 `smoke_references`（16项：4动作、4身份、4发型、1场景、3衣物）。可用 `--limit 1` 先试一个，或 `--job-id <ID>` 指定任务。
6. 对照本地小样确认后，依次执行 `main`、`scene`、`identity`、`hair`、`garment`、`motion` 队列。小样与全量共用输出根，成功且配置一致的任务直接复用。

## 续跑、输出与调度

主视频输出在 `<output_root>/main/jobs/<job_id>/`；参考输出在 `<output_root>/references/jobs/<reference_id>/`。主片和动作参考最终文件为 `video.mp4`；图片为 `frames/frame_0000.png`。每项保留 `media_receipt.json` 和错误/耗时记录。

遇到独立任务错误时现有驱动记录错误，在确认UE空闲后继续；超时或编辑器状态不明时停止队列。修复后重新运行相同命令即可，不自动无限重试，也不默认强制重拍。完整PNG中间帧默认保留，本入口不擅自清理。

当前单GPU/单编辑器串行。主队列优先完成同场景内容，减少加载；参考背景也按场景排序。多个GPU需分别使用工程副本、输出根和对应UE节点，再按整场景划分主任务，不能让多个编辑器同时写同一工程Content。服务器耗时基准完成后再确定分片，当前不预设并发收益。

## 本地证据与下一步

清晰度对照：`../dataset_texture_quality_20261023_v1/REVIEW.html`（若该页不可用，见该目录报告和corrected任务输出）。身份：`../dataset_reference_portraits_20261023_v2/REVIEW.html`。发型：`../dataset_reference_hair_adaptive_20261023_v4/REVIEW.html`。动作、场景和衣物：`../dataset_reference_production_20261023_v1/REVIEW.html`。

本轮仅准备配置和上传清单，未重复渲染、上传或启动服务器。下一步填写服务器实际路径和资源配置，上传后执行上述小批对照。

重建配置包：

```bash
python3 00_engine/scripts/dataset/build_render_bundle_v11.py --out <新的包目录>
```

重建上传清单（本地运行）：

```bash
python 00_engine/scripts/dataset/build_render_transfer_manifest_v11.py \
  --workspace D:/UE/Lance_Work --project-root D:/UE/projects/datatry_02 \
  --engine-root D:/UE/UE_5.8 \
  --run-root D:/UE/Lance_Work/00_engine/outputs/dataset_server_bundle_20261023_v1
```

## 清理后的最终入口（2026-10-23）

新生成的主片资产放在 `/Game/DataMake/Render/Main`，参考资产在 `/Game/DataMake/Render/References`，启动关卡为 `/Game/DataMake/Render/Workspace/L_RenderWorkspace`。直接使用正式38槽位蓝图装配，不依赖旧试验关卡中的角色副本。现用源资产路径保持。

`config/UE_LIBRARY.json` 记录分类；`config/editor_collections/` 包含7个本地集合文件。需要服务器编辑器显示相同分类时，在编辑器关闭状态复制这些 `.collection` 到工程 `Saved/Collections/` 即可。无头渲染不依赖集合。

清理后已实跑一段1920×1080、30帧/秒、10秒主片和一张男性发型参考图。详见[清理与复测报告](../final_pipeline_cleanup_20261023_v1/REPORT.md)。Linux现场验证和全量渲染尚未执行。

## 统一微笑（2026-10-23）

主视频、动作参考视频、身份照和发型照统一使用已有原生微笑。动作时长和身体动作不变，参考图片取微笑片段首帧。场景与服装单件图不涉及表情。运行目录为 `00_engine/assets/character_creator/dataset_smile_v1.json`，动画在 `/Game/DataMake/Render/Expressions/SmileV1`；上传必须包含本轮新动画和更新脚本。旧无表情样片仅作历史记录，续跑不会直接视为当前版本。
