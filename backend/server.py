"""AURAVIA FastAPI 服务 —— 提供 SSE 流式任务接口，并托管前端静态页面。"""
import json
import time
import asyncio

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

import config
from agent import run

app = FastAPI(title="AURAVIA (曜维) Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = config.WORKSPACE.parent.parent / "frontend"
INDEX_HTML = FRONTEND_DIR / "index.html"


def _sse(event: dict):
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "demo": config.DEMO_MODE,
        "model": config.MODEL,
        "workspace": str(config.WORKSPACE),
    }


@app.post("/api/run")
async def run_task(request: Request):
    """接收 {task: "..."}，以 SSE 流式返回 Agent 每一步事件。"""
    body = await request.json()
    task = body.get("task", "").strip()
    if not task:
        return StreamingResponse(
            iter([_sse({"type": "error", "content": "任务内容为空"})]), media_type="text/event-stream"
        )

    async def event_stream():
        yield _sse({"type": "start", "content": task})
        loop = asyncio.get_event_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def producer():
            try:
                for ev in run(task):
                    asyncio.run_coroutine_threadsafe(queue.put(ev), loop)
            except Exception as e:  # noqa
                asyncio.run_coroutine_threadsafe(
                    queue.put({"type": "error", "content": f"运行时异常：{e}"}), loop
                )
            finally:
                asyncio.run_coroutine_threadsafe(queue.put(None), loop)

        loop.run_in_executor(None, producer)
        while True:
            ev = await queue.get()
            if ev is None:
                break
            yield _sse(ev)
            await asyncio.sleep(0.05)
        yield _sse({"type": "done", "content": ""})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/")
def index():
    if INDEX_HTML.exists():
        return FileResponse(str(INDEX_HTML))
    return {"error": "前端未找到，请确认 frontend/index.html 存在"}


@app.get("/config.js")
def config_js():
    cfg = FRONTEND_DIR / "config.js"
    if cfg.exists():
        return FileResponse(str(cfg), media_type="application/javascript")
    return {"error": "config.js 未找到"}


@app.get("/workspace/{path:path}")
def serve_workspace(path: str):
    """浏览 workspace 内生成的文件。"""
    from pathlib import Path

    target = (config.WORKSPACE / path).resolve()
    if str(target).startswith(str(config.WORKSPACE)) and target.exists():
        return FileResponse(str(target))
    return {"error": "not found"}


@app.get("/{full_path:path}")
def spa_fallback(full_path: str):
    """兜底：未匹配的路径回退到首页（SPA 风格）。"""
    if INDEX_HTML.exists():
        return FileResponse(str(INDEX_HTML))
    return {"error": "前端未找到"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
