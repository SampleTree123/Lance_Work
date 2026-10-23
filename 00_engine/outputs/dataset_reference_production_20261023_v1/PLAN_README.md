# v11 全量参考任务离线计划

本计划绑定已采用 v11 的原始 reference IDs，不修改候选、节点、链或原 reference manifest。计划生成器不操作UE；实际媒体进度和接受结果以本 Run 执行回执为准。

## 文件与数量

| 文件 | 内容 |
| --- | --- |
| `carrier_jobs.json` | 2080个main-schema兼容来源：893原scene主节点、40身份、56发型载体组、282单件来源、809动作载体任务 |
| `reference_jobs.json` | 统一执行入口，2418项原始reference ID |
| `static_reference_jobs.json` | 1609图：893背景、40身份正面、112发型、564单件 |
| `motion_reference_jobs.json` | 809个动作/相机/性别/画幅组合，10秒30fps300帧 |
| `motion_pilot_jobs.json` | 4条动作真实小样候选，男女×横竖，三条front_full和一条orbit_120 |
| `reference_bindings.json` | 每原reference ID→任务/媒体路径、原始步骤绑定及完整发型载体组 |
| `motion_carriers.json` | 主会话明确冻结的男女固定动作载体selection |
| `PLAN_SUMMARY.json` | 离线计数和待执行边界 |

Scene来源保留原 `train/test_node_*` ID与完整state。其他来源用 `ref_carrier_*` 独立命名，标为 `synthetic_reference_carrier_not_an_adopted_dataset_node`；复制的node/content字段仅追溯来源，不把新组合计入数据图。静态/动作来源携带原site描述用于lineage，执行必须按reference任务的neutral stage创建灰棚；仅scene需要main.prepare，其他类型无需加载原场景。

每个reference任务含 `source_jobs_path=carrier_jobs.json`、`source_job_id` 和 `source_job_sha256`。哈希严格为 `sha256(json.dumps(carrier_job, sort_keys=True).encode())`，供worker拒绝后来变动的载体。静态图输出 `jobs/<原ref_id>/frames/frame_0000.png`；动作成片输出 `jobs/<原ref_id>/video.mp4`。

## 保留的参考语义

- 身份40张沿原 `front_face`需求，另给`render_view=front`以接入现有相机实现；原requirement key不变。
- 发型为原28发型×2个原定不同身份载体×front/back，共112图，固定black。原pool、完整组ID与每步已选组原样保留，不重新随机、不拆开选择前后载体。
- 单件为282件×front/back，共564图；其中鞋64图、family_accessory22图。每件必须加载其全部原始mesh_paths，不能用整个人物裁切替代无人体单件。
- 背景893项按原site/action/camera/sex/aspect精确匹配原main来源，实际相机应由其保存sequence首帧取得，移除人物及跟随者后渲染。
- 动作809项只使用原要求的组合和原production10资产。男女固定载体的身份、服装、鞋、发型及颜色以当前[motion_carriers.json](motion_carriers.json)为唯一配置依据，不在本页硬编码资产组合。相机取对应既有orientation-specific binding，phase0、rate1，禁止再次慢放、循环或补hold。

## 4动作小样

| 原reference ID | 性别/画幅 | 动作 | 镜头 |
| --- | --- | --- | --- |
| `ref_f752597252c97a92e70bb469` | 女横屏 | MOTION_CAND_020 | front_full |
| `ref_7454f04fb9c2b89b132899c1` | 男横屏 | MOTION_CAND_001 | front_full |
| `ref_88d4c930ae0374d3deac04b6` | 女竖屏 | ACT_M06_CHEER_HANDS_STEP_DANCE | front_full |
| `ref_babb48f602439f382fc45647` | 男竖屏 | MOTION_CAND_001 | orbit_120 |

动作小样由主会话使用 `ue_dataset_reference_v11` 串行执行；此处没有执行UE，也没有把计划写成媒体成功。

复现生成命令：

```powershell
python 00_engine/scripts/dataset/reference_plan_v11.py --motion-carriers 00_engine/outputs/dataset_reference_production_20261023_v1/motion_carriers.json
```

不提供固定动作载体配置时，809任务会明确标为blocked且没有source_job_id；不能以每个目标人物临时代替固定载体。当前这份计划已使用明确配置，blocked=0。

本轮离线定向检查覆盖原2418 IDs、视角/需求数量、完整原步骤绑定/发型pool、全部载体hash及两性固定外观。另有小fixture单元测试和300帧合成reference-ID编码/完整解码/续跑测试；合成输出只用于编码器验证，已清理，不作UE样片。没有重新审计数据图。

## 执行入口

在Lance_Work目录执行下列命令，可生成或续跑本Run全部参考任务；本轮只执行了小样，尚未启动此全量命令。

```text
python 00_engine/scripts/unreal/run_dataset_render_v11.py --worker-module ue_dataset_reference_v11 --run-root 00_engine/outputs/dataset_reference_production_20261023_v1 --jobs 00_engine/outputs/dataset_reference_production_20261023_v1/reference_jobs.json
```

将最后的文件名改为motion_pilot_jobs.json或static_pilot_jobs.json即可复现本轮小样。服务器入口还需使用既有portable-runtime路径映射配置及服务器显存预算；Linux执行尚待实际验证。

最新[迁移清单](TRANSFER_PLAN.md)已经包含本Run的载体、参考任务及绑定文件。此次仅生成清单，没有上传。
