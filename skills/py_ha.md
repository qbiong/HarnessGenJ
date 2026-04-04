# py_ha - Harness Engineering Skill

py_ha 是一个 Harness Engineering 框架，将软件工程团队最佳实践引入 AI Agent 开发。

## ⚠️ 多轮对话保持（重要）

**AI 助手在每次对话开始时必须调用 `get_context_prompt()` 获取上下文提示！**

```python
# 每次对话开始时
context = harness.get_context_prompt()
# 返回: 项目知识摘要 + 当前任务 + 进度 + 核心方法提示
```

这确保了：
1. AI 始终记住要使用 py_ha 的方法
2. 当前任务状态被正确传递
3. 项目进度信息保持同步

## Harness 6 大核心能力

| 能力 | 模块 | 说明 |
|------|------|------|
| **AGENTS.md** | `AgentsKnowledgeManager` | 项目知识文件，自动注入上下文 |
| **Hooks** | `HooksManager` | 质量门禁，确定性规则约束 |
| **Context Engine** | `ContextEngine` | 上下文压缩/摘要，对抗 Context Rot |
| **Memory** | `MemoryManager` | JVM 风格分代记忆管理 |
| **FileSystem** | `VirtualFS` | 虚拟文件系统，多后端支持 |
| **HumanLoop** | `HumanLoop` | 人机交互，审批节点 |

## 用户对话指南（AI 助手必读）

**用户只需自然对话，AI 助手自动调用相应方法：**

### 用户说："我需要/想要/添加一个功能"

→ AI 调用 `harness.receive_request("用户描述", request_type="feature")`

```python
# 用户: "我需要一个用户登录功能"
result = harness.receive_request("用户需要一个用户登录功能", request_type="feature")
# 自动分配: task_id, priority=P1, assignee=developer
```

### 用户说："有个 Bug/问题/错误"

→ AI 调用 `harness.receive_request("问题描述", request_type="bug")`

```python
# 用户: "登录页面验证码显示异常"
result = harness.receive_request("登录页面验证码显示异常", request_type="bug")
# 自动分配: task_id, priority=P0, assignee=developer
```

### 用户说："开发/实现这个功能"

→ AI 调用 `harness.develop("功能描述")`

```python
# 用户: "帮我开发用户登录功能"
result = harness.develop("实现用户登录功能")
```

### 用户说："修复这个 Bug"

→ AI 调用 `harness.fix_bug("Bug描述")`

```python
# 用户: "帮我修复验证码问题"
result = harness.fix_bug("登录页面验证码显示异常")
```

### 用户说："项目进展如何/当前状态"

→ AI 调用 `harness.get_status()` 或 `harness.get_report()`

```python
status = harness.get_status()
print(f"功能总数: {status['project_stats']['features_total']}")
print(f"当前任务: {status['current_task']}")
```

### 用户说："当前在做什么"

→ AI 调用 `harness.get_current_task()`

```python
current = harness.get_current_task()
print(f"当前任务: {current['task_desc']}")
```

## 核心工作流：项目经理对接

**所有用户请求都由项目经理接收和处理：**

```
用户对话 → AI识别意图 → 项目经理接收 → 自动分配 → 开发者执行 → 项目经理确认
```

**项目经理自动完成**：
1. 接收用户请求
2. 分配优先级（P0/P1/P2）
3. 分配负责人（developer）
4. 创建任务ID
5. 更新项目文档和统计

## 一行代码完成所有工作

```python
from py_ha import Harness

# 初始化（默认持久化）
harness = Harness("项目名")
harness.setup_team()

# 用户对话 → AI 自动处理
harness.chat("我需要一个登录功能")  # 自动: 创建任务、分配优先级、记录文档
harness.chat("帮我开发登录功能")    # 自动: 执行开发流程
harness.chat("项目进展如何")        # 自动: 返回项目状态
```

## 自动分配规则

| 用户意图 | 识别关键词 | 自动分配 |
|----------|-----------|----------|
| 新需求 | 需要、想要、添加、新增、功能 | P1, developer, requirements.md |
| Bug报告 | bug、问题、错误、异常、失败 | P0, developer, testing.md |
| 开发请求 | 开发、实现、帮我做 | 执行 develop() |
| 状态查询 | 进展、状态、当前 | 返回 get_status() |

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