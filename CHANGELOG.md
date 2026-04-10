# Changelog

All notable changes to HarnessGenJ will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.2] - 2026-04-10

### Added
- **异常处理工具模块**: 统一的异常处理机制，避免静默吞掉错误
  - `exception_handler.py`: 提供 `safe_call()`, `log_exception()`, `SafeContext`, `safe_operation` 装饰器
  - 静默异常从 103 处减少到 45 处（减少 56%）
  - 支持日志级别配置和堆栈追踪选项
- **CLI 测试覆盖**: 新增 `test_cli.py` 包含 23 个测试用例
  - 覆盖 version, init, setup-hooks, develop, fix, team, status, sync 命令
  - 测试总数从 1007 增加到 1030
- **并发安全增强**: 为关键数据结构添加线程锁
  - ScoreManager: 使用 `threading.RLock` 保护 `_scores`, `_events`
  - MemoryManager: 使用 `threading.RLock` 保护 `_current_task`, `project_info`
  - 防止多线程环境下的数据损坏

### Changed
- **异常处理改进**: 7 个关键文件的静默异常替换为日志记录
  - engine.py (27处), monitor.py (9处), hooks_auto_setup.py (8处)
  - tech_detector.py (8处), score.py (1处), storage/manager.py (1处)
  - memory/structured_knowledge.py (5处)
- **线程安全**: 关键方法的读写操作使用锁保护

### New Files
- `src/harnessgenj/utils/exception_handler.py` - 异常处理工具模块
- `tests/test_cli.py` - CLI 测试文件 (23 个测试用例)

## [1.3.1] - 2026-04-10

### Added
- **OperationInstruction 协议**: 框架生成的操作指令供 AI 执行
  - `OperationInstruction` 类：包含许可文件、执行指令、预期产出
  - `ExecutionResult` 类：AI 完成操作后报告给框架
  - 便捷函数：`create_develop_instruction()`, `create_fix_bug_instruction()`
- **FrameworkSession 会话管理**: 签发操作许可，控制 AI 的修改范围
  - `grant_permission()`: 签发操作许可
  - `check_permission()`: 检查权限
  - `revoke_permission()`: 撤销许可
- **一句话启动框架**: 用户只需说"使用HGJ框架"即可激活框架
  - 新增 `framework_activate` 意图检测
  - 自动初始化框架并引导后续操作
- **develop()/fix_bug() 指令模式**: 返回操作指令而非模拟结果
  - 新增 `execution_mode` 参数："instruction" | "simulate"
  - 默认使用 "instruction" 模式签发许可并生成指令

### Changed
- **修复核心缺陷**: `develop()` 现在签发操作许可并生成指令，而非只模拟
- **简化 CLAUDE.md**: 优化用户引导，一句话即可启动框架
- **更新 Hooks**: 新增框架激活意图检测

### Fixed
- **FrameworkSession 单例问题**: 修复 Pydantic BaseModel 中类变量被当作私有属性的问题
- **测试兼容性**: 更新测试以适应新的 CLAUDE.md 结构

### New Files
- `src/harnessgenj/harness/operation_instruction.py` - 操作指令协议
- `src/harnessgenj/harness/framework_session.py` - 框架会话管理
- `.harnessgenj/documents/admin_audit_log.md` - 框架升级审计日志

## [1.3.0] - 2026-04-09

### Added
- **MCP Server 模块**: 框架作为 MCP Server 暴露工具，让 Claude Code 可直接调用
  - 21 个内置工具：内存管理(6)、任务管理(6)、系统工具(5)、存储工具(4)
  - JSON-RPC 2.0 协议支持
  - stdio 通信模式
  - 工具注册和执行机制
- **Notify 模块增强**: 新增输出格式和进度追踪
  - JSON 输出格式支持 (`OutputFormat.JSON`)
  - ASCII 进度条渲染
  - 输出缓冲机制（用于测试）
  - 进度追踪 API (`notify_progress`, `complete_progress`)
- **TUI 仪表板模块**: 轻量级终端可视化界面
  - ASCII 艺术渲染
  - 项目状态概览
  - 积分排行榜
  - 任务进度展示
  - 零外部依赖
- **工具基类**: `MCPTool` 抽象基类，支持自定义工具扩展
- **工具注册表**: `ToolRegistry` 管理工具注册和发现
- **测试覆盖率提升**: 从 72% 提升至 73.57%
  - 新增 roles 模块测试：Developer、CodeReviewer、BugHunter、Tester
  - 修复了 `skip_hooks` 参数迁移遗留问题
  - 总测试用例达到 1013 个

