"""
Context Assembler - 上下文自动装配器

JVM 风格的分代上下文注入机制，确保每次调度大模型时自动注入核心记忆。

核心设计:
====================

1. Permanent 区（永久记忆，每次必注入）
   - 项目目标和要求
   - 智能体定义和职责
   - 调度策略和流程规范
   - 核心代码约定

2. Survivor 区（活跃记忆，当前任务上下文）
   - 当前执行的任务信息
   - 相关需求文档
   - 相关设计决策
   - 进度状态

3. Old 区（历史记忆，按需加载摘要）
   - 已完成的需求（压缩）
   - 历史设计文档（摘要）
   - 项目里程碑

4. Eden 区（临时记忆，可丢弃）
   - 最近会话消息
   - 临时讨论内容
   - 可压缩的日志

上下文注入流程:
====================

每次调度大模型前:
1. 加载 Permanent 区完整内容（核心规范）
2. 加载 Survivor 区当前任务上下文
3. 按需加载 Old 区摘要（如果相关）
4. 可选加载 Eden 区最近消息

使用示例:
====================

    assembler = ContextAssembler(harness)

    # 为开发者角色装配上下文
    context = assembler.assemble_for_role("developer")

    # 为特定任务装配上下文
    context = assembler.assemble_for_task("TASK-123")

    # 获取最小必要上下文（Token 优化）
    context = assembler.assemble_minimal()
"""

from typing import Any
from pydantic import BaseModel, Field
from enum import Enum
import time


class ContextPriority(Enum):
    """上下文优先级"""

    CRITICAL = 100    # 必须注入，不可省略
    HIGH = 80         # 重要，优先注入
    MEDIUM = 50       # 按需注入
    LOW = 20          # 可选，空间允许时注入


class ContextSection(BaseModel):
    """上下文章节"""

    name: str = Field(..., description="章节名称")
    content: str = Field(..., description="章节内容")
    priority: ContextPriority = Field(default=ContextPriority.MEDIUM, description="优先级")
    region: str = Field(default="survivor", description="所属区域: permanent/survivor/old/eden")
    token_estimate: int = Field(default=0, description="预估Token数")
    compressible: bool = Field(default=True, description="是否可压缩")
    tags: list[str] = Field(default_factory=list, description="标签")


class PermanentKnowledge(BaseModel):
    """
    永久知识 - Permanent 区核心内容

    这些内容在每次对话时都必须注入，永不省略。
    """

    # 项目核心信息
    project_name: str = Field(default="", description="项目名称")
    project_goal: str = Field(default="", description="项目目标")
    tech_stack: str = Field(default="", description="技术栈")

    # 智能体定义
    agent_definitions: dict[str, dict[str, Any]] = Field(default_factory=dict, description="智能体定义")

    # 调度策略
    dispatch_strategy: str = Field(default="", description="智能体调度策略")

    # 工作流程规范
    workflow_rules: list[str] = Field(default_factory=list, description="工作流程规则")

    # 核心代码约定
    coding_conventions: list[str] = Field(default_factory=list, description="代码约定")

    def to_context(self) -> ContextSection:
        """转换为上下文章节"""
        content_parts = []

        # 项目信息
        if self.project_name:
            content_parts.append(f"## 项目信息\n- 名称: {self.project_name}")
        if self.project_goal:
            content_parts.append(f"- 目标: {self.project_goal}")
        if self.tech_stack:
            content_parts.append(f"- 技术栈: {self.tech_stack}")

        # 智能体定义
        if self.agent_definitions:
            content_parts.append("\n## 智能体定义")
            for agent_name, agent_info in self.agent_definitions.items():
                content_parts.append(f"- **{agent_name}**: {agent_info.get('role', '未定义')}")
                if agent_info.get('skills'):
                    content_parts.append(f"  - 技能: {', '.join(agent_info['skills'])}")

        # 调度策略
        if self.dispatch_strategy:
            content_parts.append(f"\n## 调度策略\n{self.dispatch_strategy}")

        # 工作流程规则
        if self.workflow_rules:
            content_parts.append("\n## 工作流程规则")
            for rule in self.workflow_rules:
                content_parts.append(f"- {rule}")

        # 代码约定
        if self.coding_conventions:
            content_parts.append("\n## 核心约定")
            for conv in self.coding_conventions:
                content_parts.append(f"- {conv}")

        return ContextSection(
            name="permanent_knowledge",
            content="\n".join(content_parts),
            priority=ContextPriority.CRITICAL,
            region="permanent",
            compressible=False,
        )


