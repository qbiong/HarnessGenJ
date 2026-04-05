"""
Example: Operating System Style Task Management Demo

演示 HarnessGenJ 框架的操作系统风格任务管理:
1. 调度器 (Scheduler) - 任务调度
2. 生产者 (Producer) - 任务生产
3. 消费者 (Consumer) - 任务消费
4. 闭环管理 - 任务生命周期
"""

import asyncio
from harnessgenj.kernel import (
    Task,
    TaskStatus,
    TaskPriority,
    TaskResult,
    TaskKernel,
    Scheduler,
    SchedulingAlgorithm,
    Producer,
    ProducerRole,
)
from harnessgenj.kernel.producer import ProducerConfig, TaskFactory
from harnessgenj.kernel.consumer import ConsumerPool, WorkerConsumer


async def demo_task_lifecycle() -> None:
    """演示任务生命周期"""

    print("=" * 60)
    print("1. 任务生命周期演示")
    print("=" * 60)

    kernel = TaskKernel()

    print("\n→ 创建任务:")
    task = kernel.register_task(
        name="research_ai",
        description="研究AI最新进展",
        priority=TaskPriority.HIGH,
    )
    print(f"  任务ID: {task.id}")
    print(f"  状态: {task.status.value}")

    print("\n→ 发布任务 (CREATED → READY):")
    kernel.queue.update_task_status(task.id, TaskStatus.READY, "Published")
    print(f"  状态: {kernel.queue.get_task(task.id).status.value}")

    print("\n→ 开始任务 (READY → RUNNING):")
    kernel.start_task(task.id, assigned_to="consumer_1")
    print(f"  状态: {kernel.queue.get_task(task.id).status.value}")
    print(f"  分配给: {kernel.queue.get_task(task.id).assigned_to}")

    print("\n→ 完成任务 (RUNNING → DONE):")
    result = TaskResult(success=True, output="AI研究完成，发现...")
    kernel.complete_task(task.id, result)
    print(f"  状态: {kernel.queue.get_task(task.id).status.value}")

    print("\n→ 闭环验证:")
    verification = kernel.verify_all_closures()
    print(f"  全部闭环: {verification['all_closed']}")


async def demo_producer_consumer() -> None:
    """演示生产者-消费者模式"""

    print("\n" + "=" * 60)
    print("2. 生产者-消费者演示")
    print("=" * 60)

    kernel = TaskKernel()
    scheduler = Scheduler(kernel)

    # 创建生产者
    producer_config = ProducerConfig(
        id="manager_1",
        role=ProducerRole.MANAGER,
        name="Manager Agent",
    )
    producer = Producer(kernel, producer_config)

    print("\n→ 生产者创建任务:")
    task1 = producer.create_and_publish(
        name="分析数据",
        description="分析用户行为数据",
        priority=TaskPriority.HIGH,
    )
    task2 = producer.create_and_publish(
        name="生成报告",
        description="生成周报",
        priority=TaskPriority.NORMAL,
    )
    print(f"  创建任务: {task1.name} (优先级: {task1.priority.value})")
    print(f"  创建任务: {task2.name} (优先级: {task2.priority.value})")

    # 创建消费者池
    pool = ConsumerPool(kernel, scheduler)

    print("\n→ 创建消费者:")
    worker1 = pool.create_worker("Worker-1", capabilities=["general"])
    worker2 = pool.create_worker("Worker-2", capabilities=["analysis"])
    print(f"  Worker-1: 通用工作者")
    print(f"  Worker-2: 分析专家")

    print("\n→ 消费者状态:")
    status = scheduler.get_consumer_status()
    print(f"  总消费者: {status['total_consumers']}")
    print(f"  空闲: {status['idle_consumers']}")


