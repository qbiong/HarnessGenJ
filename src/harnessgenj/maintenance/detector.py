"""
Requirement Detector - 需求检测器

从以下来源检测潜在需求：
1. 用户消息中的功能请求、问题报告
2. AI 主动发现的问题或改进建议
3. 已完成任务中的经验总结

核心能力：
- 多模式匹配（关键词 + 正则表达式）
- 上下文感知检测
- 置信度评估
"""

import re
import time
import uuid
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class RequirementType(str, Enum):
    """需求类型"""

    FEATURE = "feature"  # 功能需求
    BUG_FIX = "bug_fix"  # Bug修复
    IMPROVEMENT = "improvement"  # 改进优化
    CONSTRAINT = "constraint"  # 约束条件
    QUESTION = "question"  # 问题咨询（可能隐含需求）
    FEEDBACK = "feedback"  # 用户反馈


class DetectionSource(str, Enum):
    """检测来源"""

    USER_MESSAGE = "user_message"  # 用户主动提出
    AI_ANALYSIS = "ai_analysis"  # AI 主动发现
    CODE_REVIEW = "code_review"  # 代码审查发现
    TEST_FAILURE = "test_failure"  # 测试失败发现
    EXPERIENCE = "experience"  # 经验总结


class DetectedRequirement(BaseModel):
    """检测到的需求"""

    req_id: str = Field(..., description="需求ID")
    title: str = Field(..., description="需求标题")
    description: str = Field(..., description="需求描述")
    req_type: RequirementType = Field(..., description="需求类型")
    source: DetectionSource = Field(..., description="检测来源")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度 (0-1)")
    original_message: str = Field(default="", description="原始消息")
    extracted_entities: dict[str, Any] = Field(default_factory=dict, description="提取的实体")
    suggested_priority: str = Field(default="P2", description="建议优先级")
    suggested_assignee: str = Field(default="", description="建议负责人")
    detected_at: float = Field(default_factory=time.time, description="检测时间")
    context: dict[str, Any] = Field(default_factory=dict, description="上下文信息")

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return self.model_dump()


