"""
Hooks Auto Setup - 自动 Hooks 配置系统

当用户初始化 Harness 实例时，自动检测并配置 Claude Code Hooks：
1. 检查 .claude/settings.json 是否存在
2. 检查是否已配置 Hooks
3. 如果未配置，自动创建配置
4. 创建 harnessgenj_hook.py 脚本
5. 集成事件触发系统

使用示例:
    from harnessgenj.harness.hooks_auto_setup import auto_setup_hooks

    # 在 Harness 初始化时自动调用
    auto_setup_hooks(project_dir)
"""

import os
import json
from pathlib import Path
from harnessgenj.utils.exception_handler import log_exception
from typing import Any


def check_hooks_configured(project_dir: Path) -> bool:
    """
    检查 Hooks 是否已配置

    Args:
        project_dir: 项目根目录

    Returns:
        True 如果 Hooks 已配置
    """
    settings_path = project_dir / ".claude" / "settings.json"

    if not settings_path.exists():
        return False

    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)

        # 检查是否有 hooks 配置
        hooks = settings.get("hooks", {})
        if not hooks:
            return False

        # 检查是否有 PostToolUse 配置（关键配置）
        post_hooks = hooks.get("PostToolUse", [])
        if not post_hooks:
            return False

        # 检查是否包含 harnessgenj_hook.py
        for hook_config in post_hooks:
            for hook in hook_config.get("hooks", []):
                command = hook.get("command", "")
                if "harnessgenj_hook.py" in command:
                    return True

        return False
    except (json.JSONDecodeError, KeyError):
        return False


def check_hook_script_exists(project_dir: Path) -> bool:
    """
    检查 Hook 脚本是否存在

    Args:
        project_dir: 项目根目录

    Returns:
        True 如果脚本存在
    """
    hook_script = project_dir / ".claude" / "harnessgenj_hook.py"
    return hook_script.exists()


