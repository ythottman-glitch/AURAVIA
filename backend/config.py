"""AURAVIA (曜维) 后端配置 —— 通过环境变量读取，无需改代码即可接入任意 OpenAI 兼容模型。"""
import os
from pathlib import Path

# 加载 .env（若存在）
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).parent / ".env")
except Exception:
    pass

# 工作区：Agent 在此目录读写文件（沙箱根）
WORKSPACE = Path(os.getenv("AURAVIA_WORKSPACE", "workspace")).resolve()
WORKSPACE.mkdir(parents=True, exist_ok=True)

# ---- LLM 配置（OpenAI 兼容）----
# 支持的接入方式（任选其一，设好对应环境变量即可）：
#   OpenAI:      AURAVIA_BASE_URL=https://api.openai.com/v1   AURAVIA_API_KEY=sk-xxx  AURAVIA_MODEL=gpt-4o
#   DeepSeek:    AURAVIA_BASE_URL=https://api.deepseek.com/v1 AURAVIA_API_KEY=sk-xxx  AURAVIA_MODEL=deepseek-chat
#   OpenRouter:  AURAVIA_BASE_URL=https://openrouter.ai/api/v1 AURAVIA_API_KEY=sk-or-xxx AURAVIA_MODEL=...
#   Ollama:      AURAVIA_BASE_URL=http://localhost:11434/v1   AURAVIA_API_KEY=ollama  AURAVIA_MODEL=llama3.1
BASE_URL = os.getenv("AURAVIA_BASE_URL", "https://api.openai.com/v1")
API_KEY = os.getenv("AURAVIA_API_KEY", "")
MODEL = os.getenv("AURAVIA_MODEL", "gpt-4o")

# DEMO 模式：未配置 API Key 时，用内置脚本化逻辑演示完整 Agent 流程（无需任何 key）
DEMO_MODE = (not API_KEY) or (os.getenv("AURAVIA_DEMO", "0") == "1")

# 单次任务最大步数（防止失控循环）
MAX_STEPS = int(os.getenv("AURAVIA_MAX_STEPS", "25"))

# 单次响应最长 token
MAX_TOKENS = int(os.getenv("AURAVIA_MAX_TOKENS", "1500"))

# 是否允许执行 shell（默认开启，谨慎用于公网部署）
ALLOW_SHELL = os.getenv("AURAVIA_ALLOW_SHELL", "1") == "1"

print(f"[AURAVIA] workspace={WORKSPACE}")
print(f"[AURAVIA] demo_mode={DEMO_MODE}  model={MODEL}  base_url={BASE_URL}")
