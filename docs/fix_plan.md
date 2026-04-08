# HGJ框架问题总结与修复方案

> 生成时间: 2026-04-08
> 框架版本: v1.2.4
> 项目: OpenClawAndroid

---

## 一、问题总览

| 类别 | 严重程度 | 问题数量 | 状态 |
|------|----------|----------|------|
| Hooks机制 | 高 | 2 | 需修复 |
| 对抗审查 | 高 | 3 | 需修复 |
| 角色系统 | 中 | 3 | 需修复 |
| 积分系统 | 中 | 2 | 需修复 |
| 任务管理 | 中 | 2 | 需修复 |
| 知识库 | 低 | 2 | 需修复 |
| **总计** | - | **14** | - |

---

## 二、关键问题详解

### 问题1: Hooks未自动触发对抗审查 [严重]

**现状**:
- Hooks正确记录文件修改事件 (已记录7个事件)
- 但未调用 `quick_review()` 或 `adversarial_develop()`
- 导致代码审查需要手动触发

**原因分析**:
`harnessgenj_hook.py` 的 `trigger_adversarial_review()` 函数只做了：
1. ✅ 记录到开发日志
2. ✅ 写入事件文件
3. ✅ 更新 developer 积分
4. ❌ **未执行实际代码审查**
5. ❌ **未更新 CodeReviewer 积分**

**修复方案**:

```python
# 修改 .claude/harnessgenj_hook.py

def trigger_adversarial_review(file_path: str, content: str) -> dict:
    """触发对抗性审查"""
    result = {
        "file": file_path,
        "review_triggered": False,
        "issues": [],
    }

    # 检查是否是代码文件
    code_extensions = ['.py', '.java', '.kt', '.js', '.ts', '.tsx', '.go', '.rs']
    if not any(file_path.endswith(ext) for ext in code_extensions):
        return result

    # 【新增】执行实际代码审查
    try:
        from harnessgenj import Harness
        project_root = get_project_root()
        h = Harness.from_project(str(project_root))
        
        # 调用快速审查
        success, issues = h.quick_review(content)
        result["review_triggered"] = True
        result["issues"] = issues
        
        # 更新积分
        if issues:
            # 发现问题 - CodeReviewer 得分
            _update_score(project_root, "code_reviewer_1", +5 * len(issues))
            _update_score(project_root, "developer_1", -3 * len(issues))
        else:
            # 通过审查 - Developer 得分
            _update_score(project_root, "developer_1", +10)
            
    except Exception as e:
        print(f"[HarnessGenJ] Review failed: {e}", file=sys.stderr)

    return result

def _update_score(project_root: Path, role_id: str, delta: int):
    """更新角色积分"""
    scores_path = project_root / ".harnessgenj" / "scores.json"
    try:
        with open(scores_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if role_id in data.get("scores", {}):
            data["scores"][role_id]["score"] += delta
            data["scores"][role_id]["total_tasks"] += 1
            
        with open(scores_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
```

**预计工时**: 2小时

---

### 问题2: GAN对抗循环未实现 [严重]

**现状**:
- `code_reviewer_1.total_tasks = 0`
- `bug_hunter_1.total_tasks = 0`
- Generator → Discriminator 对抗循环从未执行

**期望流程**:
```
Developer (Generator) → 产出代码
    ↓
CodeReviewer (Discriminator) → 审查代码
    ↓ (发现问题)
Developer → 修复代码
    ↓ (再次审查)
CodeReviewer → 确认通过
```

**修复方案**:

