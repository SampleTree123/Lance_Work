# 本地资产准备与服务器渲染注意事项

> 父层：[`./README.md`](./README.md) → [`../README.md`](../README.md) → [`../../README.md`](../../README.md)。
> 本文件记录 2026-07-08 起采用的“本地图形化整理资产，服务器脚本化渲染”工作方式。

## 一、当前结论

当前最稳妥的路线是：

```text
Git 仓库：文档、脚本、配置、台账、manifest、少量小文本
本地 UE Editor：找素材、导入、绑定、retarget、调材质、看镜头
服务器 UE：接收整理好的项目内容子集，跑确定脚本和批量渲染
冷存储层：长期保存原始资产包、hash、许可证取证和最终数据归档
```

不要把 Git 当素材仓库。`.uasset`、`.umap`、原始资产包、UE `Content/`、DDC、渲染输出和模型权重都不进 Git。

## 二、远程 Git 与本地 clone

把当前仓库推到用户自己的 Git 仓库后，本地 clone 只应该得到：

- 项目说明、决策日志和 handoff。
- UE 脚本、最小工程配置、MCP 配置。
- Lance 验证脚本、patch 和报告。
- 资产台账 schema、存储策略和合规入口。

本地 clone 后缺少以下内容是正常的：

- UE 5.8 引擎安装目录。
- Lance 上游代码、模型权重、输出视频和日志。
- UE 导入后的二进制资产、场景、贴图、动作和渲染输出。
- 本地/服务器 DDC、`Saved/`、`Intermediate/`、`Binaries/`。

建议本地阅读顺序：

```text
HANDOFF.md
README.md
20_planning/implementation/local_asset_workflow.md
20_planning/implementation/storage.md
00_engine/assets/asset_ledger_schema.md
20_planning/compliance/licensing_compliance.md
```

## 三、本地 UE 资产准备流程

本地 UE 只做交互预览和小规模整理，不保存完整素材库。

1. 使用与服务器目标一致的 UE 主版本。当前服务器目标是 UE 5.8。
2. 新建或打开本地测试工程，导入候选资产。
3. 先做小子集：1 个场景、1-2 个角色、2-3 个动作、少量道具/配饰。
4. 检查骨骼、动作 retarget、材质、贴图、LOD、碰撞、尺度、相机和灯光。
5. 每个候选资产先登记台账，至少写 `asset_id`、来源、许可证、取证日期、大小、状态和技术备注。
6. 没有训练/再分发结论的资产只能标记 `candidate` 或 `prototype-only`。
7. 本地确认能打开、能播放动作、能进入镜头后，再打包当前 pilot 子集给服务器。

本地不需要把所有可能素材都同步到服务器。每次只上传当前批次需要的工作副本。

## 四、本地到服务器的传输包

建议每次上传一个明确命名的资产包，例如：

```text
datamake_asset_pack_20260708_pilot01/
  project_delta/
    Config/
    Content/DataMakePilot/
    Plugins/                 # 只有确实需要时包含
  manifests/
    asset_ledger.csv
    asset_manifest.json
    checksums.sha256
  notes/
    import_notes.md
    known_issues.md
```

上传到服务器后：

```text
00_engine/assets/prototype/<pack_id>/          # 原型资产工作副本
00_engine/projects/MVPProject/Content/...      # UE 工程实际引用内容，仍然不进 Git
```

不要上传：

```text
Saved/
Intermediate/
DerivedDataCache/
Binaries/
.vs/
本地缓存
一次性下载 token
未登记来源的大资产包
```

传输方式可以是 `rsync`、`scp`、压缩包或后续确定的冷存储同步工具。Git 只记录 manifest、台账、hash 和说明。

## 五、素材选择准则

第一批素材优先服务 MVP，不追求丰富度：

| 类型 | 第一批建议 | 原因 |
|------|------------|------|
| 场景 | 1 个简单可控场景 | 降低构图和光照变量 |
| 角色 | 1-2 个可稳定绑定动作的角色 | 先验证动作和相机稳定性 |
| 动作 | 2-3 个循环或短动作 | 便于端点复用和多轮链 |
| 道具/配饰 | 明显可见、容易开关的对象 | 支持 E5/E6 最小编辑 |
| 光照 | 白天、夕阳、冷暖色等可控参数 | 支持 E8 光照编辑 |

暂时不要把以下内容作为第一批核心：

- 复杂身份替换。
- 需要大量布料/头发仿真的角色。
- 过重的开放世界场景。
- 权利状态不清楚但看起来很好的商店资产。
- MetaHuman 作为训练/测试数据主体。

## 六、合规注意

本节是项目执行规则，不是法律意见。执行前应重新核实对应许可证页面和资产详情页。

- 2026-07-08 查阅的 Fab Standard License 摘要允许私用/商用、修改并并入项目、与项目协作者共享，但不允许单独转售或免费再分发资产本体。训练权、NoAI、再分发衍生数据仍要按具体资产记录，不能默认 `cleared`。
- 2026-07-08 查阅的 Unreal Engine EULA 将 UE 引擎许可和 Fab 等外部内容许可区分开；渲染视频文件可作为 Non-Engine Product 免 UE royalty 的情形，与第三方资产是否允许训练/发布是两个问题。
- Unreal Engine EULA 同时包含对 Licensed Technology、MetaHuman 数字角色/动画曲线及特定输出用于 AI 训练/测试的限制。MetaHuman 暂不进入本项目训练/测试数据主资产池，除非后续有明确授权结论。
- 所有资产先按 [`../../00_engine/assets/asset_ledger_schema.md`](../../00_engine/assets/asset_ledger_schema.md) 登记。未完成来源、许可证、训练权、再分发权和 NoAI 状态确认前，只能 `candidate` 或 `prototype-only`。

参考入口：

- Fab Standard License: <https://www.fab.com/eula>
- Unreal Engine EULA: <https://www.unrealengine.com/eula/unreal>

## 七、服务器接收后的检查

服务器拿到资产包后先做 smoke，不直接批量渲染：

1. 检查 `asset_manifest.json`、`asset_ledger.csv` 和 `checksums.sha256` 是否齐全。
2. 确认没有把 `Saved/`、`Intermediate/`、`DerivedDataCache/`、`Binaries/` 一起传上来。
3. 用 UE 命令行打开工程或跑 Python smoke。
4. 检查资源引用是否丢失，材质是否变粉，动作是否正确 retarget。
5. 生成 1-3 个短视频样例和 sidecar。
6. 人工看过样例后，才进入 20-50 条 pilot 样本。

## 八、Git 提交前检查

每次推送远程仓库前：

```bash
git status --short
git diff --check
git ls-files | rg '\\.(uasset|umap|ubulk|uexp|mp4|zip|safetensors|pth|pt)$'
```

最后一条命令如果有输出，需要逐项确认是否误提交。正常情况下，UE 资产、视频、压缩包和模型权重都不应出现在 Git tracked files 中。

## Agent 备忘

- 用户本地找素材时，优先提醒“先小子集、先台账、先 prototype-only”。
- 不要建议用户把完整素材库塞进 Git 或 DataMake 工作盘。
- 本地 UE 工程内容可以通过资产包同步到服务器，但不作为 Git 正文提交。
- 服务器渲染前必须能从台账和 manifest 追溯每个资产来源。
