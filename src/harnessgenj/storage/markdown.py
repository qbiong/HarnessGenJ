"""
Markdown Storage - 使用Markdown文件存储知识库

轻量化存储方案:
- 无需数据库配置
- 人类可读的知识库
- 版本控制友好
- 开箱即用
"""

from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field
from enum import Enum
import time


class KnowledgeType(str, Enum):
    """知识条目类型"""

    BUG_FIX = "bug_fix"                    # 问题修复记录
    DECISION_PATTERN = "decision_pattern"  # 决策模式沉淀
    ARCHITECTURE_CHANGE = "architecture"   # 架构演进追踪
    TEST_CASE = "test_case"                # 测试用例库
    SECURITY_ISSUE = "security_issue"      # 安全问题追踪
    GENERAL = "general"                    # 通用知识


class KnowledgeEntry(BaseModel):
    """知识条目"""

    id: str = Field(..., description="知识ID")
    title: str = Field(..., description="标题")
    content: str = Field(..., description="内容")
    category: str = Field(default="general", description="分类")
    knowledge_type: KnowledgeType = Field(default=KnowledgeType.GENERAL, description="知识类型")
    tags: list[str] = Field(default_factory=list, description="标签")
    importance: int = Field(default=50, ge=0, le=100, description="重要性")
    created_at: float = Field(default_factory=time.time, description="创建时间")
    updated_at: float = Field(default_factory=time.time, description="更新时间")
    metadata: dict[str, Any] = Field(default_factory=dict, description="元数据")

    # 新增结构化字段
    problem: str | None = Field(default=None, description="问题描述")
    solution: str | None = Field(default=None, description="解决方案")
    code_location: str | None = Field(default=None, description="代码位置（文件:行号）")
    rationale: str | None = Field(default=None, description="决策理由")
    alternatives: list[str] = Field(default_factory=list, description="备选方案")
    verified: bool = Field(default=False, description="是否已验证")


# ==================== 类型模板工厂 ====================

def create_bug_fix_entry(
    problem: str,
    solution: str,
    code_location: str | None = None,
    tags: list[str] | None = None,
) -> KnowledgeEntry:
    """
    创建 Bug 修复记录

    Args:
        problem: 问题描述
        solution: 解决方案
        code_location: 代码位置（如 "src/main.py:42"）
        tags: 标签列表

    Returns:
        结构化的知识条目

    使用示例:
        entry = create_bug_fix_entry(
            problem="登录页面验证码显示异常",
            solution="修复 CSS z-index 问题",
            code_location="src/views/login.py:156",
        )
    """
    import uuid

    return KnowledgeEntry(
        id=f"bug-fix-{uuid.uuid4().hex[:8]}",
        title=f"Bug修复: {problem[:50]}",
        content=f"## 问题\n{problem}\n\n## 解决方案\n{solution}",
        category="bug_fix",
        knowledge_type=KnowledgeType.BUG_FIX,
        problem=problem,
        solution=solution,
        code_location=code_location,
        tags=tags or ["bug"],
        importance=70,
    )


def create_decision_pattern_entry(
    rationale: str,
    choice: str,
    alternatives: list[str] | None = None,
    context: str | None = None,
) -> KnowledgeEntry:
    """
    创建决策模式记录

    Args:
        rationale: 决策理由
        choice: 选择的方案
        alternatives: 备选方案列表
        context: 决策上下文

    Returns:
        结构化的知识条目

    使用示例:
        entry = create_decision_pattern_entry(
            rationale="PostgreSQL 更适合复杂查询场景",
            choice="PostgreSQL",
            alternatives=["MySQL", "MongoDB"],
            context="电商系统数据库选型",
        )
    """
    import uuid

    alt_text = "\n".join(f"- {alt}" for alt in (alternatives or []))

    return KnowledgeEntry(
        id=f"decision-{uuid.uuid4().hex[:8]}",
        title=f"决策: {choice}",
        content=f"## 决策\n选择: {choice}\n\n## 理由\n{rationale}\n\n## 备选方案\n{alt_text}",
        category="decision_pattern",
        knowledge_type=KnowledgeType.DECISION_PATTERN,
        rationale=rationale,
        alternatives=alternatives or [],
        metadata={"context": context} if context else {},
        tags=["decision"],
        importance=75,
    )


