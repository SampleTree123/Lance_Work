# 身份双发型参考离线计划

本轮只写新目录；原配置图、主作业、原参考清单及旧运行不改写。计划生成阶段未生成媒体；后续已完成4张样图，见[当前结果](REPORT.md)。

- 总任务2458：静态1649（其中身份80，对应40人），动作809；载体2120。
- 每人两种不同既有发型，统一正式白色silver_white。女性复用Large bun／Top knot long ponytail，男性复用Back-swept Top／Top knot samurai；不要求人物之间发型组合唯一。仅依据目录标签选择低遮脸候选，最终遮挡与构图待小样确认。
- 身份任务garments_present=false、framing_policy=tight_face_no_neck_or_shoulders；头发任务采用下方v4自适应构图，保持原黑色与两个载体。渲染器需消费这些字段。
- reference_bindings.json的reference_links逐项保留原来源；训练消费effective_reference_links，每条身份边只选一图，记录selection_seed和原reference_ids。非身份链接逐项保持。identity_reference_pools把原逻辑需求ID映射到两图，第一图沿用原ID，第二图稳定派生。
- portrait_pilot_jobs.json含两位人物各两图，以及旧小样同一载体同款头发前后图。carrier_jobs.json在本目录，静态与动作任务source_jobs_path均相对本目录。
- 动作809项只使用原要求的组合和原production10资产。男女固定载体的身份、服装、鞋、发型及颜色以当前[motion_carriers.json](motion_carriers.json)为唯一配置依据，不在本页硬编码资产组合。相机取对应既有orientation-specific binding，phase0、rate1，禁止再次慢放、循环或补hold。

重建时必须选择尚无计划的新输出目录，命令：

```powershell
python 00_engine/scripts/dataset/reference_plan_v11.py --identity-portrait-variants --motion-carriers 00_engine/outputs/dataset_reference_portraits_20261023_v2/motion_carriers.json --out 00_engine/outputs/dataset_reference_portraits_20261023_v2_rebuild
```

## v4 发型自适应完整取景

112发型任务framing_policy=adaptive_complete_hair、garments_present=true、neutral_garment_color=true。相机以实际头发边界和紧凑头部代理自适应：短发靠近头部，长发后退保证完整，FOV28°、边距1.12，不设100cm距离下限；简单灰衣物延续v3合法配置。身份80图、809动作、所有参考ID与链接保持。hair_framing_pilot_jobs.json含男女各前后共4图，已渲染完成，见[审查页](REVIEW.html)。

```powershell
python 00_engine/scripts/dataset/reference_plan_v11.py --identity-portrait-variants --adaptive-hair-framing --hair-carrier-clothing 00_engine/outputs/dataset_reference_hair_adaptive_20261023_v4/hair_carrier_clothing.json --motion-carriers 00_engine/outputs/dataset_reference_hair_adaptive_20261023_v4/motion_carriers.json --out 00_engine/outputs/dataset_reference_hair_adaptive_20261023_v4_rebuild
```
