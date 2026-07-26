# Video Agent

当前版本：**v0.1.1**

Video Agent 是一个运行在 Windows 本机的视频采集基础工程。当前稳定基线包含
Playwright 可见浏览器控制、Chrome persistent Profile 复用、YouTube URL
校验、yt-dlp 下载、FFmpeg 音视频合并、metadata 和日志记录。

## 安装

PowerShell：

```powershell
C:\Users\minzh\AppData\Local\Python\bin\python.exe -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
```

项目默认使用本机已安装的 Chromium-based Chrome。只有切换到 Playwright
自带 Chromium 时才需要执行最后一条浏览器安装命令。

## 配置

编辑 `config/settings.yaml`。默认浏览器 Profile 位于：

```text
%LOCALAPPDATA%/video-agent/browser-profile
```

该目录在项目之外。不要复制、上传或提交它。

`download.cookies_from_browser` 控制 yt-dlp 是否直接复用该本机 Profile。
启用时程序会在下载前关闭 Chrome，避免 Windows Profile 锁定；不会导出或
保存 Cookie 文件到项目中。只有在明确授权后才应启用该项。

## 运行

命令行 URL 模式：

```powershell
python main.py "YouTube_URL"
```

交互模式：

```powershell
python main.py
```

如果没有激活虚拟环境，Windows 下使用明确入口：

```powershell
.\.venv\Scripts\python.exe main.py "YouTube_URL"
.\.venv\Scripts\python.exe main.py
```

无参数运行会打开可见 Chrome，可在窗口中手动登录 YouTube，然后在终端输入
视频 URL。登录状态由本机 Profile 复用。经用户明确授权后，yt-dlp 会直接
读取该本机 Profile，不生成 `cookies.txt`，也不把 Cookie 内容写入项目日志。

当前配置使用本机已安装的 Chromium-based Chrome（`channel: chrome`）。
如需改用 Playwright 自带 Chromium，先执行安装命令，再删除该配置项。

下载结果按 YouTube 视频 ID 存入 `data/downloads/<video_id>/`：

- 合并后的 MP4 视频
- `metadata.json`

日志写入 `data/logs/`。

## 项目结构

```text
video-agent/
├── browser/                 # Playwright persistent browser
├── downloader/              # yt-dlp download and FFmpeg merge
├── config/settings.yaml     # Browser and download settings
├── data/
│   ├── downloads/           # Generated media and metadata (ignored)
│   └── logs/                # Runtime logs (ignored)
├── CHANGELOG.md
├── VERSION
├── requirements.txt
└── main.py                  # CLI and interactive entry point
```

## 当前能力边界

v0.1.1 只负责单个 YouTube URL 的浏览器登录状态复用、校验和下载，不包含
频道扫描、Whisper、GPT、Agent、MCP、自动剪辑、发布或调度。
