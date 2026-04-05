"""
Example: Using Harness Built-in Capabilities

演示如何使用 Harness 的内置能力
"""

import asyncio
from harnessgenj.harness import (
    PlanningTool,
    VirtualFS,
    LocalStorage,
    CodeSandbox,
    HumanLoop,
    ExecutionEnvironment,
)
from pathlib import Path
import tempfile


async def main() -> None:
    """主函数 - Harness内置能力示例"""

    print("=" * 50)
    print("HarnessGenJ Harness 内置能力演示")
    print("=" * 50)

    # 1. Planning Tool - 任务规划
    print("\n1. Planning Tool (任务规划)")
    planning = PlanningTool()
    plan = planning.create_plan("project-plan")

    # 添加任务
    task1 = plan.add("分析需求", priority=1)
    task2 = plan.add("设计架构", priority=2, dependencies=[task1.id])
    task3 = plan.add("实现代码", priority=3, dependencies=[task2.id])
    task4 = plan.add("测试验证", priority=4, dependencies=[task3.id])

    print(f"  创建了 {len(plan.items)} 个任务")
    print(f"  进度: {planning.get_progress('project-plan')}")

    # 执行任务
    for _ in range(4):
        next_task = plan.get_next_ready()
        if next_task:
            plan.update_status(next_task.id, "completed")
            print(f"  ✓ 完成: {next_task.content}")

    # 2. Virtual Filesystem - 虚拟文件系统
    print("\n2. Virtual Filesystem (虚拟文件系统)")
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = LocalStorage(Path(tmpdir))
        fs = VirtualFS(storage)

        # 写入文件
        await fs.write("notes.txt", "AI框架设计笔记\n...")
        await fs.write("config.json", '{"version": "1.0.0"}')

        print(f"  文件列表: {await fs.list_files()}")

        # 读取文件
        content = await fs.read("notes.txt")
        print(f"  读取 notes.txt: {content.content[:30]}...")

    # 3. Code Sandbox - 代码沙箱
    print("\n3. Code Sandbox (代码沙箱)")
    sandbox = CodeSandbox()

    # 安全代码
    safe_code = """
result = sum(range(1, 11))
print(f"Sum of 1-10: {result}")
"""
    result = await sandbox.execute(safe_code)
    print(f"  安全代码执行: {result.success}")

    # 危险代码检测
    dangerous_code = "import os; os.system('echo dangerous')"
    issues = sandbox.validate_code(dangerous_code)
    print(f"  危险代码检测: 发现 {len(issues)} 个问题")

    # 4. Human-in-the-loop - 人机交互
    print("\n4. Human-in-the-loop (人机交互)")
    human_loop = HumanLoop()

    # 创建审批请求
    request = await human_loop.request_approval(
        action="删除测试文件?",
        context={"files": ["test1.txt", "test2.txt"]},
    )
    print(f"  审批请求: {request.action}")
    print(f"  状态: {request.status.value}")

    # 模拟响应
    response = human_loop.respond_approval(
        request.request_id,
        approved=True,
        feedback="同意删除",
    )
    print(f"  审批结果: {response.approved}")

    print("\n" + "=" * 50)
    print("演示完成!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())