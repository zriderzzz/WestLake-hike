# WestLake-hike

目前仅供个人使用，不知道有什么别的用处。

西湖群山 GPX 轨迹地图。

## 如何新增轨迹

1. 把新的 `.gpx` 文件上传到 `tracks/` 文件夹。
2. 打开 `tracks.json`，在最后增加一条记录：

```json
{
  "id": 15,
  "date": "2026-06-20",
  "title": "北高峰—灵隐",
  "file": "tracks/2026-06-20-北高峰-灵隐.gpx",
  "visible": true
}
```

3. 保存后，GitHub Pages 会自动更新。

## 如何隐藏某条轨迹

把对应记录的：

```json
"visible": true
```

改成：

```json
"visible": false
```

## 隐私说明

本包中的 GPX 已移除轨迹点精确时间，仅保留路线坐标和日期。
