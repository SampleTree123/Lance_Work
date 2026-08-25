# 术语表

> 文档角色：`glossary`
> 上级入口：[`README.md`](./README.md)
> 最近核验：2026-08-06

| 术语 | 本项目含义 |
| --- | --- |
| BodyFit | 一个 hash 锁定的成人身体源 `.ccProject`，含完整身体比例，不等于单个 Morph |
| Body/Junction | 身体和头身连接相关 Morph 域，用于确认脸部流程没有污染身体 |
| Head Scale | CC UI 中校准头部整体比例的参数；当前按 BodyFit 固定 |
| Neck Height | CC UI 中校准颈长的参数；只在部分 BodyFit 非零 |
| Face seed | 一套可加载的完整面部身份状态，而不是几项 Morph 数值 |
| Primary seed | 可作为生产配方基础的完整同性交付面部原型 |
| Facial Profile | CC 的面部骨骼、表情和支撑配置；需与主 seed 成对保存和应用 |
| Local Morph | 在主 seed 之上允许修改的少量安全局部面部参数 |
| Face recipe | `primary_face_seed_id + local_morphs` 等确定性身份配方 |
| Full Face Elder | 当前使用的面部年龄 Morph 名；0/0.5/1 只是三档变体，不是精确年龄 |
| Appearance recipe | 皮肤、眼眉睫、牙齿、毛发、色素和质量档案的登记组合 |
| Registry | 机器可读的资产、顺序、策略和状态总登记，不是人工描述文档 |
| Manifest | 将请求解析为具体 BodyFit、Face、Appearance 和 QA 步骤的确定性执行文件 |
| Preset | manifest 内可单独执行的一条角色或验证配置；不是 CC UI 里所有“预设”的泛称 |
| Artifact | 一次运行留下的 request、manifest、result、报告、截图和日志证据 |
| Technical specification | 描述数据模型、算法、约束和长期规则的技术文档；必须链接实现，但不必复制整段源码 |
| Runbook | 可按步骤复现任务的操作文档；必须给出执行环境、入口、命令、输入输出、通过条件和恢复方式 |
| Bridge | 系统 Python 与 CC/RLPy 之间的受控离线文件队列 |
| Heartbeat | CC Bridge 插件周期写出的存活状态；配置存在不等于 heartbeat 新鲜 |
| Lease | 防止多个 worker 同时处理队列的短时所有权记录 |
| UE Remote Execution | UE Python 插件提供的远程脚本通道；系统 Python 发现已运行 UE 节点并提交 `unreal` 脚本，不等于 Unreal MCP |
| Unreal MCP | Agent 调用 UE 工具集的 MCP 通道；只有编辑器插件和本地服务实际监听时才在线 |
| Vendor | UE 中保留外部导入资产和原路径的内容层 |
| DataMake | UE 中本项目自有的地图入口、角色 Blueprint、派生动画和配置层 |
| Leader Pose | 多 Skeletal Mesh Component 由 Body 的骨骼姿态驱动的 UE 机制 |
| Follower | 使用 Body Leader Pose 的拆分网格组件 |
| Morph Target | UE 中按权重施加的顶点差值；只能安全用于同拓扑和正确 Vertex ID |
| Animation curve | AnimSequence 中驱动 Morph/Rig Logic 等值的时间曲线 |
| Body-only | 已移除面部轨道、可与批准面部片段重组的身体动画 |
| Face-only | 只包含面部曲线或面部支撑骨骼的动画片段 |
| Hybrid face clip | 同时包含面部曲线和下颌/牙齿/舌头等支撑骨骼的片段 |
| Full performance | 身体和面部已经构成完整表演，应登记为 paired/locked 而非随机重组 |
| Look | 一套具有槽位、层级、互斥、隐藏和动作约束的完整服装组合 |
| Pilot | 在明确对象和边界内验证成功，尚不能直接推广到全部角色的实现 |
| MRQ | Unreal Movie Render Queue，用于最终视频和图像渲染 |
| GT | Ground Truth，合成数据的深度、分割、关键点等真值输出 |
