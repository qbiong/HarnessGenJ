"""
Stage Memory Mapping - 工作流阶段与记忆管理的映射

定义每个工作流阶段的产出物如何存储到 MemoryManager 的各个区域。

核心原则：
1. 不修改现有 MemoryManager，只使用其公开 API
2. 明确定义每个阶段的输入来源和输出目标
3. 自动管理质量分数更新

记忆区域映射：
- Permanent区: 项目核心知识（通过 store_knowledge）
- Old区: 文档资产（通过 store_document）
- Survivor区: 当前任务（通过 store_task）
- Eden区: 会话消息（通过 store_message）

质量集成：
- 对抗审查结果通过 update_quality 更新条目质量字段
"""

from typing import Any
from pydantic import BaseModel, Field
from enum import Enum


class MemoryRegion(Enum):
    """目标记忆区域"""

    PERMANENT = "permanent"   # 核心知识
    OLD = "old"               # 文档资产
    SURVIVOR = "survivor"     # 当前任务
    EDEN = "eden"             # 会话消息


class OutputAction(Enum):
    """输出动作类型"""

    STORE_DOCUMENT = "store_document"       # 存储文档
    STORE_KNOWLEDGE = "store_knowledge"     # 存储知识
    STORE_TASK = "store_task"               # 存储任务
    UPDATE_QUALITY = "update_quality"       # 更新质量分数
    STORE_MESSAGE = "store_message"         # 存储消息
    STORE_ARTIFACT = "store_artifact"       # 存储产出物（通用）


class InputSource(BaseModel):
    """输入来源定义"""

    source_type: str = Field(..., description="来源类型: document/knowledge/task/message")
    key: str = Field(..., description="键名")
    required: bool = Field(default=True, description="是否必需")
    default: Any = Field(default=None, description="默认值")


class OutputTarget(BaseModel):
    """输出目标定义"""

    action: OutputAction = Field(..., description="输出动作")
    region: MemoryRegion = Field(default=MemoryRegion.OLD, description="目标区域")
    key: str = Field(..., description="存储键名")
    source_key: str | None = Field(default=None, description="来源键名（从阶段输出的哪个键取值，默认等于key）")
    doc_type: str | None = Field(default=None, description="文档类型（用于store_document）")
    importance: int = Field(default=70, description="重要性评分")
    generator_role: str | None = Field(default=None, description="生成者角色")
    update_quality_target: str | None = Field(default=None, description="更新质量的目标键名")


class StageMemoryMapping(BaseModel):
    """
    阶段记忆映射 - 定义单个阶段的输入输出映射

    示例：
    ```python
    mapping = StageMemoryMapping(
        stage_name="requirements",
        inputs=[
            InputSource(source_type="document", key="requirements"),
        ],
        outputs=[
            OutputTarget(
                action=OutputAction.STORE_DOCUMENT,
                region=MemoryRegion.OLD,
                key="requirements",
                doc_type="requirements",
                importance=80,
            ),
        ],
    )
    ```
    """

    stage_name: str = Field(..., description="阶段名称")
    inputs: list[InputSource] = Field(default_factory=list, description="输入来源")
    outputs: list[OutputTarget] = Field(default_factory=list, description="输出目标")
    description: str = Field(default="", description="映射描述")


# ==================== 标准工作流记忆映射定义 ====================

