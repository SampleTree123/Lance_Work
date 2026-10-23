# v11 本地渲染小样报告

> 2026-10-23更新：本页为旧版技术试跑记录，画面模糊已被用户指出。清晰度修正后的结果请使用[新审查入口](../dataset_texture_quality_20261023_v1/REVIEW.md)及[修正报告](../dataset_texture_quality_20261023_v1/REPORT.md)。旧耗时、显存和体积仅为旧策略历史数据。

生成时间：2026-10-22T18:24:35.050486+00:00。当前 **12/12 条成片具有成功编码校验回执且文件存在**；状态：`complete_receipt_snapshot`。未完成条目保留原状态，可重复运行更新。

耗时主要取准备回执、MRQ提交到结束时间、编码回执；续跑覆盖的driver_attempt不作为原始总耗时。成片校验结论来自已有全解码回执，本次报告只核对文件存在与当前作业规格，不重新解码或哈希。

## 每条作业

|节点|性别/方向|状态|场景复用|准备s|MRQ实际s|编码s|阶段合计s|PNG数|原始GiB|MP4 MiB|PIE网格|
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
|0|female/landscape|media_success|False|20.64|46.85|4.49|75.21|300|0.99|24.9|missing|
|1|female/landscape|media_success|True|15.50|21.30|4.63|43.71|300|0.92|20.0|matching_expected_visible_meshes|
|2|female/landscape|media_success|True|16.42|22.07|5.64|46.55|300|1.01|30.4|matching_expected_visible_meshes|
|5|female/landscape|media_success|True|15.61|21.96|4.81|44.61|300|0.92|20.3|matching_expected_visible_meshes|
|18|female/landscape|media_success|True|24.20|22.80|5.24|54.67|300|0.92|20.4|matching_expected_visible_meshes|
|3775|female/portrait|media_success|True|25.05|23.62|4.91|55.86|300|0.83|18.5|matching_expected_visible_meshes|
|3792|female/portrait|media_success|True|16.91|21.08|4.47|44.65|300|0.83|18.4|matching_expected_visible_meshes|
|967|male/landscape|media_success|False|27.92|29.27|4.26|64.44|300|1.07|22.7|matching_expected_visible_meshes|
|978|male/landscape|media_success|True|6.70|26.28|4.63|40.11|300|1.07|22.8|matching_expected_visible_meshes|
|979|male/landscape|media_success|True|8.84|15.49|4.35|31.13|300|1.07|22.8|matching_expected_visible_meshes|
|4040|male/portrait|media_success|False|19.12|39.27|4.53|66.49|300|0.92|16.9|matching_expected_visible_meshes|
|4058|male/portrait|media_success|True|12.33|17.14|4.67|36.25|300|0.92|17.1|matching_expected_visible_meshes|

成功样本覆盖：{"sex": {"female": 7, "male": 5}, "orientation": {"landscape": 8, "portrait": 4}, "scene": {"/Game/Scenes/Synthwave_city/Level/L_showcase_synthwave_city": 7, "/Game/Scenes/Evening_Highway/Maps/demo_level": 3, "/Game/Scenes/RedDesertPack/Maps/Showcase": 2}}。

详细地图、身份/服装/发型、实际PIE组件网格、leader、可见性、所有MRQ尝试及编码字段保存在 `PILOT_REPORT.json`。PIE网格一致不代表画面、动作曲线或发色已经通过人工验收。

## 准备细分与缓存

|阶段|样本数|最小s|中位数s|最大s|
|---|---:|---:|---:|---:|
|assembly_initialization|12|0.00|0.00|0.00|
|scene_load|12|0.06|0.12|14.72|
|scene_copy_cleanup|12|3.61|9.06|12.08|
|character_wardrobe_hair_motion|12|0.30|0.73|10.06|
|camera|12|0.01|0.03|2.42|
|ground_follow|12|0.12|0.14|0.19|
|sequence_and_save|12|2.25|3.45|3.81|

scene_reused=False：3条，准备耗时范围 19.12–27.92 秒。

scene_reused=True：9条，准备耗时范围 6.70–25.05 秒。

## 成对变化观察

