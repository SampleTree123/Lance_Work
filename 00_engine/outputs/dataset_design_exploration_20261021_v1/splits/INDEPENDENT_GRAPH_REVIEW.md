# 图候选独立有限审阅：最终场景留出主候选

日期：2026-10-21。**当前主结论只对应 `main_scene_holdout_*` 文件。**图 agent 确认最终写完后，本分工重新独立读取主候选图、15,000 条 session 与身份目录，重算以下门禁；未重验全部旧产物。

最终主候选通过限定结构复验：**train 2,500 节点/12,000 session，test 500 节点/3,000 session；16 个训练 site 与 5 个测试 site 零交集；两侧均有全部 40 身份；所有登记边和实际 session 边均不跨性别兼容域。**这支持目录中选定 site 的未见场景拓扑候选，不是身份留出。场景资产族之间是否存在共享底图或其他视觉重复，未由本次结构检查验证；不把 site ID 不同直接扩大成视觉场景族独立。

## 当前最终 main：独立复验结果

| 检查项 | train | test |
| --- | ---: | ---: |
| 唯一完整 state / 节点 | 2,500 | 500 |
| 登记有向边 | 11,800 | 4,166 |
| session | 12,000 | 3,000 |
| 身份覆盖 | 40（女 20/男 20） | 40（女 20/男 20） |
| site 覆盖 | 16 | 5 |
| linear / one historical fork | 8,000 / 4,000 | 2,000 / 1,000 |
| 未知 identity、显式 sex 与目录不符、动作性别不兼容 | 0 | 0 |
| generation parent 跨性别 | 0 | 0 |
| 登记边跨性别 / 实际 session 边跨性别 | 0 / 0 | 0 / 0 |
| 全登记边不满足单属性变化 | 0 | 0 |
| parent 非真实先前 occurrence、实际边与标记轴不符 | 0 | 0 |
| 一个 session 含两次以上非最新选源 | 0 | 0 |
| session 内重复输出 state / 少于两种编辑轴 | 0 / 0 | 0 / 0 |
| fork source/latest 差异被当前编辑完全覆盖 | 0 | 0 |
| fork 后无继续编辑 | 0 | 0 |

完整 state 跨划分交集 **0**；site 跨划分交集 **0**；identity 跨划分交集 **40**。node 没有单独保存 sex 字段时，以 `normalized_inventory.json` 的 identity→sex 映射为权威重算，而非凭内部 ID 字符串猜男女；逐节点确认 identity 在目录内、动作支持其性别，并检查 generation parent、全部登记边和实际选中 parent 的同域性。没有把“生成时分域”当成“后补的诱导边也必然分域”。

主候选测试 site 是 `site_2a054574eb`、`site_6af8ead41a`、`site_7dbc277564`、`site_7f07230597`、`site_91fc32ba93`；其余 16 个 site 在 train。两侧画幅均固定 `landscape`，六个 state 字段中仅五项可变化，不能把 `aspect` 自动当本轮确认的编辑任务。完整服装、发型和参考条件仍未纳入该六字段状态，故本结论不是全生产配置或视觉原子性验收。

## 当前最终 main：长度与可辨分支

| session 类别 | train 长度 2/3/4/5 | test 长度 2/3/4/5 |
| --- | --- | --- |
| linear | 2,000 / 2,000 / 2,000 / 2,000 | 500 / 500 / 500 / 500 |
| one fork | 0 / 800 / 1,600 / 1,600 | 0 / 200 / 400 / 400 |
| 合计 | 2,000 / 2,800 / 3,600 / 3,600 | 500 / 700 / 900 / 900 |

已精确满足 fork 长度 3/4/5 = **20%/40%/40%**；主训练共 **44,800** 次编辑，测试 **11,200** 次。旧 run 的 fork 等分配额和 uniform-length alternative 均不用于当前 main。

分支计数直接数 `parent[t] != t−1`，不只看 `has_branch`。分支反事实检查采用 `target != replace_axis(latest, edit_axis, target_value)`，确认从最新版本照做同一编辑不会得到相同目标；5,000 个 fork 全通过。分叉轮次 2/3/4 的实际 train 数为 2,389/1,198/413，test 为 595/323/82；这是保证分叉后继续编辑的候选，并非末轮分叉或均衡早中晚位置评测。

