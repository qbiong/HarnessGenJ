"""
Example: JVM-style Memory Management Demo

演示 HarnessGenJ 框架的 JVM 风格记忆管理:
1. 分代记忆管理 (Eden → Survivor → Old → Permanent)
2. 自动记忆回收 (Minor GC, Major GC, Full GC)
3. 热点检测与自动装配 (类似 JIT)
"""

import asyncio
from harnessgenj import MemoryManager, MemoryHeap, GarbageCollector, HotspotDetector, AutoAssembler


async def demo_generational_memory() -> None:
    """演示分代记忆管理"""

    print("=" * 60)
    print("1. 分代记忆管理演示 (类似 JVM Heap 分代)")
    print("=" * 60)

    # 创建记忆管理器
    manager = MemoryManager(
        eden_size=100,          # Eden区大小
        survivor_size=50,       # Survivor区大小
        old_size=200,           # 老年代大小
        permanent_size=500,     # 永久代大小
        promotion_threshold=5,  # 晋升阈值
    )

    print(f"\n初始状态:")
    status = manager.get_memory_status()
    print(f"  Eden: {status['heap']['eden_size']}/{status['heap']['eden_max']}")
    print(f"  Old: {status['heap']['old_size']}/{status['heap']['old_max']}")

    # 1. 分配新消息到 Eden
    print(f"\n→ 分配新消息到 Eden 区:")
    for i in range(10):
        entry = manager.allocate_memory(f"消息 {i+1}: 用户提问...", importance=40 + i * 3)
        print(f"  [{entry.region.value}] {entry.content[:20]}... (重要性: {entry.importance})")

    # 2. 高重要性内容直接进 Old
    print(f"\n→ 高重要性内容直接进入老年代:")
    entry = manager.allocate_memory("核心业务规则: ...", importance=95)
    print(f"  [{entry.region.value}] 重要性 {entry.importance} 直接进入老年代")

    # 3. 大内容直接进 Old
    print(f"\n→ 大内容直接进入老年代:")
    large_content = "这是一段很长的历史记录..." * 100
    entry = manager.allocate_memory(large_content, importance=50)
    print(f"  [{entry.region.value}] 内容长度 {len(large_content)} 超过阈值进入老年代")

    # 4. 核心知识进入 Permanent
    print(f"\n→ 核心知识进入永久代:")
    manager.store_important_knowledge("agent_role", "你是一个专业的AI助手")
    manager.store_important_knowledge("core_rules", "遵循安全准则，保护用户隐私")
    print(f"  [permanent] agent_role: 你是一个专业的AI助手")
    print(f"  [permanent] core_rules: 遵循安全准则，保护用户隐私")

    status = manager.get_memory_status()
    print(f"\n当前状态:")
    print(f"  Eden: {status['heap']['eden_size']}/{status['heap']['eden_max']}")
    print(f"  Old: {status['heap']['old_size']}/{status['heap']['old_max']}")
    print(f"  Permanent: {status['heap']['permanent_size']}/{status['meta_space']['knowledge_count']}")


