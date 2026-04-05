"""
Hotspot Detector - JIT-style Hotspot Detection

严格实现 JIT 编译器中的热点检测机制:
- 统计工具/知识调用频率
- 统计方法执行次数
- 检测热点触发自动装配
"""

from typing import Any
from pydantic import BaseModel, Field
from collections import defaultdict
import time


class CallCounter(BaseModel):
    """
    调用计数器 - 类似 JIT 的方法计数器

    JVM 有两种计数器:
    - Method Call Counter: 方法调用次数
    - Back-edge Counter: 循环回边次数

    Agent 对应:
    - Tool Call Counter: 工具调用次数
    - Knowledge Reference Counter: 知识引用次数
    """

    name: str = Field(..., description="名称")
    call_count: int = Field(default=0, ge=0, description="调用次数")
    back_edge_count: int = Field(default=0, ge=0, description="回边次数(循环)")
    total_execution_time: float = Field(default=0.0, description="总执行时间")
    avg_execution_time: float = Field(default=0.0, description="平均执行时间")
    last_call_time: float = Field(default=0.0, description="最后调用时间")
    created_at: float = Field(default_factory=time.time, description="创建时间")

    def record_call(self, execution_time: float = 0.0) -> None:
        """记录一次调用"""
        self.call_count += 1
        self.total_execution_time += execution_time
        self.avg_execution_time = self.total_execution_time / self.call_count
        self.last_call_time = time.time()

    def record_back_edge(self) -> None:
        """记录一次回边 (循环执行)"""
        self.back_edge_count += 1

    def get_hotness_score(self) -> float:
        """
        计算热度分数

        基于多个因素:
        1. 调用次数权重
        2. 回边次数权重 (循环热点)
        3. 执行频率 (调用次数/时间)
        """
        time_elapsed = time.time() - self.created_at
        if time_elapsed <= 0:
            return 0

        # 调用频率
        call_frequency = self.call_count / time_elapsed

        # 综合热度 = 调用次数 + 回边次数 * 2 + 调用频率 * 100
        hotness = self.call_count + self.back_edge_count * 2 + call_frequency * 100

        return hotness


class HotspotInfo(BaseModel):
    """
    热点信息 - 类似 JIT 检测到的热点方法

    包含:
    - 热点名称
    - 热度分数
    - 是否达到编译阈值
    - 建议的优化策略
    """

    name: str = Field(..., description="热点名称")
    hotness_score: float = Field(default=0.0, description="热度分数")
    call_count: int = Field(default=0, description="调用次数")
    threshold_reached: bool = Field(default=False, description="是否达到阈值")
    suggested_strategy: str = Field(default="inline", description="建议策略")
    counter: CallCounter | None = Field(default=None, description="计数器详情")


