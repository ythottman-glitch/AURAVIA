"""AURAVIA 工具集 —— 所有工具都是真实可用、无需付费 API key 的本地/联网能力。

工具以注册表形式暴露给 Agent，每个工具都有 JSON Schema 描述，
便于 LLM 理解如何调用。返回结果均为字符串（交给模型续写）。
"""
import os
import json
import subprocess
import textwrap
import re
import shutil
from pathlib import Path

import requests
from bs4 import BeautifulSoup

import config

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}


# --------------------------------------------------------------------------- #
# 工具实现
# --------------------------------------------------------------------------- #
def _safe_workspace_path(p: str) -> Path:
    """把相对路径限制在 workspace 内，防止越权访问。"""
    target = (config.WORKSPACE / p).resolve()
    if not str(target).startswith(str(config.WORKSPACE)):
        raise ValueError(f"路径越界: {p}")
    return target


def tool_web_search(query: str, k: int = 5) -> str:
    """DuckDuckGo 网页搜索（无需 key）。"""
    try:
        resp = requests.post(
            "https://lite.duckduckgo.com/lite/",
            data={"q": query, "kl": ""},
            headers=_HEADERS,
            timeout=20,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        links = soup.select("a.result-link")
        snippets = soup.select("td.result-snippet")
        for i, a in enumerate(links[:k]):
            title = a.get_text(strip=True)
            url = a.get("href", "")
            snippet = snippets[i].get_text(" ", strip=True) if i < len(snippets) else ""
            results.append(f"{i+1}. {title}\n   {url}\n   {snippet}")
        if not results:
            return "（搜索未返回结果，可换关键词重试）"
        return "\n\n".join(results)
    except Exception as e:
        return f"（搜索失败: {e}）"


def tool_web_fetch(url: str, max_chars: int = 4000) -> str:
    """抓取网页并提取正文文本（自动截断）。"""
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=25)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg"]):
            tag.decompose()
        text = soup.get_text("\n", strip=True)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text[:max_chars] + ("\n…(已截断)" if len(text) > max_chars else "")
    except Exception as e:
        return f"（抓取失败: {e}）"


def tool_python(code: str) -> str:
    """在沙箱中执行 Python 代码，返回 stdout/stderr（带超时）。"""
    tmp = config.WORKSPACE / "_sandbox.py"
    tmp.write_text(code, encoding="utf-8")
    try:
        proc = subprocess.run(
            [shutil.which("python") or "python", str(tmp)],
            cwd=str(config.WORKSPACE),
            capture_output=True,
            text=True,
            timeout=30,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        if not out.strip():
            out = "（代码已执行，无输出）"
        return out[:4000]
    except subprocess.TimeoutExpired:
        return "（执行超时 >30s，已被强制终止）"
    except Exception as e:
        return f"（执行出错: {e}）"
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass


def tool_shell(command: str) -> str:
    """执行 Shell 命令（Windows 默认 cmd）。返回输出（带超时）。"""
    if not config.ALLOW_SHELL:
        return "（Shell 已被管理员禁用）"
    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=str(config.WORKSPACE),
            capture_output=True,
            text=True,
            timeout=30,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        if not out.strip():
            out = "（命令已执行，无输出）"
        return out[:4000]
    except subprocess.TimeoutExpired:
        return "（执行超时 >30s）"
    except Exception as e:
        return f"（执行出错: {e}）"


def tool_write_file(path: str, content: str) -> str:
    """把文本写入 workspace 内的文件。"""
    try:
        p = _safe_workspace_path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"已写入 {p}（{len(content)} 字符）"
    except Exception as e:
        return f"（写入失败: {e}）"


def tool_read_file(path: str, max_chars: int = 8000) -> str:
    """读取 workspace 内的文本文件。"""
    try:
        p = _safe_workspace_path(path)
        if not p.exists():
            return f"（文件不存在: {path}）"
        text = p.read_text(encoding="utf-8", errors="replace")
        return text[:max_chars] + ("\n…(已截断)" if len(text) > max_chars else "")
    except Exception as e:
        return f"（读取失败: {e}）"


# --------------------------------------------------------------------------- #
# 注册表（供 LLM 选择）
# --------------------------------------------------------------------------- #
TOOLS = [
    {
        "name": "web_search",
        "description": "使用 DuckDuckGo 进行网页搜索，获取相关链接与摘要。当用户需要最新信息、事实核查或未知知识时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词"},
                "k": {"type": "integer", "description": "返回结果条数，默认 5"},
            },
            "required": ["query"],
        },
        "fn": tool_web_search,
    },
    {
        "name": "web_fetch",
        "description": "抓取指定网页 URL 并提取正文文本。当需要阅读某个页面的具体内容时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "目标网页 URL"},
                "max_chars": {"type": "integer", "description": "最大字符数，默认 4000"},
            },
            "required": ["url"],
        },
        "fn": tool_web_fetch,
    },
    {
        "name": "python",
        "description": "在沙箱中执行 Python 代码并返回 stdout/stderr。适合计算、数据处理、生成图表、自动化脚本等。",
        "parameters": {
            "type": "object",
            "properties": {"code": {"type": "string", "description": "要执行的 Python 代码"}},
            "required": ["code"],
        },
        "fn": tool_python,
    },
    {
        "name": "shell",
        "description": "执行 Shell 命令（Windows 为 cmd）。用于文件操作、运行程序、系统任务等。",
        "parameters": {
            "type": "object",
            "properties": {"command": {"type": "string", "description": "要执行的命令"}},
            "required": ["command"],
        },
        "fn": tool_shell,
    },
    {
        "name": "write_file",
        "description": "把文本内容写入 workspace 内的文件（相对路径）。用于保存结果、生成报告/代码。",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "相对 workspace 的文件路径"},
                "content": {"type": "string", "description": "文件内容"},
            },
            "required": ["path", "content"],
        },
        "fn": tool_write_file,
    },
    {
        "name": "read_file",
        "description": "读取 workspace 内已有的文本文件内容。",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "相对 workspace 的文件路径"},
                "max_chars": {"type": "integer", "description": "最大字符数，默认 8000"},
            },
            "required": ["path"],
        },
        "fn": tool_read_file,
    },
]

TOOL_MAP = {t["name"]: t for t in TOOLS}


def run_tool(name: str, arguments: dict) -> str:
    """分发并执行一个工具调用，返回字符串结果。"""
    tool = TOOL_MAP.get(name)
    if not tool:
        return f"（未知工具: {name}）"
    try:
        return tool["fn"](**{k: v for k, v in arguments.items() if k in tool["parameters"]["properties"]})
    except TypeError as e:
        return f"（参数错误: {e}）"
    except Exception as e:
        return f"（工具异常: {e}）"
