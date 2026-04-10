#!/usr/bin/env python3
"""
harnessgenj_hook.py - Claude Code Hooks 桥接脚本 (v1.6.0)

功能:
1. PostToolUse: 自动记录文件操作到开发日志，触发对抗审查
2. PreToolUse: 安全检查 + 框架权限检查
3. IntentDetection: 检测用户意图，引导使用框架
4. FrameworkActivation: 一句话激活框架（新增）

此文件由 HarnessGenJ 自动生成

Claude Code Hooks 输入规范:
- stdin 传递完整 JSON 对象: {"tool_name": "...", "tool_input": {...}, "tool_response": {...}}
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Any


# ==================== 意图检测配置 ====================

INTENT_PATTERNS = {
    # 框架激活 - 最高优先级
    "framework_activate": [
        r"使用HGJ框架", r"HGJ框架辅助", r"作为HGJ框架",
        r"HGJ项目经理", r"进入HGJ", r"用HGJ",
        r"启动HGJ", r"HGJ开发", r"HGJ辅助开发",
        r"使用.*框架.*开发", r"框架辅助",
    ],
    # 开发任务
    "develop": [
        r"实现.*功能", r"开发.*模块", r"添加.*特性", r"创建.*组件",
        r"构建.*系统", r"写.*代码", r"编写.*功能", r"新增.*功能"
    ],
    "fix_bug": [
        r"修复.*bug", r"修复.*问题", r"解决.*错误", r"调试.*异常",
        r"修复.*崩溃", r"解决.*bug", r"fix.*bug", r"修复.*缺陷"
    ],
    "review": [
        r"审查.*代码", r"检查.*质量", r"code\s*review", r"代码审查",
        r"检查.*代码", r"review.*code"
    ],
    "project_management": [
        r"项目.*状态", r"任务.*分配", r"进度.*报告", r"团队.*协调",
        r"项目经理", r"PM.*角色", r"进入.*角色", r"项目总览"
    ],
    "knowledge": [
        r"记住", r"记录", r"存储.*知识", r"保存.*信息", r"记住这个"
    ]
}

FRAMEWORK_SUGGESTIONS = {
    "framework_activate": """
[HGJ] 🎯 框架激活指令已识别！

请立即执行以下代码初始化框架：

```python
from harnessgenj import Harness
harness = Harness.from_project(".")
status = harness.get_status()
```

初始化后，您可以直接说：
- "实现用户登录功能"
- "修复首页加载问题"
- "查看项目进度"