def create_security_hook_standalone(project_dir: Path) -> bool:
    """
    创建独立的安全检查模块（供 hook 脚本导入）

    Args:
        project_dir: 项目根目录

    Returns:
        True 如果创建成功
    """
    claude_dir = project_dir / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)

    security_hook = claude_dir / "security_hook_standalone.py"
    # Generate security module content (using raw string for cleaner regex)
    security_content = '''#!/usr/bin/env python3
"""
security_hook_standalone.py - Standalone security check module

Reuses harnessgenj.harness.hooks.SecurityHook logic
Supports multi-language sensitive data detection
"""

import re
from typing import Any

# Multi-language sensitive patterns
LANGUAGE_PATTERNS = {
    "python": {
        "sensitive": [
            r'password\\s*=\\s*["\\'][^"\\']+["\\']',
            r'api_key\\s*=\\s*["\\'][^"\\']+["\\']',
            r'secret\\s*=\\s*["\\'][^"\\']+["\\']',
            r'token\\s*=\\s*["\\'][^"\\']+["\\']',
            r'credential\\s*=\\s*["\\'][^"\\']+["\\']',
        ],
        "high_risk": ["password", "api_key", "secret", "token", "credential"],
    },
    "java": {
        "sensitive": [
            r'String\\s+(password|apiKey|secret|token)\\s*=\\s*"[^"]+"',
            r'private\\s+String\\s+\\w*[Pp]assword\\w*\\s*=\\s*"[^"]+"',
            r'private\\s+String\\s+\\w*[Tt]oken\\w*\\s*=\\s*"[^"]+"',
            r'@Value\\s*\\(["\\'][^"\\']*(password|secret|token|key)["\\']',
        ],
        "high_risk": ["password", "apiKey", "secret", "token", "credential"],
    },
    "kotlin": {
        "sensitive": [
            r'val\\s+(password|apiKey|secret|token)\\s*=\\s*"[^"]+"',
            r'private\\s+val\\s+\\w*[Pp]assword\\w*\\s*=',
            r'private\\s+val\\s+\\w*[Tt]oken\\w*\\s*=',
            r'const\\s+val\\s+\\w*[Kk]ey\\w*\\s*=\\s*"[^"]+"',
        ],
        "high_risk": ["password", "apiKey", "secret", "token", "credential"],
    },
    "javascript": {
        "sensitive": [
            r'(const|let|var)\\s+(password|apiKey|secret|token)\\s*=\\s*["\\'][^"\\']+["\\']',
            r'process\\.env\\.\\w*(PASSWORD|SECRET|TOKEN|KEY)',
        ],
        "high_risk": ["password", "apiKey", "secret", "token", "credential", "PRIVATE_KEY"],
    },
    "typescript": {
        "sensitive": [
            r'(const|let|var)\\s+(password|apiKey|secret|token)\\s*:\\s*string\\s*=\\s*["\\'][^"\\']+["\\']',
            r'process\\.env\\.\\w*(PASSWORD|SECRET|TOKEN|KEY)',
        ],
        "high_risk": ["password", "apiKey", "secret", "token", "credential"],
    },
}

# Common high-risk patterns
HIGH_RISK_PATTERNS = [
    "password", "secret", "api_key", "token", "credential", "private_key"
]


def detect_language(file_path: str) -> str:
    """Detect language by file extension"""
    import os
    ext_map = {
        ".py": "python",
        ".java": "java",
        ".kt": "kotlin",
        ".kts": "kotlin",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
    }
    ext = os.path.splitext(file_path)[1].lower() if file_path else ""
    return ext_map.get(ext, "python")


def check_security(content: str, file_path: str = "") -> dict[str, Any]:
    """
    Execute security check

    Args:
        content: Content to check
        file_path: File path (for language detection)

    Returns:
        Check result {"errors": [], "warnings": []}
    """
    result = {
        "errors": [],
        "warnings": [],
        "passed": True,
    }

    if not content:
        return result

    # Detect language
    detected_lang = detect_language(file_path)
    lang_patterns = LANGUAGE_PATTERNS.get(detected_lang, LANGUAGE_PATTERNS["python"])

    # Check language-specific hardcoded sensitive data
    for pattern in lang_patterns["sensitive"]:
        try:
            if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
                result["errors"].append(f"[{detected_lang}] Hardcoded sensitive data: {pattern}")
                result["passed"] = False
        except re.error:
            pass

    # Check high-risk keywords
    for keyword in lang_patterns["high_risk"]:
        if keyword.lower() in content.lower():
            if "=" in content or ":" in content:
                result["warnings"].append(f"Potential sensitive data: {keyword}")

    # Check common dangerous patterns
    for pattern in HIGH_RISK_PATTERNS:
        if pattern.lower() in content.lower():
            lines = content.split('\\n')
            for i, line in enumerate(lines):
                if pattern.lower() in line.lower():
                    stripped = line.strip()
                    if not stripped.startswith('#') and not stripped.startswith('//') and not stripped.startswith('*'):
                        if '=' in line or ':' in line:
                            result["warnings"].append(f"Line {i+1}: potential sensitive config '{pattern}'")

    return result
'''

    try:
        security_hook.write_text(security_content, encoding="utf-8")
        return True
    except Exception as e:
        log_exception(e, context="create_security_hook_standalone", level=30)
        return False


