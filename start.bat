@echo off
chcp 65001 >nul
REM ===== AURAVIA 一键启动（Windows） =====
REM 双击本文件即可启动后端 + 打开浏览器访问 http://localhost:8000
title AURAVIA (曜维) 启动中…

cd /d "%~dp0backend"

REM 创建 / 使用虚拟环境
if not exist .venv (
  echo [1/3] 创建虚拟环境…
  uv venv .venv
)
call .venv\Scripts\activate.bat

REM 安装依赖
echo [2/3] 安装依赖（首次较慢）…
uv pip install -r requirements.txt

REM 加载 .env（若存在）
if exist .env (
  for /f "usebackq tokens=1,* delims==" %%a in (.env) do (
    if not "%%a"=="" if not "%%a:~0,1%"=="#" set "%%a=%%b"
  )
)

REM 启动服务
echo [3/3] 启动 AURAVIA 服务 → http://localhost:8000
start "" http://localhost:8000
uvicorn server:app --host 0.0.0.0 --port 8000
pause
