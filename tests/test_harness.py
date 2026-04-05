"""
Tests for Harness Layer
"""

import pytest

from harnessgenj.harness import (
    HumanLoop,
    ApprovalRequest,
    HooksManager,
    BaseHook,
    HookType,
    HookResult,
    AgentsKnowledgeManager,
)


class TestHumanLoop:
    """测试人机交互"""

    def test_request_approval(self) -> None:
        """请求审批"""
        human_loop = HumanLoop()

        request = human_loop.request_approval_sync("Delete file?")

        assert request.action == "Delete file?"
        assert request.status.value in ["pending", "approved"]

    def test_respond_approval(self) -> None:
        """响应审批"""
        human_loop = HumanLoop()

        # 创建请求
        request = human_loop.request_approval_sync("Action?")

        # 响应审批
        response = human_loop.respond_approval(request.request_id, approved=True)

        assert response.approved is True
        assert human_loop.get_request(request.request_id).status.value == "approved"


class TestHooksManager:
    """测试钩子管理器"""

    def test_register_hook(self) -> None:
        """注册钩子"""
        manager = HooksManager()

        # 创建简单钩子
        class TestHook(BaseHook):
            name = "test_hook"
            hook_type = HookType.PRE

            def check(self, context: dict) -> HookResult:
                return HookResult(hook_name="test_hook", passed=True)

        hook = TestHook()
        manager.register(hook)

        hooks = manager.list_hooks()
        assert any(h.get("name") == "test_hook" for h in hooks)

    def test_run_hooks(self) -> None:
        """运行钩子"""
        manager = HooksManager()

        class PassHook(BaseHook):
            name = "pass_hook"
            hook_type = HookType.PRE

            def check(self, context: dict) -> HookResult:
                return HookResult(hook_name="pass_hook", passed=True)

        hook = PassHook()
        manager.register(hook)

        results = manager.run_all_hooks({})

        assert results.passed is True


class TestAgentsKnowledgeManager:
    """测试 AGENTS 知识管理器"""

    def test_initialize(self, tmp_path) -> None:
        """初始化知识管理器"""
        manager = AgentsKnowledgeManager(str(tmp_path))

        assert not manager.is_initialized()

        manager.initialize("Test Project", "Python", "init")

        assert manager.is_initialized()

    def test_get_knowledge(self, tmp_path) -> None:
        """获取知识"""
        manager = AgentsKnowledgeManager(str(tmp_path))
        manager.initialize("Test Project", "Python", "init")

        knowledge = manager.get_full_knowledge()

        assert "Test Project" in knowledge