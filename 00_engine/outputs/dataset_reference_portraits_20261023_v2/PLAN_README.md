# 身份双发型参考离线计划

原配置图、主作业、原参考清单保持。本目录现已完成6张小样，其余媒体尚未全量生成，见[当前样图](REVIEW.html)与[执行报告](REPORT.md)。

- 总任务2458：静态1649（其中身份80，对应40人），动作809；载体2120。
- 每人两种不同既有发型，统一正式白色silver_white。女性复用Large bun／Top knot long ponytail，男性复用Back-swept Top／Top knot samurai；不要求人物之间发型组合唯一。仅依据目录标签选择低遮脸候选，最终遮挡与构图待小样确认。
- 身份任务garments_present=false、framing_policy=tight_face_no_neck_or_shoulders；头发任务garments_present=false，保持原黑色、两个载体和相机。渲染器需消费这些字段。
- reference_bindings.json的reference_links逐项保留原来源；训练消费effective_reference_links，每条身份边只选一图，记录selection_seed和原reference_ids。非身份链接逐项保持。identity_reference_pools把原逻辑需求ID映射到两图，第一图沿用原ID，第二图稳定派生。
- portrait_pilot_jobs.json含两位人物各两图，以及旧小样同一载体同款头发前后图。carrier_jobs.json在本目录，静态与动作任务source_jobs_path均相对本目录。

当前参考默认执行目录已指向本版。重现6图（已完成图会续用）：

```text
python 00_engine/scripts/unreal/run_dataset_render_v11.py --worker-module ue_dataset_reference_v11 --run-root 00_engine/outputs/dataset_reference_portraits_20261023_v2 --jobs 00_engine/outputs/dataset_reference_portraits_20261023_v2/portrait_pilot_jobs.json
```

全量执行时将最后文件名换为reference_jobs.json；本轮尚未启动全量任务。上传前需以本目录重新生成迁移清单。
- 动作809项只使用原要求的组合和原production10资产。男女固定载体的身份、服装、鞋、发型及颜色以当前[motion_carriers.json](motion_carriers.json)为唯一配置依据，不在本页硬编码资产组合。相机取对应既有orientation-specific binding，phase0、rate1，禁止再次慢放、循环或补hold。

重建时必须选择尚无计划的新输出目录，命令：

```powershell
python 00_engine/scripts/dataset/reference_plan_v11.py --identity-portrait-variants --motion-carriers 00_engine/outputs/dataset_reference_portraits_20261023_v2/motion_carriers.json --out 00_engine/outputs/dataset_reference_portraits_20261023_v2_rebuild
```
