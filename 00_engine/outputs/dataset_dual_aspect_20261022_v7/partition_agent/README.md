# 整链双画幅分配试验（2026-10-22）

本目录只读取 v6 `selected_seed1` 原图与原链，不修改原节点、历史、编辑或 UE。每条链只选一个画幅；同一原节点被两个画幅的链需要时分别渲染。交付是离线候选分配与准确渲染需求，尚未渲染，也不是全局最优证明。

最后追加的推荐组合为 `economy/train` + `axis_balanced/test`：训练4963次保持不变，测试1187次，合计6150次。它比全经济档只多65次渲染，把test两画幅内部六轴最大相对偏差压到横5.37%/竖8.52%。全部原链保留，不重采样。

## 结果

| 候选 | train 渲染数 / 共享节点 | test 渲染数 / 共享节点 | 合计渲染数 | 相对原4552节点增幅 |
|---|---:|---:|---:|---:|
| random_baseline | 7471 / 3719 | 1600 / 800 | 9071 | 99.28% |
| spectral_baseline | 6461 / 2709 | 1501 / 701 | 7962 | 74.91% |
| economy | 4963 / 1211 | 1122 / 322 | 6085 | 33.68% |
| economy train + axis_balanced test | 4963 / 1211 | 1187 / 387 | 6150 | 35.11% |
| compromise_budget | 5117 / 1365 | 1160 / 360 | 6277 | 37.90% |
| compromise | 5145 / 1393 | 1174 / 374 | 6319 | 38.82% |
| balanced | 5576 / 1824 | 1236 / 436 | 6812 | 49.65% |
| tight | 5563 / 1811 | 1280 / 480 | 6843 | 50.33% |

经济档全链横竖比例 train=49.65:50.35、test=50.29:49.71；每个起始镜头的竖屏链占比为 train 19.58%–80.27%、test 20.00%–80.77%。它节省渲染，但个别镜头允许约二八分配。

从经济档继续优化得到两个折中档。compromise把镜头竖占收至train24.68%–75.29%、test24.76%–75.00%，合计增加234次渲染。compromise_budget放轻软惩罚后，镜头train23.95%–75.67%、test23.81%–76.92%，合计增加192次渲染；总6277，接近约6200目标但未降到6200以内。

严格档 train 正好6000横/6000竖，每个起始镜头的竖屏链占49.90%–50.10%；test为1203横/1197竖，各镜头40.00%–55.77%。均衡档 test 1236次，较严格档1280次少44次，镜头允许34.62%–65.38%。train 的 balanced 被 tight 在成本与镜头均衡上支配；不同split可以选择不同候选。

全部十五份候选split已重新从assignment重算验证：一链一个画幅、链ID顺序精确对应源、需求节点集合精确、男女/21起始镜头/7类编辑轴在两画幅均覆盖、没有非法竖屏链。完整男女、sex×camera、编辑轴、axis×mode、链形态/长度、实际渲染节点男女与镜头数量都在各自 `stats.json`。

经济档六个非身份轴在各画幅内部相对均匀1/6的最大相对偏差：train横1.99%/竖6.08%，test横22.16%/竖34.45%。budget折中test降至横16.03%/竖28.28%，仍明显不均匀。六轴分别有40–60%的编辑分到每个画幅，与每个画幅内部六轴等量是两个不同口径，不能混称通过。衣物single/whole统计是所有服装边实际计数，不是按来源合法单件条件校正的比例。

最后的test专门优化七轴各自分到portrait约49–51%，放宽镜头至20–80软范围。结果test横1198/竖1202，七轴竖占49.02%–50.07%，起始镜头竖占19.05%–80.77%；男女横636F/562M、竖617F/585M，服装single/whole横276/404、竖257/425。它的每画幅六轴内部最大相对偏差为5.37%/8.52%，对应0.90/1.42个百分点。

优化过程先修正轴偏差、再回收共享节点。保存的计算中间点：第0轮test1526次、偏差8.88%/5.00%；第2轮1251次、5.61%/8.28%；第3轮1228次、5.21%/8.69%；第5轮1213次、5.35%/8.55%；最终1187次、5.37%/8.52%。这些是候选计算成本，不表示已经实际渲染。完整曲线为 `axis_balanced/test/cost_distribution_curve.csv`。

