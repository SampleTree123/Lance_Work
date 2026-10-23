# 有限节点联合构造的独立核验

2026-10-21；仅纯 Python、符号 state、节点/边/会话及采样诊断；不调用 UE，不渲染。

## v1 的具体问题

源 state 在编辑轴上有 N 个正式合法目标，固定子图只表示其中 d 个。如果 session 从图内邻居均匀抽取，每个图内目标概率为 1/d，图外合法目标为 0；这不等于正式域上的 1/N。刚到达的源通常已经连回其入边起点，所以逆向 return 会系统性膨胀。增补 square 能增加 d，但不会自动消除这个机制。

v1 `full_squares_uniform_nodes/train` 中，沿实际 selected parent occurrence 的入边定位、条件在当前编辑轴与该入边轴相同：

| 轴 | return / 机会 | 实际概率 | 正式全域概率 |
| --- | ---: | ---: | ---: |
| color | 1502 / 1703 | 88.2% | 1/6 = 16.7% |
| identity | 1124 / 1391 | 80.8% | 1/19 = 5.26% |
| hair | 1624 / 1905 | 85.2% | 女 1/19，男 1/12 |

不能以全局 identity/hair/color 计数均衡推翻这类条件偏差。固定有限支持若缺目标，也不能宣称所有源的完整域 target conditional 精确均匀。

## 联合构造建议

先固定会话类型、长度和 fork 的 t/parent，再按正式域 eligibility 决定 axis、wardrobe mode 和目标层级。缺边不能成为重抽 axis、mode 或 fork source 的理由。记录全部因预算或支持不足而发生的拒绝、替换和失败；静默重抽会把偏差转移到其他条件。

在有限支持近似中，非服装轴可对历史已知且仍合法的每个目标值保留 1/N 概率，把剩余概率留给其他目标。即刻 return 不是禁用，也不人为配固定比例；它随正式域大小产生。如果剩余目标在支持内不存在，应视为构造失败或扩展支持，不能把剩余质量重新加到已知 return 目标上。即使历史回访概率正确，固定子图内全部目标的条件分布仍只能是近似，必须明确报告。

## 本核验程序

`verify_joint.py` 不 import 主生成器，复用 v1 独立语义检查器与正式服装解析器。输入为含 train/test 子目录的 candidate；每个 split 提供 `nodes.json`、`edges.json`、`sessions.jsonl`，格式沿用 v1。

```powershell
python 00_engine/outputs/dataset_joint_build_20261021_v2/audit/verify_joint.py --candidate <absolute-candidate-path>
```

报告的结构正确与采样诊断分开；程序退出成功仅表示结构与预算等硬检查通过，不把统计偏差写成采样成功。诊断包括：

1. axis 条件在正式 eligible axes、源 camera、kind/L/round；每一步的期望均重新使用正式域。
2. 非 wardrobe target 条件在 axis/source value/sex、源 camera、kind/L/round；每步 action/camera/site 合法排除保留在期望中。camera 编辑目标由 `--camera-target-policy` 指定；本次两候选根据主 agent 转达的用户最新澄清采用 `weighted_four`，四个指定镜头权重为 1.5；`uniform` 仅保留为原始规则解释的对照模式。
3. history 中已知合法目标值的总概率 K/N，以及实际 selected parent 的同轴逆向 return；附 1/N 与图内 1/d 对照。
4. wardrobe mode 条件在正式 single availability 与 camera；single 的 slot/value 层级；whole 的 family/group/slot/shoe 层级。服装候选仅枚举当前登记的小域，按逐 slot 均匀、optional independent bit、conditional shoe 概率计算，并在实际 core/upper 变化约束下归一。whole intended hierarchy 为 eligible family→eligible group；在整个 family/group 外层反复 rejection 会改变其概率，报告会暴露该偏差。
5. fork t 条件在 L；parent 条件在 L,t；初始 sex、identity/hair 条件在 sex、color 条件在 sex。

标准化残差和 total variation 用于定位偏差；稀疏小桶不作为强结论，session 复用节点/边也不满足独立样本假设，因此不提供伪精确的独立样本 p 值。初始 scene/action/camera 的合法性与抽样先后相关，当前不替未冻结的先后顺序伪造独立联合期望。

已执行 alternative roots40 的预算 prefix 和 joint_reserve35。报告见 `verification_alternative_roots40.json`、`verification_joint_reserve35.json`，精简指标见 `COMPARISON.json`。两者结构检查通过，但目标会话配额均未完成；`--partial` 只把未完成预算/配额单列为 expected shortfall，不代表候选达到最终交付要求。主候选 train 的正式轴条件残差达 8.52，hair target 条件残差达 14.05；被接受会话的 color 完整历史节点 return 为 31，正式期望为 14.83。声明的 history gate 概率与独立正式概率相符，接受后的事件仍偏高，显示失败重试会重新引入选择偏差。残差仅用于诊断，不能当作独立样本检验的 p 值。

alternative roots40 以 2,499/499 个节点获得 699/122 条完整会话；train 的 axis 最大条件残差为 2.40，target 为 3.63（均要求该桶 n≥50），color 完整历史节点 return 为 11、期望 10，没有出现 v1 的巨大逆向 return 放大。但有限 root 导致初始 hair 最大残差 13.84、family 8.30，且配额大幅未满。joint_reserve35 用满 2,500/500 个节点，得到 1,897/242 条会话，提高节点复用，却同时保留初始偏差并引入明显接受偏差。两条路线都只是部分构造证据，不是正式采样要求已全部实现的证明。
