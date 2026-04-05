"""
HarnessGenJ CLI - Command Line Interface

Usage:
    py-ha --help
    py-ha version
    py-ha init                     # 首次使用引导
    py-ha setup-hooks              # 自动生成 hooks 配置
    py-ha develop "实现用户登录功能"
    py-ha fix "登录页面报错"
    py-ha team
    py-ha status
    py-ha interactive
    py-ha sync                     # 同步知识文件
"""

import argparse
import sys
import os
from pathlib import Path
from typing import Any

from harnessgenj import Harness, __version__


def cmd_version(args: Any) -> None:
    """显示版本信息"""
    print(f"HarnessGenJ version {__version__}")
    print("Python Harness for AI Agents")
    print("A Harness Engineering Framework")


def cmd_init(args: Any) -> None:
    """首次使用引导"""
    harness = Harness(args.project or "")
    harness.start_onboarding()


def cmd_setup_hooks(args: Any) -> None:
    """自动生成 hooks 配置"""
    project_dir = Path(args.project_dir) if args.project_dir else Path.cwd()
    claude_dir = project_dir / ".claude"

    # 确保目录存在
    claude_dir.mkdir(parents=True, exist_ok=True)

    # 生成 pyha_hook.py
    hook_script = claude_dir / "pyha_hook.py"
    hook_content = '''#!/usr/bin/env python3
"""
pyha_hook.py - Claude Code Hooks 桥梁脚本 (自动生成)

功能:
1. PostToolUse: 自动记录文件操作到开发日志
2. PreToolUse: 安全检查 (可选)

此文件由 py-ha setup-hooks 命令自动生成
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
    tool_input = os.environ.get("TOOL_INPUT", "{}")
    try:
        return json.loads(tool_input)
    except json.JSONDecodeError:
        pass
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
            dev_log_path.write_text("# 开发日志\\n\\n此文件由 HarnessGenJ 自动维护。\\n\\n---\\n", encoding="utf-8")

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"\\n## 记录 ({timestamp}) [{context}]\\n\\n{content}\\n\\n---\\n"
        with open(dev_log_path, "a", encoding="utf-8") as f:
            f.write(entry)
        return True
    except Exception:
        return False


def handle_post_tool_use() -> int:
    """处理 PostToolUse 事件"""
    tool_input = get_tool_input()
    tool_name = os.environ.get("TOOL_NAME", "")

    file_path = tool_input.get("file_path", tool_input.get("path", ""))
    content = tool_input.get("content", tool_input.get("new_string", ""))

    if not file_path:
        return 0

    action = "创建" if tool_name == "Write" else "修改"
    record_content = f"{action}文件: `{file_path}`"

    if file_path.endswith(('.java', '.kt', '.py', '.js', '.ts', '.tsx')):
        if content:
            lines = content.count('\\n') + 1
            record_content += f" ({lines} 行)"

    append_to_development_log(record_content, context=f"PostToolUse:{tool_name}")
    return 0


def handle_pre_tool_use_security() -> int:
    """处理 PreToolUse 安全检查"""
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
        if pattern in content_lower and ("=" in content or ":" in content):
            warnings.append(f"可能包含敏感信息: {pattern}")

    if warnings:
        print(f"[HarnessGenJ Security Warning] {', '.join(warnings)}", file=sys.stderr)

    return 0


def main():
    """主入口"""
    if len(sys.argv) < 2:
        print("Usage: pyha_hook.py --post|--security", file=sys.stderr)
        return 1

    command = sys.argv[1]

    if command == "--post":
        return handle_post_tool_use()
    elif command == "--security":
        return handle_pre_tool_use_security()
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
'''

    hook_script.write_text(hook_content, encoding="utf-8")
    print(f"✓ 已生成: {hook_script}")

    # 生成 settings.json 配置（如果不存在或请求更新）
    settings_path = claude_dir / "settings.json"

    # 读取现有配置或创建新配置
    existing_settings = {}
    if settings_path.exists():
        try:
            import json
            with open(settings_path, "r", encoding="utf-8") as f:
                existing_settings = json.load(f)
        except Exception:
            pass

    # 添加 hooks 配置
    existing_settings["hooks"] = {
        "PreToolUse": [
            {
                "matcher": "Write|Edit",
                "hooks": [
                    {
                        "type": "command",
                        "command": 'python "$CLAUDE_PROJECT_DIR/.claude/pyha_hook.py" --security "$TOOL_INPUT_CONTENT"'
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
                        "command": 'python "$CLAUDE_PROJECT_DIR/.claude/pyha_hook.py" --post'
                    }
                ]
            }
        ]
    }

    # 写入配置
    import json
    with open(settings_path, "w", encoding="utf-8") as f:
        json.dump(existing_settings, f, ensure_ascii=False, indent=2)
    print(f"✓ 已更新: {settings_path}")

    # 打印完成信息
    print("\n" + "=" * 50)
    print("Hooks 配置完成!")
    print("=" * 50)
    print("\n已启用的功能:")
    print("  • PreToolUse 安全检查 - 检测敏感信息")
    print("  • PostToolUse 自动记录 - 记录文件操作到开发日志")
    print("\n注意: 如果这是全局配置，请重启 Claude Code 以生效。")


def cmd_welcome(args: Any) -> None:
    """显示欢迎信息"""
    harness = Harness(args.project or "CLI Project")
    print(harness.welcome())


