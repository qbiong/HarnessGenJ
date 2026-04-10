# HarnessGenJ 项目开发规范

> 此文件为 Claude Code 项目级指令，确保 AI 在开发过程中主动使用框架功能

---

## 🎯 一句话启动框架

**当用户消息包含以下任一触发词时，必须立即执行框架初始化：**

| 触发词 | 立即执行 |
|--------|----------|
| "使用HGJ框架" | ✅ 初始化框架并进入框架模式 |
| "HGJ框架辅助开发" | ✅ 初始化框架并进入框架模式 |
| "作为HGJ框架的项目经理" | ✅ 初始化框架并进入PM角色 |
| "HGJ项目经理" | ✅ 初始化框架并进入PM角色 |
| "进入HGJ框架" | ✅ 初始化框架并进入框架模式 |
| "用HGJ" | ✅ 初始化框架并进入框架模式 |

### 🚀 触发后立即执行（不可跳过）

```python
from harnessgenj import Harness

# 1. 初始化框架（必须执行）
harness = Harness.from_project(".")

# 2. 显示框架状态
status = harness.get_status()

# 3. 输出引导信息（告诉用户下一步该怎么做）
print(f"""
✅ HGJ框架已就绪
   项目: {status['project']}
   团队: {status['team']['size']} 个角色
   状态: 准备就绪

📋 您可以直接说：
   - "实现用户登录功能"
   - "修复首页加载问题"
   - "查看项目进度"

💡 框架会自动：
   - 签发操作许可
   - 生成操作指令
   - 执行质量检查
   - 更新积分排名
""")
```

---

## ⚠️ 强制触发条件（必须遵守）

**当用户消息包含以下开发关键词时，必须使用框架工具：**

| 关键词模式 | 必须使用 |
|------------|----------|
| 实现、开发、添加、创建、编写功能 | `harness.develop("描述")` |
| 修复、解决、调试、bug | `harness.fix_bug("描述")` |
| 审查、检查代码 | `harness.quick_review(code)` |
| 状态、进度、任务 | `harness.get_status()` |

**❌ 禁止行为：跳过框架直接编码**

**✅ 正确流程：框架签发许可 → 执行指令 → 完成任务**

---

## 🔄 标准开发流程

### 用户说："实现用户登录功能"

**AI 必须执行：**

```python
# 1. 通过框架开发
result = harness.develop("实现用户登录功能")

# 2. 查看操作指令
print(f"任务ID: {result['task_id']}")
print(f"许可文件: {result['permitted_files']}")
print(result['instruction_prompt'])

# 3. 在许可范围内执行代码修改
# ... 编写代码 ...

# 4. 完成任务
harness.complete_task(result['task_id'], "功能已完成")
```

---

## 📋 MCP 工具速查（21个）

| 类别 | 常用工具 |
|------|----------|
| 开发 | `task_develop`, `task_fix_bug` |
| 系统 | `system_status`, `system_scoreboard` |
| 内存 | `memory_store`, `memory_retrieve` |

---

## ⚡ 快速参考

### 框架初始化
```python
from harnessgenj import Harness
harness = Harness.from_project(".")
```

### 开发功能
```python
result = harness.develop("功能描述")
# 执行指令中的操作...
harness.complete_task(result['task_id'], "摘要")
```

### 修复Bug
```python
result = harness.fix_bug("问题描述")
# 执行指令中的操作...
harness.complete_task(result['task_id'], "摘要")
```

### 查看状态
```python
harness.get_status()
harness.get_score_leaderboard()
```

---

## 🎭 角色说明

| 角色 | 职责 | 禁止 |
|------|------|------|
| Developer | 编写代码 | 修改架构设计 |
| CodeReviewer | 审查代码 | 修改代码 |
| ProjectManager | 协调任务 | 修改代码 |
| BugHunter | 安全审查 | 修改代码 |

---

## 💰 积分系统

```
🏆 90+ 分 - 团队核心成员
⭐ 70-89 分 - 稳定贡献者
📌 50-69 分 - 需要提升
⚠️ <50 分 - 警告
```

**使用框架开发 = 获得积分奖励 = 提升职业信誉**

---

## 🔧 Hooks 权限检查

框架已集成 Hooks 权限检查：
- PreToolUse: 检查是否有操作许可
- 无许可时：提示用户先调用 `develop()` 或 `fix_bug()`

---

**记住：用户只需说"使用HGJ框架"，AI 就应该自动初始化并引导后续操作。**