def create_hook_script(project_dir: Path) -> bool:
    """
    创建 Hook 脚本

    Args:
        project_dir: 项目根目录

    Returns:
        True 如果创建成功
    """
    claude_dir = project_dir / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)

    # 创建独立安全检查模块
    security_created = create_security_hook_standalone(project_dir)
    if not security_created:
        return False

    hook_script = claude_dir / "harnessgenj_hook.py"
    hook_content = '''#!/usr/bin/env python3
"""
harnessgenj_hook.py - Claude Code Hooks 桥接脚本 (自动生成)

功能:
1. PostToolUse: 自动记录文件操作到开发日志，触发对抗审查
2. PreToolUse: 安全检查，检测敏感信息泄露

此文件由 HarnessGenJ 自动生成
"""

import os
import sys
import json
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
    # 尝试从环境变量获取
    tool_input = os.environ.get("TOOL_INPUT", "{}")
    try:
        return json.loads(tool_input)
    except json.JSONDecodeError:
        pass

    # 尝试从命令行参数获取
    if len(sys.argv) > 2:
        try:
            return json.loads(sys.argv[2])
        except json.JSONDecodeError:
            pass

    return {}


def append_to_development_log(content: str, context: str = "Hooks") -> bool:
    """追加内容到开发日志"""
    try:
        workspace = get_project_root() / ".harnessgenj"
        dev_log_path = workspace / "documents" / "development.md"
        dev_log_path.parent.mkdir(parents=True, exist_ok=True)

        if not dev_log_path.exists():
            dev_log_path.write_text(
                "# 开发日志\\n\\n此文件由 HarnessGenJ Hooks 自动维护。\\n\\n---\\n",
                encoding="utf-8"
            )

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"\\n## [{timestamp}] [{context}]\\n\\n{content}\\n\\n---\\n"
        with open(dev_log_path, "a", encoding="utf-8") as f:
            f.write(entry)
        return True
    except Exception as e:
        log_exception(e, context="write_to_development_log", level=30)
        return False


def trigger_adversarial_review(file_path: str, content: str) -> dict[str, Any]:
    """
    触发对抗性审查（记录到积分系统并通过事件系统通知）

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
    lines = content.count('\\n') + 1 if content else 0
    log_content = f"Code file changed: `{file_path}` ({lines} lines)"
    append_to_development_log(log_content, context="AdversarialTrigger")

    # 写入事件文件，供 TriggerManager 消费
    try:
        workspace = get_project_root() / ".harnessgenj"
        events_dir = workspace / "events"
        events_dir.mkdir(parents=True, exist_ok=True)

        event_file = events_dir / f"event_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json"
        event_data = {
            "type": "on_write_complete",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "file_path": file_path,
                "lines": lines,
                "triggered_by": "hooks",
            }
        }

        with open(event_file, "w", encoding="utf-8") as f:
            json.dump(event_data, f, ensure_ascii=False, indent=2)

        result["review_triggered"] = True
    except Exception as e:
        log_exception(e, context="trigger_adversarial_review 事件写入", level=30)

    # 更新积分系统（如果存在）- 保持向后兼容
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
    except Exception as e:
        log_exception(e, context="trigger_adversarial_review scores更新", level=30)

    return result


def handle_post_tool_use() -> int:
    """
    处理 PostToolUse 事件

    功能:
    1. 记录文件操作到开发日志
    2. 触发对抗性审查（更新积分系统）
    """
    tool_input = get_tool_input()
    tool_name = os.environ.get("TOOL_NAME", "")

    file_path = tool_input.get("file_path", tool_input.get("path", ""))
    content = tool_input.get("content", tool_input.get("new_string", ""))

    if not file_path:
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

    复用 SecurityHook 进行多语言安全检查
    """
    tool_input = get_tool_input()
    tool_name = os.environ.get("TOOL_NAME", "")

    file_path = tool_input.get("file_path", tool_input.get("path", ""))
    content = tool_input.get("content", tool_input.get("new_string", ""))

    if not content:
        if len(sys.argv) > 2:
            content = sys.argv[2]

    if not content:
        return 0

    # 尝试导入 SecurityHook 进行专业检查
    try:
        # 动态导入 SecurityHook
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "hooks",
            get_project_root() / ".claude" / "security_hook_standalone.py"
        )
        if spec and spec.loader:
            hooks_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(hooks_module)
            result = hooks_module.check_security(content, file_path)
            if result.get("warnings") or result.get("errors"):
                for err in result.get("errors", []):
                    print(f"[HarnessGenJ Security Error] {err}", file=sys.stderr)
                for warn in result.get("warnings", []):
                    print(f"[HarnessGenJ Security Warning] {warn}", file=sys.stderr)
                print("[HarnessGenJ] Suggest using environment variables or key management service for sensitive data", file=sys.stderr)
            return 0
    except Exception as e:
        log_exception(e, context="handle_pre_tool_use_security", level=30)

    # 回退到简化检查（当 SecurityHook 不可用时）
    high_risk_patterns = [
        "password", "secret", "api_key", "apikey", "token",
        "credential", "private_key", "access_key", "auth"
    ]
    warnings = []
    content_lower = content.lower()

    for pattern in high_risk_patterns:
        if pattern in content_lower:
            if "=" in content or ":" in content:
                lines = content.split("\\n")
                for line in lines:
                    if pattern in line.lower() and ("=" in line or ":" in line):
                        if not line.strip().startswith("#") and not line.strip().startswith("//"):
                            warnings.append(f"Potential sensitive data: {pattern}")

    if warnings:
        print(f"[HarnessGenJ Security Warning] {', '.join(warnings)}", file=sys.stderr)
        print("[HarnessGenJ] Suggest using environment variables or key management service for sensitive data", file=sys.stderr)

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
    except Exception as e:
        log_exception(e, context="handle_flush_state", level=30)

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
'''

    try:
        hook_script.write_text(hook_content, encoding="utf-8")
        return True
    except Exception as e:
        log_exception(e, context="create_hook_script", level=30)
        return False


