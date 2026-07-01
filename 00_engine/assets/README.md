# assets —— 引擎资产入口

> 父层：[`../README.md`](../README.md)。

本目录记录会进入 UE 合成画面的角色、服装、动作、场景、道具和配饰。当前阶段尚未建立资产台账；原型资产可以用于内部管线验证，但必须明确标记 `prototype-only`。

## 约定

- 原始资产包、大型贴图、压缩包、下载缓存不进 Git。
- 每个可能进入训练/发布数据的资产必须记录来源、许可证、NoAI 状态、训练权、再分发权和取证日期。
- 许可证策略见 [`../../20_planning/compliance/licensing_compliance.md`](../../20_planning/compliance/licensing_compliance.md)。
- 资产形态与数据设计的关系见 [`../../20_planning/data_design/README.md`](../../20_planning/data_design/README.md)。

## Agent 备忘

- 不要把 `prototype-only` 资产误写成可训练或可发布。
- 真正引入资产时先建台账，再写下载/转换步骤。
