# 全量参考入口与本轮11项执行结果

**2418项原reference ID已绑定全量执行入口；本轮实际完成并核对的是4条动作视频和7张静态图。** 当前worker签名、carrier哈希、成功MRQ回执来源与媒体哈希一致；动作成片完整解码回执通过，静态PNG结构/解压检查通过。本报告不表示2407项其余任务已执行，也不表示服务器或全库验证。

展示方案及此前清晰版12主片/6图已获用户接受；本轮新增动作载体、灰棚地面和7图仍需[人工审查](REVIEW.md)。首轮女性宽裤草稿媒体已在同一job目录中被新轮替代，保留的是日志，不能声称旧媒体仍在。当前展示读取最新motion_carriers.json，为新选择与当前worker策略，不能把旧轮回执当成新轮成功。

鞋的正面/背面取景均改为抬高25°，便于看清鞋面与立体形状；本轮共享鞋正面使用shoe_framing_version=1新签名重渲染。该签名增量仅作用于garment/shoes，其他6静态任务可按原签名续用，不作无必要重渲染。主会话已完成31项直接相关测试并全部通过；本finalizer只核验回执链，不再次执行测试。

## 当前固定动作载体

- female：CFD40_AF_001，Workout_BlueOutfit, Shoes3，HAIR_HB1_02，black。
- male：CFD40_AM_001，Top 01, Shorts 01, Shoes 01，HAIR_HB3_02，black。

动作直接复用对应已有production10资产：start0、rate1、30fps、300帧、10秒，不重新烘焙、慢放、重复或补hold。四样本覆盖男女横竖，包含front_full和orbit_120；灰背景/地面及灯光为当前reference worker实现。

## 绑定、续跑与范围

统一入口reference_jobs.json含1609静态图与809动作视频；carrier_jobs.json提供来源。scene保留原main ID/state，其余carrier为明确标识的参考组合，不新增数据图节点。原reference IDs、每步reference_links、28发型双载体完整组及既定视角保持；含单件鞋和配件，单件图无人体。完整组前后视角不能分开随机选载体。

每任务source_job_sha256绑定其carrier内容；prepare/render的当前worker版本签名随任务保存。PNG/MP4媒体回执绑定成功MRQ来源及文件SHA；缺少签名、旧版本、载体变动或媒体损坏时不得直接resume复用。原始视频帧清理后的复用仍须成功回执和成片哈希一致；本脚本不清理任何素材。

精确11项证据见EXECUTION_RESULT.json。这里只检查当前Run的11任务链，不重审候选图、不运行全库测试、不推断Linux/服务器画面和资源。R17及唯一current父计划继续；全量入口ready与全部媒体完成是不同状态。下一步审查新增11项，并按授权推进其余参考生成及Linux同节点资源/画面对照。
