#!/usr/bin/env python3
"""
pyha_hook.py - Claude Code Hooks 桥梁脚本 (增强版)
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime


def get_project_root() -> Path:
    """获取项目根目录"""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if project_dir:
        return Path(project_dir)
    script_path = Path(__file__).resolve()
    return script_path.parent.parent


def get_tool_input() -> dict:
    """获取工具输入参数"""
    tool_input = os.environ.get("TOOL_INPUT", "{}")
    try:
        return json.loads(tool_input)
    except json.JSONDecodeError:
        pass
    if len(sys.argv) > 1:
        for i, arg in enumerate(sys.argv):
            if arg == "--input" and i + 1 < len(sys.argv):
                try:
                    return json.loads(sys.argv[i + 1])
                except json.JSONDecodeError:
                    pass
    try:
        if not sys.stdin.isatty():
            return json.load(sys.stdin)
    except Exception:
        pass
    return {}


def get_tool_name() -> str:
    """获取工具名称"""
    return os.environ.get("TOOL_NAME", "")


def get_workspace_path() -> Path:
    """获取 HarnessGenJ 工作空间路径"""
    project_root = get_project_root()
    return project_root / ".HarnessGenJ"


def append_to_development_log(content: str, context: str = "Hooks") -> bool:
    """追加内容到开发日志"""
    try:
        workspace = get_workspace_path()
        dev_log_path = workspace / "documents" / "development.md"
        dev_log_path.parent.mkdir(parents=True, exist_ok=True)
        if not dev_log_path.exists():
            default_content = "# 开发日志\n\n此文件由 HarnessGenJ 自动维护。\n\n---\n"
            dev_log_path.write_text(default_content, encoding="utf-8")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"\n## 记录 ({timestamp}) [{context}]\n\n{content}\n\n---\n"
        with open(dev_log_path, "a", encoding="utf-8") as f:
            f.write(entry)
        return True
    except Exception as e:
        error_log = get_workspace_path() / "hooks_error.log"
        try:
            with open(error_log, "a", encoding="utf-8") as f:
                f.write(f"{datetime.now().isoformat()} - Error: {e}\n")
        except Exception:
            pass
        return False


def handle_post_tool_use() -> int:
    """处理 PostToolUse 事件"""
    tool_input = get_tool_input()
    tool_name = get_tool_name()
    file_path = tool_input.get("file_path", tool_input.get("path", ""))
    content = tool_input.get("content", tool_input.get("new_string", ""))
    if not file_path:
        return 0
    action = "创建" if tool_name == "Write" else "修改"
    record_content = f"{action}文件: `{file_path}`"
    if file_path.endswith(('.java', '.kt', '.py', '.js', '.ts', '.tsx')):
        if content:
            lines = content.count('\n') + 1
            record_content += f" ({lines} 行)"
    if content:
        summary = content[:100].replace('\n', ' ').strip()
        if len(content) > 100:
            summary += "..."
        record_content += f"\n\n摘要: {summary}"
    append_to_development_log(record_content, context=f"PostToolUse:{tool_name}")
    return 0


def handle_pre_tool_use_security() -> int:
    """处理 PreToolUse 安全检查"""
    # 从命令行参数获取内容
    content = ""
    if len(sys.argv) > 2:
        content = sys.argv[2]
    if not content:
        tool_input = get_tool_input()
        content = tool_input.get("content", tool_input.get("new_string", ""))
    if not content:
        return 0
    high_risk_patterns = ["password", "secret", "api_key", "token", "credential", "private_key"]
    warnings = []
    content_lower = content.lower()
    for pattern in high_risk_patterns:
        if pattern in content_lower:
            if "=" in content or ":" in content:
                warnings.append(f"可能包含敏感信息: {pattern}")
    if warnings:
        print(f"[HarnessGenJ Security Warning] {', '.join(warnings)}", file=sys.stderr)
    return 0


def inject_context_reminder() -> str:
    """生成上下文提醒内容"""
    return """
[HarnessGenJ 提醒] 核心方法:
- receive_request("需求") - 接收用户请求
- develop("功能") - 开发功能
- fix_bug("Bug描述") - 修复 Bug
- record("内容") - 记录开发日志
- get_status() - 查看项目状态
"""


def main():
    """主入口"""
    if len(sys.argv) < 2:
        print("Usage: pyha_hook.py --post|--security|--reminder", file=sys.stderr)
        return 1
    command = sys.argv[1]
    if command == "--post":
        return handle_post_tool_use()
    elif command == "--security":
        return handle_pre_tool_use_security()
    elif command == "--reminder":
        print(inject_context_reminder())
        return 0
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