### New Files
- `src/harnessgenj/mcp/__init__.py` - MCP 模块导出
- `src/harnessgenj/mcp/server.py` - MCP Server 核心实现
- `src/harnessgenj/mcp/protocol.py` - JSON-RPC 协议
- `src/harnessgenj/mcp/config.py` - 配置定义
- `src/harnessgenj/mcp/tools/*.py` - 工具实现
- `src/harnessgenj/dashboard/__init__.py` - Dashboard 模块导出
- `src/harnessgenj/dashboard/tui.py` - 终端仪表板实现
- `tests/mcp/test_mcp.py` - MCP 模块测试 (41 个测试用例)
- `tests/notify/test_notify_enhanced.py` - Notify 增强测试 (17 个测试用例)
- `tests/roles/test_developer.py` - Developer 角色测试 (31 个测试用例)
- `tests/roles/test_code_reviewer.py` - CodeReviewer 角色测试 (19 个测试用例)
- `tests/roles/test_bug_hunter.py` - BugHunter 角色测试 (19 个测试用例)
- `tests/roles/test_tester.py` - Tester 角色测试 (18 个测试用例)
- `tests/dashboard/test_dashboard.py` - Dashboard 测试 (13 个测试用例)

### Fixed
- 修复测试中 `skip_hooks=True` 参数遗留问题，替换为 `skip_level=SkipLevel.ALL`
- 修复 Developer `_report_to_pm` 方法参数传递问题

### Purpose
- MCP Server：解决 AI 不主动调用框架的根本问题
- Notify 增强：提升用户体验，支持更多输出格式
- TUI 仪表板：提供轻量级可视化界面
- 测试补充：确保代码健壮性，roles 模块覆盖率显著提升

## [1.2.9] - 2026-04-09

### Added
- **MCP Server 模块**: 框架作为 MCP Server 暴露工具，让 Claude Code 可直接调用
  - 19 个内置工具：内存管理(6)、任务管理(6)、存储(4)、系统(3)
  - JSON-RPC 2.0 协议支持
  - stdio 通信模式
  - 工具注册和执行机制
- **工具基类**: `MCPTool` 抽象基类，支持自定义工具扩展
- **工具注册表**: `ToolRegistry` 管理工具注册和发现
- **协议层**: 完整的 JSON-RPC 请求/响应处理

### New Files
- `src/harnessgenj/mcp/__init__.py` - 模块导出
- `src/harnessgenj/mcp/server.py` - MCP Server 核心实现
- `src/harnessgenj/mcp/protocol.py` - JSON-RPC 协议
- `src/harnessgenj/mcp/config.py` - 配置定义
- `src/harnessgenj/mcp/tools/__init__.py` - 工具基类
- `src/harnessgenj/mcp/tools/memory_tools.py` - 内存工具
- `src/harnessgenj/mcp/tools/task_tools.py` - 任务工具
- `src/harnessgenj/mcp/tools/system_tools.py` - 系统工具
- `src/harnessgenj/mcp/tools/storage_tools.py` - 存储工具
- `tests/mcp/test_mcp.py` - MCP 模块测试 (41 个测试用例)

### Purpose
解决 AI 不主动调用框架的根本问题，通过 MCP 协议让 Claude Code 原生集成框架功能。

## [1.2.8] - 2026-04-09

### Added
- **框架主动输出机制**: 初始化时主动输出框架状态和使用指南
  - 初始化完成时自动输出框架已就绪信息
  - 输出项目基本信息（名称、工作空间、团队、技术栈）
  - 输出下一步操作建议（develop/fix_bug/get_status）
  - 输出积分系统提示
- **框架状态检测机制**: 提供静态方法供 Hooks 和外部检测框架状态
  - `Harness.is_initialized()` - 检查框架是否已初始化
  - `Harness.get_initialization_status()` - 获取详细初始化状态
  - `Harness.get_last_instance()` - 获取最后创建的框架实例
  - 状态包含：项目路径、活动工作流、活动角色等
- **CLAUDE.md 项目级指令**: 确保 AI 主动使用框架
  - 强制声明：所有开发任务必须通过框架执行
  - 框架初始化和使用代码示例
  - 开发流程规范和检查清单
  - 角色边界定义和违规后果
  - API 速查表

### Purpose
解决 AI 不主动调用框架的问题：
- CLAUDE.md 作为项目级指令，直接影响 AI 行为
- 框架初始化时主动输出，提醒用户框架已就绪
- 状态检测机制让 Hooks 可判断是否需要提醒用户

## [1.2.7] - 2026-04-09

### Added
- **流程强制执行系统**: 确保所有角色严格遵守工作流程
  - SkipLevel 枚举替代 skip_hooks 参数，支持分级跳过控制
  - admin_override 参数允许管理员覆盖强制检查（记录审计日志）
  - MANDATORY_CHECKS 和 MANDATORY_GATES 强制质量门禁
- **边界检查强制执行**: `coordinator.execute_stage()` 集成边界检查
  - 执行前检查角色是否有权限执行该阶段
  - 违规记录到 boundary_violations.json
- **工具权限运行时强制**: `AgentRole.execute_task()` 添加权限检查
  - 任务执行前检查所需工具权限
  - 权限不足时阻止执行并通知用户
- **违规管理模块 (ViolationManager)**: 与积分系统联动
  - ViolationSeverity 枚举：LOW/MEDIUM/HIGH/CRITICAL
  - ViolationType 枚举：边界违规/权限拒绝/绕过门禁/未授权修改
  - 违规记录自动触发积分扣减
