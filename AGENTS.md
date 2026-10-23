# DataMake Codex 项目规则

## 项目范围

- 本工作空间用于多轮视频编辑模型的数据集构建。
- 不要把这里当成通用训练代码仓库。用户已于 2026-08-29 明确扩展 Lance 微调接入范围；允许在 `10_research/model_experiments/lance/` 维护 DataMake 专用数据适配器、patch、配置、测试和小规模训练验证，上游 clone 与大型 checkpoint/output 仍不进入 Git。
- 允许在本仓库维护论文笔记、外部模型验证计划和少量实验记录；这些内容服务于数据方案设计和基线判断。
- 当前主线是 Unreal Engine 引擎合成视频数据。UE第一批已发布；CoinVE真实数据已通过引用式索引接入Lance混合训练，大模型生成来源仍以规划/验收记录为准。

## 接手时先读

- 先读 `HANDOFF.md`，确认当前状态和下一步。
- 用 `README.md` 查看完整目录图和决策日志。
- 用 `00_engine/README.md` 查看引擎合成工作区。
- 用 `00_engine/scripts/README.md` 查看当前脚本导航与生命周期。
- 用 `10_research/README.md` 查看论文、外部项目和 UE harness 调研。
- 用 `10_research/model_experiments/README.md` 查看外部模型验证计划。
- 用 `20_planning/README.md` 查看讨论、实施计划和合规入口。
- 用 `20_planning/implementation/storage.md` 查看存储、环境和风险。
- 用 `20_planning/data_design/README.md` 查看核心数据模型、edit taxonomy 和多样性目标。

## 文档规则

- 项目文档默认中文；明显偏命令、配置或代码的文件可用英文。
- 文件名默认英文。
- 保持分层文档模型：顶层 `README.md` 讲全局，越往子目录越具体。
- 讨论产生稳定决策时，要更新对应正式文档和顶层决策日志，不要只留在 `20_planning/discussions/`。
- 外部事实必须带日期和范围。Unreal Engine 版本、许可证、集群策略、工具可用性等在执行前必须重新核实。

## 当前操作假设

- 2026-06-28仅有规划文档是历史状态；当前UE工程、渲染/发布流水线和Lance训练均已有实现与证据。具体成熟度从PROJECT_STATUS及各Workflow Status读取。
- 当前目录已是本地 Git 仓库，分支 `main`。开始写脚本或做大改前先看 `git status --short`，确认没有意外大文件或无关改动。
- 大型生成数据、Unreal 缓存、引擎安装、数据集、模型文件和凭据不要提交进 Git；本项目用 `.gitignore` 排除这些路径。
- 管理员已确认不能使用 `/local`。当前阶段 UE、DDC、MVP 工程、外部模型验证权重/cache 和少量输出都放在当前 DataMake 目录下，按 `20_planning/implementation/storage.md` 执行。
- UE 安装、DDC、工程和渲染输出放在 `00_engine/` 下。
- 外部模型代码、权重和验证输出放在 `10_research/model_experiments/` 下；Lance 当前使用用户已配置的 scratch 全局 HF cache `/scratch/prj0000000275/jcy/.cache/huggingface`，不要落回默认小 home。
- 文档中的当前 Unreal 目标是 UE 5.8，来自 2026-06-19 规划。UE 5.6 相关备忘录视为历史调研，除非用户明确要钉死 5.6。
- Lance当前源码基线/补丁合同从`10_research/model_experiments/lance/patches/current/source_lock.json`读取；旧9717d91走读、batch8和“等待WF-90发布”是历史阶段，不作为当前运行状态。
- 2026-10-23起模型架构讨论与同步/UE执行分工并行。接手本地/服务器同步和UE渲染时先读`SERVER_SYNC_STATUS.md`，不覆盖另一对话的模型决定。历史生产兼容引擎原路径缺失，下一次渲染先核验实际构建，不能把工作区Installed Build默认当替代。

## 工程优先级

- 始终保护核心不变量：配置图、确定性节点渲染、原子编辑边、端点复用。
- 第一个 MVP 优先选择低风险确定性编辑：E8 光照、E5 道具可见性、E6 配饰可见性或 E11 表情。E2 服装和 E1 身份放在基础闭环之后。
- 当前盘是 `/scratch` 网络盘，小文件 I/O 可能慢。接受该限制，先控制规模完成 MVP；不要在这里直接启动正式大规模生产。
- 不预建空目录。只有具体工作流需要时才创建文件和文件夹；为说明长期目录职责而放置的 README 可以保留。
- 后续写脚本时，metadata/sidecar 是一等输出，不是事后补丁。
- UE harness 采用官方 UE Python + Automation Test Framework + MRQ/MRG 自建薄脚本；第三方 Unreal MCP/agent 工具只能作为编辑器辅助或原型探索，不作为批量数据生产核心依赖。
- 外部模型验证优先记录失败模式对数据需求的反推，不要把工作扩成完整 benchmark 平台。

## 安全与合规

- `prototype-only` 资产可以服务内部管线测试，但必须明确标记，不能误入可发布或训练数据。
- 可发布数据必须有资产台账：来源、许可证、NoAI 状态、训练权、再分发权、取证日期。
- 本仓库里的许可证说明只是规划指导，不是法律意见。
