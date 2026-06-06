# WestLake-hike
仅自娱自乐用，西湖群山 GPX 轨迹地图。


## 如何新增轨迹

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

