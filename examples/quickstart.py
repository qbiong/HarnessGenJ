"""
HarnessGenJ Quick Start - Harness Engineering Framework

展示 Harness Engineering 核心理念:
- 角色驱动协作: 用真实团队角色替代抽象概念
- 工作流驱动: 需求→设计→开发→测试→文档→发布
- 一键执行: 快速完成开发任务
"""

from harnessgenj import (
    # 角色系统
    RoleType,
    Developer,
    Tester,
    ProductManager,
    Architect,
    DocWriter,
    ProjectManager,
    # 工作流系统
    WorkflowCoordinator,
    create_standard_pipeline,
    create_feature_pipeline,
    create_bugfix_pipeline,
    # 记忆管理
    MemoryManager,
    # 存储
    create_storage,
)


def demo_roles():
    """演示角色系统 - 每个角色有明确的职责和技能"""
    print("\n" + "=" * 50)
    print("角色系统演示")
    print("=" * 50)

    # 创建角色
    pm = ProductManager(role_id="pm_1", name="产品经理小王")
    dev = Developer(role_id="dev_1", name="开发人员小李")
    tester = Tester(role_id="test_1", name="测试人员小张")

    # 查看角色信息
    print("\n[角色职责]")
    print(f"  产品经理: {', '.join(pm.responsibilities[:3])}")
    print(f"  开发人员: {', '.join(dev.responsibilities[:3])}")
    print(f"  测试人员: {', '.join(tester.responsibilities[:3])}")

    # 查看角色技能
    print("\n[角色技能]")
    print(f"  产品经理: {', '.join(s.name for s in pm.list_skills())}")
    print(f"  开发人员: {', '.join(s.name for s in dev.list_skills())}")
    print(f"  测试人员: {', '.join(s.name for s in tester.list_skills())}")


def demo_workflow():
    """演示工作流系统 - 自动驱动角色协作"""
    print("\n" + "=" * 50)
    print("工作流系统演示")
    print("=" * 50)

    # 创建协调器
    coordinator = WorkflowCoordinator()

    # 组建团队
    coordinator.create_role(RoleType.PRODUCT_MANAGER, "pm_1", "产品经理")
    coordinator.create_role(RoleType.DEVELOPER, "dev_1", "开发人员")
    coordinator.create_role(RoleType.TESTER, "test_1", "测试人员")

    print("\n[团队组建完成]")
    for role in coordinator.list_roles():
        print(f"  - {role['name']} ({role['role_type']})")

    # 注册工作流
    coordinator.register_workflow("feature", create_feature_pipeline())

    print("\n[工作流: 功能开发流程]")
    print("  阶段: 需求分析 → 开发实现 → 测试验证")

    # 运行工作流
    result = coordinator.run_workflow(
        "feature",
        {"feature_request": "实现用户登录功能"},
    )

    print(f"\n[执行结果]")
    print(f"  状态: {result['status']}")
    print(f"  完成阶段: {len(result.get('results', []))}")
    print(f"  交付物: {result.get('artifacts', [])}")


def demo_quick_feature():
    """演示快速功能开发 - 一键完成"""
    print("\n" + "=" * 50)
    print("快速功能开发演示")
    print("=" * 50)

    coordinator = WorkflowCoordinator()

    # 自动创建默认团队
    coordinator.create_role(RoleType.PRODUCT_MANAGER, "pm_1")
    coordinator.create_role(RoleType.DEVELOPER, "dev_1")
    coordinator.create_role(RoleType.TESTER, "test_1")

    coordinator.register_workflow("feature", create_feature_pipeline())

    # 一键执行
    print("\n输入需求: 实现用户注册功能")

    result = coordinator.run_workflow(
        "feature",
        {"feature_request": "实现用户注册功能"},
    )

    print(f"\n输出状态: {result['status']}")
    print("流程自动完成: 需求分析 → 开发 → 测试")


def demo_quick_bugfix():
    """演示快速Bug修复"""
    print("\n" + "=" * 50)
    print("快速Bug修复演示")
    print("=" * 50)

    coordinator = WorkflowCoordinator()

    coordinator.create_role(RoleType.DEVELOPER, "dev_1")
    coordinator.create_role(RoleType.TESTER, "test_1")

    coordinator.register_workflow("bugfix", create_bugfix_pipeline())

    print("\n输入Bug: 登录页面无法提交表单")

    result = coordinator.run_workflow(
        "bugfix",
        {"bug_report": "登录页面无法提交表单"},
    )

    print(f"\n输出状态: {result['status']}")
    print("流程自动完成: Bug分析 → 修复 → 验证")


def demo_full_pipeline():
    """演示完整开发流水线"""
    print("\n" + "=" * 50)
    print("完整开发流水线演示")
    print("=" * 50)

    coordinator = WorkflowCoordinator()

    # 组建完整团队
    coordinator.create_role(RoleType.PRODUCT_MANAGER, "pm_1", "产品经理")
    coordinator.create_role(RoleType.ARCHITECT, "arch_1", "架构师")
    coordinator.create_role(RoleType.DEVELOPER, "dev_1", "开发人员")
    coordinator.create_role(RoleType.TESTER, "test_1", "测试人员")
    coordinator.create_role(RoleType.DOC_WRITER, "doc_1", "文档管理员")
    coordinator.create_role(RoleType.PROJECT_MANAGER, "mgr_1", "项目经理")

    print("\n[完整团队]")
    for role in coordinator.list_roles():
        print(f"  - {role['name']}")

    # 注册标准流水线
    coordinator.register_workflow("standard", create_standard_pipeline())

    print("\n[标准流水线]")
    print("  需求分析 → 架构设计 → 开发实现 → 测试验证 → 文档编写 → 发布评审")

    # 执行
    result = coordinator.run_workflow(
        "standard",
        {"user_request": "开发一个待办事项应用"},
    )

    print(f"\n[执行结果]")
    print(f"  状态: {result['status']}")
    print(f"  阶段数: {len(result.get('results', []))}")


def main():
    print("=" * 50)
    print("HarnessGenJ - Harness Engineering Framework")
    print("角色驱动协作 · 工作流驱动开发")
    print("=" * 50)

    demo_roles()
    demo_workflow()
    demo_quick_feature()
    demo_quick_bugfix()
    demo_full_pipeline()

    print("\n" + "=" * 50)
    print("演示完成!")
    print("=" * 50)
    print("\n核心概念:")
    print("  - 角色系统: Developer/Tester/PM/Architect等真实团队角色")
    print("  - 技能系统: 每个角色有特定技能集")
    print("  - 工作流: 需求→设计→开发→测试→文档→发布")
    print("  - 一键执行: 快速完成功能开发/Bug修复")
    print("=" * 50)


if __name__ == "__main__":
    main()