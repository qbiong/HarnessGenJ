"""
Knowledge Feedback - 知识反馈系统

处理对抗审查结果反馈到知识验证：
1. 处理对抗审查记录
2. 更新知识质量分数
3. 标记验证状态
4. 生成改进建议
5. 触发质量感知GC

使用示例:
    from harnessgenj.evolution.knowledge_feedback import KnowledgeFeedback

    feedback = KnowledgeFeedback()

    # 处理对抗审查结果
    record = feedback.process_adversarial_result(review_record)

    # 更新知识质量
    feedback.update_knowledge_quality(knowledge_id, new_score)

    # 批量验证
    results = feedback.batch_validate(knowledge_ids)
"""

from typing import Any, Optional
from pydantic import BaseModel, Field
from enum import Enum
import time
import json
from pathlib import Path


class FeedbackStatus(str, Enum):
    """反馈状态"""

    VALIDATED = "validated"      # 已验证
    DEPRECATED = "deprecated"    # 已淘汰
    NEEDS_REVIEW = "needs_review"  # 待审查
    IMPROVED = "improved"        # 已改进
    NO_CHANGE = "no_change"      # 无变化


class FeedbackRecord(BaseModel):
    """反馈记录"""

    feedback_id: str = Field(..., description="反馈ID")
    source_type: str = Field(default="adversarial_review", description="来源类型")
    knowledge_id: str = Field(..., description="关联的知识ID")
    original_quality: float = Field(default=0.0, description="原始质量分数")
    quality_update: float = Field(default=0.0, description="质量更新值")
    new_quality: float = Field(default=0.0, description="新质量分数")
    validation_status: FeedbackStatus = Field(default=FeedbackStatus.NEEDS_REVIEW, description="验证状态")
    improvement_suggestions: list[str] = Field(default_factory=list, description="改进建议")
    issues_found: list[str] = Field(default_factory=list, description="发现的问题")
    created_at: float = Field(default_factory=time.time, description="创建时间")
    metadata: dict[str, Any] = Field(default_factory=dict, description="额外元数据")


class KnowledgeFeedbackStats(BaseModel):
    """知识反馈统计"""

    total_feedbacks: int = Field(default=0, description="总反馈数")
    validated_knowledge: int = Field(default=0, description="已验证知识数")
    deprecated_knowledge: int = Field(default=0, description="已淘汰知识数")
    needs_review: int = Field(default=0, description="待审查知识数")
    avg_quality_improvement: float = Field(default=0.0, description="平均质量提升")
    quality_distribution: dict[str, int] = Field(default_factory=dict, description="质量分布")


class KnowledgeFeedbackConfig(BaseModel):
    """知识反馈配置"""

    validate_threshold: float = Field(default=70.0, description="验证阈值")
    deprecate_threshold: float = Field(default=30.0, description="淘汰阈值")
    quality_weight: float = Field(default=0.2, description="新质量权重")
    min_feedback_count: int = Field(default=3, description="最小反馈数")
    auto_gc_trigger: int = Field(default=10, description="自动GC触发阈值")