def update_settings_json(project_dir: Path) -> bool:
    """
    更新 settings.json 添加 Hooks 配置

    Args:
        project_dir: 项目根目录

    Returns:
        True 如果更新成功
    """
    claude_dir = project_dir / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)

    settings_path = claude_dir / "settings.json"

    # 读取现有配置或创建新配置
    existing_settings: dict[str, Any] = {}
    if settings_path.exists():
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                existing_settings = json.load(f)
        except (json.JSONDecodeError, Exception):
            existing_settings = {}

    # 添加 Hooks 配置
    existing_settings["hooks"] = {
        "PreToolUse": [
            {
                "matcher": "Write|Edit",
                "hooks": [
                    {
                        "type": "command",
                        "command": 'python "$CLAUDE_PROJECT_DIR/.claude/harnessgenj_hook.py" --security "$TOOL_INPUT_CONTENT"'
                    }
                ]
            }
        ],
        "PostToolUse": [
            {
                "matcher": "Write|Edit",
                "hooks": [
                    {
                        "type": "command",
                        "command": 'python "$CLAUDE_PROJECT_DIR/.claude/harnessgenj_hook.py" --post'
                    }
                ]
            }
        ],
        "Stop": [
            {
                "matcher": "*",
                "hooks": [
                    {
                        "type": "command",
                        "command": 'python "$CLAUDE_PROJECT_DIR/.claude/harnessgenj_hook.py" --flush-state'
                    }
                ]
            }
        ]
    }

    # 写入配置
    try:
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(existing_settings, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        log_exception(e, context="update_settings_json", level=30)
        return False


def auto_setup_hooks(
    project_dir: str | Path | None = None,
    silent: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    """
    自动设置 Hooks 配置

    当用户初始化 Harness 时自动调用，检测并配置 Claude Code Hooks。

    Args:
        project_dir: 项目根目录（默认当前工作目录）
        silent: 是否静默模式（不输出提示信息）
        force: 是否强制更新（即使已配置也更新）

    Returns:
        设置结果
    """
    if project_dir is None:
        project_dir = Path.cwd()
    elif isinstance(project_dir, str):
        project_dir = Path(project_dir)

    result = {
        "project_dir": str(project_dir),
        "hooks_configured": False,
        "script_created": False,
        "settings_updated": False,
        "already_configured": False,
        "message": "",
    }

    # 检查是否已配置
    if not force and check_hooks_configured(project_dir):
        result["already_configured"] = True
        result["hooks_configured"] = True
        result["message"] = "Hooks 已配置，无需更新"
        if not silent:
            print("[HarnessGenJ] Hooks 已配置 ✓")
        return result

    # 创建 Hook 脚本
    script_created = create_hook_script(project_dir)
    result["script_created"] = script_created

    if not script_created:
        result["message"] = "创建 Hook 脚本失败"
        if not silent:
            print("[HarnessGenJ] 创建 Hook 脚本失败 ✗", file=sys.stderr)
        return result

    # 更新 settings.json
    settings_updated = update_settings_json(project_dir)
    result["settings_updated"] = settings_updated

    if not settings_updated:
        result["message"] = "更新 settings.json 失败"
        if not silent:
            print("[HarnessGenJ] 更新 settings.json 失败 ✗", file=sys.stderr)
        return result

    # 成功
    result["hooks_configured"] = True
    result["message"] = "Hooks 配置完成"

    if not silent:
        print("\n" + "=" * 50)
        print("[HarnessGenJ] Claude Code Hooks auto-config completed [OK]")
        print("=" * 50)
        print("\nFeatures enabled:")
        print("  * PreToolUse security check - detect sensitive information")
        print("  * PostToolUse auto-log - record file operations to dev log")
        print("  * PostToolUse adversarial review - trigger score system update")
        print("  * Stop state persistence - auto-save work state")
        print("\nConfig file location:")
        print(f"  * {project_dir / '.claude' / 'settings.json'}")
        print(f"  * {project_dir / '.claude' / 'harnessgenj_hook.py'}")
        print("\nTip: If hooks are not working, please restart Claude Code.")

    return result


def get_hooks_setup_status(project_dir: str | Path | None = None) -> dict[str, Any]:
    """
    获取 Hooks 设置状态

    Args:
        project_dir: 项目根目录

    Returns:
        状态信息
    """
    if project_dir is None:
        project_dir = Path.cwd()
    elif isinstance(project_dir, str):
        project_dir = Path(project_dir)

    return {
        "project_dir": str(project_dir),
        "hooks_configured": check_hooks_configured(project_dir),
        "hook_script_exists": check_hook_script_exists(project_dir),
        "settings_path": str(project_dir / ".claude" / "settings.json"),
        "hook_script_path": str(project_dir / ".claude" / "harnessgenj_hook.py"),
    }