|节点对|预期轴|实际state变化|MRQ秒|准备秒|
|---|---|---|---|---|
|0→1|camera|camera|46.85→21.30|20.64→15.50|
|0→2|action|action|46.85→22.07|20.64→16.42|
|0→5|wardrobe|wardrobe|46.85→21.96|20.64→15.61|
|5→18|identity|identity|21.96→22.80|15.61→24.20|
|967→978|hair_color|hair_color|29.27→26.28|27.92→6.70|
|967→979|hair|hair|29.27→15.49|27.92→8.84|
|3775→3792|hair|hair|23.62→21.08|25.05→16.91|
|4040→4058|hair_color|hair_color|39.27→17.14|19.12→12.33|

这些是数据状态的成对变化，不是严格单变量硬件基准。场景缓存、材质/着色器首次加载、运行顺序不同；不能将两条耗时差直接归因为某个编辑轴。

## 中断恢复

记录 `train_node_000967` 在 192 帧时停止外部驱动，UE未停止。当前帧数 300，停止后完成渲染：True；resume_render日志 1条，成片成功：True。

完整证据链成立：**True**。

## GPU采样

180个采样点，覆盖 6.4分钟；采样峰值显存 10734MiB、GPU利用率 100%、功率 129.3W。采样不是全程覆盖，也不保证捕获瞬时峰值。

## 失败与修复证据

保留 8条历史失败/错误证据。详细错误、来源与之后是否已有成功成片见JSON。失败后成功可以证明恢复，不能单凭报告推断具体代码修复。

- train_node_000000 / appearance_selection_validation：ValueError: 外观所用角色、服装、发色或表情目录已变化，请重新选择。；后续成功恢复：True（main_media_success）。
- train_node_000000 / temporary_actor_label_guard：ValueError: 只允许修改拍摄点专用临时角色。；后续成功恢复：True（main_media_success）。
- 未绑定作业 / editor_discovery：Need one editor for ['datatry_02']; found 0. Use --node-id if ambiguous.；后续成功恢复：False（not_proven）。
- ref_identity_train_node_000000_front / remote_exception：Exception: SkeletalMeshActor: Internal Error - ObjectInstance is null!；后续成功恢复：True（reference_png_render_success）。
- ref_scene_train_node_000000 / remote_exception：RuntimeError: Resolve unsaved packages before switching to a reference stage: ['/Game/DataMake/Characters/Revisions/CFD40_20261019_v1/CFD40_WM_001/MaterialWitnessInteractive/Materials/character/Lash_Thick36_Transparency_Pbr_LWHQ_Inst', '/Game/DataMake/Characte；后续成功恢复：True（reference_png_render_success）。
- ref_scene_train_node_000000 / remote_exception：ValueError: Saved main frame-zero camera differs from its prepared receipt；后续成功恢复：True（reference_png_render_success）。
- train_node_000000 / owned_map_save：RuntimeError: Cannot save owned map；后续成功恢复：True（main_media_success）。
- ref_identity_train_node_000000_front / remote_exception：AttributeError: 'SkeletalMeshComponent' object has no attribute 'get_component_transform'；后续成功恢复：True（reference_png_render_success）。

参考PNG的历史错误单独查询其成功渲染回执判断恢复；参考任务不计入上面的12条主视频成功数。正在重渲染的参考原型仍需以最新图片和回执验收，历史恢复记录不代表新版本已接受。

编码兼容修复有独立离线验证记录：UE输出可为RGBA PNG，编码先丢弃alpha再做BT.709有限范围转换。原始帧与成片保留，具体输入通道和策略写入媒体回执；此项不等同于完整画面验收。

## 数据规模情景范围

7203条主视频 + 809条动作参考，共8012条。按已成功的同场景复用样本阶段合计，单机串行约 **69.3–124.3小时**。

此范围只作本地负载情景估算：剔除首次场景加载样本；首次着色器/引擎启动未单独测量，额外成本未计入，也未包含轮询/传输间隔。服务器GPU、Linux和插件不同，不能直接套用本地速度；动作参考若采用不同负载也不适用。

- 保留全部原始PNG按样本大小外推：6638.1–8554.2GiB；非精确存储承诺。
- MP4按样本大小外推：132.1–238.1GiB；非精确存储承诺。

重跑：`python 00_engine/scripts/dataset/report_render_pilot_v11.py --run-root "D:\UE\Lance_Work\00_engine\outputs\dataset_render_pilot_20261023_v1"`。
