# 当前七轴成功覆盖了多少衣柜

2026-10-21。只读 `../graph/appearance_catalog.json` 与正式衣柜/面板接口源码；没有 UE 调用、导入验证或视觉验收，没有改目录或原 run，没有枚举完整衣柜笛卡尔积。

结论：**当前七轴实验确实只在两个方便的局部服装域上成功，不能宣称完整衣柜已验证。**女性是 `streetwear_collection / full_body` 的 16 个 full_body 注册值，男性是 `1920s_collection / separates` 的 5 个 pants 值；其他服装槽位和鞋固定，且选择了允许发型的子集。此选择由采样器“挑最大可变非鞋槽”产生，不是按衣柜类型广度抽样。

## 1. 单件与整套：两种合法候选契约

用户已确认一次改一个属性、换衣服不顺便换头发/场景；尚未决定“服装属性”必须是一件还是整套。以下两种均可合法，不替用户冻结：

- **piece-level / 单槽候选**：在同一个 family/group 内，只改指定槽，例如裤子、上衣或 full_body；其他服装槽、配饰、鞋、头发、身份、动作和场景保持。当前七轴采用这一明确解释。
- **outfit-level / 整套候选**：把一整套服装定义为一个属性，则多件衣服/多个 mesh 同时变化可以是一条编辑。要声明鞋与配饰是否也包含在这一属性中；身份、场景和头发仍需保持。locked bundle 可以作为一个完整 outfit 值，不能因它有多个部件就自动判违反用户规则。

两者的图元粒度不同，应分别标注与评测，不能用单槽实验的结论代替整套实验。`full_body` 是注册槽名，不保证只对应现实中的“一件衣服”；一个 bundle 也可能含饰物或面部装饰。pixel/语义影响需要另验。

## 2. 准确的注册接口计数

| 当前导出接口 | 女性 | 男性 | 合计 |
| --- | ---: | ---: | ---: |
| family | 12 | 26 | 38 |
| family/group | 17 | 29 | 46 |
| 支持至少一项核心服装槽变化的 group | 15 | 14 | 29 |
| 可变核心槽域，按 family/group/slot 计 | 26 | 29 | 55 |
| 没有核心槽替换的 group | 2 | 15 | 17 |
| locked bundle family | 2 | 2 | 4 |
| 核心服装池中可选择的不同 asset ID | 112 | 110 | 222 |
| 界面暴露的 family asset ID，含固定件/配饰/原生鞋 | 131 | 158 | 289 |
| 保留的 preset 快捷项 | 79 | 73 | 152 |
| 独立可选配饰 ID | 5 | 2 | 7 |
| 共享鞋 ID | 9 | 22 | 31 |
| 原生鞋 ID | 0 | 37 | 37 |

“可变核心槽域”包括合法 optional none，例如外套可不穿；不包含鞋和独立配饰开关。女性 26 个核心槽都可变；男性另有 27 个固定单值槽，合计 56 个核心槽出现位置。ID 不等于独立几何或视觉样式，一个 ID 可关联多个 mesh，颜色/材质和重复路径也不能靠 ID 计数替代视觉多样性。

每个槽有 m 个合法注册值时，在**其他选择固定的一个上下文**中有 C(m,2) 个无向值对、m(m−1) 条有向候选。按 group/slot 求和得到女性 **348**、男性 **95**，合计 **443 个局部无向值对**；去掉同一 family/slot 在重复 group 中出现的同值对后为 **327+95=422**。这不是所有服装配置的图边总数，也没有乘身份、动作、场景、鞋和头发。

当前 21 个可选 core ID / 全接口 222 = **9.46% 的注册选项 ID 覆盖**，不是外观覆盖率或视觉多样性覆盖率。按域看仅 2/38 family、2/46 group、2/55 可变核心槽域；两个局部池理论上有 120+10=130 个无向值对，也不表示这些值对已经全部进入实际稀疏图或已渲染。

完整 46 行候选域表见 `DOMAIN_TABLE.md`，逐槽 ID、值对、鞋策略与限制见 `wardrobe_domain_inventory.json`。

## 3. 哪些局部域真的支持单槽选择

正式接口 `_canonical/_selected_assets/resolve_selection` 要求资产来自本 family/group 的 slot pool；每个 required 槽恰好一个、optional 槽至多一个，必须部件不能丢；不能拿同名槽当作跨族通用池。裤子/裙子共占 Bottom，full_body 与分体衣物互斥。上述规则允许在同一合法 group 中冻结其他选择、只改一槽；不证明所有人物/动作下视觉适配均已验证。

有代表性的扩展域：

