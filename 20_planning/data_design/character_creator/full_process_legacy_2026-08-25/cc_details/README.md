# Character Creator 领域规范

> 文档角色：`subsystem_index`
> 状态：`current`
> 适用阶段：`WF-01..WF-04`
> 权威范围：CC 身体、面部和外观规则的目录导航
> 上级入口：[`../CHARACTER_FACTORY_MASTER_SPEC.md`](../CHARACTER_FACTORY_MASTER_SPEC.md)
> 上游：机器 JSON 与 CC 资产库
> 下游：本目录领域文档
> 最近核验：2026-08-08

日常生产不从本目录拼接流程，应走 [`workflow/README.md`](../workflow/README.md)。只有需要理解约束、诊断或扩展资产池时进入这里。

| 文档 | 何时阅读 | 权威内容 |
| --- | --- | --- |
| [`BODYFIT_PIPELINE.md`](./BODYFIT_PIPELINE.md) | 选择、修改或新增 BodyFit | 十体型、源哈希、Head/Neck 比例和身体不变量 |
| [`FACE_IDENTITY_AND_AGE.md`](./FACE_IDENTITY_AND_AGE.md) | 生成/修改脸、年龄或 Headshot | Face V3、Facial Profile、局部 Morph 和年龄边界 |
| [`HEADSHOT_PIPELINE.md`](./HEADSHOT_PIPELINE.md) | 生成、检查、保存或晋级 Headshot 身份原型 | 输入冻结、CC5 Profile 门禁、规范原型包、哈希和 project-seed 接入契约 |
| [`APPEARANCE_PIPELINE.md`](./APPEARANCE_PIPELINE.md) | 修改皮肤、眼睛、牙齿、眉睫、胡须、头发或材质 | 审核池、应用顺序、兼容性、色素和质量档案 |
| [`OUTFIT_PIPELINE.md`](./OUTFIT_PIPELINE.md) | 盘点、筛选、适配或导出服装 | Source package、Look、层级互斥、十体型矩阵和 UE 切换边界 |
