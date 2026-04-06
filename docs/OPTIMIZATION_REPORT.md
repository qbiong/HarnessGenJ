# HarnessGenJ 框架优化分析报告

> 生成时间: 2026-04-05
> 项目: OpenClawAndroid
> 分析范围: 框架核心代码 + 项目实际使用文件

---

## 一、框架层面问题

### 1.1 Hooks 与 Claude Code 集成不足

**严重程度**: ⚠️ 高

**现状问题**:
- `HooksManager` 是纯 Python 内部系统，无法直接与 Claude Code 交互
- 当前桥梁脚本 `harnessgenj_hook.py` 只是简单转发，功能有限
- `PreToolUse` 的 `$TOOL_INPUT_CONTENT` 变量在 Claude Code 中可能不完整（大文件分块写入时不触发完整检查）
- `SecurityHook` 的敏感信息模式主要针对 Python，不适用于 Java/Kotlin 项目

**代码位置**: `HarnessGenJ/src/HarnessGenJ/harness/hooks.py`

```python
# 当前 SecurityHook 的模式定义
HIGH_RISK_PATTERNS = [
    "password",
    "secret",
    "api_key",
    "token",
    "credential",
]

SENSITIVE_PATTERNS = [
    r'password\s*=\s*"[^"]+"',
    r'api_key\s*=\s*"[^"]+"',
    # ... 仅适用于 Python 语法
]
```

**优化建议**:
```python
# 扩展多语言支持
LANGUAGE_PATTERNS = {
    "python": {
        "sensitive": [r'password\s*=\s*["\'][^"\']+["\']'],
        "high_risk": ["password", "api_key", "secret"],
    },
    "java": {
        "sensitive": [
            r'String\s+(password|apiKey|secret)\s*=\s*"[^"]+"',
            r'private\s+String\s+\w*[Pp]assword\w*\s*;',
        ],
        "high_risk": ["password", "apiKey", "secret", "token"],
    },
    "kotlin": {
        "sensitive": [
            r'val\s+(password|apiKey|secret)\s*=\s*"[^"]+"',
            r'private\s+val\s+\w*[Pp]assword\w*\s*=',
        ],
        "high_risk": ["password", "apiKey", "secret", "token"],
    },
}
```

---

### 1.2 上下文注入时机问题

**严重程度**: ⚠️ 高

**现状问题**:
- `get_context_prompt()` 需要手动调用，AI 容易忘记
- 没有自动注入机制（框架本身无法控制 Claude Code 的 system prompt）
- 多轮对话后 AI 可能忘记使用 HarnessGenJ 的方法

**代码位置**: `HarnessGenJ/src/HarnessGenJ/harness/context_assembler.py`

**优化建议**:

| 方案 | 实现复杂度 | 效果 |
|------|-----------|------|
| A: 创建 MCP Server | 高 | Claude Code 自动加载上下文 |
| B: PreToolUse 阶段注入 | 中 | 每次写入前自动提醒 |
| C: 写入 CLAUDE.md | 低 | 静态注入，无动态更新 |

**推荐方案 B 实现**:
```python
# harnessgenj_hook.py 增强版
def inject_context_reminder():
    """在关键操作前注入上下文提醒"""
    return """
[HarnessGenJ 提醒] 核心方法:
- receive_request("需求") - 接收用户请求
- develop("功能") - 开发功能
- record("内容") - 记录开发日志
- get_status() - 查看项目状态
"""
```

---

### 1.3 HumanLoop 实现不完整

**严重程度**: ⚠️ 中

**现状问题**:
- 审批功能为空实现，自动批准所有请求
- 无法真正实现人机交互审批

**代码位置**: `HarnessGenJ/src/HarnessGenJ/harness/human_loop.py:89`

```python
# 当前实现
async def request_approval(self, action: str, ...) -> ApprovalRequest:
    # TODO: 实现实际的审批等待逻辑
    # 当前为简化实现，自动批准
    request.status = ApprovalStatus.APPROVED  # 直接批准！
    return request
```

**优化建议**:
- 与 Claude Code 的 `AskUserQuestion` 工具集成
- 或创建独立审批 UI（Web Dashboard）
- 实现真正的异步等待机制

---

### 1.4 文档智能分类精度不足

**严重程度**: ⚠️ 中

**现状问题**:
- 依赖简单关键词匹配（"完成"、"bug"、"需求"）
- 可能误分类：如 "需求完成测试" 可能被分类到 progress 而非 requirements

