"""
HarnessGenJ 最简使用示例

展示 Harness Engineering 框架的核心能力：
- 一键开发功能
- 一键修复 Bug
- 团队协作
"""

from harnessgenj import Harness, create_harness


def demo_simple():
    """最简单的使用方式"""
    print("\n" + "=" * 50)
    print("最简单的使用方式")
    print("=" * 50)

    # 创建 Harness 实例
    harness = create_harness("我的项目")

    # 一键开发功能（自动组建团队）
    result = harness.develop("实现用户登录功能")
    print(f"\n开发结果: {result['status']}")
    print(f"完成阶段: {result['stages_completed']}")

    # 一键修复 Bug
    result = harness.fix_bug("登录页面验证码无法显示")
    print(f"\n修复结果: {result['status']}")


def demo_team():
    """组建团队"""
    print("\n" + "=" * 50)
    print("组建开发团队")
    print("=" * 50)

    harness = Harness("电商平台")

    # 自定义团队
    team = harness.setup_team({
        "product_manager": "王产品",
        "developer": "李开发",
        "tester": "张测试",
    })

    print(f"\n团队规模: {team['team_size']} 人")
    for member in team['members']:
        print(f"  - {member['name']} ({member['type']})")

    # 开发功能
    result = harness.develop("实现购物车功能")
    print(f"\n开发结果: {result['status']}")


def demo_analyze():
    """需求分析"""
    print("\n" + "=" * 50)
    print("需求分析")
    print("=" * 50)

    harness = Harness()
    harness.setup_team()

    # 分析需求
    result = harness.analyze("用户需要一个仪表盘来查看销售数据")
    print(f"\n需求分析完成")
    print(f"输出: {list(result['analysis'].keys())}")


def demo_design():
    """架构设计"""
    print("\n" + "=" * 50)
    print("架构设计")
    print("=" * 50)

    harness = Harness()
    harness.setup_team()

    # 设计系统
    result = harness.design("微服务架构的电商系统")
    print(f"\n架构设计完成")
    print(f"输出: {list(result['design'].keys())}")


def demo_remember():
    """记忆系统"""
    print("\n" + "=" * 50)
    print("记忆系统")
    print("=" * 50)

    harness = Harness("知识管理项目")

    # 记住重要信息
    harness.remember("项目目标", "构建一个高效的 Harness 框架", important=True)
    harness.remember("技术栈", "Python 3.13 + Pydantic")

    # 回忆信息
    goal = harness.recall("项目目标")
    tech = harness.recall("技术栈")

    print(f"\n项目目标: {goal}")
    print(f"技术栈: {tech}")


def demo_report():
    """项目报告"""
    print("\n" + "=" * 50)
    print("项目报告")
    print("=" * 50)

    harness = Harness("AI Agent 项目")
    harness.setup_team()

    # 执行一些工作
    harness.develop("用户认证模块")
    harness.develop("权限管理模块")
    harness.fix_bug("登录超时问题")

    # 生成报告
    report = harness.get_report()
    print(report)


def demo_chain():
    """链式调用"""
    print("\n" + "=" * 50)
    print("链式调用")
    print("=" * 50)

    harness = Harness("快速开发项目")

    # 一行代码完成所有操作
    (harness
        .setup_team()
        .develop("用户注册功能")
        .develop("用户登录功能")
        .fix_bug("注册邮箱验证失败"))

    print(f"\n项目报告:")
    print(harness.get_report())


def main():
    print("=" * 50)
    print("HarnessGenJ 使用示例")
    print("Harness Engineering Framework")
    print("=" * 50)

    demo_simple()
    demo_team()
    demo_analyze()
    demo_design()
    demo_remember()
    demo_report()

    print("\n" + "=" * 50)
    print("演示完成!")
    print("=" * 50)
    print("\n核心 API:")
    print("  harness = create_harness('项目名')")
    print("  harness.develop('功能描述')  # 一键开发")
    print("  harness.fix_bug('Bug描述')  # 一键修复")
    print("  harness.get_report()        # 项目报告")


if __name__ == "__main__":
    main()