"""
Skill Accumulator - 技能积累器

将提取的模式转换为可复用的技能定义：
1. 验证模式有效性
2. 生成技能定义
3. 存储到知识库
4. 管理技能生命周期
5. 技能淘汰机制

使用示例:
    from harnessgenj.evolution.skill_accumulator import SkillAccumulator, SkillType

    accumulator = SkillAccumulator()

    # 从模式积累技能
    skill = accumulator.accumulate_pattern(pattern)

    # 存储技能
    skill_id = accumulator.store_skill(skill)

    # 获取角色可用技能
    skills = accumulator.get_skills_for_role("developer")
"""

from typing import Any, Optional
from pydantic import BaseModel, Field
from enum import Enum
import time
import json
from pathlib import Path


class SkillType(str, Enum):
    """技能类型"""

    GENERATOR = "generator"         # 生成器技能（编码、设计）
    DISCRIMINATOR = "discriminator"  # 判别器技能（审查、检测）
    COMMON = "common"               # 通用技能


class RoleSkill(BaseModel):
    """角色技能定义"""

    skill_id: str = Field(..., description="技能ID")
    skill_name: str = Field(..., description="技能名称")
    skill_type: SkillType = Field(default=SkillType.GENERATOR, description="技能类型")
    applicable_roles: list[str] = Field(default_factory=list, description="适用角色")
    trigger_conditions: list[str] = Field(default_factory=list, description="触发条件")
    execution_template: str = Field(default="", description="执行模板")
    context_requirements: list[str] = Field(default_factory=list, description="所需上下文")
    quality_threshold: float = Field(default=70.0, description="质量阈值")
    success_rate: float = Field(default=0.0, description="成功率")
    usage_count: int = Field(default=0, description="使用次数")
    created_at: float = Field(default_factory=time.time, description="创建时间")
    updated_at: float = Field(default_factory=time.time, description="更新时间")
    verified: bool = Field(default=False, description="是否已验证")
    source_pattern_id: Optional[str] = Field(default=None, description="来源模式ID")
    is_retired: bool = Field(default=False, description="是否已淘汰")
    retirement_reason: Optional[str] = Field(default=None, description="淘汰原因")
    tags: list[str] = Field(default_factory=list, description="标签")
    metadata: dict[str, Any] = Field(default_factory=dict, description="额外元数据")

    def is_applicable_to(self, role_type: str) -> bool:
        """检查是否适用于指定角色"""
        return role_type.lower() in [r.lower() for r in self.applicable_roles]

    def matches_trigger(self, context: str) -> bool:
        """检查是否匹配触发条件"""
        for condition in self.trigger_conditions:
            if condition.lower() in context.lower():
                return True
        return False

    def record_usage(self, success: bool) -> None:
        """记录使用"""
        self.usage_count += 1
        # 更新成功率（加权平均）
        if success:
            self.success_rate = self.success_rate * 0.9 + 0.1
        else:
            self.success_rate = self.success_rate * 0.9
        self.updated_at = time.time()


class SkillAccumulatorStats(BaseModel):
    """技能积累器统计"""

    total_skills: int = Field(default=0, description="总技能数")
    verified_skills: int = Field(default=0, description="已验证技能数")
    retired_skills: int = Field(default=0, description="已淘汰技能数")
    avg_success_rate: float = Field(default=0.0, description="平均成功率")
    skills_by_type: dict[str, int] = Field(default_factory=dict, description="按类型统计")
    skills_by_role: dict[str, int] = Field(default_factory=dict, description="按角色统计")
    recently_added: list[str] = Field(default_factory=list, description="最近添加的技能")


class SkillAccumulatorConfig(BaseModel):
    """技能积累器配置"""

    min_success_rate: float = Field(default=0.7, description="最小成功率阈值")
    min_usage_count: int = Field(default=5, description="最小使用次数")
    retire_threshold: float = Field(default=0.3, description="淘汰阈值（成功率低于此值）")
    auto_verify: bool = Field(default=True, description="自动验证")
    max_skills_per_role: int = Field(default=20, description="每角色最大技能数")


