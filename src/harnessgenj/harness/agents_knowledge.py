"""
AGENTS.md 知识文件管理 - Harness 核心能力

类比 Cursor 的 .cursorrules 或 Claude 的 CLAUDE.md:
- 项目知识文件，自动注入上下文
- 存储项目规范、约定、重要知识
- AI 助手启动时自动加载
- 渐进式披露，按需加载

文件结构:
.harnessgenj/
├── AGENTS.md           # 主知识文件（核心规范）
├── agents/             # 分类知识文件
│   ├── tech.md         # 技术栈规范
│   ├── conventions.md  # 代码约定
│   ├── architecture.md # 架构决策
│   ├── testing.md      # 测试规范
│   └── deployment.md   # 部署流程
└── summaries/          # 知识摘要（用于快速加载）
    ├── tech.summary.md
    └── architecture.summary.md
"""

from typing import Any
from pydantic import BaseModel, Field
from pathlib import Path
import time
import os


class KnowledgeSection(BaseModel):
    """知识章节"""

    name: str = Field(..., description="章节名称")
    content: str = Field(..., description="章节内容")
    priority: int = Field(default=50, description="加载优先级 (0-100)")
    auto_inject: bool = Field(default=True, description="是否自动注入上下文")
    roles: list[str] = Field(default_factory=lambda: ["all"], description="适用角色")
    tags: list[str] = Field(default_factory=list, description="标签")


class AgentsKnowledge(BaseModel):
    """AGENTS 知识库"""

    project_name: str = Field(default="", description="项目名称")
    main_content: str = Field(default="", description="AGENTS.md 主内容")
    sections: dict[str, KnowledgeSection] = Field(default_factory=dict, description="分类知识")
    last_updated: float = Field(default_factory=time.time, description="最后更新时间")
    version: int = Field(default=1, description="版本号")


