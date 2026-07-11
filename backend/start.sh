#!/usr/bin/env bash
# Render 启动脚本（备用；render.yaml 已直接写 startCommand，此文件用于本地/手动验证）
set -e
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port "${PORT:-8000}"
