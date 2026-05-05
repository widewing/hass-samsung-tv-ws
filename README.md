# Samsung TV WS Home Assistant Integration

基于 [`samsungtvws`](https://github.com/xchwarze/samsung-tv-ws-api) 的 Home Assistant 自定义集成。

## 功能

- UI 配置流添加电视。
- 设备信息：通过 `/api/v2/` REST API 创建诊断 sensor，并写入 Home Assistant 设备注册表。
  - 设备信息每 30 秒轮询一次；也可以调用 `samsung_tv_ws.get_device_info` 立即刷新。
- 常用控制服务：
  - `samsung_tv_ws.send_key`
  - `samsung_tv_ws.run_app`
  - `samsung_tv_ws.open_browser`
  - `samsung_tv_ws.send_text`
  - `samsung_tv_ws.list_apps`
  - `samsung_tv_ws.get_device_info`
- Frame TV Art Mode：
  - `switch` 实体：Art Mode 开关。
  - `number` 实体：Art brightness、Art color temperature。
  - `select` 实体：Artwork，选择后立即显示对应 artwork。
  - 服务：开启/关闭 Art Mode、列出 artwork、获取当前 artwork、上传图片、选择图片、删除图片、修改 matte、设置亮度和色温。
- App：
  - `select` 实体：App launcher，选择已安装 app 后立即启动。

## 安装

把 `custom_components/samsung_tv_ws` 复制到 Home Assistant 配置目录的 `custom_components` 下，重启 Home Assistant，然后在“设备与服务”里添加 `Samsung TV WS`。

默认端口是 `8001`。如果你的电视需要安全 websocket/token，尝试改用 `8002`。

## 注意

- Samsung 电视通常要求和 Home Assistant 在同一子网。
- 第一次 WebSocket 控制时，电视可能弹出授权提示。建议在电视上把访问通知设置为 “First Time Only”。
- `art_upload` 的 `path` 必须是 Home Assistant 容器/主机能读取到的本地路径，例如 `/config/www/art/image.png`。
