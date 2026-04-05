# HarnessGenJ 部署指南

HarnessGenJ 提供三种部署方式，适用于不同场景：

| 方式 | 适用场景 | 特点 |
|------|----------|------|
| **pip** | Python 项目集成 | 灵活，可编程控制 |
| **MCP** | Claude Code / OpenClaude 集成 | 无缝集成，工具化使用 |
| **Skill** | Claude Code 快速使用 | 简单配置，快速上手 |

---

## 方式一：pip 安装

### 安装

```bash
# 从 PyPI 安装（发布后）
pip install harnessgenj

# 从源码安装
git clone https://github.com/harnessgenj/harnessgenj.git
cd harnessgenj
pip install -e .

# 开发模式（包含测试工具）
pip install -e ".[dev]"
```

### CLI 使用

安装后可以直接使用命令行：

```bash
# 查看帮助
harnessgenj --help

# 查看版本
harnessgenj version

# 开发功能
harnessgenj develop "实现用户登录功能"

# 修复Bug
harnessgenj fix "登录页面报错"

# 查看团队
harnessgenj team

# 查看状态
harnessgenj status

# 交互模式
harnessgenj interactive
```

### Python 代码使用

```python
from harnessgenj import Harness

# 创建实例
harness = Harness("我的项目")

# 一键开发
result = harness.develop("实现用户登录功能")
print(f"状态: {result['status']}")

# 一键修复
result = harness.fix_bug("登录页面报错")

# 项目报告
print(harness.get_report())
```

### requirements.txt

```
harnessgenj>=0.2.0
```

---

## 方式二：MCP Server

MCP (Model Context Protocol) 用于与 Claude Code、OpenClaude 等平台集成。

### 配置 Claude Code

编辑配置文件：
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS/Linux**: `~/.claude/claude_desktop_config.json`

#### 方式 A：从 PyPI 安装后使用

```json
{
  "mcpServers": {
    "HarnessGenJ": {
      "command": "harnessgenj-mcp",
      "args": []
    }
  }
}
```

#### 方式 B：直接运行模块

```json
{
  "mcpServers": {
    "HarnessGenJ": {
      "command": "python",
      "args": ["-m", "HarnessGenJ.mcp.server"],
      "env": {}
    }
  }
}
```

#### 方式 C：从源码运行

```json
{
  "mcpServers": {
    "HarnessGenJ": {
      "command": "python",
      "args": ["-m", "HarnessGenJ.mcp.server"],
      "cwd": "/path/to/harnessgenj/src",
      "env": {
        "PYTHONPATH": "/path/to/harnessgenj/src"
      }
    }
  }
}
```

### MCP Tools 列表

| 工具 | 说明 |
|------|------|
| `team_list` | 列出团队成员 |
| `team_add_role` | 添加角色 |
| `role_get_skills` | 获取角色技能 |
| `role_assign_task` | 分配任务 |
| `role_execute` | 执行任务 |
| `workflow_list` | 列出工作流 |
| `workflow_start` | 启动工作流 |
| `workflow_status` | 查询状态 |
| `workflow_run_all` | 运行完整流程 |
| `quick_feature` | 一键功能开发 |
| `quick_bugfix` | 一键Bug修复 |
| `system_status` | 系统状态 |

### 在 Claude Code 中使用

配置完成后重启 Claude Code，然后可以直接使用工具：

```
# 一键开发功能
请使用 quick_feature 工具开发"用户注册功能"

# 一键修复Bug
请使用 quick_bugfix 工具修复"支付页面无法提交"

# 查看团队
请使用 team_list 查看当前团队

# 查看系统状态
请使用 system_status 查看状态
```

---

## 方式三：Skill

Skill 方式适合快速将 HarnessGenJ 的能力引入 Claude Code。

### 安装 Skill

将 `skills/HarnessGenJ.md` 文件放到 Claude Code 的 skills 目录：

- **Windows**: `%USERPROFILE%\.claude\skills\HarnessGenJ.md`
- **macOS/Linux**: `~/.claude/skills/HarnessGenJ.md`

或者直接复制内容到对话中：

```
/HarnessGenJ
```

### 使用 Skill

在 Claude Code 对话中：

```
/HarnessGenJ

请帮我开发一个用户登录功能
```

Claude 会根据 skill 文档自动使用 HarnessGenJ 框架：

```python
from harnessgenj import Harness

harness = Harness("用户系统")
harness.develop("实现用户登录功能，支持用户名密码和手机验证码")
```

---

## 快速对比

| 功能 | pip | MCP | Skill |
|------|-----|-----|-------|
| Python 集成 | ✅ | ❌ | ❌ |
| CLI 命令 | ✅ | ❌ | ❌ |
| Claude Code 集成 | ❌ | ✅ | ✅ |
| 工具化使用 | ❌ | ✅ | ✅ |
| 配置复杂度 | 低 | 中 | 低 |
| 灵活性 | 高 | 中 | 低 |

## 推荐使用场景

### 适合 pip 方式
- Python 项目中直接使用
- 需要完全控制框架行为
- 自定义扩展和集成

### 适合 MCP 方式
- 使用 Claude Code 或 OpenClaude
- 需要通过工具调用框架
- 多个项目共享同一个框架实例

### 适合 Skill 方式
- 快速上手，不想复杂配置
- 偶尔使用框架能力
- 学习和探索框架功能

---

## 常见问题

### Q: pip 安装后找不到命令？

确保 Python Scripts 目录在 PATH 中：
```bash
# Linux/macOS
export PATH="$HOME/.local/bin:$PATH"

# Windows
# 将 %APPDATA%\Python\Scripts 添加到 PATH
```

### Q: MCP Server 连接失败？

1. 确保已安装 harnessgenj
2. 检查配置文件路径是否正确
3. 查看 Claude Code 日志

### Q: Skill 不生效？

1. 确认 skill 文件位置正确
2. 重启 Claude Code
3. 使用 `/HarnessGenJ` 显式加载

---

## 下一步

- 阅读 [README.md](README.md) 了解核心概念
- 运行 `python examples/quickstart.py` 查看示例
- 查看 [API 文档](docs/api.md) 了解详细接口