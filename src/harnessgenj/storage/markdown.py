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
import time


class KnowledgeEntry(BaseModel):
    """知识条目"""

    id: str = Field(..., description="知识ID")
    title: str = Field(..., description="标题")
    content: str = Field(..., description="内容")
    category: str = Field(default="general", description="分类")
    tags: list[str] = Field(default_factory=list, description="标签")
    importance: int = Field(default=50, ge=0, le=100, description="重要性")
    created_at: float = Field(default_factory=time.time, description="创建时间")
    updated_at: float = Field(default_factory=time.time, description="更新时间")
    metadata: dict[str, Any] = Field(default_factory=dict, description="元数据")


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