测试池全部采用留出 site，没有同分布对照小池，且只包含 5 个 site；本次证明的是预算内合法 session 可采到，不证明 3,000 session 是独立样本、不证明稳健性，也不提供已见/未见场景性能差值。此前 A/B 分层仅为其他参数化候选，不应据其建议表推断 main 已实际生成了 80/340/80 分区。

## 当前最终 main：固定快照

| `../graph/` 中的文件 | SHA-256 |
| --- | --- |
| `main_scene_holdout_hybrid_train_graph.json` | `a592a4c29a3e72dc7dff802357d1bc9a3f79eec383f370948763e87b8c7eda1b` |
| `main_scene_holdout_hybrid_train_sessions.jsonl` | `a7f1b3bdf9a4abba6c774b36b044755fbac7d1d78b713427482fe04e5013cc11` |
| `main_scene_holdout_hybrid_test_graph.json` | `695212a901c0dfc40308268adaecfc91fd40b8d94d13302a98e9545d5ae86349` |
| `main_scene_holdout_hybrid_test_sessions.jsonl` | `fdbc74ed3779f11a23c95604112de0a97afc036c3b0cbcc8a2127804332a42f5` |

发现的两类 bug 已通知主/图 agent：①选源差异可被当前编辑完全覆盖；②节点生长分域，但登记诱导 identity 边时漏过滤跨性别端点。图 agent 修正后，本节最终文件重新独立检查，两类错误均为 0。以下历史快照不再充当 main，尤其旧审阅未检查性别边，不能沿用其“所列项目零错误”宣称兼容域完整通过。

---

# 历史快照：旧身份留出 quality run（已被 main 替代）

日期：2026-10-21。范围：先重读现行 `CONFIG_GRAPH_SCHEMA_V1.md` 的单属性边/完整配置约束，再阅读 `../graph/explore_graph_routes.py`，独立重算 quality landscape hybrid 图与 15,000 条 session 的关键结构。不运行 UE、不改图脚本、不扩资产审计，不验证模型性能。

结论：**本次读取的 quality 文件通过所列分支结构检查，但不构成未见场景评测验证。**发现的分叉源差异被编辑覆盖问题已通知图 agent，并在其修正后重新核对文件；下述快照中该错误为零。当前长度配额与主报告早先的 20%/40%/40% 分支候选不同，仍需统一。

## 1. 已检查的实际产物

| 检查项 | train | test |
| --- | ---: | ---: |
| 唯一节点 | 2,500 | 500 |
| 有向边 | 12,416 | 4,522 |
| session | 12,000 | 3,000 |
| linear session（非最新父 occurrence 数为 0） | 8,000 | 2,000 |
| one-fork session（非最新父 occurrence 数精确为 1） | 4,000 | 1,000 |
| 一个 session 含两次以上非最新选源 | 0 | 0 |
| parent 非真实先前 occurrence | 0 | 0 |
| source→target 不在登记边中或不是所标轴的单属性变化 | 0 | 0 |
| session 内重复完整输出状态 | 0 | 0 |
| session 编辑轴少于两种 | 0 | 0 |
| fork 当前编辑完全覆盖 source/latest 差异 | 0 | 0 |

两侧完整状态集合交集为 **0**。以上由独立读取 `*_graph.json` 与 `*_sessions.jsonl` 后重算，未直接信任 sampler 的 `has_branch` 布尔值或自报指标。

单属性检查相对 `parent_occurrence_indices_gt[t]` 指定源进行：比较所有保存的 state 字段，差异字段必须精确等于 `edge_axes[t−1]`，并核对对应有向边。fork 条件直接数 `parent[t] != t−1` 的次数。历史父指针必须满足 `0 <= parent[t] < t`；根父指针为 null。其余状态继承由完整 state 对比保证，不从时间线上 latest 计算原子性。

## 2. 找到并修正的分叉可辨性缺口

初读脚本时，quality filter 的条件是：在 source 与 latest 原有差异的字段中，target 至少一项仍不同于 latest。这个条件不足以保证选源有意义。

最小反例：source 是红衣近景，latest 是蓝衣近景，本轮把衣服改成绿。旧条件会接受，因为绿色仍不同于 latest 的蓝色；但从 source 或 latest 执行同一条“改绿”指令，结果完全相同，历史选源差异已被编辑抹掉。

