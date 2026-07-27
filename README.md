# Video Agent

当前版本：**v0.2.0（开发中）**

Video Agent 是一个运行在 Windows 本机的视频采集基础工程。当前稳定基线包含
Playwright 可见浏览器控制、Chrome persistent Profile 复用、多平台URL
校验、yt-dlp 下载、FFmpeg 音视频合并、metadata 和日志记录。

v0.2.0 在现有下载链路上增加JSON任务队列、顺序下载Worker和资产登记，
不改变下载器核心及浏览器机制。

当前识别：

- YouTube
- X/Twitter
- 小红书
- Bilibili
- TikTok

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
python main.py "VIDEO_URL"
```

交互模式：

```powershell
python main.py
```

剪贴板模式：

```powershell
python main.py --clipboard
```

也可以先复制受支持平台的视频URL，再双击项目根目录的 `download.bat`。批处理会
自动进入项目目录，调用 `.venv\Scripts\python.exe`，并在结束后保留窗口供
查看下载文件路径。

添加下载任务：

```powershell
python main.py --add "VIDEO_URL"
```

执行全部pending任务：

```powershell
python main.py --queue
```

如果没有激活虚拟环境，Windows 下使用明确入口：

```powershell
.\.venv\Scripts\python.exe main.py "VIDEO_URL"
.\.venv\Scripts\python.exe main.py
```

无参数运行会按既有机制打开可见Chrome和YouTube登录页，然后可在终端输入
任一受支持平台的视频URL。登录状态由本机Profile复用。经用户明确授权后，yt-dlp会直接
读取该本机 Profile，不生成 `cookies.txt`，也不把 Cookie 内容写入项目日志。

当前配置使用本机已安装的 Chromium-based Chrome（`channel: chrome`）。
如需改用 Playwright 自带 Chromium，先执行安装命令，再删除该配置项。

下载结果按媒体ID存入 `D:\Media\video-downloads\<media_id>\`：

- 合并后的 MP4 视频
- `metadata.json`

日志写入 `D:\Media\video-downloads\logs\`。任务状态保存在
`D:\Media\video-downloads\runtime\tasks.json`，资产索引保存在
`D:\Media\video-downloads\runtime\registry.json`。仓库中的
`task_queue/tasks.example.json` 和 `assets/registry.example.json` 只作为空模板。

## 项目结构

```text
video-agent/
├── browser/                 # Playwright persistent browser
├── downloader/              # yt-dlp download and FFmpeg merge
├── platform/detector.py     # Multi-platform URL detection
├── utils/                   # Windows text clipboard reader
├── task_queue/              # JSON task queue code and empty template
├── worker/                  # Sequential download worker
├── assets/                  # Asset registry code and empty template
├── config/settings.yaml     # Browser and download settings
├── CHANGELOG.md
├── VERSION
├── download.bat             # Double-click clipboard download entry
├── requirements.txt
└── main.py                  # CLI and interactive entry point
```

## 当前能力边界

v0.2.0 只负责手动添加任务、顺序执行下载和登记资产，不包含频道扫描、
自动发现、Whisper、GPT、Agent、MCP、Web UI、数据库服务器或自动调度。
