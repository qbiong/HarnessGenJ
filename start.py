#!/usr/bin/env python
"""
HarnessGenJ 快速启动脚本

直接运行此脚本来初始化项目并开始使用 HarnessGenJ 框架。

用法:
    python start.py                    # 交互式初始化
    python start.py "项目名"            # 快速初始化
    python start.py "项目名" "技术栈"   # 完整初始化
"""

import sys
import os

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from harnessgenj import Harness, ProjectStateManager, MemoryManager


def interactive_init():
    """交互式初始化"""
    print("=" * 50)
    print("  HarnessGenJ - AI Agent 协作框架")
    print("=" * 50)
    print()

    project_name = input("项目名称: ").strip() or "我的项目"
    tech_stack = input("技术栈 (如 Python + FastAPI): ").strip() or "Python"
    description = input("项目描述 (可选): ").strip()

    print()
    print("正在初始化项目...")

    # 创建 Harness
    harness = Harness(project_name, persistent=True)
    harness.setup_team()

    # 初始化项目状态
    state = ProjectStateManager(".HarnessGenJ")
    state.initialize(project_name, tech_stack, description)

    # 存储重要信息
    harness.remember("project_name", project_name, important=True)
    harness.remember("tech_stack", tech_stack, important=True)

    print()
    print("✓ 项目初始化完成!")
    print()
    print("可用操作:")
    print("  harness.develop('功能描述')   - 开发功能")
    print("  harness.fix_bug('Bug描述')    - 修复 Bug")
    print("  harness.analyze('需求')       - 分析需求")
    print("  harness.design('描述')        - 设计架构")
    print("  harness.remember('key', 'value', important=True) - 存储记忆")
    print("  harness.get_status()          - 获取状态")
    print()

    return harness, state


def quick_init(project_name: str, tech_stack: str = "Python"):
    """快速初始化"""
    print(f"正在初始化项目: {project_name}")

    harness = Harness(project_name, persistent=True)
    harness.setup_team()

    state = ProjectStateManager(".HarnessGenJ")
    state.initialize(project_name, tech_stack)

    harness.remember("project_name", project_name, important=True)
    harness.remember("tech_stack", tech_stack, important=True)

    print(f"✓ 项目 '{project_name}' 初始化完成!")
    return harness, state


def demo_usage(harness: Harness):
    """演示用法"""
    print()
    print("=" * 50)
    print("  使用示例")
    print("=" * 50)
    print()

    # 开发功能示例
    print(">>> harness.develop('实现用户登录功能')")
    result = harness.develop("实现用户登录功能")
    print(f"    状态: {result['status']}")
    print()

    # 获取状态
    print(">>> harness.get_status()")
    status = harness.get_status()
    print(f"    项目: {status['project']}")
    print(f"    团队规模: {status['team']['size']}")
    print(f"    开发功能: {status['stats']['features_developed']}")
    print()

    # 生成报告
    print(">>> print(harness.get_report())")
    print(harness.get_report())


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        # 快速初始化
        project_name = sys.argv[1]
        tech_stack = sys.argv[2] if len(sys.argv) >= 3 else "Python"
        harness, state = quick_init(project_name, tech_stack)
    else:
        # 交互式初始化
        harness, state = interactive_init()

    # 询问是否演示
    print()
    demo = input("是否运行演示? (y/n): ").strip().lower()
    if demo == 'y':
        demo_usage(harness)