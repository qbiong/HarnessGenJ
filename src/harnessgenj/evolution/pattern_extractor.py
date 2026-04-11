"""
Pattern Extractor - 模式提取器

从成功解决方案中提取可复用模式：
1. 分析对抗审查通过的记录
2. 提取代码结构、决策流程、错误处理模式
3. 生成可复用的模式定义
4. 验证模式有效性

使用示例:
    from harnessgenj.evolution.pattern_extractor import PatternExtractor, PatternType

    extractor = PatternExtractor()

    # 从成功记录提取模式
    patterns = extractor.extract_from_success_records(passed_records)

    # 验证模式
    result = extractor.validate_pattern(patterns[0], test_cases)

    # 生成技能定义
    skill_def = extractor.generate_skill_definition(patterns[0])
"""

from typing import Any, Optional
from pydantic import BaseModel, Field
from enum import Enum
import time
import re
import json
from pathlib import Path


class PatternType(str, Enum):
    """模式类型"""

    CODE_TEMPLATE = "code_template"      # 代码模板
    DECISION_FLOW = "decision_flow"      # 决策流程
    ERROR_HANDLING = "error_handling"    # 错误处理
    OPTIMIZATION = "optimization"        # 优化策略
    TESTING = "testing"                  # 测试模式
    SECURITY = "security"                # 安全模式
    ARCHITECTURE = "architecture"        # 架构模式


class CodeLocation(BaseModel):
    """代码位置"""

    file_path: str = Field(..., description="文件路径")
    line_start: int = Field(default=0, description="起始行")
    line_end: int = Field(default=0, description="结束行")
    function_name: Optional[str] = Field(default=None, description="函数名")


class ExtractedPattern(BaseModel):
    """提取的模式"""

    pattern_id: str = Field(..., description="模式ID")
    pattern_type: PatternType = Field(default=PatternType.CODE_TEMPLATE, description="模式类型")
    name: str = Field(..., description="模式名称")
    description: str = Field(default="", description="模式描述")
    trigger_conditions: list[str] = Field(default_factory=list, description="触发条件")
    solution_template: str = Field(default="", description="解决方案模板")
    context_requirements: list[str] = Field(default_factory=list, description="所需上下文")
    success_rate: float = Field(default=0.0, description="成功率")
    sample_count: int = Field(default=0, description="样本数量")
    quality_score: float = Field(default=0.0, description="质量分数")
    code_locations: list[CodeLocation] = Field(default_factory=list, description="相关代码位置")
    tags: list[str] = Field(default_factory=list, description="标签")
    created_at: float = Field(default_factory=time.time, description="创建时间")
    verified: bool = Field(default=False, description="是否已验证")
    metadata: dict[str, Any] = Field(default_factory=dict, description="额外元数据")


class PatternValidationResult(BaseModel):
    """模式验证结果"""

    pattern_id: str = Field(..., description="模式ID")
    is_valid: bool = Field(default=False, description="是否有效")
    validation_score: float = Field(default=0.0, description="验证分数")
    test_cases_passed: int = Field(default=0, description="通过的测试用例数")
    test_cases_total: int = Field(default=0, description="总测试用例数")
    issues: list[str] = Field(default_factory=list, description="发现的问题")
    suggestions: list[str] = Field(default_factory=list, description="改进建议")


class PatternExtractorConfig(BaseModel):
    """模式提取器配置"""

    min_sample_count: int = Field(default=3, description="最小样本数量")
    min_success_rate: float = Field(default=0.7, description="最小成功率")
    min_quality_score: float = Field(default=70.0, description="最小质量分数")
    max_patterns_per_type: int = Field(default=10, description="每类型最大模式数")
    auto_verify: bool = Field(default=False, description="自动验证")