class KnowledgeFeedback:
    """
    知识反馈系统

    功能：
    1. 处理对抗审查结果
    2. 更新知识质量
    3. 标记验证状态
    4. 生成改进建议
    5. 触发质量感知GC

    与 QualityTracker 和 StructuredKnowledgeManager 集成。
    """

    # 存储文件
    FEEDBACK_FILE = "feedback_history.json"

    def __init__(
        self,
        storage_path: Optional[str] = None,
        config: Optional[KnowledgeFeedbackConfig] = None,
        knowledge_manager: Optional[Any] = None,
        quality_tracker: Optional[Any] = None,
        garbage_collector: Optional[Any] = None,
    ):
        """
        初始化知识反馈系统

        Args:
            storage_path: 存储路径
            config: 反馈配置
            knowledge_manager: 结构化知识管理器
            quality_tracker: 质量追踪器
            garbage_collector: 垃圾收集器
        """
        self._storage_path = Path(storage_path or ".harnessgenj")
        self._config = config or KnowledgeFeedbackConfig()
        self._knowledge_manager = knowledge_manager
        self._quality_tracker = quality_tracker
        self._garbage_collector = garbage_collector

        # 反馈存储
        self._feedbacks: dict[str, FeedbackRecord] = {}
        self._feedbacks_by_knowledge: dict[str, list[str]] = {}

        # 知识质量追踪
        self._knowledge_quality: dict[str, float] = {}
        self._deprecated_count: int = 0

        # 加载已有反馈
        self._load()

    def process_adversarial_result(
        self,
        review_record: dict[str, Any],
    ) -> FeedbackRecord:
        """
        处理对抗审查结果

        Args:
            review_record: 对抗审查记录

        Returns:
            反馈记录
        """
        # 提取关键信息
        generator_output = review_record.get("generator_output", {})
        quality_score = review_record.get("quality_score", 50.0)
        issues = review_record.get("issues", [])
        passed = review_record.get("passed", False)

        # 查找关联知识
        related_knowledge = self._find_related_knowledge(generator_output)

        if not related_knowledge:
            # 创建临时反馈记录
            return FeedbackRecord(
                feedback_id=self._generate_feedback_id(),
                knowledge_id="unknown",
                quality_update=quality_score,
                new_quality=quality_score,
                validation_status=FeedbackStatus.NO_CHANGE,
                issues_found=issues,
            )

        # 处理每个关联知识
        feedback = None
        for knowledge_id in related_knowledge:
            feedback = self._update_single_knowledge(
                knowledge_id,
                quality_score,
                issues,
                passed
            )

        return feedback or FeedbackRecord(
            feedback_id=self._generate_feedback_id(),
            knowledge_id="unknown",
            validation_status=FeedbackStatus.NO_CHANGE,
        )

    def update_knowledge_quality(
        self,
        knowledge_id: str,
        score: float,
    ) -> bool:
        """
        更新知识质量分数

        Args:
            knowledge_id: 知识ID
            score: 新分数

        Returns:
            是否成功更新
        """
        original_quality = self._knowledge_quality.get(knowledge_id, 50.0)

        # 加权更新
        new_quality = original_quality * (1 - self._config.quality_weight) + score * self._config.quality_weight

        self._knowledge_quality[knowledge_id] = new_quality

        # 创建反馈记录
        feedback = FeedbackRecord(
            feedback_id=self._generate_feedback_id(),
            knowledge_id=knowledge_id,
            original_quality=original_quality,
            quality_update=score,
            new_quality=new_quality,
            validation_status=self._determine_status(new_quality),
        )

        self._feedbacks[feedback.feedback_id] = feedback
        if knowledge_id not in self._feedbacks_by_knowledge:
            self._feedbacks_by_knowledge[knowledge_id] = []
        self._feedbacks_by_knowledge[knowledge_id].append(feedback.feedback_id)

        # 持久化
        self._persist()

        return True

    def mark_for_review(
        self,
        knowledge_id: str,
        reason: str,
    ) -> bool:
        """
        标记知识待审查

        Args:
            knowledge_id: 知识ID
            reason: 原因

        Returns:
            是否成功标记
        """
        feedback = FeedbackRecord(
            feedback_id=self._generate_feedback_id(),
            knowledge_id=knowledge_id,
            validation_status=FeedbackStatus.NEEDS_REVIEW,
            improvement_suggestions=[reason],
        )

        self._feedbacks[feedback.feedback_id] = feedback
        if knowledge_id not in self._feedbacks_by_knowledge:
            self._feedbacks_by_knowledge[knowledge_id] = []
        self._feedbacks_by_knowledge[knowledge_id].append(feedback.feedback_id)

        # 持久化
        self._persist()

        return True

    def generate_improvement_suggestions(
        self,
        knowledge_id: str,
    ) -> list[str]:
        """
        生成改进建议

        Args:
            knowledge_id: 知识ID

        Returns:
            改进建议列表
        """
        suggestions = []

        # 从历史反馈分析
        feedback_ids = self._feedbacks_by_knowledge.get(knowledge_id, [])
        issues_found = []
        for fid in feedback_ids:
            if fid in self._feedbacks:
                issues_found.extend(self._feedbacks[fid].issues_found)

        # 统计常见问题
        issue_counts: dict[str, int] = {}
        for issue in issues_found:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1

        # 生成建议
        for issue, count in sorted(issue_counts.items(), key=lambda x: -x[1]):
            if count >= 2:
                suggestions.append(f"重点解决: {issue}（出现{count}次）")

        # 添加通用建议
        quality = self._knowledge_quality.get(knowledge_id, 50.0)
        if quality < self._config.validate_threshold:
            suggestions.append("需要加强代码质量和测试覆盖率")
        if quality < self._config.deprecate_threshold:
            suggestions.append("建议重新设计或淘汰")

        return suggestions

    def batch_validate(
        self,
        knowledge_ids: list[str],
    ) -> dict[str, Any]:
        """
        批量验证知识

        Args:
            knowledge_ids: 知识ID列表

        Returns:
            验证结果统计
        """
        results = {
            "total": len(knowledge_ids),
            "validated": 0,
            "deprecated": 0,
            "needs_review": 0,
            "unchanged": 0,
        }

        for knowledge_id in knowledge_ids:
            quality = self._knowledge_quality.get(knowledge_id, 50.0)
            status = self._determine_status(quality)

            feedback = FeedbackRecord(
                feedback_id=self._generate_feedback_id(),
                knowledge_id=knowledge_id,
                original_quality=quality,
                new_quality=quality,
                validation_status=status,
            )

            self._feedbacks[feedback.feedback_id] = feedback

            # 统计
            if status == FeedbackStatus.VALIDATED:
                results["validated"] += 1
            elif status == FeedbackStatus.DEPRECATED:
                results["deprecated"] += 1
                self._deprecated_count += 1
            elif status == FeedbackStatus.NEEDS_REVIEW:
                results["needs_review"] += 1
            else:
                results["unchanged"] += 1

        # 检查是否触发GC
        if self._deprecated_count >= self._config.auto_gc_trigger:
            self._trigger_gc()

        # 持久化
        self._persist()

        return results

    def get_feedback_for_knowledge(
        self,
        knowledge_id: str,
    ) -> list[FeedbackRecord]:
        """获取知识的所有反馈"""
        feedback_ids = self._feedbacks_by_knowledge.get(knowledge_id, [])
        return [self._feedbacks[id] for id in feedback_ids if id in self._feedbacks]

    def get_deprecated_knowledge(self) -> list[str]:
        """获取已淘汰的知识ID"""
        deprecated = []
        for knowledge_id, quality in self._knowledge_quality.items():
            if quality < self._config.deprecate_threshold:
                deprecated.append(knowledge_id)
        return deprecated

    def get_needs_review_knowledge(self) -> list[str]:
        """获取待审查的知识ID"""
        needs_review = []
        for knowledge_id, quality in self._knowledge_quality.items():
            if self._config.deprecate_threshold <= quality < self._config.validate_threshold:
                needs_review.append(knowledge_id)
        return needs_review

    def get_stats(self) -> KnowledgeFeedbackStats:
        """获取统计信息"""
        stats = KnowledgeFeedbackStats()

        stats.total_feedbacks = len(self._feedbacks)

        # 统计各状态
        for feedback in self._feedbacks.values():
            if feedback.validation_status == FeedbackStatus.VALIDATED:
                stats.validated_knowledge += 1
            elif feedback.validation_status == FeedbackStatus.DEPRECATED:
                stats.deprecated_knowledge += 1
            elif feedback.validation_status == FeedbackStatus.NEEDS_REVIEW:
                stats.needs_review += 1

        # 计算质量提升
        improvements = []
        for feedback in self._feedbacks.values():
            if feedback.original_quality > 0:
                improvement = feedback.new_quality - feedback.original_quality
                improvements.append(improvement)

        if improvements:
            stats.avg_quality_improvement = sum(improvements) / len(improvements)

        # 质量分布
        distribution = {"high": 0, "medium": 0, "low": 0}
        for quality in self._knowledge_quality.values():
            if quality >= 70:
                distribution["high"] += 1
            elif quality >= 40:
                distribution["medium"] += 1
            else:
                distribution["low"] += 1
        stats.quality_distribution = distribution

        return stats

    def _update_single_knowledge(
        self,
        knowledge_id: str,
        quality_score: float,
        issues: list[str],
        passed: bool,
    ) -> FeedbackRecord:
        """更新单个知识"""
        original_quality = self._knowledge_quality.get(knowledge_id, 50.0)

        # 计算新质量
        if passed:
            # 通过审查，质量提升
            new_quality = min(100, original_quality + quality_score * self._config.quality_weight)
        else:
            # 未通过，质量下降
            new_quality = original_quality * (1 - self._config.quality_weight) + quality_score * self._config.quality_weight

        self._knowledge_quality[knowledge_id] = new_quality

        # 确定状态
        status = self._determine_status(new_quality)

        # 生成改进建议
        suggestions = []
        if not passed and issues:
            suggestions = [f"修复: {issue}" for issue in issues[:3]]

        # 创建反馈记录
        feedback = FeedbackRecord(
            feedback_id=self._generate_feedback_id(),
            source_type="adversarial_review",
            knowledge_id=knowledge_id,
            original_quality=original_quality,
            quality_update=quality_score,
            new_quality=new_quality,
            validation_status=status,
            improvement_suggestions=suggestions,
            issues_found=issues,
        )

        self._feedbacks[feedback.feedback_id] = feedback
        if knowledge_id not in self._feedbacks_by_knowledge:
            self._feedbacks_by_knowledge[knowledge_id] = []
        self._feedbacks_by_knowledge[knowledge_id].append(feedback.feedback_id)

        # 检查淘汰
        if status == FeedbackStatus.DEPRECATED:
            self._deprecated_count += 1
            if self._deprecated_count >= self._config.auto_gc_trigger:
                self._trigger_gc()

        return feedback

    def _find_related_knowledge(
        self,
        output: dict[str, Any],
    ) -> list[str]:
        """查找关联知识"""
        related = []

        # 从知识管理器搜索
        if self._knowledge_manager:
            try:
                # 提取关键词
                code = output.get("code", "")
                if code:
                    # 搜索相关知识
                    results = self._knowledge_manager.search(code)
                    related = [r.get("id") for r in results[:3] if r.get("id")]
            except Exception:
                pass

        return related

    def _determine_status(self, quality: float) -> FeedbackStatus:
        """确定验证状态"""
        if quality >= self._config.validate_threshold:
            return FeedbackStatus.VALIDATED
        elif quality < self._config.deprecate_threshold:
            return FeedbackStatus.DEPRECATED
        else:
            return FeedbackStatus.NEEDS_REVIEW

    def _trigger_gc(self) -> None:
        """触发垃圾收集"""
        if self._garbage_collector:
            try:
                # 获取淘汰的知识
                deprecated = self.get_deprecated_knowledge()
                if deprecated:
                    self._garbage_collector.quality_gc()
                    self._deprecated_count = 0  # 重置计数
            except Exception:
                pass

    def _generate_feedback_id(self) -> str:
        """生成反馈ID"""
        return f"feedback-{int(time.time() * 1000)}-{len(self._feedbacks) + 1}"

    def _persist(self) -> None:
        """持久化存储"""
        self._storage_path.mkdir(parents=True, exist_ok=True)
        file_path = self._storage_path / self.FEEDBACK_FILE

        data = {
            "feedbacks": {id: f.model_dump() for id, f in self._feedbacks.items()},
            "by_knowledge": self._feedbacks_by_knowledge,
            "knowledge_quality": self._knowledge_quality,
            "deprecated_count": self._deprecated_count,
            "updated_at": time.time(),
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load(self) -> None:
        """加载已有反馈"""
        file_path = self._storage_path / self.FEEDBACK_FILE

        if not file_path.exists():
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for id, feedback_data in data.get("feedbacks", {}).items():
                self._feedbacks[id] = FeedbackRecord(**feedback_data)

            self._feedbacks_by_knowledge = data.get("by_knowledge", {})
            self._knowledge_quality = data.get("knowledge_quality", {})
            self._deprecated_count = data.get("deprecated_count", 0)

        except (json.JSONDecodeError, KeyError, ValueError):
            pass


def create_knowledge_feedback(
    storage_path: Optional[str] = None,
    **kwargs: Any,
) -> KnowledgeFeedback:
    """创建知识反馈系统"""
    return KnowledgeFeedback(storage_path, **kwargs)