## 文件

- `{candidate}/{train,test}/assignment.jsonl`：每行 `{"id":"原session_id","aspect":"landscape或portrait"}`，与原sessions.jsonl逐行一一对应。原history和steps无需改动。
- 同目录 `node_requirements.json`：各画幅实际需要的原节点ID；交集即重复渲染节点。这里保留原ID作索引，不冒充已重算canonical_id的新节点文件；下游生成渲染节点时应以完整含aspect的state重新算canonical_id。
- 同目录 `stats.json`：详细实际计数；`method.json`：选中随机种子、优化参数与每轮轨迹。
- `comparison.csv` / `summary.json`：全部候选比较与完整统计。
- `distribution_detail.json`：各候选每画幅男女、六非身份轴内部最大相对偏差和百分点偏差、服装single/whole实际数量与比例；经济档另有 `economy_distribution_detail.json` 便于审阅。
- `verification.json`：定向复算验证和assignment SHA256。
- `input_hashes.json`：四个不可变源文件SHA256。
- `portrait_eligibility_mask.json`：审核agent的正式规则快照。当前train 3752/test800节点在portrait均合法，非法链数均0。脚本仍实施forced-landscape保护。
- `axis_balanced/COMPOSITION.json`：最后test专门优化的组合说明，明确train继续使用 `economy/train`；该目录只拥有新test分配。

## 方法和边界

train共有6个连通块，每块含2–4个起始镜头；test只有2块，分别是男女。整个连通块直接选画幅虽可零重复，会使镜头或性别只出现在一个画幅，所以没有把这种退化结果作为候选。

算法把链当作待分配项、把每个原节点看作连接所有使用它的链的超边。代价直接为切开的超边数，即共享节点数；总渲染数严格等于 `N_union + N_intersection`。相同节点集合的链打包移动，但每条链仍单独输出。

先做归一化节点图谱排序，按起始镜头取得约半数作为初值。随后做单链包翻转，以及“某节点相关的全部链一起移到一个画幅”的大步，辅以低温退火和最后贪心。后者能越过单链翻转无法消除高复用共享节点的局部障碍。实际优化只有节点重复收费；链数、男女、起始镜头、七编辑轴和axis×mode用可复查的软惩罚控制，各档参数在 `partition.py` 的 `PROFILES`。不要求全目录逐值均匀。

软上下界允许少量超出，例如经济档某镜头19.58%，不是20%的硬门槛。全链45–55在实际全部输出满足；覆盖在保存后逐项核验。样本性别/起始镜头的原有关系不被修改，本分配保证这些值在两个画幅均出现。

portrait mask由v5正式 `Rules.valid_state` 在每个节点上把aspect置为portrait后检查，含 `(site,action,camera,aspect)` 排除与服装合法性。规则代码与catalog哈希在mask中；源文件哈希在input_hashes中。后续换图须重建mask，不能沿用本次全合法结论。

## 复现

依赖Python和NumPy。本次运行使用本机Python 3.12与NumPy 2.4.4；不需要SciPy。精确交付运行参数：

```powershell
python 00_engine/outputs/dataset_dual_aspect_20261022_v7/partition_agent/partition.py --passes 18
python 00_engine/outputs/dataset_dual_aspect_20261022_v7/partition_agent/refine_economy.py
python 00_engine/outputs/dataset_dual_aspect_20261022_v7/partition_agent/refine_budget.py
python 00_engine/outputs/dataset_dual_aspect_20261022_v7/partition_agent/refine_test_axes.py
python 00_engine/outputs/dataset_dual_aspect_20261022_v7/partition_agent/summarize_verify.py
```

从 `D:/UE/Lance_Work` 运行。初始三档各自独立尝试6101和6102种子，compromise从经济档用6103/6104、16轮，budget分别从economy/compromise用6105/6106、12轮，并按完整代价选取；最后axis_balanced仅test从economy用6107、24轮，不改train。不是把多个seed合并。`--quick`只生成随机与谱基线。默认不带参数运行会用24轮，因此不承诺与18轮交付逐字节相同；精确参数以上述命令为准。初始三档墙钟约125秒，仅为本机本次记录；追加优化另计。
