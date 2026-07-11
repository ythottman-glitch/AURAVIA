@echo off
chcp 65001 >nul
title AURAVIA 曜维 · 一键上线
cd /d "%~dp0"

echo ============================================
echo    AURAVIA 曜维 - 一键上线（后端 + 公网隧道）
echo ============================================
echo.

REM ---- 1. 准备后端虚拟环境 ----
cd /d "%~dp0backend"
if not exist .venv (
  echo [1/4] 首次运行，创建虚拟环境...
  uv venv .venv
)
call .venv\Scripts\activate.bat
echo [2/4] 安装/校验依赖...
uv pip install -r requirements.txt >nul 2>&1

REM ---- 2. 后台启动后端 ----
echo [3/4] 启动后端服务 http://localhost:8000 ...
start "AURAVIA-后端" /min cmd /c "call .venv\Scripts\activate.bat && uvicorn server:app --host 0.0.0.0 --port 8000"

REM 等后端起来
timeout /t 5 >nul

REM ---- 3. 启动公网隧道 ----
cd /d "%~dp0"
if not exist cloudflared.exe (
  echo    下载 cloudflared...
  curl -sL -o cloudflared.exe https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe
)
echo [4/4] 启动公网隧道，稍等几秒会显示 https://xxxx.trycloudflare.com 地址
echo.
echo ============================================
echo   下面出现的 https://....trycloudflare.com
echo   就是你的公网地址，手机/别人都能打开！
echo   ★ 本窗口不要关闭，关了链接就失效 ★
echo ============================================
echo.
cloudflared.exe tunnel --url http://localhost:8000
pause