# 开发流水线的记忆映射
DEVELOPMENT_PIPELINE_MAPPINGS: dict[str, StageMemoryMapping] = {
    "requirements": StageMemoryMapping(
        stage_name="requirements",
        description="需求分析阶段 - 读取用户请求，产出需求文档",
        inputs=[
            InputSource(source_type="task", key="current_task", required=False),
            InputSource(source_type="knowledge", key="project_name", required=False),
        ],
        outputs=[
            OutputTarget(
                action=OutputAction.STORE_DOCUMENT,
                region=MemoryRegion.OLD,
                key="requirements",
                doc_type="requirements",
                importance=80,
                generator_role="product_manager",
            ),
            OutputTarget(
                action=OutputAction.STORE_KNOWLEDGE,
                region=MemoryRegion.PERMANENT,
                key="acceptance_criteria",
                importance=90,
            ),
        ],
    ),

    "design": StageMemoryMapping(
        stage_name="design",
        description="架构设计阶段 - 读取需求，产出设计文档",
        inputs=[
            InputSource(source_type="document", key="requirements"),
            InputSource(source_type="knowledge", key="user_stories", required=False),
        ],
        outputs=[
            OutputTarget(
                action=OutputAction.STORE_DOCUMENT,
                region=MemoryRegion.OLD,
                key="design",
                source_key="design_doc",  # Pipeline outputs design_doc
                doc_type="design",
                importance=85,
                generator_role="architect",
            ),
            OutputTarget(
                action=OutputAction.STORE_KNOWLEDGE,
                region=MemoryRegion.PERMANENT,
                key="tech_stack",
                source_key="tech_decisions",  # Pipeline outputs tech_decisions
                importance=95,
            ),
        ],
    ),

    "development": StageMemoryMapping(
        stage_name="development",
        description="代码开发阶段 - 读取设计，产出代码",
        inputs=[
            InputSource(source_type="document", key="design"),
            InputSource(source_type="document", key="requirements", required=False),
        ],
        outputs=[
            OutputTarget(
                action=OutputAction.STORE_DOCUMENT,
                region=MemoryRegion.OLD,
                key="development",
                source_key="code",  # Pipeline outputs code
                doc_type="development",
                importance=75,
                generator_role="developer",
            ),
            OutputTarget(
                action=OutputAction.STORE_KNOWLEDGE,
                region=MemoryRegion.OLD,
                key="code_snapshot",
                source_key="code",  # Pipeline outputs code
                importance=80,
            ),
        ],
    ),

    "adversarial_review": StageMemoryMapping(
        stage_name="adversarial_review",
        description="对抗审查阶段 - 读取代码，产出审查结果和质量分数",
        inputs=[
            InputSource(source_type="knowledge", key="code_snapshot", required=False),
            InputSource(source_type="document", key="development", required=False),
        ],
        outputs=[
            OutputTarget(
                action=OutputAction.UPDATE_QUALITY,
                region=MemoryRegion.OLD,
                key="review_result",
                update_quality_target="code_snapshot",
            ),
            OutputTarget(
                action=OutputAction.STORE_KNOWLEDGE,
                region=MemoryRegion.OLD,
                key="last_review_issues",
                source_key="issues_found",  # Pipeline outputs issues_found
                importance=70,
            ),
        ],
    ),

    "fix_and_optimize": StageMemoryMapping(
        stage_name="fix_and_optimize",
        description="修复优化阶段 - 读取审查结果，产出优化代码",
        inputs=[
            InputSource(source_type="knowledge", key="code_snapshot"),
            InputSource(source_type="knowledge", key="last_review_issues", required=False),
        ],
        outputs=[
            OutputTarget(
                action=OutputAction.STORE_DOCUMENT,
                region=MemoryRegion.OLD,
                key="development",
                source_key="optimized_code",  # Pipeline outputs optimized_code
                doc_type="development",
                importance=80,
                generator_role="developer",
            ),
        ],
    ),

    "unit_test": StageMemoryMapping(
        stage_name="unit_test",
        description="单元测试阶段 - 读取代码，产出测试报告",
        inputs=[
            InputSource(source_type="document", key="development"),
            InputSource(source_type="document", key="requirements", required=False),
            InputSource(source_type="knowledge", key="acceptance_criteria", required=False),
        ],
        outputs=[
            OutputTarget(
                action=OutputAction.STORE_DOCUMENT,
                region=MemoryRegion.OLD,
                key="testing",
                source_key="unit_tests",  # Pipeline outputs unit_tests
                doc_type="testing",
                importance=75,
                generator_role="tester",
            ),
            OutputTarget(
                action=OutputAction.STORE_KNOWLEDGE,
                region=MemoryRegion.OLD,
                key="coverage_report",
                importance=70,
            ),
        ],
    ),

    "integration_test": StageMemoryMapping(
        stage_name="integration_test",
        description="集成测试阶段 - 读取代码和测试，产出集成报告",
        inputs=[
            InputSource(source_type="document", key="development"),
            InputSource(source_type="knowledge", key="coverage_report", required=False),
        ],
        outputs=[
            OutputTarget(
                action=OutputAction.STORE_DOCUMENT,
                region=MemoryRegion.OLD,
                key="testing",
                source_key="integration_results",  # Pipeline outputs integration_results
                doc_type="testing",
                importance=80,
                generator_role="tester",
            ),
        ],
    ),

    "acceptance": StageMemoryMapping(
        stage_name="acceptance",
        description="验收阶段 - 读取所有产出，产出验收结果",
        inputs=[
            InputSource(source_type="document", key="testing"),
            InputSource(source_type="knowledge", key="coverage_report", required=False),
            InputSource(source_type="knowledge", key="quality_score", required=False),
        ],
        outputs=[
            OutputTarget(
                action=OutputAction.STORE_DOCUMENT,
                region=MemoryRegion.OLD,
                key="progress",
                source_key="acceptance_result",  # Pipeline outputs acceptance_result
                doc_type="progress",
                importance=85,
                generator_role="project_manager",
            ),
            OutputTarget(
                action=OutputAction.STORE_TASK,
                region=MemoryRegion.SURVIVOR,
                key="completion_record",
                source_key="release_ready",  # Pipeline outputs release_ready
                importance=90,
            ),
        ],
    ),
}

