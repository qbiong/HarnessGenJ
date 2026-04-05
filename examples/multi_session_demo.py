"""
多会话记忆示例

展示如何在项目开发过程中维护多个独立的对话会话：
- 主开发对话：核心开发流程，不被打断
- 产品经理对话：需求沟通
- 项目经理对话：进度协调
- 架构师对话：技术讨论

使用场景：
在开发过程中，你可以随时切换到不同的对话会话，
与其他角色沟通需求、进度等，然后切换回主开发对话继续工作。
"""

from harnessgenj import Harness


def demo_multi_session():
    """演示多会话功能"""
    print("\n" + "=" * 60)
    print("多会话记忆演示")
    print("=" * 60)

    harness = Harness("电商平台项目")

    # ==================== 主开发对话 ====================
    print("\n[主开发对话] 开始开发功能...")
    harness.switch_session("development")
    harness.chat("我正在开发用户登录功能")
    harness.chat("已经完成了基本登录逻辑")

    print(f"当前会话: {harness.get_current_session()['name']}")
    print(f"消息数: {harness.get_current_session()['message_count']}")

    # ==================== 切换到产品经理对话 ====================
    print("\n[切换] -> 产品经理对话")
    harness.switch_session("product_manager")
    harness.chat("登录功能需要支持哪些登录方式？")
    harness.chat("用户提出了微信登录的需求")
    harness.chat("好的，我记录下来，稍后评估")

    print(f"当前会话: {harness.get_current_session()['name']}")
    print(f"消息数: {harness.get_current_session()['message_count']}")

    # ==================== 切换到项目经理对话 ====================
    print("\n[切换] -> 项目经理对话")
    harness.switch_session("project_manager")
    harness.chat("登录功能的开发进度如何？")
    harness.chat("预计今天完成基础功能，明天接入微信登录")
    harness.chat("好的，我更新一下项目进度")

    print(f"当前会话: {harness.get_current_session()['name']}")

    # ==================== 切换回主开发对话 ====================
    print("\n[切换] -> 主开发对话")
    harness.switch_session("development")
    harness.chat("继续完成登录功能...")
    harness.chat("产品经理说需要支持微信登录，我稍后实现")

    print(f"当前会话: {harness.get_current_session()['name']}")
    print(f"消息数: {harness.get_current_session()['message_count']}")

    # ==================== 查看所有会话 ====================
    print("\n" + "=" * 60)
    print("所有会话概览")
    print("=" * 60)

    sessions = harness.list_sessions()
    for session in sessions:
        active = " (当前)" if session.get("is_active") else ""
        print(f"  {session['name']}{active}: {session['message_count']} 条消息")


def demo_session_history():
    """演示会话历史查看"""
    print("\n" + "=" * 60)
    print("会话历史查看")
    print("=" * 60)

    harness = Harness("示例项目")

    # 在不同会话中发送消息
    harness.switch_session("development")
    harness.chat("开始开发功能A")
    harness.chat("功能A开发完成")

    harness.switch_session("product_manager")
    harness.chat("讨论功能B的需求")

    # 查看特定会话的历史
    print("\n[主开发对话历史]")
    harness.switch_session("development")
    history = harness.get_session_history()
    for msg in history:
        print(f"  [{msg['role']}] {msg['content']}")

    print("\n[产品经理对话历史]")
    harness.switch_session("product_manager")
    history = harness.get_session_history()
    for msg in history:
        print(f"  [{msg['role']}] {msg['content']}")


def demo_session_report():
    """演示会话报告"""
    print("\n" + "=" * 60)
    print("会话报告")
    print("=" * 60)

    harness = Harness("AI项目")

    # 模拟多角色沟通
    harness.switch_session("development")
    harness.chat("实现核心算法")
    harness.chat("优化性能")

    harness.switch_session("architect")
    harness.chat("讨论系统架构")
    harness.chat("确定微服务方案")

    harness.switch_session("tester")
    harness.chat("编写测试用例")

    # 生成报告
    print(harness.get_session_report())


def demo_real_world_workflow():
    """演示真实工作流场景"""
    print("\n" + "=" * 60)
    print("真实工作流场景演示")
    print("=" * 60)

    harness = Harness("电商平台")

    # 1. 主开发流程
    print("\n[1] 主开发流程")
    harness.switch_session("development")
    harness.chat("开始开发购物车功能")

    # 2. 需要确认需求，切换到产品经理对话
    print("\n[2] 需要确认需求，切换到产品经理对话")
    harness.switch_session("product_manager")
    harness.chat("购物车需要支持哪些功能？")
    harness.chat("需要：添加商品、修改数量、删除商品、计算总价")
    harness.chat("好的，需求已明确")

    # 3. 切回主开发继续工作
    print("\n[3] 切回主开发继续工作")
    harness.switch_session("development")
    harness.chat("需求已确认，继续开发购物车")
    harness.chat("完成添加商品功能")

    # 4. 遇到技术问题，咨询架构师
    print("\n[4] 遇到技术问题，咨询架构师")
    harness.switch_session("architect")
    harness.chat("购物车数据如何存储？Redis还是数据库？")
    harness.chat("建议用Redis存储临时购物车，数据库存储持久化数据")

    # 5. 切回主开发应用建议
    print("\n[5] 切回主开发应用建议")
    harness.switch_session("development")
    harness.chat("架构师建议使用Redis，我按这个方案实现")
    harness.chat("购物车功能开发完成")

    # 6. 汇报进度给项目经理
    print("\n[6] 汇报进度给项目经理")
    harness.switch_session("project_manager")
    harness.chat("购物车功能已开发完成")
    harness.chat("好的，记录进度")

    # 最终报告
    print("\n" + "=" * 60)
    print("最终会话报告")
    print("=" * 60)
    print(harness.get_session_report())


def main():
    print("=" * 60)
    print("HarnessGenJ 多会话记忆功能演示")
    print("在不打断主开发流程的情况下与其他角色沟通")
    print("=" * 60)

    demo_multi_session()
    demo_session_history()
    demo_session_report()
    demo_real_world_workflow()

    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)
    print("\n核心 API:")
    print("  harness.switch_session('product_manager')  # 切换会话")
    print("  harness.chat('消息内容')                   # 发送消息")
    print("  harness.get_session_history()             # 获取历史")
    print("  harness.list_sessions()                   # 列出会话")
    print("  harness.get_session_report()              # 会话报告")
    print("=" * 60)


if __name__ == "__main__":
    main()