def cmd_develop(args: Any) -> None:
    """开发功能"""
    harness = Harness(args.project or "CLI Project")
    result = harness.develop(args.feature)

    print(f"\n功能开发: {args.feature}")
    print(f"状态: {result['status']}")
    print(f"完成阶段: {result['stages_completed']}")
    print(f"交付物: {', '.join(result['artifacts'])}")


def cmd_fix(args: Any) -> None:
    """修复Bug"""
    harness = Harness(args.project or "CLI Project")
    result = harness.fix_bug(args.bug)

    print(f"\nBug修复: {args.bug}")
    print(f"状态: {result['status']}")
    print(f"完成阶段: {result['stages_completed']}")


def cmd_team(args: Any) -> None:
    """显示团队信息"""
    harness = Harness(args.project or "CLI Project")
    harness.setup_team()

    team = harness.get_team()
    print(f"\n团队规模: {len(team)} 人")
    print("-" * 40)
    for member in team:
        print(f"  {member['name']}: {member['role_type']}")


def cmd_status(args: Any) -> None:
    """显示项目状态"""
    harness = Harness(args.project or "CLI Project")
    harness.setup_team()

    print(harness.get_report())


def cmd_interactive(args: Any) -> None:
    """交互模式"""
    print("=" * 50)
    print("HarnessGenJ Interactive Mode")
    print("Harness Engineering Framework")
    print("=" * 50)
    print("\nCommands:")
    print("  develop <feature>  - 开发功能")
    print("  fix <bug>          - 修复Bug")
    print("  team               - 显示团队")
    print("  status             - 显示状态")
    print("  exit               - 退出")
    print()

    harness = Harness("Interactive Project")
    harness.setup_team()

    while True:
        try:
            user_input = input("\nharnessgenj> ").strip()
            if not user_input:
                continue

            parts = user_input.split(maxsplit=1)
            cmd = parts[0].lower()

            if cmd == "exit" or cmd == "quit":
                print("再见!")
                break
            elif cmd == "develop" and len(parts) > 1:
                result = harness.develop(parts[1])
                print(f"状态: {result['status']}")
            elif cmd == "fix" and len(parts) > 1:
                result = harness.fix_bug(parts[1])
                print(f"状态: {result['status']}")
            elif cmd == "team":
                team = harness.get_team()
                for m in team:
                    print(f"  {m['name']}: {m['role_type']}")
            elif cmd == "status":
                print(harness.get_report())
            else:
                print(f"未知命令: {cmd}")

        except KeyboardInterrupt:
            print("\n再见!")
            break
        except Exception as e:
            print(f"错误: {e}")


def main() -> None:
    """CLI 主入口"""
    parser = argparse.ArgumentParser(
        prog="py-ha",
        description="Python Harness for AI Agents - A Harness Engineering Framework",
    )

    parser.add_argument(
        "--version", "-v",
        action="store_true",
        help="显示版本信息",
    )

    parser.add_argument(
        "--project", "-p",
        help="项目名称",
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # version 命令
    subparsers.add_parser("version", help="显示版本")

    # init 命令 - 首次使用引导
    subparsers.add_parser("init", help="首次使用引导，配置项目信息")

    # setup-hooks 命令 - 自动生成 hooks 配置
    setup_hooks_parser = subparsers.add_parser("setup-hooks", help="自动生成 Claude Code hooks 配置")
    setup_hooks_parser.add_argument("--project-dir", help="项目目录路径")

    # welcome 命令 - 显示欢迎信息
    subparsers.add_parser("welcome", help="显示欢迎信息和快速提示")

    # develop 命令
    develop_parser = subparsers.add_parser("develop", help="开发功能")
    develop_parser.add_argument("feature", help="功能描述")

    # fix 命令
    fix_parser = subparsers.add_parser("fix", help="修复Bug")
    fix_parser.add_argument("bug", help="Bug描述")

    # team 命令
    subparsers.add_parser("team", help="显示团队")

    # status 命令
    subparsers.add_parser("status", help="显示项目状态")

    # interactive 命令
    subparsers.add_parser("interactive", help="交互模式")

    # sync 命令 - 同步知识文件
    subparsers.add_parser("sync", help="同步知识文件")

    args = parser.parse_args()

    if args.version:
        cmd_version(args)
        return

    commands = {
        "version": cmd_version,
        "init": cmd_init,
        "setup-hooks": cmd_setup_hooks,
        "welcome": cmd_welcome,
        "develop": cmd_develop,
        "fix": cmd_fix,
        "team": cmd_team,
        "status": cmd_status,
        "interactive": cmd_interactive,
        "sync": cmd_sync,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


def cmd_sync(args: Any) -> None:
    """同步知识文件"""
    harness = Harness(args.project or "CLI Project")

    if harness._agents_knowledge:
        result = harness._agents_knowledge.sync_all_knowledge()
        print("\n知识同步结果:")
        print(f"  更新文件: {len(result.get('updated', []))}")
        for f in result.get('updated', []):
            print(f"    • {f}")

        if result.get('errors'):
            print(f"  错误: {len(result['errors'])}")
            for e in result['errors']:
                print(f"    • {e}")
    else:
        print("知识管理器未初始化")


if __name__ == "__main__":
    main()