class PatternExtractor:
    """
    模式提取器

    功能：
    1. 从成功记录提取模式
    2. 跨任务模式分析
    3. 生成技能定义
    4. 模式验证

    支持多种模式类型，自动分类和索引。
    """

    def __init__(
        self,
        storage_path: Optional[str] = None,
        config: Optional[PatternExtractorConfig] = None,
        quality_tracker: Optional[Any] = None,
    ):
        """
        初始化模式提取器

        Args:
            storage_path: 存储路径
            config: 提取器配置
            quality_tracker: 质量追踪器
        """
        self._storage_path = Path(storage_path or ".harnessgenj/patterns")
        self._config = config or PatternExtractorConfig()
        self._quality_tracker = quality_tracker

        # 模式存储
        self._patterns: dict[str, ExtractedPattern] = {}
        self._pattern_index: dict[PatternType, list[str]] = {}

        # 加载已有模式
        self._load()

    def extract_from_success_records(
        self,
        records: list[dict[str, Any]],
    ) -> list[ExtractedPattern]:
        """
        从成功记录提取模式

        Args:
            records: 对抗审查通过的记录列表

        Returns:
            提取的模式列表
        """
        patterns: list[ExtractedPattern] = []

        for record in records:
            # 分析解决方案
            solution = record.get("generator_output", {})
            task_type = record.get("task_type", "unknown")
            quality_score = record.get("quality_score", 0)

            # 提取模式特征
            extracted = self._analyze_solution(solution, task_type, quality_score)

            if extracted:
                # 检查是否已有类似模式
                similar = self._find_similar_pattern(extracted)
                if similar:
                    # 合入已有模式
                    similar.sample_count += 1
                    similar.success_rate = self._update_rate(similar.success_rate, True)
                    similar.quality_score = (similar.quality_score + quality_score) / 2
                else:
                    # 创建新模式
                    extracted.pattern_id = self._generate_pattern_id()
                    extracted.sample_count = 1
                    extracted.success_rate = 1.0
                    extracted.quality_score = quality_score
                    patterns.append(extracted)
                    self._patterns[extracted.pattern_id] = extracted

        # 持久化
        self._persist()

        return patterns

    def analyze_cross_task_patterns(
        self,
        task_history: list[dict[str, Any]],
    ) -> list[ExtractedPattern]:
        """
        跨任务模式分析

        分析历史任务记录，挖掘最佳实践。

        Args:
            task_history: 任务历史记录

        Returns:
            提取的模式列表
        """
        patterns: list[ExtractedPattern] = []

        # 按类型分组
        type_groups: dict[str, list[dict]] = {}
        for task in task_history:
            task_type = task.get("task_type", "unknown")
            if task_type not in type_groups:
                type_groups[task_type] = []
            type_groups[task_type].append(task)

        # 分析每类任务
        for task_type, tasks in type_groups.items():
            if len(tasks) >= self._config.min_sample_count:
                # 提取共同模式
                common_patterns = self._extract_common_patterns(tasks)
                for pattern in common_patterns:
                    pattern.pattern_type = self._determine_pattern_type(task_type)
                    patterns.append(pattern)

        return patterns

    def generate_skill_definition(
        self,
        pattern: ExtractedPattern,
    ) -> dict[str, Any]:
        """
        从模式生成技能定义

        Args:
            pattern: 提取的模式

        Returns:
            技能定义字典
        """
        skill_def = {
            "skill_id": f"skill-{pattern.pattern_id}",
            "skill_name": pattern.name,
            "skill_type": self._determine_skill_type(pattern.pattern_type),
            "applicable_roles": self._determine_applicable_roles(pattern.pattern_type),
            "trigger_conditions": pattern.trigger_conditions,
            "execution_template": pattern.solution_template,
            "context_requirements": pattern.context_requirements,
            "quality_threshold": self._config.min_quality_score,
            "success_rate": pattern.success_rate,
            "source_pattern_id": pattern.pattern_id,
            "verified": pattern.verified,
            "tags": pattern.tags,
            "created_at": time.time(),
        }

        return skill_def

    def validate_pattern(
        self,
        pattern: ExtractedPattern,
        test_cases: Optional[list[dict[str, Any]]] = None,
    ) -> PatternValidationResult:
        """
        验证模式有效性

        Args:
            pattern: 待验证的模式
            test_cases: 测试用例（可选）

        Returns:
            验证结果
        """
        result = PatternValidationResult(
            pattern_id=pattern.pattern_id,
            test_cases_total=len(test_cases or []),
        )

        # 检查基本指标
        if pattern.sample_count < self._config.min_sample_count:
            result.issues.append(f"样本数量不足: {pattern.sample_count} < {self._config.min_sample_count}")
            result.is_valid = False
            return result

        if pattern.success_rate < self._config.min_success_rate:
            result.issues.append(f"成功率不足: {pattern.success_rate:.2f} < {self._config.min_success_rate}")
            result.is_valid = False
            return result

        if pattern.quality_score < self._config.min_quality_score:
            result.issues.append(f"质量分数不足: {pattern.quality_score:.1f} < {self._config.min_quality_score}")
            result.is_valid = False
            return result

        # 检查模板完整性
        if not pattern.solution_template:
            result.issues.append("解决方案模板为空")
            result.is_valid = False
            return result

        if not pattern.trigger_conditions:
            result.issues.append("触发条件为空")
            result.is_valid = False
            return result

        # 运行测试用例
        if test_cases:
            passed = 0
            for case in test_cases:
                if self._run_test_case(pattern, case):
                    passed += 1
            result.test_cases_passed = passed
            result.test_cases_total = len(test_cases)

            if passed < len(test_cases) * 0.8:
                result.issues.append(f"测试通过率不足: {passed}/{len(test_cases)}")

        # 计算验证分数
        result.validation_score = self._calculate_validation_score(pattern, result)
        result.is_valid = result.validation_score >= 0.7

        # 更新模式验证状态
        if result.is_valid:
            pattern.verified = True
            self._persist()

        return result

    def get_patterns_by_type(
        self,
        pattern_type: PatternType,
    ) -> list[ExtractedPattern]:
        """获取指定类型的模式"""
        pattern_ids = self._pattern_index.get(pattern_type, [])
        return [self._patterns[id] for id in pattern_ids if id in self._patterns]

    def get_pattern(self, pattern_id: str) -> Optional[ExtractedPattern]:
        """获取指定模式"""
        return self._patterns.get(pattern_id)

    def get_verified_patterns(self) -> list[ExtractedPattern]:
        """获取已验证的模式"""
        return [p for p in self._patterns.values() if p.verified]

    def get_high_quality_patterns(
        self,
        min_score: float = 80.0,
    ) -> list[ExtractedPattern]:
        """获取高质量模式"""
        return [p for p in self._patterns.values() if p.quality_score >= min_score]

    def _analyze_solution(
        self,
        solution: dict[str, Any],
        task_type: str,
        quality_score: float,
    ) -> Optional[ExtractedPattern]:
        """分析解决方案提取模式"""
        code = solution.get("code", "")
        decisions = solution.get("decisions", [])
        error_handling = solution.get("error_handling", [])

        # 提取关键特征
        features = self._extract_features(code, decisions, error_handling)

        if not features:
            return None

        # 确定模式类型
        pattern_type = self._determine_pattern_type(task_type)

        # 生成模式定义
        pattern = ExtractedPattern(
            name=self._generate_pattern_name(features, task_type),
            pattern_type=pattern_type,
            description=self._generate_description(features),
            trigger_conditions=self._extract_trigger_conditions(features),
            solution_template=self._generate_template(features, code),
            context_requirements=self._extract_context_requirements(features),
            quality_score=quality_score,
            tags=self._extract_tags(features, task_type),
        )

        return pattern

    def _extract_features(
        self,
        code: str,
        decisions: list,
        error_handling: list,
    ) -> dict[str, Any]:
        """提取代码特征"""
        features: dict[str, Any] = {}

        # 代码结构特征
        if code:
            # 提取函数签名
            func_pattern = r"def\s+(\w+)\s*\(([^)]*)\)"
            funcs = re.findall(func_pattern, code)
            features["functions"] = funcs

            # 提取类定义
            class_pattern = r"class\s+(\w+)\s*[:\(]"
            classes = re.findall(class_pattern, code)
            features["classes"] = classes

            # 提取导入
            import_pattern = r"import\s+(\w+)|from\s+(\w+)\s+import"
            imports = re.findall(import_pattern, code)
            features["imports"] = [i[0] or i[1] for i in imports]

            # 提取异常处理
            try_pattern = r"try\s*:[\s\S]*?except\s*(\w+)"
            exceptions = re.findall(try_pattern, code)
            features["exceptions"] = exceptions

        # 决策流程
        if decisions:
            features["decisions"] = decisions

        # 错误处理模式
        if error_handling:
            features["error_handling"] = error_handling

        return features if features else None

    def _determine_pattern_type(self, task_type: str) -> PatternType:
        """确定模式类型"""
        type_map = {
            "bug": PatternType.ERROR_HANDLING,
            "feature": PatternType.CODE_TEMPLATE,
            "refactor": PatternType.OPTIMIZATION,
            "test": PatternType.TESTING,
            "security": PatternType.SECURITY,
            "architecture": PatternType.ARCHITECTURE,
        }
        return type_map.get(task_type, PatternType.CODE_TEMPLATE)

    def _determine_skill_type(self, pattern_type: PatternType) -> str:
        """确定技能类型"""
        discriminator_types = [PatternType.TESTING, PatternType.SECURITY]
        if pattern_type in discriminator_types:
            return "discriminator"
        return "generator"

    def _determine_applicable_roles(self, pattern_type: PatternType) -> list[str]:
        """确定适用角色"""
        role_map = {
            PatternType.CODE_TEMPLATE: ["developer", "architect"],
            PatternType.DECISION_FLOW: ["developer", "architect", "product_manager"],
            PatternType.ERROR_HANDLING: ["developer", "bug_hunter"],
            PatternType.OPTIMIZATION: ["developer", "architect"],
            PatternType.TESTING: ["tester", "developer"],
            PatternType.SECURITY: ["bug_hunter", "developer"],
            PatternType.ARCHITECTURE: ["architect", "developer"],
        }
        return role_map.get(pattern_type, ["developer"])

    def _find_similar_pattern(self, pattern: ExtractedPattern) -> Optional[ExtractedPattern]:
        """查找类似模式"""
        for existing in self._patterns.values():
            if existing.pattern_type == pattern.pattern_type:
                # 检查触发条件相似度
                common_conditions = set(existing.trigger_conditions) & set(pattern.trigger_conditions)
                if len(common_conditions) >= 2:
                    return existing
        return None

    def _generate_pattern_id(self) -> str:
        """生成模式ID"""
        return f"pattern-{int(time.time() * 1000)}-{len(self._patterns) + 1}"

    def _generate_pattern_name(self, features: dict, task_type: str) -> str:
        """生成模式名称"""
        if "functions" in features and features["functions"]:
            func_name = features["functions"][0][0]
            return f"{task_type}_{func_name}_pattern"
        return f"{task_type}_solution_pattern"

    def _generate_description(self, features: dict) -> str:
        """生成模式描述"""
        parts = []
        if "functions" in features:
            parts.append(f"函数: {', '.join(f[0] for f in features['functions'][:3])}")
        if "exceptions" in features:
            parts.append(f"异常处理: {', '.join(features['exceptions'][:3])}")
        return " | ".join(parts) if parts else "通用解决方案模式"

    def _extract_trigger_conditions(self, features: dict) -> list[str]:
        """提取触发条件"""
        conditions = []
        if "exceptions" in features:
            for exc in features["exceptions"]:
                conditions.append(f"遇到 {exc} 异常")
        if "imports" in features:
            for imp in features["imports"][:2]:
                conditions.append(f"使用 {imp} 模块")
        return conditions if conditions else ["通用开发场景"]

    def _generate_template(self, features: dict, code: str) -> str:
        """生成解决方案模板"""
        if code:
            # 简化模板：提取核心结构
            lines = code.split("\n")
            template_lines = []
            for line in lines[:20]:  # 取前20行
                # 替换具体值为占位符
                template_line = re.sub(r"'[^']*'", "'{value}'", line)
                template_line = re.sub(r'"[^"]*"', '"{value}"', template_line)
                template_line = re.sub(r"\b\d+\b", "{number}", template_line)
                template_lines.append(template_line)
            return "\n".join(template_lines)
        return "# 解决方案模板待填充"

    def _extract_context_requirements(self, features: dict) -> list[str]:
        """提取上下文要求"""
        requirements = []
        if "imports" in features:
            requirements.append("需要导入相关模块")
        if "classes" in features:
            requirements.append("需要了解相关类定义")
        return requirements

    def _extract_tags(self, features: dict, task_type: str) -> list[str]:
        """提取标签"""
        tags = [task_type]
        if "exceptions" in features:
            tags.append("error-handling")
        if "imports" in features:
            tags.extend(features["imports"][:2])
        return tags

    def _extract_common_patterns(self, tasks: list[dict]) -> list[ExtractedPattern]:
        """提取共同模式"""
        patterns = []
        # 分析共同决策
        decisions = [t.get("decisions", []) for t in tasks]
        common_decisions = self._find_common_items(decisions)

        if common_decisions:
            pattern = ExtractedPattern(
                name=f"common_{tasks[0].get('task_type', 'unknown')}_pattern",
                pattern_type=PatternType.DECISION_FLOW,
                description="跨任务共同决策模式",
                trigger_conditions=[f"处理 {tasks[0].get('task_type', 'unknown')} 类型任务"],
                solution_template=json.dumps(common_decisions, indent=2),
            )
            patterns.append(pattern)

        return patterns

    def _find_common_items(self, items_list: list[list]) -> list:
        """找出共同项"""
        if not items_list or not items_list[0]:
            return []

        common = set(items_list[0])
        for items in items_list[1:]:
            common &= set(items)
        return list(common)

    def _update_rate(self, current: float, success: bool) -> float:
        """更新成功率（加权平均）"""
        if success:
            return current * 0.9 + 0.1
        else:
            return current * 0.9

    def _run_test_case(self, pattern: ExtractedPattern, case: dict) -> bool:
        """运行测试用例"""
        # 简化实现：检查模板是否匹配
        context = case.get("context", "")
        expected = case.get("expected", "")

        # 检查触发条件
        triggered = False
        for condition in pattern.trigger_conditions:
            if condition.lower() in context.lower():
                triggered = True
                break

        return triggered

    def _calculate_validation_score(
        self,
        pattern: ExtractedPattern,
        result: PatternValidationResult,
    ) -> float:
        """计算验证分数"""
        score = 0.0

        # 基本指标分数 (0-40)
        if pattern.sample_count >= self._config.min_sample_count:
            score += 10
        if pattern.success_rate >= self._config.min_success_rate:
            score += 15
        if pattern.quality_score >= self._config.min_quality_score:
            score += 15

        # 完整性分数 (0-30)
        if pattern.solution_template:
            score += 10
        if pattern.trigger_conditions:
            score += 10
        if pattern.context_requirements:
            score += 10

        # 测试通过分数 (0-30)
        if result.test_cases_total > 0:
            pass_rate = result.test_cases_passed / result.test_cases_total
            score += pass_rate * 30

        return score / 100

    def _persist(self) -> None:
        """持久化存储"""
        self._storage_path.mkdir(parents=True, exist_ok=True)
        file_path = self._storage_path / "patterns.json"

        data = {
            "patterns": {id: p.model_dump() for id, p in self._patterns.items()},
            "index": {t.name: ids for t, ids in self._pattern_index.items()},
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load(self) -> None:
        """加载已有模式"""
        file_path = self._storage_path / "patterns.json"

        if not file_path.exists():
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for id, pattern_data in data.get("patterns", {}).items():
                self._patterns[id] = ExtractedPattern(**pattern_data)

            for type_name, ids in data.get("index", {}).items():
                self._pattern_index[PatternType(type_name)] = ids

        except (json.JSONDecodeError, KeyError, ValueError):
            pass


def create_pattern_extractor(
    storage_path: Optional[str] = None,
    **kwargs: Any,
) -> PatternExtractor:
    """创建模式提取器"""
    return PatternExtractor(storage_path, **kwargs)