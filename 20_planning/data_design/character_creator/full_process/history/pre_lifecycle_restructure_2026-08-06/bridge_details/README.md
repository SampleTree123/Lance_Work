# CC Bridge 文档

> 文档角色：`subsystem_index`
> 上级入口：[`../CHARACTER_FACTORY_MASTER_SPEC.md`](../CHARACTER_FACTORY_MASTER_SPEC.md)
> 最近核验：2026-08-06

## 当前文档

| 文档 | 职责 |
| --- | --- |
| [`BRIDGE_OPERATIONS.md`](./BRIDGE_OPERATIONS.md) | 安装、健康检查、命令、队列、弹窗和恢复 |
| [`protocol_v1.md`](../../../../../00_engine/character_creator_bridge/protocol_v1.md) | 线协议、请求/结果结构和 lease 规则 |
| [Bridge 代码目录 README](../../../../../00_engine/character_creator_bridge/README.md) | 代码目录和组件入口 |

## 当前能力

| 能力 | 状态 |
| --- | --- |
| 文件队列、心跳、单消费者和结果保留 | `validated_pilot` |
| `ping` / `scene_summary` | `production` 级诊断入口 |
| BodyFit 和兼容 manifest 执行 | `validated_pilot` |
| 旧 target-face recipe 预览 | `historical` 兼容命令，不支持当前 Face V3 schema |
| 精确 Undo 警告守卫 | `validated_pilot` |
| 完整角色专用命令 | `planned` |
| 取消、进度查询、批量调度和自动资源治理 | `planned` |

新增 Bridge 能力时先更新能力矩阵，再修改协议、插件、客户端、测试和 Operations 文档。