| family / group | 已注册的局部可变槽 | 需要特别保留 |
| --- | --- | --- |
| 女 Summer Girl Four Colors | shirts 4、pants 4 | 两槽能独立变化；不是必须同色套装 |
| 女 Bikini Ruana | pants 5、shirts 5、coats 5+none | 外套“无”是一合法值，不能默默换上下装 |
| 女 Pretty Dresses | pants 或 skirts 两个 group，各 shirts 6 + 下装 3 | 不在两个 group 之间自动连单件边 |
| 女 Streetwear | full_body 16；另有 skirt_with_shirt 3×3 | 当前只覆盖前者，后者是未覆盖局部域 |
| 女 Shirts Pants A–I | shirts 9、pants 9 | 可用小网格/方形而非枚举 81 组合 |
| 女 African Casual | full_body 4；分体 group 有 pants 4、shirts 2、部分 coats 2 | 三个 group 分开处理；不默认跨 group 原子 |
| 男 Casual 01–04 | coats 4、shirts 4、pants 4、原生 shoes 4 | 原生鞋与共享鞋互斥 |
| 男 Jiving | pants 3、shirts 4 | 允许共享鞋的独立域 |
| 男 Mesh It Up / Streetstyle / Workout | 多个 3 或 4 值上衣/裤子池 | 比只取 1920s 裤子更能覆盖分体结构 |
| 男 1920s Collection | full_body group 5；separates 有 pants 5、shirts 3、coats 4+none | 当前只换 separates 裤子，未覆盖其他槽 |

`shirts 9 / pants 9` 表示两条轴的值数，不是已枚举或已验证所有 81 组合。共享身份/动作的多个局部图可以并列，不要求它们跨 family 相连。

## 4. locked、固定组与 preset 不能混为一谈

四个 locked 核心是女性 **Elise（9 必需部件）/Misaki（5）**，男性 **RedSoul（当前 5）/Cyberpunk Locked（4）**。接口要求整个 required bundle；piece-level 下不能从中拆一条裤子，outfit-level 下可以把整包作为一个值。女性两 bundle 仍可在外部共享鞋/发型轴变化；男性 bundle 内含固定原生鞋，不能另加共享鞋。

男性 Cheer Leader 的三个 matched group，以及 Dawkins、Hippasuta、Lederhosen、Lincoln、Mercenery、Owen、Rugged & Trendy、Underbelly、Vacation、Wrinkled 等没有核心替换值或只有固定槽，但有些仍有可选配饰、共享鞋或发型。**“核心服装无可变值”不等于“整个 appearance 只能选 preset”。**例如 Vacation 有腰包开关；Wrinkled 虽上衣/裤子固定，仍有共享鞋域。

152 个 preset 是快捷项，不是合法组合全集。只比较这 152 个已有项，不枚举完整衣柜，得到：

| 已有 preset 的有限配对诊断 | 女性 | 男性 |
| --- | ---: | ---: |
| 无向 preset 对 | 3,081 | 2,628 |
| 同 family/group | 251 | 120 |
| 同组、恰好一核心槽变化，其余选择固定 | 182 | 13 |
| 同组但至少两核心槽变化 | 66 | 53 |
| 任意两 preset 的鞋选择签名不同 | 1,635 | 2,579 |
| 任意两 preset 的 hair-deny 策略不同 | 0 | 72 |

这些多件/鞋变化在 outfit-level 契约下可能仍合法，不能直接称错误；在 piece-level 或鞋独立轴下则不能盲目当单槽边。跨 family/group 的多数对不在本分析中推定互换兼容。

全部 preset 存档的 `hair_id` 都为 null，这**不证明当前面板选衣服会清头发**。源码明确在改 family/group 或选 preset 时保留当前 hair ID，随后只按禁发规则处理；数据构造若直接深拷贝整个 preset，仍需显式保留未编辑的 hair/color，不能把存档 null 当指令。

## 5. 鞋与发型应怎样作为局部域

女性 17 个 group 中 **13 个允许赤足、4 个必须共享鞋**：前者 9 鞋+none=10 值，后者 9 值。每个 group 的一个冻结上下文中，鞋值对为 45 或 36，合计 **729**；这只是同一九鞋池在多个服装上下文重复出现，不是 729 款鞋。

男性 25 个 group 必须使用原生鞋/整包鞋，其中 7 组的原生鞋确有多个值；Jiving/Pyjamas/Rugged & Trendy/Wrinkled 四组允许 22 个共享鞋+none=23 值。局部上下文鞋值对合计 **1,032**，其中 1,012 来自四组重复的共享鞋池，另外 20 来自原生鞋池。不能把 22 个共享鞋直接套进要求原生鞋的所有 group。

