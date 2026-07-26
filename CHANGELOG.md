# Changelog

## v0.1.3

发布日期：2026-07-26

## 新增

- YouTube、X/Twitter、小红书、Bilibili、TikTok URL自动识别
- 多平台视频URL结构校验
- 下载开始前输出平台识别结果

## 保持

- v0.1.2 命令行、剪贴板和`download.bat`入口
- YouTube下载能力
- yt-dlp核心
- Playwright Profile机制
- FFmpeg处理流程

## v0.1.2

发布日期：2026-07-26

## 新增

- Windows `download.bat` 一键下载入口
- `python main.py --clipboard` 剪贴板模式
- 仅文本剪贴板读取与空内容提示

## 保持

- v0.1.1 命令行 URL 模式
- v0.1.1 无参数交互模式
- Playwright Profile、yt-dlp 和 FFmpeg 处理流程

## v0.1.1

发布日期：2026-07-26

## 新增

- 命令行 URL 下载模式
- YouTube URL 参数校验
- 保留交互模式

## 保持

- Playwright Profile 机制
- yt-dlp 下载模块
- FFmpeg 处理流程

## 验证

- `main.py` 退出码 0
- 视频下载成功
- `metadata.json` 生成成功
- 日志生成成功
