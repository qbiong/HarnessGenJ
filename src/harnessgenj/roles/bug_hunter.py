"""
Bug Hunter Role - 漏洞猎手角色（激进判别器）

职责：
- 深度测试
- 边界探索
- 异常场景构造
- 性能压力测试

特点：
- 激进的测试策略
- 关注容易被忽略的边界
- 模拟恶意输入
- 目标是"打破"代码

对抗机制：
- 发现隐藏Bug高分
- 使用多种攻击策略
- 模拟真实攻击者思维
"""

from typing import Any
from pydantic import BaseModel, Field
import time
import re

from harnessgenj.roles.base import (
    AgentRole,
    RoleType,
    RoleSkill,
    RoleContext,
    SkillCategory,
    TaskType,
)
from harnessgenj.quality.record import IssueRecord, IssueSeverity, create_issue


class HuntResult(BaseModel):
    """漏洞猎取结果"""
    vulnerabilities: list[IssueRecord] = Field(default_factory=list, description="发现的漏洞")
    attack_surface: dict[str, Any] = Field(default_factory=dict, description="攻击面分析")
    risk_score: float = Field(default=0.0, description="风险分数")
    report: str = Field(default="", description="漏洞报告")


class BugHunter(AgentRole):
    """
    漏洞猎手 - 激进的判别器角色

    与普通审查者不同，BugHunter 采用激进策略：
    - 假设代码有漏洞，目标是找到它
    - 使用多种攻击策略
    - 关注边界和异常场景
    - 模拟恶意用户行为

    对抗机制：
    - 发现隐藏Bug → 高分奖励
    - 发现高危漏洞 → 更高分
    - 漏掉真实漏洞 → 重罚
    """

    # 攻击策略
    HUNT_STRATEGIES = {
        "boundary_attack": {
            "name": "边界攻击",
            "description": "测试边界条件和极限值",
            "priority": 1,
        },
        "fuzzing": {
            "name": "模糊测试",
            "description": "使用随机和异常输入",
            "priority": 2,
        },
        "edge_case": {
            "name": "边缘情况",
            "description": "测试罕见但可能的场景",
            "priority": 3,
        },
        "negative_test": {
            "name": "负面测试",
            "description": "测试错误和失败路径",
            "priority": 4,
        },
        "stress_test": {
            "name": "压力测试",
            "description": "测试高负载和资源限制",
            "priority": 5,
        },
        "security_probe": {
            "name": "安全探测",
            "description": "模拟安全攻击",
            "priority": 6,
        },
    }

    # 边界值测试用例
    BOUNDARY_VALUES = {
        "integer": [0, -1, 1, -2147483648, 2147483647, None],
        "string": ["", "a", " " * 1000, "<script>", "'; DROP TABLE--", None],
        "list": [[], [1], [1] * 10000, None],
        "float": [0.0, -0.0, 3.14159, float('inf'), float('-inf'), float('nan'), None],
    }

    # 安全攻击模式
    SECURITY_PATTERNS = {
        "sql_injection": {
            "patterns": [
                (r"['\"]\s*(OR|AND)\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+", "SQL注入点"),
                (r";\s*(DROP|DELETE|UPDATE|INSERT)", "SQL命令注入"),
                (r"UNION\s+SELECT", "UNION注入"),
            ],
            "severity": IssueSeverity.CRITICAL,
        },
        "xss": {
            "patterns": [
                (r"<script[^>]*>", "XSS脚本标签"),
                (r"javascript:", "JavaScript协议"),
                (r"on(error|load|click)\s*=", "事件处理器注入"),
            ],
            "severity": IssueSeverity.CRITICAL,
        },
        "path_traversal": {
            "patterns": [
                (r"\.\./", "路径遍历"),
                (r"\.\.\\", "Windows路径遍历"),
            ],
            "severity": IssueSeverity.CRITICAL,
        },
        "command_injection": {
            "patterns": [
                (r";\s*(rm|del|format|shutdown)", "命令注入"),
                (r"\|\s*(bash|sh|cmd)", "管道命令注入"),
                (r"`[^`]+`", "命令替换"),
            ],
            "severity": IssueSeverity.CRITICAL,
        },
        "ssrf": {
            "patterns": [
                (r"https?://(?!(localhost|127\.0\.0\.1))", "外部URL访问"),
                (r"file://", "本地文件访问"),
            ],
            "severity": IssueSeverity.MAJOR,
        },
    }

    def __init__(
        self,
        role_id: str = "hunter_1",
        name: str = "漏洞猎手",
        context: RoleContext | None = None,
    ) -> None:
        super().__init__(role_id=role_id, name=name, context=context)
        self._last_hunt: HuntResult | None = None
        self._hunt_history: list[dict[str, Any]] = []

    @property
    def role_type(self) -> RoleType:
        return RoleType.BUG_HUNTER

    @property
    def responsibilities(self) -> list[str]:
        return [
            "深度漏洞挖掘",
            "边界条件测试",
            "异常场景构造",
            "安全攻击模拟",
            "性能压力测试",
            "风险评估报告",
        ]

    def _setup_skills(self) -> None:
        """设置猎取技能"""
        skills = [
            RoleSkill(
                name="hunt_bugs",
                description="挖掘漏洞",
                category=SkillCategory.TESTING,
                inputs=["code", "requirements"],
                outputs=["vulnerabilities", "risk_report"],
            ),
            RoleSkill(
                name="fuzz_test",
                description="模糊测试",
                category=SkillCategory.TESTING,
                inputs=["code", "input_spec"],
                outputs=["crashes", "anomalies"],
            ),
            RoleSkill(
                name="security_audit",
                description="安全审计",
                category=SkillCategory.ANALYSIS,
                inputs=["code"],
                outputs=["security_issues", "recommendations"],
            ),
            RoleSkill(
                name="stress_test",
                description="压力测试",
                category=SkillCategory.TESTING,
                inputs=["code", "load_params"],
                outputs=["performance_issues", "bottlenecks"],
            ),
        ]

        for skill in skills:
            self.add_skill(skill)

    def get_supported_task_types(self) -> list[TaskType]:
        return [TaskType.RUN_TEST, TaskType.BUG_REPORT]

    def _execute_by_type(self, task_type: TaskType) -> dict[str, Any]:
        if task_type == TaskType.RUN_TEST:
            return self._hunt_bugs_task()
        elif task_type == TaskType.BUG_REPORT:
            return self._generate_report_task()
        return {"status": "error", "message": f"Unsupported task: {task_type}"}

    # ==================== 核心猎取方法 ====================

    def hunt(self, code: str, context: dict[str, Any] | None = None) -> HuntResult:
        """
        执行漏洞猎取

        使用多种策略发现隐藏问题

        Args:
            code: 待猎取代码
            context: 上下文信息

        Returns:
            猎取结果
        """
        vulnerabilities: list[IssueRecord] = []
        attack_surface = {}

        # 1. 安全模式检测
        security_issues = self._security_scan(code)
        vulnerabilities.extend(security_issues)
        attack_surface["security"] = len(security_issues)

        # 2. 边界分析
        boundary_issues = self._boundary_analysis(code)
        vulnerabilities.extend(boundary_issues)
        attack_surface["boundary"] = len(boundary_issues)

        # 3. 异常处理分析
        exception_issues = self._exception_analysis(code)
        vulnerabilities.extend(exception_issues)
        attack_surface["exception"] = len(exception_issues)

        # 4. 输入验证分析
        input_issues = self._input_validation_analysis(code)
        vulnerabilities.extend(input_issues)
        attack_surface["input_validation"] = len(input_issues)

        # 计算风险分数
        risk_score = self._calculate_risk_score(vulnerabilities)

        # 生成报告
        report = self._generate_hunt_report(vulnerabilities, risk_score)

        result = HuntResult(
            vulnerabilities=vulnerabilities,
            attack_surface=attack_surface,
            risk_score=risk_score,
            report=report,
        )

        self._last_hunt = result
        self._hunt_history.append({
            "timestamp": time.time(),
            "issue_count": len(vulnerabilities),
            "risk_score": risk_score,
        })

        return result

    def quick_hunt(self, code: str) -> tuple[float, list[str]]:
        """
        快速猎取（简化版）

        Returns:
            (风险分数, 问题列表)
        """
        issues = self._security_scan(code)
        risk = self._calculate_risk_score(issues)
        return risk, [i.description for i in issues]

    # ==================== 猎取策略实现 ====================

    def _security_scan(self, code: str) -> list[IssueRecord]:
        """安全扫描"""
        issues = []

        for vuln_type, config in self.SECURITY_PATTERNS.items():
            for pattern, description in config["patterns"]:
                try:
                    matches = re.finditer(pattern, code, re.IGNORECASE)
                    for match in matches:
                        line_num = code[:match.start()].count('\n') + 1
                        issue = create_issue(
                            description=f"[{vuln_type}] {description}",
                            severity=config["severity"],
                            found_by=self.role_id,
                            line_number=line_num,
                        )
                        issues.append(issue)
                except re.error:
                    continue

        return issues

    def _boundary_analysis(self, code: str) -> list[IssueRecord]:
        """边界分析"""
        issues = []

        # 检测数组/列表访问
        list_access_pattern = r'\w+\s*\[\s*\w+\s*\]'
        for match in re.finditer(list_access_pattern, code):
            # 检查是否有边界检查
            var_name = match.group(0).split('[')[0]
            context_start = max(0, match.start() - 200)
            context = code[context_start:match.start()]

            if 'len(' + var_name not in context and 'if ' + var_name not in context:
                line_num = code[:match.start()].count('\n') + 1
                issue = create_issue(
                    description=f"可能的数组越界: {var_name}",
                    severity=IssueSeverity.MAJOR,
                    found_by=self.role_id,
                    line_number=line_num,
                )
                issues.append(issue)

        # 检测整数运算
        int_ops = [r'\+\+', r'--', r'\+=', r'-=']
        for op in int_ops:
            for match in re.finditer(op, code):
                context_start = max(0, match.start() - 100)
                context = code[context_start:match.start()]

                # 检查是否有溢出保护
                if 'if ' not in context and 'max' not in context.lower():
                    line_num = code[:match.start()].count('\n') + 1
                    issue = create_issue(
                        description="可能的整数溢出",
                        severity=IssueSeverity.MAJOR,
                        found_by=self.role_id,
                        line_number=line_num,
                    )
                    issues.append(issue)
                    break  # 每种操作只报一次

        return issues

    def _exception_analysis(self, code: str) -> list[IssueRecord]:
        """异常处理分析"""
        issues = []

        # 检测可能抛出异常但没有处理的代码
        risk_operations = [
            (r'open\s*\(', "文件操作", "可能抛出 FileNotFoundError"),
            (r'\.read\s*\(', "读取操作", "可能抛出 IOError"),
            (r'\.write\s*\(', "写入操作", "可能抛出 IOError"),
            (r'int\s*\(', "类型转换", "可能抛出 ValueError"),
            (r'json\.loads', "JSON解析", "可能抛出 JSONDecodeError"),
            (r'requests\.\w+', "网络请求", "可能抛出 ConnectionError"),
        ]

        for pattern, op_name, risk in risk_operations:
            for match in re.finditer(pattern, code):
                # 检查是否在 try 块中
                context_start = max(0, match.start() - 500)
                context = code[context_start:match.start()]

                if 'try:' not in context and 'try :' not in context:
                    line_num = code[:match.start()].count('\n') + 1
                    issue = create_issue(
                        description=f"{op_name}缺少异常处理: {risk}",
                        severity=IssueSeverity.MAJOR,
                        found_by=self.role_id,
                        line_number=line_num,
                    )
                    issues.append(issue)

        return issues

    def _input_validation_analysis(self, code: str) -> list[IssueRecord]:
        """输入验证分析"""
        issues = []

        # 检测用户输入点
        input_patterns = [
            (r'input\s*\(', "用户输入"),
            (r'request\.(GET|POST|data|json)', "HTTP请求"),
            (r'args\.get', "命令行参数"),
            (r'os\.environ', "环境变量"),
        ]

        for pattern, input_type in input_patterns:
            for match in re.finditer(pattern, code, re.IGNORECASE):
                # 检查后续是否有验证
                context_end = min(len(code), match.end() + 300)
                context = code[match.end():context_end]

                validation_keywords = ['if ', 'validate', 'check', 'isinstance', 'type']
                has_validation = any(kw in context[:100] for kw in validation_keywords)

                if not has_validation:
                    line_num = code[:match.start()].count('\n') + 1
                    issue = create_issue(
                        description=f"{input_type}缺少验证",
                        severity=IssueSeverity.MAJOR,
                        found_by=self.role_id,
                        line_number=line_num,
                    )
                    issues.append(issue)

        return issues

    def _calculate_risk_score(self, vulnerabilities: list[IssueRecord]) -> float:
        """计算风险分数"""
        if not vulnerabilities:
            return 0.0

        score = 0.0
        for vuln in vulnerabilities:
            if vuln.severity == IssueSeverity.CRITICAL:
                score += 30
            elif vuln.severity == IssueSeverity.MAJOR:
                score += 15
            else:
                score += 5

        return min(100, score)

    def _generate_hunt_report(
        self,
        vulnerabilities: list[IssueRecord],
        risk_score: float,
    ) -> str:
        """生成猎取报告"""
        if not vulnerabilities:
            return "漏洞猎取完成：未发现明显漏洞"

        # 按严重程度分组
        by_severity = {
            "critical": [],
            "major": [],
            "minor": [],
        }
        for v in vulnerabilities:
            by_severity[v.severity.value].append(v)

        lines = [
            f"# 漏洞猎取报告",
            f"",
            f"**风险分数**: {risk_score:.0f}/100",
            f"",
            f"## 发现摘要",
            f"- 严重: {len(by_severity['critical'])}",
            f"- 中等: {len(by_severity['major'])}",
            f"- 轻微: {len(by_severity['minor'])}",
            f"",
        ]

        if by_severity['critical']:
            lines.append("## 严重漏洞")
            for v in by_severity['critical']:
                lines.append(f"- [L{v.line_number or '?'}] {v.description}")
            lines.append("")

        if by_severity['major']:
            lines.append("## 中等问题")
            for v in by_severity['major'][:10]:  # 只显示前10个
                lines.append(f"- [L{v.line_number or '?'}] {v.description}")
            lines.append("")

        return "\n".join(lines)

    # ==================== 任务执行 ====================

    def _hunt_bugs_task(self) -> dict[str, Any]:
        """执行漏洞猎取任务"""
        code = self._current_task.get("inputs", {}).get("code", "")
        context = self._current_task.get("inputs", {}).get("context", {})

        result = self.hunt(code, context)

        return {
            "status": "completed",
            "outputs": {
                "vulnerabilities": [v.model_dump() for v in result.vulnerabilities],
                "attack_surface": result.attack_surface,
                "risk_score": result.risk_score,
                "report": result.report,
            },
        }

    def _generate_report_task(self) -> dict[str, Any]:
        """生成报告任务"""
        if self._last_hunt:
            return {
                "status": "completed",
                "outputs": {
                    "report": self._last_hunt.report,
                },
            }
        return {"status": "error", "message": "No hunt performed"}

    # ==================== 状态 ====================

    def get_last_hunt(self) -> HuntResult | None:
        """获取最近猎取结果"""
        return self._last_hunt

    def get_hunt_history(self) -> list[dict[str, Any]]:
        """获取猎取历史"""
        return self._hunt_history.copy()

    def get_status(self) -> dict[str, Any]:
        """获取角色状态"""
        status = super().get_status()
        status["is_discriminator"] = True
        status["hunt_count"] = len(self._hunt_history)
        status["last_risk_score"] = self._last_hunt.risk_score if self._last_hunt else None
        return status


def create_bug_hunter(
    hunter_id: str = "hunter_1",
    name: str = "漏洞猎手",
    context: RoleContext | None = None,
) -> BugHunter:
    """创建漏洞猎手实例"""
    return BugHunter(role_id=hunter_id, name=name, context=context)