def create_architecture_change_entry(
    before: str,
    after: str,
    reason: str,
    affected_files: list[str] | None = None,
) -> KnowledgeEntry:
    """
    创建架构变更记录

    Args:
        before: 变更前架构
        after: 变更后架构
        reason: 变更原因
        affected_files: 受影响的文件列表

    Returns:
        结构化的知识条目

    使用示例:
        entry = create_architecture_change_entry(
            before="单体架构",
            after="微服务架构",
            reason="支持独立部署和扩展",
            affected_files=["src/api/", "src/services/"],
        )
    """
    import uuid

    return KnowledgeEntry(
        id=f"arch-{uuid.uuid4().hex[:8]}",
        title=f"架构变更: {before} → {after}",
        content=f"## 变更前\n{before}\n\n## 变更后\n{after}\n\n## 原因\n{reason}",
        category="architecture",
        knowledge_type=KnowledgeType.ARCHITECTURE_CHANGE,
        metadata={"affected_files": affected_files or []},
        tags=["architecture"],
        importance=90,  # 架构变更重要性高
    )


def create_test_case_entry(
    scenario: str,
    expected: str,
    actual: str | None = None,
    code_location: str | None = None,
) -> KnowledgeEntry:
    """
    创建测试用例记录

    Args:
        scenario: 测试场景
        expected: 预期结果
        actual: 实际结果（可选）
        code_location: 测试代码位置

    Returns:
        结构化的知识条目

    使用示例:
        entry = create_test_case_entry(
            scenario="用户登录成功后跳转首页",
            expected="跳转到 /home",
            actual="跳转到 /dashboard",
            code_location="tests/test_login.py:45",
        )
    """
    import uuid

    content = f"## 场景\n{scenario}\n\n## 预期\n{expected}"
    if actual:
        content += f"\n\n## 实际\n{actual}"

    return KnowledgeEntry(
        id=f"test-{uuid.uuid4().hex[:8]}",
        title=f"测试: {scenario[:50]}",
        content=content,
        category="test_case",
        knowledge_type=KnowledgeType.TEST_CASE,
        code_location=code_location,
        verified=actual == expected,
        tags=["test"],
        importance=60,
    )


def create_security_issue_entry(
    vulnerability: str,
    severity: str,
    fix: str | None = None,
    code_location: str | None = None,
) -> KnowledgeEntry:
    """
    创建安全问题记录

    Args:
        vulnerability: 漏洞描述
        severity: 严重程度（critical/high/medium/low）
        fix: 修复方案
        code_location: 代码位置

    Returns:
        结构化的知识条目

    使用示例:
        entry = create_security_issue_entry(
            vulnerability="SQL注入漏洞",
            severity="critical",
            fix="使用参数化查询",
            code_location="src/db/query.py:78",
        )
    """
    import uuid

    severity_importance = {
        "critical": 100,
        "high": 90,
        "medium": 70,
        "low": 50,
    }

    return KnowledgeEntry(
        id=f"sec-{uuid.uuid4().hex[:8]}",
        title=f"安全: [{severity.upper()}] {vulnerability[:50]}",
        content=f"## 漏洞\n{vulnerability}\n\n## 严重程度\n{severity}\n\n## 修复\n{fix or '待修复'}",
        category="security_issue",
        knowledge_type=KnowledgeType.SECURITY_ISSUE,
        problem=vulnerability,
        solution=fix,
        code_location=code_location,
        metadata={"severity": severity},
        tags=["security", severity],
        importance=severity_importance.get(severity, 70),
        verified=fix is not None,
    )


