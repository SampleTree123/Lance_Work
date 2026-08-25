# Character Factory 运行输出

本目录保存本地生产、验证、审查和诊断产物；默认被 Git 排除。目录名或文件年龄不决定保留等级，也不能据此删除。

权威规则：

- [输出契约目录](../../20_planning/data_design/character_creator/full_process/technical/output/OUTPUT_CONTRACTS.md)：`OUT-*`、存储类别和 Run Root。
- [输出盘点与保留](../../20_planning/data_design/character_creator/full_process/technical/output/INVENTORY_AND_RETENTION.md)：登记、盘点和清理前置条件。
- `RETENTION_POLICY.json`：人工审查的 owner 与保留规则。
- `OUTPUT_INVENTORY.json`：由 Builder 生成的当前盘点。

每个新运行使用唯一 `run_id`，至少保留 `manifest.json`、输入锁、结果/状态、日志和适用证据。稳定结论回写 Workflow/Batch Status；输出目录本身不是当前状态权威。

重建盘点：

```powershell
python 00_engine/scripts/documentation/build_output_inventory.py
```

`unclassified` 默认受保护。只有经过替代关系、Manifest、Status 引用和绝对路径复核的 `superseded/disposable` 项，才可进入独立审批的清理操作。
