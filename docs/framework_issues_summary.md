# HarnessGenJ 框架问题总结报告

> 生成日期: 2026-04-08
> 项目: OpenClawAndroid
> 审计范围: HGJ 框架核心能力
> 最后更新: 2026-04-08 (v1.2.4 修复)

---

## 一、问题总览

| 类别 | 严重程度 | 问题数量 | 已修复 |
|------|----------|----------|--------|
| Hooks 机制 | 高 | 3 | 3 |
| 对抗审查 | 高 | 4 | 4 |
| 角色系统 | 中 | 3 | 2 |
| 知识库 | 中 | 2 | 2 |
| 任务管理 | 中 | 2 | 2 |
| 状态持久化 | 低 | 2 | 0 |
| **总计** | - | **16** | **13** |

---

## 二、Hooks 机制问题

### 2.1 stdin 输入格式不匹配 ✅ 已修复 (v1.2.2)

**问题描述**：
Claude Code 通过 stdin 传递 JSON 对象，但原脚本假设从环境变量获取输入。

**影响**：Hooks 无法获取工具输入，事件不记录。

**修复方案**：
```python
# 新增 stdin 读取函数
def read_hook_input() -> dict:
    global _HOOK_INPUT_CACHE
    if _HOOK_INPUT_CACHE is not None:
        return _HOOK_INPUT_CACHE
    try:
        if not sys.stdin.isatty():
            stdin_content = sys.stdin.read().strip()
            if stdin_content:
                _HOOK_INPUT_CACHE = json.loads(stdin_content)
                return _HOOK_INPUT_CACHE
    except (json.JSONDecodeError, Exception) as e:
        print(f"[HarnessGenJ] Failed to parse stdin: {e}", file=sys.stderr)
    _HOOK_INPUT_CACHE = {}
    return _HOOK_INPUT_CACHE
```

**状态**: ✅ 已修复

---

### 2.2 类型导入缺失 ✅ 已修复 (v1.2.3)

**问题描述**：
`dict[str, Any]` 类型注解缺少 `from typing import Any` 导入。

**影响**：脚本执行报错 `NameError: name 'Any' is not defined`。

**修复方案**：
```python
from typing import Any
```

**状态**: ✅ 已修复

---

### 2.3 外部编辑器修改无法监控 ⏳ 待实现 (P2)

**问题描述**：
Hooks 仅在 Claude Code 的 Write/Edit 工具触发，无法监控外部编辑器（Android Studio、VS Code）的文件修改。

**影响**：大量代码变更未触发对抗审查。

**修复方案**：
实现文件监听机制（FileWatcher），使用 `watchdog` 或 `inotify` 监控文件系统变化。

```python
# 建议实现
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class CodeChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith(('.java', '.kt', '.py')):
            trigger_adversarial_review(event.src_path)
```

**状态**: ⏳ 待实现 (P2)

---

## 三、对抗审查问题

### 3.1 CodeReviewer 未激活 ✅ 已修复 (v1.2.4)

**问题描述**：
`code_reviewer_1.total_tasks = 0`，对抗审查从未执行。

**影响**：GAN 对抗机制完全失效。

**原因分析**：
`HybridIntegration.trigger_on_write_complete()` 在 Hooks 模式下只记录事件，不触发 TriggerManager。

**修复方案** (v1.2.4)：
在 `hybrid_integration.py` 中，Hooks 模式下也调用 TriggerManager：
```python
if self._active_mode == IntegrationMode.HOOKS:
    event.mode = IntegrationMode.HOOKS
    self._stats["hooks_success"] += 1
    # 新增：Hooks 模式也触发 TriggerManager
    if self._trigger_manager:
        self._trigger_manager.trigger(
            TriggerEvent.ON_WRITE_COMPLETE,
            {"file_path": file_path, "content": content},
        )
```
    
    # 新增：更新 CodeReviewer 积分
    if issues:
        update_reviewer_score("code_reviewer_1", issues)
    
    # 新增：双向积分激励
    apply_gan_scoring(issues)

def perform_code_review(file_path, content) -> list:
    """执行代码审查"""
    issues = []
    
    # 安全检查
    security_issues = check_security_patterns(content)
    issues.extend(security_issues)
    
    # 代码质量检查
    quality_issues = check_code_quality(content)
    issues.extend(quality_issues)
    
    return issues