class ActiveTaskContext(BaseModel):
    """
    活跃任务上下文 - Survivor 区核心内容

    当前正在执行的任务相关信息。
    """

    task_id: str = Field(default="", description="任务ID")
    task_type: str = Field(default="", description="任务类型: feature/bug/task")
    task_desc: str = Field(default="", description="任务描述")
    priority: str = Field(default="", description="优先级: P0/P1/P2")
    assignee: str = Field(default="", description="负责人")
    status: str = Field(default="", description="状态")

    # 相关需求
    related_requirements: str = Field(default="", description="相关需求文档摘要")

    # 相关设计
    related_design: str = Field(default="", description="相关设计文档摘要")

    # 进度信息
    progress_notes: list[str] = Field(default_factory=list, description="进度记录")

    def to_context(self) -> ContextSection:
        """转换为上下文章节"""
        content_parts = [f"## 当前任务 [{self.priority}]"]

        if self.task_id:
            content_parts.append(f"- 任务ID: {self.task_id}")
        if self.task_type:
            content_parts.append(f"- 类型: {self.task_type}")
        if self.task_desc:
            content_parts.append(f"- 描述: {self.task_desc}")
        if self.assignee:
            content_parts.append(f"- 负责人: {self.assignee}")
        if self.status:
            content_parts.append(f"- 状态: {self.status}")

        if self.related_requirements:
            content_parts.append(f"\n### 相关需求\n{self.related_requirements[:500]}")

        if self.related_design:
            content_parts.append(f"\n### 相关设计\n{self.related_design[:500]}")

        if self.progress_notes:
            content_parts.append("\n### 进度记录")
            for note in self.progress_notes[-5:]:
                content_parts.append(f"- {note}")

        return ContextSection(
            name="active_task",
            content="\n".join(content_parts),
            priority=ContextPriority.HIGH,
            region="survivor",
            compressible=True,
        )


