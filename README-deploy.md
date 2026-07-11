# AURAVIA 部署到 Render（拿固定公网网址）

目标：得到一个 **固定不变的 `https://auravia.onrender.com`**，手机 / 任意电脑浏览器打开即用，
后端常驻、无需本机开机。

---

## 前置条件
- 一个 GitHub 账号（把代码推上去）
- 一个邮箱（注册 Render，免费）

> 若你暂未登录 GitHub CLI，下面用「网页手动推」的方式，零命令行门槛。

---

## 步骤 1：把代码推到 GitHub

1. 打开 https://github.com/new
2. Repository name 填 `auravia`，选 **Public**，点 **Create repository**
3. 在本机 `auravia` 文件夹里，右键 → Git Bash Here，执行：
   ```bash
   git init
   git add .
   git commit -m "AURAVIA MVP: autonomous agent + Render deploy"
   git branch -M main
   git remote add origin https://github.com/<你的用户名>/auravia.git
   git push -u origin main
   ```
   第一次 push 会弹窗要你登录 GitHub，按提示授权即可。

---

## 步骤 2：在 Render 一键拉起服务

1. 打开 https://render.com ，用 GitHub 登录（点 "Sign In" → 选 GitHub）
2. 右上角 **New** → **Blueprint**
3. 连上你的 GitHub，选中 `auravia` 仓库 → **Connect**
4. Render 会自动读取仓库根目录的 `render.yaml`，显示要创建的服务 `auravia`（free 计划）
5. 点 **Apply** / **Create**

部署会自动：
- `pip install -r requirements.txt`
- 启动 `uvicorn server:app --host 0.0.0.0 --port $PORT`
- 健康检查 `/api/health`

约 1–2 分钟后，Render 给你的固定地址形如：
```
https://auravia.onrender.com
```
手机扫码或别的电脑直接打开即可。

> ⚠️ 免费计划有「冷启动」：闲置约 15 分钟后会休眠，下次访问需等 ~50 秒唤醒，
> 之后一直正常。这是 Render free 的免费特性，属正常。

---

## 步骤 3（可选）：接真实 LLM，关闭 DEMO 模式

默认部署后是 **DEMO 模式**（免 key，用脚本化流程演示闭环，能跑但不能真正自主推理）。

要获得真正自主的智能体：
1. Render 控制台 → 你的 `auravia` 服务 → **Environment**
2. 添加变量：
   - `AURAVIA_API_KEY` = 你的 OpenAI / DeepSeek / OpenRouter key
   - `AURAVIA_BASE_URL` = `https://api.openai.com/v1`（或对应厂商）
   - `AURAVIA_MODEL` = `gpt-4o`（或对应模型名）
3. 保存 → 服务自动重启
4. 打开网站，右上角徽标会从「DEMO 演示模式」变成「真实模式 · <模型名>」

---

## 本地运行（开发 / 调试）

```bash
cd backend
python -m venv .venv && .venv\Scripts\activate      # Windows
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8000
# 浏览器打开 http://localhost:8000
```

前端与后端同源（同一份 `uvicorn` 服务既跑 API 又托管 `frontend/`），
无需任何跨域 / 代理配置。`frontend/config.js` 里 `AURAVIA_API_BASE` 留空即可。

---

## 排错

| 现象 | 原因 / 解决 |
|------|------------|
| 打开网址白屏 | 服务在冷启动，等 30–60 秒刷新；或看 Render 日志 |
| `/api/run` 报 500 | 本地测试时若用 curl 发中文，需保证 UTF-8；浏览器无此问题 |
| 一直 DEMO 模式 | 没配 `AURAVIA_API_KEY`，见步骤 3 |
| 部署失败 | 看 Render Build Log，通常是依赖没装全（已含 python-dotenv） |
