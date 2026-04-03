# py_ha - Harness Engineering Skill

py_ha 是一个 Harness Engineering 框架，将软件工程团队最佳实践引入 AI Agent 开发。

## 核心工作流：项目经理对接

**默认所有用户请求都由项目经理接收和处理：**

```
用户 → 项目经理（接收、分配、监督） → 开发者（执行） → 项目经理（确认完成）
```

## 多窗口任务检测

**不同窗口可以检测正在执行的任务：**

```python
from py_ha import Harness

# 窗口1: 接收需求
harness1 = Harness("项目名", workspace=".py_ha")
result = harness1.receive_request("用户需要一个登录功能")
print(f"任务ID: {result['task_id']}")

# 窗口2: 检测当前任务
harness2 = Harness("新窗口", workspace=".py_ha")
harness2.reload()  # 从文件系统重新加载最新状态
current = harness2.get_current_task()
print(f"当前任务: {current['task_desc']}")  # "用户需要一个登录功能"
print(f"有活动任务: {harness2.has_active_task()}")  # True

# 窗口1: 完成任务
harness1.complete_task(result['task_id'], summary="功能已完成")

# 窗口2: 再次检测
harness2.reload()
print(f"有活动任务: {harness2.has_active_task()}")  # False
```

## API 速查

| 方法 | 说明 | 返回 |
|------|------|------|
| `receive_request(请求, 类型)` | 项目经理接收请求 | task_id, priority, assignee |
| `get_current_task()` | 获取当前执行的任务 | task_id, task_desc, status |
| `has_active_task()` | 检查是否有活动任务 | bool |
| `reload()` | 从文件系统重新加载状态 | success |
| `chat(消息)` | 对话（自动项目经理处理） | task_info |
| `complete_task(task_id, 摘要)` | 确认完成 | success |
| `get_status()` | 获取项目状态（含当前任务） | stats, current_task |

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