async def demo_garbage_collection() -> None:
    """演示垃圾回收机制"""

    print("\n" + "=" * 60)
    print("2. 垃圾回收演示 (类似 JVM GC)")
    print("=" * 60)

    manager = MemoryManager(
        eden_size=20,
        old_size=50,
        promotion_threshold=3,
    )

    # 填充 Eden
    print(f"\n→ 填充 Eden 区:")
    for i in range(20):
        importance = 30 + (i % 5) * 10  # 30-70 之间波动
        manager.allocate_memory(f"消息 {i+1}", importance=importance)

    status = manager.get_memory_status()
    print(f"  Eden 使用: {status['heap']['eden_size']}/{status['heap']['eden_max']}")

    # 触发 Minor GC
    print(f"\n→ 触发 Minor GC (Eden + Survivor):")
    result = manager.invoke_gc_minor()
    print(f"  算法: {result.algorithm.value}")
    print(f"  清除: {result.removed_count} 条")
    print(f"  晋升到老年代: {result.promoted_count} 条")
    print(f"  执行时间: {result.execution_time:.4f}s")

    status = manager.get_memory_status()
    print(f"  Eden 使用: {status['heap']['eden_size']}/{status['heap']['eden_max']}")
    print(f"  Old 使用: {status['heap']['old_size']}/{status['heap']['old_max']}")

    # 填充老年代并触发 Major GC
    print(f"\n→ 填充老年代:")
    for i in range(40):
        large = "x" * 600  # 大内容直接进Old
        manager.allocate_memory(large, importance=40)

    status = manager.get_memory_status()
    print(f"  Old 使用: {status['heap']['old_size']}/{status['heap']['old_max']}")

    print(f"\n→ 触发 Major GC (老年代):")
    result = manager.invoke_gc_major()
    print(f"  算法: {result.algorithm.value}")
    print(f"  清除: {result.removed_count} 条")
    print(f"  压缩: {result.details.get('compact', {})}")

    # Full GC
    print(f"\n→ 触发 Full GC (全堆):")
    result = manager.invoke_gc_full()
    print(f"  总清除: {result.removed_count} 条")

    # GC 统计
    stats = manager.heap.get_stats()
    print(f"\n→ GC 统计:")
    print(f"  Minor GC: {stats['minor_gc_count']} 次")
    print(f"  Major GC: {stats['major_gc_count']} 次")
    print(f"  Full GC: {stats['full_gc_count']} 次")
    print(f"  总清除: {stats['total_removed']} 条")


async def demo_hotspot_detection() -> None:
    """演示热点检测"""

    print("\n" + "=" * 60)
    print("3. 热点检测演示 (类似 JIT 热点检测)")
    print("=" * 60)

    manager = MemoryManager(compile_threshold=10)

    # 模拟工具调用
    print(f"\n→ 模拟工具调用:")
    tools = ["web_search", "summarize", "code_execute", "file_read"]

    # 频繁调用 web_search
    for i in range(25):
        manager.record_tool_usage("web_search", execution_time=0.1 + i * 0.01)

    # 中等频率调用 summarize
    for i in range(15):
        manager.record_tool_usage("summarize", execution_time=0.2)

    # 低频率调用其他
    for i in range(5):
        manager.record_tool_usage("code_execute", execution_time=0.5)
        manager.record_tool_usage("file_read", execution_time=0.05)

    print(f"  web_search: 25 次")
    print(f"  summarize: 15 次")
    print(f"  code_execute: 5 次")
    print(f"  file_read: 5 次")

    # 检测热点
    print(f"\n→ 检测热点:")
    hotspots = manager.detect_hotspots()
    for h in hotspots:
        print(f"  [{h.suggested_strategy}] {h.name}: 调用 {h.call_count} 次, 热度 {h.hotness_score:.2f}")

    # 热点统计
    stats = manager.hotspot_detector.get_stats()
    print(f"\n→ 热点统计:")
    print(f"  总调用: {stats['total_calls']} 次")
    print(f"  检测到热点: {stats['hotspots_count']} 个")
    print(f"  编译阈值: {stats['compile_threshold']}")


