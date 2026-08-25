# Reference：稳定术语与路径

> 文档 ID：`REFERENCE-INDEX`
> 文档类型：`reference_index`
> 生命周期：`current`
> 权威范围：稳定术语、ID 含义、路径别名和跨机器引用边界
> 最近核验：2026-08-25

## 1. 子系统职责

Reference 只负责回答两类不随单次运行变化的问题：

1. 一个项目术语、ID 类型或状态词是什么意思；
2. 文档中的路径别名映射到哪里，以及哪些路径可以写入可迁移清单。

Reference 不负责执行顺序、实现命令、当前进度、未来计划、验证结果或机器 Registry 内容。对应问题分别回到 Workflow、Technical、Status、Plan、Validation 或独立的 Registry 子系统。

## 2. 文档索引

| 文档 | 何时使用 | 不负责什么 |
| --- | --- |
| [术语表](./GLOSSARY.md) | 不熟悉项目名词、稳定 ID、生命周期或结果状态时 | 不保存当前对象的实际状态 |
| [路径别名](./PATH_ALIASES.md) | 把 `%...%` 映射到本机目录，或准备跨机器迁移时 | 不声明某个输出是否已验收或可删除 |

机器配置的反向查询由独立的 [Registry 子系统](../registry/README.md) 负责。

## 3. 查询顺序

1. 不懂词义或状态词：查 [术语表](./GLOSSARY.md)。
2. 不懂 `%...%`、外部目录或 URI：查 [路径别名](./PATH_ALIASES.md)。
3. 已知资产/配置名但不知道机器权威：查 [Registry](../registry/README.md)。
4. 已知当前要做的阶段：不要从 Reference 开始，直接从 [Master](../README.md)、[项目状态](../project_management/status/PROJECT_STATUS.md) 和对应 [Workflow](../workflow/README.md) 进入。

## 4. 独立维护契约

- 新增稳定术语时，必须在术语表中给出唯一含义，不能只在某份状态或计划中临时解释。
- 新增文档路径别名或外部根目录时，必须记录所有权、写入边界和跨机器表达方式。
- 动态数量、当前通过状态、运行时间戳和资产版本不得写入 Reference 作为第二份真相。
- 本目录的所有当前文件必须出现在本索引；Registry 不计入 Reference 文件清单。
