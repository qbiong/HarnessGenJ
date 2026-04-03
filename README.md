# py_ha - Python Harness for AI Agents

<div align="center">

**基于 Harness Engineering 理念的 AI Agent 协作框架**

通过**角色驱动**和**工作流驱动**实现高效的开发协作

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-117%20passed-green.svg)](tests/)

</div>

---

## 目录

- [核心理念](#核心理念)
- [安装方式](#安装方式)
- [快速开始](#快速开始)
- [核心功能](#核心功能)
- [项目管理与渐进式披露](#项目管理与渐进式披露)
- [JVM风格记忆管理](#jvm风格记忆管理)
- [工作流系统](#工作流系统)
- [多会话记忆](#多会话记忆)
- [项目结构](#项目结构)
- [更新日志](#更新日志)

---

## 核心理念

### 为什么选择 py_ha？

py_ha 将软件工程团队的最佳实践引入 AI Agent 开发，让 AI 像真实团队一样协作：

| 传统方式 | py_ha 方式 |
|----------|-----------|
| 抽象的 Agent 概念 | 真实团队角色（开发、测试、产品等） |
| 难以追踪的任务 | 完整的工作流和阶段 |
| 混乱的记忆管理 | JVM 风格的分代记忆系统 |
| 复杂的数据库配置 | 轻量化存储，开箱即用 |
| Token 消耗过大 | 渐进式披露，按需加载 |

### 角色驱动协作

每个角色有明确的职责和技能集：

| 角色 | 职责 | 核心技能 |
|------|------|----------|
| **ProductManager** | 需求管理 | 需求分析、用户故事、验收标准、优先级排序 |
| **Architect** | 架构设计 | 系统设计、技术选型、架构评审、设计模式 |
| **Developer** | 功能开发 | 编码实现、Bug修复、代码重构、代码审查 |
| **Tester** | 质量保证 | 测试编写、测试执行、Bug报告、覆盖率分析 |
| **DocWriter** | 文档管理 | 技术文档、API文档、用户手册、知识库维护 |
| **ProjectManager** | 项目协调 | 任务协调、进度追踪、资源分配、风险管理 |

---

## 安装方式

```bash
# 从源码安装
git clone https://github.com/py-ha/py-ha.git
cd py-ha
pip install -e .

# 开发模式（包含测试工具）
pip install -e ".[dev]"
```

---

## 快速开始

### 用户对话指南（AI 助手必读）

**用户只需自然对话，AI 助手自动调用相应方法：**

| 用户说 | AI 调用 | 自动处理 |
|--------|---------|----------|
| "我需要一个登录功能" | `receive_request("...", "feature")` | 创建任务、分配P1、记录文档 |
| "有个Bug/问题" | `receive_request("...", "bug")` | 创建任务、分配P0、记录文档 |
| "帮我开发这个功能" | `develop("...")` | 执行开发流程 |
| "帮我修复这个Bug" | `fix_bug("...")` | 执行修复流程 |
| "项目进展如何" | `get_status()` | 返回项目状态 |
| "当前在做什么" | `get_current_task()` | 返回当前任务 |

### 一行代码完成所有工作

```python
from py_ha import Harness

harness = Harness("项目名")
harness.setup_team()

# 用户对话 → 自动处理
harness.chat("我需要一个登录功能")  # 自动: 创建任务、分配优先级、记录文档
```

### 核心工作流

### 项目经理对接用户

**所有用户请求都由项目经理接收和处理：**

```
用户 → 项目经理（接收、分配、监督） → 开发者（执行） → 项目经理（确认完成）
```

**项目经理职责**：
1. 接收用户需求/Bug报告
2. 自动分配优先级和负责人
3. 更新项目文档和统计数据
4. 监督任务进度并确认完成

### receive_request() - 项目经理接收请求

```python
from py_ha import Harness

harness = Harness("项目名", persistent=True)
harness.setup_team()

# 项目经理接收需求（自动分配优先级、负责人、任务ID）
result = harness.receive_request("用户需要一个登录功能")
print(f"任务ID: {result['task_id']}")      # TASK-xxx
print(f"优先级: {result['priority']}")     # P1
print(f"负责人: {result['assignee']}")     # developer

# 项目经理接收 Bug 报告（默认 P0 高优先级）
result = harness.receive_request("登录页面异常", request_type="bug")
```

### chat() - 自动项目经理处理

```python
# 用户提出需求 → 项目经理自动接收并分配
harness.chat("我需要一个搜索功能")
# 自动: 创建任务、分配优先级、更新统计

# AI 回复
harness.chat("好的，我来实现搜索模块", role="assistant")
```

### 自动分配规则

| 请求类型 | 默认优先级 | 默认负责人 | 记录文档 |
|----------|------------|------------|----------|
| feature | P1 | developer | requirements.md |
| bug | P0 | developer | testing.md |
| task | P2 | developer | requirements.md |

### AI 对话自动记录（核心功能）

AI 只需调用一个方法，自动识别内容类型并持久化到对应文档：

```python
from py_ha import Harness

harness = Harness("项目名", persistent=True)
harness.setup_team()

# 智能识别并自动记录
harness.record("用户需要一个登录功能")    # → requirements.md
harness.record("发现登录页面验证码异常")  # → testing.md
harness.record("已完成登录模块开发")      # → progress.md
harness.record("正在实现用户认证逻辑")    # → development.md

# chat() 方法默认自动记录
harness.chat("我需要添加一个搜索功能")    # 用户消息自动记录
harness.chat("好的，我来实现", role="assistant")  # AI回复自动记录
```

**自动识别规则**：

| 优先级 | 关键词 | 记录位置 |
|--------|--------|----------|
| 1（最高）| 完成、已、进度、状态、更新、通过、成功 | progress.md |
| 2 | bug、问题、错误、异常、失败、修复 | testing.md |
| 3 | 需求、功能、需要、添加、新增、设计 | requirements.md |
| 4（默认）| 实现、开发、编写、修改、优化 | development.md |

### 一行代码开发功能

```python
from py_ha import Harness

harness = Harness("我的项目")
harness.setup_team()

# 一键开发功能
result = harness.develop("实现用户登录功能")
print(f"状态: {result['status']}")  # completed

# 一键修复 Bug
result = harness.fix_bug("登录页面验证码无法显示")
```

### 组建自定义团队

```python
harness = Harness("电商平台")

# 自定义团队成员
harness.setup_team({
    "product_manager": "王产品",
    "developer": "李开发",
    "tester": "张测试",
})

harness.develop("实现购物车功能")
```

---

## 核心功能

### 快速开发

一键完成需求分析 → 开发实现 → 测试验证：

```python
harness.develop("实现用户注册功能，支持邮箱和手机号注册")
```

### 快速修复

一键完成 Bug分析 → 代码修复 → 验证测试：

```python
harness.fix_bug("支付页面偶尔超时")
```

### 需求分析

```python
result = harness.analyze("用户需要一个仪表盘查看销售数据")
# 输出: 需求列表、用户故事、验收标准
```

### 架构设计

```python
result = harness.design("微服务架构的电商系统")
# 输出: 架构图、技术选型、设计决策
```

### 记忆系统

JVM 风格的记忆管理，重要信息永不丢失：

```python
# 存储重要知识（进入 Permanent 区，永不回收）
harness.remember("project_goal", "构建电商平台", important=True)

# 回忆信息
goal = harness.recall("project_goal")
```

---

## 项目管理与渐进式披露

### 核心概念

项目采用**渐进式披露**原则，每个角色只获取自己需要的信息：

```
┌─────────────────────────────────────────────────────────────┐
│                    项目经理（中央协调者）                       │
│                    可访问所有文档和状态                         │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ↓                     ↓                     ↓
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│   产品经理     │    │    开发者      │    │    测试员      │
│ 需求文档完整   │    │ 项目信息+摘要  │    │ 测试相关+摘要  │
│ 其他文档摘要   │    │ 当前任务完整   │    │ 需求摘要      │
└───────────────┘    └───────────────┘    └───────────────┘
```

### 使用示例

```python
from py_ha import ProjectStateManager, DocumentType

# 创建项目状态管理器
state = ProjectStateManager(".py_ha")
state.initialize("电商平台", "Python + FastAPI")

# 更新需求文档
state.update_document(
    DocumentType.REQUIREMENTS,
    "# 需求\n## 用户登录\n...",
    "product_manager"
)

# 为开发者生成最小上下文
context = state.get_context_for_role("developer")
# 只包含: 项目信息 + 需求摘要 + 设计摘要
```

### 文档所有权

| 文档 | 所有者 | 可见角色 |
|------|--------|---------|
| 需求文档 | 产品经理 | PM, 产品经理, 开发者(只读) |
| 设计文档 | 架构师 | PM, 架构师, 开发者(只读) |
| 开发日志 | 开发者 | PM, 开发者 |
| 测试报告 | 测试员 | PM, 测试员, 开发者(只读) |
| 进度报告 | 项目经理 | 所有角色 |

---

## JVM风格记忆管理

### 分代存储架构

```
┌─────────────────────────────────────────────────────────────┐
│                     JVM 风格记忆堆                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │            Permanent 区（永久代）                      │   │
│  │  项目核心信息、重要知识 - 永不回收                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Old 区（老年代）                          │   │
│  │  长期存活记忆、设计文档 - Major GC 清理                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌───────────────────┐    ┌───────────────────┐           │
│  │   Survivor 区     │ ←→ │   Survivor 区     │           │
│  │  活跃文档、需求    │    │   GC 交换区       │           │
│  └───────────────────┘    └───────────────────┘           │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │               Eden 区（新生代）                        │   │
│  │  新消息、临时内容 - Minor GC 频繁清理                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 文档区域映射

| 区域 | 文档类型 | 特点 |
|------|----------|------|
| Permanent | 项目信息、团队配置 | 永不回收，始终加载 |
| Old | 设计文档、已完成需求 | 长期存储，按需加载摘要 |
| Survivor | 当前需求、进度报告 | 活跃文档，自动加载摘要 |
| Eden | 开发日志、测试报告 | 临时内容，按需加载 |

### 使用示例

```python
from py_ha import MemoryManager, MemoryRegion

manager = MemoryManager()

# 分配记忆（自动进入 Eden 区）
entry = manager.allocate_memory("用户需要登录功能", importance=50)

# 存储重要知识（进入 Permanent 区）
manager.store_important_knowledge("project_goal", "构建电商平台")

# 触发 GC 清理不活跃记忆
result = manager.invoke_gc_minor()
print(f"清理了 {len(result.collected_ids)} 条记忆")

# 获取健康报告
health = manager.get_health_report()
print(f"状态: {health['status']}")
```

---

## 工作流系统

### 预定义流水线

```
┌─────────────────────────────────────────────────────────────────┐
│                     标准开发流水线                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  需求分析 ──► 架构设计 ──► 开发实现 ──► 测试验证 ──► 文档编写 ──► 发布评审  │
│  (PM)        (Arch)      (Dev)       (Tester)     (Doc)       (Mgr)    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

| 流水线 | 流程 | 用途 |
|--------|------|------|
| `standard` | 需求→设计→开发→测试→文档→发布 | 完整开发流程 |
| `feature` | 需求→开发→测试 | 快速功能开发 |
| `bugfix` | 分析→修复→验证 | Bug修复 |

### 使用示例

```python
# 运行功能开发流程
result = harness.run_pipeline("feature", feature_request="用户登录")

# 运行标准流程
result = harness.run_pipeline("standard", user_request="电商平台")

# 运行 Bug 修复流程
result = harness.run_pipeline("bugfix", bug_report="支付超时")
```

---

## 多会话记忆

在项目开发过程中维护多个独立的对话会话：

```python
# 主开发流程
harness.chat("正在开发购物车功能")

# 切换到产品经理对话
harness.switch_session("product_manager")
harness.chat("购物车需要支持哪些功能？")

# 切回主开发
harness.switch_session("development")
harness.chat("需求已确认，继续开发")
```

---

## 项目结构

```
py_ha/
├── src/py_ha/
│   ├── engine.py              # 主入口 Harness 类
│   ├── session.py             # 多会话管理
│   ├── guide.py               # 首次使用引导
│   ├── cli.py                 # 命令行接口
│   │
│   ├── roles/                 # 角色系统
│   │   ├── base.py           # 角色基类
│   │   ├── developer.py      # 开发者
│   │   ├── tester.py         # 测试员
│   │   ├── product_manager.py # 产品经理
│   │   ├── architect.py      # 架构师
│   │   ├── doc_writer.py     # 文档管理员
│   │   └── project_manager.py # 项目经理
│   │
│   ├── workflow/              # 工作流系统
│   │   ├── pipeline.py       # 流水线定义
│   │   ├── coordinator.py    # 协调器
│   │   └── context.py        # 上下文
│   │
│   ├── memory/                # JVM风格记忆管理
│   │   ├── heap.py           # 分代堆内存
│   │   ├── gc.py             # 垃圾回收
│   │   ├── hotspot.py        # 热点检测
│   │   ├── assembler.py      # 自动装配
│   │   └── manager.py        # 记忆管理器
│   │
│   ├── project/               # 项目管理
│   │   ├── document.py       # 文档实体 + JVM区域映射
│   │   └── state.py          # 项目状态管理
│   │
│   ├── kernel/                # 任务内核
│   │   ├── kernel.py         # 内核
│   │   ├── task.py           # 任务定义
│   │   ├── queue.py          # 任务队列
│   │   ├── producer.py       # 生产者
│   │   ├── consumer.py       # 消费者
│   │   └── scheduler.py      # 调度器
│   │
│   ├── storage/               # 轻量化存储
│   │   ├── memory.py         # 内存存储
│   │   ├── json_store.py     # JSON存储
│   │   ├── markdown.py       # Markdown存储
│   │   └── manager.py        # 存储管理器
│   │
│   ├── harness/               # 可选功能
│   │   ├── planning.py       # Todo管理
│   │   ├── filesystem.py     # 虚拟文件系统
│   │   ├── sandbox.py        # 代码沙箱
│   │   └── human_loop.py     # 人机交互
│   │
│   └── mcp/                   # MCP Server
│       └── server.py         # MCP工具定义
│
├── tests/                     # 测试文件
└── examples/                  # 使用示例
```

---

## 更新日志

### v0.3.2 (当前版本)

**新增：项目经理工作流**

- `receive_request()`: 项目经理接收用户请求，自动分配优先级和负责人
- `assign_task()`: 项目经理分配任务
- `complete_task()`: 项目经理确认任务完成
- 默认会话改为项目经理，所有用户请求通过项目经理对接
- 项目统计自动更新：功能总数、已完成、进度百分比

**新增：多窗口任务检测**

- `get_current_task()`: 获取当前执行的任务
- `has_active_task()`: 检查是否有活动任务
- `reload()`: 从文件系统重新加载最新状态
- 不同窗口可以检测正在执行的需求

**工作流程优化**：
- 用户 → 项目经理 → 开发者 → 项目经理确认
- 需求自动记录到 requirements.md（带任务ID、优先级、负责人）
- 进度自动记录到 progress.md
- 统计数据实时更新

### v0.3.1

**新增：AI 对话智能自动记录**

- `record()` 方法：智能识别内容类型并自动持久化到对应文档
- `chat()` 方法增强：默认自动调用 `record()` 记录对话内容
- 便捷方法：`record_requirement()`、`record_bug()`、`record_progress()`
- 关键词优先级匹配：进度 > Bug > 需求 > 开发

**解决问题**：
- AI 对话时无需显式调用文档管理方法
- 不同对话框可以维护同一份项目文件
- 所有操作自动持久化到 `.py_ha/documents/` 目录

### v0.3.0

**架构重构：精简核心，消除冗余**

- 删除未使用的 `runtime/` 模块（与 `engine.py` 重复设计）
- 删除未使用的 `core/` 模块
- 合并 `project/memory_integration.py` 到 `document.py`
- 将 JVM 区域映射整合到文档系统

**新增：项目管理与渐进式披露**

- `ProjectStateManager`: 项目状态管理器，提供渐进式信息披露
- `ProjectDocument`: 文档实体，支持所有权和版本管理
- 文档按 JVM 风格分代：Permanent(永久) / Old(长期) / Survivor(活跃) / Eden(临时)
- 每个角色只获取最小必要上下文，减少 Token 消耗

**代码量变化**

| 指标 | v0.2.0 | v0.3.0 | 减少 |
|------|--------|--------|------|
| Python 文件 | 57 | 51 | -6 |
| 代码行数 | 12,574 | 11,435 | -1,139 |
| 测试数量 | 133 | 117 | -16 |

### v0.2.3

**新增：完整的持久化存储支持**

- 默认开启持久化，所有工作内容自动保存到 `.py_ha/` 目录
- 会话历史、项目状态、知识库持久化

### v0.2.2

**新增：首次使用引导系统**

- 交互式首次使用引导
- 欢迎信息生成
- CLI 命令：`py-ha init`、`py-ha welcome`

### v0.2.1

**新增：多会话记忆**

- 支持 7 种会话类型的独立对话历史
- 会话切换和持久化

### v0.2.0

**初始版本**

- 角色驱动协作：6 种团队角色
- 工作流驱动：标准/功能/Bug修复流程
- JVM 风格记忆管理
- 轻量化存储
- MCP 集成
- CLI 命令

---

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

---

<div align="center">

**如果这个项目对你有帮助，请给一个 Star！**

</div>