"""
Example: Multi-Agent Coordination

演示如何使用 HarnessGenJ 框架进行多 Agent 协调
"""

import asyncio
from harnessgenj import Harness, AgentSpec, AgentManifest
from harnessgenj.harness import SubagentManager, SubagentConfig


async def main() -> None:
    """主函数 - 多Agent协调示例"""

    # 1. 创建 Harness
    harness = Harness()

    # 2. 定义多个 Agent
    coordinator = AgentSpec(
        name="coordinator",
        description="协调Agent，负责任务分配和结果聚合",
        capabilities=[{"name": "planning"}, {"name": "delegation"}],
    )

    researcher = AgentSpec(
        name="researcher",
        description="研究Agent，负责信息收集",
        tools=[{"name": "web_search"}],
    )

    analyst = AgentSpec(
        name="analyst",
        description="分析Agent，负责数据处理和总结",
        tools=[{"name": "summarize"}, {"name": "code_execute"}],
    )

    # 3. 加载所有 Agent
    for spec in [coordinator, researcher, analyst]:
        harness.load_agent(spec)

    print(f"已注册Agent: {harness.list_agents()}")

    # 4. 配置子代理管理器
    subagent_manager = SubagentManager()

    # 注册子代理
    subagent_manager.register(SubagentConfig(
        name="researcher",
        description="执行研究任务的子代理",
        tools=["web_search"],
    ))

    subagent_manager.register(SubagentConfig(
        name="analyst",
        description="执行分析任务的子代理",
        tools=["summarize", "code_execute"],
    ))

    # 5. 委托任务
    research_task = await subagent_manager.delegate(
        task_description="收集AI领域最新进展的信息",
        subagent_type="researcher",
    )
    print(f"\n研究任务状态: {research_task.status}")

    analysis_task = await subagent_manager.delegate(
        task_description="分析收集到的信息并生成报告",
        subagent_type="analyst",
    )
    print(f"\n分析任务状态: {analysis_task.status}")

    # 6. 聚合结果
    results = subagent_manager.aggregate_results([
        research_task.task_id,
        analysis_task.task_id,
    ])
    print(f"\n聚合结果: {results}")


if __name__ == "__main__":
    asyncio.run(main())