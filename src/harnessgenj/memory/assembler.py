"""
Auto Assembler - JIT-style Hotspot Optimization

严格实现 JIT 编译器的优化机制:
- 知识内联 (类似方法内联)
- 工具内联 (类似代码内联)
- 模板缓存 (类似 Code Cache)
- 逃逸分析 (类似 JIT 逃逸分析)
"""

from typing import Any
from pydantic import BaseModel, Field
import time


class AssemblyTemplate(BaseModel):
    """
    装配模板 - 类似 JIT 的编译代码缓存

    JVM Code Cache 存储:
    - 编译后的本地代码
    - 编译信息

    Agent 对应:
    - 内联后的执行模板
    - 预装配的工具链
    - 常用知识摘要
    """

    template_id: str = Field(..., description="模板ID")
    name: str = Field(..., description="模板名称")
    category: str = Field(..., description="类别: tool/knowledge/pattern")
    strategy: str = Field(..., description="策略: inline/osr/cache")

    # 内联内容
    inlined_knowledge: list[str] = Field(default_factory=list, description="内联知识")
    inlined_tools: list[str] = Field(default_factory=list, description="内联工具")
    execution_template: str | None = Field(default=None, description="执行模板")

    # 统计
    usage_count: int = Field(default=0, description="使用次数")
    creation_time: float = Field(default_factory=time.time, description="创建时间")
    last_used_time: float = Field(default_factory=time.time, description="最后使用时间")

    # 效果
    speedup_factor: float = Field(default=1.0, description="加速因子")
    original_execution_time: float = Field(default=0.0, description="原始执行时间")
    optimized_execution_time: float = Field(default=0.0, description="优化后执行时间")


class EscapeAnalysisResult(BaseModel):
    """
    逃逸分析结果 - 类似 JIT 逃逸分析

    JIT 逃逸分析判断:
    - NoEscape: 对象不逃逸方法，可栈上分配
    - ArgEscape: 对象作为参数逃逸
    - GlobalEscape: 对象全局逃逸

    Agent 对应:
    - NoEscape: 上下文仅在本任务有效，可内联
    - ArgEscape: 上下文传递给子任务
    - GlobalEscape: 上下文全局共享
    """

    name: str = Field(..., description="分析对象")
    escape_level: str = Field(..., description="逃逸级别: no_escape/arg_escape/global_escape")
    can_inline: bool = Field(default=False, description="是否可内联")
    can_stack_allocate: bool = Field(default=False, description="是否可栈分配")
    dependencies: list[str] = Field(default_factory=list, description="依赖项")
    details: dict[str, Any] = Field(default_factory=dict, description="详情")