class MarkdownKnowledgeBase:
    """
    Markdown知识库 - 使用Markdown文件存储知识

    特点:
    - 人类可读
    - 版本控制友好
    - 无需数据库
    - 开箱即用

    目录结构:
    .harnessgenj/
    └── knowledge/
        ├── system/         # 系统知识
        │   └── agent_role.md
        ├── tasks/          # 任务知识
        │   └── research.md
        └── index.md        # 知识索引
    """

    def __init__(self, base_path: Path | str = ".harnessgenj/knowledge") -> None:
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._index: dict[str, KnowledgeEntry] = {}
        self._load_index()

    def _load_index(self) -> None:
        """加载知识索引"""
        index_file = self.base_path / "index.md"
        if index_file.exists():
            content = index_file.read_text(encoding="utf-8")
            # 解析索引 (简化实现)
            for line in content.split("\n"):
                if line.startswith("- [") and "](" in line:
                    # 格式: - [title](path)
                    try:
                        title = line.split("[")[1].split("]")[0]
                        path = line.split("](")[1].split(")")[0]
                        # 存储到索引
                        self._index[path] = KnowledgeEntry(
                            id=path.replace("/", "_").replace(".md", ""),
                            title=title,
                            content="",
                        )
                    except (IndexError, ValueError):
                        continue

    def _save_index(self) -> None:
        """保存知识索引"""
        index_file = self.base_path / "index.md"
        lines = ["# Knowledge Index\n\n"]
        lines.append(f"Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        lines.append("## Knowledge Base\n\n")

        for path, entry in sorted(self._index.items()):
            lines.append(f"- [{entry.title}]({path})\n")

        index_file.write_text("".join(lines), encoding="utf-8")

    def save(self, entry: KnowledgeEntry, category: str = "general") -> bool:
        """
        保存知识条目

        Args:
            entry: 知识条目
            category: 分类目录

        Returns:
            是否保存成功
        """
        # 创建分类目录
        category_path = self.base_path / category
        category_path.mkdir(parents=True, exist_ok=True)

        # 生成文件路径
        file_path = category_path / f"{entry.id}.md"
        relative_path = f"{category}/{entry.id}.md"

        # 构建Markdown内容
        content = self._build_markdown(entry)
        file_path.write_text(content, encoding="utf-8")

        # 更新索引
        self._index[relative_path] = entry
        self._save_index()

        return True

    def _build_markdown(self, entry: KnowledgeEntry) -> str:
        """构建Markdown内容"""
        lines = [
            f"# {entry.title}\n\n",
            f"> ID: `{entry.id}` | Category: `{entry.category}` | Importance: `{entry.importance}`\n\n",
            "---\n\n",
            "## Content\n\n",
            f"{entry.content}\n\n",
        ]

        if entry.tags:
            lines.append("## Tags\n\n")
            lines.append(" | ".join([f"`{tag}`" for tag in entry.tags]) + "\n\n")

        lines.extend([
            "---\n\n",
            "## Metadata\n\n",
            f"- Created: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(entry.created_at))}\n",
            f"- Updated: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(entry.updated_at))}\n",
        ])

        if entry.metadata:
            lines.append("\n### Additional Info\n\n")
            for key, value in entry.metadata.items():
                lines.append(f"- **{key}**: {value}\n")

        return "".join(lines)

    def load(self, knowledge_id: str, category: str = "general") -> KnowledgeEntry | None:
        """
        加载知识条目

        Args:
            knowledge_id: 知识ID
            category: 分类

        Returns:
            知识条目
        """
        file_path = self.base_path / category / f"{knowledge_id}.md"
        if not file_path.exists():
            return None

        content = file_path.read_text(encoding="utf-8")
        return self._parse_markdown(content, knowledge_id, category)

    def _parse_markdown(self, content: str, knowledge_id: str, category: str) -> KnowledgeEntry:
        """解析Markdown内容"""
        lines = content.split("\n")

        # 提取标题
        title = knowledge_id
        for line in lines:
            if line.startswith("# "):
                title = line[2:].strip()
                break

        # 提取内容
        content_start = False
        main_content = []
        for line in lines:
            if "## Content" in line:
                content_start = True
                continue
            if content_start and line.startswith("## "):
                break
            if content_start:
                main_content.append(line)

        return KnowledgeEntry(
            id=knowledge_id,
            title=title,
            content="\n".join(main_content).strip(),
            category=category,
        )

    def delete(self, knowledge_id: str, category: str = "general") -> bool:
        """删除知识条目"""
        file_path = self.base_path / category / f"{knowledge_id}.md"
        relative_path = f"{category}/{knowledge_id}.md"

        if file_path.exists():
            file_path.unlink()
            self._index.pop(relative_path, None)
            self._save_index()
            return True
        return False

    def list_all(self) -> list[KnowledgeEntry]:
        """列出所有知识条目"""
        return list(self._index.values())

    def search(self, query: str) -> list[KnowledgeEntry]:
        """
        搜索知识

        Args:
            query: 搜索关键词

        Returns:
            匹配的知识条目
        """
        results = []
        query_lower = query.lower()

        for entry in self._index.values():
            if (query_lower in entry.title.lower() or
                query_lower in entry.content.lower() or
                any(query_lower in tag.lower() for tag in entry.tags)):
                results.append(entry)

        return results


class MarkdownStorage:
    """
    Markdown存储 - 轻量化文件存储

    用于存储:
    - 知识库 (knowledge/)
    - 任务记录 (tasks/)
    - 对话历史 (history/)
    - 配置文件 (config.md)
    """

    def __init__(self, base_path: Path | str = ".harnessgenj") -> None:
        self.base_path = Path(base_path)
        self.knowledge = MarkdownKnowledgeBase(self.base_path / "knowledge")
        self._ensure_structure()

    def _ensure_structure(self) -> None:
        """确保目录结构"""
        (self.base_path / "tasks").mkdir(parents=True, exist_ok=True)
        (self.base_path / "history").mkdir(parents=True, exist_ok=True)

    def save_task(self, task_id: str, content: str, metadata: dict[str, Any] | None = None) -> bool:
        """保存任务记录"""
        file_path = self.base_path / "tasks" / f"{task_id}.md"
        lines = [
            f"# Task: {task_id}\n\n",
            f"> Saved at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n",
            "---\n\n",
            f"{content}\n\n",
        ]
        if metadata:
            lines.append("## Metadata\n\n")
            for key, value in metadata.items():
                lines.append(f"- **{key}**: {value}\n")
        file_path.write_text("".join(lines), encoding="utf-8")
        return True

    def load_task(self, task_id: str) -> str | None:
        """加载任务记录"""
        file_path = self.base_path / "tasks" / f"{task_id}.md"
        if file_path.exists():
            return file_path.read_text(encoding="utf-8")
        return None

    def save_history(self, session_id: str, messages: list[dict[str, str]]) -> bool:
        """保存对话历史"""
        file_path = self.base_path / "history" / f"{session_id}.md"
        lines = [
            f"# Session: {session_id}\n\n",
            f"> Saved at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n",
            "---\n\n",
        ]
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            lines.append(f"### {role.upper()}\n\n{content}\n\n")
        file_path.write_text("".join(lines), encoding="utf-8")
        return True

    def load_history(self, session_id: str) -> list[dict[str, str]]:
        """加载对话历史"""
        file_path = self.base_path / "history" / f"{session_id}.md"
        if not file_path.exists():
            return []
        # 简化实现，返回空列表
        return []

    def save_config(self, config: dict[str, Any]) -> bool:
        """保存配置"""
        file_path = self.base_path / "config.md"
        lines = [
            "# HarnessGenJ Configuration\n\n",
            "> Auto-generated configuration file\n\n",
            "---\n\n",
        ]
        for key, value in config.items():
            lines.append(f"- **{key}**: `{value}`\n")
        file_path.write_text("".join(lines), encoding="utf-8")
        return True

    def get_stats(self) -> dict[str, Any]:
        """获取存储统计"""
        knowledge_count = len(self.knowledge.list_all())
        tasks_count = len(list((self.base_path / "tasks").glob("*.md")))
        history_count = len(list((self.base_path / "history").glob("*.md")))

        return {
            "knowledge_count": knowledge_count,
            "tasks_count": tasks_count,
            "history_count": history_count,
            "base_path": str(self.base_path),
        }