**代码位置**: `HarnessGenJ/src/HarnessGenJ/engine.py:890-913`

```python
# 当前分类逻辑
requirement_keywords = ["需求", "功能", "需要", "要", "添加", "新增", "设计"]
bug_keywords = ["bug", "问题", "错误", "异常", "失败", "修复", "fix", "报错", "崩溃"]
progress_keywords = ["完成", "已", "进度", "状态", "更新", "通过", "成功"]

# 问题：无优先级处理，简单匹配
if any(kw in content_lower for kw in progress_keywords):
    doc_type = DocumentType.PROGRESS
```

**优化建议**:
- 引入上下文权重分析
- 支持显式指定文档类型 + 自动分类双重模式
- 添加分类置信度评分

---

### 1.5 AGENTS.md 知识同步问题

**严重程度**: ⚠️ 中

**现状问题**:
- 知识分散在 `.HarnessGenJ/knowledge/` 多个文件
- `tech_stack.md` 等需要手动更新
- 项目代码变更后知识不自动同步
- 多处知识文件内容不一致

**实际文件状态**:
```
knowledge/general/tech_stack.md  ← 已更新 (760B)
agents/tech.md                   ← 空模板！ (149B)
summaries/tech.summary.md        ← 空内容！ (80B)
```

**优化建议**:
- 添加 `sync_knowledge()` 方法，自动从 `build.gradle`、`package.json` 等提取技术栈
- 实现 AGENTS.md 作为唯一源，其他文件为派生
- 定期自动更新机制

---

### 1.6 多语言 Token 估算局限

**严重程度**: ⚠️ 低

**现状问题**:
- 使用简单的字符计数估算 Token
- 精度不足，可能影响上下文裁剪决策

**代码位置**: `HarnessGenJ/src/HarnessGenJ/harness/context_assembler.py:571`

```python
# 当前实现
def _estimate_tokens(self, content: str) -> int:
    # 简化估算：中文约 1 token = 2 chars，英文约 1 token = 4 chars
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
    other_chars = len(content) - chinese_chars
    return chinese_chars // 2 + other_chars // 4
```

**优化建议**:
- 使用 tiktoken 等标准库精确估算
- 支持更多语言（日文、韩文等）

---

### 1.7 配置体验问题

**严重程度**: ⚠️ 中

**现状问题**:
- 每个项目需要单独配置 `harnessgenj_hook.py`
- settings.json hooks 配置复杂
- 无自动化初始化流程

**优化建议**:
- 提供 `harnessgenj init` CLI 命令自动生成配置
- 支持全局 hooks 模板 + 项目级覆盖
- 交互式配置向导

---

### 1.8 Hooks 检查结果处理

**严重程度**: ⚠️ 中

**现状问题**:
- hooks 失败返回非零状态码，但 Claude Code 可能不显示详细错误
- 编码问题（Windows GBK）导致输出乱码

**优化建议**:
- 输出使用纯 ASCII 或 UTF-8 强制编码
- 错误信息写入日志文件而非 stdout
- 提供结构化 JSON 输出格式

---

## 二、文件系统问题

### 2.1 文件冗余与版本管理问题

**严重程度**: ⚠️ 严重

**问题详情**:

| 问题类型 | 具体表现 | 数据证据 |
|----------|----------|----------|
| 版本文件高度重复 | `progress.v1.md` ≈ `progress.v2.md` | 1726B vs 1856B，差异仅 130B |
| documents 与 history 重复 | 同一内容存两份 | `documents/progress.md` ≈ `history/progress.v3.md` |
| 无清理机制 | 版本文件持续累积 | 已有 v1/v2/v3 三个版本 |
| 版本命名不规范 | 无时间戳语义 | `.v1.md`, `.v2.md` 难以追溯 |

**当前文件状态**:
```
.HarnessGenJ/history/
├── progress.v1.md  (1726 bytes) - 状态：部分任务待处理
├── progress.v2.md  (1856 bytes) - 状态：同上，多一行记录
├── progress.v3.md  (990 bytes)  - 状态：部分完成
├── requirements.v1.md (945 bytes)
└── requirements.v2.md (727 bytes)

.HarnessGenJ/documents/
├── progress.md     (2002 bytes) - 当前版本
├── requirements.md (1112 bytes)
└── development.md  (360 bytes)
```

**优化建议**:
- 实现 Git-like 版本策略：只保留最近 3 版本
- 版本命名包含时间戳：`progress.20260405-1255.md`
- 自动清理超过 N 天的旧版本

---