```python
# 新增 .harnessgenj/adversarial_loop.py

from typing import List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class AdversarialRound:
    round_num: int
    issues_found: List[dict]
    developer_score_delta: int
    reviewer_score_delta: int
    passed: bool

class GANAdversarialLoop:
    """GAN式对抗循环"""
    
    def __init__(self, harness, max_rounds: int = 3):
        self.harness = harness
        self.max_rounds = max_rounds
        self.rounds = []
    
    def execute(self, code: str, file_path: str) -> Tuple[bool, List[AdversarialRound]]:
        """执行对抗循环"""
        current_code = code
        
        for round_num in range(1, self.max_rounds + 1):
            # Discriminator 审查
            success, issues = self.harness.quick_review(current_code)
            
            if success and not issues:
                # 一轮通过
                round_result = AdversarialRound(
                    round_num=round_num,
                    issues_found=[],
                    developer_score_delta=+10 if round_num == 1 else +5,
                    reviewer_score_delta=0,
                    passed=True
                )
                self.rounds.append(round_result)
                self._apply_scores(round_result)
                return True, self.rounds
            
            # 发现问题
            round_result = AdversarialRound(
                round_num=round_num,
                issues_found=issues,
                developer_score_delta=-5 if round_num == 1 else -3,
                reviewer_score_delta=+5 if round_num == 1 else +3,
                passed=False
            )
            self.rounds.append(round_result)
            self._apply_scores(round_result)
            
            # 通知 Developer 修复 (这里需要人工介入或AI修复)
            # current_code = self._request_fix(current_code, issues)
        
        return False, self.rounds
    
    def _apply_scores(self, round_result: AdversarialRound):
        """应用积分变化"""
        # 更新 Developer 积分
        self._update_role_score("developer_1", round_result.developer_score_delta)
        
        # 更新 Reviewer 积分
        if round_result.reviewer_score_delta > 0:
            self._update_role_score("code_reviewer_1", round_result.reviewer_score_delta)
    
    def _update_role_score(self, role_id: str, delta: int):
        """更新角色积分"""
        # 实现积分更新逻辑
        pass
```

**预计工时**: 4小时

---

### 问题3: 双向积分激励未实现 [严重]

**现状**:
- 积分系统仅有 developer 有数据
- Discriminator 角色积分为零
- 无法激励角色协作

**期望规则**:

| 行为 | Generator积分 | Discriminator积分 |
|------|---------------|-------------------|
| 一轮通过审查 | +10 | 0 |
| 二轮通过 | +5 | 0 |
| 发现关键问题 | -10 | +10 |
| 发现中等问题 | -5 | +5 |
| 误报问题 | +3 | -3 |

**修复方案**:

```python
# 在 harnessgenj_hook.py 或新建 scoring.py

class BidirectionalScoring:
    """双向积分激励系统"""
    
    SCORE_RULES = {
        "first_round_pass": {"developer": +10, "reviewer": 0},
        "second_round_pass": {"developer": +5, "reviewer": 0},
        "critical_issue_found": {"developer": -10, "reviewer": +10},
        "medium_issue_found": {"developer": -5, "reviewer": +5},
        "false_positive": {"developer": +3, "reviewer": -3},
    }
    
    @classmethod
    def apply_rule(cls, rule_name: str, scores_data: dict, 
                   developer_id: str = "developer_1",
                   reviewer_id: str = "code_reviewer_1"):
        """应用积分规则"""
        rule = cls.SCORE_RULES.get(rule_name)
        if not rule:
            return
        
        if developer_id in scores_data.get("scores", {}):
            scores_data["scores"][developer_id]["score"] += rule["developer"]
            scores_data["scores"][developer_id]["total_tasks"] += 1
        
        if reviewer_id in scores_data.get("scores", {}):
            scores_data["scores"][reviewer_id]["score"] += rule["reviewer"]
            if rule["reviewer"] != 0:
                scores_data["scores"][reviewer_id]["total_tasks"] += 1
        
        # 记录事件
        event = {
            "timestamp": datetime.now().isoformat(),
            "rule": rule_name,
            "developer_delta": rule["developer"],
            "reviewer_delta": rule["reviewer"]
        }
        if "scoring_events" not in scores_data:
            scores_data["scoring_events"] = []
        scores_data["scoring_events"].append(event)
```

**预计工时**: 2小时

---

### 问题4: 角色协作未激活 [中等]

**现状**:
- `team.members = []` (空)
- `messages_sent = 0`
- `active_roles = 0`
- MessageBus 未使用

**修复方案**:

