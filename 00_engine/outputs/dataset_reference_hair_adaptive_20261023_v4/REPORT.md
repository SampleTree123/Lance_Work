# 发型自适应取景与简单灰衣物小样

当前2458项参考计划保持：1649静态（含80身份图、112发型图）与809动作。本轮完成男女各正背面共4图的当前worker签名、载体哈希、成功MRQ来源及PNG完整结构／解压检查回执核验；[当前画廊](REVIEW.md)等待用户确认。本次确认覆盖拍摄规则与4张样图；其余发型仍需按此规则生成。

根据实际头发边界加紧凑头部代理，自动决定取景中心和距离：短发更靠近头部，长发后退以完整入镜。统一水平FOV28°、边距1.12、1024方图，不设100cm距离下限；每图实际相机读回值存入EXECUTION_RESULT.json。固定简单衣物覆盖入镜身体，拍摄副本中统一灰色；源服装几何和源材质不改写。具体衣物以[hair_carrier_clothing.json](hair_carrier_clothing.json)为准。签名adaptive_hair_framing_version=1使旧发型构图失效，其他类别保持续跑兼容。

身份80图、原ID、原始及有效绑定、发型双载体组、809动作与v2保持，详见[离线检查](OFFLINE_VALIDATION.json)；身份双白发紧脸小样继续由[v2审查](../dataset_reference_portraits_20261023_v2/REVIEW.html)提供。v2发型图和前轮任务数字保留历史，本v4为当前发型入口；v3固定相机图保留历史。此前4动作及背景、衬衫、鞋、配件共8项沿用用户接受：[原样片](../dataset_reference_production_20261023_v1/REVIEW.html)。

主会话报告16驱动＋6计划＋5小样＋1投影测试，共28项通过。本收尾仅检查4图回执链，不重复测试、不重审配置图、不扫描大资源树、不操作UE。精确结果见[EXECUTION_RESULT.json](EXECUTION_RESULT.json)，重建命令见[PLAN_README.md](PLAN_README.md)。旧迁移清单不含v4，上传时需用当前--run-root重新生成；本轮不刷新约107GiB资源统计。R17继续in_progress，唯一current父计划保持；下一步按已确认规则继续其余参考及Linux同节点／资源核验。
