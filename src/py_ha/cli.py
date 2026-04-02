"""
py_ha CLI - Command Line Interface

Usage:
    py-ha --help
    py-ha version
    py-ha init                     # 首次使用引导
    py-ha develop "实现用户登录功能"
    py-ha fix "登录页面报错"
    py-ha team
    py-ha status
    py-ha interactive
"""

import argparse
import sys
from typing import Any

from py_ha import Harness, __version__


def cmd_version(args: Any) -> None:
    """显示版本信息"""
    print(f"py_ha version {__version__}")
    print("Python Harness for AI Agents")
    print("A Harness Engineering Framework")


def cmd_init(args: Any) -> None:
    """首次使用引导"""
    harness = Harness(args.project or "")
    harness.start_onboarding()


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
    print("py_ha Interactive Mode")
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
            user_input = input("\npy_ha> ").strip()
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

    args = parser.parse_args()

    if args.version:
        cmd_version(args)
        return

    commands = {
        "version": cmd_version,
        "init": cmd_init,
        "welcome": cmd_welcome,
        "develop": cmd_develop,
        "fix": cmd_fix,
        "team": cmd_team,
        "status": cmd_status,
        "interactive": cmd_interactive,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()