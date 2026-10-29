# 服务器同步与 UE 渲染工作状态

2026-10-29修复展示已获用户Git上传授权：独立展示包含24条最终production视频，2322条全量重渲染已技术通过；推送待执行，整体数据仍REPAIR_PENDING，视觉确认和数据替换不在本次上传授权中。详见[发布记录](../../../../../../00_engine/render_pipeline/docs/REPAIR_SHOWCASE_PUBLICATION_20261029.md)。

2026-10-28按用户要求追加8条真实分叉会话，新增36份视频副本；直链和分叉分别成页、互相链接。实际起点由原source_history_occurrence定位，不把兄弟节点串成直链。校验和发布记录见[分叉展示归档](../../../../../../00_engine/render_pipeline/docs/BRANCH_SHOWCASE_20261028.md)。

2026-10-28展示包已上传GitHub：用户完成推送后，独立核验远端main为963eb1d；网页与全部72份MP4真实副本已发布，先前认证阻碍解除。GitHub的53.49MB文件警告未阻止上传。入口与校验范围见[展示归档](../../../../../../00_engine/render_pipeline/docs/CHAIN_SHOWCASE_20261028.md)。

2026-10-28展示包已完成本机验证：按用户最终要求选择2–5轮各4条完整直链，网页、原始MP4副本及属性/编辑说明统一保存；本次视频获明确Git上传例外，发布范围仅限展示包。用户已在本地定位此前服装问题并表示大部分视频无需处理，服务器尚未收到具体修复方案，本轮未改生产媒体。数量、校验范围及发布记录见[展示归档](../../../../../../00_engine/render_pipeline/docs/CHAIN_SHOWCASE_20261028.md)。此前同日“公共流程根因待排查”段落为本地反馈前的历史，不表示全批数据需要重渲染。

> 文档 ID：`STATUS-SERVER-SYNC`
> 文档类型：`status`
> 生命周期：`current`
> 状态来源：2026-10-23服务器只读核对、第一批发布Manifest与历史profile
> 当前计划：全项目仍以PROJECT_STATE为准；本页记录独立的文档同步/UE执行工作，不另建第二个主计划
> 最近核验：2026-10-23，Asia/Singapore；约00:24–00:30

## 1. 本分支范围与下一步

用户于2026-10-23将对话分工拆开：本分支负责本地/服务器同步及UE渲染；模型架构由另一对话推进。本轮已完成服务器文档整理，用户随后授权通过GitHub上传已审查的服务器差异。2026-10-23确认排除UE源码patch及临时文件，用户已删除独立robotdata目录；GitHub登录节点认证已通过，遗留LFS钩子已备份停用，内容提交e0dd61c已推送至main并核验远端，详见[GITHUB_SYNC_REVIEW](GITHUB_SYNC_REVIEW.md)。未修改模型实现、渲染代码、正式配置或资产，也未启动/停止作业。

下一步：用户先保存Windows端未提交改动，fetch GitHub main并比较合并；按[文档同步说明](../../technical/rendering_release/DOCUMENT_SYNC.md)把服务器版本先放入本地暂存目录，再合并本地独有文档和最新架构记录。同步完成后，确认下一批UE输入和可用生产引擎，再安排新allocation上的预检。当前尚未验收两端一致，也未登记新渲染批次或通过新会话Gate。

## 2. 当前机器快照

| 项目 | 2026-10-23读取结果 | 含义 |
| --- | --- | --- |
| 节点/GPU/驱动 | 8GS9B74；NVIDIA H200；580.126.20 | 只证明本次读取的节点，不固定未来GPU节点 |
| 工作区 | `/scratch/prj0000000275/jcy/xks/DataMake`；shell物理路径显示home下别名 | 跨机器使用repo相对路径，不把home显示路径当第二份工作区 |
| Git | main；HEAD b578a02f8302bfceb6a2f8f0ffa65cf9246db921；有大量已修改及未跟踪文件 | HEAD不足以代表当前服务器内容，单纯git pull不能同步未提交文件 |
| scratch容量 | 2.8T总量、2.3T使用、约511G可用 | 共享盘时点读数，下一轮渲染前重新检查 |
| 用户队列 | 170881 interactive与171441 sx_ue5_render均RUNNING | 只读快照；没有操作作业 |
| 171441工作目录 | `/scratch/prj0000000275/jcy/sx/videoedting/video-edit-structure` | 不是本DataMake目录，不能据作业名认作本项目新渲染 |

## 3. UE与第一批数据：历史接受和当前可用性分开

- 第一批v004的渲染、WF-90发布和独立验证已完成；唯一交付根仍为`00_engine/outputs/delivery/first_batch_candidate_20260830_v002/dataset_v1/`，本次确认目录和manifest存在，没有重新逐个解码/校验全部媒体。
- `datatry_02.uproject`存在，其SHA-256为`38496810df01221fb1a2bb87d98b92d27613f47de07778d57c0ddcd4be3c83e0`，与发布证据中的profile相符。这只核验uproject文件，不证明全部Content/插件闭包未变。
- 已发布profile所记的`/scratch/prj0000000275/jcy/sx/UnrealEngine/Engine/Binaries/Linux/UnrealEditor`当前不存在，因而无法重算历史生产二进制SHA；旧生产命令不能直接照抄执行。
- `00_engine/unreal/UE_5.8/Engine/Binaries/Linux/UnrealEditor`存在；Build.version为5.8.0、CL55116800。它是工作区保留的安装版，尚未证明与历史source compatibility build等价，不能自动替换后继承旧Gate。
- 八份兼容补丁仍有记录，位于`00_engine/scripts/unreal/patches/ue58_vulkan_compatibility/`。本轮未编译、下载、恢复或运行引擎。
- 当前引擎路径缺失不推翻已发布媒体的历史验收；影响的是后续重新渲染/复现的环境准备。

## 4. 本次文档修正与验收边界

修复三个指向已归档第一批计划的断链；更新渲染/发布导航及WF-00/WF-80的旧“等待发布”表述；区分Windows与服务器路径；标记早期Installed Build/MVP/磁盘容量报告的历史范围；清理AGENTS和HANDOFF中的过期接手描述；增加同步范围、冲突合并和机器快照规则。

架构讨论内容及另一分支刚确认的决定原样保留。归档计划、历史报告、rebuild_reference和legacy快照不重写；本次不删除任何历史材料。

文档审计和既有Python测试只证明文档/代码回归范围；不代表UE当前像素、项目资产闭包或下一批生产验收。同步清单提供当前服务器文件hash；本地尚未提供清单，不能声称两端相同。

## 5. 本轮文档检查

2026-10-23：主文档体系审计通过，0错误/0警告；额外扫描234份非legacy/rebuild Markdown，无本地断链。已有标准库测试共132项通过（文档22、数据30、UE脚本80），未启动真实UE或GPU渲染。使用unittest执行这些已有测试，不宣称运行了依赖UE/CC的集成Gate。

同步文件以[本轮清单](../../../../../implementation/server_documentation_sync_20261023.json)中的相对路径和hash为准；清单不包含自身的自引用hash。后续任一对话修改文件后，该文件应补同步或刷新清单。