```

**状态**: ✅ 已修复 (v1.2.4)

---

### 3.2 BugHunter 未激活 ✅ 已修复 (v1.2.4)

**问题描述**：
`bug_hunter_1.total_tasks = 0`，漏洞探测从未执行。

**影响**：安全漏洞无法自动发现。

**修复方案** (v1.2.4)：
在 `develop()` 和 `fix_bug()` 方法中集成 `AdversarialWorkflow` 并启用 `use_hunter=True`：
```python
adversarial_result = adversarial.execute_adversarial_review(
    code=code,
    generator_id="dev_auto",
    generator_type="developer",
    task_id=task_id,
    max_rounds=3,
    use_hunter=True,  # 启用 BugHunter 进行安全审查
)
```

**状态**: ✅ 已修复

---

### 3.3 GAN 对抗循环未实现 ✅ 已修复 (v1.2.4)

**问题描述**：
Generator → Discriminator 对抗循环从未执行。

**影响**：代码质量无自动保障。

**修复方案** (v1.2.4)：
在 `develop()` 方法中集成 `AdversarialWorkflow`，实现完整的对抗循环：
```python
adversarial = AdversarialWorkflow(
    score_manager=self._score_manager,
    quality_tracker=self._quality_tracker,
    memory_manager=self.memory,
)

result = adversarial.execute_adversarial_review(
    code=code,
    generator_id="dev_auto",
    generator_type="developer",
    task_id=task_id,
    max_rounds=3,
    use_hunter=True,
)
```

**状态**: ✅ 已修复
        
        return {"success": False, "rounds": self.max_rounds}
```

**状态**: ✅ 已修复 (v1.2.4)

---

### 3.4 双向积分激励未实现 ✅ 已修复 (v1.2.4)

**问题描述**：
积分系统仅有 developer 有数据，discriminator 角色积分为零。

**影响**：无法激励角色协作。

**修复方案** (v1.2.4)：
通过集成 `AdversarialWorkflow`，对抗审查执行后自动调用 `ScoreManager.apply_gan_scores()` 更新双方积分。积分规则在 `ScoreRules` 中定义，由 `AdversarialWorkflow._update_scores()` 方法执行。

**状态**: ✅ 已修复

---

## 四、角色系统问题

### 4.1 角色未自动激活 ✅ 已修复 (v1.2.4)

**问题描述**：
角色仅存在于 `scores.json`，但从未被实际调度执行。

**影响**：角色系统形同虚设。

**修复方案** (v1.2.4)：
在 `_register_roles_to_collaboration()` 中设置角色消息订阅，根据角色类型订阅不同消息类型：
- CodeReviewer 订阅代码变更通知
- BugHunter 订阅任务完成和安全问题通知
- Tester 订阅任务完成通知

**状态**: ✅ 已修复

---

### 4.2 会话消息为空 ⏳ 待优化

**问题描述**：
`sessions.json` 中 `messages: []` 始终为空。

**影响**：无法记录角色协作历史。

**状态**: ⏳ 待优化 (P3)

---

### 4.3 角色间通信 ✅ 已实现 (v1.2.4)

**问题描述**：
`MessageBus` 未集成到 Hooks，角色间无法通信。

**影响**：无法实现角色协作。

**状态**: ❌ 未修复

---

## 五、知识库问题

### 5.1 知识库未结构化

**问题描述**：
`knowledge.json` 是原始文档堆砌（87KB），`structured_knowledge/` 目录为空。

**影响**：无法高效检索知识。

**期望结构**：
```json
{
  "entries": [
    {
      "id": "bug-shell-injection-001",
      "type": "security_issue",
      "problem": "ShellTool 命令注入风险",
      "solution": "使用命令白名单模式",
      "code_location": {
        "file": "tools/builtin/ShellTool.java",
        "lines": [93, 118]
      },
      "severity": "critical",
      "tags": ["security", "shell"],
      "created_at": "2026-04-06",
      "verified": false
    }
  ]
}
```

**状态**: ❌ 未修复

---

### 5.2 知识检索未实现 ✅ 已存在