async def demo_scheduler() -> None:
    """演示调度器"""

    print("\n" + "=" * 60)
    print("3. 调度器演示")
    print("=" * 60)

    kernel = TaskKernel()
    scheduler = Scheduler(kernel, algorithm=SchedulingAlgorithm.PRIORITY)

    # 注册消费者
    scheduler.register_consumer("consumer_1", capabilities=["general"])
    scheduler.register_consumer("consumer_2", capabilities=["research"])

    print("\n→ 创建不同优先级任务:")
    low = kernel.register_task(name="低优先级任务", priority=TaskPriority.LOW)
    high = kernel.register_task(name="高优先级任务", priority=TaskPriority.HIGH)
    critical = kernel.register_task(name="紧急任务", priority=TaskPriority.CRITICAL)

    for task in [low, high, critical]:
        kernel.queue.update_task_status(task.id, TaskStatus.READY)

    print(f"  {low.name}: 优先级 {low.priority.value}")
    print(f"  {high.name}: 优先级 {high.priority.value}")
    print(f"  {critical.name}: 优先级 {critical.priority.value}")

    print("\n→ 执行调度 (按优先级):")
    results = scheduler.schedule()
    for r in results:
        print(f"  调度: {r['task_name']} → {r['consumer_id']}")

    print("\n→ 队列状态:")
    queue_status = scheduler.get_queue_status()
    print(f"  Ready: {queue_status['ready']}")
    print(f"  Running: {queue_status['running']}")


async def demo_task_dependencies() -> None:
    """演示任务依赖"""

    print("\n" + "=" * 60)
    print("4. 任务依赖演示")
    print("=" * 60)

    kernel = TaskKernel()
    scheduler = Scheduler(kernel)

    print("\n→ 创建任务链 (有依赖关系):")

    # 任务1: 收集数据
    task1 = kernel.register_task(name="1.收集数据", priority=TaskPriority.HIGH)
    kernel.queue.update_task_status(task1.id, TaskStatus.READY)

    # 任务2: 分析数据 (依赖任务1)
    task2 = kernel.register_task(
        name="2.分析数据",
        dependencies=[task1.id],
    )
    kernel.queue.update_task_status(task2.id, TaskStatus.READY)

    # 任务3: 生成报告 (依赖任务2)
    task3 = kernel.register_task(
        name="3.生成报告",
        dependencies=[task2.id],
    )
    kernel.queue.update_task_status(task3.id, TaskStatus.READY)

    print(f"  {task1.name} (无依赖)")
    print(f"  {task2.name} (依赖: {task1.name})")
    print(f"  {task3.name} (依赖: {task2.name})")

    print("\n→ 检查依赖满足情况:")
    print(f"  {task1.name}: 依赖满足 = {kernel.dependency_graph.check_dependencies_met(task1.id)}")
    print(f"  {task2.name}: 依赖满足 = {kernel.dependency_graph.check_dependencies_met(task2.id)}")
    print(f"  {task3.name}: 依赖满足 = {kernel.dependency_graph.check_dependencies_met(task3.id)}")

    print("\n→ 执行任务链:")
    scheduler.register_consumer("worker_1")

    # 执行任务1
    scheduler.schedule()
    kernel.start_task(task1.id, "worker_1")
    kernel.complete_task(task1.id, TaskResult(success=True, output="数据已收集"))

    print(f"  {task1.name} ✓ 完成")

    # 检查任务2依赖
    print(f"  {task2.name}: 依赖满足 = {kernel.dependency_graph.check_dependencies_met(task2.id)}")


async def demo_task_decomposition() -> None:
    """演示任务分解"""

    print("\n" + "=" * 60)
    print("5. 任务分解演示")
    print("=" * 60)

    kernel = TaskKernel()
    producer = Producer(kernel)

    print("\n→ 创建父任务:")
    parent = producer.create_task(
        name="研究项目",
        description="完整的AI研究项目",
        priority=TaskPriority.HIGH,
    )
    print(f"  父任务: {parent.name}")

    print("\n→ 分解为子任务:")
    subtask_defs = [
        {"description": "文献调研", "type": "research"},
        {"description": "数据收集", "type": "data"},
        {"description": "模型训练", "type": "ml"},
        {"description": "结果分析", "type": "analysis"},
    ]

    subtasks = producer.decompose_task(parent, subtask_defs)
    for i, subtask in enumerate(subtasks):
        print(f"  子任务 {i+1}: {subtask.name} - {subtask.metadata.get('description', '')}")

    print(f"\n→ 父任务信息:")
    print(f"  子任务数量: {parent.metadata.get('subtask_count')}")


