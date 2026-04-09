"""
测试流程强制执行功能

验证：
1. skip_hooks 已被替换为 skip_level 和 admin_override
2. 边界检查强制执行
3. 工具权限运行时强制
4. 质量门禁强制执行
5. 违规记录与积分联动
"""

import pytest
import io
from pathlib import Path

from harnessgenj.engine import (
    Harness,
    SkipLevel,
    MANDATORY_CHECKS,
    QualityGate,
    MANDATORY_GATES,
)
from harnessgenj.roles import (
    RoleType,
    create_role,
    ToolPermission,
)
from harnessgenj.quality import (
    ScoreManager,
    ViolationManager,
    ViolationSeverity,
    ViolationType,
    create_violation_manager,
)
from harnessgenj.notify import UserNotifier, VerbosityMode


class TestSkipHooksReplacement:
    """测试 skip_hooks 参数已被替换"""

    def test_skip_level_enum_exists(self):
        """测试 SkipLevel 枚举存在"""
        assert hasattr(SkipLevel, "NONE")
        assert hasattr(SkipLevel, "OPTIONAL_HOOKS")
        assert hasattr(SkipLevel, "ALL")

    def test_mandatory_checks_defined(self):
        """测试强制检查项定义"""
        assert "adversarial_review" in MANDATORY_CHECKS
        assert "security_check" in MANDATORY_CHECKS
        assert "boundary_check" in MANDATORY_CHECKS

    def test_mandatory_gates_defined(self):
        """测试强制质量门禁定义"""
        gate_names = [g.name for g in MANDATORY_GATES]
        assert "adversarial_review" in gate_names
        assert "security_check" in gate_names
        assert "test_pass" in gate_names

    def test_develop_method_signature(self):
        """测试 develop 方法签名包含 skip_level 和 admin_override"""
        import inspect
        sig = inspect.signature(Harness.develop)
        params = list(sig.parameters.keys())
        assert "skip_level" in params
        assert "admin_override" in params
        assert "skip_hooks" not in params

    def test_fix_bug_method_signature(self):
        """测试 fix_bug 方法签名包含 skip_level 和 admin_override"""
        import inspect
        sig = inspect.signature(Harness.fix_bug)
        params = list(sig.parameters.keys())
        assert "skip_level" in params
        assert "admin_override" in params
        assert "skip_hooks" not in params


class TestBoundaryEnforcement:
    """测试边界检查强制执行"""

    def test_project_manager_forbidden_actions(self):
        """测试项目经理禁止行为定义"""
        pm = create_role(RoleType.PROJECT_MANAGER, "pm_test", "项目经理")
        forbidden = pm.forbidden_actions
        assert len(forbidden) > 0
        # 检查是否包含代码修改相关禁止
        assert any("代码" in f or "code" in f.lower() for f in forbidden)

    def test_code_reviewer_forbidden_actions(self):
        """测试代码审查者禁止行为定义"""
        reviewer = create_role(RoleType.CODE_REVIEWER, "reviewer_test", "审查者")
        forbidden = reviewer.forbidden_actions
        assert len(forbidden) > 0

    def test_boundary_check_method(self):
        """测试边界检查方法"""
        pm = create_role(RoleType.PROJECT_MANAGER, "pm_test", "项目经理")

        # 测试合法操作
        result = pm.check_boundary("track_progress")
        assert result.allowed is True

        # 测试禁止操作 - 使用完整的禁止行为描述
        result = pm.check_boundary("修改代码文件")
        # 注意：边界检查基于 forbidden_actions 中的关键词匹配
        # "修改代码文件" 应该匹配 "修改代码文件"
        assert result.allowed is False

    def test_boundary_violation_recording(self):
        """测试边界违规记录"""
        pm = create_role(RoleType.PROJECT_MANAGER, "pm_test", "项目经理")

        # 尝试禁止操作 - 使用完整的禁止行为描述
        result = pm.check_boundary("做技术决策")
        assert result.allowed is False


class TestToolPermissionEnforcement:
    """测试工具权限运行时强制"""

    def test_project_manager_permissions(self):
        """测试项目经理权限"""
        pm = create_role(RoleType.PROJECT_MANAGER, "pm_test", "项目经理")
        permissions = pm.get_tool_permissions()

        assert ToolPermission.READ in permissions
        assert ToolPermission.SEARCH in permissions
        assert ToolPermission.EDIT_DOC in permissions
        # 项目经理不应该有代码编辑权限
        assert ToolPermission.EDIT_CODE not in permissions

    def test_developer_permissions(self):
        """测试开发者权限"""
        dev = create_role(RoleType.DEVELOPER, "dev_test", "开发者")
        permissions = dev.get_tool_permissions()

        assert ToolPermission.READ in permissions
        assert ToolPermission.SEARCH in permissions
        assert ToolPermission.EDIT_CODE in permissions
        assert ToolPermission.TERMINAL in permissions

    def test_code_reviewer_permissions(self):
        """测试代码审查者权限（只读）"""
        reviewer = create_role(RoleType.CODE_REVIEWER, "reviewer_test", "审查者")
        permissions = reviewer.get_tool_permissions()

        assert ToolPermission.READ in permissions
        assert ToolPermission.SEARCH in permissions
        # 审查者不应该有编辑权限
        assert ToolPermission.EDIT_CODE not in permissions
        assert ToolPermission.EDIT_DOC not in permissions

    def test_can_use_tool_method(self):
        """测试 can_use_tool 方法"""
        pm = create_role(RoleType.PROJECT_MANAGER, "pm_test", "项目经理")

        # 测试允许的工具
        result = pm.can_use_tool(ToolPermission.READ)
        assert result.allowed is True

        # 测试禁止的工具
        result = pm.can_use_tool(ToolPermission.EDIT_CODE)
        assert result.allowed is False
        assert "没有" in result.reason or "无" in result.reason


