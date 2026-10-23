# GitHub同步前审查

> 文档 ID：`STATUS-GITHUB-SYNC-REVIEW`
> 文档类型：`status`
> 生命周期：`current`
> 状态来源：2026-10-23工作区差异、GitHub仓库API、测试及推送dry-run
> 最近核验：2026-10-23，Asia/Singapore

## 结论与上传状态

2026-10-23已按用户批准范围完成上传。内容提交[`e0dd61c`](https://github.com/SampleTree123/Lance_Work/commit/e0dd61cacecdc6e27ec3a74621f7549bfd42ff0f)已正常推送至main，远端读取确认一致；共338个文件变更，包含历史路径迁移。登录节点HTTPS认证及遗留LFS钩子问题均已解决，无需用户新增密钥。下面保留范围与验证记录，本页后续提交只补记同步结果。

1. GitHub目标`SampleTree123/Lance_Work`当前为public。候选包含8份UE引擎源码patch的两套副本，共16文件；其中两份各有162/121行原始上下文或删除行，不能按普通自有脚本默认公开。用户已确认保持当前仓库公开，排除这16份patch，仅保留说明/哈希与服务器原件；两处精确路径已写入根.gitignore。本轮不改变仓库可见性、不删patch。
2. 原HTTPS认证返回Invalid username or token；现有专用SSH身份King-Wood-Shen也无目标仓库写权限。用户随后在orion-login01配置HTTPS令牌与4小时credential-cache，现已验证成功；计算节点8FS9B74不能直接使用登录节点的内存缓存，因此通过已有集群SSH在登录节点执行Git。没有打印、复制或写入任何令牌。
3. push被遗留Git LFS pre-push钩子拦截，而PATH中没有git-lfs。核对全部1579个本地可达Git对象、1354个当前文件路径和有效filter后，未发现LFS指针或lfs过滤规则；钩子仅含标准LFS调用。已可逆改名备份为.git/hooks/pre-push.disabled-no-lfs-20261023，其他钩子与全局LFS配置不变。若未来实际引入LFS，须先安装git-lfs并恢复相应钩子。

公开片段及对其他许可方分发的边界见[Epic EULA第5节](https://www.unrealengine.com/eula/unreal)，核对日期2026-10-23。上述是根据实际补丁内容提出的上传范围建议，不替代项目许可证审查。

## 已上传内容

- DataMake文档、状态、决策、索引和轻量证据；保持另一对话新增的模型架构记录。
- UE自有Python/shell脚本、轻量项目配置、输入hash清单、发布与恢复实现及测试。
- Lance适配脚本、配方/作业文件、测试、单一当前patch/source_lock及历史兼容记录；不上传ignored clone、模型、训练输出或数据集。
- 已记录的历史清理与迁移：旧计划移入completed_plans、阶段补丁移入legacy、旧验证输入与报告退出当前路径。不是新增删除服务器媒体。

已批准排除：根目录`chains.json`（两条数据样例）、`html.md`（临时访问命令）、独立嵌套仓库`robotdata/`，以及上述16个UE源码patch。除用户已自行删除的`robotdata/`外，其余原件均保留在服务器；同时核实用户消息中的`robodata/`拼写路径也不存在。精确排除规则已写入根.gitignore，避免再次出现时误加入Git。

提交前候选路径和哈希见[github_sync_preflight_20261023.json](../../../../../implementation/github_sync_preflight_20261023.json)。候选按本轮工作树明确列出并逐个核对后提交，没有使用`git add .`。范围与认证均已确认；清单区分仍保留的排除文件和用户已删除的目录。清单是提交前时点快照，实际上传结果以后续Git提交为准。

## 检查结果

| 检查 | 结果与边界 |
| --- | --- |
| 远端基线与上传 | 上传前fetch确认b578a02无分叉；e0dd61c正常推送成功，ls-remote确认一致 |
| 文档审计 | 通过，0错误/0警告 |
| 核心现有单元测试 | 文档22＋数据30＋UE脚本80，共132项通过 |
| Lance现有单元测试 | xks_lance环境145项通过；合计277项 |
| 当前Lance重建合同 | rebuild_lance_checkout.py --verify-only通过，官方4baeee0＋当前patch/source_lock匹配 |
| Python/JSON/shell语法 | 拟审查的Python AST、JSON解析及bash -n无错误 |
| 凭据扫描 | 对变更候选扫描常见GitHub/HF/OpenAI/AWS/Slack token、私钥、带密码URL和明文字面量密码赋值，未命中；不是完备安全证明 |
| 文件体积 | 最大候选为约1.53MB的项目SHA清单；无checkpoint/视频/UE资产大文件。两张PNG为代码结构图 |
| Git默认空白检查 | 有提示：Windows工程CRLF、patch格式/原文空白、历史Markdown换行及个别文件尾空行；不是语法失败，本轮保留冻结输入与patch原始字节，未宣称diff --check无提示 |
| 推送dry-run | orion-login01使用用户已配置的HTTPS缓存通过；Everything up-to-date；dry-run未修改远端 |
| LFS核对与修复 | 本地可达历史和当前候选无LFS指针/规则；仅备份停用遗留LFS pre-push钩子 |
| 新UE/模型端到端运行 | 未执行；旧生产引擎路径缺失仍是后续渲染问题，不是文档上传阻塞 |

## 提交与两端同步顺序

本次已冻结候选、核对另一对话新增文档并按明确路径提交，正常fast-forward推送完成，未force-push。下一步由用户在Windows保存本地未提交改动，fetch后对比本地分支与origin/main，再合并；服务器上传成功不代表两端已一致。

本地Windows接收前保留自身未提交改动，再通过Git合并。当前没有本地Windows状态，不承诺它可无冲突直接覆盖。`server_documentation_sync_20261023.json`仍是00:33的历史文档快照；后续Git提交应以提交树为准，不把旧快照hash失配误当数据损坏。
