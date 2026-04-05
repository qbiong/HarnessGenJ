"""
System Adversarial Controller - 系统级对抗控制器

跨任务分析模式，驱动持续改进

核心功能：
1. 检测重复失败模式
2. 识别生成器薄弱环节
3. 检测判别器偏差（过严/过松）
4. 触发系统改进建议
"""

from typing import Any
from pydantic import BaseModel, Field
import time
from collections import Counter

from py_ha.quality.tracker import QualityTracker, FailurePattern
from py_ha.quality.score import ScoreManager, RoleScore
from py_ha.memory.manager import MemoryManager


class WeaknessPattern(BaseModel):
    """生成器薄弱点模式"""

    pattern_id: str = Field(..., description="模式ID")
    role_type: str = Field(..., description="角色类型")
    role_id: str = Field(..., description="角色ID")
    weakness_type: str = Field(..., description="薄弱类型")
    frequency: int = Field(default=0, description="出现频率")
    examples: list[str] = Field(default_factory=list, description="示例")
    suggestions: list[str] = Field(default_factory=list, description="改进建议")


class BiasPattern(BaseModel):
    """判别器偏差模式"""

    pattern_id: str = Field(..., description="模式ID")
    role_type: str = Field(..., description="角色类型")
    role_id: str = Field(..., description="角色ID")
    bias_type: str = Field(..., description="偏差类型: over_strict | over_loose | selective")
    evidence: list[str] = Field(default_factory=list, description="证据")
    impact: str = Field(default="", description="影响描述")
    suggestions: list[str] = Field(default_factory=list, description="改进建议")


class SystemAnalysisResult(BaseModel):
    """系统级分析结果"""

    analysis_time: float = Field(default_factory=time.time, description="分析时间")
    total_tasks_analyzed: int = Field(default=0, description="分析任务数")

    # 生成器分析
    generator_weaknesses: list[WeaknessPattern] = Field(default_factory=list, description="生成器薄弱点")
    generator_performance: dict[str, float] = Field(default_factory=dict, description="生成器表现")

    # 判别器分析
    discriminator_biases: list[BiasPattern] = Field(default_factory=list, description="判别器偏差")
    discriminator_performance: dict[str, float] = Field(default_factory=dict, description="判别器表现")

    # 失败模式
    failure_patterns: list[FailurePattern] = Field(default_factory=list, description="失败模式")

    # 系统改进建议
    improvement_actions: list[str] = Field(default_factory=list, description="改进建议")

    # 健康度评分
    system_health_score: float = Field(default=0.0, ge=0, le=100, description="系统健康度")


class ImprovementAction(BaseModel):
    """系统改进行动"""

    action_id: str = Field(..., description="行动ID")
    action_type: str = Field(..., description="行动类型: training | adjustment | reinforcement")
    target: str = Field(..., description="目标角色或系统")
    description: str = Field(..., description="行动描述")
    priority: str = Field(default="normal", description="优先级: high | normal | low")
    expected_impact: str = Field(default="", description="预期影响")
    created_at: float = Field(default_factory=time.time)