```python
# 修改框架初始化，自动注册团队成员

def setup_team(harness):
    """设置团队"""
    from harnessgenj.roles import Developer, CodeReviewer, BugHunter, ProjectManager
    
    # 注册团队成员
    team = harness.get_team()
    
    team.register(Developer("developer_1", "开发者"))
    team.register(CodeReviewer("code_reviewer_1", "代码审查者"))
    team.register(BugHunter("bug_hunter_1", "漏洞猎手"))
    team.register(ProjectManager("project_manager_1", "项目经理"))
    
    # 设置消息总线
    from harnessgenj.messaging import MessageBus
    bus = MessageBus()
    
    # 订阅事件
    bus.subscribe("code_written", "code_reviewer_1")
    bus.subscribe("review_complete", "developer_1")
    bus.subscribe("bug_found", "bug_hunter_1")
    
    return team
```

**预计工时**: 3小时

---

### 问题5: 任务状态机未生效 [中等]

**现状**:
- `current_task.json` 长期处于 `pending` 状态
- 无状态流转

**期望状态流转**:
```
pending → in_progress → reviewing → completed/failed
```

**修复方案**:

```python
# 新建 .harnessgenj/task_state_machine.py

class TaskStateMachine:
    """任务状态机"""
    
    STATES = ["pending", "in_progress", "reviewing", "completed", "failed"]
    
    VALID_TRANSITIONS = [
        ("pending", "in_progress"),
        ("in_progress", "reviewing"),
        ("reviewing", "completed"),
        ("reviewing", "failed"),
        ("failed", "in_progress"),  # 重试
    ]
    
    def __init__(self, task_file: str):
        self.task_file = task_file
    
    def transition(self, new_state: str) -> bool:
        """状态转换"""
        task = self._load_task()
        current_state = task.get("status", "pending")
        
        if (current_state, new_state) in self.VALID_TRANSITIONS:
            task["status"] = new_state
            task["updated_at"] = datetime.now().isoformat()
            self._save_task(task)
            return True
        
        return False
    
    def start(self) -> bool:
        return self.transition("in_progress")
    
    def submit_for_review(self) -> bool:
        return self.transition("reviewing")
    
    def complete(self) -> bool:
        return self.transition("completed")
    
    def fail(self) -> bool:
        return self.transition("failed")
```

**预计工时**: 2小时

---

### 问题6: 知识库未结构化 [低]

**现状**:
- `knowledge.json` 是原始文档堆砌
- `structured_knowledge/` 目录为空
- 无 `recall(query)` API 实现

**修复方案**:

```python
# 新建 .harnessgenj/knowledge_manager.py

from dataclasses import dataclass
from typing import List, Optional
import json

@dataclass
class KnowledgeEntry:
    id: str
    type: str  # security_issue, pattern, best_practice
    problem: str
    solution: str
    code_location: Optional[dict]
    severity: str
    tags: List[str]
    verified: bool

class StructuredKnowledgeManager:
    """结构化知识管理"""
    
    def __init__(self, knowledge_dir: str):
        self.knowledge_dir = Path(knowledge_dir)
        self.entries: List[KnowledgeEntry] = []
        self._load()
    
    def add_entry(self, entry: KnowledgeEntry):
        """添加知识条目"""
        self.entries.append(entry)
        self._save()
    
    def recall(self, query: str, limit: int = 10) -> List[KnowledgeEntry]:
        """检索相关知识"""
        results = []
        query_lower = query.lower()
        
        for entry in self.entries:
            # 简单关键词匹配
            if (query_lower in entry.problem.lower() or
                query_lower in entry.solution.lower() or
                any(query_lower in tag.lower() for tag in entry.tags)):
                results.append(entry)
        
        return results[:limit]
    
    def get_by_type(self, entry_type: str) -> List[KnowledgeEntry]:
        """按类型获取"""
        return [e for e in self.entries if e.type == entry_type]
    
    def get_by_severity(self, severity: str) -> List[KnowledgeEntry]:
        """按严重程度获取"""
        return [e for e in self.entries if e.severity == severity]
```

**预计工时**: 3小时

---

## 三、修复优先级

### P0 - 立即修复 (影响核心功能)

| # | 问题 | 预计工时 | 文件 |
|---|------|----------|------|
| 1 | Hooks未触发对抗审查 | 2h | `harnessgenj_hook.py` |
| 2 | GAN对抗循环实现 | 4h | `adversarial_loop.py` (新建) |
| 3 | 双向积分激励 | 2h | `scoring.py` (新建) |

