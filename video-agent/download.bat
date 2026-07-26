@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "VIDEO_AGENT_PYTHON=.venv\Scripts\python.exe"
if not exist "%VIDEO_AGENT_PYTHON%" (
    echo 未找到项目虚拟环境：%VIDEO_AGENT_PYTHON%
    echo 请先按照 README.md 完成安装。
    echo.
    pause
    exit /b 1
)

"%VIDEO_AGENT_PYTHON%" main.py --clipboard
set "VIDEO_AGENT_EXIT=%ERRORLEVEL%"

echo.
pause
exit /b %VIDEO_AGENT_EXIT%
