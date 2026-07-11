"""AURAVIA Agent 核心循环 —— ReAct 式自主任务执行。

两种运行模式：
  1) 真实模式：调用任意 OpenAI 兼容 LLM，使用 function calling 自主选择工具。
  2) DEMO 模式：未配置 key 时启用，用内置脚本化规划 + 真实工具，
     完整演示「思考→搜索→观察→计算→写文件→交付」的闭环，无需任何 API key。

对外暴露 run(task) -> 生成器，产出统一的事件字典：
  {"type": "thinking"|"tool_call"|"observation"|"result"|"error", "content": ...}
"""
import json
from datetime import datetime

import config
from tools import TOOLS, TOOL_MAP, run_tool

SYSTEM_PROMPT = """你是一个名为 AURAVIA（曜维）的自主任务型 AI 智能体。你的目标是独立、可靠地完成用户交给你的任务。

工作原则：
1. 先理解任务，再制定分步计划（在内心思考，用中文或英文均可）。
2. 逐步调用工具推进：可以搜索、抓取网页、运行 Python 代码、执行 Shell、读写文件。
3. 每步都要基于上一步的观察结果做推理，必要时调整计划。
4. 善用工具：需要最新信息时搜索；需要计算/数据处理时写 Python；需要保存成果时写文件。
5. 当你确信任务已完成时，停止调用工具，给出清晰的总结与（如有）产出文件路径。

请保持高效，避免重复或无效的工具调用。最多不超过 {max_steps} 步。"""


def _tool_schemas():
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["parameters"],
            },
        }
        for t in TOOLS
    ]


# --------------------------------------------------------------------------- #
# 真实 LLM 模式
# --------------------------------------------------------------------------- #
def _real_run(task):
    try:
        from openai import OpenAI
    except ImportError:
        yield {"type": "error", "content": "未安装 openai 库，请运行 pip install openai"}
        return

    client = OpenAI(api_key=config.API_KEY, base_url=config.BASE_URL)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(max_steps=config.MAX_STEPS)},
        {"role": "user", "content": task},
    ]
    schemas = _tool_schemas()

    for step in range(1, config.MAX_STEPS + 1):
        yield {"type": "thinking", "content": f"第 {step} 步：规划中…"}
        try:
            resp = client.chat.completions.create(
                model=config.MODEL,
                messages=messages,
                tools=schemas,
                tool_choice="auto",
                temperature=0.3,
                max_tokens=config.MAX_TOKENS,
            )
        except Exception as e:
            yield {"type": "error", "content": f"调用模型失败：{e}"}
            return

        msg = resp.choices[0].message
        if not msg.tool_calls:
            # 没有工具调用 —— 视为最终答复
            yield {"type": "result", "content": msg.content or "（模型未返回内容）"}
            return

        # 把 assistant 的工具调用消息回写
        messages.append(
            {
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in msg.tool_calls
                ],
            }
        )

        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            arg_str = ", ".join(f"{k}={v!r}" for k, v in args.items())
            yield {"type": "tool_call", "content": f"🔧 调用 {name}({arg_str})"}
            result = run_tool(name, args)
            yield {"type": "observation", "content": result}
            messages.append(
                {"role": "tool", "content": str(result), "tool_call_id": tc.id}
            )

    yield {"type": "result", "content": "（已达到最大步数上限，任务中止。可在 config 中调高 MAX_STEPS。）"}


# --------------------------------------------------------------------------- #
# DEMO 模式（无需 key，用真实工具跑一个像样的闭环）
# --------------------------------------------------------------------------- #
def _demo_run(task):
    topic = task.strip() or "通用任务"
    yield {"type": "thinking", "content": f"分析任务：「{topic}」。我将通过搜索获取信息、用 Python 做整理，并把成果写入文件。"}

    yield {"type": "thinking", "content": "步骤 1/4：检索与任务相关的网络资料…"}
    yield {"type": "tool_call", "content": f"🔧 调用 web_search(query={topic!r})"}
    search_res = run_tool("web_search", {"query": topic, "k": 4})
    yield {"type": "observation", "content": search_res}

    yield {"type": "thinking", "content": "步骤 2/4：用 Python 对检索到的信息做结构化摘要与统计…"}
    yield {"type": "tool_call", "content": "🔧 调用 python(code=摘要抽取脚本)"}
    py_res = run_tool("python", {"code": DEMO_PY_CODE})
    yield {"type": "observation", "content": py_res}

    yield {"type": "thinking", "content": "步骤 3/4：把成果整理成 Markdown 报告并保存到 workspace…"}
    yield {"type": "tool_call", "content": "🔧 调用 write_file(path=report.md)"}
    report = build_report(task, search_res, py_res)
    write_res = run_tool("write_file", {"path": "report.md", "content": report})
    yield {"type": "observation", "content": write_res}

    yield {"type": "thinking", "content": "步骤 4/4：汇总并向用户交付结论。"}
    yield {
        "type": "result",
        "content": (
            f"✅ 任务「{topic}」已完成。\n\n"
            f"我执行了：网络检索 → Python 结构化处理 → 生成报告文件。\n"
            f"产出文件：`workspace/report.md`（已在左侧工作区生成）。\n\n"
            f"—— 这是 DEMO 模式（未配置 LLM key）的演示流程。\n"
            f"接入真实模型后，AURAVIA 会用 LLM 自主规划每一步、调用工具，"
            f"完成更复杂的真实任务。在 backend/.env 填入 AURAVIA_API_KEY 等即可切换。"
        ),
    }


# DEMO 模式下实际执行的 Python 脚本（纯静态、不与用户输入拼接，保证不会语法错误）
DEMO_PY_CODE = """import os, glob
ws = os.environ.get("AURAVIA_WORKSPACE", ".")
files = [f for f in glob.glob(os.path.join(ws, "*")) if os.path.isfile(f)]
print("已检索到的原始资料行数统计：")
print("工作区现有文件数:", len(files))
for f in files:
    print(" -", os.path.basename(f))
print("状态: 信息已结构化，可用于生成报告。")
"""


# 单独放一个实现，避免上面闭包问题
import textwrap as _tw


def build_report(task, search_res, py_res):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""# AURAVIA 任务报告

**任务**：{task}
**生成时间**：{now}
**模式**：DEMO（演示）

## 一、检索到的信息
```
{search_res[:1500]}
```

## 二、数据处理结果
```
{py_res[:1500]}
```

## 三、结论
本报告由 AURAVIA（曜维）自主任务型 Agent 在 DEMO 模式下生成，
用于演示「规划 → 工具调用 → 观察 → 交付」的完整闭环。
接入真实 LLM 后将具备自主推理与更复杂的执行能力。
"""


# --------------------------------------------------------------------------- #
# 统一入口
# --------------------------------------------------------------------------- #
def run(task: str):
    if config.DEMO_MODE:
        yield from _demo_run(task)
    else:
        yield from _real_run(task)
