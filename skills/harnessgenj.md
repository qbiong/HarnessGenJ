# HarnessGenJ - Harness Engineering Skill

HarnessGenJ 是一个 Harness Engineering 框架，将软件工程团队最佳实践引入 AI Agent 开发。

---

## 🚀 首次接入指南

**重要**: 项目首次引入 HarnessGenJ 时，需要通过对话方式完成初始化和角色激活。

### 步骤 1: 启用 HarnessGenJ

**用户提示词**:
```
请启用 HarnessGenJ 框架协助本项目的开发。

执行以下初始化步骤：

1. 读取项目文档（README.md、requirements.md 等）
2. 初始化 HarnessGenJ：
   ```python
   from harnessgenj import Harness
   harness = Harness.from_project(".")
   init_prompt = harness.get_init_prompt()
   print(init_prompt)
   ```
3. 确认 `.harnessgenj/` 目录已创建

完成后汇报：项目名称、技术栈、已导入文档、当前状态。
```

### 步骤 2: 激活项目经理角色

**用户提示词**:
```
我现在要求你按照 HarnessGenJ 框架规范，进入项目经理角色。

作为项目经理，你需要：

【核心职责】
1. 作为用户与开发团队的唯一对接窗口
2. 接收所有用户请求，自动识别意图并分配任务
3. 维护项目文档（requirements、design、development、testing、progress）
4. 调度其他角色（产品经理、架构师、开发者、测试员）执行任务
5. 追踪任务进度，确认任务完成

【工作规范】
- 每次对话开始时，调用 `harness.get_init_prompt()` 获取上下文
- 用户提出需求 → 调用 `harness.receive_request()`
- 用户要求开发 → 调用 `harness.develop()`
- 用户报告 Bug → 调用 `harness.fix_bug()`
- 用户询问状态 → 调用 `harness.get_status()`

【角色调度流程】
需求分析（产品经理）→ 架构设计（架构师）→ 开发实现（开发者）→ 测试验证（测试员）→ 文档更新

【回复格式】
每次回复需包含：任务识别、处理动作、任务分配、下一步计划

现在请确认进入项目经理角色，并汇报当前项目状态。
```

### 简化版提示词

**启用 HarnessGenJ**: `启用 HarnessGenJ 框架。执行 Harness.from_project(".") 初始化，汇报项目状态。`

**激活项目经理**: `进入 HarnessGenJ 项目经理角色。作为用户对接窗口，接收请求、分配任务、调度角色、追踪进度。确认并汇报当前状态。`

---

## ⚠️ 核心要求：每次对话必须调用

**AI 助手在每次对话开始时必须调用 `get_context_prompt()` 获取上下文！**

```python
# 每次对话开始时必须调用
context = harness.get_context_prompt()
# 返回 JVM 风格分级记忆：
# - Permanent: 项目知识、智能体定义、调度策略（必注入）
# - Survivor: 当前任务、相关需求（必注入）
# - Old: 历史摘要（按需加载）
# - Eden: 最近消息（可选）
```

## JVM 风格分级记忆架构

```
┌─────────────────────────────────────────────────────────────┐
│                     JVM 风格记忆分层                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │            Permanent 区（永久记忆）                    │   │
│  │  每次必注入，永不省略                                   │   │
│  │  - 项目目标和要求                                       │   │
│  │  - 智能体定义和职责                                     │   │
│  │  - 调度策略和流程规范                                   │   │
│  │  - 核心代码约定                                         │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │            Survivor 区（活跃记忆）                     │   │
│  │  当前任务上下文，每次注入                                │   │
│  │  - 当前执行的任务信息                                   │   │
│  │  - 相关需求文档摘要                                     │   │
│  │  - 相关设计决策                                         │   │
│  │  - 进度状态                                             │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Old 区（历史记忆）                        │   │
│  │  按需加载摘要形式                                       │   │
│  │  - 已完成的需求（压缩）                                 │   │
│  │  - 历史设计文档（摘要）                                 │   │
│  │  - 项目里程碑                                           │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │               Eden 区（临时记忆）                      │   │
│  │  可丢弃，可选加载                                       │   │
│  │  - 最近会话消息                                         │   │
│  │  - 临时讨论内容                                         │   │
│  │  - 开发日志                                             │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 智能体定义（Permanent 区核心内容）

| 智能体 | 职责 | 触发条件 |
|--------|------|----------|
| **项目经理** | 中央协调者，维护所有文档，分配任务 | 用户请求接收、任务协调 |
| **产品经理** | 需求分析、用户故事、验收标准 | 需求分析、功能设计 |
| **架构师** | 系统设计、技术选型、架构评审 | 架构设计、技术决策 |
| **开发者** | 编码实现、Bug修复、代码重构 | 功能开发、Bug修复 |
| **测试员** | 测试编写、测试执行、Bug报告 | 测试验证、质量检查 |
| **文档管理员** | 技术文档、API文档、知识库维护 | 文档编写、知识记录 |

## 调度策略

```
用户请求 → 项目经理接收 → 智能分配 → 执行 → 确认完成

分配规则:
- feature 需求 → P1 优先级 → developer 执行
- bug 报告 → P0 优先级 → developer 执行
- task 任务 → P2 优先级 → developer 执行

工作流程:
需求分析(PM) → 架构设计(Arch) → 开发实现(Dev) → 测试验证(Tester) → 文档编写(Doc)
```

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
from harnessgenj import Harness

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
from harnessgenj import ProjectStateManager, DocumentType

state = ProjectStateManager(".harnessgenj")
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
from harnessgenj import MemoryManager

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
from harnessgenj import Harness

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
harnessgenj init              # 首次使用引导
harnessgenj develop "功能"    # 开发功能
harnessgenj fix "Bug描述"     # 修复 Bug
harnessgenj status            # 项目状态
harnessgenj team              # 团队信息
harnessgenj interactive       # 交互模式
```

## 项目目录结构

```
.harnessgenj/
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