class SkillAccumulator:
    """
    技能积累器

    功能：
    1. 模式转换为技能
    2. 技能存储和管理
    3. 技能验证和淘汰
    4. 角色技能查询

    与 StructuredKnowledgeManager 集成存储技能。
    """

    # 存储目录
    SKILLS_DIR = "skills"

    def __init__(
        self,
        storage_path: Optional[str] = None,
        config: Optional[SkillAccumulatorConfig] = None,
        knowledge_manager: Optional[Any] = None,
        pattern_extractor: Optional[Any] = None,
    ):
        """
        初始化技能积累器

        Args:
            storage_path: 存储路径
            config: 积累器配置
            knowledge_manager: 结构化知识管理器
            pattern_extractor: 模式提取器
        """
        self._storage_path = Path(storage_path or ".harnessgenj")
        self._skills_path = self._storage_path / self.SKILLS_DIR
        self._config = config or SkillAccumulatorConfig()
        self._knowledge_manager = knowledge_manager
        self._pattern_extractor = pattern_extractor

        # 技能存储
        self._skills: dict[str, RoleSkill] = {}
        self._skills_by_role: dict[str, list[str]] = {}
        self._skills_by_type: dict[SkillType, list[str]] = {}

        # 加载已有技能
        self._load()

    def accumulate_pattern(
        self,
        pattern: dict[str, Any] | Any,
        validate: bool = True,
    ) -> Optional[RoleSkill]:
        """
        从模式积累技能

        Args:
            pattern: 提取的模式（dict 或 ExtractedPattern）
            validate: 是否验证模式有效性

        Returns:
            生成的技能或 None（如果模式无效）
        """
        # 提取模式数据
        if hasattr(pattern, "model_dump"):
            pattern_data = pattern.model_dump()
        elif isinstance(pattern, dict):
            pattern_data = pattern
        else:
            return None

        # 验证模式有效性
        if validate:
            success_rate = pattern_data.get("success_rate", 0)
            quality_score = pattern_data.get("quality_score", 0)

            if success_rate < self._config.min_success_rate:
                return None

            if quality_score < 70:
                return None

        # 创建技能定义
        skill = RoleSkill(
            skill_id=self._generate_skill_id(pattern_data),
            skill_name=pattern_data.get("name", "unnamed_skill"),
            skill_type=SkillType(pattern_data.get("skill_type", "generator")),
            applicable_roles=pattern_data.get("applicable_roles", ["developer"]),
            trigger_conditions=pattern_data.get("trigger_conditions", []),
            execution_template=pattern_data.get("execution_template", ""),
            context_requirements=pattern_data.get("context_requirements", []),
            quality_threshold=self._config.min_success_rate,
            success_rate=pattern_data.get("success_rate", 0.8),
            source_pattern_id=pattern_data.get("pattern_id"),
            verified=pattern_data.get("verified", False) if self._config.auto_verify else False,
            tags=pattern_data.get("tags", []),
        )

        return skill

    def store_skill(self, skill: RoleSkill) -> str:
        """
        存储技能

        Args:
            skill: 技能定义

        Returns:
            技能ID
        """
        # 存入内存
        self._skills[skill.skill_id] = skill

        # 按角色索引
        for role in skill.applicable_roles:
            role_lower = role.lower()
            if role_lower not in self._skills_by_role:
                self._skills_by_role[role_lower] = []
            if skill.skill_id not in self._skills_by_role[role_lower]:
                self._skills_by_role[role_lower].append(skill.skill_id)

        # 按类型索引
        if skill.skill_type not in self._skills_by_type:
            self._skills_by_type[skill.skill_type] = []
        self._skills_by_type[skill.skill_type].append(skill.skill_id)

        # 存入知识库
        if self._knowledge_manager:
            self._store_to_knowledge_manager(skill)

        # 持久化
        self._persist()

        return skill.skill_id

    def update_skill(
        self,
        skill_id: str,
        updates: dict[str, Any],
    ) -> Optional[RoleSkill]:
        """
        更新技能

        Args:
            skill_id: 技能ID
            updates: 更新内容

        Returns:
            更新后的技能或 None
        """
        if skill_id not in self._skills:
            return None

        skill = self._skills[skill_id]

        # 应用更新
        for key, value in updates.items():
            if hasattr(skill, key):
                setattr(skill, key, value)

        skill.updated_at = time.time()

        # 持久化
        self._persist()

        return skill

    def retire_skill(
        self,
        skill_id: str,
        reason: str = "成功率过低",
    ) -> bool:
        """
        淘汰技能

        Args:
            skill_id: 技能ID
            reason: 淘汰原因

        Returns:
            是否成功淘汰
        """
        if skill_id not in self._skills:
            return False

        skill = self._skills[skill_id]
        skill.is_retired = True
        skill.retirement_reason = reason
        skill.updated_at = time.time()

        # 从角色索引移除
        for role in skill.applicable_roles:
            role_lower = role.lower()
            if role_lower in self._skills_by_role:
                if skill_id in self._skills_by_role[role_lower]:
                    self._skills_by_role[role_lower].remove(skill_id)

        # 持久化
        self._persist()

        return True

    def get_skills_for_role(
        self,
        role_type: str,
        include_retired: bool = False,
    ) -> list[RoleSkill]:
        """
        获取角色可用技能

        Args:
            role_type: 角色类型
            include_retired: 是否包含已淘汰技能

        Returns:
            技能列表
        """
        role_lower = role_type.lower()
        skill_ids = self._skills_by_role.get(role_lower, [])

        skills = []
        for skill_id in skill_ids:
            if skill_id in self._skills:
                skill = self._skills[skill_id]
                if include_retired or not skill.is_retired:
                    skills.append(skill)

        # 按成功率排序
        skills.sort(key=lambda s: s.success_rate, reverse=True)

        return skills

    def get_verified_skills(self) -> list[RoleSkill]:
        """获取已验证技能"""
        return [s for s in self._skills.values() if s.verified and not s.is_retired]

    def get_skill(self, skill_id: str) -> Optional[RoleSkill]:
        """获取指定技能"""
        return self._skills.get(skill_id)

    def find_matching_skills(
        self,
        context: str,
        role_type: Optional[str] = None,
    ) -> list[RoleSkill]:
        """
        查找匹配上下文的技能

        Args:
            context: 上下文描述
            role_type: 角色类型（可选）

        Returns:
            匹配的技能列表
        """
        matching = []

        for skill in self._skills.values():
            if skill.is_retired:
                continue

            # 检查角色适用性
            if role_type and not skill.is_applicable_to(role_type):
                continue

            # 检查触发条件
            if skill.matches_trigger(context):
                matching.append(skill)

        return matching

    def record_skill_usage(
        self,
        skill_id: str,
        success: bool,
    ) -> bool:
        """
        记录技能使用

        Args:
            skill_id: 技能ID
            success: 是否成功

        Returns:
            是否成功记录
        """
        if skill_id not in self._skills:
            return False

        skill = self._skills[skill_id]
        skill.record_usage(success)

        # 检查是否需要淘汰
        if skill.success_rate < self._config.retire_threshold:
            if skill.usage_count >= self._config.min_usage_count:
                self.retire_skill(skill_id, f"成功率降至 {skill.success_rate:.2f}")

        # 持久化
        self._persist()

        return True

    def validate_all_skills(self) -> dict[str, Any]:
        """
        验证所有技能

        Returns:
            验证结果统计
        """
        results = {
            "total": len(self._skills),
            "verified": 0,
            "need_review": 0,
            "retired": 0,
        }

        for skill in self._skills.values():
            if skill.is_retired:
                results["retired"] += 1
            elif skill.verified:
                results["verified"] += 1
            elif skill.success_rate >= self._config.min_success_rate:
                # 自动验证
                skill.verified = True
                results["verified"] += 1
            else:
                results["need_review"] += 1

        # 持久化
        self._persist()

        return results

    def get_stats(self) -> SkillAccumulatorStats:
        """获取统计信息"""
        stats = SkillAccumulatorStats()

        active_skills = [s for s in self._skills.values() if not s.is_retired]

        stats.total_skills = len(self._skills)
        stats.verified_skills = len([s for s in active_skills if s.verified])
        stats.retired_skills = len([s for s in self._skills.values() if s.is_retired])

        if active_skills:
            stats.avg_success_rate = sum(s.success_rate for s in active_skills) / len(active_skills)

        stats.skills_by_type = {
            t.name: len(ids) for t, ids in self._skills_by_type.items()
        }
        stats.skills_by_role = dict(self._skills_by_role)

        # 最近添加的5个技能
        recent = sorted(
            [s for s in self._skills.values()],
            key=lambda s: s.created_at,
            reverse=True
        )[:5]
        stats.recently_added = [s.skill_id for s in recent]

        return stats

    def _generate_skill_id(self, pattern_data: dict) -> str:
        """生成技能ID"""
        name = pattern_data.get("name", "skill")
        # 清理名称
        clean_name = name.lower().replace(" ", "_").replace("-", "_")
        return f"skill-{clean_name}-{int(time.time() * 1000) % 10000}"

    def _store_to_knowledge_manager(self, skill: RoleSkill) -> bool:
        """存储到知识管理器"""
        if not self._knowledge_manager:
            return False

        try:
            # 创建知识条目
            entry = {
                "id": skill.skill_id,
                "type": "skill",
                "problem": skill.trigger_conditions,
                "solution": skill.execution_template,
                "verified": skill.verified,
                "tags": skill.tags,
            }

            # 存储
            self._knowledge_manager.store(entry)
            return True
        except Exception:
            return False

    def _persist(self) -> None:
        """持久化存储"""
        self._skills_path.mkdir(parents=True, exist_ok=True)

        # 按角色存储
        for role, skill_ids in self._skills_by_role.items():
            file_path = self._skills_path / f"{role}_skills.json"
            skills_data = [
                self._skills[id].model_dump()
                for id in skill_ids
                if id in self._skills
            ]
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(skills_data, f, indent=2, ensure_ascii=False)

        # 存储所有技能索引
        index_path = self._skills_path / "skills_index.json"
        index_data = {
            "all_skills": {id: s.model_dump() for id, s in self._skills.items()},
            "by_role": self._skills_by_role,
            "by_type": {t.name: ids for t, ids in self._skills_by_type.items()},
            "updated_at": time.time(),
        }
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)

    def _load(self) -> None:
        """加载已有技能"""
        index_path = self._skills_path / "skills_index.json"

        if not index_path.exists():
            return

        try:
            with open(index_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for id, skill_data in data.get("all_skills", {}).items():
                self._skills[id] = RoleSkill(**skill_data)

            self._skills_by_role = data.get("by_role", {})

            for type_name, ids in data.get("by_type", {}).items():
                self._skills_by_type[SkillType(type_name)] = ids

        except (json.JSONDecodeError, KeyError, ValueError):
            pass


def create_skill_accumulator(
    storage_path: Optional[str] = None,
    **kwargs: Any,
) -> SkillAccumulator:
    """创建技能积累器"""
    return SkillAccumulator(storage_path, **kwargs)