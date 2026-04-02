# py_ha 项目上下文

## 项目概述

py_ha 是一个 Harness Engineering 框架，用于 AI Agent 协作开发。

**核心工作流：项目经理对接**

```
用户 → 项目经理（接收、分配、监督） → 开发者（执行） → 项目经理（确认完成）
```

**项目经理职责**：
1. 接收所有用户请求
2. 分配优先级和负责人
3. 更新项目文档和统计
4. 监督任务完成

## 当前项目状态

**项目名称**: 待配置
**技术栈**: 待配置
**当前阶段**: 初始化

## AI 对话核心方法

### receive_request() - 项目经理接收请求

```python
from py_ha import Harness

harness = Harness("项目名称", persistent=True)
harness.setup_team()

# 项目经理接收需求
result = harness.receive_request("用户需要一个登录功能")
# 返回: task_id, priority (P1), assignee (developer)

# 项目经理接收 Bug
result = harness.receive_request("登录页面异常", request_type="bug")
# 返回: task_id, priority (P0), assignee (developer)
```

### chat() - 自动项目经理处理

```python
# 用户提出需求 → 项目经理自动接收并分配
harness.chat("我需要一个搜索功能")
# 自动: 创建任务、分配优先级、更新统计

# AI 回复
harness.chat("好的，我来实现", role="assistant")
```

### 任务管理

```python
# 分配任务
harness.assign_task("TASK-123", assignee="developer", priority="P0")

# 确认完成
harness.complete_task("TASK-123", summary="功能已完成")

# 查看状态
status = harness.get_status()
print(f"功能总数: {status['project_stats']['features_total']}")
print(f"已完成: {status['project_stats']['features_completed']}")
print(f"进度: {status['project_stats']['progress']}%")
```

## 自动分配规则

| 请求类型 | 优先级 | 负责人 | 文档 |
|----------|--------|--------|------|
| feature | P1 | developer | requirements.md |
| bug | P0 | developer | testing.md |
| task | P2 | developer | requirements.md |

## 使用方式

### 完整工作流

```python
from py_ha import Harness

# 1. 初始化
harness = Harness("电商平台")
harness.setup_team()

# 2. 项目经理接收需求
result = harness.receive_request("实现用户登录功能")
# 任务ID: TASK-xxx, 优先级: P1, 负责人: developer

# 3. 开发功能（项目经理调度）
dev_result = harness.develop("实现用户登录功能")

# 4. 项目经理确认完成
harness.complete_task(result['task_id'], summary="登录功能已完成")

# 5. 查看项目状态
status = harness.get_status()
```

### 快速开发（自动项目经理调度）

```python
# 一键开发（项目经理接收 → 分配 → 开发 → 确认）
result = harness.develop("实现购物车功能")
print(f"任务: {result['task_id']}")
print(f"优先级: {result['priority']}")
print(f"状态: {result['status']}")

# 一键修复 Bug
result = harness.fix_bug("支付页面超时")
```

## 工作流程

当用户请求开发功能时，按以下流程执行：

1. **需求分析** → 产品经理角色分析需求
2. **架构设计** → 架构师角色设计方案
3. **开发实现** → 开发者角色编码
4. **测试验证** → 测试员角色测试
5. **文档编写** → 文档管理员记录

## 可用工具

| 工具 | 说明 | 自动记录 |
|------|------|----------|
| `harness.record(内容)` | 智能记录（自动识别类型） | ✓ |
| `harness.chat(消息)` | 对话（默认自动记录） | ✓ |
| `harness.develop(需求)` | 一键开发功能 | ✓ |
| `harness.fix_bug(描述)` | 一键修复 Bug | ✓ |
| `harness.remember(key, value)` | 存储记忆 | ✓ |
| `harness.recall(key)` | 回忆信息 | - |

## 角色职责

| 角色 | 职责 |
|------|------|
| ProductManager | 需求分析、用户故事、验收标准 |
| Architect | 系统设计、技术选型、架构评审 |
| Developer | 编码实现、Bug修复、代码审查 |
| Tester | 测试编写、测试执行、Bug报告 |
| DocWriter | 文档编写、知识库维护 |
| ProjectManager | 任务协调、进度追踪 |

## 项目目录

```
.py_ha/
├── project.json     # 项目信息
├── documents/       # 项目文档
│   ├── requirements.md   # 需求文档
│   ├── design.md        # 设计文档
│   ├── development.md   # 开发日志
│   ├── testing.md       # 测试报告
│   └── progress.md      # 进度报告
└── sessions.json    # 会话历史
```