已向主 agent 和图 agent 报告。图 agent 将条件改为 `any(d != edited_axis for d in differences)`：至少一个 source/latest 的差异属于本轮不编辑的字段。对合法原子边，这保证至少一项历史选择造成的差异真实保留。独立重算采用等价但不同写法：**target 必须不等于 `replace_axis(latest, edited_axis, target_value)`**。本次快照中 train/test 共 5,000 个 fork 全部通过。

该规则只检查 fork 当轮，未要求差异在以后所有编辑中永久存在。以后用户再改掉这个差异可以合法。

## 3. 这不是未见场景或随机 split 的验证

脚本 `Catalog.domains()` 实际按每性别排序的身份列表前 80%/后 20% 留出，不是随机逐 session 切分。当前 train 覆盖 32 身份、test 覆盖 8 身份；两侧身份不同，使完整状态自然不交叉。这是**候选未见身份值拓扑**，尚未得到对人物外观视觉不混淆的验收。

实际覆盖如下：两侧各有 25 动作值、21 相机值、21 site 值、7 发色；两侧共享全部 **21 个 site**。因此，这些文件不能支持“测试场景在训练未见”的结论。它们也未实施 `split_candidates.json` 推荐 A 的场景族留出与主测分层。要做未见场景，需按场景资产族重新分配 domain、连接节点、session 与参考条件后重新生成检查。

图脚本声明六个 state 字段 `identity/action/camera/aspect/site/hair_color`；当前 quality 输入固定 `aspect=landscape`，实际仅五个字段有变化。**六轴是拓扑表示，不是用户已经确认的六类编辑任务**，不能把画幅变化自动当已授权任务类别，也不能把 `>=2 axes` 解释为已覆盖所有真实任务类型。当前实验未纳入完整服装、发型与参考条件状态；结构通过仅限保存的 state 字段，不等于完整生产配置已原子继承。

同理，保存的 GT parent、state 与节点哈希是审计数据；本审阅未把它们当 public model input，也未验证未来的 public/hidden 输入过滤器。

## 4. 长度与分支位置口径

当前 `quotas()` 将 linear 的长度 2/3/4/5 等分，将 fork 的长度 3/4/5 近似等分。文件实数为：

| 长度 | train session | test session |
| --- | ---: | ---: |
| 2 | 2,000 | 500 |
| 3 | 3,334 | 834 |
| 4 | 3,333 | 833 |
| 5 | 3,333 | 833 |

总编辑次数为 train **43,999**、test **10,999**。这既不是主报告先前 linear 等分 + fork 20%/40%/40% 的 44,800/11,200，也不是本分工 uniform-length alternative 的 42,000/10,500。已通知主/图 agent，最终需选择一种配额并更新其 manifest；这些数不能互相替代。

默认 `followup=True` 时分叉轮次为 2 到 L−1，保证分叉后至少一次继续编辑；没有“最后一轮才分叉”的案例。实际 fork 轮次 2/3/4 的 train 数是 2,376/1,191/433，test 是 601/310/89。此分布来自短长度限制和随机采样，不是全体早中晚位置平衡。若论文要比较分支位置，需按合法长度条件下分层报告，不能把缺失格子当性能满分或零错误。

## 5. 快照与可复核边界

| 文件 | SHA-256 |
| --- | --- |
| `quality_landscape_hybrid_train_graph.json` | `7ed8fde44728ae52f3289ccd398b4253ab0dd5350fd165493f60bc355396d42e` |
| `quality_landscape_hybrid_train_sessions.jsonl` | `46f99748ce3e3347b092cb76390d13ad6062fabd2d8b8e2e6fb2a25d2643e5e6` |
| `quality_landscape_hybrid_test_graph.json` | `c0c2152396dc24ddc3731c38396cc2912f2f009d695b86fa28f9edae37289d1b` |
| `quality_landscape_hybrid_test_sessions.jsonl` | `16126833fd44e6fd5170ca038b24a965cfc1d75fe9b92d26ee20949525fdab37` |

文件位于 `../graph/`。若图 agent 继续调整长度/轴/过滤条件，以上结论只对应所列哈希，需要重新做同范围检查；不要求扩成全库审计。
