# AURAVIA · 曜维 — 自主任务型 AI 智能体（MVP）

像 Manus / Genspark 的自主任务型 Agent：用户给一个目标，Agent 自主完成
**规划 → 调用工具（搜索 / 抓取 / Python / Shell / 文件）→ 观察 → 反思 → 交付** 的闭环。

- 后端：FastAPI + SSE 流式推送（实时展示 Agent 每一步思考与工具调用）
- 前端：单页双语（中 / EN）深色 UI，流式卡片展示执行轨迹
- 模型：**OpenAI 兼容接口** —— 可接 OpenAI / DeepSeek / OpenRouter / 本地 Ollama
- 免 key 演示：未配置 API Key 时自动进入 **DEMO 模式**，用真实工具跑完整闭环，无需任何付费账号

---

## 一、目录结构

```
auravia/
├── start.bat            # Windows 一键启动（建环境+装依赖+开浏览器）
├── backend/
│   ├── config.py        # 配置（模型/工作区/开关）
│   ├── tools.py         # 工具集（搜索/抓取/Python/Shell/文件）
│   ├── agent.py         # ReAct 自主循环（真实 LLM + DEMO 两种模式）
│   ├── server.py        # FastAPI + SSE 接口 + 托管前端
│   ├── requirements.txt
│   ├── .env.example     # 配置模板
│   └── workspace/       # Agent 读写文件的沙箱目录
└── frontend/
    └── index.html       # 双语流式 UI（已内联 CSS/JS，单文件）
```

---

## 二、本地运行（3 种方式）

### 方式 A：一键启动（推荐 Windows 用户）
双击 `start.bat` → 自动建虚拟环境、装依赖、打开浏览器到 http://localhost:8000

### 方式 B：手动（bash / 任意平台）
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8000
# 浏览器打开 http://localhost:8000
```

### 方式 C：强制 DEMO 模式（即使有 key 也想看演示）
```bash
AURAVIA_DEMO=1 uvicorn server:app --port 8000
```

---

## 三、接入真实 LLM（关闭 DEMO，获得真正自主推理）

复制 `backend/.env.example` 为 `backend/.env`，填入：

```ini
# OpenAI
AURAVIA_BASE_URL=https://api.openai.com/v1
AURAVIA_API_KEY=sk-xxxx
AURAVIA_MODEL=gpt-4o

# 或 DeepSeek（便宜，推荐）
# AURAVIA_BASE_URL=https://api.deepseek.com/v1
# AURAVIA_API_KEY=sk-xxxx
# AURAVIA_MODEL=deepseek-chat

# 或本地 Ollama（完全免费、离线）
# AURAVIA_BASE_URL=http://localhost:11434/v1
# AURAVIA_API_KEY=ollama
# AURAVIA_MODEL=llama3.1
```

配置后重启服务，顶部状态徽标会从「DEMO 演示模式」变为「真实模式 · <模型名>」。
此时 Agent 由 LLM 自主决定每一步调用哪个工具、何时结束。

---

## 四、工具（全部免 key 真实可用）

| 工具 | 作用 |
|------|------|
| `web_search` | DuckDuckGo 联网搜索 |
| `web_fetch`   | 抓取网页正文 |
| `python`      | 沙箱执行 Python（计算 / 数据处理 / 画图） |
| `shell`       | 执行 Shell 命令（Windows=cmd） |
| `write_file` / `read_file` | 在 workspace 读写文件 |

> 安全提示：公网部署时请将 `.env` 中 `AURAVIA_ALLOW_SHELL` 设为 `0`，并限制 workspace 暴露。

---

## 五、部署到公网 HTTPS（无需打开任何厂商后台）

### 步骤 1：暴露后端（Cloudflare 隧道，免费、无需登录后台即可用）
```bash
# 安装 cloudflared（已装则跳过）
# Windows: winget install Cloudflare.cloudflared
cloudflared tunnel --url http://localhost:8000
```
终端会打印一个 `https://xxxx.trycloudflare.com` 公网地址，任何设备/网络都能访问。

### 步骤 2：把前端发到 Surge（你已有账号 intian-tech@outlook.com）
```bash
cd frontend
npm i -g surge
surge .   # 按提示登录，得到 *.surge.sh 公网地址
```
> 前端默认连 `http://localhost:8000`。若要指向公网后端，把 `index.html` 里
> `fetch("/api/...")` 改为你的 Cloudflare 公网地址（搜索 `/api` 替换即可）。

### （可选）Render / Railway 部署后端
直接把 `backend/` 作为 Python 服务部署，启动命令 `uvicorn server:app --host 0.0.0.0 --port $PORT`，
并在环境变量里填好 API Key。

---

## 六、API 用法

```bash
curl -N -X POST http://localhost:8000/api/run \
  -H "Content-Type: application/json" \
  -d '{"task":"调研 AI 智能体最新进展"}'
# 返回 text/event-stream，每条为 JSON： {"type":"thinking|tool_call|observation|result|error","content":"..."}
```

健康检查：`GET /api/health`

---

## 七、路线图（MVP 之后可扩展）

- [ ] 多轮对话 / 任务续写
- [ ] 工具结果可视化（图表、表格渲染）
- [ ] 文件浏览器侧栏 + 下载
- [ ] 子任务并行（多 Agent 协作）
- [ ] 用户中途干预（批准/拒绝某步工具调用）
- [ ] 持久化任务历史