### 2.2 知识分散与同步缺失

**严重程度**: ⚠️ 严重

**知识存储位置分布**:
```
.HarnessGenJ/
├── AGENTS.md              ← 主知识文件 (1794B)
├── knowledge/
│   ├── index.md           ← 知识索引
│   └── general/
│       ├── tech_stack.md  ← 已更新 (760B)
│       ├── description.md ← 项目描述 (257B)
│       └── project_name.md
├── agents/
│   ├── tech.md            ← 空模板！未同步 (149B)
│   ├── conventions.md     ← 空模板 (173B)
│   └── workflow.md        ← 空模板 (194B)
└── summaries/
    ├── tech.summary.md    ← 空内容！未同步 (80B)
    ├── conventions.summary.md (114B)
    └── workflow.summary.md    (141B)
```

**问题分析**:
- `knowledge/general/tech_stack.md` 已更新，但 `agents/tech.md` 和 `summaries/tech.summary.md` 仍为默认 Python 模板
- 无自动同步机制，一处更新后其他位置不会联动
- 知识索引 `index.md` 仅记录 general 目录，不包含 agents/summaries

**优化建议**:
```python
def sync_all_knowledge(self):
    """一处更新，全局同步"""
    # 1. 从 AGENTS.md 提取核心知识
    # 2. 更新 knowledge/general/ 各文件
    # 3. 生成 agents/ 角色专用知识
    # 4. 压缩生成 summaries/ 摘要
    # 5. 更新 index.md 索引
```

---

### 2.3 Hooks 功能未生效

**严重程度**: ⚠️ 高

**问题详情**:

**development.md 记录内容**:
```markdown
## 记录 (2026-04-05 12:54)
文件 modified:

## 记录 (2026-04-05 12:55)
文件 modified:
```

**问题分析**:

| 问题 | 原因 | 影响 |
|------|------|------|
| 记录内容为空 | `$TOOL_INPUT_PATH` 变量传递不完整 | 开发日志无实质内容 |
| PostToolUse 未生效 | Claude Code hooks 环境变量机制与脚本不匹配 | 自动记录失败 |
| 记录格式单一 | 只有时间戳和空路径 | 无法追溯开发历史 |

**优化建议**:
```python
# 修复环境变量问题
# Claude Code 可用变量:
# - $CLAUDE_PROJECT_DIR
# - $TOOL_NAME
# - $TOOL_INPUT (JSON 格式的完整输入)

# harnessgenj_hook.py 改进
def main():
    import os
    import json

    # 使用 TOOL_INPUT 获取完整信息
    tool_input = os.environ.get("TOOL_INPUT", "{}")
    data = json.loads(tool_input)

    file_path = data.get("file_path", "")
    content = data.get("content", "")

    # 记录完整信息
    if file_path:
        harness.record(f"修改文件: {file_path}")
```

---

### 2.4 会话管理未激活

**严重程度**: ⚠️ 中

**sessions.json 状态**:
```json
{
  "sessions": [{
    "id": "e16542ba",
    "name": "主开发对话",
    "session_type": "development",
    "messages": []  // 空！无对话记录
  }]
}
```

**问题分析**:
- `harness.chat()` 调用后 messages 应有记录，但实际为空
- 多会话功能（product_manager、architect 等）未使用
- 会话历史无法追溯

**优化建议**:
- 检查 `chat()` 方法的消息持久化逻辑
- 提供会话切换 CLI 命令
- 实现会话历史查询功能

---

### 2.5 文件调度性能问题

**严重程度**: ⚠️ 中

**每次操作的文件 I/O 分析**:

