# 本地与服务器文档同步

> 文档 ID：`TECH-DOC-SYNC`
> 文档类型：`technical`
> 生命周期：`current`
> 适用阶段：跨机器交接；UE执行前准备
> 实现所有权：文档同步范围、差异合并、服务器快照及同步清单
> 验证所有权：`VAL-DOC-01`；文件SHA-256仅验证本次快照传输一致性
> 输出契约：本页第2节的轻量同步清单；文档检查结果沿用`OUT-GLOBAL-DOC-AUDIT`
> 最近核验：2026-10-23

## 1. 入口和边界

服务器整理状态见[SERVER_SYNC_STATUS](../../project_management/status/SERVER_SYNC_STATUS.md)，跨机器路径见[PATH_ALIASES](../../reference/PATH_ALIASES.md)。同步文档不启动UE，也不自动同步二进制工程、资产、模型或训练结果。

本次服务器根为`/scratch/prj0000000275/jcy/xks/DataMake`。Windows已有路径`D:\UE\Lance_Work`是历史记录，用户应先确认本机实际repo根；不要把服务器绝对路径批量替换成Windows盘符。模型架构对话与UE执行对话可以分别更新其所属文档，共享状态必须合并字段，不覆盖另一工作流的最新决定。

## 2. 同步内容

本轮清单为[server_documentation_sync_20261023.json](../../../../../implementation/server_documentation_sync_20261023.json)，由本文拥有。它记录repo相对路径、字节数、SHA-256与文件用途，按当前工作树生成，包含新增未跟踪文档，不仅是Git HEAD。

| 内容 | 同步方式 |
| --- | --- |
| 根README/HANDOFF/AGENTS与目录导航 | 合并后作为接手入口 |
| 20_planning的现行规范、状态、决策、归档计划和历史报告 | 保留相对层级；同名有两端独有修改时逐项合并 |
| 00_engine下的文档、UE脚本说明和维护Skill | 同步说明；不因此下载UE或脚本目录内全部文件 |
| 10_research下的报告、说明、报告图表/HTML和轻量JSON证据 | 保留架构分支的原有记录，历史报告不作为当前执行入口 |
| PROJECT_STATE.json | 合并模型工作流与server_sync工作流字段，禁止旧副本整体覆盖 |
| SCRIPT_CATALOG / OUTPUT_INVENTORY / RETENTION_POLICY | 服务器目录快照和保留依据；本地Catalog/Inventory须按本地代码/输出重建，不能拿服务器文件存在性替代本机事实；Retention仅合并已批准规则 |

明确不在本轮清单中：UE Content/uasset/umap/引擎、DDC/Saved/Intermediate、原始视频/交付媒体、checkpoint、Lance clone、环境/缓存、凭据及私人工具连接配置、源码脚本/训练配置/补丁主体、rebuild_reference和full_process_legacy快照。文档里指向代码或大型证据的链接，在仅同步文档的机器上可能没有对应实体；这不是自动补拷全部数据的指令。

## 3. 推荐步骤

1. 两端分别保存本轮前的文档副本/差异；将服务器清单及所列文件下载到本地暂存目录，保持repo相对结构。
2. 先在暂存目录核对文件数量/字节/SHA-256；此时验证的是传输一致性。Windows工具/Git若已转换LF/CRLF，原始字节hash会变，应在转换前验证；不能为了匹配hash丢掉本地更新。
3. 与本地当前文档比较：仅服务器新增的可加入；双方同名不同内容的做合并；本地独有文件保留。清单中的“服务器已删除跟踪文档”仅为提示，不授权在本地删除。
4. 服务器运行结论以服务器证据为准，本地资产/CC/UE导出事实以本地证据为准；架构设计由负责该讨论的分支合并，不能按文件mtime自动决策。
5. 文档与代码都合并后，重建机器目录并执行文档审计。只有文档的副本不能通过完整代码/资产Gate，应明确记录缺失范围。
6. 记录双方核对日期、清单版本和未解决冲突；清单之后若另一分支新增文档，单独补同步或刷新清单。本次清单是时点快照，不是持续同步服务。

禁止使用整目录`--delete`或镜像覆盖来同步这批文档。当前服务器工作树包含大量未提交文件，不能把“同一Git提交”当作两端内容一致。

## 4. 合并后检查

在具有配套代码的repo根执行：

```text
python 00_engine/scripts/documentation/build_script_lifecycle_catalog.py
python 00_engine/scripts/documentation/build_output_inventory.py
python 00_engine/scripts/documentation/check_character_factory_docs.py --json
```

