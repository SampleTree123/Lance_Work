# v10 整分量双画幅：7203个主视频，零画幅重复

已完成候选4的离线画幅分配、物化、参考需求与复核。当前输出为 `selected_candidate/`；来源唯一绑定 `../structural_candidate` 及其 `SOURCES.json`。没有采用候选5，没有改源图/链，没有操作UE或渲染。

| split | 原内容/实际主视频 | 横/竖链数 | 横/竖主视频 | 横/竖六非身份轴最大相对偏差 |
|---|---:|---:|---:|---:|
| train | 5980 / 5980 | 6388 / 5612 | 3234 / 2746 | 6.26% / 9.17% |
| test | 1223 / 1223 | 1252 / 1148 | 652 / 571 | 9.68% / 8.50% |

共7203个主视频，比v8的6439增加764（11.87%）。全部12000/2400条结构链恰好保留一次，所有分支与历史源不变，每条链固定一个画幅；两画幅均有男女、21起始镜头、7编辑轴。竖屏链分别占46.77%/47.83%。逐值0.5–1.5要求仍只在合并train检查，没有扩成每画幅约束。

## 零重复方法与成本下界

训练源图97个连通分量、测试21个。每条链完全位于单个分量，所以将整个分量分给一个画幅即可避免共享节点。每个分量只用一个二元变量，CBC仅求小型可行分配：链数45–55%、各性别链的40–60%分到竖屏、双方所有起始镜头/轴出现、双方六非身份轴偏差≤10%。没有运行旧的逐链切割，也没有增加内容节点。

每个必须使用的原内容至少需要一次渲染，因此固定图与全链保留条件下主视频数不可能少于5980+1223。当前正好达到7203，已达到该条件下的数量下界。`component_assignment/`和`selected_assignment/`保存逐链画幅、节点需求、分量编号/画幅、统计及CBC日志。

## 审核

运行前要求根目录两套structural独立审计均passed。物化后再独立重算：

- `aspect_audit.json`：原链/非画幅内容精确保留、合法性、跨split忽略aspect无重合、实际镜头绑定，passed。
- `projected_frequency_audit.json`：新unique内容与完整history频率、动作内部镜头频率、衣物组合和语义，passed。
- `projected_inherited_audit.json`：真实编辑目标、21起始镜头整数配额、合法服装单件机会/slot及旧语义，passed。
- `reference_binding_check.json`：52560条编辑参考链接，passed。

训练25动作的最少有效镜头15，合计443个有效动作×镜头对；测试最少17、合计113对。有效镜头排除front_head。`action_camera_coverage.json`保留包含head的旧诊断字段，并附上明确排除head的独立验收字段，不能混用。

内容边平均复用train2.137/test2.112，未达到软目标2.5；四用边比例0.49766%/0.16876%，最大4。分配不改变这些结构统计。服装条件单件比例48.01%/47.39%；slot条件TV为1.41%/9.18%，是原审核口径的实际结果。

物化器使用自有 `materialize_snapshot.py`，保留源图真实 `created_by` 并按新ID重映射父节点，保留同分量真实原图边。首次复核发现旧v7物化器缺顶层provenance，已在本目录补全并重新生成参考哈希/四套复核；源图和链不变。原始与新代码哈希及修复说明在ASSEMBLY/INPUTS中记录。

## 参考需求

符号参考2398项：1609张图和789个动作片。分类为衣物564、身份40、发型112、场景893、动作789。它们不计入7203主视频；尚未生成媒体，最终像素尺寸、帧率、时长与实际场景镜头变换仍待冻结。详细需求在 `selected_candidate/reference_manifest.json`、`reference_summary.json` 和 `REFERENCES.md`。

## 复现

Python、NumPy、PuLP/CBC；不需要SciPy。由 `D:/UE/Lance_Work` 执行：

```powershell
C:/ProgramData/anaconda3/python.exe -B 00_engine/outputs/dataset_distributed_graph_20261022_v10/aspect_work/finish_candidate.py --source D:/UE/Lance_Work/00_engine/outputs/dataset_distributed_graph_20261022_v10/structural_candidate --ready-audit D:/UE/Lance_Work/00_engine/outputs/dataset_distributed_graph_20261022_v10/structural_frequency_audit.json --rules D:/UE/Lance_Work/00_engine/outputs/dataset_distributed_graph_20261022_v10/RULES.json
```

输出存在时禁止覆盖；`--resume-materialized`仅对现有同源投影补全provenance并重算审核/参考，不重选链或画幅。所有来源和代码哈希在 `INPUTS_AND_METHODS.json`。旧 `chain_pool_model.py` 和trial8研究仅作备忘，不参与最终候选。
