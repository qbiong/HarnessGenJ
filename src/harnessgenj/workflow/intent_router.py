"""
Intent Router - 意图识别与工作流路由

负责：
1. 识别用户意图类型
2. 提取关键实体
3. 路由到对应的工作流

意图类型：
- development: 功能开发（涉及代码变更）
- bugfix: Bug修复（涉及代码变更）
- inquiry: 问题咨询（无代码变更）
- management: 项目管理（无代码变更）
"""

from typing import Any
from pydantic import BaseModel, Field
from enum import Enum
import re


class IntentType(Enum):
    """意图类型"""

    DEVELOPMENT = "development"      # 功能开发
    BUGFIX = "bugfix"               # Bug修复
    INQUIRY = "inquiry"             # 问题咨询
    MANAGEMENT = "management"        # 项目管理
    UNKNOWN = "unknown"             # 未知


class IntentConfidence(Enum):
    """意图置信度"""

    HIGH = "high"       # 高置信度 (> 0.8)
    MEDIUM = "medium"   # 中置信度 (0.5 - 0.8)
    LOW = "low"         # 低置信度 (< 0.5)


class IntentPattern(BaseModel):
    """意图匹配模式"""

    keywords: list[str] = Field(default_factory=list, description="关键词列表")
    patterns: list[str] = Field(default_factory=list, description="正则模式列表")
    weight: float = Field(default=1.0, description="权重")
    exclude_keywords: list[str] = Field(default_factory=list, description="排除关键词")


class ExtractedEntity(BaseModel):
    """提取的实体"""

    name: str = Field(..., description="实体名称")
    value: str = Field(..., description="实体值")
    confidence: float = Field(default=1.0, description="置信度")


class IntentResult(BaseModel):
    """意图识别结果"""

    intent_type: IntentType = Field(..., description="意图类型")
    confidence: float = Field(default=0.0, description="置信度 (0-1)")
    entities: list[ExtractedEntity] = Field(default_factory=list, description="提取的实体")
    target_workflow: str = Field(default="", description="目标工作流")
    priority: str = Field(default="P2", description="建议优先级")
    reason: str = Field(default="", description="识别原因")
    original_message: str = Field(default="", description="原始消息")


