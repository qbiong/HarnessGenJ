"""
Example: Basic Agent Usage

演示如何使用 HarnessGenJ 框架创建和运行一个简单的 Agent
"""

import asyncio
from harnessgenj import Harness, AgentSpec, ToolSpec, CapabilitySpec
from harnessgenj.runtime import ExecutionStrategy


async def main() -> None:
    """主函数"""

    # 1. 创建 Harness 实例
    harness = Harness(strategy=ExecutionStrategy.SEQUENTIAL)

    # 2. 定义 Agent 规范
    agent_spec = AgentSpec(
        name="research-agent",
        description="一个用于研究和分析的Agent",
        version="1.0.0",
        tools=[
            ToolSpec(
                name="web_search",
                description="搜索网络获取信息",
                parameters={
                    "query": {"type": "string", "description": "搜索查询"},
                    "max_results": {"type": "integer", "default": 5},
                },
            ),
            ToolSpec(
                name="summarize",
                description="总结文本内容",
                parameters={
                    "text": {"type": "string", "description": "要总结的文本"},
                },
            ),
        ],
        capabilities=[
            CapabilitySpec(name="planning", enabled=True),
            CapabilitySpec(name="delegation", enabled=True),
        ],
        system_prompt="你是一个研究助手，帮助用户收集和分析信息。",
        max_tokens=4096,
        timeout=300,
    )

    # 3. 加载 Agent
    harness.load_agent(agent_spec)
    print(f"已注册的Agent: {harness.list_agents()}")

    # 4. 运行任务
    result = await harness.run(
        spec="research-agent",
        task="研究2025年AI领域的最新发展趋势",
    )

    # 5. 输出结果
    print(f"\n执行结果:")
    print(f"  成功: {result.success}")
    print(f"  输出: {result.output}")
    print(f"  步骤: {result.steps}")

    # 6. 查看上下文
    agents = harness.list_agents()
    if agents:
        context = harness.save_context(agents[0])
        print(f"\n上下文快照: {context}")


if __name__ == "__main__":
    asyncio.run(main())