### P1 - 短期修复 (影响用户体验)

| # | 问题 | 预计工时 | 文件 |
|---|------|----------|------|
| 4 | 角色协作激活 | 3h | 框架初始化 |
| 5 | 任务状态机 | 2h | `task_state_machine.py` (新建) |
| 6 | 状态实时持久化 | 2h | 框架核心 |

### P2 - 中期修复 (优化功能)

| # | 问题 | 预计工时 | 文件 |
|---|------|----------|------|
| 7 | 知识库结构化 | 3h | `knowledge_manager.py` (新建) |
| 8 | 知识检索API | 2h | `knowledge_manager.py` |
| 9 | 外部编辑器监控 | 4h | `file_watcher.py` (新建) |

---

## 四、建议的修复顺序

```
Week 1: P0 修复 (8小时)
├── Day 1: Hooks对抗审查触发 (2h)
├── Day 2-3: GAN对抗循环 (4h)
└── Day 4: 双向积分激励 (2h)

Week 2: P1 修复 (7小时)
├── Day 1: 角色协作激活 (3h)
├── Day 2: 任务状态机 (2h)
└── Day 3: 状态持久化 (2h)

Week 3: P2 修复 (9小时)
├── Day 1-2: 知识库结构化 (3h)
├── Day 3: 知识检索API (2h)
└── Day 4: 外部编辑器监控 (4h)
```

---

## 五、快速修复脚本

创建一个快速修复脚本，立即解决问题1：

```python
# .harnessgenj/quick_fix.py

"""
快速修复脚本 - 启用Hooks对抗审查
"""

import os
import sys
from pathlib import Path

def fix_hooks_adversarial():
    """修复Hooks对抗审查触发"""
    
    hook_file = Path(".claude/harnessgenj_hook.py")
    
    if not hook_file.exists():
        print("[ERROR] harnessgenj_hook.py 不存在")
        return False
    
    content = hook_file.read_text(encoding="utf-8")
    
    # 检查是否已修复
    if "harnessgenj import Harness" in content:
        print("[INFO] Hooks已包含对抗审查调用")
        return True
    
    # 添加导入和调用
    import_section = """
from harnessgenj import Harness
"""
    
    review_call = """
    # 【修复】执行实际代码审查
    try:
        h = Harness.from_project(str(get_project_root()))
        success, issues = h.quick_review(content)
        result["review_triggered"] = True
        result["issues"] = issues
        
        if issues:
            print(f"[HarnessGenJ] 发现 {len(issues)} 个问题", file=sys.stderr)
        else:
            print("[HarnessGenJ] 代码审查通过", file=sys.stderr)
    except Exception as e:
        print(f"[HarnessGenJ] 审查失败: {e}", file=sys.stderr)
"""
    
    # 在 trigger_adversarial_review 函数中插入审查调用
    # (需要更精确的代码修改)
    
    print("[INFO] 请手动修改 harnessgenj_hook.py 添加对抗审查调用")
    return True

if __name__ == "__main__":
    fix_hooks_adversarial()
```

---

## 六、验证清单

修复完成后，运行以下验证：

```bash
# 1. 验证Hooks触发
echo "def test(): pass" > .harnessgenj/test_hooks.py
# 检查是否触发对抗审查

# 2. 验证积分双向更新
python -c "
from harnessgenj import Harness
h = Harness.from_project('.')
print(h.get_score_leaderboard())
"

# 3. 验证对抗循环
python -c "
from harnessgenj import Harness
h = Harness.from_project('.')
result = h.adversarial_develop('测试', max_rounds=1, code='print(1)')
print(f'success={result.success}, rounds={result.rounds}')
"

# 4. 验证任务状态机
python -c "
from harnessgenj.task_state_machine import TaskStateMachine
tsm = TaskStateMachine('.harnessgenj/current_task.json')
print(tsm.start())  # pending -> in_progress
"
```

---

*此文档由HGJ监控服务生成*
*生成时间: 2026-04-08*