# Bug修复流水线的记忆映射
BUGFIX_PIPELINE_MAPPINGS: dict[str, StageMemoryMapping] = {
    "analysis": StageMemoryMapping(
        stage_name="analysis",
        description="问题分析阶段 - 读取Bug报告，产出根因分析",
        inputs=[
            InputSource(source_type="task", key="current_task"),
        ],
        outputs=[
            OutputTarget(
                action=OutputAction.STORE_KNOWLEDGE,
                region=MemoryRegion.OLD,
                key="root_cause",
                importance=75,
            ),
            OutputTarget(
                action=OutputAction.STORE_DOCUMENT,
                region=MemoryRegion.OLD,
                key="development",
                source_key="affected_modules",  # Pipeline outputs affected_modules
                doc_type="development",
                importance=70,
                generator_role="developer",
            ),
        ],
    ),

    "fix_design": StageMemoryMapping(
        stage_name="fix_design",
        description="修复设计阶段 - 读取根因，产出修复方案",
        inputs=[
            InputSource(source_type="knowledge", key="root_cause"),
        ],
        outputs=[
            OutputTarget(
                action=OutputAction.STORE_KNOWLEDGE,
                region=MemoryRegion.OLD,
                key="fix_plan",
                source_key="fix_plan",  # Pipeline outputs fix_plan
                importance=80,
            ),
        ],
    ),

    "fix_implementation": StageMemoryMapping(
        stage_name="fix_implementation",
        description="修复实现阶段 - 读取方案，产出修复代码",
        inputs=[
            InputSource(source_type="knowledge", key="fix_plan"),
            InputSource(source_type="knowledge", key="root_cause"),
        ],
        outputs=[
            OutputTarget(
                action=OutputAction.STORE_DOCUMENT,
                region=MemoryRegion.OLD,
                key="development",
                source_key="fixed_code",  # Pipeline outputs fixed_code
                doc_type="development",
                importance=75,
                generator_role="developer",
            ),
            OutputTarget(
                action=OutputAction.STORE_KNOWLEDGE,
                region=MemoryRegion.OLD,
                key="code_snapshot",
                source_key="fixed_code",  # Pipeline outputs fixed_code
                importance=80,
            ),
        ],
    ),

    "adversarial_verification": StageMemoryMapping(
        stage_name="adversarial_verification",
        description="对抗验证阶段 - 读取修复代码，产出验证结果",
        inputs=[
            InputSource(source_type="knowledge", key="code_snapshot"),
        ],
        outputs=[
            OutputTarget(
                action=OutputAction.UPDATE_QUALITY,
                region=MemoryRegion.OLD,
                key="verification_result",
                update_quality_target="code_snapshot",
            ),
            OutputTarget(
                action=OutputAction.STORE_KNOWLEDGE,
                region=MemoryRegion.OLD,
                key="edge_cases",
                importance=70,
            ),
        ],
    ),

    "edge_fix": StageMemoryMapping(
        stage_name="edge_fix",
        description="边界修复阶段 - 读取边界情况，产出最终代码",
        inputs=[
            InputSource(source_type="knowledge", key="code_snapshot"),
            InputSource(source_type="knowledge", key="edge_cases", required=False),
        ],
        outputs=[
            OutputTarget(
                action=OutputAction.STORE_DOCUMENT,
                region=MemoryRegion.OLD,
                key="development",
                source_key="final_code",  # Pipeline outputs final_code
                doc_type="development",
                importance=80,
                generator_role="developer",
            ),
        ],
    ),

    "regression_test": StageMemoryMapping(
        stage_name="regression_test",
        description="回归测试阶段 - 读取最终代码，产出回归报告",
        inputs=[
            InputSource(source_type="document", key="development"),
        ],
        outputs=[
            OutputTarget(
                action=OutputAction.STORE_DOCUMENT,
                region=MemoryRegion.OLD,
                key="testing",
                source_key="regression_results",  # Pipeline outputs regression_results
                doc_type="testing",
                importance=75,
                generator_role="tester",
            ),
        ],
    ),

    "integration_verification": StageMemoryMapping(
        stage_name="integration_verification",
        description="集成验证阶段 - 读取回归结果，产出集成报告",
        inputs=[
            InputSource(source_type="document", key="development"),
        ],
        outputs=[
            OutputTarget(
                action=OutputAction.STORE_DOCUMENT,
                region=MemoryRegion.OLD,
                key="testing",
                source_key="integration_results",  # Pipeline outputs integration_results
                doc_type="testing",
                importance=80,
                generator_role="tester",
            ),
        ],
    ),

    "fix_completion": StageMemoryMapping(
        stage_name="fix_completion",
        description="修复完成阶段 - 产出完成记录和经验总结",
        inputs=[
            InputSource(source_type="document", key="testing"),
        ],
        outputs=[
            OutputTarget(
                action=OutputAction.STORE_DOCUMENT,
                region=MemoryRegion.OLD,
                key="progress",
                source_key="fix_complete",  # Pipeline outputs fix_complete
                doc_type="progress",
                importance=85,
                generator_role="project_manager",
            ),
            OutputTarget(
                action=OutputAction.STORE_KNOWLEDGE,
                region=MemoryRegion.PERMANENT,
                key="lessons_learned",
                importance=90,
            ),
        ],
    ),
}