class SystemAdversarialController:
    """
    系统级对抗控制器

    跨任务分析模式，驱动系统持续改进

    使用示例：
        controller = SystemAdversarialController(
            quality_tracker, score_manager, memory_manager
        )

        # 执行系统级分析
        analysis = controller.analyze_cross_task_patterns()

        # 获取改进建议
        actions = controller.generate_improvement_actions(analysis)
    """

    def __init__(
        self,
        quality_tracker: QualityTracker,
        score_manager: ScoreManager,
        memory_manager: MemoryManager,
    ) -> None:
        self.quality_tracker = quality_tracker
        self.score_manager = score_manager
        self.memory_manager = memory_manager

        # 分析历史
        self._analysis_history: list[SystemAnalysisResult] = []
        self._max_history = 10

    def analyze_cross_task_patterns(self) -> SystemAnalysisResult:
        """
        跨任务模式分析

        分析多个任务的数据，识别系统性问题

        Returns:
            系统分析结果
        """
        # 获取最近的对抗记录
        records = self.quality_tracker.get_recent_records(limit=50)

        if not records:
            return SystemAnalysisResult(
                total_tasks_analyzed=0,
                system_health_score=100.0,
                improvement_actions=["系统刚启动，暂无分析数据"],
            )

        # 分析生成器薄弱点
        generator_weaknesses = self.detect_generator_weakness(records)

        # 分析判别器偏差
        discriminator_biases = self.detect_discriminator_bias(records)

        # 分析失败模式
        failure_patterns = self.quality_tracker.analyze_patterns(limit=10)

        # 计算角色表现
        generator_perf = self._calculate_generator_performance(records)
        discriminator_perf = self._calculate_discriminator_performance(records)

        # 计算系统健康度
        health_score = self._calculate_system_health(
            generator_weaknesses,
            discriminator_biases,
            failure_patterns,
        )

        # 生成改进建议
        improvement_actions = self._generate_improvement_actions(
            generator_weaknesses,
            discriminator_biases,
            failure_patterns,
        )

        result = SystemAnalysisResult(
            total_tasks_analyzed=len(records),
            generator_weaknesses=generator_weaknesses,
            generator_performance=generator_perf,
            discriminator_biases=discriminator_biases,
            discriminator_performance=discriminator_perf,
            failure_patterns=failure_patterns,
            improvement_actions=improvement_actions,
            system_health_score=health_score,
        )

        # 保存分析历史
        self._analysis_history.append(result)
        if len(self._analysis_history) > self._max_history:
            self._analysis_history = self._analysis_history[-self._max_history:]

        return result

    def detect_generator_weakness(self, records: list[Any] | None = None) -> list[WeaknessPattern]:
        """
        识别生成器薄弱点

        分析：
        1. 哪些生成器经常产生问题
        2. 问题类型分布
        3. 需要多轮修复的情况

        Args:
            records: 对抗记录（可选，默认使用最近记录）

        Returns:
            薄弱点模式列表
        """
        if records is None:
            records = self.quality_tracker.get_recent_records(limit=30)

        weaknesses: dict[str, WeaknessPattern] = {}

        # 统计各生成器的问题分布
        for record in records:
            gen_id = record.generator_id

            # 统计问题
            issues = record.get_all_issues()
            issue_types = Counter(
                self._classify_issue_type(issue.description)
                for issue in issues
            )

            # 统计轮次（多轮意味着初始质量低）
            rounds = record.current_round

            # 更新薄弱点统计
            key = f"{gen_id}_{issue_types.most_common(1)[0][0] if issue_types else 'general'}"

            if key not in weaknesses:
                weaknesses[key] = WeaknessPattern(
                    pattern_id=f"WP_{gen_id}_{len(weaknesses)}",
                    role_type=record.generator_id.split("_")[0] if "_" in record.generator_id else "developer",
                    role_id=gen_id,
                    weakness_type=issue_types.most_common(1)[0][0] if issue_types else "general",
                    frequency=0,
                    examples=[],
                    suggestions=[],
                )

            weaknesses[key].frequency += len(issues) + (rounds - 1) * 2

            # 收集示例
            if issues:
                weaknesses[key].examples.append(issues[0].description[:100])

        # 按频率排序
        sorted_weaknesses = sorted(weaknesses.values(), key=lambda w: w.frequency, reverse=True)

        # 添加改进建议
        for weakness in sorted_weaknesses:
            weakness.suggestions = self._get_weakness_suggestions(weakness.weakness_type)

        return sorted_weaknesses[:5]  # 返回前5个最显著的薄弱点

    def detect_discriminator_bias(self, records: list[Any] | None = None) -> list[BiasPattern]:
        """
        检测判别器偏差

        分析：
        1. 过严（误报率高）
        2. 过松（漏报率高）
        3. 选择性偏差（只关注某些类型问题）

        Args:
            records: 对抗记录（可选，默认使用最近记录）

        Returns:
            偏差模式列表
        """
        if records is None:
            records = self.quality_tracker.get_recent_records(limit=30)

        biases: dict[str, BiasPattern] = {}

        # 获取判别器积分数据
        disc_scores = self.score_manager.get_all_scores()
        disc_score_map = {s.role_id: s for s in disc_scores if s.is_discriminator}

        # 分析各判别器
        for record in records:
            disc_id = record.discriminator_id

            # 统计误报和漏报
            false_positives = record.false_positives
            issues = record.get_all_issues()

            # 计算偏差类型
            bias_type = self._determine_bias_type(false_positives, issues, disc_id, disc_score_map)

            if bias_type == "neutral":
                continue

            key = f"{disc_id}_{bias_type}"

            if key not in biases:
                biases[key] = BiasPattern(
                    pattern_id=f"BP_{disc_id}_{len(biases)}",
                    role_type=disc_id.split("_")[0] if "_" in disc_id else "code_reviewer",
                    role_id=disc_id,
                    bias_type=bias_type,
                    evidence=[],
                    impact="",
                    suggestions=[],
                )

            # 添加证据
            if false_positives > 0:
                biases[key].evidence.append(f"误报 {false_positives} 个问题")
            if not issues:
                biases[key].evidence.append("未发现任何问题")

        # 设置影响和改进建议
        for bias in biases.values():
            bias.impact = self._get_bias_impact(bias.bias_type)
            bias.suggestions = self._get_bias_suggestions(bias.bias_type)

        return list(biases.values())[:5]

    def trigger_system_improvement(self, pattern: WeaknessPattern | BiasPattern | FailurePattern) -> ImprovementAction:
        """
        触发系统改进

        根据发现的问题模式，生成改进行动

        Args:
            pattern: 问题模式

        Returns:
            改进行动
        """
        import uuid

        action_id = str(uuid.uuid4())[:8]

        if isinstance(pattern, WeaknessPattern):
            action = ImprovementAction(
                action_id=f"ACT_W{action_id}",
                action_type="training",
                target=pattern.role_id,
                description=f"针对 {pattern.weakness_type} 类型问题进行强化训练",
                priority="high" if pattern.frequency >= 10 else "normal",
                expected_impact=f"减少 {pattern.weakness_type} 类型问题的发生",
            )

        elif isinstance(pattern, BiasPattern):
            action = ImprovementAction(
                action_id=f"ACT_B{action_id}",
                action_type="adjustment",
                target=pattern.role_id,
                description=f"调整 {pattern.role_id} 的审查标准，纠正 {pattern.bias_type} 偏差",
                priority="high" if pattern.bias_type == "over_loose" else "normal",
                expected_impact=f"提高审查准确性，减少 {pattern.bias_type} 情况",
            )

        else:  # FailurePattern
            action = ImprovementAction(
                action_id=f"ACT_F{action_id}",
                action_type="reinforcement",
                target="system",
                description=f"系统级改进：强化 {pattern.name} 相关检查",
                priority="high" if pattern.frequency >= 5 else "normal",
                expected_impact=f"降低 {pattern.name} 失败模式的发生频率",
            )

        # 保存到记忆系统
        self.memory_manager.heap.permanent.store_knowledge(
            f"improvement_{action_id}",
            action.model_dump_json(),
            importance=80,
        )

        return action

    def get_system_health_trend(self) -> list[float]:
        """获取系统健康度趋势"""
        return [r.system_health_score for r in self._analysis_history]

    def _calculate_generator_performance(self, records: list[Any]) -> dict[str, float]:
        """计算生成器表现"""
        performance = {}

        for record in records:
            gen_id = record.generator_id
            if gen_id not in performance:
                performance[gen_id] = {"success": 0, "total": 0}

            performance[gen_id]["total"] += 1
            if record.final_result == "passed":
                performance[gen_id]["success"] += 1

        return {
            role_id: data["success"] / data["total"] if data["total"] > 0 else 0
            for role_id, data in performance.items()
        }

    def _calculate_discriminator_performance(self, records: list[Any]) -> dict[str, float]:
        """计算判别器表现"""
        performance = {}

        for record in records:
            disc_id = record.discriminator_id
            if disc_id not in performance:
                performance[disc_id] = {"valid": 0, "false_positive": 0, "missed": 0}

            # 有效发现
            issues = record.get_all_issues()
            for issue in issues:
                if issue.status != "false_positive":
                    performance[disc_id]["valid"] += 1
                else:
                    performance[disc_id]["false_positive"] += 1

            performance[disc_id]["missed"] += record.false_positives

        # 计算有效率
        return {
            role_id: data["valid"] / (data["valid"] + data["false_positive"])
            if (data["valid"] + data["false_positive"]) > 0 else 1.0
            for role_id, data in performance.items()
        }

    def _classify_issue_type(self, description: str) -> str:
        """分类问题类型"""
        desc_lower = description.lower()

        if any(kw in desc_lower for kw in ["null", "空值", "none", "空指针"]):
            return "null_handling"
        if any(kw in desc_lower for kw in ["error", "exception", "异常", "错误"]):
            return "error_handling"
        if any(kw in desc_lower for kw in ["boundary", "边界", "范围", "limit"]):
            return "boundary_check"
        if any(kw in desc_lower for kw in ["type", "类型", "typeerror"]):
            return "type_safety"
        if any(kw in desc_lower for kw in ["security", "安全", "漏洞", "sql", "xss"]):
            return "security"
        if any(kw in desc_lower for kw in ["performance", "性能", "慢", "timeout"]):
            return "performance"

        return "general"

    def _determine_bias_type(
        self,
        false_positives: int,
        issues: list[Any],
        disc_id: str,
        disc_score_map: dict[str, RoleScore],
    ) -> str:
        """判定偏差类型"""
        score = disc_score_map.get(disc_id)

        if score and score.issues_false_positive >= 3:
            return "over_strict"

        if score and score.issues_missed >= 2:
            return "over_loose"

        if false_positives >= 2:
            return "over_strict"

        if len(issues) == 0 and score and score.total_tasks >= 3:
            return "over_loose"

        return "neutral"

    def _get_weakness_suggestions(self, weakness_type: str) -> list[str]:
        """获取薄弱点改进建议"""
        suggestions_map = {
            "null_handling": ["添加空值检查", "使用 Optional 类型", "编写防御性代码"],
            "error_handling": ["添加异常处理", "使用 try-except", "记录错误日志"],
            "boundary_check": ["验证输入边界", "添加范围检查", "编写边界测试"],
            "type_safety": ["添加类型注解", "使用类型检查工具", "验证输入类型"],
            "security": ["输入验证", "参数化查询", "避免硬编码敏感信息"],
            "performance": ["优化算法", "减少循环嵌套", "使用缓存"],
            "general": ["加强代码审查", "编写更多测试", "参考最佳实践"],
        }
        return suggestions_map.get(weakness_type, suggestions_map["general"])

    def _get_bias_impact(self, bias_type: str) -> str:
        """获取偏差影响描述"""
        impact_map = {
            "over_strict": "可能导致开发效率降低，生成者需要额外时间处理误报",
            "over_loose": "可能导致质量问题漏检，增加生产环境风险",
            "selective": "可能导致某些类型问题被忽略，影响整体质量",
        }
        return impact_map.get(bias_type, "")

    def _get_bias_suggestions(self, bias_type: str) -> list[str]:
        """获取偏差改进建议"""
        suggestions_map = {
            "over_strict": ["调整审查标准", "增加上下文理解", "减少过度审查"],
            "over_loose": ["提高审查标准", "增加审查深度", "关注边界情况"],
            "selective": ["扩展审查范围", "均衡审查各类问题", "避免选择性关注"],
        }
        return suggestions_map.get(bias_type, [])

    def _calculate_system_health(
        self,
        weaknesses: list[WeaknessPattern],
        biases: list[BiasPattern],
        failure_patterns: list[FailurePattern],
    ) -> float:
        """计算系统健康度"""
        base_score = 100.0

        # 薄弱点扣分
        for w in weaknesses:
            base_score -= min(w.frequency * 2, 20)

        # 偏差扣分
        for b in biases:
            base_score -= 10 if b.bias_type in ["over_loose", "over_strict"] else 5

        # 失败模式扣分
        for p in failure_patterns:
            base_score -= min(p.frequency * 1, 10)

        return max(0.0, min(100.0, base_score))

    def _generate_improvement_actions(
        self,
        weaknesses: list[WeaknessPattern],
        biases: list[BiasPattern],
        failure_patterns: list[FailurePattern],
    ) -> list[str]:
        """生成改进建议列表"""
        actions = []

        # 生成器改进
        for w in weaknesses[:3]:
            actions.append(f"建议对 {w.role_id} 进行 {w.weakness_type} 方面强化")

        # 判别器改进
        for b in biases[:2]:
            actions.append(f"建议调整 {b.role_id} 的审查标准，纠正 {b.bias_type} 偏差")

        # 系统级改进
        for p in failure_patterns[:2]:
            actions.append(f"系统级建议：强化 {p.name} 相关检查")

        return actions[:10]  # 最多返回10条


def create_system_adversarial(
    quality_tracker: QualityTracker,
    score_manager: ScoreManager,
    memory_manager: MemoryManager,
) -> SystemAdversarialController:
    """创建系统级对抗控制器"""
    return SystemAdversarialController(
        quality_tracker,
        score_manager,
        memory_manager,
    )