class TestViolationManager:
    """测试违规管理器"""

    def test_violation_manager_creation(self, tmp_path):
        """测试违规管理器创建"""
        score_manager = ScoreManager(str(tmp_path))
        violation_manager = create_violation_manager(score_manager, str(tmp_path))

        assert violation_manager is not None
        assert violation_manager.score_manager is score_manager

    def test_violation_record(self, tmp_path):
        """测试违规记录"""
        score_manager = ScoreManager(str(tmp_path))
        score_manager.register_role("developer", "dev_test", "开发者", 100)

        violation_manager = create_violation_manager(score_manager, str(tmp_path))

        # 记录违规
        record = violation_manager.record(
            role_id="dev_test",
            violation_type=ViolationType.BOUNDARY_VIOLATION.value,
            action="尝试修改禁止文件",
            reason="超出职责范围",
            severity=ViolationSeverity.MEDIUM,
            blocked=True,
        )

        assert record is not None
        assert record.role_id == "dev_test"
        assert record.blocked is True
        assert record.score_delta < 0  # 扣分

    def test_violation_score_impact(self, tmp_path):
        """测试违规对积分的影响"""
        score_manager = ScoreManager(str(tmp_path))
        score_manager.register_role("developer", "dev_test", "开发者", 100)

        violation_manager = create_violation_manager(score_manager, str(tmp_path))

        # 记录违规
        violation_manager.record(
            role_id="dev_test",
            violation_type=ViolationType.BOUNDARY_VIOLATION.value,
            action="边界违规",
            reason="测试",
            severity=ViolationSeverity.MEDIUM,
            blocked=True,
        )

        # 检查积分是否变化
        score = score_manager.get_score("dev_test")
        assert score.score < 100  # 积分应该减少

    def test_violation_stats(self, tmp_path):
        """测试违规统计"""
        score_manager = ScoreManager(str(tmp_path))
        score_manager.register_role("developer", "dev_test", "开发者", 100)

        violation_manager = create_violation_manager(score_manager, str(tmp_path))

        # 记录多个违规
        violation_manager.record(
            role_id="dev_test",
            violation_type=ViolationType.BOUNDARY_VIOLATION.value,
            action="违规1",
            reason="测试",
            blocked=True,
        )
        violation_manager.record(
            role_id="dev_test",
            violation_type=ViolationType.PERMISSION_DENIED.value,
            action="违规2",
            reason="测试",
            blocked=False,
        )

        stats = violation_manager.get_violation_stats()
        assert stats["total"] == 2
        assert stats["blocked"] == 1


class TestScoreRules:
    """测试积分规则"""

    def test_violation_rules_exist(self):
        """测试违规惩罚规则存在"""
        from harnessgenj.quality.score import ScoreRules

        assert hasattr(ScoreRules, "BOUNDARY_VIOLATION")
        assert hasattr(ScoreRules, "PERMISSION_DENIED")
        assert hasattr(ScoreRules, "GATE_BYPASS_ATTEMPT")
        assert hasattr(ScoreRules, "UNAUTHORIZED_CODE_EDIT")

    def test_compliance_rules_exist(self):
        """测试合规奖励规则存在"""
        from harnessgenj.quality.score import ScoreRules

        assert hasattr(ScoreRules, "PROCESS_COMPLIANCE")
        assert hasattr(ScoreRules, "QUALITY_GATE_PASS")

    def test_record_violation_method(self, tmp_path):
        """测试 record_violation 方法"""
        score_manager = ScoreManager(str(tmp_path))
        score_manager.register_role("developer", "dev_test", "开发者", 100)

        # 记录违规
        event = score_manager.record_violation(
            role_id="dev_test",
            violation_type="boundary_violation",
            action="边界违规测试",
            blocked=True,
        )

        assert event is not None
        assert event.delta < 0

        # 检查积分变化
        score = score_manager.get_score("dev_test")
        assert score.score < 100

    def test_reward_compliance_method(self, tmp_path):
        """测试 reward_compliance 方法"""
        score_manager = ScoreManager(str(tmp_path))
        score_manager.register_role("developer", "dev_test", "开发者", 95)

        # 奖励合规
        event = score_manager.reward_compliance(
            role_id="dev_test",
            compliance_type="process_compliance",
        )

        assert event is not None
        assert event.delta > 0

        # 检查积分变化（积分限制在 0-100 范围内）
        score = score_manager.get_score("dev_test")
        # 从95分开始，加2分应该到97分（在范围内）
        assert score.score == 97


