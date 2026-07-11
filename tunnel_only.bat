@echo off
chcp 65001 >nul
cd /d "%~dp0"
"%~dp0cloudflared.exe" tunnel --url http://localhost:8000 > "%~dp0tunnel.log" 2>&1
