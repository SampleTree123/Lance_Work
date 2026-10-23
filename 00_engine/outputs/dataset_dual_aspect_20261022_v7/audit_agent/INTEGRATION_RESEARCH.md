# 双画幅离线接入核对（2026-10-22）

本文件为定向只读研究与审核入口。未改 UE、正式资产、点位、曝光或正式文档；不是媒体规格冻结，也不代表已渲染。

## 已核对

- 原输入为 `dataset_compact_graph_20261022_v6/selected_seed1`：训练 3,752 节点／12,000 链，测试 800 节点／2,400 链；节点 `state.aspect` 均为 `landscape`。
- 正式库 `production_workflow_20261017_v1/camera_library/production10/camera_plan.json` 有 1,092 个条目，26 动作×21 镜头×两画幅，各画幅 546。当前候选仍按现用目录的 25 动作选择，不把库中额外历史动作恢复进来。
- 匹配键是 `(motion_id, camera_id, orientation)`。条目含 `shot_id`、`orientation`、`width`、`height`、`aspect_ratio`、`trajectory_sha256`、`frames`、`endpoint_validation_frame`、动作版本和时钟字段。预设尺寸为横屏 1280×720、竖屏 720×1280；仅用于引用既有轨迹预设，不能写成用户已确认的最终分辨率、帧率或时长。
- `ue_production_trial_render_v1.py:make_plan()` 的现有接入按上述键选择条目；点位变换修改轨迹后会重新计算轨迹哈希。数据请求中的库轨迹哈希是**局部库轨迹**，不能冒充已应用场景点位后的最终世界轨迹哈希。
- `ue_production_site_runtime_v1.py:load_mode()` 联合读取 `geometry.json`、`catalog.json`、`camera_plan.json` 并校验镜头目录。`scene_site_review_geometry_v1.py:build_catalog()` 将画幅、尺寸与轨迹哈希写入目录条目。
- 正式合法性使用既有 `dataset_balanced_graph_20261022_v5/audit_candidate.py:Rules`，其纯 Python 服装合同与冻结目录均沿用 v6。人工排除键为 `(site, action, camera, aspect)`，快照横竖各 714 条。逐节点把 aspect 改为 portrait 后，当前选中训练／测试节点均合法；详见 `portrait_eligibility_mask.json`，两 split 禁止节点及禁止链均为 0。

## 参考素材引用

既有 `dataset_trial_build_20261021_v1/plan_references.py:Planner` 可从最终保存的 nodes／edges／sessions 重新派生未渲染参考需求。其动作视频键为 action×camera×sex×symbolic_aspect；场景空背景图还包含 site，且 action 保留是因为相机初始位置可能依赖动作。应在最终双画幅候选上重算这两类需求，不能直接继承旧横屏参考清单。

人物正脸、发型正背图和衣物／鞋单件正背图不以主视频 aspect 作为身份键；横竖版本可以引用同一素材。换发型载体、文本改写或双画幅副本都不增加独立结构链数。动态镜头场景参考仍为目标镜头初始空背景图，既有脚本的实际初帧、载体及最终媒体 profile 保持待冻结状态。

参考脚本能写入目标候选的 `reference_manifest.json`／`reference_summary.json`／`REFERENCES.md`，但本子任务尚未调用它，避免提前写入父 agent 正在构造的候选。

## 独立审核

`audit_dual_aspect.py --root <candidate> --require-render-requests --output <audit_agent/result.json>`：

1. 以完整非画幅状态推导每个新节点的唯一原节点，再核对声明的 `original_node_id`。
2. 按原 session ID（或显式 original/source session ID）逐条核对 kind、length、fork_round、完整 history 与 steps；每个 source_position 必须指向实际完整父历史，分叉轮次不得变化。
3. 逐节点／边重跑正式合法性，要求每链同画幅、图边原子语义和已登记边一致。
4. 按完整实际状态重算渲染节点数、横竖双用原节点数、新增节点数与每画幅链数；跨 split 在去掉画幅后仍不得重合。
5. 默认每原链恰一条；`--copies 2` 专用于明确的双份镜像对照，报告始终把相同原结构计为一条结构链。
6. 如提供 `render_requests.json`，要求每个 used node 恰一项，并核对 state、原节点、画幅和正式库条目的 ID、匹配键、尺寸与局部轨迹哈希。

`baseline_self_audit.json` 是原数据自检，不是最终候选的审核回执。候选结果须另存回执。

## 最终选择后需要定向同步的入口（尚未写入）

遵循仓库权威 `.codex/skills/character-factory-doc-maintenance/SKILL.md`。父 agent 选择候选后，仅同步变化事实的所有者：

- Technical：`technical/dataset/DATASET_DESIGN_EXPLORATION_20261021.md`（运行根、候选、方法、来源与审核入口）。
- 规则契约：`technical/dataset/DATASET_TRIAL_CONTRACT_20261021.md`（用户本轮允许横竖链数近似、主视频预算适度超出 5000／800及同链固定画幅；不回改历史实验）。
- 状态：`project_management/status/PROJECT_STATUS.md` 和 `PROJECT_STATE.json` 的数据集分支部分；保持唯一 current 父计划与其他分支原状，不把离线候选晋升为生产接受。
- Plan／Workflow／Batch：只有本次确实改变该层需求或阶段事实时才更新对应 R17／WF-70／WF-80。不能因为节点请求已生成就改成已渲染。
- 输出所有权：新运行根登记为离线候选与证据，由上述探索 Technical 拥有；保留旧 immutable v6。精确数字由候选 JSON 和审核回执拥有，顶层导航不重复动态数字。

本子任务没有写入这些正式入口；待父 agent 的最终选择。