class IntentRouter:
    """
    意图识别路由器

    通过多模式匹配识别用户意图：
    1. 关键词匹配
    2. 正则表达式匹配
    3. 语义特征分析
    """

    # 意图匹配规则
    INTENT_PATTERNS: dict[IntentType, IntentPattern] = {
        IntentType.DEVELOPMENT: IntentPattern(
            keywords=[
                "需要", "要", "添加", "新增", "开发", "实现", "功能",
                "做一个", "帮我写", "编写", "创建", "构建",
                "增加", "扩展", "改进", "优化",
            ],
            patterns=[
                r"(需要|要)(开发|实现|添加|新增|创建).{0,20}功能",
                r"帮我(开发|写|实现|做)",
                r"(实现|开发|编写).{0,20}(功能|模块|组件)",
                r"(添加|新增).{0,20}(功能|特性|模块)",
            ],
            weight=1.0,
            exclude_keywords=["bug", "问题", "错误", "报错"],
        ),
        IntentType.BUGFIX: IntentPattern(
            keywords=[
                "bug", "问题", "错误", "异常", "报错", "崩溃",
                "无法", "不能", "不工作", "失败", "闪退",
                "修复", "改正", "解决",
                "没有正确", "不正确", "不对", "缺少",
            ],
            patterns=[
                r"(有|发现|遇到).{0,10}(bug|问题|错误|异常)",
                r"(无法|不能).{0,20}(使用|工作|运行|切换)",
                r".{0,20}(报错|报异常|崩溃|闪退)",
                r"(修复|解决).{0,20}(bug|问题|错误)",
                r"(不工作|不能用|不好使)",
                r"AI.{0,10}(无法|不能|不).{0,10}(理解|识别|判别)",
                r"(没有|未).{0,10}(正确|正常|成功)",
                r".{0,20}(没有|未)(正确|正常).{0,10}(更新|显示|执行)",
            ],
            weight=1.0,
            exclude_keywords=[],
        ),
        IntentType.INQUIRY: IntentPattern(
            keywords=[
                "什么是", "为什么", "怎么", "如何", "什么",
                "能不能", "是否", "有没有", "支持吗",
                "解释", "说明", "介绍",
            ],
            patterns=[
                r"^(什么|为什么|怎么|如何)",
                r"(能不能|是否|有没有).{0,20}\?",
                r"(解释|说明|介绍一下)",
            ],
            weight=0.8,
            exclude_keywords=["需要", "开发", "实现"],
        ),
        IntentType.MANAGEMENT: IntentPattern(
            keywords=[
                "进度", "状态", "报告", "统计",
                "规划", "计划", "安排", "调整",
                "团队", "人员", "资源",
            ],
            patterns=[
                r"(项目|当前).{0,10}(进度|状态)",
                r"(生成|查看).{0,10}(报告|统计)",
                r"(规划|计划|安排)",
            ],
            weight=0.8,
            exclude_keywords=[],
        ),
    }

    # 优先级映射
    PRIORITY_MAP = {
        IntentType.BUGFIX: "P0",
        IntentType.DEVELOPMENT: "P1",
        IntentType.INQUIRY: "P2",
        IntentType.MANAGEMENT: "P2",
        IntentType.UNKNOWN: "P2",
    }

    # 工作流映射
    WORKFLOW_MAP = {
        IntentType.DEVELOPMENT: "development_pipeline",
        IntentType.BUGFIX: "bugfix_pipeline",
        IntentType.INQUIRY: "inquiry_pipeline",
        IntentType.MANAGEMENT: "management_pipeline",
        IntentType.UNKNOWN: "inquiry_pipeline",
    }

    def __init__(self) -> None:
        self._compiled_patterns: dict[IntentType, list[re.Pattern]] = {}
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """预编译正则表达式"""
        for intent_type, pattern in self.INTENT_PATTERNS.items():
            self._compiled_patterns[intent_type] = [
                re.compile(p, re.IGNORECASE) for p in pattern.patterns
            ]

    def identify(self, message: str) -> IntentResult:
        """
        识别用户意图

        Args:
            message: 用户消息

        Returns:
            IntentResult: 识别结果
        """
        scores: dict[IntentType, float] = {}
        matched_reasons: dict[IntentType, list[str]] = {}

        for intent_type, pattern in self.INTENT_PATTERNS.items():
            score = 0.0
            reasons = []

            # 检查排除关键词
            if any(kw in message for kw in pattern.exclude_keywords):
                continue

            # 关键词匹配
            keyword_matches = sum(1 for kw in pattern.keywords if kw in message)
            if keyword_matches > 0:
                score += min(keyword_matches * 0.3, 0.6) * pattern.weight
                matched_keywords = [kw for kw in pattern.keywords if kw in message]
                reasons.append(f"关键词匹配: {', '.join(matched_keywords[:3])}")

            # 正则模式匹配
            compiled_patterns = self._compiled_patterns.get(intent_type, [])
            pattern_matches = 0
            for compiled in compiled_patterns:
                if compiled.search(message):
                    pattern_matches += 1

            if pattern_matches > 0:
                score += min(pattern_matches * 0.4, 0.4) * pattern.weight
                reasons.append(f"模式匹配: {pattern_matches} 个")

            scores[intent_type] = min(score, 1.0)
            matched_reasons[intent_type] = reasons

        # 选择最高分的意图
        if not scores:
            best_intent = IntentType.UNKNOWN
            best_score = 0.0
        else:
            best_intent = max(scores, key=scores.get)
            best_score = scores[best_intent]

        # 提取实体
        entities = self._extract_entities(message, best_intent)

        return IntentResult(
            intent_type=best_intent,
            confidence=best_score,
            entities=entities,
            target_workflow=self.WORKFLOW_MAP[best_intent],
            priority=self.PRIORITY_MAP[best_intent],
            reason="; ".join(matched_reasons.get(best_intent, ["默认匹配"])),
            original_message=message,
        )

    def _extract_entities(self, message: str, intent_type: IntentType) -> list[ExtractedEntity]:
        """提取实体"""
        entities = []

        # 提取功能名
        feature_patterns = [
            r"(实现|开发|添加|新增).{0,5}([^\s,，。！？]{2,10})(功能|模块|组件)",
            r"([^\s,，。！？]{2,10})(功能|模块)",
        ]
        for pattern in feature_patterns:
            match = re.search(pattern, message)
            if match:
                feature_name = match.group(2) if len(match.groups()) >= 2 else match.group(1)
                entities.append(ExtractedEntity(
                    name="feature_name",
                    value=feature_name,
                    confidence=0.8,
                ))
                break

        # 提取模块名
        module_patterns = [
            r"在.{0,5}([^\s,，。！？]{2,10})(模块|组件|页面)中",
            r"([^\s,，。！？]{2,10})(模块|组件|页面).{0,5}(的|中)",
        ]
        for pattern in module_patterns:
            match = re.search(pattern, message)
            if match:
                entities.append(ExtractedEntity(
                    name="module_name",
                    value=match.group(1),
                    confidence=0.7,
                ))
                break

        # 提取问题描述
        if intent_type == IntentType.BUGFIX:
            issue_patterns = [
                r"(无法|不能|不).{0,20}",
                r"(报错|错误|异常).{0,20}",
                r"(问题|bug).{0,20}",
            ]
            for pattern in issue_patterns:
                match = re.search(pattern, message)
                if match:
                    entities.append(ExtractedEntity(
                        name="issue_description",
                        value=match.group(0),
                        confidence=0.8,
                    ))
                    break

        return entities

    def get_supported_intents(self) -> list[str]:
        """获取支持的意图类型"""
        return [intent.value for intent in IntentType if intent != IntentType.UNKNOWN]

    def get_intent_description(self, intent_type: IntentType) -> str:
        """获取意图描述"""
        descriptions = {
            IntentType.DEVELOPMENT: "功能开发 - 新增或修改功能代码",
            IntentType.BUGFIX: "Bug修复 - 修复代码缺陷或问题",
            IntentType.INQUIRY: "问题咨询 - 了解项目信息或技术方案",
            IntentType.MANAGEMENT: "项目管理 - 进度追踪、资源调配等",
            IntentType.UNKNOWN: "未知意图 - 需要进一步确认",
        }
        return descriptions.get(intent_type, "未知意图")


# ==================== 便捷函数 ====================

def create_intent_router() -> IntentRouter:
    """创建意图识别路由器"""
    return IntentRouter()


def identify_intent(message: str) -> IntentResult:
    """快速识别意图"""
    router = create_intent_router()
    return router.identify(message)