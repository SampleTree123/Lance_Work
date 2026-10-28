# DataMake：16条直链＋8条分叉会话展示

2026-10-28创建，随后按用户要求追加8条真实分叉会话。新增2–5轮各2条、36个视频、28次编辑，其中8次回到历史版本分叉。现共24条会话、108个互不重复节点视频、84次编辑，媒体合计约2.32GiB。分叉入口为 `branches.html`，与直链入口 `index.html` 相互链接。

初始直链要求：用户最终要求为 **2、3、4、5轮编辑各4条，共16条**，不使用1轮节选。共72个互不重复节点视频、56条编辑边；每组包含男女角色和横竖画幅。

## 查看

完整下载此文件夹后，直接用Chrome或Edge打开 `index.html`。数据通过本地 `data.js` 加载，不依赖外部服务、CDN或服务器路径。也可以在此目录运行 `python -m http.server 8767` 后访问 `http://localhost:8767/`。

网页按轮数筛选，单条链从左至右展示原始视频、编辑边和各轮结果。每个视频下方展示人物、发型、发色、衣物、动作、镜头、场景、表情、画幅及输出规格；当轮变化的属性用橙色标出。支持整链从头播放、暂停和横向翻阅，单个视频可全屏打开。整链播放不是逐帧同步播放器，网络加载差异可能导致各播放器时刻不完全一致。

## 文件组织

```text
chain_examples_20261028/
  index.html / style.css / app.js   网页
  data.js                          页面直接加载的选例数据
  examples.json                    同内容JSON：节点属性和实际编辑关系
  selection.json                   冻结的16条原始session编号
  media_manifest.json              108个MP4的大小与SHA256
  branches.html / branch_app.js    分叉图与两条路径展示
  branch_data.js / branch_examples.json  分叉节点和实际父子关系
  branch_selection.json            冻结的8条分叉会话
  media/<node_id>.mp4              108个原视频的真实副本
  posters/<node_id>.jpg            视频0.7秒预览图
  fonts/                          离线中文字体子集及许可证
```

2026-10-28用户**明确特许此展示目录的视频副本上传Git**。这些MP4为原文件的逐字节副本，不是符号链接，也不是Git LFS指针；没有重新编码。初始直链视频约1.39GiB，追加分叉视频约0.93GiB；合计2,493,413,878字节。例外仅限本文件夹，不推广到完整数据集、UE工程或其他输出。GitHub普通文件/单次推送限制已按[大文件说明](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)和[推送上限](https://docs.github.com/en/get-started/using-git/troubleshooting-the-2-gb-push-limit)核对。

## 内容来源与准确性

- 源数据是服务器 `00_engine/outputs/data_v12_20261028/{chains,nodes}.json`；两份源JSON的SHA256保存在examples.json，不需要复制整个数据集到本页。
- 直链页的16条是原会话中的完整、无分叉直链；原session/node编号不变，不把分叉误画成连续编辑，也没有拼接不相关的视频。
- 编辑说明由真实source/target的属性差异生成，核验为单一编辑轴变化。服装额外列出增删部件的精确ID；其他节点属性保持的说明指元数据约束，不是对每个像素不变的保证。
- 正式训练prompt与参考图片尚待上传。本页文字是**真实编辑差异说明**，不是原训练prompt；不展示尚未上传的参考素材。所有视频均为UE数据，不是模型推理结果。
- 动作中文名称来自随上传工作区保存的production motion catalog；发型保留HAIR编号及真实网格部件名称，服装保留源资产label及ID，避免凭空编造外观描述。
- 为本次展示保守排除全部 `female.bikini_ruana` 及此前重点排查的三个动作M04、M05、035。用户已在本地定位先前问题并确认大部分数据不受影响，具体修复仍由本地推进；排除策略不是全数据质量判定。

## 分叉页面

8条分叉会话不拆成伪直链。每例上方用SVG标出真实父子关系，虚线标记回到历史版本的那次编辑；下方按两个叶节点展开两条完整路径。V编号按会话生成顺序递增，父节点由原始source_history_occurrence决定，共享前缀重复显示同一个视频文件。每条边的属性差异相对于真正父节点计算，不与时间上最近生成的兄弟视频比较。

追加生成工具为 `00_engine/render_pipeline/tools/server/build_branch_showcase.py`，复用原工具的属性解释和媒体校验函数。新增视频为真实副本，没有重渲染；参考媒体和正式prompt仍未加入。

## 复现和校验

生成工具：`00_engine/render_pipeline/tools/server/build_chain_showcase.py`。已有selection.json时保持选例不变。服务器有原始数据与上传catalog时可运行：

```bash
python 00_engine/render_pipeline/tools/server/build_chain_showcase.py --copy-media
```

仅用冻结examples.json准备媒体，无需原始catalog：

```bash
python 00_engine/render_pipeline/tools/server/build_chain_showcase.py \
  --link-only --copy-media --dataset /path/to/data_v12_20261028 \
  --output /path/to/chain_examples_20261028
```

不会覆盖或删除源数据。通过 `media_manifest.json` 可独立核对副本SHA256。浏览器检查截图、临时检查脚本和额外抽帧位于本机 `validation/`，不上传Git。

这是一个内部展示选例包。用户授权上传本包不改变源资产既有许可证范围，也不等于完整数据集发布验收。