# 意图识别流水线的记忆映射
INTENT_PIPELINE_MAPPINGS: dict[str, StageMemoryMapping] = {
    "receive_input": StageMemoryMapping(
        stage_name="receive_input",
        description="接收输入阶段 - 存储用户消息",
        inputs=[],
        outputs=[
            OutputTarget(
                action=OutputAction.STORE_MESSAGE,
                region=MemoryRegion.EDEN,
                key="user_message",
                source_key="raw_input",  # Pipeline outputs raw_input
                importance=50,
            ),
        ],
    ),

    "identify_intent": StageMemoryMapping(
        stage_name="identify_intent",
        description="意图识别阶段 - 产出意图结果",
        inputs=[
            InputSource(source_type="message", key="user_message", required=False),
        ],
        outputs=[
            OutputTarget(
                action=OutputAction.STORE_KNOWLEDGE,
                region=MemoryRegion.SURVIVOR,
                key="intent_result",
                importance=70,
            ),
        ],
    ),

    "extract_entities": StageMemoryMapping(
        stage_name="extract_entities",
        description="实体提取阶段 - 产出实体信息",
        inputs=[
            InputSource(source_type="knowledge", key="intent_result"),
        ],
        outputs=[
            OutputTarget(
                action=OutputAction.STORE_KNOWLEDGE,
                region=MemoryRegion.SURVIVOR,
                key="extracted_entities",
                source_key="feature_name",  # Pipeline outputs feature_name
                importance=65,
            ),
        ],
    ),

    "route_workflow": StageMemoryMapping(
        stage_name="route_workflow",
        description="工作流路由阶段 - 创建任务",
        inputs=[
            InputSource(source_type="knowledge", key="intent_result"),
            InputSource(source_type="knowledge", key="extracted_entities", required=False),
        ],
        outputs=[
            OutputTarget(
                action=OutputAction.STORE_TASK,
                region=MemoryRegion.SURVIVOR,
                key="routed_task",
                source_key="task_id",  # Pipeline outputs task_id
                importance=80,
            ),
        ],
    ),
}

