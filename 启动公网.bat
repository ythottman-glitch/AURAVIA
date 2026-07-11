@echo off
chcp 65001 >nul
title AURAVIA 曜维 · 启动公网（地址会弹窗+写文件）
cd /d "%~dp0"

echo ============================================================
echo    AURAVIA 曜维 —— 本地后端 + 公网隧道一键启动
echo ============================================================
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
start "AURAVIA-后端" /min cmd /c "call .venv\Scripts\activate.bat && python -m uvicorn server:app --host 0.0.0.0 --port 8000"
timeout /t 5 >nul

REM ---- 3. 启动公网隧道，并把地址抓出来 ----
cd /d "%~dp0"
if not exist cloudflared.exe (
  echo    下载 cloudflared...
  curl -sL -o cloudflared.exe https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe
)

echo [4/4] 启动公网隧道... 稍等几秒会获取地址
echo.
echo ============================================================
echo   正在获取 https://xxxx.trycloudflare.com 公网地址
echo   获取后自动写入桌面「AURAVIA公网地址.txt」并弹窗
echo   ★ 本窗口不要关闭，关了链接就失效 ★
echo ============================================================
echo.

REM 启动隧道，输出写入 tunnel.log
start "AURAVIA-隧道" /min cmd /c "cloudflared.exe tunnel --url http://localhost:8000 > \"%~dp0tunnel.log\" 2>&1"

REM 轮询日志，等出现 trycloudflare.com 地址（最多 60 秒）
set "ADDR="
for /l %%i in (1,1,30) do (
  for /f "tokens=*" %%l in ('powershell -NoProfile -Command "(Get-Content \"%~dp0tunnel.log\" -ErrorAction SilentlyContinue | Select-String -Pattern 'https://[a-z0-9-]+\.trycloudflare\.com' | ForEach-Object { $_.Matches.Value } | Select-Object -First 1)"') do set "ADDR=%%l"
  if defined ADDR goto :found
  timeout /t 2 >nul
)
:found
if defined ADDR (
  echo 公网地址: %ADDR%
  echo %ADDR% > "%USERPROFILE%\Desktop\AURAVIA公网地址.txt"
  echo 已写入桌面: AURAVIA公网地址.txt
  powershell -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show('AURAVIA 公网地址：\n\n%ADDR%\n\n（已同时写入桌面 AURAVIA公网地址.txt）\n手机/别人打开这个网址即可。\n保持本窗口开启，关闭则链接失效。','AURAVIA 曜维 · 公网已就绪')"
) else (
  echo 未能自动获取地址，请查看 tunnel.log
  notepad "%~dp0tunnel.log"
)
pause