- **积分动机提示词 (SCORE_MOTIVATION_PROMPT)**: 让角色以追求高积分为目标
  - 积分意义：职业信誉、团队地位、任务分配、晋升评估
  - 积分排行：90+分（优秀）、70-89分（良好）、50-69分（合格）、<50分（警告）
- **流程合规提示词 (PROCESS_COMPLIANCE_PROMPT)**: 明确告知违规后果
- **强制文档更新**: 任务完成后自动更新相关文档
  - 进度文档 (progress.md) 自动更新
  - 开发日志 (development.md) 自动记录
  - 用户通知文档更新状态

### Changed
- `develop()` 方法参数变更：
  - 移除 `skip_hooks` 参数
  - 新增 `skip_level: SkipLevel` 参数（默认 NONE）
  - 新增 `admin_override: bool` 参数（默认 False）
- `fix_bug()` 方法参数变更：同上
- `ScoreManager` 新增违规惩罚规则：
  - BOUNDARY_VIOLATION = -5
  - PERMISSION_DENIED = -3
  - GATE_BYPASS_ATTEMPT = -10
  - UNAUTHORIZED_CODE_EDIT = -15
- `ScoreManager` 新增合规奖励规则：
  - PROCESS_COMPLIANCE = +2
  - QUALITY_GATE_PASS = +3

### Output Example
```
[HGJ] ⛔ 角色 [ProjectManager] pm_1 无权执行: edit_code
[HGJ]    原因: ProjectManager 只能编辑文档，不能修改代码文件
[HGJ]    建议: 请将代码修改任务分配给 Developer 角色
[HGJ] 📋 违规已记录到审计日志

[HGJ] 🚫 质量门禁 'adversarial_review' 未通过
[HGJ]    原因: 发现 3 个问题需要修复
[HGJ]    流程已暂停，请修复问题后重试
```

## [1.2.6] - 2026-04-08

### Added
- **用户感知通知模块 (UserNotifier)**: 实时输出框架运行状态，增强用户感知
  - 工作流开始/结束通知
  - 阶段执行状态通知
  - 角色任务处理通知
  - **GAN积分变化实时通知**: 积分更新时立即输出到 stderr
  - 问题发现通知
- **详细模式输出**: 输出完整的工作流执行过程和积分变化汇总
- **简洁模式**: 只输出关键节点信息
- **调试模式**: 包含详细调试信息

### Changed
- `ScoreManager._apply_delta()` 现在会触发积分变化通知
- `WorkflowCoordinator.execute_stage()` 现在会输出阶段状态
- `AdversarialWorkflow.execute_adversarial_review()` 现在会输出审查过程
- `Engine.develop()` 现在会输出工作流开始/完成通知

### Output Example
```
[HGJ] ═══════════════════════════════════════════════════════
[HGJ] [12:34:56] 🚀 工作流开始: feature
[HGJ]    阶段: requirement → design → development → testing
[HGJ]   ▶ 阶段 'development' 开始
[HGJ]     角色: developer_1
[HGJ]    [Developer] developer_1 正在处理: Stage: development
[HGJ]      📊 [Score] Developer +10 (一轮通过) → 85
[HGJ]  ✅ 工作流完成: feature (耗时 1.2s)
[HGJ] ═══════════════════════════════════════════════════════
```

## [1.2.5] - 2026-04-08

### Fixed
- **Hooks脚本调用实际代码审查**: `trigger_adversarial_review()` 现在会调用 `Harness.quick_review()` 执行实际代码审查
- Hooks脚本发现问题时会同时更新 Developer 和 CodeReviewer 积分
- 审查结果会记录到开发日志中

### Added
- 新增 5 个 Hooks 脚本审查功能测试用例

## [1.2.4] - 2026-04-08

### Fixed
- **Hooks模式触发TriggerManager**: `hybrid_integration.py:296-302` 现在即使 Hooks 模式也会触发 TriggerManager
- **GAN对抗机制激活**: `develop()` 方法现在集成 `AdversarialWorkflow` 进行代码审查
- **任务状态流转**: 任务创建后状态正确流转 pending → in_progress → reviewing → completed
- **角色协作消息订阅**: 角色现在正确订阅消息总线，协作机制生效
- **双向积分激励**: 审查执行后积分规则正确触发

### Added
- 新增 `test_gan_activation.py` 测试文件，包含 10 个测试用例

## [1.2.3] - 2026-04-06

### Added
- 主动文档维护系统 (DocumentMaintenanceManager)
- 需求检测器 (RequirementDetector)
- 确认管理器 (ConfirmationManager)

## [1.2.2] - 2026-04-05

### Added
- Chat 模式增强功能
- 质量追踪系统 (QualityTracker)
- 失败模式检测

## [1.2.1] - 2026-04-04

### Fixed
- 修复触发链路断裂问题

### Added
- 首次接入引导增强

## [1.2.0] - 2026-04-03

### Changed
- **架构重构优化**: 解决模块职责冗余问题

## [1.1.1] - 2026-04-02

### Added
- 首次接入引导系统

## [1.1.0] - 2026-04-01

### Added
- 初始版本发布
- 角色驱动协作系统
- JVM风格记忆管理
- GAN对抗审查机制