# 问题咨询流水线的记忆映射
INQUIRY_PIPELINE_MAPPINGS: dict[str, StageMemoryMapping] = {
    "understand_question": StageMemoryMapping(
        stage_name="understand_question",
        description="问题理解阶段 - 分析用户问题",
        inputs=[
            InputSource(source_type="message", key="user_message", required=False),
        ],
        outputs=[
            OutputTarget(
                action=OutputAction.STORE_KNOWLEDGE,
                region=MemoryRegion.SURVIVOR,
                key="question_type",
                importance=60,
            ),
        ],
    ),

    "retrieve_info": StageMemoryMapping(
        stage_name="retrieve_info",
        description="信息检索阶段 - 查找相关内容",
        inputs=[
            InputSource(source_type="knowledge", key="question_type"),
        ],
        outputs=[
            OutputTarget(
                action=OutputAction.STORE_KNOWLEDGE,
                region=MemoryRegion.SURVIVOR,
                key="relevant_docs",
                source_key="relevant_docs",  # Pipeline outputs relevant_docs
                importance=55,
            ),
        ],
    ),

    "generate_answer": StageMemoryMapping(
        stage_name="generate_answer",
        description="答案生成阶段 - 产出回答",
        inputs=[
            InputSource(source_type="knowledge", key="question_type"),
            InputSource(source_type="knowledge", key="relevant_docs", required=False),
        ],
        outputs=[
            OutputTarget(
                action=OutputAction.STORE_MESSAGE,
                region=MemoryRegion.EDEN,
                key="answer",
                source_key="answer",  # Pipeline outputs answer
                importance=65,
            ),
        ],
    ),
}

# 项目管理流水线的记忆映射
MANAGEMENT_PIPELINE_MAPPINGS: dict[str, StageMemoryMapping] = {
    "collect_status": StageMemoryMapping(
        stage_name="collect_status",
        description="状态收集阶段 - 收集团队和任务状态",
        inputs=[],
        outputs=[
            OutputTarget(
                action=OutputAction.STORE_KNOWLEDGE,
                region=MemoryRegion.SURVIVOR,
                key="team_status",
                importance=70,
            ),
        ],
    ),

    "analyze": StageMemoryMapping(
        stage_name="analyze",
        description="分析报告阶段 - 生成分析报告",
        inputs=[
            InputSource(source_type="knowledge", key="team_status"),
        ],
        outputs=[
            OutputTarget(
                action=OutputAction.STORE_DOCUMENT,
                region=MemoryRegion.OLD,
                key="progress",
                source_key="progress_report",  # Pipeline outputs progress_report
                doc_type="progress",
                importance=80,
                generator_role="project_manager",
            ),
        ],
    ),

    "decide": StageMemoryMapping(
        stage_name="decide",
        description="决策建议阶段 - 产出决策建议",
        inputs=[
            InputSource(source_type="document", key="progress", required=False),
        ],
        outputs=[
            OutputTarget(
                action=OutputAction.STORE_TASK,
                region=MemoryRegion.SURVIVOR,
                key="action_items",
                source_key="action_items",  # Pipeline outputs action_items
                importance=85,
            ),
        ],
    ),
}

# 所有工作流映射的注册表
WORKFLOW_MEMORY_MAPPINGS: dict[str, dict[str, StageMemoryMapping]] = {
    "development_pipeline": DEVELOPMENT_PIPELINE_MAPPINGS,
    "bugfix_pipeline": BUGFIX_PIPELINE_MAPPINGS,
    "intent_pipeline": INTENT_PIPELINE_MAPPINGS,
    "inquiry_pipeline": INQUIRY_PIPELINE_MAPPINGS,
    "management_pipeline": MANAGEMENT_PIPELINE_MAPPINGS,
}


def get_stage_mapping(pipeline_name: str, stage_name: str) -> StageMemoryMapping | None:
    """
    获取指定阶段的记忆映射

    Args:
        pipeline_name: 工作流名称
        stage_name: 阶段名称

    Returns:
        StageMemoryMapping 或 None
    """
    pipeline_mappings = WORKFLOW_MEMORY_MAPPINGS.get(pipeline_name, {})
    return pipeline_mappings.get(stage_name)


def get_pipeline_mappings(pipeline_name: str) -> dict[str, StageMemoryMapping]:
    """
    获取整个工作流的记忆映射

    Args:
        pipeline_name: 工作流名称

    Returns:
        阶段映射字典
    """
    return WORKFLOW_MEMORY_MAPPINGS.get(pipeline_name, {})


def list_mappings() -> dict[str, list[str]]:
    """列出所有已定义映射的阶段"""
    result = {}
    for pipeline_name, mappings in WORKFLOW_MEMORY_MAPPINGS.items():
        result[pipeline_name] = list(mappings.keys())
    return result