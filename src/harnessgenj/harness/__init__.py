"""
Harness Layer - Built-in Capabilities

类比 JVM 的 JDK 内置工具:
- 预定义能力，开箱即用
- 可插拔，可扩展
- 标准化接口

核心能力:
1. AGENTS.md - 项目知识文件，自动注入上下文
2. Hooks - 质量门禁，确定性规则约束
3. HumanLoop - 人机交互节点
4. Adversarial - 对抗性质量保证
5. Decorators - 便利性装饰器
"""

from harnessgenj.harness.human_loop import HumanLoop, ApprovalRequest
from harnessgenj.harness.agents_knowledge import (
    AgentsKnowledgeManager,
    KnowledgeSection,
    AgentsKnowledge,
)
from harnessgenj.harness.hooks import (
    HooksManager,
    BaseHook,
    HookType,
    HookMode,
    HookResult,
    HooksResult,
    CodeLintHook,
    SecurityHook,
    ValidationHook,
    TestPassHook,
    FormatHook,
    create_default_hooks,
)
from harnessgenj.harness.context_assembler import (
    ContextAssembler,
    ContextSection,
    ContextPriority,
    PermanentKnowledge,
    ActiveTaskContext,
    create_context_assembler,
)
from harnessgenj.harness.adversarial import (
    AdversarialWorkflow,
    AdversarialResult,
    create_adversarial_workflow,
)
from harnessgenj.harness.decorators import (
    trace_decision,
    on_task_complete,
    on_issue_found,
    with_context,
    LifecycleHooks,
    lifecycle_hooks,
    set_global_harness,
    get_global_harness,
)
from harnessgenj.harness.git_integration import (
    GitHooks,
    create_git_hooks,
)
from harnessgenj.harness.hooks_integration import (
    HooksIntegration,
    HooksConfig,
    HooksIntegrationBuilder,
    create_hooks_integration,
)

__all__ = [
    # HumanLoop
    "HumanLoop",
    "ApprovalRequest",
    # AGENTS Knowledge
    "AgentsKnowledgeManager",
    "KnowledgeSection",
    "AgentsKnowledge",
    # Hooks
    "HooksManager",
    "BaseHook",
    "HookType",
    "HookMode",
    "HookResult",
    "HooksResult",
    "CodeLintHook",
    "SecurityHook",
    "ValidationHook",
    "TestPassHook",
    "FormatHook",
    "create_default_hooks",
    # Context Assembler
    "ContextAssembler",
    "ContextSection",
    "ContextPriority",
    "PermanentKnowledge",
    "ActiveTaskContext",
    "create_context_assembler",
    # Adversarial
    "AdversarialWorkflow",
    "AdversarialResult",
    "create_adversarial_workflow",
    # Decorators
    "trace_decision",
    "on_task_complete",
    "on_issue_found",
    "with_context",
    "LifecycleHooks",
    "lifecycle_hooks",
    "set_global_harness",
    "get_global_harness",
    # Git Integration
    "GitHooks",
    "create_git_hooks",
    # Hooks Integration
    "HooksIntegration",
    "HooksConfig",
    "HooksIntegrationBuilder",
    "create_hooks_integration",
]