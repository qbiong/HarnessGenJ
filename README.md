# py_ha - Python Harness for AI Agents

<div align="center">

**基于 Harness Engineering 理念的 AI Agent 协作框架**

通过**角色驱动**和**工作流驱动**实现高效的开发协作

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-80%20passed-green.svg)](tests/)

</div>

---

## 目录

- [核心理念](#核心理念)
- [安装方式](#安装方式)
- [首次接入流程](#首次接入流程)
- [快速开始](#快速开始)
- [从现有项目初始化](#从现有项目初始化)
- [核心功能](#核心功能)
- [JVM风格记忆管理](#jvm风格记忆管理)
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
| 无持久化 | 自动持久化，重启恢复 |

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
# 从 PyPI 安装（发布后）
pip install py-ha

# 从源码安装
git clone https://github.com/py-ha/py-ha.git
cd py-ha
pip install -e .

# 开发模式（包含测试工具）
pip install -e ".[dev]"
```

---

## 首次接入流程

**重要**: 项目首次引入 py_ha 时，需要通过对话方式完成初始化和角色激活。

### 接入流程概览

```
步骤 1: 启用 py_ha     →  AI 读取项目文档，完成初始化
步骤 2: 激活项目经理   →  AI 进入项目经理角色
步骤 3: 持续对话推进   →  用户直接对话项目经理推进项目
```

### 步骤 1: 启用 py_ha

在 Claude Code 对话中发送以下提示词：

```
请启用 py_ha 框架协助本项目的开发。

执行以下初始化步骤：
1. 读取项目文档（README.md、requirements.md 等）
2. 初始化 py_ha：
   from py_ha import Harness
   harness = Harness.from_project(".")
   print(harness.get_init_prompt())
3. 确认 `.py_ha/` 目录已创建

完成后汇报：项目名称、技术栈、已导入文档、当前状态。
```

### 步骤 2: 激活项目经理角色

初始化完成后，发送以下提示词让 AI 进入项目经理角色：

```
我现在要求你按照 py_ha 框架规范，进入项目经理角色。

作为项目经理，你需要：

【核心职责】
1. 作为用户与开发团队的唯一对接窗口
2. 接收所有用户请求，自动识别意图并分配任务
3. 维护项目文档（requirements、design、development、testing、progress）
4. 调度其他角色（产品经理、架构师、开发者、测试员）执行任务
5. 追踪任务进度，确认任务完成

【工作规范】
- 每次对话开始时，调用 harness.get_init_prompt() 获取上下文
- 用户提出需求 → 调用 harness.receive_request()
- 用户要求开发 → 调用 harness.develop()
- 用户报告 Bug → 调用 harness.fix_bug()
- 用户询问状态 → 调用 harness.get_status()

【回复格式】
每次回复需包含：任务识别、处理动作、任务分配、下一步计划

现在请确认进入项目经理角色，并汇报当前项目状态。
```

### 简化版提示词（快速激活）

| 场景 | 提示词 |
|------|--------|
| 启用 py_ha | `启用 py_ha 框架。执行 Harness.from_project(".") 初始化，汇报项目状态。` |
| 激活项目经理 | `进入 py_ha 项目经理角色。作为用户对接窗口，接收请求、分配任务、调度角色、追踪进度。确认并汇报当前状态。` |

### 持续对话推进

激活项目经理后，用户可直接对话推进项目：

| 用户说 | 项目经理响应 |
|--------|--------------|
| "我需要一个登录功能" | 创建任务 TASK-xxx，分配 P1，负责人 developer |
| "有个 Bug：支付超时" | 创建任务 TASK-xxx，分配 P0，负责人 developer |
| "帮我开发购物车" | 调度开发流程：需求→设计→开发→测试 |
| "项目进展如何" | 汇报当前进度、已完成任务、活动任务 |

详细说明请参阅 [首次接入指南](docs/ONBOARDING_GUIDE.md)。

---

## 快速开始

### 方式一：直接创建（新项目）

```python
from py_ha import Harness

# 创建项目（默认持久化到 .py_ha/ 目录）
harness = Harness("我的项目")

# 存储核心知识
harness.remember("tech_stack", "Python + FastAPI", importance=100)

# 接收需求
result = harness.receive_request("实现用户登录功能")
print(f"任务ID: {result['task_id']}")  # TASK-xxx
print(f"优先级: {result['priority']}")  # P1

# 获取上下文（用于 Claude Code 对话）
context = harness.get_init_prompt()
```

### 方式二：从现有项目初始化（推荐）

如果你已经有项目文档（README.md、requirements.md 等），可以直接导入：

```python
from py_ha import Harness

# 从项目目录初始化（自动扫描并导入文档）
harness = Harness.from_project("/path/to/your/project")

# 自动完成：
# - 提取项目名称和描述
# - 识别技术栈
# - 导入需求文档、设计文档等
# - 生成完整的项目上下文

# 获取初始化提示
init_prompt = harness.get_init_prompt()
print(init_prompt)  # 包含：API指南 + 项目信息 + 文档内容 + 当前任务
```

### Claude Code 对话初始化

每次新对话开始时：

```python
from py_ha import Harness

# 初始化（自动恢复之前的工作）
harness = Harness("我的项目")

# 获取上下文提示（注入到对话中）
init_prompt = harness.get_init_prompt()

# 之后正常对话
harness.chat("我需要一个购物车功能")  # 自动识别并创建任务
```

### 用户对话自动处理

| 用户说 | AI 调用 | 自动处理 |
|--------|---------|----------|
| "我需要/要/添加功能" | `receive_request("...", "feature")` | 创建任务、分配P1、记录文档 |
| "有bug/问题/错误" | `receive_request("...", "bug")` | 创建任务、分配P0、记录文档 |
| "帮我开发" | `develop("...")` | 执行开发流程 |
| "帮我修复" | `fix_bug("...")` | 执行修复流程 |
| "项目进展如何" | `get_status()` | 返回项目状态 |

---

## 从现有项目初始化

### `Harness.from_project()` 功能

自动扫描项目文档并导入到记忆系统：

```python
harness = Harness.from_project("/path/to/project")
```

### 自动识别的文档

| 文件名 | 导入到 |
|--------|--------|
| README.md | 项目名称、描述、技术栈提取 |
| requirements.md / 需求.md | requirements 文档 |
| design.md / 设计.md | design 文档 |
| development.md / 开发.md | development 文档 |
| testing.md / 测试.md | testing 文档 |
| progress.md / 进度.md | progress 文档 |
| docs/*.md | 核心知识存储 |

### 自动检测的技术栈

- **语言**: Python, Node.js, Go, Rust, Java
- **框架**: FastAPI, Django, Flask, React, Vue
- **数据库**: PostgreSQL, MySQL, MongoDB, Redis
- **部署**: Docker

### 完整示例

```python
# 假设项目目录：
# my-project/
# ├── README.md           # 项目说明
# ├── requirements.md     # 需求文档
# ├── design.md           # 设计文档
# └── pyproject.toml      # Python 配置

from py_ha import Harness

# 一行代码完成初始化
harness = Harness.from_project("my-project")

# 查看导入结果
print(harness.project_name)           # 从 README 标题提取
print(harness.recall("tech_stack"))   # 自动检测的技术栈
print(harness.memory.get_document("requirements"))  # 需求文档

# 开始开发
harness.receive_request("实现购物车功能")
```

---

## 核心功能

### 1. 接收用户请求

```python
# 接收功能需求
result = harness.receive_request("实现用户登录功能", request_type="feature")
# 返回: {"task_id": "TASK-xxx", "priority": "P1", "assignee": "developer"}

# 接收 Bug 报告
result = harness.receive_request("登录页面报错", request_type="bug")
# 返回: {"task_id": "TASK-xxx", "priority": "P0", ...}
```

### 2. 记忆管理

```python
# 存储核心知识（Permanent 区，永不回收）
harness.remember("project_goal", "构建电商平台", importance=100)

# 回忆知识
goal = harness.recall("project_goal")

# 记录到文档
harness.record("完成了用户认证模块", context="开发进度")
```

### 3. 对话记录

```python
# 用户消息（自动识别需求/Bug）
harness.chat("我需要一个搜索功能")

# AI 回复
harness.chat("好的，我来实现搜索模块", role="assistant")
```

### 4. 任务完成

```python
# 标记任务完成
harness.complete_task("TASK-xxx", "功能已完成，测试通过")
```

### 5. 状态查询

```python
# 获取项目状态
status = harness.get_status()
# 包含：项目信息、团队、统计、记忆状态、当前任务

# 获取项目报告
report = harness.get_report()
```

---

## JVM风格记忆管理

### 分代存储架构

```
┌─────────────────────────────────────────────────────────────┐
│                     JVM 风格记忆堆                            │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐   │
│  │            Permanent 区（永久代）                      │   │
│  │  项目核心信息、重要知识 - 永不回收                       │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Old 区（老年代）                          │   │
│  │  长期存活记忆、设计文档 - Major GC 清理                 │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌───────────────────┐    ┌───────────────────┐           │
│  │   Survivor 区     │ ←→ │   Survivor 区     │           │
│  │  活跃文档、需求    │    │   GC 交换区       │           │
│  └───────────────────┘    └───────────────────┘           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │               Eden 区（新生代）                        │   │
│  │  新消息、临时内容 - Minor GC 频繁清理                   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 渐进式披露

每个角色只获取最小必要上下文：

```python
# 开发者上下文：项目信息 + 需求摘要 + 设计摘要
dev_context = harness.memory.get_context_for_role("developer")

# 项目经理上下文：所有文档完整内容
pm_context = harness.memory.get_context_for_role("project_manager")
```

---

## 项目结构

```
py_ha/
├── src/py_ha/
│   ├── engine.py              # 主入口 Harness 类
│   ├── session.py             # 多会话管理
│   ├── guide.py               # 首次使用引导
│   │
│   ├── roles/                 # 角色系统
│   │   ├── developer.py      # 开发者
│   │   ├── tester.py         # 测试员
│   │   ├── product_manager.py # 产品经理
│   │   ├── architect.py      # 架构师
│   │   └── project_manager.py # 项目经理
│   │
│   ├── memory/                # JVM风格记忆管理（统一入口）
│   │   ├── manager.py        # 记忆管理器 + 文档系统
│   │   ├── heap.py           # 分代堆内存
│   │   ├── gc.py             # 垃圾回收
│   │   └── hotspot.py        # 热点检测
│   │
│   ├── storage/               # 轻量化存储
│   │   ├── json_store.py     # JSON存储
│   │   └── markdown.py       # Markdown存储
│   │
│   └── harness/               # 核心能力
│       ├── human_loop.py     # 人机交互
│       ├── agents_knowledge.py # AGENTS.md
│       ├── hooks.py          # 质量门禁
│       └── context_assembler.py # 上下文装配
│
└── tests/                     # 测试文件
```

---

## 更新日志

### v0.5.1 (当前版本)

**首次接入优化**

1. **首次接入流程** - 新增规范化提示词模板
   - 启用 py_ha 提示词：引导 AI 完成项目初始化
   - 激活项目经理提示词：让 AI 进入项目经理角色
   - 简化版提示词：快速激活

2. **首次接入指南** - 新增 `docs/ONBOARDING_GUIDE.md`
   - 完整的接入流程说明
   - 提示词模板详解
   - 对话示例和最佳实践
   - 故障排除指南

3. **skills/py_ha.md 增强** - 新增首次接入章节
   - 集成提示词模板
   - 快速激活指引

### v0.5.0

**新功能**

1. **`Harness.from_project()`** - 从现有项目目录初始化
   - 自动扫描项目文档（README.md、requirements.md 等）
   - 自动提取项目名称、描述、技术栈
   - 一行代码完成项目导入

2. **`get_init_prompt()`** - 获取完整的初始化提示
   - 包含 API 使用指南
   - 包含项目信息和文档内容
   - 专为 Claude Code 对话设计

3. **任务持久化** - 新增 `current_task.json`
   - 当前任务自动保存
   - 重启后自动恢复

4. **知识持久化** - 新增 `knowledge.json`
   - Permanent 区知识自动保存
   - 重启后自动恢复

**架构重构**

- 删除冗余模块：`kernel/`、`mcp/`、`tools/`、`project/`
- 合并 `project/` 到 `memory/` - `MemoryManager` 成为统一入口
- 激活 JVM 功能：GC 和 Hotspot 正常工作
- 代码精简约 3000 行

**API 变更**

```python
# 旧版本
from py_ha import ProjectStateManager
state = ProjectStateManager(".py_ha")

# 新版本（统一入口）
from py_ha import Harness
harness = Harness("项目名")
harness.memory  # MemoryManager 统一管理
```

### v0.4.0

- 新增 Harness 6 大核心能力
- 移除 Sandbox 模块

### v0.3.0

- 项目管理与渐进式披露
- JVM 风格分代存储

### v0.2.0

- 角色驱动协作：6 种团队角色
- 工作流驱动开发
- 轻量化存储

---

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

---

<div align="center">

**如果这个项目对你有帮助，请给一个 Star！**

</div>