框架会自动签发操作许可并生成操作指令。
""",
    "develop": "[HGJ] 检测到开发任务 → 使用: harness.develop('功能描述')",
    "fix_bug": "[HGJ] 检测到修复任务 → 使用: harness.fix_bug('问题描述')",
    "review": "[HGJ] 检测到审查任务 → 使用: harness.quick_review(code)",
    "project_management": "[HGJ] 项目管理任务 → 使用: harness.get_status()",
    "knowledge": "[HGJ] 知识存储需求 → 使用: harness.remember('key', 'value')"
}


# 全局缓存，避免重复读取 stdin
_hook_input_cache: dict | None = None


def read_hook_input() -> dict:
    """从 stdin 读取完整的 Claude Code Hooks JSON 对象（带缓存）"""
    global _hook_input_cache

    if _hook_input_cache is not None:
        return _hook_input_cache

    if not sys.stdin.isatty():
        try:
            stdin_content = sys.stdin.read().strip()
            if stdin_content:
                _hook_input_cache = json.loads(stdin_content)
                return _hook_input_cache
        except (json.JSONDecodeError, Exception):
            pass

    _hook_input_cache = {}
    return {}


def get_tool_name() -> str:
    """从 stdin JSON 中获取 tool_name 字段"""
    hook_input = read_hook_input()
    if "tool_name" in hook_input:
        return hook_input["tool_name"]
    return os.environ.get("TOOL_NAME", "")


def get_tool_input() -> dict:
    """从 stdin JSON 中获取 tool_input 字段"""
    hook_input = read_hook_input()
    if "tool_input" in hook_input:
        return hook_input["tool_input"]
    return {}


def get_project_root() -> Path:
    """获取项目根目录"""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if project_dir:
        return Path(project_dir)
    script_path = Path(__file__).resolve()
    return script_path.parent.parent


def get_tool_response() -> dict:
    """从 stdin JSON 中获取 tool_response 字段"""
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
    """触发对抗性审查"""
    result = {
        "file": file_path,
        "review_triggered": False,
        "issues": [],
    }

    code_extensions = ['.py', '.java', '.kt', '.js', '.ts', '.tsx', '.go', '.rs']
    if not any(file_path.endswith(ext) for ext in code_extensions):
        return result

    try:
        from harnessgenj import Harness
        project_root = get_project_root()

        harness = None
        try:
            harness = Harness.from_project(str(project_root))
        except Exception:
            harness = Harness(project_name=project_root.name)

        passed, issue_descriptions = harness.quick_review(content)
        result["review_triggered"] = True
        result["issues"] = [{"type": "review_issue", "message": desc} for desc in issue_descriptions]

        if issue_descriptions:
            print(f"[HarnessGenJ] 发现 {len(issue_descriptions)} 个问题", file=sys.stderr)
            for desc in issue_descriptions:
                print(f"  - {desc}", file=sys.stderr)
        else:
            print("[HarnessGenJ] 代码审查通过", file=sys.stderr)

    except ImportError:
        print("[HarnessGenJ] 框架未安装，跳过代码审查", file=sys.stderr)
    except Exception as e:
        print(f"[HarnessGenJ] 审查失败: {e}", file=sys.stderr)

    lines = content.count('\n') + 1 if content else 0
    log_content = f"代码文件变更: `{file_path}` ({lines} 行)"
    if result["issues"]:
        log_content += f"\n发现 {len(result['issues'])} 个问题"
        for issue in result["issues"]:
            log_content += f"\n  - {issue['message']}"
    append_to_development_log(log_content, context="AdversarialTrigger")

    return result


# ==================== 意图检测功能 ====================

def detect_user_intent(user_message: str) -> str | None:
    """检测用户消息中的意图"""
    if not user_message:
        return None

    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, user_message, re.IGNORECASE):
                return intent
    return None


def handle_intent_detection() -> int:
    """处理意图检测 - 在用户发送消息时引导使用框架"""
    # 尝试从环境变量或stdin获取用户消息
    user_message = os.environ.get("CLAUDE_USER_MESSAGE", "")

    if not user_message:
        hook_input = read_hook_input()
        user_message = hook_input.get("user_message", hook_input.get("prompt", ""))

    if not user_message:
        return 0

    intent = detect_user_intent(user_message)

    if intent and intent in FRAMEWORK_SUGGESTIONS:
        print(FRAMEWORK_SUGGESTIONS[intent], file=sys.stderr)

        # 尝试显示框架状态
        try:
            from harnessgenj import Harness
            harness = Harness.get_last_instance()
            if not harness:
                project_root = get_project_root()
                harness = Harness.from_project(str(project_root))

            if harness:
                leaderboard = harness.get_score_leaderboard()
                if leaderboard:
                    top = leaderboard[0]
                    print(f"[HGJ 状态] 当前最高分: {top['role_id']} = {top['score']}分", file=sys.stderr)
        except Exception:
            pass

    return 0


# ==================== Hook 处理函数 ====================

def handle_post_tool_use() -> int:
    """处理 PostToolUse 事件"""
    tool_input = get_tool_input()
    tool_name = get_tool_name()

    file_path = tool_input.get("file_path", tool_input.get("path", ""))
    content = tool_input.get("content", tool_input.get("new_string", ""))

    print(f"[HarnessGenJ] PostToolUse 触发: tool={tool_name}, file={file_path}", file=sys.stderr)

    if not file_path:
        print("[HarnessGenJ] PostToolUse: 未获取到文件路径", file=sys.stderr)
        return 0

    action = "创建" if tool_name == "Write" else "修改"
    log_content = f"{action}文件: `{file_path}`"

    review_result = trigger_adversarial_review(file_path, content)
    if review_result["review_triggered"]:
        log_content += " [审查已触发]"

    print("[HarnessGenJ] 代码审查中...", file=sys.stderr)
    print(f"[HarnessGenJ] 已记录到开发日志: {file_path}", file=sys.stderr)

    return 0


def handle_pre_tool_use_security() -> int:
    """处理 PreToolUse 安全检查 + 框架权限检查"""
    tool_input = get_tool_input()
    tool_name = get_tool_name()

    file_path = tool_input.get("file_path", tool_input.get("path", ""))
    content = tool_input.get("content", tool_input.get("new_string", ""))

    print(f"[HarnessGenJ] PreToolUse Security: tool={tool_name}, file={file_path}", file=sys.stderr)

    # ==================== 新增：框架权限检查 ====================
    # 检查是否在框架控制下执行操作
    permission_result = _check_framework_permission(file_path, tool_name)
    if permission_result["blocked"]:
        print(permission_result["message"], file=sys.stderr)
        # 返回非零值会阻止工具执行
        # 但我们不强制阻止，只是警告（让用户决定是否继续）
        # 如果需要强制阻止，可以返回 1

    if not content:
        print("[HarnessGenJ] PreToolUse: 未获取到内容", file=sys.stderr)
        return 0

    high_risk_patterns = [
        "password", "secret", "api_key", "apikey", "token",
        "credential", "private_key", "access_key", "auth"
    ]
    warnings = []
    content_lower = content.lower()

    for pattern in high_risk_patterns:
        if pattern in content_lower:
            if "=" in content or ":" in content:
                lines = content.split("\n")
                for line in lines:
                    if pattern in line.lower() and ("=" in line or ":" in line):
                        if not line.strip().startswith("#") and not line.strip().startswith("//"):
                            warnings.append(f"可能包含敏感信息: {pattern}")

    if warnings:
        print(f"[HarnessGenJ Security Warning] {', '.join(warnings)}", file=sys.stderr)
        print("[HarnessGenJ] 建议使用环境变量或密钥管理服务存储敏感信息", file=sys.stderr)

    return 0


def _check_framework_permission(file_path: str, tool_name: str) -> dict[str, Any]:
    """
    检查框架操作权限

    Args:
        file_path: 文件路径
        tool_name: 工具名称

    Returns:
        检查结果 {"blocked": bool, "message": str, "hint": str}
    """
    result = {"blocked": False, "message": "", "hint": ""}

    if not file_path:
        return result

    # 跳过非项目文件（如 .claude/ 内部配置）
    if ".claude" in file_path or ".harnessgenj" in file_path:
        return result

    # 检查框架是否已初始化
    try:
        from harnessgenj.engine import Harness

        if not Harness.is_initialized():
            result["blocked"] = True
            result["message"] = """