如果将鞋设为独立轴，应把 `native/shared/none + asset ID` 规范为一个 footwear choice。native→shared 涉及清原生鞋和填共享鞋两个实现字段，仍可以是一项语义鞋编辑，但只能在接口允许的组中；不能让数据只比较 `shared_shoe_id` 而漏看原生鞋。鞋差异还需要脚部可见，head-only 镜头不能仅凭配置判鞋编辑可观察。

当前导出目录中，唯一 family-level hair deny 是 **male.rugged_trendy**；该核心本身只有一个 full_body 值。它应作为固定 `hair=none`、`hair_color=original` 的局部域，不应为了纳入服装范围而伪造发型/发色可编辑轴。转入这个域时若原源戴着头发，必须避免把清头发暗含在“只换衣服”边中；可选择源本就无发的 slice，或分两步明确编辑。不要将这个局部限制扩大到全部男性衣柜。

RedSoul 的当前 shooting overlay 已去除必需 hood、允许发型；不能沿用历史禁发结论。当前 slot 选项和 required/optional 资产没有另一个被导出为 deny_all 的部件，但未来目录变化仍须重算部件级规则。

发型池女性 20、男性 13；非空发型间的无向选择对分别为 190/78。在颜色固定 original 且服装允许时可加入 none，变成 21/14 值、210/91 对。非 original 发色不能在 `hair=none` 时伪造可见变化；从彩发直接变 none 若要同时重置发色，应按明确的局部规范处理，不能静默增加第二语义变化。

## 6. 有限预算扩展，不强连全衣柜

**路线 A：多域覆盖优先。**在支持核心变化的 29 个 group 各取一个合法 anchor，冻结一个身份/动作/镜头/场景/鞋/发型上下文，再沿每个核心槽单独替换值。星形覆盖上界为女 **112**、男 **69**，合计 **181 节点**，即可在注册层覆盖 55 个核心槽域的单轴值；这是构造预算上界，不是唯一节点最终数，规范化去重与 resolver/视觉仍需验证。再给其余 17 个固定核心 group 各一个 anchor，总上界 198。

星形图的不同轴通过 anchor 连接，若禁止重复输出状态，单靠星形不保证长 session 或分支容量。优先为每域补少量两轴方形/小矩形：例如同一服装槽两值 × 同域动作两值，或有两服装槽的 group 各取两值，保留原子边与新端点复用；不必把同一族所有槽全做乘积。

**路线 B：核心+鞋/配饰分层。**在上述所有 46 个组 anchor 和核心星形上，沿鞋轴覆盖其合法值，额外节点上界 **250**；独立可选配饰按组开关再加 **10**，合计一个冻结视觉上下文的上界 **458 节点**。它扩大的是目录覆盖，仍不是多身份、多场景全面泛化；鞋用脚可见的镜头，发型另选头部可辨镜头，不为统一相机牺牲可观察性。

**路线 C：跨上下文复验，限制 family 桥。**用剩余预算选择少量代表域扩到多个身份/动作/场景，重点验分体/full_body/optional/locked/hairdeny 五种接口形态。多个域可共享相同 identity/action 值，但服装配置不同，因此视频端点仍分别计预算；不能因为身份和动作相同就把整条视频当同节点。仅在两端完整解析配置只差所选契约允许字段时登记跨 group/family 边，不为图全局连通强造边。

**路线 D：并列 outfit-level 小图。**直接在有代表性的完整 outfit 值间做整体衣服编辑，冻结头发/身份/场景，并明确 footwear/accessory 是否包含在 outfit 属性。将 bundle 与分体整套都纳入，另报这个契约下的保持性；它补充当前 piece-level 结果，而不是让已有单槽数字自动覆盖全套变化。

建议汇报“在哪些 family/group/槽、哪些冻结上下文通过”，并对未覆盖的接口形态设清单。不能仅在方便的 16 full_body+5 pants 上得到 15,000 session，就把实例数量当成完整衣柜广度。

## 7. 来源与验证边界

读取了 `formal_wardrobe_registry_v1.py` 的选择/冲突/发型规则，`complete_character_slot_review_contract_v1.py` 的 slot 规范与 preset 快捷性质，`appearance_selection_policy_v1.py` 的 RedSoul overlay，以及 `scene_site_review_panel_v1.py` 的 hair 保留与禁发逻辑。正式 runtime 使用发布目录和 overlay；本轮没有重新执行 resolver、导入或渲染，也没有把这些旧源码路径当 UE 运行现场。

`analyze_wardrobe_domains.py` 只做槽、值对、小量 preset 对计数；`validate_wardrobe_domains.py` 核验汇总和预算公式。当前 exported catalog 中暴露资产、历史 registry 全资产、preset 引用资产、mesh 数是不同口径，不互相替代。
