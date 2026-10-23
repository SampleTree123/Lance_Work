# 参考素材原型（布置尚未冻结）

交付6个可串行执行的原型任务，位于 `reference_pilot_jobs.json`。它们没有修改既有 `reference_manifest.json`，也不表示正式参考素材已生成。主会话负责实际 UE 执行；各项技术成功与实际图片以其 job 回执为准。

1. `ref_scene_train_node_000000`：主节点0的横屏背景，1920×1080。
2. `ref_garment_train_node_000000_front`：主节点0实际穿着的白色蕾丝裙单件，正面1024×1024。
3. `ref_scene_train_node_003775`：主节点3775的竖屏背景，1080×1920；先完成该主节点的 prepare。
4. `ref_identity_train_node_000000_front`：源节点0的 `CFD40_AF_004` 正脸近景，1024×1024。
5. `ref_hair_train_node_000000_front`：同源节点发型 `HAIR_HB2_19`，固定黑色，完整发型正面，1024×1024。
6. `ref_hair_train_node_000000_back`：同一黑色发型背面，1024×1024。

每项输出只有一张 PNG，`jobs/<ref_job_id>/frames/frame_0000.png`。不要交给固定300帧的视频编码器；原型PNG应直接保留。

## 由主会话串行执行

脚本 `00_engine/scripts/unreal/ue_dataset_reference_pilot_v11.py` 导入时不操作 UE。调用独立 `dispatch(request)`：

```python
import ue_dataset_reference_pilot_v11 as reference

request = {
    "action": "prepare",
    "run_root": "D:/UE/Lance_Work/00_engine/outputs/dataset_render_pilot_20261023_v1",
    "jobs_path": "reference_pilot_jobs.json",
    "job_id": "ref_scene_train_node_000000",
}
prepared = reference.dispatch(request)
# prepare 成功后，由主会话确认当前没有其他渲染再提交。
request["action"] = "render"
submitted = reference.dispatch(request)
# 另一次调用读取异步结果，不自动启动后续任务。
status = reference.dispatch({"action": "status", "run_root": request["run_root"]})
```

`pool_mb` 可传给 render，沿用主渲染器的实际本机预算。背景/单件都会用1帧 sequence，30fps display rate；MRQ 的 warmup 不增加输出帧数。参考渲染有独立的会话 receipt 状态，但仍检查全局 MRQ 是否正在运行。

出现与本 Run 无关的未保存地图时脚本会报出列表，不自行保存原工程状态；加载源材质产生的编辑器升级 dirtiness 不触发源材质保存。所有新资产在 `/Game/DataMake/Capture/DatasetPilot20261023/ReferencePilot/` 下使用新名字。失败可重新 prepare，不覆盖旧源资产。

## 背景相机和人物移除

必须先有相应主节点的 `prepared.json`、保存的主 map/sequence；脚本核对其签名与原主 job 一致。相机从**已保存主 sequence 的第0帧 transform/FOV key**直接读取，并与主 prepared 的首相机数据核对，不用近似镜头或临时 plan 冒充。

顺序固定为加载主 owned map → SaveMap 到新的 reference copy → **显式加载 copy** → 删除 copy 中的主角色与独立睫毛/跟随者、旧 LevelSequenceActor → 保留复制过来的主相机及其相机设置 → 构造第0帧相机恒定的1帧 sequence。不会只隐藏主角色后留下阴影投射。

主 map/sequence 文件在操作前后验证 SHA256，记录在参考 prepared 回执中。背景仍继承原场景设置；动态场景、曝光适应、Lumen更新的画面一致性必须查看实际PNG，不能据此宣称主视频首帧背景逐像素相同。

## 单件服装原型

使用**新建空 owned map**。只从主节点已经选择的一个 garment asset 读取其全部 `mesh_paths`，逐个创建独立 SkeletalMeshActor；不创建人体、头发、眼睛、睫毛或主完整 slot actor，也不裁剪完整人物截图。准备结束再枚举关卡中所有 SkeletalMeshComponent，必须恰好只有该单件的那些 mesh。

这版使用导入的 skeletal reference pose、无身体动作、关闭刚体物理，按全部实际 mesh 包围框自动取正面完整视图。CC 原始参考姿态正面为 **+Y**：front 相机位于 +Y、yaw=-90°，back 位于 -Y、yaw=+90°。背景是新建的灰色材质球，方向光/补光和固定曝光仅为**未接受的原型布置**。没有展平衣服、修改顶点或修改源材质。

需要在实际PNG检查衣服是否完整、材质是否正常、反面/内衬是否需要展示、参考姿态是否合适、有无衣服资产自身嵌入的人体几何。自动包围框取景与这组灯光尚未冻结为正式 reference 方案；多视角、遮挡、鞋和配饰另行定义。

## 正脸与发型新增原型

独立空 owned stage 复用当前40人 `pair.worker()`、正式38-slot模板与 `main.selection(source,current)`，用当前人物目录应用外观，再将睫毛转为可保存的永久跟随者。新增分支不使用旧人体carrier，也不改变源节点state或主视频。

身体采用已有静止 `None` / imported reference pose，不播放动作；face 为 none。人物朝向固定为 native CC 的 +Y，actor yaw=0。identity 对准 head socket 的面部近景，沿用源节点原发色；hair 使用同一目标发型与人物，发色固定black，分别保存前/后两张PNG。

hair 取景读取全部已加载 HairPart 的 **mesh自身参考包围框**，将其角点按实际组件变换转到世界，再与头部范围合并。不会读取继承了Body范围的hair component bounds而把整个人缩小。它是保守的参考姿态包围框，不是逐顶点轮廓或发型可见性证明；长发、服装/配饰遮挡、黑发细节和脸部大小仍须看实际PNG。

## v2 修正及尚未覆盖

初版 garment front 的 +X相机实际拍到侧面，原图保留为已取代的原型，不再作为正面接受依据。VERSION=2改为 +Y正面 / -Y背面，prepare会生成新owned资产；新图仍需重新渲染。neutral manual exposure bias从0降至-1EV以减轻白裙过曝，未同时降低灯强，后续由实际画面确定布置。

动作视频 reference 这轮暂不实现，专用载体尚未确定。后续必须与对应主视频使用同一已有 production10 动作、30fps/300帧、10秒时钟，不能重新重复、慢放或改变动作相位；目前没有专用动作参考样片，不把主视频或静止人物图冒充专用动作reference。

离线5项 fake checks 已通过：主sequence第0帧 key读取与不一致拒绝、SaveMap后明确load copy的顺序、单件全部mesh及包围框取景、+Y/-Y与正脸/完整长发取景、hair mesh自身bounds变换。新增identity/hair分支尚待主会话实际UE渲染；离线实现者没有操作UE。详见 `REFERENCE_PILOT_OFFLINE_VALIDATION.json`。

## 2026-10-23 本地执行结果

六项已实际渲染成功，图片从[审查入口](REVIEW.md)查看。中性布光原型修正正面轴后，前后各使用20强度、240宽高的矩形补光，固定曝光-1；它们仅存在于本次独立场景，不改用户地图。当前worker版本4。服装单件无人体，身份／发型由正式40人槽位装配；展示布置仍待确认，未生成专用动作参考。原离线校验JSON是当时快照，当前实机结果以各job prepared、render_receipts及REFERENCE_LOCAL_RESULTS为准。