若该机器没有完整服务器outputs，保留其“缺少证据/机器范围”事实，不通过改写历史Gate来消除差异。服务器与Windows的环境会话状态分别记录。

## 5. 同步之后进入UE任务

按[SERVER_EXECUTION](SERVER_EXECUTION.md)重新确认引擎构建、项目闭包、驱动、allocation和新Run Root，再执行环境/项目预检。历史生产引擎当前路径缺失是已知准备项；不能直接用安装版覆盖冻结profile，也不能在已发布dataset_v1中继续写新一轮输出。

## 6. GitHub维护与本轮上传审查

用户确认后续仍通过GitHub维护。本次审查与上传准备由本文拥有，见[GITHUB_SYNC_REVIEW](../../project_management/status/GITHUB_SYNC_REVIEW.md)。候选清单`20_planning/implementation/github_sync_preflight_20261023.json`记录已批准范围与hash，不包含凭据、引擎源码正文或Git对象。用户已确认排除16份UE引擎源码patch、根目录chains.json/html.md及独立robotdata仓库；规则写入.gitignore。robotdata已由用户删除，UE补丁和临时文件保留服务器。2026-10-23用户已配置登录节点HTTPS认证，遗留LFS钩子修复后dry-run通过；实际上传结果以审查状态和Git提交为准。

通过Git同步时，以实际提交为内容版本；目录清单只用于提交前的差异核对。生成式Catalog/Inventory应与该提交的脚本/机器范围配套，不单独用旧目录快照覆盖新代码。

## 7. 本轮GitHub写入认证

2026-10-23实测：当前HTTPS远端为`SampleTree123/Lance_Work`，原credential.helper为store但令牌无效；现有专用SSH密钥能认证为King-Wood-Shen，却没有本仓库写权限。没有修改这些已有凭据。

推荐由用户登录**SampleTree123**，在GitHub的Settings → Developer settings → Personal access tokens → Fine-grained tokens创建令牌：Resource owner选SampleTree123，Only select repositories选Lance_Work，Repository permissions中的Contents设为Read and write，Metadata保留默认只读。设置到期时间，例如30天。本轮不修改GitHub Actions工作流，不需要Workflows权限。参见[GitHub官方说明](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)，核对日期2026-10-23。

在执行Git推送的服务器节点运行下列命令；用户本次实际使用orion-login01，代理可经集群SSH在该节点执行。计算节点后来已换为8FS9B74，不共享登录节点的内存缓存。只配置本仓库使用4小时内存缓存，空helper用于屏蔽继承的store，避免继续使用失效令牌。令牌仅在终端Password提示出现时粘贴；不要写入命令、文档、远端URL或聊天。

```bash
cd /scratch/prj0000000275/jcy/xks/DataMake
git config --local --replace-all credential.helper ''
git config --local --add credential.helper 'cache --timeout=14400'
env -u GIT_ASKPASS -u SSH_ASKPASS GIT_TERMINAL_PROMPT=1 \
  git -c core.askPass= push --dry-run origin HEAD:refs/heads/main
```

若提示Username，填SampleTree123；Password填新令牌，不填GitHub登录密码。dry-run不上传内容，当前HEAD未变化时成功输出通常为Everything up-to-date；认证成功不替代正式推送时的分支规则检查。缓存仅在该节点进程存活期间可用，换节点、进程结束或超时后需要重新输入。参见[Git credential-cache](https://git-scm.com/docs/git-credential-cache)。

2026-10-23用户已完成以上配置；orion-login01的HTTPS dry-run已通过。上面命令保留为缓存失效后的恢复步骤，不需要重新申请令牌或重复确认上传范围。

## 8. 本次遗留LFS钩子修复

2026-10-23用户在orion-login01遇到git-lfs不在PATH导致pre-push失败。该仓库没有.gitattributes，全部本地可达历史与当前候选未发现LFS指针，有效filter查询也无lfs；.git/lfs/objects不存在。唯一pre-push为标准LFS调用，无自定义检查。

核验后只将.git/hooks/pre-push备份改名为.git/hooks/pre-push.disabled-no-lfs-20261023，没有删除内容、跳过其他钩子、清空凭据或上传大型文件。再次dry-run成功。此修复只适用于已核验不使用LFS的当前仓库；未来引入LFS应安装git-lfs并恢复钩子，否则可能漏传LFS对象。官方用途见[git-lfs pre-push](https://github.com/git-lfs/git-lfs/blob/main/docs/man/git-lfs-pre-push.adoc)。