[HGJ 框架未初始化] ⚠️

检测到代码修改操作，但框架未初始化。

建议先初始化框架:
  harness = Harness.from_project('.')
  harness.develop('功能描述')

或在对话中直接说明需求，框架会自动引导你完成开发流程。

当前积分系统: 使用框架可获得积分奖励
"""
            result["hint"] = "请初始化框架后再进行代码修改"
            return result

        # 检查文件操作权限
        from harnessgenj.harness.framework_session import FrameworkSession
        session = FrameworkSession.get_instance()

        if not session.check_permission(file_path):
            result["blocked"] = True
            result["message"] = session.get_permission_hint(file_path)
            result["hint"] = f"未获得 {file_path} 的操作许可"

            # 记录违规尝试
            session._log_operation("unauthorized_tool_use", {
                "tool": tool_name,
                "file_path": file_path,
            })

            return result

    except ImportError:
        # 框架未安装，跳过权限检查
        print("[HarnessGenJ] 框架模块未安装，跳过权限检查", file=sys.stderr)
    except Exception as e:
        print(f"[HarnessGenJ] 权限检查异常: {e}", file=sys.stderr)

    return result


def handle_flush_state() -> int:
    """处理 Stop 事件 - 持久化状态"""
    try:
        workspace = get_project_root() / ".harnessgenj"
        state_path = workspace / "state.json"

        if state_path.exists():
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
        print("Usage: harnessgenj_hook.py --post|--security|--intent|--flush-state", file=sys.stderr)
        return 1

    command = sys.argv[1]

    if command == "--post":
        return handle_post_tool_use()
    elif command == "--security":
        return handle_pre_tool_use_security()
    elif command == "--intent":
        return handle_intent_detection()
    elif command == "--flush-state":
        return handle_flush_state()
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())