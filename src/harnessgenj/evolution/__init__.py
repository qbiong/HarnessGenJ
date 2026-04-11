"""
Evolution Module - 自我进化系统

实现框架的自我进化能力：
1. PatternExtractor - 从成功解决方案提取可复用模式
2. SkillAccumulator - 自动积累技能定义
3. KnowledgeFeedback - 对抗审查结果反馈到知识验证
4. TokenOptimizer - 高频模式内联减少token消耗
5. SkillRegistry - 技能注册和管理

核心流程：
- 成功记录 → PatternExtractor → ExtractedPattern
- ExtractedPattern → SkillAccumulator → RoleSkill
- RoleSkill → StructuredKnowledgeManager → 知识库
- 高频技能 → TokenOptimizer → ContextAssembler (inline)

使用示例:
    from harnessgenj.evolution import (
        PatternExtractor,
        SkillAccumulator,
        KnowledgeFeedback,
        TokenOptimizer,
    )

    # 提取模式
    extractor = PatternExtractor()
    patterns = extractor.extract_from_success_records(records)

    # 积累技能
    accumulator = SkillAccumulator()
    for pattern in patterns:
        skill = accumulator.accumulate_pattern(pattern)
        accumulator.store_skill(skill)

    # 反馈知识质量
    feedback = KnowledgeFeedback()
    feedback.process_adversarial_result(review_record)
"""

from harnessgenj.evolution.pattern_extractor import (
    PatternExtractor,
    ExtractedPattern,
    PatternType,
    PatternValidationResult,
    create_pattern_extractor,
)
from harnessgenj.evolution.skill_accumulator import (
    SkillAccumulator,
    RoleSkill,
    SkillType,
    SkillAccumulatorStats,
    create_skill_accumulator,
)
from harnessgenj.evolution.knowledge_feedback import (
    KnowledgeFeedback,
    FeedbackRecord,
    FeedbackStatus,
    KnowledgeFeedbackStats,
    create_knowledge_feedback,
)
from harnessgenj.evolution.token_optimizer import (
    TokenOptimizer,
    InlineCandidate,
    TokenSavingsReport,
    create_token_optimizer,
)
from harnessgenj.evolution.skill_registry import (
    SkillRegistry,
    SkillRegistryStats,
    create_skill_registry,
)

__all__ = [
    # Pattern Extractor
    "PatternExtractor",
    "ExtractedPattern",
    "PatternType",
    "PatternValidationResult",
    "create_pattern_extractor",
    # Skill Accumulator
    "SkillAccumulator",
    "RoleSkill",
    "SkillType",
    "SkillAccumulatorStats",
    "create_skill_accumulator",
    # Knowledge Feedback
    "KnowledgeFeedback",
    "FeedbackRecord",
    "FeedbackStatus",
    "KnowledgeFeedbackStats",
    "create_knowledge_feedback",
    # Token Optimizer
    "TokenOptimizer",
    "InlineCandidate",
    "TokenSavingsReport",
    "create_token_optimizer",
    # Skill Registry
    "SkillRegistry",
    "SkillRegistryStats",
    "create_skill_registry",
]