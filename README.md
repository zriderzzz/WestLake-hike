# WestLake-hike

西湖群山 GPX 轨迹地图。

## 使用方式

网站读取 `tracks.geojson`，因此打开速度较快。

## 以后如何新增轨迹

1. 把新的 `.gpx` 文件上传到 `tracks/` 文件夹。
2. 文件名建议用日期开头，例如：

```text
2026-06-20-北高峰-灵隐.gpx
```

3. 上传并 `Commit changes` 后，GitHub Actions 会自动运行，重新生成：

```text
tracks.geojson
tracks.json
```

4. 等 1–3 分钟后刷新网站即可。

## 如何查看自动任务是否成功

进入仓库顶部的 `Actions`，点击最新的 `Build tracks GeoJSON`。如果是绿色对勾，说明成功。

## 隐私说明

自动脚本会删除 GPX 里的轨迹点精确时间，只保留路线坐标、文件日期和轨迹名称。