class HotspotDetector:
    """
    热点检测器 - 类似 JIT 编译器的热点检测

    JVM JIT 热点检测机制:
    1. 方法调用计数器
    2. 循环回边计数器
    3. 达到阈值触发编译

    Agent 对应实现:
    1. 工具调用计数器 - 统计工具使用频率
    2. 知识引用计数器 - 统计知识访问频率
    3. Agent调用计数器 - 统计Agent使用频率
    4. 回边计数器 - 检测重复执行模式
    """

    def __init__(
        self,
        compile_threshold: int = 100,         # 类似 -XX:CompileThreshold
        back_edge_threshold: int = 50,        # 类似 -XX:BackEdgeThreshold
        on_stack_replacement: bool = True,   # 类似 -XX:+OnStackReplacement
        time_decay: bool = True,             # 是否启用时间衰减
        decay_factor: float = 0.95,          # 衰减因子
    ) -> None:
        self.compile_threshold = compile_threshold
        self.back_edge_threshold = back_edge_threshold
        self.on_stack_replacement = on_stack_replacement
        self.time_decay = time_decay
        self.decay_factor = decay_factor

        # 计数器
        self._tool_counters: dict[str, CallCounter] = {}
        self._knowledge_counters: dict[str, CallCounter] = {}
        self._agent_counters: dict[str, CallCounter] = {}
        self._pattern_counters: dict[str, CallCounter] = {}  # 执行模式计数器

        # 已检测到的热点
        self._hotspots: dict[str, HotspotInfo] = {}

        # 统计
        self._stats = {
            "total_calls": 0,
            "hotspots_detected": 0,
            "last_detection_time": 0,
        }

    def record_tool_call(
        self,
        tool_name: str,
        execution_time: float = 0.0,
        is_repeated: bool = False,
    ) -> CallCounter:
        """
        记录工具调用 - 类似 JIT 方法调用计数

        Args:
            tool_name: 工具名称
            execution_time: 执行时间
            is_repeated: 是否重复调用 (循环)

        Returns:
            更新后的计数器
        """
        if tool_name not in self._tool_counters:
            self._tool_counters[tool_name] = CallCounter(name=tool_name)

        counter = self._tool_counters[tool_name]
        counter.record_call(execution_time)

        if is_repeated:
            counter.record_back_edge()

        self._stats["total_calls"] += 1

        # 检查是否达到阈值
        self._check_threshold(tool_name, counter, "tool")

        return counter

    def record_knowledge_reference(
        self,
        knowledge_key: str,
        execution_time: float = 0.0,
        is_repeated: bool = False,
    ) -> CallCounter:
        """
        记录知识引用 - 类似 JIT 方法调用计数

        Args:
            knowledge_key: 知识键
            execution_time: 执行时间
            is_repeated: 是否重复引用

        Returns:
            更新后的计数器
        """
        if knowledge_key not in self._knowledge_counters:
            self._knowledge_counters[knowledge_key] = CallCounter(name=knowledge_key)

        counter = self._knowledge_counters[knowledge_key]
        counter.record_call(execution_time)

        if is_repeated:
            counter.record_back_edge()

        self._stats["total_calls"] += 1

        # 检查是否达到阈值
        self._check_threshold(knowledge_key, counter, "knowledge")

        return counter

    def record_agent_call(
        self,
        agent_name: str,
        execution_time: float = 0.0,
        is_repeated: bool = False,
    ) -> CallCounter:
        """
        记录Agent调用

        Args:
            agent_name: Agent名称
            execution_time: 执行时间
            is_repeated: 是否重复调用

        Returns:
            更新后的计数器
        """
        if agent_name not in self._agent_counters:
            self._agent_counters[agent_name] = CallCounter(name=agent_name)

        counter = self._agent_counters[agent_name]
        counter.record_call(execution_time)

        if is_repeated:
            counter.record_back_edge()

        self._stats["total_calls"] += 1

        # 检查是否达到阈值
        self._check_threshold(agent_name, counter, "agent")

        return counter

    def record_execution_pattern(
        self,
        pattern_name: str,
        execution_time: float = 0.0,
    ) -> CallCounter:
        """
        记录执行模式 - 类似 JIT 检测热点代码路径

        Args:
            pattern_name: 模式名称
            execution_time: 执行时间

        Returns:
            更新后的计数器
        """
        if pattern_name not in self._pattern_counters:
            self._pattern_counters[pattern_name] = CallCounter(name=pattern_name)

        counter = self._pattern_counters[pattern_name]
        counter.record_call(execution_time)

        self._stats["total_calls"] += 1

        # 检查是否达到阈值
        self._check_threshold(pattern_name, counter, "pattern")

        return counter

    def _check_threshold(self, name: str, counter: CallCounter, category: str) -> None:
        """
        检查是否达到编译阈值 - 类似 JIT 的阈值检测

        JVM 会在以下情况触发编译:
        1. 方法调用次数 > CompileThreshold
        2. 循环回边次数 > BackEdgeThreshold (OSR编译)
        """
        threshold_reached = False
        suggested_strategy = "inline"

        # 检查调用阈值
        if counter.call_count >= self.compile_threshold:
            threshold_reached = True
            suggested_strategy = "inline"

        # 检查回边阈值 (OSR编译)
        if counter.back_edge_count >= self.back_edge_threshold and self.on_stack_replacement:
            threshold_reached = True
            suggested_strategy = "osr"  # On-Stack Replacement

        # 记录热点
        if threshold_reached and name not in self._hotspots:
            hotspot = HotspotInfo(
                name=name,
                hotness_score=counter.get_hotness_score(),
                call_count=counter.call_count,
                threshold_reached=True,
                suggested_strategy=suggested_strategy,
                counter=counter,
            )
            self._hotspots[name] = hotspot
            self._stats["hotspots_detected"] += 1
            self._stats["last_detection_time"] = time.time()

    def detect_hotspots(self) -> list[HotspotInfo]:
        """
        检测所有热点 - 类似 JIT 扫描热点方法

        Returns:
            按热度排序的热点列表
        """
        # 应用时间衰减
        if self.time_decay:
            self._apply_decay()

        # 收集所有热点
        hotspots = list(self._hotspots.values())

        # 按热度排序
        hotspots.sort(key=lambda h: h.hotness_score, reverse=True)

        return hotspots

    def get_hotspot(self, name: str) -> HotspotInfo | None:
        """获取特定热点信息"""
        return self._hotspots.get(name)

    def is_hotspot(self, name: str) -> bool:
        """判断是否为热点"""
        return name in self._hotspots

    def get_top_hotspots(self, top_n: int = 10) -> list[HotspotInfo]:
        """获取前N个热点"""
        hotspots = self.detect_hotspots()
        return hotspots[:top_n]

    def _apply_decay(self) -> None:
        """
        应用时间衰减 - 类似 JIT 的计数器衰减

        JVM 会定期衰减计数器以避免长期累积
        """
        for counter in self._tool_counters.values():
            counter.call_count = int(counter.call_count * self.decay_factor)

        for counter in self._knowledge_counters.values():
            counter.call_count = int(counter.call_count * self.decay_factor)

        for counter in self._agent_counters.values():
            counter.call_count = int(counter.call_count * self.decay_factor)

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        return {
            **self._stats,
            "tool_counters": len(self._tool_counters),
            "knowledge_counters": len(self._knowledge_counters),
            "agent_counters": len(self._agent_counters),
            "pattern_counters": len(self._pattern_counters),
            "hotspots_count": len(self._hotspots),
            "compile_threshold": self.compile_threshold,
            "back_edge_threshold": self.back_edge_threshold,
        }

    def reset(self) -> None:
        """重置所有计数器"""
        self._tool_counters.clear()
        self._knowledge_counters.clear()
        self._agent_counters.clear()
        self._pattern_counters.clear()
        self._hotspots.clear()
        self._stats = {
            "total_calls": 0,
            "hotspots_detected": 0,
            "last_detection_time": 0,
        }