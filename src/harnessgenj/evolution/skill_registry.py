"""
Skill Registry - 技能注册表

管理技能注册和发现：
1. 技能注册
2. 按角色查找技能
3. 按触发条件匹配技能
4. 技能生命周期管理

使用示例:
    from harnessgenj.evolution.skill_registry import SkillRegistry

    registry = SkillRegistry()

    # 注册技能
    registry.register("developer", skill)

    # 查找技能
    skills = registry.get_skills_for_role("developer")

    # 匹配触发条件
    matching = registry.find_matching_skills("处理登录验证")
"""

from typing import Any, Optional
from pydantic import BaseModel, Field
import time
import json
from pathlib import Path


class SkillRegistryStats(BaseModel):
    """技能注册表统计"""

    total_registrations: int = Field(default=0, description="总注册数")
    roles_with_skills: int = Field(default=0, description="有技能的角色数")
    avg_skills_per_role: float = Field(default=0.0, description="每角色平均技能数")
    most_used_skill: Optional[str] = Field(default=None, description="最常用技能")
    least_used_skill: Optional[str] = Field(default=None, description="最不常用技能")


class SkillRegistry:
    """
    技能注册表

    功能：
    1. 技能注册
    2. 按角色查找
    3. 触发条件匹配
    4. 使用统计

    与 SkillAccumulator 集成。
    """

    # 存储文件
    REGISTRY_FILE = "skill_registry.json"

    def __init__(
        self,
        storage_path: Optional[str] = None,
        skill_accumulator: Optional[Any] = None,
    ):
        """
        初始化技能注册表

        Args:
            storage_path: 存储路径
            skill_accumulator: 技能积累器
        """
        self._storage_path = Path(storage_path or ".harnessgenj")
        self._skill_accumulator = skill_accumulator

        # 注册表
        self._registry: dict[str, list[str]] = {}  # role_type -> skill_ids
        self._skills: dict[str, Any] = {}  # skill_id -> RoleSkill

        # 使用统计
        self._usage_stats: dict[str, int] = {}  # skill_id -> usage_count

        # 加载已有注册
        self._load()

    def register(
        self,
        role_type: str,
        skill: Any,
    ) -> bool:
        """
        注册技能到角色

        Args:
            role_type: 角色类型
            skill: 技能（RoleSkill）

        Returns:
            是否成功注册
        """
        # 提取技能数据
        if hasattr(skill, "skill_id"):
            skill_id = skill.skill_id
            skill_data = skill
        elif isinstance(skill, dict):
            skill_id = skill.get("skill_id", "")
            skill_data = skill
        else:
            return False

        if not skill_id:
            return False

        # 添加到注册表
        role_lower = role_type.lower()
        if role_lower not in self._registry:
            self._registry[role_lower] = []

        if skill_id not in self._registry[role_lower]:
            self._registry[role_lower].append(skill_id)

        # 存储技能
        self._skills[skill_id] = skill_data

        # 初始化使用统计
        if skill_id not in self._usage_stats:
            self._usage_stats[skill_id] = 0

        # 持久化
        self._persist()

        return True

    def unregister(
        self,
        role_type: str,
        skill_id: str,
    ) -> bool:
        """
        从角色注销技能

        Args:
            role_type: 角色类型
            skill_id: 技能ID

        Returns:
            是否成功注销
        """
        role_lower = role_type.lower()

        if role_lower not in self._registry:
            return False

        if skill_id not in self._registry[role_lower]:
            return False

        self._registry[role_lower].remove(skill_id)

        # 持久化
        self._persist()

        return True

    def get_skills_for_role(
        self,
        role_type: str,
    ) -> list[Any]:
        """
        获取角色的所有技能

        Args:
            role_type: 角色类型

        Returns:
            技能列表
        """
        role_lower = role_type.lower()
        skill_ids = self._registry.get(role_lower, [])

        skills = []
        for skill_id in skill_ids:
            if skill_id in self._skills:
                skills.append(self._skills[skill_id])

        # 按使用次数排序
        skills.sort(
            key=lambda s: self._usage_stats.get(
                s.skill_id if hasattr(s, "skill_id") else s.get("skill_id", ""),
                0
            ),
            reverse=True
        )

        return skills

    def get_skill(
        self,
        skill_id: str,
    ) -> Optional[Any]:
        """
        获取指定技能

        Args:
            skill_id: 技能ID

        Returns:
            技能或 None
        """
        return self._skills.get(skill_id)

    def find_matching_skills(
        self,
        context: str,
        role_type: Optional[str] = None,
    ) -> list[Any]:
        """
        查找匹配触发条件的技能

        Args:
            context: 上下文描述
            role_type: 角色类型（可选）

        Returns:
            匹配的技能列表
        """
        matching = []

        # 确定搜索范围
        if role_type:
            skill_ids = self._registry.get(role_type.lower(), [])
            search_skills = [self._skills.get(id) for id in skill_ids if id in self._skills]
        else:
            search_skills = list(self._skills.values())

        # 匹配触发条件
        for skill in search_skills:
            if skill is None:
                continue

            # 获取触发条件
            if hasattr(skill, "trigger_conditions"):
                conditions = skill.trigger_conditions
            elif isinstance(skill, dict):
                conditions = skill.get("trigger_conditions", [])
            else:
                continue

            # 检查匹配
            for condition in conditions:
                if condition.lower() in context.lower():
                    matching.append(skill)
                    break

        return matching

    def record_usage(
        self,
        skill_id: str,
    ) -> bool:
        """
        记录技能使用

        Args:
            skill_id: 技能ID

        Returns:
            是否成功记录
        """
        if skill_id not in self._skills:
            return False

        self._usage_stats[skill_id] = self._usage_stats.get(skill_id, 0) + 1

        # 持久化
        self._persist()

        return True

    def get_most_used_skills(
        self,
        limit: int = 5,
    ) -> list[tuple[str, int]]:
        """
        获取最常用技能

        Args:
            limit: 返回数量

        Returns:
            (skill_id, usage_count) 列表
        """
        sorted_skills = sorted(
            self._usage_stats.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_skills[:limit]

    def get_unused_skills(self) -> list[str]:
        """获取未使用的技能"""
        return [id for id, count in self._usage_stats.items() if count == 0]

    def cleanup_unused(
        self,
        min_usage: int = 0,
    ) -> int:
        """
        清理低使用技能

        Args:
            min_usage: 最小使用次数阈值

        Returns:
            清理数量
        """
        to_remove = []
        for skill_id, count in self._usage_stats.items():
            if count <= min_usage:
                to_remove.append(skill_id)

        # 从注册表移除
        for skill_id in to_remove:
            self._skills.pop(skill_id, None)
            self._usage_stats.pop(skill_id, None)
            for role in self._registry:
                if skill_id in self._registry[role]:
                    self._registry[role].remove(skill_id)

        # 持久化
        self._persist()

        return len(to_remove)

    def get_stats(self) -> SkillRegistryStats:
        """获取统计信息"""
        stats = SkillRegistryStats()

        stats.total_registrations = sum(len(ids) for ids in self._registry.values())
        stats.roles_with_skills = len([r for r in self._registry.values() if r])

        if stats.roles_with_skills > 0:
            stats.avg_skills_per_role = stats.total_registrations / stats.roles_with_skills

        # 最常用和最不常用
        if self._usage_stats:
            sorted_usage = sorted(self._usage_stats.items(), key=lambda x: x[1])
            stats.least_used_skill = sorted_usage[0][0] if sorted_usage[0][1] == 0 else None
            stats.most_used_skill = sorted_usage[-1][0]

        return stats

    def list_roles(self) -> list[str]:
        """列出所有注册的角色"""
        return [r for r, ids in self._registry.items() if ids]

    def _persist(self) -> None:
        """持久化存储"""
        self._storage_path.mkdir(parents=True, exist_ok=True)
        file_path = self._storage_path / self.REGISTRY_FILE

        # 序列化技能数据
        skills_data = {}
        for skill_id, skill in self._skills.items():
            if hasattr(skill, "model_dump"):
                skills_data[skill_id] = skill.model_dump()
            elif isinstance(skill, dict):
                skills_data[skill_id] = skill
            else:
                skills_data[skill_id] = str(skill)

        data = {
            "registry": self._registry,
            "skills": skills_data,
            "usage_stats": self._usage_stats,
            "updated_at": time.time(),
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load(self) -> None:
        """加载已有注册"""
        file_path = self._storage_path / self.REGISTRY_FILE

        if not file_path.exists():
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._registry = data.get("registry", {})
            self._usage_stats = data.get("usage_stats", {})

            # 加载技能数据（简化为字典形式）
            self._skills = data.get("skills", {})

        except (json.JSONDecodeError, KeyError, ValueError):
            pass


def create_skill_registry(
    storage_path: Optional[str] = None,
    **kwargs: Any,
) -> SkillRegistry:
    """创建技能注册表"""
    return SkillRegistry(storage_path, **kwargs)