class AgentsKnowledgeManager:
    """
    AGENTS.md 知识管理器

    Harness 核心能力之一:
    1. 知识文件管理（AGENTS.md + 分类知识）
    2. 自动加载和注入
    3. 渐进式披露（按角色/场景加载）
    4. 版本管理

    使用示例:
        manager = AgentsKnowledgeManager(".harnessgenj")

        # 获取全部知识（用于初始化）
        full_knowledge = manager.get_full_knowledge()

        # 获取特定角色的知识（渐进式披露）
        dev_knowledge = manager.get_knowledge_for_role("developer")

        # 获取特定场景的知识
        test_knowledge = manager.get_knowledge_for_context("testing")
    """

    DEFAULT_TEMPLATE = """# AGENTS.md - 项目知识库

> 此文件存储项目核心知识，AI 助手启动时自动加载

## 项目信息

- **项目名称**: {project_name}
- **技术栈**: {tech_stack}
- **当前状态**: {status}

## 核心规范

### 代码规范
- 遵循项目既有的代码风格
- 所有修改需保持向后兼容
- 重要的修改需要添加测试

### 工作流程
- 用户需求 → 项目经理接收 → 开发者执行 → 项目经理确认
- 所有请求通过 `harness.receive_request()` 接收
- 开发完成通过 `harness.complete_task()` 确认

## 重要约定

1. **渐进式披露**: 每个角色只获取最小必要信息
2. **持久化优先**: 所有重要操作自动保存
3. **文档驱动**: 需求/设计/开发/测试都有对应文档

## 常用命令

```python
# 接收用户需求
harness.receive_request("功能描述")

# 开发功能
harness.develop("功能描述")

# 查看状态
harness.get_status()

# 记录内容
harness.record("自动识别类型并记录")
```

---
*此文件由 HarnessGenJ 自动生成和维护*
"""

    def __init__(self, workspace: str = ".harnessgenj") -> None:
        self.workspace = workspace
        self.agents_path = Path(workspace) / "AGENTS.md"
        self.agents_dir = Path(workspace) / "agents"
        self.summaries_dir = Path(workspace) / "summaries"

        self._knowledge: AgentsKnowledge | None = None

        # 确保目录存在
        self._ensure_dirs()

        # 加载知识
        self._load()

    def _ensure_dirs(self) -> None:
        """确保目录存在"""
        self.agents_dir.mkdir(parents=True, exist_ok=True)
        self.summaries_dir.mkdir(parents=True, exist_ok=True)

    def initialize(self, project_name: str, tech_stack: str = "", status: str = "init") -> bool:
        """
        初始化 AGENTS.md

        Args:
            project_name: 项目名称
            tech_stack: 技术栈
            status: 项目状态

        Returns:
            是否成功
        """
        content = self.DEFAULT_TEMPLATE.format(
            project_name=project_name,
            tech_stack=tech_stack or "未指定",
            status=status,
        )

        # 创建主知识文件
        self.agents_path.write_text(content, encoding="utf-8")

        # 创建默认分类知识
        default_sections = {
            "tech": KnowledgeSection(
                name="技术栈",
                content=f"# 技术栈\n\n## 主要技术\n- {tech_stack}\n\n## 依赖管理\n- 使用 pip 或 poetry\n",
                priority=80,
                auto_inject=True,
                roles=["developer", "architect"],
            ),
            "conventions": KnowledgeSection(
                name="代码约定",
                content="# 代码约定\n\n## 编码风格\n- 遵循 PEP 8\n- 类型注解\n\n## 文档\n- 函数必须有文档字符串\n",
                priority=70,
                auto_inject=True,
                roles=["developer"],
            ),
            "workflow": KnowledgeSection(
                name="工作流程",
                content="# 工作流程\n\n## 标准流程\n1. 需求分析 (PM)\n2. 架构设计 (Architect)\n3. 开发实现 (Developer)\n4. 测试验证 (Tester)\n",
                priority=60,
                auto_inject=True,
                roles=["all"],
            ),
        }

        for name, section in default_sections.items():
            self._save_section(name, section)

        self._knowledge = AgentsKnowledge(
            project_name=project_name,
            main_content=content,
            sections=default_sections,
        )

        return True

    def _load(self) -> bool:
        """加载知识文件"""
        if not self.agents_path.exists():
            return False

        try:
            # 加载主文件
            main_content = self.agents_path.read_text(encoding="utf-8")

            # 加载分类知识
            sections = {}
            for section_file in self.agents_dir.glob("*.md"):
                name = section_file.stem
                content = section_file.read_text(encoding="utf-8")

                # 解析元数据（如果存在）
                priority = 50
                auto_inject = True
                roles = ["all"]

                # 从文件内容提取元数据
                for line in content.split("\n")[:10]:
                    if line.startswith("> priority:"):
                        priority = int(line.split(":")[1].strip())
                    elif line.startswith("> auto_inject:"):
                        auto_inject = line.split(":")[1].strip().lower() == "true"
                    elif line.startswith("> roles:"):
                        roles = [r.strip() for r in line.split(":")[1].strip().split(",")]

                sections[name] = KnowledgeSection(
                    name=name,
                    content=content,
                    priority=priority,
                    auto_inject=auto_inject,
                    roles=roles,
                )

            self._knowledge = AgentsKnowledge(
                main_content=main_content,
                sections=sections,
            )
            return True
        except Exception:
            return False

    def _save_section(self, name: str, section: KnowledgeSection) -> bool:
        """保存分类知识"""
        try:
            path = self.agents_dir / f"{name}.md"

            # 构建内容（包含元数据）
            content = f"> priority: {section.priority}\n"
            content += f"> auto_inject: {section.auto_inject}\n"
            content += f"> roles: {','.join(section.roles)}\n\n"
            content += section.content

            path.write_text(content, encoding="utf-8")

            # 保存摘要
            self._save_summary(name, section.content[:200])

            return True
        except Exception:
            return False

    def _save_summary(self, name: str, summary: str) -> bool:
        """保存知识摘要"""
        try:
            path = self.summaries_dir / f"{name}.summary.md"
            path.write_text(summary, encoding="utf-8")
            return True
        except Exception:
            return False

    def get_full_knowledge(self) -> str:
        """
        获取全部知识（用于初始化）

        Returns:
            合并后的知识内容
        """
        if not self._knowledge:
            self._load()

        if not self._knowledge:
            return ""

        # 合并主内容和所有章节
        parts = [self._knowledge.main_content]

        # 按优先级排序章节
        sorted_sections = sorted(
            self._knowledge.sections.items(),
            key=lambda x: x[1].priority,
            reverse=True,
        )

        for name, section in sorted_sections:
            if section.auto_inject:
                parts.append(f"\n\n## {section.name}\n\n{section.content}")

        return "\n".join(parts)

    def get_knowledge_for_role(self, role: str) -> str:
        """
        获取特定角色的知识（渐进式披露）

        Args:
            role: 角色类型

        Returns:
            该角色需要的知识内容
        """
        if not self._knowledge:
            self._load()

        if not self._knowledge:
            return ""

        parts = [self._knowledge.main_content]

        # 只加载该角色相关的章节
        for name, section in self._knowledge.sections.items():
            if section.auto_inject and (
                "all" in section.roles or role in section.roles
            ):
                parts.append(f"\n\n## {section.name}\n\n{section.content}")

        return "\n".join(parts)

    def get_knowledge_summary(self, role: str = "all") -> str:
        """
        获取知识摘要（快速加载）

        Args:
            role: 角色类型

        Returns:
            知识摘要
        """
        if not self._knowledge:
            self._load()

        if not self._knowledge:
            return ""

        summary_lines = [
            f"# {self._knowledge.project_name} 知识摘要",
            "",
            f"版本: {self._knowledge.version}",
            f"更新: {time.strftime('%Y-%m-%d', time.localtime(self._knowledge.last_updated))}",
            "",
        ]

        # 添加章节摘要
        for name, section in self._knowledge.sections.items():
            if "all" in section.roles or role in section.roles:
                summary_path = self.summaries_dir / f"{name}.summary.md"
                if summary_path.exists():
                    summary = summary_path.read_text(encoding="utf-8")
                    summary_lines.append(f"- **{section.name}**: {summary[:100]}...")

        return "\n".join(summary_lines)

    def get_knowledge_for_context(self, context: str) -> str:
        """
        获取特定场景的知识

        Args:
            context: 场景类型

        Returns:
            该场景需要的知识
        """
        context_role_map = {
            "testing": ["tester", "developer"],
            "development": ["developer"],
            "design": ["architect", "developer"],
            "review": ["developer", "architect"],
            "deployment": ["developer", "devops"],
        }

        roles = context_role_map.get(context, ["all"])

        parts = []
        for role in roles:
            parts.append(self.get_knowledge_for_role(role))

        return "\n".join(parts)

    def update_section(self, name: str, content: str, priority: int = 50, roles: list[str] | None = None) -> bool:
        """
        更新知识章节

        Args:
            name: 章节名称
            content: 新内容
            priority: 优先级
            roles: 适用角色

        Returns:
            是否成功
        """
        if not self._knowledge:
            self._load()

        section = KnowledgeSection(
            name=name,
            content=content,
            priority=priority,
            auto_inject=True,
            roles=roles or ["all"],
        )

        if self._knowledge:
            self._knowledge.sections[name] = section
            self._knowledge.last_updated = time.time()
            self._knowledge.version += 1

        return self._save_section(name, section)

    def add_knowledge(self, content: str, section: str = "general") -> bool:
        """
        添加知识内容

        Args:
            content: 知识内容
            section: 章节名称

        Returns:
            是否成功
        """
        if not self._knowledge:
            self._load()

        # 如果章节存在，追加内容
        if self._knowledge and section in self._knowledge.sections:
            existing = self._knowledge.sections[section]
            existing.content += f"\n\n{content}"
            return self._save_section(section, existing)

        # 否则创建新章节
        return self.update_section(section, content)

    def reload(self) -> bool:
        """重新加载知识文件"""
        return self._load()

    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self.agents_path.exists()

    def sync_all_knowledge(self) -> dict[str, Any]:
        """
        同步所有知识文件

        确保 AGENTS.md 为唯一源，其他文件自动派生。
        解决知识分散和不一致问题。

        Returns:
            同步结果统计
        """
        results = {
            "updated": [],
            "skipped": [],
            "errors": [],
            "timestamp": time.time(),
        }

        if not self._knowledge:
            self._load()

        if not self._knowledge:
            results["errors"].append("无法加载知识库")
            return results

        try:
            # 1. 获取主知识内容
            main_content = self._knowledge.main_content

            # 2. 同步 knowledge/general/ 目录
            general_dir = Path(self.workspace) / "knowledge" / "general"
            general_dir.mkdir(parents=True, exist_ok=True)

            # 提取技术栈信息
            tech_stack = self._extract_section(main_content, "技术栈")
            if tech_stack:
                tech_path = general_dir / "tech_stack.md"
                tech_path.write_text(f"# 技术栈\n\n{tech_stack}", encoding="utf-8")
                results["updated"].append("knowledge/general/tech_stack.md")

            # 提取项目描述
            description = self._extract_section(main_content, "项目信息")
            if description:
                desc_path = general_dir / "description.md"
                desc_path.write_text(f"# 项目描述\n\n{description}", encoding="utf-8")
                results["updated"].append("knowledge/general/description.md")

            # 3. 同步 agents/ 目录（角色专用知识）
            for role in ["developer", "architect", "tester", "product_manager"]:
                role_knowledge = self._generate_role_knowledge(main_content, role)
                role_path = self.agents_dir / f"{role}.md"
                role_path.write_text(role_knowledge, encoding="utf-8")
                results["updated"].append(f"agents/{role}.md")

            # 4. 同步 summaries/ 目录（知识摘要）
            for section_name, section in self._knowledge.sections.items():
                summary = self._generate_section_summary(section.content)
                summary_path = self.summaries_dir / f"{section_name}.summary.md"
                summary_path.write_text(summary, encoding="utf-8")
                results["updated"].append(f"summaries/{section_name}.summary.md")

            # 5. 更新知识索引
            self._update_knowledge_index()
            results["updated"].append("knowledge/index.md")

            # 更新版本号
            self._knowledge.last_updated = time.time()
            self._knowledge.version += 1

        except Exception as e:
            results["errors"].append(f"同步失败: {str(e)}")

        return results

    def _extract_section(self, content: str, section_name: str) -> str:
        """
        从内容中提取特定章节

        Args:
            content: 文档内容
            section_name: 章节名称

        Returns:
            提取的章节内容
        """
        import re

        # 匹配章节标题及其内容
        pattern = rf'##\s*{re.escape(section_name)}.*?\n(.*?)(?=\n##|\Z)'
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)

        if match:
            return match.group(1).strip()

        # 尝试匹配带星号的标题
        pattern = rf'\*\*{re.escape(section_name)}\*\*:?\s*(.*?)(?=\n|\Z)'
        match = re.search(pattern, content, re.IGNORECASE)

        if match:
            return match.group(1).strip()

        return ""

    def _generate_role_knowledge(self, main_content: str, role: str) -> str:
        """
        为特定角色生成知识文件

        Args:
            main_content: 主知识内容
            role: 角色名称

        Returns:
            角色专用知识内容
        """
        role_descriptions = {
            "developer": "开发者 - 专注于代码实现",
            "architect": "架构师 - 专注于系统设计",
            "tester": "测试员 - 专注于质量验证",
            "product_manager": "产品经理 - 专注于需求管理",
        }

        # 获取该角色相关的章节
        role_sections = self.get_knowledge_for_role(role)

        content = f"""# {role_descriptions.get(role, role)} 知识文件

> 此文件由 AGENTS.md 自动派生，请勿手动修改
> 更新时间: {time.strftime('%Y-%m-%d %H:%M')}

---

{role_sections}

---

*自动生成于 {time.strftime('%Y-%m-%d %H:%M:%S')}*
"""
        return content

    def _generate_section_summary(self, content: str, max_length: int = 200) -> str:
        """
        生成章节摘要

        Args:
            content: 章节内容
            max_length: 最大长度

        Returns:
            摘要文本
        """
        # 移除 Markdown 格式
        import re
        text = re.sub(r'#+\s*', '', content)
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'`([^`]+)`', r'\1', text)
        text = re.sub(r'\n+', ' ', text)

        # 截断
        if len(text) > max_length:
            return text[:max_length].strip() + "..."

        return text.strip()

    def _update_knowledge_index(self) -> None:
        """更新知识索引文件"""
        index_path = Path(self.workspace) / "knowledge" / "index.md"

        if not self._knowledge:
            return

        content = f"""# 知识库索引

> 更新时间: {time.strftime('%Y-%m-%d %H:%M')}
> 版本: {self._knowledge.version}

## 知识文件列表

### 主知识文件
- [AGENTS.md](../AGENTS.md) - 项目核心知识

### 通用知识 (knowledge/general/)
- [tech_stack.md](general/tech_stack.md) - 技术栈信息
- [description.md](general/description.md) - 项目描述

### 角色知识 (agents/)
- [developer.md](../agents/developer.md) - 开发者知识
- [architect.md](../agents/architect.md) - 架构师知识
- [tester.md](../agents/tester.md) - 测试员知识
- [product_manager.md](../agents/product_manager.md) - 产品经理知识

### 知识摘要 (summaries/)
"""

        for name, section in self._knowledge.sections.items():
            content += f"- [{name}.summary.md](../summaries/{name}.summary.md) - {section.name} 摘要\n"

        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text(content, encoding="utf-8")

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        if not self._knowledge:
            return {"initialized": False}

        return {
            "initialized": True,
            "project_name": self._knowledge.project_name,
            "sections_count": len(self._knowledge.sections),
            "version": self._knowledge.version,
            "last_updated": self._knowledge.last_updated,
            "total_size": len(self.get_full_knowledge()),
        }


def create_agents_knowledge(workspace: str = ".harnessgenj") -> AgentsKnowledgeManager:
    """创建 AGENTS 知识管理器"""
    return AgentsKnowledgeManager(workspace)