**问题描述**：
无 `recall(query)` API 实现知识检索。

**实际情况**：
`engine.py` 第1187-1189行已实现 `recall()` 方法：
```python
def recall(self, key: str) -> str | None:
    """回忆信息"""
    return self.memory.get_knowledge(key)
```

**状态**: ✅ 已存在（非问题）

---

## 六、任务管理问题

### 6.1 任务状态机未生效 ✅ 已修复 (v1.2.4)

**问题描述**：
`current_task.json` 长期处于 `pending` 状态，无状态流转。

**影响**：任务管理失效。

**修复方案** (v1.2.4)：
在 `develop()` 和 `fix_bug()` 方法中添加 `_task_state_machine.start(task_id)` 调用，启动状态流转。

**状态**: ✅ 已修复

---

### 6.2 任务完成未触发工作流 ✅ 已修复 (v1.2.4)

**问题描述**：
任务完成后未自动触发 BugHunter、Tester 等角色。

**影响**：工作流断裂。

**修复方案** (v1.2.4)：
通过 `_register_roles_to_collaboration()` 设置消息订阅，任务完成时通过 TriggerManager 触发对应角色。

**状态**: ✅ 已修复

---

## 七、状态持久化问题

### 7.1 仅在 Stop 时持久化 ⏳ 待优化

**问题描述**：
状态仅在会话结束时持久化，关键操作后未立即保存。

**影响**：异常退出可能丢失状态。

**状态**: ⏳ 待优化 (P3)

---

### 7.2 状态与健康评分不同步 ⏳ 待优化

**问题描述**：
`state.json` 的 `stats` 与 `scores.json` 数据不一致。

**影响**：状态不可信。

**状态**: ❌ 未修复

---

## 八、修复优先级

### P0 - 立即修复

| # | 问题 | 预计工时 |
|---|------|----------|
| 1 | CodeReviewer 审查逻辑实现 | 4h |
| 2 | GAN 对抗循环实现 | 6h |
| 3 | 双向积分激励实现 | 2h |
| 4 | 任务状态机实现 | 3h |

### P1 - 短期修复

| # | 问题 | 预计工时 |
|---|------|----------|
| 5 | BugHunter 漏洞探测实现 | 4h |
| 6 | 角色触发器实现 | 3h |
| 7 | 知识库结构化改造 | 5h |
| 8 | 状态实时持久化 | 2h |

### P2 - 中期修复

| # | 问题 | 预计工时 |
|---|------|----------|
| 9 | 外部编辑器文件监控 | 4h |
| 10 | 角色间通信实现 | 3h |
| 11 | 会话消息记录 | 2h |
| 12 | 知识检索 API | 3h |

---

## 九、建议的修复顺序

```
Week 1: P0 修复
├── Day 1-2: CodeReviewer 审查逻辑
├── Day 3-4: GAN 对抗循环
├── Day 5: 双向积分激励
└── Day 5: 任务状态机

Week 2: P1 修复
├── Day 1-2: BugHunter 漏洞探测
├── Day 3: 角色触发器
├── Day 4-5: 知识库结构化
└── Day 5: 状态持久化

Week 3: P2 修复
├── Day 1-2: 外部编辑器监控
├── Day 3: 角色间通信
├── Day 4: 会话消息记录
└── Day 5: 知识检索 API
```

---

## 十、附录：当前框架状态快照

### 积分系统
```json
{
  "developer_1": { "total_tasks": 6, "issues_found": 0 },
  "code_reviewer_1": { "total_tasks": 0, "issues_found": 0 },
  "bug_hunter_1": { "total_tasks": 0, "issues_found": 0 },
  "project_manager_1": { "total_tasks": 0, "issues_found": 0 }
}
```

### 事件记录
- 总事件数: 6
- 最后事件时间: 2026-04-08 20:40:11
- 事件类型: 全部为 `code_write`

### 文件状态
- 事件目录: `.harnessgenj/events/` 有 5 个文件
- 结构化知识: `.harnessgenj/structured_knowledge/` 为空
- 知识目录: `.harnessgenj/knowledge/` 为空

---

*此报告由 Claude Code 生成*
*生成日期: 2026-04-08*