class TestNotifierEnhancements:
    """测试通知器增强"""

    def test_notify_boundary_violation(self):
        """测试边界违规通知"""
        output = io.StringIO()
        notifier = UserNotifier(enabled=True, output=output)

        notifier.notify_boundary_violation(
            role_type="ProjectManager",
            role_id="pm_1",
            action="edit_code",
            reason="只能编辑文档，不能修改代码文件",
            suggestion="请将代码修改任务分配给 Developer 角色",
        )

        content = output.getvalue()
        assert "无权执行" in content
        assert "edit_code" in content

    def test_notify_gate_blocked(self):
        """测试质量门禁阻塞通知"""
        output = io.StringIO()
        notifier = UserNotifier(enabled=True, output=output)

        notifier.notify_gate_blocked(
            gate_name="adversarial_review",
            reason="发现 3 个问题需要修复",
        )

        content = output.getvalue()
        assert "质量门禁" in content
        assert "未通过" in content

    def test_notify_process_guide(self):
        """测试流程指引通知"""
        output = io.StringIO()
        notifier = UserNotifier(enabled=True, output=output)

        notifier.notify_process_guide(
            current_stage="development",
            next_stages=["review", "testing"],
            required_roles=["Developer", "CodeReviewer"],
        )

        content = output.getvalue()
        assert "流程指引" in content
        assert "development" in content

    def test_notify_bypass_attempt(self):
        """测试跳过尝试通知"""
        output = io.StringIO()
        notifier = UserNotifier(enabled=True, output=output)

        notifier.notify_bypass_attempt(
            action="develop",
            skip_level="optional",
            admin_override=True,
        )

        content = output.getvalue()
        assert "管理员覆盖" in content


class TestRolePromptEnhancement:
    """测试角色提示词增强"""

    def test_score_motivation_prompt_exists(self):
        """测试积分动机提示词存在"""
        from harnessgenj.roles.base import AgentRole

        assert hasattr(AgentRole, "SCORE_MOTIVATION_PROMPT")
        assert "积分" in AgentRole.SCORE_MOTIVATION_PROMPT
        assert "职业信誉" in AgentRole.SCORE_MOTIVATION_PROMPT

    def test_process_compliance_prompt_exists(self):
        """测试流程合规提示词存在"""
        from harnessgenj.roles.base import AgentRole

        assert hasattr(AgentRole, "PROCESS_COMPLIANCE_PROMPT")
        assert "流程" in AgentRole.PROCESS_COMPLIANCE_PROMPT
        assert "违规" in AgentRole.PROCESS_COMPLIANCE_PROMPT

    def test_build_role_prompt_includes_motivation(self):
        """测试角色提示词包含积分动机"""
        # 使用基类方法测试
        from harnessgenj.roles.base import AgentRole
        prompt = AgentRole.build_role_prompt  # 方法存在
        assert prompt is not None

        # 验证提示词模板包含关键内容
        assert "积分" in AgentRole.SCORE_MOTIVATION_PROMPT
        assert "职业信誉" in AgentRole.SCORE_MOTIVATION_PROMPT

    def test_build_role_prompt_includes_compliance(self):
        """测试角色提示词包含流程合规"""
        from harnessgenj.roles.base import AgentRole

        # 验证提示词模板包含关键内容
        assert "流程合规" in AgentRole.PROCESS_COMPLIANCE_PROMPT or "合规" in AgentRole.PROCESS_COMPLIANCE_PROMPT


class TestIntegration:
    """集成测试"""

    def test_full_workflow_with_enforcement(self, tmp_path):
        """测试完整工作流中的强制执行"""
        # 创建 Harness 实例
        harness = Harness(
            project_name="Test Project",
            persistent=False,
            workspace=str(tmp_path),
        )

        # 验证强制检查项配置
        assert len(MANDATORY_CHECKS) > 0
        assert len(MANDATORY_GATES) > 0

    def test_project_manager_cannot_edit_code(self):
        """测试项目经理无法编辑代码"""
        pm = create_role(RoleType.PROJECT_MANAGER, "pm_test", "项目经理")

        # 检查权限
        result = pm.can_use_tool(ToolPermission.EDIT_CODE)
        assert result.allowed is False

        # 检查边界 - 使用完整的禁止行为描述
        boundary = pm.check_boundary("修改代码文件")
        assert boundary.allowed is False

    def test_code_reviewer_read_only(self):
        """测试代码审查者只读"""
        reviewer = create_role(RoleType.CODE_REVIEWER, "reviewer_test", "审查者")

        # 应该有读取权限
        assert reviewer.can_use_tool(ToolPermission.READ).allowed is True
        assert reviewer.can_use_tool(ToolPermission.SEARCH).allowed is True

        # 不应该有编辑权限
        assert reviewer.can_use_tool(ToolPermission.EDIT_CODE).allowed is False
        assert reviewer.can_use_tool(ToolPermission.EDIT_DOC).allowed is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])