| 操作 | 涉及文件 | I/O 次数 | 潜在瓶颈 |
|------|----------|----------|----------|
| `chat()` | sessions.json + state.json + documents/*.md + project.json | 4-6 次 | 多文件串行写入 |
| `record()` | documents/*.md + project.json + state.json | 3-4 次 | 无批量优化 |
| `PostToolUse hook` | harnessgenj_hook.py + documents/development.md + state.json | 3-4 次 | 每次写入触发 |

**问题分析**:
- 无缓存机制，每次操作直接写磁盘
- 多文件串行写入，无批量优化
- 历史版本叠加写入（追加而非覆盖）

**优化建议**:
```python
class WriteBatch:
    """批量写入优化"""

    def __init__(self):
        self._pending = {}
        self._timer = None

    def queue(self, file_path: str, content: str):
        """加入写入队列"""
        self._pending[file_path] = content
        if not self._timer:
            self._timer = threading.Timer(1.0, self.flush)
            self._timer.start()

    def flush(self):
        """批量写入"""
        for path, content in self._pending.items():
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
        self._pending.clear()
        self._timer = None
```

---

### 2.6 项目状态一致性问题

**严重程度**: ⚠️ 中

**对比 documents 与 project.json**:

| 指标 | documents/progress.md | project.json | 差异 |
|------|----------------------|--------------|------|
| 已完成任务数 | 4 个 (视觉统计) | `features_completed: 2` | 不一致 |
| 总任务数 | 4 个 | `features_total: 4` | 一致 |
| 进度 | 100% (视觉) | `progress: 50` | 不一致 |

**project.json 实际内容**:
```json
{
  "info": {
    "name": "OpenClawAndroid",
    "status": "completed"
  },
  "stats": {
    "features_total": 4,
    "features_completed": 2,
    "progress": 50
  }
}
```

**progress.md 显示**:
```markdown
## TASK-1775146965 - 功能开发
- **状态**: 已完成  ✅

## TASK-1775195518 - 任务
- **状态**: 已完成  ✅

## TASK-1775195750 - 功能开发
- **状态**: 已完成  ✅

## TASK-1775195750 - 任务
- **状态**: 已完成  ✅
```

**问题分析**:
- 视觉统计 4 个任务完成，但 `project.json` 仅记录 2
- `complete_task()` 方法的统计更新逻辑可能有问题
- 状态同步缺失

**优化建议**:
```python
def complete_task(self, task_id: str, summary: str = "") -> bool:
    # 修复统计逻辑
    # 1. 确保 features_completed 正确递增
    # 2. 确保 progress 百分比正确计算
    # 3. 同步更新 project.json 和 progress.md
```

---

## 三、优先级排序

### P0 - 紧急修复（影响核心功能）

| 序号 | 问题 | 影响 | 工作量 |
|------|------|------|--------|
| 1 | PostToolUse hooks 失效 | 开发记录无法自动保存 | 低 |
| 2 | 知识同步缺失 | 知识文件不一致 | 中 |
| 3 | 统计不一致 | 项目状态错误 | 低 |
| 4 | SecurityHook 多语言支持 | Java/Kotlin 项目无安全检查 | 低 |

### P1 - 性能优化（影响使用体验）

| 序号 | 问题 | 影响 | 工作量 |
|------|------|------|--------|
| 5 | 版本文件冗余 | 存储浪费，查找慢 | 中 |
| 6 | 多文件 I/O 无优化 | 操作延迟 | 中 |
| 7 | 上下文自动注入 | AI 忘记使用框架方法 | 中 |
| 8 | HumanLoop 完善 | 审批流程无法使用 | 中 |

### P2 - 功能增强（提升易用性）

| 序号 | 问题 | 影响 | 工作量 |
|------|------|------|--------|
| 9 | 配置自动化 CLI | 初始化复杂 | 低 |
| 10 | 会话管理未激活 | 多会话功能不可用 | 低 |
| 11 | 文档智能分类 | 记录可能误分类 | 高 |
| 12 | Token 估算精度 | 上下文裁剪不准确 | 低 |

---

## 四、具体修复方案

### 4.1 修复 PostToolUse Hooks

**文件**: `.claude/harnessgenj_hook.py`

```python
#!/usr/bin/env python3
"""
harnessgenj_hook.py - Claude Code Hooks 桥梁脚本 (增强版)
"""

import os
import sys
import json
from pathlib import Path

# 添加 HarnessGenJ 到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "HarnessGenJ" / "src"))

def handle_post_tool_use():
    """处理 PostToolUse 事件"""
    # 获取完整输入
    tool_input = os.environ.get("TOOL_INPUT", "{}")
    tool_name = os.environ.get("TOOL_NAME", "")

    try:
        data = json.loads(tool_input)
    except json.JSONDecodeError:
        data = {}

    file_path = data.get("file_path", data.get("path", ""))
    content = data.get("content", data.get("new_string", ""))

    if not file_path:
        return

    # 调用 HarnessGenJ 记录
    try:
        from HarnessGenJ import Harness
        project_root = Path(__file__).parent.parent
        harness = Harness(str(project_root), persistent=True)

        # 记录详细信息
        action = "创建" if tool_name == "Write" else "修改"
        record_content = f"{action}文件: {file_path}"

        # 如果是代码文件，提取关键信息
        if file_path.endswith(('.java', '.kt', '.py')):
            lines = content.count('\n') + 1 if content else 0
            record_content += f" ({lines} 行)"

        harness.record(record_content, context="Hooks")

    except Exception as e:
        # 静默失败，不影响主流程
        pass

if __name__ == "__main__":
    handle_post_tool_use()
```

**settings.json 更新**:
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "python \"$CLAUDE_PROJECT_DIR/.claude/harnessgenj_hook.py\""
          }
        ]
      }
    ]
  }
}
```

---

### 4.2 实现知识同步

**文件**: `HarnessGenJ/src/HarnessGenJ/harness/agents_knowledge.py` (新增方法)

```python
def sync_all_knowledge(self) -> dict[str, Any]:
    """
    同步所有知识文件

    确保 AGENTS.md 为唯一源，其他文件自动派生
    """
    results = {
        "updated": [],
        "skipped": [],
        "errors": []
    }

    # 1. 从 AGENTS.md 提取知识
    agents_content = self.get_full_knowledge()

    # 2. 更新 knowledge/general/ 文件
    tech_stack = self._extract_section(agents_content, "技术栈")
    if tech_stack:
        self._update_knowledge_file("general/tech_stack.md", tech_stack)
        results["updated"].append("tech_stack.md")

    # 3. 生成 agents/ 角色专用知识
    for role in ["developer", "architect", "tester"]:
        role_knowledge = self._generate_role_knowledge(agents_content, role)
        self._update_knowledge_file(f"agents/{role}.md", role_knowledge)
        results["updated"].append(f"{role}.md")

    # 4. 生成 summaries/ 摘要
    for name, content in self._generate_summaries(agents_content).items():
        self._update_knowledge_file(f"summaries/{name}.summary.md", content)
        results["updated"].append(f"{name}.summary.md")

    # 5. 更新索引
    self._update_index()

    return results
```

---

### 4.3 修复统计一致性

**文件**: `HarnessGenJ/src/HarnessGenJ/engine.py` (修改 `complete_task` 方法)

```python
def complete_task(self, task_id: str, summary: str = "") -> bool:
    """项目经理标记任务完成"""
    if not self.project_state:
        return False

    timestamp = time.strftime('%Y-%m-%d %H:%M')

    # 更新进度文档
    progress = self.project_state.get_document(
        DocumentType.PROGRESS, "project_manager", full=True
    ) or ""

    if task_id in progress:
        import re
        # 更新状态
        progress = re.sub(
            rf'(\*\*状态\*\*:\s*)\S+',
            '**状态**: 已完成',
            progress
        )

        # 添加完成记录
        completion_note = f"\n  - **完成时间**: {timestamp}"
        if summary:
            completion_note += f"\n  - **完成说明**: {summary}"

        self.project_state.update_document(
            DocumentType.PROGRESS,
            progress + completion_note,
            "project_manager",
            f"完成任务: {task_id}"
        )

        # 修复：正确更新统计
        # 检查任务类型，只统计一次
        if "Bug修复" in progress or "Bug" in progress:
            self.project_state.stats.bugs_fixed += 1
        else:
            # 避免重复计数：检查是否已经计数
            current_task = self.project_state.get_current_task()
            if current_task.get("task_id") == task_id:
                self.project_state.stats.features_completed += 1

        # 重新计算进度百分比
        total = max(self.project_state.stats.features_total, 1)
        completed = self.project_state.stats.features_completed
        self.project_state.stats.progress = int(completed / total * 100)

        # 清除当前任务
        self.project_state.clear_current_task()

        self.project_state._save()
        self._save_state()

        return True

    return False
```

---

## 五、总结

### 问题统计

| 类别 | 严重 | 高 | 中 | 低 | 合计 |
|------|------|-----|-----|-----|------|
| 框架层面 | 2 | 2 | 3 | 1 | 8 |
| 文件系统 | 2 | 1 | 3 | 0 | 6 |
| **合计** | **4** | **3** | **6** | **1** | **14** |

### 关键改进方向

1. **自动化**: hooks 自动记录、知识自动同步、配置自动初始化
2. **一致性**: 统计数据同步、知识文件统一、版本管理规范
3. **性能**: 批量写入、缓存机制、文件精简
4. **多语言**: 安全检查支持 Java/Kotlin、Token 估算支持多语言

### 预期收益

- 减少 50% 手动操作（自动记录、自动同步）
- 提升 30% 文件调度性能（批量写入、缓存）
- 消除知识不一致问题（单一源派生）
- 支持 Java/Kotlin 项目安全检查

---

*报告结束*