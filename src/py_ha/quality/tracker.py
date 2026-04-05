"""
Quality Tracker - 质量追踪器

分析对抗记录，识别失败模式，生成改进建议
"""

from typing import Any
from pydantic import BaseModel, Field
import json
import os
import time
from collections import Counter

from py_ha.quality.record import AdversarialRecord, IssueRecord, IssueSeverity


class FailurePattern(BaseModel):
    """失败模式"""
    pattern_id: str = Field(..., description="模式ID")
    name: str = Field(..., description="模式名称")
    description: str = Field(..., description="模式描述")
    frequency: int = Field(default=0, description="出现频率")
    last_seen: float = Field(default_factory=time.time, description="最后出现时间")
    affected_roles: list[str] = Field(default_factory=list, description="受影响角色")
    suggestions: list[str] = Field(default_factory=list, description="改进建议")


class QualityMetrics(BaseModel):
    """质量指标"""
    # 成功率
    first_pass_rate: float = Field(default=0.0, description="首轮通过率")
    overall_pass_rate: float = Field(default=0.0, description="总体通过率")

    # 效率
    avg_rounds: float = Field(default=0.0, description="平均对抗轮次")
    avg_duration: float = Field(default=0.0, description="平均时长")

    # 问题分布
    issues_per_session: float = Field(default=0.0, description="每会话问题数")
    critical_rate: float = Field(default=0.0, description="严重问题占比")
    false_positive_rate: float = Field(default=0.0, description="误报率")

    # 角色表现
    generator_performance: dict[str, float] = Field(default_factory=dict, description="生成器表现")
    discriminator_performance: dict[str, float] = Field(default_factory=dict, description="判别器表现")


