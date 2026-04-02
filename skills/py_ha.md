# py_ha - Harness Engineering Skill

py_ha 是一个 Harness Engineering 框架，将软件工程团队最佳实践引入 AI Agent 开发。

## 核心工作流：项目经理对接

**默认所有用户请求都由项目经理接收和处理：**

```
用户 → 项目经理（接收、分配、监督） → 开发者（执行） → 项目经理（确认完成）
```

### 项目经理职责

1. **接收请求**：所有用户需求/Bug通过项目经理接收
2. **分配任务**：自动分配优先级和负责人
3. **更新状态**：更新项目文档和统计数据
4. **监督完成**：跟踪任务进度并确认完成

## AI 对话核心方法

### receive_request() - 项目经理接收请求

```python
from py_ha import Harness

harness = Harness("项目名", persistent=True)
harness.setup_team()

# 项目经理接收需求（自动分配优先级、负责人、任务ID）
result = harness.receive_request("用户需要一个登录功能")
# 返回: task_id, priority, assignee, status

# 项目经理接收 Bug 报告
result = harness.receive_request("登录页面验证码异常", request_type="bug")
```

### chat() - 自动通过项目经理处理

```python
# 用户提出需求 → 项目经理自动接收并分配
harness.chat("我需要一个搜索功能")
# 自动创建任务、分配优先级、更新统计

# AI 回复
harness.chat("好的，我来实现搜索模块", role="assistant")
```

### complete_task() - 项目经理确认完成

```python
# 项目经理标记任务完成
harness.complete_task("TASK-1234567890", summary="功能开发完成")
```

## 工作流程示例

```python
from py_ha import Harness

# 1. 初始化项目
harness = Harness("电商平台", persistent=True)
harness.setup_team()

# 2. 用户提出需求 → 项目经理接收
result = harness.receive_request("实现用户登录功能")
print(f"任务已创建: {result['task_id']}")
print(f"优先级: {result['priority']}")  # P1
print(f"负责人: {result['assignee']}")  # developer

# 3. 开发功能
dev_result = harness.develop("实现用户登录功能")

# 4. 项目经理确认完成
harness.complete_task(result['task_id'], summary="登录功能已完成")

# 5. 查看项目状态
status = harness.get_status()
print(f"功能总数: {status['project_stats']['features_total']}")
print(f"已完成: {status['project_stats']['features_completed']}")
print(f"进度: {status['project_stats']['progress']}%")
```

## 自动分配规则

| 请求类型 | 默认优先级 | 默认负责人 | 记录文档 |
|----------|------------|------------|----------|
| feature | P1 | developer | requirements.md |
| bug | P0 | developer | testing.md |
| task | P2 | developer | requirements.md |

## API 速查

| 方法 | 说明 | 返回 |
|------|------|------|
| `receive_request(请求, 类型)` | 项目经理接收请求 | task_id, priority, assignee |
| `chat(消息)` | 对话（自动项目经理处理） | task_info（如创建任务） |
| `assign_task(task_id, 负责人)` | 分配任务 | success |
| `complete_task(task_id, 摘要)` | 确认完成 | success |
| `develop(需求)` | 快速开发（项目经理调度） | task_id, status |
| `fix_bug(描述)` | 快速修复（项目经理调度） | task_id, status |
| `get_status()` | 获取项目状态 | stats, documents |
| `get_requirements()` | 获取需求文档 | content |
| `get_progress()` | 获取进度报告 | content |

## 角色系统

| 角色 | 职责 | 调用场景 |
|------|------|----------|
| ProductManager | 需求分析、用户故事 | 分析需求时 |
| Architect | 架构设计、技术选型 | 设计系统时 |
| Developer | 编码、Bug修复、代码审查 | 开发实现时 |
| Tester | 测试编写、测试执行 | 质量验证时 |
| DocWriter | 文档编写、知识库维护 | 文档记录时 |
| ProjectManager | 任务协调、进度追踪 | 项目管理时 |

## 工作流

```
需求分析 → 架构设计 → 开发实现 → 测试验证 → 文档编写 → 发布评审
```

**预定义流水线**：
- `feature`: 需求→开发→测试（快速功能开发）
- `bugfix`: 分析→修复→验证（Bug修复）
- `standard`: 完整流程

```python
harness.run_pipeline("feature", feature_request="用户登录")
harness.run_pipeline("bugfix", bug_report="支付超时")
```

## 项目管理（渐进式披露）

每个角色只获取必要信息，减少 Token 消耗：

```python
from py_ha import ProjectStateManager, DocumentType

state = ProjectStateManager(".py_ha")
state.initialize("项目名", "技术栈")

# 更新文档
state.update_document(DocumentType.REQUIREMENTS, "内容", "product_manager")

# 为角色生成上下文
dev_context = state.get_context_for_role("developer")  # 最小信息
pm_context = state.get_context_for_role("project_manager")  # 完整信息
```

**文档类型**：
- `REQUIREMENTS` - 需求文档
- `DESIGN` - 设计文档
- `DEVELOPMENT` - 开发日志
- `TESTING` - 测试报告
- `PROGRESS` - 进度报告

## JVM 风格记忆管理

```python
from py_ha import MemoryManager

manager = MemoryManager()

# 存储重要知识（Permanent 区，永不回收）
manager.store_important_knowledge("key", "value")

# 分配普通记忆（Eden 区）
manager.allocate_memory("内容", importance=50)

# 触发 GC
manager.invoke_gc_minor()
```

## 多会话管理

```python
# 主开发对话
harness.chat("正在开发功能")

# 切换到产品经理对话
harness.switch_session("product_manager")
harness.chat("需求讨论")

# 切回主开发
harness.switch_session("development")
```

## 使用场景示例

### 场景1：用户说"帮我开发一个登录功能"

```python
from py_ha import Harness

harness = Harness("用户系统")
harness.setup_team()
result = harness.develop("实现用户登录功能，支持用户名密码和手机验证码")
```

### 场景2：用户说"有个支付超时的 Bug"

```python
harness.fix_bug("订单支付时偶现超时问题")
```

### 场景3：用户说"帮我分析一下需求"

```python
harness.analyze("用户需要一个仪表盘来查看销售数据")
```

### 场景4：用户说"帮我设计系统架构"

```python
harness.design("微服务架构的电商系统，包含用户、商品、订单服务")
```

### 场景5：用户说"记住这个重要信息"

```python
harness.remember("project_goal", "构建电商平台", important=True)
```

### 场景6：用户说"项目进展如何"

```python
print(harness.get_report())
```

## CLI 命令

```bash
py-ha init              # 首次使用引导
py-ha develop "功能"    # 开发功能
py-ha fix "Bug描述"     # 修复 Bug
py-ha status            # 项目状态
py-ha team              # 团队信息
py-ha interactive       # 交互模式
```

## 项目目录结构

```
.py_ha/
├── project.json         # 项目信息
├── state.json           # 工作状态
├── sessions.json        # 会话历史
├── documents/           # 项目文档
│   ├── requirements.md
│   ├── design.md
│   ├── development.md
│   ├── testing.md
│   └── progress.md
└── knowledge/           # 知识库
```