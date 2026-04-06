#!/usr/bin/env python3
"""
harnessgenj_hook.py - Claude Code Hooks 桥接脚本 (自动生成)

功能:
1. PostToolUse: 自动记录文件操作到开发日志，触发对抗审查
2. PreToolUse: 安全检查，检测敏感信息泄露

此文件由 HarnessGenJ 自动生成

Claude Code Hooks 输入规范:
- stdin 传递完整 JSON 对象: {"tool_name": "...", "tool_input": {...}, "tool_response": {...}}
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Any


# 全局缓存，避免重复读取 stdin
_hook_input_cache: dict | None = None


def read_hook_input() -> dict:
    """
    从 stdin 读取完整的 Claude Code Hooks JSON 对象（带缓存）

    Claude Code 官方规范:
    stdin 传递完整 JSON 对象结构:
    {
        "tool_name": "Write" | "Edit" | "Bash" | ...,
        "tool_input": {
            "file_path": "/path/to/file",
            "content": "...",
            ...
        },
        "tool_response": {...}  # 仅 PostToolUse 有此字段
    }

    Returns:
        dict: 完整的 hook 输入对象，解析失败返回空 dict
    """
    global _hook_input_cache

    if _hook_input_cache is not None:
        return _hook_input_cache

    # stdin 可能已被读取过（多次调用同一 hook）
    if not sys.stdin.isatty():
        try:
            stdin_content = sys.stdin.read().strip()
            if stdin_content:
                _hook_input_cache = json.loads(stdin_content)
                return _hook_input_cache
        except (json.JSONDecodeError, Exception):
            pass

    # 备用方案：从环境变量获取（某些版本可能使用）
    tool_input_env = os.environ.get("TOOL_INPUT", "")
    if tool_input_env:
        try:
            parsed = json.loads(tool_input_env)
            # 封装成标准格式
            _hook_input_cache = {
                "tool_name": os.environ.get("TOOL_NAME", ""),
                "tool_input": parsed,
                "tool_response": {},
            }
            return _hook_input_cache
        except json.JSONDecodeError:
            pass

    _hook_input_cache = {}
    return {}


def get_tool_name() -> str:
    """
    从 stdin JSON 中获取 tool_name 字段

    Returns:
        str: 工具名称（如 "Write", "Edit", "Bash" 等）
    """
    hook_input = read_hook_input()

    # 优先从 stdin JSON 获取
    if "tool_name" in hook_input:
        return hook_input["tool_name"]

    # 备用：从环境变量获取
    return os.environ.get("TOOL_NAME", "")


def get_tool_input() -> dict:
    """
    从 stdin JSON 中获取 tool_input 字段

    Claude Code 官方规范:
    tool_input 包含工具调用的参数，如:
    - Write: {"file_path": "...", "content": "..."}
    - Edit: {"file_path": "...", "old_string": "...", "new_string": "..."}
    - Bash: {"command": "...", "timeout": ...}

    Returns:
        dict: 工具输入参数
    """
    hook_input = read_hook_input()

    # 优先从 stdin JSON 的 tool_input 字段获取
    if "tool_input" in hook_input:
        return hook_input["tool_input"]

    # 备用方案：尝试从命令行参数获取
    if len(sys.argv) > 2:
        arg = sys.argv[2]
        try:
            return json.loads(arg)
        except json.JSONDecodeError:
            # 可能是文件路径
            if arg.startswith("/") or arg.startswith("\\") or ":" in arg:
                return {"file_path": arg}
            return {"content": arg}

    return {}


def get_project_root() -> Path:
    """获取项目根目录"""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if project_dir:
        return Path(project_dir)
    script_path = Path(__file__).resolve()
    return script_path.parent.parent


def get_tool_response() -> dict:
    """
    从 stdin JSON 中获取 tool_response 字段（仅 PostToolUse 有效）

    Returns:
        dict: 工具响应结果
    """
    hook_input = read_hook_input()
    return hook_input.get("tool_response", {})


def append_to_development_log(content: str, context: str = "Hooks") -> bool:
    """追加内容到开发日志"""
    try:
        workspace = get_project_root() / ".harnessgenj"
        dev_log_path = workspace / "documents" / "development.md"
        dev_log_path.parent.mkdir(parents=True, exist_ok=True)

        if not dev_log_path.exists():
            dev_log_path.write_text(
                "# 开发日志\n\n此文件由 HarnessGenJ Hooks 自动维护。\n\n---\n",
                encoding="utf-8"
            )

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"\n## [{timestamp}] [{context}]\n\n{content}\n\n---\n"
        with open(dev_log_path, "a", encoding="utf-8") as f:
            f.write(entry)
        return True
    except Exception:
        return False


def trigger_adversarial_review(file_path: str, content: str) -> dict[str, Any]:
    """
    触发对抗性审查（记录到积分系统）

    Args:
        file_path: 文件路径
        content: 文件内容

    Returns:
        审查结果
    """
    result = {
        "file": file_path,
        "review_triggered": False,
        "issues": [],
    }

    # 检查是否是代码文件
    code_extensions = ['.py', '.java', '.kt', '.js', '.ts', '.tsx', '.go', '.rs']
    if not any(file_path.endswith(ext) for ext in code_extensions):
        return result

    # 记录到开发日志
    lines = content.count('\n') + 1 if content else 0
    log_content = f"代码文件变更: `{file_path}` ({lines} 行)"
    append_to_development_log(log_content, context="AdversarialTrigger")

    # 更新积分系统（如果存在）
    try:
        workspace = get_project_root() / ".harnessgenj"
        scores_path = workspace / "scores.json"

        if scores_path.exists():
            with open(scores_path, "r", encoding="utf-8") as f:
                scores_data = json.load(f)

            # 添加事件记录
            event = {
                "timestamp": datetime.now().isoformat(),
                "type": "code_write",
                "file": file_path,
                "lines": lines,
                "triggered_by": "hooks",
            }
            if "events" not in scores_data:
                scores_data["events"] = []
            scores_data["events"].append(event)

            # 更新 developer 统计
            if "scores" in scores_data and "developer_1" in scores_data["scores"]:
                scores_data["scores"]["developer_1"]["total_tasks"] += 1

            with open(scores_path, "w", encoding="utf-8") as f:
                json.dump(scores_data, f, ensure_ascii=False, indent=2)

            result["review_triggered"] = True
    except Exception:
        pass

    return result


def handle_post_tool_use() -> int:
    """
    处理 PostToolUse 事件

    功能:
    1. 记录文件操作到开发日志
    2. 触发对抗性审查（更新积分系统）

    Claude Code 输入格式:
    stdin JSON: {"tool_name": "Write", "tool_input": {...}, "tool_response": {...}}
    """
    # 使用新的 stdin JSON 解析方法
    tool_input = get_tool_input()
    tool_name = get_tool_name()

    file_path = tool_input.get("file_path", tool_input.get("path", ""))
    content = tool_input.get("content", tool_input.get("new_string", ""))

    # 调试输出（帮助诊断 hooks 是否正常工作）
    print(f"[HarnessGenJ] PostToolUse 触发: tool={tool_name}, file={file_path}", file=sys.stderr)

    if not file_path:
        print("[HarnessGenJ] PostToolUse: 未获取到文件路径", file=sys.stderr)
        return 0

    # 记录操作
    action = "创建" if tool_name == "Write" else "修改"
    log_content = f"{action}文件: `{file_path}`"

    # 触发对抗性审查
    review_result = trigger_adversarial_review(file_path, content)
    if review_result["review_triggered"]:
        log_content += " [审查已触发]"

    # 输出提示信息
    print("[HarnessGenJ] 代码审查中...", file=sys.stderr)
    print(f"[HarnessGenJ] 已记录到开发日志: {file_path}", file=sys.stderr)

    return 0


def handle_pre_tool_use_security() -> int:
    """
    处理 PreToolUse 安全检查

    检测敏感信息泄露风险

    Claude Code 输入格式:
    stdin JSON: {"tool_name": "Write|Edit", "tool_input": {...}}
    """
    # 使用新的 stdin JSON 解析方法
    tool_input = get_tool_input()
    tool_name = get_tool_name()

    file_path = tool_input.get("file_path", tool_input.get("path", ""))
    content = tool_input.get("content", tool_input.get("new_string", ""))

    # 调试输出
    print(f"[HarnessGenJ] PreToolUse Security: tool={tool_name}, file={file_path}", file=sys.stderr)

    if not content:
        print("[HarnessGenJ] PreToolUse: 未获取到内容", file=sys.stderr)
        return 0

    # 高风险模式检测
    high_risk_patterns = [
        "password", "secret", "api_key", "apikey", "token",
        "credential", "private_key", "access_key", "auth"
    ]
    warnings = []
    content_lower = content.lower()

    for pattern in high_risk_patterns:
        if pattern in content_lower:
            # 检查是否是实际赋值（不是变量名或注释引用）
            if "=" in content or ":" in content:
                # 排除注释中的引用
                lines = content.split("\n")
                for line in lines:
                    if pattern in line.lower() and ("=" in line or ":" in line):
                        if not line.strip().startswith("#") and not line.strip().startswith("//"):
                            warnings.append(f"可能包含敏感信息: {pattern}")

    if warnings:
        print(f"[HarnessGenJ Security Warning] {', '.join(warnings)}", file=sys.stderr)
        print("[HarnessGenJ] 建议使用环境变量或密钥管理服务存储敏感信息", file=sys.stderr)

    return 0


def handle_flush_state() -> int:
    """
    处理 Stop 事件 - 持久化状态
    """
    try:
        workspace = get_project_root() / ".harnessgenj"
        state_path = workspace / "state.json"

        if state_path.exists():
            # 更新最后同步时间
            with open(state_path, "r", encoding="utf-8") as f:
                state = json.load(f)

            state["last_hooks_sync"] = datetime.now().isoformat()

            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)

            print("[HarnessGenJ] 状态已持久化", file=sys.stderr)
    except Exception:
        pass

    return 0


def main():
    """主入口"""
    if len(sys.argv) < 2:
        print("Usage: harnessgenj_hook.py --post|--security|--flush-state", file=sys.stderr)
        return 1

    command = sys.argv[1]

    if command == "--post":
        return handle_post_tool_use()
    elif command == "--security":
        return handle_pre_tool_use_security()
    elif command == "--flush-state":
        return handle_flush_state()
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