class QualityTracker:
    """
    质量追踪器

    功能：
    1. 记录对抗会话
    2. 分析失败模式
    3. 计算质量指标
    4. 生成改进建议

    使用示例：
        tracker = QualityTracker(".py_ha")

        # 记录对抗
        tracker.record_adversarial(record)

        # 获取指标
        metrics = tracker.get_metrics()

        # 分析失败模式
        patterns = tracker.analyze_patterns()
    """

    # 预定义的失败模式
    PREDEFINED_PATTERNS = {
        "null_check_missing": FailurePattern(
            pattern_id="FP001",
            name="空值检查缺失",
            description="未对可能为空的值进行检查",
            suggestions=[
                "添加空值检查",
                "使用 Optional 类型标注",
                "编写防御性代码",
            ],
        ),
        "error_handling_missing": FailurePattern(
            pattern_id="FP002",
            name="异常处理缺失",
            description="未处理可能的异常情况",
            suggestions=[
                "添加 try-except 块",
                "定义明确的异常类型",
                "记录异常日志",
            ],
        ),
        "boundary_check_missing": FailurePattern(
            pattern_id="FP003",
            name="边界检查缺失",
            description="未检查输入边界条件",
            suggestions=[
                "验证输入范围",
                "添加边界条件测试",
                "使用断言检查",
            ],
        ),
        "type_mismatch": FailurePattern(
            pattern_id="FP004",
            name="类型不匹配",
            description="类型使用不正确",
            suggestions=[
                "添加类型注解",
                "使用类型检查工具",
                "验证输入类型",
            ],
        ),
        "security_vulnerability": FailurePattern(
            pattern_id="FP005",
            name="安全漏洞",
            description="存在潜在安全问题",
            suggestions=[
                "输入验证",
                "参数化查询",
                "避免硬编码敏感信息",
            ],
        ),
        "performance_issue": FailurePattern(
            pattern_id="FP006",
            name="性能问题",
            description="存在性能瓶颈",
            suggestions=[
                "优化算法复杂度",
                "减少不必要的计算",
                "使用缓存",
            ],
        ),
    }

    def __init__(self, workspace: str = ".py_ha") -> None:
        self.workspace = workspace
        self._records: list[AdversarialRecord] = []
        self._patterns: dict[str, FailurePattern] = dict(self.PREDEFINED_PATTERNS)
        self._max_records = 100

        self._load()

    # ==================== 记录管理 ====================

    def record_adversarial(self, record: AdversarialRecord) -> None:
        """记录对抗会话"""
        self._records.append(record)

        # 限制记录数量
        if len(self._records) > self._max_records:
            self._records = self._records[-self._max_records:]

        self._save()

    def get_recent_records(self, limit: int = 20) -> list[AdversarialRecord]:
        """获取最近记录"""
        return self._records[-limit:]

    def get_records_by_task(self, task_id: str) -> list[AdversarialRecord]:
        """获取任务相关记录"""
        return [r for r in self._records if r.task_id == task_id]

    # ==================== 指标计算 ====================

    def get_metrics(self, days: int = 7) -> QualityMetrics:
        """
        计算质量指标

        Args:
            days: 统计最近N天的数据

        Returns:
            质量指标对象
        """
        if not self._records:
            return QualityMetrics()

        # 筛选时间范围
        cutoff = time.time() - days * 86400
        records = [r for r in self._records if r.created_at >= cutoff]

        if not records:
            return QualityMetrics()

        # 计算成功率
        completed = [r for r in records if r.is_completed]
        passed = [r for r in completed if r.final_result == "passed"]
        first_pass = [r for r in completed if r.current_round == 1 and r.final_result == "passed"]

        total_sessions = len(completed)
        overall_pass_rate = len(passed) / total_sessions if total_sessions > 0 else 0
        first_pass_rate = len(first_pass) / total_sessions if total_sessions > 0 else 0

        # 计算效率
        avg_rounds = sum(r.current_round for r in completed) / len(completed) if completed else 0
        avg_duration = sum(r.duration for r in completed) / len(completed) if completed else 0

        # 问题统计
        total_issues = sum(r.total_issues for r in completed)
        issues_per_session = total_issues / len(completed) if completed else 0

        # 严重问题统计
        critical_count = 0
        total_found = 0
        false_positive = 0

        for r in completed:
            for severity, count in r.issue_summary.items():
                total_found += count
                if severity == "critical":
                    critical_count += count
            false_positive += r.false_positives

        critical_rate = critical_count / total_found if total_found > 0 else 0
        false_positive_rate = false_positive / total_found if total_found > 0 else 0

        # 角色表现
        generator_perf = self._calculate_role_performance(records, "generator")
        discriminator_perf = self._calculate_role_performance(records, "discriminator")

        return QualityMetrics(
            first_pass_rate=round(first_pass_rate, 3),
            overall_pass_rate=round(overall_pass_rate, 3),
            avg_rounds=round(avg_rounds, 2),
            avg_duration=round(avg_duration, 2),
            issues_per_session=round(issues_per_session, 2),
            critical_rate=round(critical_rate, 3),
            false_positive_rate=round(false_positive_rate, 3),
            generator_performance=generator_perf,
            discriminator_performance=discriminator_perf,
        )

    def _calculate_role_performance(
        self,
        records: list[AdversarialRecord],
        role_type: str,
    ) -> dict[str, float]:
        """计算角色表现"""
        performance = {}

        for record in records:
            if role_type == "generator":
                role_id = record.generator_id
                success = record.final_result == "passed"
            else:
                role_id = record.discriminator_id
                success = record.total_issues > 0 and record.false_positives == 0

            if role_id not in performance:
                performance[role_id] = {"success": 0, "total": 0}

            performance[role_id]["total"] += 1
            if success:
                performance[role_id]["success"] += 1

        # 计算成功率
        return {
            role_id: data["success"] / data["total"] if data["total"] > 0 else 0
            for role_id, data in performance.items()
        }

    # ==================== 失败模式分析 ====================

    def analyze_patterns(self, limit: int = 50) -> list[FailurePattern]:
        """
        分析失败模式

        Returns:
            发现的失败模式列表
        """
        if not self._records:
            return []

        # 收集所有问题描述
        issue_descriptions = []
        for record in self._records:
            for issue in record.get_all_issues():
                if issue.status != "false_positive":
                    issue_descriptions.append(issue.description.lower())

        if not issue_descriptions:
            return []

        # 匹配预定义模式
        pattern_matches: dict[str, list[str]] = {p.pattern_id: [] for p in self._patterns.values()}

        keywords_map = {
            "FP001": ["null", "none", "空", "空值", "nonecheck", "nullcheck"],
            "FP002": ["exception", "error", "异常", "错误处理", "try", "catch"],
            "FP003": ["boundary", "range", "边界", "范围", "limit", "边界条件"],
            "FP004": ["type", "类型", "typeerror", "类型错误", "mismatch"],
            "FP005": ["security", "安全", "漏洞", "sql", "xss", "injection"],
            "FP006": ["performance", "性能", "slow", "timeout", "慢", "优化"],
        }

        for desc in issue_descriptions:
            for pattern_id, keywords in keywords_map.items():
                if any(kw in desc for kw in keywords):
                    pattern_matches[pattern_id].append(desc)
                    break

        # 构建结果
        results = []
        for pattern in self._patterns.values():
            matches = pattern_matches.get(pattern.pattern_id, [])
            if matches:
                updated_pattern = FailurePattern(
                    pattern_id=pattern.pattern_id,
                    name=pattern.name,
                    description=pattern.description,
                    frequency=len(matches),
                    last_seen=time.time(),
                    suggestions=pattern.suggestions,
                )
                results.append(updated_pattern)

        # 按频率排序
        results.sort(key=lambda p: p.frequency, reverse=True)
        return results[:10]

    def get_improvement_suggestions(self) -> list[str]:
        """获取改进建议"""
        patterns = self.analyze_patterns()
        suggestions = []

        for pattern in patterns[:3]:  # 取前3个最常见模式
            suggestions.extend(pattern.suggestions)

        # 去重
        return list(dict.fromkeys(suggestions))

    # ==================== 报告生成 ====================

    def get_quality_report(self) -> dict[str, Any]:
        """生成质量报告"""
        metrics = self.get_metrics()
        patterns = self.analyze_patterns()
        suggestions = self.get_improvement_suggestions()

        return {
            "summary": {
                "total_sessions": len(self._records),
                "pass_rate": f"{metrics.overall_pass_rate:.1%}",
                "first_pass_rate": f"{metrics.first_pass_rate:.1%}",
                "avg_rounds": metrics.avg_rounds,
            },
            "metrics": metrics.model_dump(),
            "top_patterns": [
                {
                    "name": p.name,
                    "frequency": p.frequency,
                    "suggestions": p.suggestions[:2],
                }
                for p in patterns[:5]
            ],
            "improvement_suggestions": suggestions,
            "generated_at": time.time(),
        }

    # ==================== 持久化 ====================

    def _save(self) -> None:
        """保存到文件"""
        try:
            data_path = os.path.join(self.workspace, "quality_tracker.json")

            data = {
                "records": [r.model_dump() for r in self._records[-50:]],  # 只保存最近50条
            }

            with open(data_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        except Exception:
            pass

    def _load(self) -> None:
        """从文件加载"""
        data_path = os.path.join(self.workspace, "quality_tracker.json")
        if not os.path.exists(data_path):
            return

        try:
            with open(data_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for rdata in data.get("records", []):
                # 重建嵌套对象
                rounds_data = rdata.pop("rounds", [])
                record = AdversarialRecord(**rdata)
                for round_data in rounds_data:
                    from py_ha.quality.record import AdversarialRound
                    findings_data = round_data.pop("discriminator_findings", [])
                    adv_round = AdversarialRound(**round_data)
                    for finding_data in findings_data:
                        adv_round.discriminator_findings.append(IssueRecord(**finding_data))
                    record.rounds.append(adv_round)
                self._records.append(record)
        except Exception:
            pass

    def get_recent_reviews(self, limit: int = 20) -> list[dict[str, Any]]:
        """获取最近的审查记录（用于上下文装配）"""
        records = self._records[-limit:]
        return [
            {
                "task_id": r.task_id,
                "generator_id": r.generator_id,
                "discriminator_id": r.discriminator_id,
                "result": r.final_result,
                "rounds": r.current_round,
                "issues": r.total_issues,
                "created_at": r.created_at,
            }
            for r in records
        ]

    def get_failed_reviews(self, limit: int = 20) -> list[dict[str, Any]]:
        """获取失败的审查记录（用于漏洞猎手）"""
        failed = [r for r in self._records if r.final_result == "failed" or r.total_issues > 0]
        return [
            {
                "task_id": r.task_id,
                "generator_id": r.generator_id,
                "issues": r.get_all_issues(),
                "issue_summary": r.issue_summary,
                "created_at": r.created_at,
            }
            for r in failed[-limit:]
        ]

    def clear(self) -> None:
        """清除所有记录"""
        self._records.clear()
        self._save()