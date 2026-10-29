# 修复视频展示发布记录

2026-10-29，用户已明确要求上传本次修复样例网页及视频。当前状态：展示包已准备、校验并提交；GitHub推送因当前终端无HTTPS写入凭据而未完成；用户视觉验收和整体数据替换仍待后续确认。

## 本次范围

[离线网页](../showcase/repair_examples_20261029/index.html)与[使用说明](../showcase/repair_examples_20261029/README.md)位于`00_engine/render_pipeline/showcase/repair_examples_20261029/`。视频真实副本24份（16动作/性别、4粉色罩衫、4动作参考），共352453683字节，均与正式production媒体摘要一致；不包含其他2322条原始渲染媒体、UE资产或缓存。此Git媒体例外仅适用于本目录。

服务器已完成2322条重渲染（2099主视频、223动作参考），696600帧严格解码，修正动作与罩衫资产核验及独立技术审查均通过。24份样例均绑定最终production，实际播放及每份3帧有限抽查已完成。完整运行证据保留在服务器`00_engine/outputs/video_v12/motion_coat_repair_20261028/`；本包仅附摘要、播放记录、抽帧和副本校验。

## 待用户判断

网页明确保留4条观察：005809举手指尖贴近上沿、000729举手接近/越过上沿、004766裙腰局部斑块、ref_1b454fe9bf33032b838abfd9前臂/手部出画。它们不是自动技术拒绝，未更改相机或扩大修复范围。002904中的035轻微重合已由用户接受，不判错；该视频只因错误罩衫资产重拍。

数据集仍为REPAIR_PENDING：原先获授权删除的1097份错误旧媒体已删除，新2322份尚未导入；剩余1225份目标旧媒体只核存在，未重算旧SHA。Git上传仅供用户查看，不表示通过视觉Gate或批准替换整体数据。

## 校验与维护

本次仅提交展示包和这次状态说明；工作区其他模型、资产清理和历史运行改动不随本次上传。展示视频SHA、24份绑定、相对播放/字体依赖、文件大小与凭据模式均须在提交前检查。`SHA256SUMS`覆盖整个展示包（自身除外）。展示包归SERVER_EXECUTION技术所有者管理，属于用户特许入Git的展示副本，不是新的运行outputs类别。

## 上传执行结果

展示内容提交：`387bd25034affe3b57186a1965625ca18a6d0fe8`。本次推送返回`could not read Password ... terminal prompts disabled`，因此尚未宣称GitHub已收到新提交；先前只读核验远端main为`57e0abaf24feb1981f7b5dbe74434a68b6d2f61d`。没有变更origin、绕过认证或使用其他身份。

提交前校验：24份视频SHA匹配，76份包内文件SHA校验通过，页面/字体相对依赖全部存在，凭据模式扫描无命中；文档审计0错误/0警告，22项unittest通过。工作区无pytest，未声称执行pytest。

用户可在服务器交互式终端完成推送（Password处输入GitHub有该仓库写入权限的访问令牌，不要将令牌发到对话）：

```bash
cd /scratch/prj0000000275/jcy/xks/DataMake
env -u GIT_ASKPASS -u SSH_ASKPASS GIT_TERMINAL_PROMPT=1 \
  git -c core.askPass= push origin HEAD:main
```

成功后须再核验远端提交并更新发布状态；这不自动批准整体数据替换。
