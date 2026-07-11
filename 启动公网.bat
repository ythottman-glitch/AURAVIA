@echo off
chcp 65001 >nul
setlocal
title AURAVIA public launch
cd /d "%~dp0"

set "LOG=%~dp0startup.log"
echo [%date% %time%] START >> "%LOG%"

REM ---- paths ----
set "BK=%~dp0backend"
set "VENV=%BK%\.venv"
set "PY=%VENV%\Scripts\python.exe"
set "UV=C:\Users\ytcbw\AppData\Local\hermes\bin\uv.exe"

echo ============================================
echo    AURAVIA - start backend + public tunnel
echo ============================================
echo log: %LOG%
echo.

REM ---- 1. venv ----
cd /d "%BK%"
echo [%date% %time%] check venv >> "%LOG%"
if not exist "%PY%" (
  echo [1/4] creating venv...
  "%UV%" venv "%VENV%" >> "%LOG%" 2>&1
)
echo [%date% %time%] PY=%PY% >> "%LOG%"

REM ---- 2. deps (use uv pip, no need for venv pip) ----
echo [2/4] installing deps...
"%UV%" pip install --python "%PY%" -r "%BK%\requirements.txt" >> "%LOG%" 2>&1
echo [%date% %time%] deps done >> "%LOG%"

REM ---- 3. backend ----
echo [3/4] starting backend on :8000 ...
start "AURAVIA-backend" /min "%PY%" -m uvicorn server:app --host 0.0.0.0 --port 8000
ping -n 7 127.0.0.1 >nul
curl -sS -m 5 -o nul -w "backend health: HTTP %{http_code}\n" http://localhost:8000/api/health >> "%LOG%" 2>&1

REM ---- 4. tunnel ----
cd /d "%~dp0"
if not exist cloudflared.exe (
  echo downloading cloudflared...
  curl -sL -o cloudflared.exe https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe >> "%LOG%" 2>&1
)
echo [4/4] starting public tunnel...
echo ============================================
echo    getting https://xxxx.trycloudflare.com
echo    address will be saved to Desktop + popup
echo    DO NOT CLOSE this window
echo ============================================
echo.
start "AURAVIA-tunnel" /min "%~dp0tunnel_only.bat"
echo [%date% %time%] tunnel started >> "%LOG%"

set "ADDR="
for /l %%i in (1,1,30) do (
  for /f "tokens=*" %%l in ('powershell -NoProfile -Command "Get-Content \"%~dp0tunnel.log\" -ErrorAction SilentlyContinue | Select-String -Pattern \"https://[a-z0-9-]+\.trycloudflare\.com\" | ForEach-Object { $_.Matches.Value } | Select-Object -First 1"') do set "ADDR=%%l"
  if defined ADDR goto :found
  ping -n 3 127.0.0.1 >nul
)
:found
if defined ADDR (
  echo PUBLIC URL: %ADDR%
  echo %ADDR% > "%USERPROFILE%\Desktop\AURAVIA-URL.txt"
  echo [%date% %time%] URL=%ADDR% >> "%LOG%"
  echo saved to Desktop: AURAVIA-URL.txt
  powershell -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show('AURAVIA public URL:' + [char]10 + [char]10 + '%ADDR%' + [char]10 + [char]10 + '(also saved to Desktop AURAVIA-URL.txt)' + [char]10 + 'Keep this window open.','AURAVIA Ready')"
) else (
  echo failed to get URL, see startup.log
  echo [%date% %time%] no URL >> "%LOG%"
)
echo.
echo [done] running. Press any key to close this notice.
pause
endlocal
