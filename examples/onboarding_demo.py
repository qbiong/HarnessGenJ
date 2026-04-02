"""
首次使用引导示例

展示如何使用 py_ha 的引导系统：
- 检测是否首次使用
- 启动引导流程
- 加载项目配置
- 显示欢迎信息

使用场景:
当用户第一次使用框架时，自动引导完成项目配置，
并告诉用户如何通过对话的方式开始使用框架。
"""

from py_ha import Harness


def demo_first_time_check():
    """演示首次使用检测"""
    print("\n" + "=" * 60)
    print("首次使用检测演示")
    print("=" * 60)

    # 创建 Harness 实例
    harness = Harness()

    # 检测是否首次使用
    if harness.is_first_time():
        print("\n[OK] 检测到这是首次使用")
        print("  建议运行引导: harness.start_onboarding()")
    else:
        print("\n[OK] 已完成引导配置")
        config = harness.load_project_config()
        if config:
            print(f"  项目名称: {config['project_name']}")


def demo_welcome_message():
    """演示欢迎信息"""
    print("\n" + "=" * 60)
    print("欢迎信息演示")
    print("=" * 60)

    harness = Harness("演示项目")

    # 显示欢迎信息
    print(harness.welcome())


def demo_quick_help():
    """演示快速帮助"""
    print("\n" + "=" * 60)
    print("快速帮助演示")
    print("=" * 60)

    harness = Harness()
    harness.show_help()


def demo_onboarding_flow():
    """演示引导流程（交互式）"""
    print("\n" + "=" * 60)
    print("引导流程演示")
    print("=" * 60)
    print("\n注意: 这是一个交互式流程，需要用户输入")
    print("如果你想跳过交互式演示，请注释掉此函数的调用\n")

    # 启动引导（需要用户交互）
    harness = Harness()
    # harness.start_onboarding()  # 取消注释来运行完整引导

    # 这里演示非交互式的简化流程
    print("简化演示（非交互式）:")
    print("-" * 40)

    # 模拟配置
    from py_ha import ProjectConfig

    config = ProjectConfig(
        project_name="电商平台",
        project_description="一个现代化的电商平台",
        tech_stack="Python + FastAPI + PostgreSQL",
        team_config={
            "product_manager": "王产品",
            "architect": "李架构",
            "developer": "张开发",
            "tester": "刘测试",
        },
        onboarding_completed=True,
    )

    print(f"  项目名称: {config.project_name}")
    print(f"  项目描述: {config.project_description}")
    print(f"  技术栈: {config.tech_stack}")
    print(f"  团队配置: {len(config.team_config)} 人")

    print("\n引导完成后，你可以这样使用框架:")
    print("-" * 40)
    print("""
# 方式一：对话式使用（推荐）
harness.chat("我想开发一个用户登录功能")

# 方式二：快速开发
harness.develop("实现购物车功能")

# 方式三：切换对话
harness.switch_session("product_manager")
harness.chat("购物车需要支持哪些功能？")

# 方式四：保存记忆
harness.remember("api_endpoint", "/api/v1", important=True)
""")


def demo_after_onboarding():
    """演示引导完成后的使用"""
    print("\n" + "=" * 60)
    print("引导完成后的使用演示")
    print("=" * 60)

    # 创建已配置的 Harness
    harness = Harness("电商平台")

    # 设置团队
    harness.setup_team({
        "product_manager": "王产品",
        "developer": "张开发",
        "tester": "刘测试",
    })

    # 保存项目信息到记忆
    harness.remember("project_goal", "构建电商平台 MVP", important=True)
    harness.remember("tech_stack", "Python + FastAPI")

    # 显示项目状态
    print("\n项目状态:")
    print(harness.get_report())

    # 开始对话开发
    print("\n开始对话开发:")
    print("-" * 40)

    harness.chat("我需要开发用户登录功能")
    print("  [用户] 我需要开发用户登录功能")

    harness.switch_session("product_manager")
    harness.chat("登录功能需要支持邮箱和手机号登录")
    print("  [产品经理对话] 登录功能需要支持邮箱和手机号登录")

    harness.switch_session("development")
    harness.chat("需求已确认，开始实现登录功能")
    print("  [主开发对话] 需求已确认，开始实现登录功能")

    # 查看会话状态
    print("\n会话状态:")
    sessions = harness.list_sessions()
    for session in sessions:
        active = " (当前)" if session.get("is_active") else ""
        print(f"  {session['name']}{active}: {session['message_count']} 条消息")


def main():
    """主演示函数"""
    print("=" * 60)
    print("py_ha 首次使用引导系统演示")
    print("=" * 60)

    demo_first_time_check()
    demo_welcome_message()
    demo_quick_help()
    demo_onboarding_flow()
    demo_after_onboarding()

    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)
    print("\n核心 API:")
    print("  harness.is_first_time()        # 检测是否首次使用")
    print("  harness.start_onboarding()     # 启动引导流程")
    print("  harness.welcome()              # 显示欢迎信息")
    print("  harness.show_help()            # 显示快速帮助")
    print("  harness.load_project_config()  # 加载项目配置")
    print("=" * 60)

    print("\nCLI 命令:")
    print("  py-ha init      # 启动引导")
    print("  py-ha welcome   # 显示欢迎")
    print("  py-ha --help    # 查看帮助")
    print("=" * 60)


if __name__ == "__main__":
    main()