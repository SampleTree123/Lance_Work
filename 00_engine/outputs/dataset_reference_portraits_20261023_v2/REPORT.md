# 身份双发型与去服装参考小样

当前全量计划为2458项：1649静态图（含40人各两种白发、共80身份图）与809动作视频。本轮实际核验的是4张身份图和2张同载体黑发图；6图当前worker签名、载体哈希、成功MRQ来源、PNG哈希及完整结构／解压检查回执通过，仍待[人工审查](REVIEW.md)。不能推断40人全部构图已验收，也没有服务器或全库媒体验证。

用户已接受上轮除身份、发型以外的样片：4动作视频及背景、衬衫、鞋子、配件。它们继续使用[旧运行报告](../dataset_reference_production_20261023_v1/REPORT.md)和[原画廊](../dataset_reference_production_20261023_v1/REVIEW.html)，原报告中的11项／2418任务是当时历史状态，保留不回写；本轮新参考入口以此目录为准。上轮身份、发型已由当前方案替代，尚未接受本轮新图。

身份图统一正式白色silver_white，每人两种不同既有发型，允许多个人物复用同一组合；通过固定头部锚点收紧脸部构图，不刻意展示脖子或肩膀，为保全下巴轮廓可留极细下缘，外围头发可以裁切。身份及头发任务garments_present=false，拍摄时隐藏衣物而保留载体原穿搭来源；头发图仍用原黑色、原两个载体和既定相机，本小样只核对其中同一载体前后两图。

## 全量绑定与复现入口

reference_jobs.json／static_reference_jobs.json／motion_reference_jobs.json及carrier_jobs.json为本轮入口，新增40个身份参考ID，不新增或更改已采用图节点、边、链和主任务。每个原身份需求作为逻辑池保留，第一图沿用原ID，第二图稳定派生；identity_reference_pools.json列出40个两图池。reference_bindings.json的reference_links保留原来源；实际使用effective_reference_links，每条身份编辑步骤只选一图，记录selection_seed、原reference_ids和选中ID。非身份链接、28发型双载体组和809动作任务保持。完整发型前后图仍作为一组选择载体。

离线直接核验见[OFFLINE_VALIDATION.json](OFFLINE_VALIDATION.json)，发型目录及既有来源证据见[IDENTITY_HAIR_SELECTION.json](IDENTITY_HAIR_SELECTION.json)，生成命令见[PLAN_README.md](PLAN_README.md)。主会话报告16项驱动＋5项计划＋5项小样实现测试，共26项通过；本收尾脚本不重复运行测试，不扩展全库审计。精确6图回执见[EXECUTION_RESULT.json](EXECUTION_RESULT.json)。当前Run其余2452项未由本脚本核验；已接受旧8项另按原来源引用，未计作本Run新渲染。

当前驱动的默认参考运行目录已切换到本v2。旧v1迁移清单不包含本目录，不能作为当前上传清单；实际上传时需以本目录的--run-root重新生成清单，本轮延后资源大目录统计刷新，不重复扫描约107GiB素材。

本Technical所有者为DATASET_DESIGN_EXPLORATION_20261021.md；finalize_portraits.py仅为该Run有界prototype收尾，不操作UE、不改任务、不清理媒体。R17继续in_progress，唯一current父计划及其他分支保持；下一步审查本轮6图，再按授权生成其余参考及进行Linux同节点／资源核验。

## 女性长发补充展示

用户要求检查长发画幅，另渲染HAIR_HB2_04／CFD40_LF_003正反面2图，沿用现有黑色、去服装及实际发型边界取景规则，没有针对该例改相机参数。两图输出回执成功；查看背面可见头顶和发尾均在画内并有余量，正面长发自然被躯干遮挡。本例不等于全部长发已逐款验收。见LONG_HAIR_REVIEW.json及画廊补充部分；先前6图报告保持原范围。