async def demo_auto_assembly() -> None:
    """演示自动装配"""

    print("\n" + "=" * 60)
    print("4. 自动装配演示 (类似 JIT 编译优化)")
    print("=" * 60)

    manager = MemoryManager(compile_threshold=5)

    # 定义知识库
    manager.store_important_knowledge(
        "api_endpoint",
        "API地址: https://api.example.com/v1"
    )
    manager.store_important_knowledge(
        "auth_token",
        "认证令牌:Bearer xxx"
    )

    # 频繁引用知识
    print(f"\n→ 频繁引用知识触发自动装配:")
    for i in range(20):
        manager.get_knowledge("api_endpoint")
        manager.get_knowledge("auth_token")

    # 检测热点并自动装配
    hotspots = manager.detect_hotspots()
    print(f"  检测到 {len(hotspots)} 个热点")

    templates = manager.auto_assemble()
    print(f"\n→ 自动装配结果:")
    for t in templates:
        print(f"  [{t.strategy}] {t.name}")
        if t.inlined_knowledge:
            print(f"    内联知识: {len(t.inlined_knowledge)} 条")
        if t.inlined_tools:
            print(f"    内联工具: {t.inlined_tools}")

    # 逃逸分析
    print(f"\n→ 逃逸分析:")
    result = manager.auto_assembler.perform_escape_analysis("local_context", dependencies=[])
    print(f"  local_context: {result.escape_level} (可内联: {result.can_inline})")

    result = manager.auto_assembler.perform_escape_analysis("global_context", dependencies=["a", "b", "c", "d"])
    print(f"  global_context: {result.escape_level} (可内联: {result.can_inline})")

    # 装配统计
    stats = manager.auto_assembler.get_stats()
    print(f"\n→ 装配统计:")
    print(f"  总装配: {stats['total_assemblies']} 次")
    print(f"  缓存命中: {stats['cache_hits']} 次")
    print(f"  内联知识: {stats['inlined_knowledge_count']} 条")


async def demo_full_workflow() -> None:
    """完整工作流演示"""

    print("\n" + "=" * 60)
    print("5. 完整工作流演示")
    print("=" * 60)

    manager = MemoryManager(
        eden_size=50,
        old_size=100,
        compile_threshold=10,
    )

    print(f"\n→ 模拟 Agent 执行流程:")

    # 1. 存储核心知识
    manager.store_important_knowledge("system_prompt", "你是一个研究助手")
    print(f"  [1] 存储核心知识到永久代")

    # 2. 执行任务栈
    frame = manager.push_task("研究AI趋势")
    print(f"  [2] 压入任务栈: 研究AI趋势")

    frame.set_local("step", "collecting")
    manager.set_task_progress("研究AI趋势", total_steps=5)

    # 3. 存储对话
    manager.store_conversation("请研究最新的AI趋势", role="user", importance=60)
    print(f"  [3] 存储用户消息到 Eden")

    # 4. 记录工具使用
    for i in range(15):
        manager.record_tool_usage("web_search", execution_time=0.1)
    print(f"  [4] 记录工具调用: web_search x15")

    # 5. 自动优化
    actions = manager.optimize_if_needed()
    print(f"  [5] 自动优化:")
    if "gc" in actions:
        print(f"      GC: 清除 {actions['gc']['removed_count']} 条")
    if "assembled" in actions:
        print(f"      装配: {actions['assembled']} 个模板")

    # 6. 健康报告
    health = manager.get_health_report()
    print(f"\n→ 健康报告:")
    print(f"  状态: {health['status']}")
    print(f"  Eden压力: {health['eden_pressure']:.2%}")
    print(f"  Old压力: {health['old_pressure']:.2%}")
    if health['recommendations']:
        print(f"  建议: {health['recommendations'][0]}")

    # 7. 完整状态
    print(f"\n→ 完整记忆状态:")
    status = manager.get_memory_status()
    print(f"  Heap: Eden={status['heap']['eden_size']}, Old={status['heap']['old_size']}")
    print(f"  Stack: 深度={status['stack']['depth']}")
    print(f"  GC: Minor={status['heap']['minor_gc_count']}, Major={status['heap']['major_gc_count']}")
    print(f"  Hotspots: {status['hotspot']['hotspots_count']} 个")


async def main() -> None:
    """主函数"""

    print("\n" + "=" * 60)
    print("HarnessGenJ - JVM风格记忆管理演示")
    print("=" * 60)

    await demo_generational_memory()
    await demo_garbage_collection()
    await demo_hotspot_detection()
    await demo_auto_assembly()
    await demo_full_workflow()

    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())