class AutoAssembler:
    """
    自动装配器 - 类似 JIT 编译器

    JIT 编译优化机制:
    1. 方法内联 (Method Inlining): 将热点方法代码嵌入调用处
    2. 逃逸分析 (Escape Analysis): 分析对象作用范围
    3. 循环优化 (Loop Optimization): OSR编译热点循环
    4. 代码缓存 (Code Cache): 缓存编译结果
    5. 死代码消除 (Dead Code Elimination): 删除无用代码

    Agent 对应实现:
    1. 知识内联: 将高频知识嵌入Agent执行流程
    2. 工具内联: 预加载和优化高频工具
    3. 上下文逃逸分析: 分析上下文依赖范围
    4. 执行模板缓存: 缓存常用执行模板
    5. 无用内容消除: 清理低频内容
    """

    def __init__(
        self,
        max_inline_size: int = 1000,         # 类似 -XX:MaxInlineSize
        inline_frequency_threshold: int = 50, # 类似 -XX:InlineFrequency
        cache_size: int = 100,               # 模板缓存大小
        enable_escape_analysis: bool = True, # 启用逃逸分析
    ) -> None:
        self.max_inline_size = max_inline_size
        self.inline_frequency_threshold = inline_frequency_threshold
        self.cache_size = cache_size
        self.enable_escape_analysis = enable_escape_analysis

        # 模板缓存 (类似 JIT Code Cache)
        self._template_cache: dict[str, AssemblyTemplate] = {}

        # 统计
        self._stats = {
            "total_assemblies": 0,
            "inlined_knowledge_count": 0,
            "inlined_tools_count": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "avg_speedup": 0.0,
        }

    def assemble(self, hotspot_info: Any, knowledge_base: dict[str, str] | None = None) -> AssemblyTemplate | None:
        """
        自动装配热点 - 类似 JIT 编译热点方法

        Args:
            hotspot_info: 热点信息
            knowledge_base: 知识库

        Returns:
            装配模板
        """
        from harnessgenj.memory.hotspot import HotspotInfo

        if not isinstance(hotspot_info, HotspotInfo):
            return None

        if not hotspot_info.threshold_reached:
            return None

        # 检查缓存
        cached = self._template_cache.get(hotspot_info.name)
        if cached:
            cached.usage_count += 1
            cached.last_used_time = time.time()
            self._stats["cache_hits"] += 1
            return cached

        self._stats["cache_misses"] += 1

        # 根据策略装配
        strategy = hotspot_info.suggested_strategy

        if strategy == "inline":
            template = self._create_inline_template(hotspot_info, knowledge_base)
        elif strategy == "osr":
            template = self._create_osr_template(hotspot_info)
        else:
            template = self._create_cache_template(hotspot_info)

        if template:
            self._template_cache[template.name] = template
            self._stats["total_assemblies"] += 1

            # 维护缓存大小
            self._maintain_cache()

        return template

    def _create_inline_template(
        self,
        hotspot_info: Any,
        knowledge_base: dict[str, str] | None = None,
    ) -> AssemblyTemplate:
        """
        创建内联模板 - 类似 JIT 方法内联

        方法内联:
        - 将热点方法的代码直接嵌入调用处
        - 避免方法调用开销
        - 为后续优化提供基础

        Agent 知识内联:
        - 将高频知识内容嵌入执行流程
        - 减少知识查找开销
        - 提高执行效率
        """
        import uuid

        template = AssemblyTemplate(
            template_id=str(uuid.uuid4()),
            name=hotspot_info.name,
            category=hotspot_info.counter.name if hotspot_info.counter else "unknown",
            strategy="inline",
        )

        # 根据类别进行内联
        category = self._determine_category(hotspot_info.name)

        if category == "knowledge" and knowledge_base:
            # 知识内联
            knowledge_content = knowledge_base.get(hotspot_info.name, "")
            if len(knowledge_content) <= self.max_inline_size:
                template.inlined_knowledge.append(knowledge_content)
                self._stats["inlined_knowledge_count"] += 1

        elif category == "tool":
            # 工具内联 - 预加载工具配置
            template.inlined_tools.append(hotspot_info.name)
            self._stats["inlined_tools_count"] += 1

        # 创建执行模板
        template.execution_template = self._build_execution_template(hotspot_info, template)

        return template

    def _create_osr_template(self, hotspot_info: Any) -> AssemblyTemplate:
        """
        创建 OSR 模板 - 类似 JIT On-Stack Replacement

        OSR 编译:
        - 在循环执行过程中替换为优化代码
        - 不中断执行

        Agent OSR:
        - 在重复执行过程中切换到优化模板
        - 动态装配执行路径
        """
        import uuid

        template = AssemblyTemplate(
            template_id=str(uuid.uuid4()),
            name=f"{hotspot_info.name}_osr",
            category="pattern",
            strategy="osr",
        )

        # OSR 模板专注于重复执行优化
        template.execution_template = f"optimized_loop_{hotspot_info.name}"

        return template

    def _create_cache_template(self, hotspot_info: Any) -> AssemblyTemplate:
        """
        创建缓存模板 - 类似 JIT Code Cache

        将热点内容缓存，后续直接使用
        """
        import uuid

        template = AssemblyTemplate(
            template_id=str(uuid.uuid4()),
            name=f"{hotspot_info.name}_cached",
            category=self._determine_category(hotspot_info.name),
            strategy="cache",
        )

        return template

    def _build_execution_template(self, hotspot_info: Any, template: AssemblyTemplate) -> str:
        """
        构建执行模板 - 类似 JIT 生成的本地代码

        将内联内容组合成执行模板
        """
        parts = []

        if template.inlined_knowledge:
            parts.append(f"KNOWledge_INLINE: {template.inlined_knowledge[0][:100]}")

        if template.inlined_tools:
            parts.append(f"TOOLS_INLINE: {','.join(template.inlined_tools)}")

        return "\n".join(parts) if parts else f"TEMPLATE_{hotspot_info.name}"

    def _determine_category(self, name: str) -> str:
        """判断热点类别"""
        if "tool" in name.lower() or "search" in name.lower() or "execute" in name.lower():
            return "tool"
        if "knowledge" in name.lower() or "kb" in name.lower():
            return "knowledge"
        return "pattern"

    def _maintain_cache(self) -> None:
        """
        维护缓存大小 - 类似 JIT Code Cache 管理

        当缓存超过限制时，清除最少使用的模板
        """
        if len(self._template_cache) <= self.cache_size:
            return

        # 按使用次数排序，清除最少使用的
        sorted_templates = sorted(
            self._template_cache.values(),
            key=lambda t: t.usage_count,
        )

        # 清除底部 20%
        remove_count = int(len(self._template_cache) * 0.2)
        for template in sorted_templates[:remove_count]:
            self._template_cache.pop(template.name, None)

    def perform_escape_analysis(self, context_name: str, dependencies: list[str] | None = None) -> EscapeAnalysisResult:
        """
        逃逸分析 - 类似 JIT 逃逸分析

        分析上下文/知识的作用范围，判断是否可内联

        Args:
            context_name: 分析对象名称
            dependencies: 依赖项列表

        Returns:
            EscapeAnalysisResult: 分析结果
        """
        dependencies = dependencies or []

        # 简化逃逸分析逻辑
        if len(dependencies) == 0:
            # 无依赖，不逃逸
            return EscapeAnalysisResult(
                name=context_name,
                escape_level="no_escape",
                can_inline=True,
                can_stack_allocate=True,
                dependencies=dependencies,
            )

        if len(dependencies) <= 2:
            # 少量依赖，参数逃逸
            return EscapeAnalysisResult(
                name=context_name,
                escape_level="arg_escape",
                can_inline=True,
                can_stack_allocate=False,
                dependencies=dependencies,
            )

        # 多依赖，全局逃逸
        return EscapeAnalysisResult(
            name=context_name,
            escape_level="global_escape",
            can_inline=False,
            can_stack_allocate=False,
            dependencies=dependencies,
        )

    def get_template(self, name: str) -> AssemblyTemplate | None:
        """获取装配模板"""
        return self._template_cache.get(name)

    def apply_template(self, template_name: str) -> AssemblyTemplate | None:
        """
        应用装配模板 - 类似 JIT 执行编译代码

        Args:
            template_name: 模板名称

        Returns:
            应用的模板
        """
        template = self.get_template(template_name)
        if template:
            template.usage_count += 1
            template.last_used_time = time.time()

            # 更新加速因子
            if template.original_execution_time > 0:
                actual_speedup = template.original_execution_time / max(template.optimized_execution_time, 0.001)
                template.speedup_factor = actual_speedup

            return template
        return None

    def eliminate_dead_content(self, threshold: int = 5) -> list[str]:
        """
        死代码消除 - 类似 JIT 死代码消除

        清除使用次数低于阈值的内容

        Args:
            threshold: 使用次数阈值

        Returns:
            清除的内容名称列表
        """
        eliminated = []
        for name, template in list(self._template_cache.items()):
            if template.usage_count < threshold:
                self._template_cache.pop(name)
                eliminated.append(name)
        return eliminated

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        avg_speedup = 0.0
        if self._template_cache:
            speedups = [t.speedup_factor for t in self._template_cache.values() if t.speedup_factor > 1.0]
            if speedups:
                avg_speedup = sum(speedups) / len(speedups)

        return {
            **self._stats,
            "avg_speedup": avg_speedup,
            "cache_size": len(self._template_cache),
            "max_cache_size": self.cache_size,
        }

    def clear_cache(self) -> int:
        """清空缓存"""
        count = len(self._template_cache)
        self._template_cache.clear()
        return count