# ADR-0009：Bridge 使用受控离线文件队列

> 文档 ID：`ADR-0009`
> 状态：`accepted`
> 文档类型：`adr`
> 生命周期：`current`
> 适用阶段：`WF-00/WF-30`
> 权威范围：受控离线 Bridge 与安全边界决定
> 上级入口：[`README.md`](./README.md)
> 上游：离线许可证和自动化验证
> 下游：Bridge 规范和 CC Workflow
> 最近核验：2026-08-06
> 日期：2026-07-28

## 背景

CC 的 RLPy 只存在于应用内 Python，系统 Python 无法直接导入。离线许可证又要求避免 Agent 任意重启或联网操作。

## 决定

系统 Python 只生成配置和队列请求；CC 插件轮询受控目录并执行 allowlist 命令。Bridge 不接受任意 Python、任意路径或网络命令，使用 heartbeat、lease、1 MiB 请求上限和原子文件移动。

## 影响

- Agent 可稳定提交有限工作并读取结果。
- CC 启动和重启仍由用户在离线条件完成。
- 新能力需要扩展协议和插件，而不是把脚本字符串放进请求。
- 当前 `apply-face` 仅兼容旧 schema，完整 Face V3 使用兼容 manifest 执行路径。

## 复审条件

CC 提供正式受支持的远程自动化接口、离线启动约束改变，或文件队列无法满足幂等性与安全边界时复审。
