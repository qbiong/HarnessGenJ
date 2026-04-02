# py_ha - Python Harness for AI Agents

<div align="center">

**基于 Harness Engineering 理念的 AI Agent 协作框架**

通过**角色驱动**和**工作流驱动**实现高效的开发协作

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-133%20passed-green.svg)](tests/)

</div>

---

## 📖 目录

- [核心理念](#-核心理念)
- [安装方式](#-安装方式)
- [快速开始](#-快速开始)
- [核心功能](#-核心功能)
- [多会话记忆](#-多会话记忆)
- [API 参考](#-api-参考)
- [CLI 命令](#-cli-命令)
- [MCP 集成](#-mcp-集成)
- [项目结构](#-项目结构)
- [更新日志](#-更新日志)
- [常见问题](#-常见问题)
- [贡献指南](#-贡献指南)

---

## 🎯 核心理念

### 为什么选择 py_ha？

py_ha 将软件工程团队的最佳实践引入 AI Agent 开发，让 AI 像真实团队一样协作：

| 传统方式 | py_ha 方式 |
|----------|-----------|
| 抽象的 Agent 概念 | 真实团队角色（开发、测试、产品等） |
| 难以追踪的任务 | 完整的工作流和阶段 |
| 混乱的记忆管理 | JVM 风格的分代记忆系统 |
| 复杂的数据库配置 | 轻量化存储，开箱即用 |

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

### 工作流驱动开发

预定义的工作流确保开发过程规范有序：

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

---

## 📦 安装方式

py_ha 提供三种部署方式，满足不同使用场景：

### 方式一：pip 安装（推荐用于 Python 项目）

```bash
# 从 PyPI 安装
pip install py-ha

# 从源码安装
git clone https://github.com/py-ha/py-ha.git
cd py-ha
pip install -e .

# 开发模式（包含测试工具）
pip install -e ".[dev]"
```

### 方式二：MCP Server（推荐用于 Claude Code）

配置 Claude Code 的 `claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "py_ha": {
      "command": "py-ha-mcp",
      "args": []
    }
  }
}
```

### 方式三：Skill（快速上手）

将 `skills/py_ha.md` 文件放到 Claude Code 的 skills 目录：

- **Windows**: `%USERPROFILE%\.claude\skills\py_ha.md`
- **macOS/Linux**: `~/.claude/skills/py_ha.md`

然后在对话中使用 `/py_ha` 加载。

> 📖 详细部署说明请查看 [部署指南](docs/deployment.md)

---

## 🚀 快速开始

### 一行代码开发功能

```python
from py_ha import Harness

harness = Harness("我的项目")
result = harness.develop("实现用户登录功能")

print(f"状态: {result['status']}")      # completed
print(f"阶段: {result['stages_completed']}")  # 3
```

### 一行代码修复 Bug

```python
result = harness.fix_bug("登录页面验证码无法显示")
print(f"状态: {result['status']}")  # completed
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

# 开发功能
harness.develop("实现购物车功能")
```

### 获取项目报告

```python
harness.develop("功能1")
harness.develop("功能2")
harness.fix_bug("Bug1")

print(harness.get_report())
```

输出：
```
# 电商平台 项目报告

## 团队
- 规模: 3 人

## 统计
- 开发功能: 2 个
- 修复Bug: 1 个
- 完成工作流: 3 个

## 健康状态
- 记忆系统: healthy
```

---

## ⚡ 核心功能

### 1. 快速开发

一键完成需求分析 → 开发实现 → 测试验证：

```python
harness.develop("实现用户注册功能，支持邮箱和手机号注册")
```

### 2. 快速修复

一键完成 Bug分析 → 代码修复 → 验证测试：

```python
harness.fix_bug("支付页面偶尔超时")
```

### 3. 需求分析

产品经理角色分析需求：

```python
result = harness.analyze("用户需要一个仪表盘查看销售数据")
# 输出: 需求列表、用户故事、验收标准
```

### 4. 架构设计

架构师角色设计系统：

```python
result = harness.design("微服务架构的电商系统")
# 输出: 架构图、技术选型、设计决策
```

### 5. 代码审查

开发者角色审查代码：

```python
result = harness.review_code(code_string)
# 输出: 审查意见、改进建议
```

### 6. 记忆系统

JVM 风格的记忆管理，重要信息永不丢失：

```python
# 存储重要知识（进入 Permanent 区，永不回收）
harness.remember("project_goal", "构建电商平台", important=True)

# 存储普通信息
harness.remember("tech_stack", "Python + FastAPI")

# 回忆信息
goal = harness.recall("project_goal")
```

### 7. 工作流控制

精细控制工作流执行：

```python
# 启动工作流
harness.run_pipeline("feature", feature_request="用户登录")

# 运行标准流水线（完整流程）
harness.run_pipeline("standard", user_request="电商平台")

# 运行 Bug 修复流程
harness.run_pipeline("bugfix", bug_report="支付超时")
```

---

## 💬 多会话记忆

### 核心概念

多会话记忆允许你在项目开发过程中维护**多个独立的对话会话**，每个会话对应不同的角色，消息历史相互隔离：

```
┌─────────────────────────────────────────────────────────────┐
│                      多会话记忆架构                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ 主开发对话   │  │ 产品经理对话 │  │ 项目经理对话 │          │
│  │ development │  │ product_    │  │ project_    │          │
│  │             │  │ manager     │  │ manager     │          │
│  │ 消息历史 A   │  │ 消息历史 B   │  │ 消息历史 C   │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
│        ↑                ↑                ↑                  │
│        └────────────────┴────────────────┘                  │
│                    独立记忆空间                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 使用场景

在开发过程中，你可以：
- **主开发对话**: 保持核心开发流程不被打断
- **产品经理对话**: 随时讨论需求变更
- **项目经理对话**: 汇报进度、协调资源
- **架构师对话**: 咨询技术方案
- **测试人员对话**: 反馈测试问题

### 快速上手

```python
from py_ha import Harness

harness = Harness("电商平台项目")

# 1. 主开发流程
harness.chat("正在开发购物车功能")
harness.chat("已完成添加商品功能")

# 2. 需要确认需求，切换到产品经理对话
harness.switch_session("product_manager")
harness.chat("购物车需要支持哪些功能？")
harness.chat("好的，需求已记录")

# 3. 切回主开发，继续工作（之前的消息历史保留）
harness.switch_session("development")
harness.chat("需求已确认，继续开发购物车")

# 4. 遇到技术问题，咨询架构师
harness.switch_session("architect")
harness.chat("购物车数据应该用 Redis 还是数据库？")

# 5. 切回主开发应用建议
harness.switch_session("development")
harness.chat("架构师建议使用 Redis，按此实现")

# 6. 汇报进度给项目经理
harness.switch_session("project_manager")
harness.chat("购物车功能已开发完成")
```

### 会话类型

| 会话类型 | 说明 | 适用场景 |
|----------|------|----------|
| `development` | 主开发对话 | 核心开发流程、代码实现 |
| `product_manager` | 产品经理对话 | 需求讨论、功能确认 |
| `project_manager` | 项目经理对话 | 进度汇报、资源协调 |
| `architect` | 架构师对话 | 技术方案、架构评审 |
| `tester` | 测试人员对话 | 测试反馈、Bug 讨论 |
| `doc_writer` | 文档管理员对话 | 文档编写、知识库 |
| `general` | 通用对话 | 其他沟通 |

### 查看会话状态

```python
# 列出所有会话
sessions = harness.list_sessions()
for session in sessions:
    active = " (当前)" if session.get("is_active") else ""
    print(f"  {session['name']}{active}: {session['message_count']} 条消息")

# 获取当前会话历史
history = harness.get_session_history(limit=10)
for msg in history:
    print(f"  [{msg['role']}] {msg['content']}")

# 获取会话报告
print(harness.get_session_report())
```

输出：
```
# 电商平台项目 会话报告

## 所有会话

### 主开发对话 (当前)
- 类型: development
- 消息数: 5

### product_manager
- 类型: product_manager
- 消息数: 2
```

### 完整示例

查看 [examples/multi_session_demo.py](examples/multi_session_demo.py) 了解更多使用模式。

## 📚 API 参考

### Harness 类

主入口类，提供所有核心功能：

```python
from py_ha import Harness

harness = Harness(project_name="项目名称")
```

#### 团队管理

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `setup_team(config)` | 组建团队 | `dict` 团队信息 |
| `add_role(role_type, name)` | 添加角色 | `AgentRole` |
| `get_team()` | 获取团队列表 | `list[dict]` |

#### 快速开发

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `develop(feature_request)` | 一键开发功能 | `dict` 开发结果 |
| `fix_bug(bug_description)` | 一键修复 Bug | `dict` 修复结果 |

#### 分析设计

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `analyze(requirement)` | 需求分析 | `dict` 分析结果 |
| `design(system_description)` | 架构设计 | `dict` 设计结果 |
| `review_code(code)` | 代码审查 | `dict` 审查结果 |

#### 记忆系统

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `remember(key, content, important)` | 存储记忆 | `None` |
| `recall(key)` | 回忆信息 | `str \| None` |

#### 状态报告

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `get_status()` | 获取状态 | `dict` |
| `get_report()` | 获取报告 | `str` |
| `get_pipeline_status()` | 获取工作流状态 | `dict` |

#### 会话管理

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `chat(message, role)` | 在当前会话发送消息 | `dict` |
| `switch_session(session_type)` | 切换会话类型 | `dict` |
| `get_current_session()` | 获取当前会话信息 | `dict \| None` |
| `get_session_history(limit)` | 获取当前会话历史 | `list[dict]` |
| `list_sessions()` | 列出所有会话 | `list[dict]` |
| `get_session_report()` | 获取会话报告 | `str` |

**会话类型**: `development`, `product_manager`, `project_manager`, `architect`, `tester`, `doc_writer`, `general`

### 角色类

直接使用角色进行精细控制：

```python
from py_ha import Developer, Tester, ProductManager

# 创建开发人员
dev = Developer(role_id="dev_1", name="小李")

# 查看技能
skills = dev.list_skills()
# ['implement_feature', 'fix_bug', 'refactor_code', 'review_code', 'debug', 'write_unit_test']

# 分配任务
dev.assign_task({
    "type": "implement_feature",
    "description": "实现用户登录",
    "inputs": {"requirement": "..."},
})

# 执行任务
result = dev.execute_task()
```

### 工作流类

自定义工作流：

```python
from py_ha import WorkflowPipeline, WorkflowStage, StageStatus

# 创建自定义流水线
pipeline = WorkflowPipeline("custom_pipeline")

# 添加阶段
pipeline.add_stage(WorkflowStage(
    name="analysis",
    description="需求分析",
    role="product_manager",
    inputs=["user_request"],
    outputs=["requirements"],
))

pipeline.add_stage(WorkflowStage(
    name="implementation",
    description="功能实现",
    role="developer",
    inputs=["requirements"],
    outputs=["code"],
    dependencies=["analysis"],  # 依赖 analysis 阶段
))
```

---

## 💻 CLI 命令

安装后可直接使用命令行：

```bash
# 查看帮助
py-ha --help

# 查看版本
py-ha version
# 输出: py_ha version 0.2.0

# 开发功能
py-ha develop "实现用户登录功能"
# 输出: 状态: completed, 完成阶段: 3

# 修复 Bug
py-ha fix "登录页面验证码无法显示"
# 输出: 状态: completed, 完成阶段: 3

# 查看团队
py-ha team
# 输出: 团队规模: 6 人

# 查看状态
py-ha status
# 输出: 项目报告

# 交互模式
py-ha interactive
```

### 交互模式

```bash
$ py-ha interactive

py_ha> develop 实现用户注册功能
状态: completed

py_ha> fix 注册时邮箱验证失败
状态: completed

py_ha> team
  产品经理: product_manager
  开发人员: developer
  测试人员: tester

py_ha> status
# 项目报告...

py_ha> exit
再见!
```

---

## 🔌 MCP 集成

### 配置方式

编辑 Claude Code 配置文件：

- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS/Linux**: `~/.claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "py_ha": {
      "command": "py-ha-mcp",
      "args": []
    }
  }
}
```

### 可用工具

| 工具 | 说明 | 参数 |
|------|------|------|
| `quick_feature` | 一键功能开发 | `feature_request` |
| `quick_bugfix` | 一键 Bug 修复 | `bug_description` |
| `team_list` | 列出团队 | - |
| `team_add_role` | 添加角色 | `role_type`, `name` |
| `workflow_list` | 列出工作流 | - |
| `workflow_start` | 启动工作流 | `workflow_type`, `initial_request` |
| `workflow_status` | 查询状态 | `workflow_id` |
| `system_status` | 系统状态 | - |

#### 多会话工具

| 工具 | 说明 | 参数 |
|------|------|------|
| `session_switch` | 切换会话 | `session_type` |
| `session_chat` | 发送消息 | `message` |
| `session_list` | 列出所有会话 | - |
| `session_history` | 获取会话历史 | `limit` |
| `session_report` | 获取会话报告 | - |

**会话类型**: `development`, `product_manager`, `project_manager`, `architect`, `tester`, `doc_writer`, `general`

### 使用示例

在 Claude Code 对话中：

```
请使用 quick_feature 开发"用户登录功能"

请使用 quick_bugfix 修复"支付页面无法提交"

请使用 team_list 查看当前团队
```

---

## 📁 项目结构

```
py_ha/
├── src/py_ha/
│   ├── engine.py              # 主入口 Harness 类
│   ├── session.py             # 多会话管理模块
│   ├── cli.py                 # 命令行接口
│   │
│   ├── roles/                 # 角色系统
│   │   ├── base.py           # 角色基类、技能定义
│   │   ├── developer.py      # 开发人员角色
│   │   ├── tester.py         # 测试人员角色
│   │   ├── product_manager.py # 产品经理角色
│   │   ├── architect.py      # 架构师角色
│   │   ├── doc_writer.py     # 文档管理员角色
│   │   └── project_manager.py # 项目经理角色
│   │
│   ├── workflow/              # 工作流系统
│   │   ├── pipeline.py       # 流水线定义
│   │   ├── coordinator.py    # 协调器
│   │   └── context.py        # 上下文管理
│   │
│   ├── memory/                # JVM 风格记忆管理
│   │   ├── heap.py           # 分代堆内存
│   │   ├── gc.py             # 垃圾回收
│   │   ├── hotspot.py        # 热点检测
│   │   └── assembler.py      # 自动装配
│   │
│   ├── storage/               # 轻量化存储
│   │   ├── memory.py         # 内存存储
│   │   ├── json_store.py     # JSON 文件存储
│   │   ├── markdown.py       # Markdown 存储
│   │   └── manager.py        # 存储管理器
│   │
│   └── mcp/                   # MCP Server
│       └── server.py         # MCP 工具定义
│
├── tests/                     # 测试文件
├── examples/                  # 使用示例
│   ├── quickstart.py         # 快速入门
│   ├── harness_demo.py       # 完整示例
│   └── multi_session_demo.py # 多会话记忆示例
│
├── skills/                    # Claude Code Skill
│   └── py_ha.md              # Skill 定义
│
├── docs/                      # 文档
│   └── deployment.md         # 部署指南
│
├── pyproject.toml             # 项目配置
└── README.md                  # 本文档
```

---

## 📝 更新日志

### v0.2.1 (当前版本)

**新增功能: 多会话记忆**

- 新增 `SessionManager` 模块，支持维护多个独立的对话会话
- 支持 7 种会话类型：`development`, `product_manager`, `project_manager`, `architect`, `tester`, `doc_writer`, `general`
- 每个会话拥有独立的消息历史，互不干扰
- 可在不同会话间自由切换，保持各自上下文
- Harness 类新增会话管理方法：`chat()`, `switch_session()`, `get_session_history()`, `list_sessions()`, `get_session_report()`
- MCP Server 新增会话工具：`session_switch`, `session_chat`, `session_list`, `session_history`, `session_report`

**使用场景:**

在开发过程中，可以随时切换到产品经理对话讨论需求，然后切回主开发对话继续工作，所有对话历史独立保存。

### v0.2.0

**初始版本: Harness Engineering Framework**

- 角色驱动协作: 6 种团队角色（Developer, Tester, PM, Architect, DocWriter, ProjectManager）
- 工作流驱动: 标准流程、功能开发流程、Bug 修复流程
- JVM 风格记忆管理: 分代堆内存、垃圾回收、热点检测
- 轻量化存储: Memory/JSON/Markdown 三种存储方式
- MCP 集成: 提供 Claude Code 工具集成
- CLI 命令: 命令行交互模式

---

## ❓ 常见问题

### Q: pip 安装后找不到命令？

确保 Python Scripts 目录在 PATH 中：

```bash
# Linux/macOS
export PATH="$HOME/.local/bin:$PATH"

# Windows - 将以下路径添加到 PATH 环境变量
%APPDATA%\Python\Scripts
```

### Q: MCP Server 连接失败？

1. 确保已正确安装 py-ha
2. 检查配置文件路径是否正确
3. 尝试使用完整路径：

```json
{
  "mcpServers": {
    "py_ha": {
      "command": "python",
      "args": ["-m", "py_ha.mcp.server"]
    }
  }
}
```

### Q: 如何自定义角色行为？

继承角色基类并覆盖方法：

```python
from py_ha import Developer

class SeniorDeveloper(Developer):
    def _implement_feature(self):
        # 自定义实现逻辑
        return {"status": "completed", "outputs": {...}}
```

### Q: 如何创建自定义工作流？

```python
from py_ha import WorkflowPipeline, WorkflowStage

pipeline = WorkflowPipeline("custom")
pipeline.add_stage(WorkflowStage(
    name="custom_stage",
    description="自定义阶段",
    role="developer",
    inputs=["input"],
    outputs=["output"],
))
```

### Q: 记忆系统如何工作？

采用 JVM 风格的分代存储：

- **Eden 区**: 新存储的内容
- **Survivor 区**: 存活一段时间的内容
- **Old 区**: 长期存活的内容
- **Permanent 区**: 重要内容，永不回收

```python
# 重要内容进入 Permanent 区
harness.remember("key", "value", important=True)

# 自动触发 GC 当内存压力大时
harness.memory.auto_gc()
```

---

## 🤝 贡献指南

欢迎贡献代码、报告问题或提出建议！

### 开发环境设置

```bash
# 克隆仓库
git clone https://github.com/py-ha/py-ha.git
cd py-ha

# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
python -m pytest tests/ -v

# 代码格式化
ruff format src/

# 类型检查
mypy src/
```

### 提交代码

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

---

## 📮 联系方式

- **Issues**: [GitHub Issues](https://github.com/py-ha/py-ha/issues)
- **Discussions**: [GitHub Discussions](https://github.com/py-ha/py-ha/discussions)

---

<div align="center">

**如果这个项目对你有帮助，请给一个 ⭐️ Star！**

</div>