# Lance Visual Review

本地可视化结果审查台。每次实验以独立 `run` 保存，主页按日期、任务和状态索引。

## 启动

在 PowerShell 中运行：

```powershell
& 'D:\UE\Lance_Work\00_engine\visualization_portal\start_portal.ps1'
```

脚本会复用健康的服务，并在服务失效时重新启动。随后打开：

```text
http://127.0.0.1:8765/00_engine/visualization_portal/
```

服务根目录是 `D:\UE\Lance_Work`，因此 `run.json` 中的产物 URL 必须以
`/00_engine/outputs/...` 等相对于该根目录的路径表示。不能直接以
`file://` 打开主页，否则浏览器无法稳定加载 JSON 和图片资源。

该服务仅监听 `127.0.0.1`，不需要互联网连接。候选审查分支会把操作实时
保存在当前浏览器的 `localStorage`；长途离线审查时仍应定期点击“导出决定”
生成 JSON。重新打开同一浏览器和端口会自动恢复进度，也可用“导入决定”
在另一浏览器中继续。

P0 剩余动画审查可直接双击 `OPEN_OFFLINE_ANIMATION_REVIEW.cmd`，具体字段与
离线边界见 [OFFLINE_ANIMATION_REVIEW.md](OFFLINE_ANIMATION_REVIEW.md)。

## 注册结果

1. 创建 `runs/<run-id>/run.json`。
2. 确保 `id` 唯一，所有资源位于 `Lance_Work` 下。
3. 注册或替换结果：

```powershell
python tools/register_run.py runs/<run-id>/run.json --replace
```

注册工具会验证结构并更新 `data/registry.json`，页面本身不需要修改。

## 校验

```powershell
python -m unittest discover -s tests -v
```
