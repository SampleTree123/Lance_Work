# 发型统一构图与简单灰衣物小样

当前2458项参考计划保持：1649静态（含80身份图、112发型图）与809动作。本轮完成男女各正背面共4图的当前worker签名、载体哈希、成功MRQ来源及PNG完整结构／解压检查回执核验；[当前画廊](REVIEW.md)等待用户确认。不能推断其余发型或全部媒体已接受。

男女相同头部相对相机参数：中心Z+3cm、距离110cm、水平FOV28°、1024方图，正背面仅方向对应变化。目标为展示大部分发型（含多数长发），不要求最长发型完整入镜。固定简单衣物覆盖入镜身体，拍摄副本中统一灰色；源服装几何和源材质不改写。具体衣物以[hair_carrier_clothing.json](hair_carrier_clothing.json)为准。签名shared_hair_framing_version=1使旧发型构图失效，其他类别保持续跑兼容。

身份80图、原ID、原始及有效绑定、发型双载体组、809动作与v2保持，详见[离线检查](OFFLINE_VALIDATION.json)；身份双白发紧脸小样继续由[v2审查](../dataset_reference_portraits_20261023_v2/REVIEW.html)提供。v2发型图和前轮任务数字保留历史，本v3为当前发型入口。此前4动作及背景、衬衫、鞋、配件共8项沿用用户接受：[原样片](../dataset_reference_production_20261023_v1/REVIEW.html)。

主会话报告16驱动＋6计划＋5小样测试，共27项通过。本收尾仅检查4图回执链，不重复测试、不重审配置图、不扫描大资源树、不操作UE。精确结果见[EXECUTION_RESULT.json](EXECUTION_RESULT.json)，重建命令见[PLAN_README.md](PLAN_README.md)。旧迁移清单不含v3，上传时需用当前--run-root重新生成；本轮不刷新约107GiB资源统计。R17继续in_progress，唯一current父计划保持；下一步人工审查4图，再继续其余参考及Linux同节点／资源核验。