class ContextAssembler:
    """
    上下文装配器 - 自动注入核心记忆

    核心功能:
    1. 从各区域提取关键信息
    2. 按优先级组装上下文
    3. 支持压缩和摘要
    4. 控制 Token 消耗

    JVM 风格注入策略:
    - Permanent: 每次必注入，完整内容
    - Survivor: 每次注入，可压缩
    - Old: 按需注入，摘要形式
    - Eden: 可选注入，最近 N 条
    """

    # 默认智能体定义
    DEFAULT_AGENTS = {
        "project_manager": {
            "role": "项目经理 - 中央协调者",
            "skills": ["任务分配", "进度追踪", "文档维护", "状态报告"],
            "dispatch_trigger": "用户请求接收、任务协调",
        },
        "product_manager": {
            "role": "产品经理 - 需求管理",
            "skills": ["需求分析", "用户故事", "验收标准", "优先级排序"],
            "dispatch_trigger": "需求分析、功能设计",
        },
        "architect": {
            "role": "架构师 - 技术设计",
            "skills": ["系统设计", "技术选型", "架构评审", "设计模式"],
            "dispatch_trigger": "架构设计、技术决策",
        },
        "developer": {
            "role": "开发者 - 功能实现",
            "skills": ["编码实现", "Bug修复", "代码重构", "代码审查"],
            "dispatch_trigger": "功能开发、Bug修复",
        },
        "tester": {
            "role": "测试员 - 质量保证",
            "skills": ["测试编写", "测试执行", "Bug报告", "覆盖率分析"],
            "dispatch_trigger": "测试验证、质量检查",
        },
        "doc_writer": {
            "role": "文档管理员 - 文档维护",
            "skills": ["技术文档", "API文档", "用户手册", "知识库维护"],
            "dispatch_trigger": "文档编写、知识记录",
        },
    }

    # 默认调度策略
    DEFAULT_DISPATCH_STRATEGY = """
用户请求 → 项目经理接收 → 智能分配 → 执行 → 确认完成

分配规则:
- feature 需求 → P1 优先级 → developer 执行
- bug 报告 → P0 优先级 → developer 执行
- task 任务 → P2 优先级 → developer 执行

工作流程:
需求分析(PM) → 架构设计(Arch) → 开发实现(Dev) → 测试验证(Tester) → 文档编写(Doc)
"""

    # 默认工作流程规则
    DEFAULT_WORKFLOW_RULES = [
        "所有用户请求必须通过 receive_request() 接收",
        "开发完成必须通过 complete_task() 确认",
        "每个角色只访问最小必要信息（渐进式披露）",
        "所有重要操作自动持久化到 .harnessgenj/ 目录",
        "项目经理是中央协调者，维护所有文档",
    ]

    # 核心方法提示（每次必注入）
    CORE_METHODS_PROMPT = """
## HarnessGenJ 核心方法（AI 必须使用）

| 用户意图 | 调用方法 |
|----------|----------|
| 新需求/功能 | `harness.receive_request("描述", request_type="feature")` |
| Bug报告 | `harness.receive_request("描述", request_type="bug")` |
| 开发功能 | `harness.develop("功能描述")` |
| 修复Bug | `harness.fix_bug("Bug描述")` |
| 查看状态 | `harness.get_status()` |
| 记录内容 | `harness.record("内容")` |
| 获取上下文 | `harness.get_context_prompt()` |
"""

    def __init__(self, harness: Any) -> None:
        """
        初始化上下文装配器

        Args:
            harness: Harness 实例
        """
        self.harness = harness
        self._permanent_knowledge: PermanentKnowledge | None = None
        self._active_task: ActiveTaskContext | None = None
        self._last_assemble_time: float = 0

    def get_permanent_knowledge(self) -> PermanentKnowledge:
        """
        获取永久知识（从 AGENTS.md 或默认值）

        Returns:
            PermanentKnowledge 实例
        """
        if self._permanent_knowledge:
            return self._permanent_knowledge

        # 尝试从 AGENTS.md 加载
        knowledge = PermanentKnowledge(
            project_name=self.harness.project_name,
            project_goal="",
            tech_stack="",
            agent_definitions=self.DEFAULT_AGENTS.copy(),
            dispatch_strategy=self.DEFAULT_DISPATCH_STRATEGY,
            workflow_rules=self.DEFAULT_WORKFLOW_RULES.copy(),
            coding_conventions=[],
        )

        # 从项目状态获取更多信息
        if self.harness.memory:
            info = self.harness.memory.get_project_info()
            knowledge.project_name = info.get("name", self.harness.project_name)
            knowledge.tech_stack = info.get("tech_stack", "")

        # 从 AGENTS.md 加载（如果存在）
        if self.harness._agents_knowledge and self.harness._agents_knowledge.is_initialized():
            full_knowledge = self.harness._agents_knowledge.get_full_knowledge()
            # 解析关键信息
            knowledge.project_goal = self._extract_goal(full_knowledge)
            knowledge.coding_conventions = self._extract_conventions(full_knowledge)

        self._permanent_knowledge = knowledge
        return knowledge

    def get_active_task(self) -> ActiveTaskContext | None:
        """
        获取活跃任务上下文

        Returns:
            ActiveTaskContext 实例或 None
        """
        if not self.harness.memory:
            return None

        task_info = self.harness.memory.get_current_task()
        if not task_info.get("task_id"):
            return None

        # 构建活跃任务上下文
        active_task = ActiveTaskContext(
            task_id=task_info.get("task_id", ""),
            task_type="feature",  # 默认
            task_desc=task_info.get("task_desc", ""),
            status=task_info.get("status", ""),
        )

        # 获取相关文档摘要
        from harnessgenj.memory.manager import DocumentType

        req_doc = self.harness.memory.get_document_summary(
            DocumentType.REQUIREMENTS
        )
        if req_doc:
            active_task.related_requirements = req_doc[:500]

        design_doc = self.harness.memory.get_document_summary(
            DocumentType.DESIGN
        )
        if design_doc:
            active_task.related_design = design_doc[:500]

        self._active_task = active_task
        return active_task

    def assemble_for_role(self, role_type: str, max_tokens: int = 4000) -> str:
        """
        为特定角色装配上下文

        Args:
            role_type: 角色类型
            max_tokens: 最大 Token 数

        Returns:
            装配好的上下文字符串
        """
        sections: list[ContextSection] = []
        current_tokens = 0

        # 1. 永久知识（必须注入）
        permanent = self.get_permanent_knowledge().to_context()
        sections.append(permanent)
        current_tokens += self._estimate_tokens(permanent.content)

        # 2. 核心方法提示（必须注入）
        methods_section = ContextSection(
            name="core_methods",
            content=self.CORE_METHODS_PROMPT,
            priority=ContextPriority.CRITICAL,
            region="permanent",
            compressible=False,
        )
        sections.append(methods_section)
        current_tokens += self._estimate_tokens(methods_section.content)

        # 3. 活跃任务（如果有）
        active_task = self.get_active_task()
        if active_task:
            task_section = active_task.to_context()
            if current_tokens + self._estimate_tokens(task_section.content) <= max_tokens:
                sections.append(task_section)
                current_tokens += self._estimate_tokens(task_section.content)

        # 4. 项目状态摘要
        if self.harness.memory and current_tokens < max_tokens * 0.8:
            stats = self.harness.memory.get_stats()["stats"]
            stats_section = ContextSection(
                name="project_stats",
                content=f"## 项目进度\n- 功能: {stats['features_completed']}/{stats['features_total']}\n- 进度: {stats['progress']}%",
                priority=ContextPriority.MEDIUM,
                region="survivor",
            )
            if current_tokens + self._estimate_tokens(stats_section.content) <= max_tokens:
                sections.append(stats_section)

        # 按优先级排序并组装
        sections.sort(key=lambda s: s.priority.value, reverse=True)

        return self._assemble_sections(sections)

    def assemble_for_task(self, task_id: str, max_tokens: int = 4000) -> str:
        """
        为特定任务装配上下文

        Args:
            task_id: 任务ID
            max_tokens: 最大 Token 数

        Returns:
            装配好的上下文字符串
        """
        # 基础上下文
        base_context = self.assemble_for_role("developer", max_tokens=max_tokens - 500)

        # 添加任务特定信息
        task_context = f"\n\n## 任务详情\n- 任务ID: {task_id}\n"

        return base_context + task_context

    def assemble_minimal(self) -> str:
        """
        装配最小必要上下文

        只包含永久知识和核心方法，用于快速启动。

        Returns:
            最小上下文字符串
        """
        sections: list[ContextSection] = []

        # 永久知识
        permanent = self.get_permanent_knowledge().to_context()
        sections.append(permanent)

        # 核心方法
        methods_section = ContextSection(
            name="core_methods",
            content=self.CORE_METHODS_PROMPT,
            priority=ContextPriority.CRITICAL,
            region="permanent",
        )
        sections.append(methods_section)

        return self._assemble_sections(sections)

    def assemble_full(self, max_tokens: int = 8000) -> str:
        """
        装配完整上下文（用于项目经理）

        Args:
            max_tokens: 最大 Token 数

        Returns:
            完整上下文字符串
        """
        sections: list[ContextSection] = []
        current_tokens = 0

        # 1. 永久知识
        permanent = self.get_permanent_knowledge().to_context()
        sections.append(permanent)
        current_tokens += self._estimate_tokens(permanent.content)

        # 2. 核心方法
        methods_section = ContextSection(
            name="core_methods",
            content=self.CORE_METHODS_PROMPT,
            priority=ContextPriority.CRITICAL,
            region="permanent",
        )
        sections.append(methods_section)
        current_tokens += self._estimate_tokens(methods_section.content)

        # 3. 活跃任务
        active_task = self.get_active_task()
        if active_task:
            task_section = active_task.to_context()
            sections.append(task_section)
            current_tokens += self._estimate_tokens(task_section.content)

        # 4. 项目状态
        if self.harness.memory:
            stats = self.harness.memory.get_stats()["stats"]
            stats_content = f"""## 项目状态
- 功能总数: {stats['features_total']}
- 已完成: {stats['features_completed']}
- Bug总数: {stats['bugs_total']}
- 已修复: {stats['bugs_fixed']}
- 进度: {stats['progress']}%
"""
            sections.append(ContextSection(
                name="project_status",
                content=stats_content,
                priority=ContextPriority.HIGH,
                region="survivor",
            ))

        # 5. 所有文档摘要（如果有空间）
        if self.harness.memory and current_tokens < max_tokens * 0.7:
            from harnessgenj.memory.manager import DocumentType
            for doc_type in [DocumentType.REQUIREMENTS, DocumentType.PROGRESS]:
                summary = self.harness.memory.get_document_summary(doc_type)
                if summary:
                    doc_section = ContextSection(
                        name=f"{doc_type}_summary",
                        content=f"## {doc_type} 摘要\n{summary[:300]}",
                        priority=ContextPriority.LOW,
                        region="old",
                        compressible=True,
                    )
                    if current_tokens + self._estimate_tokens(doc_section.content) <= max_tokens:
                        sections.append(doc_section)
                        current_tokens += self._estimate_tokens(doc_section.content)

        return self._assemble_sections(sections)

    def _assemble_sections(self, sections: list[ContextSection]) -> str:
        """组装上下文章节"""
        parts = ["# HarnessGenJ 上下文提示\n"]

        for section in sections:
            if section.content:
                parts.append(section.content)
                parts.append("\n")

        return "\n".join(parts)

    def _estimate_tokens(self, content: str) -> int:
        """
        估算 Token 数（增强版）

        使用更精确的多语言估算方法:
        - 英文: 约 1 token = 4 字符
        - 中文: 约 1 token = 1.5 字符
        - 日文/韩文: 约 1 token = 2 字符
        - 代码: 约 1 token = 3 字符
        - 标点符号: 约 1 token = 1 字符

        Args:
            content: 要估算的内容

        Returns:
            估算的 Token 数
        """
        import re

        if not content:
            return 0

        total_tokens = 0

        # 分类统计字符
        # 中文字符 (CJK 统一汉字)
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
        # 日文字符 (平假名 + 片假名)
        japanese_chars = len(re.findall(r'[\u3040-\u309f\u30a0-\u30ff]', content))
        # 韩文字符
        korean_chars = len(re.findall(r'[\uac00-\ud7af]', content))
        # 数字
        digits = len(re.findall(r'[0-9]', content))
        # 标点符号和特殊字符
        punctuation = len(re.findall(r'[^\w\s\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]', content))
        # 剩余字符（主要是英文和代码）
        other_chars = len(content) - chinese_chars - japanese_chars - korean_chars - digits - punctuation

        # 计算各部分的 Token 数
        # 中文: 约 1.5 字符/token
        total_tokens += int(chinese_chars / 1.5)
        # 日文: 约 2 字符/token
        total_tokens += int(japanese_chars / 2)
        # 韩文: 约 2 字符/token
        total_tokens += int(korean_chars / 2)
        # 数字: 约 0.5 字符/token (数字通常与其他字符组合)
        total_tokens += int(digits / 2)
        # 标点符号: 约 1 字符/token
        total_tokens += punctuation
        # 英文/代码: 约 4 字符/token
        total_tokens += int(other_chars / 4)

        # 确保至少返回 1
        return max(total_tokens, 1) if content else 0

    def _extract_goal(self, content: str) -> str:
        """从内容中提取项目目标"""
        import re
        # 查找目标相关的行
        for line in content.split('\n'):
            if '目标' in line or 'goal' in line.lower():
                # 提取冒号后的内容
                match = re.search(r'[:：]\s*(.+)', line)
                if match:
                    return match.group(1).strip()
        return ""

    def _extract_conventions(self, content: str) -> list[str]:
        """从内容中提取代码约定"""
        conventions = []
        in_convention_section = False
        for line in content.split('\n'):
            if '约定' in line or 'convention' in line.lower():
                in_convention_section = True
                continue
            if in_convention_section and line.startswith('-'):
                conventions.append(line[1:].strip())
            elif in_convention_section and line.startswith('#'):
                break
        return conventions

    def clear_cache(self) -> None:
        """清除缓存"""
        self._permanent_knowledge = None
        self._active_task = None
        self._last_assemble_time = 0

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        permanent = self.get_permanent_knowledge()
        active_task = self.get_active_task()

        return {
            "permanent_loaded": self._permanent_knowledge is not None,
            "active_task_exists": active_task is not None,
            "active_task_id": active_task.task_id if active_task else None,
            "last_assemble_time": self._last_assemble_time,
        }


def create_context_assembler(harness: Any) -> ContextAssembler:
    """创建上下文装配器"""
    return ContextAssembler(harness)