class RequirementDetector:
    """
    需求检测器

    从用户消息或AI发现的问题中提取潜在需求，
    支持多模式匹配和置信度评估。

    使用示例:
        detector = RequirementDetector()

        # 从用户消息检测
        result = detector.detect_from_message("我需要一个购物车功能")
        # result.requirements = [DetectedRequirement(title="购物车功能", ...)]

        # 从AI分析检测
        result = detector.detect_from_analysis({
            "issues_found": ["性能瓶颈", "内存泄漏"],
            "suggestions": ["优化数据库查询"],
        })
    """

    # 功能需求关键词
    FEATURE_KEYWORDS = [
        "需要", "想要", "添加", "新增", "实现", "开发",
        "功能", "特性", "模块", "组件", "服务",
        "我希望", "我想要", "能不能", "是否可以",
        "帮我开发", "帮我实现", "帮忙添加",
    ]

    # Bug/问题关键词
    BUG_KEYWORDS = [
        "bug", "问题", "错误", "异常", "报错", "崩溃",
        "无法", "不能", "不工作", "失败", "闪退",
        "修复", "改正", "解决", "不对", "不正确",
        "没有正确", "缺少", "漏掉",
    ]

    # 改进/优化关键词
    IMPROVEMENT_KEYWORDS = [
        "优化", "改进", "提升", "增强", "完善",
        "性能", "效率", "速度", "体验",
        "重构", "简化", "统一",
    ]

    # 约束关键词
    CONSTRAINT_KEYWORDS = [
        "必须", "要求", "限制", "约束", "规范",
        "兼容", "安全", "隐私", "法规",
    ]

    # 问题咨询关键词
    QUESTION_KEYWORDS = [
        "是什么", "为什么", "怎么", "如何", "怎样",
        "请问", "想知道", "查询", "了解",
    ]

    # 反馈关键词
    FEEDBACK_KEYWORDS = [
        "建议", "反馈", "意见", "评价", "评分",
        "不好用", "不习惯", "不喜欢", "很好", "不错",
    ]

    # 正则模式
    FEATURE_PATTERNS = [
        r"(我需要|想要|希望).{0,30}(功能|特性|模块)",
        r"(添加|新增|实现|开发).{0,30}(功能|特性|模块)",
        r"(帮我|请帮我).{0,10}(开发|实现|添加)",
        r"(能不能|是否可以|可以吗).{0,20}(实现|添加|开发)",
    ]

    BUG_PATTERNS = [
        r"(有|发现|遇到).{0,10}(bug|问题|错误|异常)",
        r"(无法|不能).{0,20}(使用|工作|运行|操作)",
        r"(没有|未).{0,10}(正确|正常|成功)",
        r"(修复|解决).{0,20}(问题|bug|错误)",
        r"(报错|崩溃|闪退).{0,20}(在|当)",
    ]

    IMPROVEMENT_PATTERNS = [
        r"(优化|改进|提升).{0,30}(性能|效率|体验)",
        r"(重构|简化).{0,20}(代码|架构|流程)",
    ]

    def __init__(
        self,
        min_confidence: float = 0.5,
        enable_multi_detection: bool = True,
    ) -> None:
        """
        初始化需求检测器

        Args:
            min_confidence: 最小置信度阈值（低于此值不返回）
            enable_multi_detection: 是否启用多需求检测
        """
        self.min_confidence = min_confidence
        self.enable_multi_detection = enable_multi_detection
        self._detected_count = 0

    def detect_from_message(
        self,
        message: str,
        context: dict[str, Any] | None = None,
    ) -> list[DetectedRequirement]:
        """
        从用户消息检测需求

        Args:
            message: 用户消息
            context: 上下文信息

        Returns:
            检测到的需求列表
        """
        requirements = []

        # 1. 关键词匹配
        keyword_matches = self._match_keywords(message)

        # 2. 正则模式匹配
        pattern_matches = self._match_patterns(message)

        # 3. 合并结果并计算置信度
        all_matches = keyword_matches + pattern_matches

        # 如果启用多需求检测，返回所有匹配
        if self.enable_multi_detection:
            for match in all_matches:
                req = self._create_requirement_from_match(
                    match, message, DetectionSource.USER_MESSAGE, context
                )
                if req.confidence >= self.min_confidence:
                    requirements.append(req)
        else:
            # 否则只返回最高置信度的匹配
            if all_matches:
                best_match = max(all_matches, key=lambda m: m.get("confidence", 0))
                req = self._create_requirement_from_match(
                    best_match, message, DetectionSource.USER_MESSAGE, context
                )
                if req.confidence >= self.min_confidence:
                    requirements.append(req)

        return requirements

    def detect_from_analysis(
        self,
        analysis_result: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> list[DetectedRequirement]:
        """
        从AI分析结果检测需求

        Args:
            analysis_result: AI分析结果（如代码审查、测试失败等）
            context: 上下文信息

        Returns:
            检测到的需求列表
        """
        requirements = []

        # 从问题列表检测
        issues = analysis_result.get("issues_found", [])
        for issue in issues:
            req = self._create_requirement_from_issue(
                issue, analysis_result, context
            )
            if req.confidence >= self.min_confidence:
                requirements.append(req)

        # 从建议列表检测
        suggestions = analysis_result.get("suggestions", [])
        for suggestion in suggestions:
            req = self._create_requirement_from_suggestion(
                suggestion, analysis_result, context
            )
            if req.confidence >= self.min_confidence:
                requirements.append(req)

        # 从经验总结检测
        lessons = analysis_result.get("lessons_learned", [])
        for lesson in lessons:
            req = self._create_requirement_from_lesson(
                lesson, analysis_result, context
            )
            if req.confidence >= self.min_confidence:
                requirements.append(req)

        return requirements

    def detect_from_code_review(
        self,
        review_result: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> list[DetectedRequirement]:
        """
        从代码审查结果检测需求

        Args:
            review_result: 代码审查结果
            context: 上下文信息

        Returns:
            检测到的需求列表
        """
        requirements = []

        # 审查问题
        issues = review_result.get("issues", [])
        for issue in issues:
            severity = issue.get("severity", "medium")
            confidence = 0.8 if severity in ["critical", "high"] else 0.6

            req_type = RequirementType.BUG_FIX if severity == "critical" else RequirementType.IMPROVEMENT

            req = DetectedRequirement(
                req_id=self._generate_req_id(),
                title=f"[代码审查] {issue.get('description', '问题')[:50]}",
                description=issue.get("description", ""),
                req_type=req_type,
                source=DetectionSource.CODE_REVIEW,
                confidence=confidence,
                original_message=str(issue),
                extracted_entities={
                    "file": issue.get("file", ""),
                    "line": issue.get("line", 0),
                    "severity": severity,
                },
                suggested_priority=self._severity_to_priority(severity),
                suggested_assignee="developer",
                context=context or {},
            )
            if req.confidence >= self.min_confidence:
                requirements.append(req)

        return requirements

    def detect_from_test_failure(
        self,
        test_result: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> list[DetectedRequirement]:
        """
        从测试失败结果检测需求

        Args:
            test_result: 测试结果
            context: 上下文信息

        Returns:
            检测到的需求列表
        """
        requirements = []

        failures = test_result.get("failures", [])
        for failure in failures:
            req = DetectedRequirement(
                req_id=self._generate_req_id(),
                title=f"[测试失败] {failure.get('test_name', '未知测试')}",
                description=failure.get("error_message", "测试失败"),
                req_type=RequirementType.BUG_FIX,
                source=DetectionSource.TEST_FAILURE,
                confidence=0.9,  # 测试失败置信度很高
                original_message=str(failure),
                extracted_entities={
                    "test_name": failure.get("test_name", ""),
                    "test_file": failure.get("test_file", ""),
                },
                suggested_priority="P0",
                suggested_assignee="developer",
                context=context or {},
            )
            requirements.append(req)

        return requirements

    # ==================== 内部方法 ====================

    def _match_keywords(self, message: str) -> list[dict[str, Any]]:
        """关键词匹配"""
        matches = []

        # 功能需求
        feature_count = sum(1 for kw in self.FEATURE_KEYWORDS if kw in message)
        if feature_count > 0:
            matches.append({
                "type": RequirementType.FEATURE,
                "confidence": min(0.5 + feature_count * 0.1, 0.9),
                "matched_keywords": [kw for kw in self.FEATURE_KEYWORDS if kw in message],
            })

        # Bug/问题
        bug_count = sum(1 for kw in self.BUG_KEYWORDS if kw in message)
        if bug_count > 0:
            matches.append({
                "type": RequirementType.BUG_FIX,
                "confidence": min(0.6 + bug_count * 0.1, 0.95),
                "matched_keywords": [kw for kw in self.BUG_KEYWORDS if kw in message],
            })

        # 改进/优化
        improvement_count = sum(1 for kw in self.IMPROVEMENT_KEYWORDS if kw in message)
        if improvement_count > 0:
            matches.append({
                "type": RequirementType.IMPROVEMENT,
                "confidence": min(0.5 + improvement_count * 0.1, 0.85),
                "matched_keywords": [kw for kw in self.IMPROVEMENT_KEYWORDS if kw in message],
            })

        # 约束
        constraint_count = sum(1 for kw in self.CONSTRAINT_KEYWORDS if kw in message)
        if constraint_count > 0:
            matches.append({
                "type": RequirementType.CONSTRAINT,
                "confidence": min(0.5 + constraint_count * 0.1, 0.8),
                "matched_keywords": [kw for kw in self.CONSTRAINT_KEYWORDS if kw in message],
            })

        # 问题咨询
        question_count = sum(1 for kw in self.QUESTION_KEYWORDS if kw in message)
        if question_count > 0:
            matches.append({
                "type": RequirementType.QUESTION,
                "confidence": min(0.4 + question_count * 0.1, 0.7),
                "matched_keywords": [kw for kw in self.QUESTION_KEYWORDS if kw in message],
            })

        # 反馈
        feedback_count = sum(1 for kw in self.FEEDBACK_KEYWORDS if kw in message)
        if feedback_count > 0:
            matches.append({
                "type": RequirementType.FEEDBACK,
                "confidence": min(0.4 + feedback_count * 0.1, 0.7),
                "matched_keywords": [kw for kw in self.FEEDBACK_KEYWORDS if kw in message],
            })

        return matches

    def _match_patterns(self, message: str) -> list[dict[str, Any]]:
        """正则模式匹配"""
        matches = []

        # 功能需求模式
        for pattern in self.FEATURE_PATTERNS:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                matches.append({
                    "type": RequirementType.FEATURE,
                    "confidence": 0.75,
                    "matched_text": match.group(0),
                    "pattern": pattern,
                })

        # Bug模式
        for pattern in self.BUG_PATTERNS:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                matches.append({
                    "type": RequirementType.BUG_FIX,
                    "confidence": 0.85,
                    "matched_text": match.group(0),
                    "pattern": pattern,
                })

        # 改进模式
        for pattern in self.IMPROVEMENT_PATTERNS:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                matches.append({
                    "type": RequirementType.IMPROVEMENT,
                    "confidence": 0.7,
                    "matched_text": match.group(0),
                    "pattern": pattern,
                })

        return matches

    def _create_requirement_from_match(
        self,
        match: dict[str, Any],
        original_message: str,
        source: DetectionSource,
        context: dict[str, Any] | None,
    ) -> DetectedRequirement:
        """从匹配结果创建需求"""
        req_type = match.get("type", RequirementType.FEATURE)
        confidence = match.get("confidence", 0.5)

        # 提取实体
        entities = {}
        if "matched_keywords" in match:
            entities["keywords"] = match["matched_keywords"]
        if "matched_text" in match:
            entities["matched_text"] = match["matched_text"]

        # 提取标题
        title = self._extract_title(original_message, req_type)

        # 确定优先级
        priority = self._determine_priority(req_type, confidence)

        # 确定负责人
        assignee = self._determine_assignee(req_type)

        return DetectedRequirement(
            req_id=self._generate_req_id(),
            title=title,
            description=original_message,
            req_type=req_type,
            source=source,
            confidence=confidence,
            original_message=original_message,
            extracted_entities=entities,
            suggested_priority=priority,
            suggested_assignee=assignee,
            context=context or {},
        )

    def _create_requirement_from_issue(
        self,
        issue: str | dict[str, Any],
        analysis_result: dict[str, Any],
        context: dict[str, Any] | None,
    ) -> DetectedRequirement:
        """从问题创建需求"""
        issue_str = str(issue) if isinstance(issue, str) else issue.get("description", str(issue))

        return DetectedRequirement(
            req_id=self._generate_req_id(),
            title=f"[问题] {issue_str[:50]}",
            description=issue_str,
            req_type=RequirementType.BUG_FIX,
            source=DetectionSource.AI_ANALYSIS,
            confidence=0.8,
            original_message=str(analysis_result),
            extracted_entities={"issue": issue},
            suggested_priority="P1",
            suggested_assignee="developer",
            context=context or {},
        )

    def _create_requirement_from_suggestion(
        self,
        suggestion: str | dict[str, Any],
        analysis_result: dict[str, Any],
        context: dict[str, Any] | None,
    ) -> DetectedRequirement:
        """从建议创建需求"""
        sug_str = str(suggestion) if isinstance(suggestion, str) else suggestion.get("description", str(suggestion))

        return DetectedRequirement(
            req_id=self._generate_req_id(),
            title=f"[改进建议] {sug_str[:50]}",
            description=sug_str,
            req_type=RequirementType.IMPROVEMENT,
            source=DetectionSource.AI_ANALYSIS,
            confidence=0.7,
            original_message=str(analysis_result),
            extracted_entities={"suggestion": suggestion},
            suggested_priority="P2",
            suggested_assignee="developer",
            context=context or {},
        )

    def _create_requirement_from_lesson(
        self,
        lesson: str | dict[str, Any],
        analysis_result: dict[str, Any],
        context: dict[str, Any] | None,
    ) -> DetectedRequirement:
        """从经验总结创建需求"""
        lesson_str = str(lesson) if isinstance(lesson, str) else lesson.get("description", str(lesson))

        return DetectedRequirement(
            req_id=self._generate_req_id(),
            title=f"[经验总结] {lesson_str[:50]}",
            description=lesson_str,
            req_type=RequirementType.IMPROVEMENT,
            source=DetectionSource.EXPERIENCE,
            confidence=0.6,
            original_message=str(analysis_result),
            extracted_entities={"lesson": lesson},
            suggested_priority="P3",
            suggested_assignee="architect",
            context=context or {},
        )

    def _generate_req_id(self) -> str:
        """生成需求ID（使用UUID确保唯一性）"""
        return f"REQ-{uuid.uuid4().hex[:8].upper()}"

    def _extract_title(self, message: str, req_type: RequirementType) -> str:
        """提取需求标题"""
        # 截取前50字符作为标题
        title = message[:50]
        if len(message) > 50:
            title += "..."

        # 根据类型添加前缀
        prefixes = {
            RequirementType.FEATURE: "[功能]",
            RequirementType.BUG_FIX: "[Bug]",
            RequirementType.IMPROVEMENT: "[改进]",
            RequirementType.CONSTRAINT: "[约束]",
            RequirementType.QUESTION: "[咨询]",
            RequirementType.FEEDBACK: "[反馈]",
        }

        return prefixes.get(req_type, "") + title

    def _determine_priority(self, req_type: RequirementType, confidence: float) -> str:
        """确定优先级"""
        if req_type == RequirementType.BUG_FIX and confidence >= 0.8:
            return "P0"
        elif req_type == RequirementType.BUG_FIX:
            return "P1"
        elif req_type == RequirementType.FEATURE and confidence >= 0.7:
            return "P1"
        elif req_type == RequirementType.FEATURE:
            return "P2"
        elif req_type == RequirementType.IMPROVEMENT:
            return "P2"
        else:
            return "P3"

    def _determine_assignee(self, req_type: RequirementType) -> str:
        """确定负责人"""
        assigns = {
            RequirementType.FEATURE: "developer",
            RequirementType.BUG_FIX: "developer",
            RequirementType.IMPROVEMENT: "developer",
            RequirementType.CONSTRAINT: "architect",
            RequirementType.QUESTION: "project_manager",
            RequirementType.FEEDBACK: "product_manager",
        }
        return assigns.get(req_type, "developer")

    def _severity_to_priority(self, severity: str) -> str:
        """将严重程度映射到优先级"""
        mapping = {
            "critical": "P0",
            "high": "P1",
            "medium": "P2",
            "low": "P3",
        }
        return mapping.get(severity, "P2")


def create_detector(
    min_confidence: float = 0.5,
    enable_multi_detection: bool = True,
) -> RequirementDetector:
    """创建需求检测器"""
    return RequirementDetector(
        min_confidence=min_confidence,
        enable_multi_detection=enable_multi_detection,
    )