async def demo_parallel_tasks() -> None:
    """演示并行任务"""

    print("\n" + "=" * 60)
    print("6. 并行任务演示")
    print("=" * 60)

    kernel = TaskKernel()
    producer = Producer(kernel)

    print("\n→ 创建并行任务组:")

    parallel_defs = [
        {"name": "分析用户A"},
        {"name": "分析用户B"},
        {"name": "分析用户C"},
    ]

    merge_def = {"name": "汇总分析结果"}

    tasks = producer.create_parallel_tasks(parallel_defs, merge_def)

    print("  并行任务:")
    for task in tasks[:-1]:
        print(f"    - {task.name}")

    print(f"  合并任务: {tasks[-1].name}")
    print(f"    依赖: {len(tasks[-1].dependencies)} 个并行任务")


async def demo_closed_loop_management() -> None:
    """演示闭环管理"""

    print("\n" + "=" * 60)
    print("7. 闭环管理演示")
    print("=" * 60)

    kernel = TaskKernel()
    scheduler = Scheduler(kernel)
    producer = Producer(kernel)

    scheduler.register_consumer("worker_1")

    print("\n→ 完整任务流程:")

    # 1. 生产者创建任务
    task = producer.create_and_publish(
        name="闭环测试任务",
        description="验证任务闭环管理",
    )
    print(f"  [1] 生产者创建任务: {task.name}")

    # 2. 调度器调度任务
    scheduler.schedule()
    print(f"  [2] 调度器分配任务给消费者")

    # 3. 消费者执行任务
    kernel.start_task(task.id, "worker_1")
    print(f"  [3] 消费者开始执行")

    # 4. 完成任务
    result = TaskResult(success=True, output="执行完成")
    kernel.complete_task(task.id, result)
    print(f"  [4] 消费者完成任务")

    # 5. 闭环验证
    verification = kernel.verify_all_closures()
    print(f"  [5] 闭环验证: {'成功' if verification['all_closed'] else '失败'}")

    # 6. 统计报告
    stats = kernel.get_stats()
    print(f"\n→ 统计报告:")
    print(f"  创建: {stats.total_tasks_created}")
    print(f"  完成: {stats.total_tasks_completed}")
    print(f"  失败: {stats.total_tasks_failed}")

    # 7. 健康报告
    health = kernel.get_health_report()
    print(f"\n→ 健康报告:")
    print(f"  状态: {health['status']}")
    print(f"  失败率: {health['failure_rate']:.2%}")


async def demo_task_factory() -> None:
    """演示任务工厂"""

    print("\n" + "=" * 60)
    print("8. 任务工厂演示")
    print("=" * 60)

    kernel = TaskKernel()
    producer = Producer(kernel)
    factory = TaskFactory(producer)

    print("\n→ 使用工厂创建研究任务:")
    research_task = factory.create_research_task("量子计算", depth="deep")
    print(f"  任务: {research_task.name}")
    print(f"  类型: {research_task.type}")
    print(f"  优先级: {research_task.priority.value}")

    print("\n→ 创建工作流任务链:")
    steps = [
        "数据预处理",
        "特征提取",
        "模型训练",
        "模型评估",
    ]
    workflow = factory.create_workflow_task("ML Pipeline", steps)
    print(f"  工作流步骤: {len(workflow)} 个任务")
    for i, task in enumerate(workflow):
        print(f"    {i+1}. {task.name}")


async def main() -> None:
    """主函数"""

    print("\n" + "=" * 60)
    print("HarnessGenJ - 操作系统风格任务管理演示")
    print("=" * 60)

    await demo_task_lifecycle()
    await demo_producer_consumer()
    await demo_scheduler()
    await demo_task_dependencies()
    await demo_task_decomposition()
    await demo_parallel_tasks()
    await demo_closed_loop_management()
    await demo_task_factory()

    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())