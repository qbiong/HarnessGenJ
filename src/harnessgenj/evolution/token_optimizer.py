"""
Token Optimizer - Token 优化器

实现高频模式内联以减少 token 消耗：
1. 识别高频模式（HotspotDetector）
2. 自动内联到上下文模板
3. 减少知识检索开销
4. 计算节省效果
5. 与 AutoAssembler 集成

使用示例:
    from harnessgenj.evolution.token_optimizer import TokenOptimizer

    optimizer = TokenOptimizer()

    # 识别内联候选
    candidates = optimizer.identify_inline_candidates(hotspots)

    # 内联模式
    optimizer.inline_pattern(pattern, context_template)

    # 计算节省
    savings = optimizer.compute_token_savings(pattern_id)
"""

from typing import Any, Optional
from pydantic import BaseModel, Field
import time
import json
from pathlib import Path


class InlineCandidate(BaseModel):
    """内联候选"""

    pattern_id: str = Field(..., description="模式ID")
    pattern_name: str = Field(..., description="模式名称")
    call_count: int = Field(default=0, description="调用次数")
    estimated_tokens: int = Field(default=0, description="估计token数")
    potential_savings: int = Field(default=0, description="潜在节省token数")
    priority: int = Field(default=0, description="内联优先级")
    recommended: bool = Field(default=False, description="是否推荐内联")


class TokenSavingsReport(BaseModel):
    """Token 节省报告"""

    report_id: str = Field(..., description="报告ID")
    patterns_inlined: int = Field(default=0, description="已内联模式数")
    total_tokens_saved: int = Field(default=0, description="总节省token数")
    retrieval_calls_reduced: int = Field(default=0, description="减少的检索调用数")
    avg_time_saved_ms: float = Field(default=0.0, description="平均时间节省(毫秒)")
    inline_candidates: list[str] = Field(default_factory=list, description="内联候选列表")
    created_at: float = Field(default_factory=time.time, description="创建时间")


class TokenOptimizerConfig(BaseModel):
    """Token 优化器配置"""

    min_call_count: int = Field(default=10, description="最小调用次数阈值")
    max_inline_tokens: int = Field(default=500, description="最大内联token数")
    inline_threshold: float = Field(default=0.8, description="内联阈值（频率）")
    auto_inline: bool = Field(default=False, description="自动内联")
    report_interval: float = Field(default=3600.0, description="报告间隔(秒)")


class TokenOptimizer:
    """
    Token 优化器

    功能：
    1. 识别高频模式
    2. 自动内联
    3. 计算节省效果
    4. 更新装配器模板

    与 HotspotDetector 和 ContextAssembler 集成。
    """

    # 存储文件
    OPTIMIZER_FILE = "token_optimizer.json"

    def __init__(
        self,
        storage_path: Optional[str] = None,
        config: Optional[TokenOptimizerConfig] = None,
        hotspot_detector: Optional[Any] = None,
        context_assembler: Optional[Any] = None,
        auto_assembler: Optional[Any] = None,
        skill_registry: Optional[Any] = None,
    ):
        """
        初始化 Token 优化器

        Args:
            storage_path: 存储路径
            config: 优化器配置
            hotspot_detector: 热点检测器
            context_assembler: 上下文装配器
            auto_assembler: 自动装配器
            skill_registry: 技能注册表
        """
        self._storage_path = Path(storage_path or ".harnessgenj")
        self._config = config or TokenOptimizerConfig()
        self._hotspot_detector = hotspot_detector
        self._context_assembler = context_assembler
        self._auto_assembler = auto_assembler
        self._skill_registry = skill_registry

        # 内联状态
        self._inline_patterns: dict[str, str] = {}  # pattern_id -> inline_content
        self._savings_history: list[TokenSavingsReport] = []
        self._total_savings: int = 0

        # 加载已有状态
        self._load()

    def identify_inline_candidates(
        self,
        hotspots: Optional[list[dict[str, Any]]] = None,
    ) -> list[InlineCandidate]:
        """
        识别可内联的高频模式

        Args:
            hotspots: 热点检测结果（可选）

        Returns:
            内联候选列表
        """
        candidates = []

        # 获取热点数据
        if hotspots is None and self._hotspot_detector:
            try:
                hotspots = self._hotspot_detector.detect_hotspots()
            except Exception:
                hotspots = []

        if not hotspots:
            return candidates

        for hotspot in hotspots:
            # 检查是否适合内联
            suggested_strategy = hotspot.get("suggested_strategy", "")
            call_count = hotspot.get("call_count", 0)
            name = hotspot.get("name", "")

            if suggested_strategy == "inline" and call_count >= self._config.min_call_count:
                # 估算 token 数
                estimated_tokens = self._estimate_tokens(name)

                if estimated_tokens <= self._config.max_inline_tokens:
                    candidate = InlineCandidate(
                        pattern_id=hotspot.get("id", name),
                        pattern_name=name,
                        call_count=call_count,
                        estimated_tokens=estimated_tokens,
                        potential_savings=call_count * estimated_tokens,
                        priority=call_count,
                        recommended=True,
                    )
                    candidates.append(candidate)

        # 按优先级排序
        candidates.sort(key=lambda c: c.priority, reverse=True)

        return candidates

    def inline_pattern(
        self,
        pattern: dict[str, Any] | Any,
        context_template: Optional[str] = None,
    ) -> str:
        """
        内联模式到上下文模板

        Args:
            pattern: 模式（dict 或 ExtractedPattern）
            context_template: 现有模板（可选）

        Returns:
            更新后的模板
        """
        # 提取模式数据
        if hasattr(pattern, "model_dump"):
            pattern_data = pattern.model_dump()
        elif isinstance(pattern, dict):
            pattern_data = pattern
        else:
            return context_template or ""

        pattern_id = pattern_data.get("pattern_id", "")
        name = pattern_data.get("name", "unnamed")
        template = pattern_data.get("solution_template", "")

        if not template:
            return context_template or ""

        # 格式化内联内容
        inline_section = self._format_inline_section(name, template)

        # 添加到模板
        if context_template:
            # 查找插入位置
            if "## 高频技能" in context_template:
                # 已有高频技能部分，追加
                updated = context_template + "\n" + inline_section
            else:
                # 新增高频技能部分
                updated = context_template + "\n\n## 高频技能（自动内联）\n" + inline_section
        else:
            updated = inline_section

        # 记录内联状态
        self._inline_patterns[pattern_id] = inline_section

        # 更新上下文装配器
        if self._context_assembler:
            self._update_assembler(inline_section)

        # 持久化
        self._persist()

        return updated

    def compute_token_savings(
        self,
        pattern_id: str,
    ) -> int:
        """
        计算 token 节省

        Args:
            pattern_id: 模式ID

        Returns:
            节省的 token 数
        """
        if pattern_id not in self._inline_patterns:
            return 0

        # 从热点检测器获取调用频率
        call_count = 0
        if self._hotspot_detector:
            try:
                frequency = self._hotspot_detector.get_pattern_frequency(pattern_id)
                call_count = frequency
            except Exception:
                pass

        # 估算每次检索的 token 开销
        retrieval_cost = 100  # 估算：每次检索约100 token

        # 内联后的开销
        inline_cost = len(self._inline_patterns[pattern_id]) // 4  # 约4字符=1token

        # 总节省
        savings = call_count * retrieval_cost - inline_cost

        return max(0, savings)

    def get_total_savings(self) -> int:
        """获取总 token 节省"""
        return self._total_savings

    def get_inline_patterns(self) -> list[str]:
        """获取已内联的模式ID列表"""
        return list(self._inline_patterns.keys())

    def generate_report(self) -> TokenSavingsReport:
        """生成节省报告"""
        report = TokenSavingsReport(
            report_id=f"report-{int(time.time() * 1000)}",
            patterns_inlined=len(self._inline_patterns),
            total_tokens_saved=self._total_savings,
            retrieval_calls_reduced=sum(
                self._get_pattern_calls(pid) for pid in self._inline_patterns.keys()
            ),
            inline_candidates=self.get_inline_patterns(),
        )

        self._savings_history.append(report)

        # 持久化
        self._persist()

        return report

    def optimize_all_candidates(self) -> TokenSavingsReport:
        """
        优化所有候选模式

        Returns:
            优化报告
        """
        candidates = self.identify_inline_candidates()

        total_savings = 0

        for candidate in candidates:
            if candidate.recommended:
                # 获取模式内容
                pattern = self._get_pattern(candidate.pattern_id)

                if pattern:
                    # 内联
                    self.inline_pattern(pattern)

                    # 计算节省
                    savings = self.compute_token_savings(candidate.pattern_id)
                    total_savings += savings

        self._total_savings += total_savings

        return self.generate_report()

    def _estimate_tokens(self, content: str) -> int:
        """估算 token 数"""
        # 简化估算：约4字符=1token
        return len(content) // 4

    def _format_inline_section(self, name: str, template: str) -> str:
        """格式化内联内容"""
        return f"""
### {name}

{template}

---
"""

    def _update_assembler(self, inline_content: str) -> bool:
        """更新上下文装配器"""
        if not self._context_assembler:
            return False

        try:
            # 更新永久知识区域
            self._context_assembler.update_permanent_knowledge(inline_content)
            return True
        except Exception:
            return False

    def _get_pattern(self, pattern_id: str) -> Optional[dict[str, Any]]:
        """获取模式内容"""
        if self._skill_registry:
            skill = self._skill_registry.get_skill(pattern_id)
            if skill:
                return {
                    "pattern_id": pattern_id,
                    "name": skill.skill_name,
                    "solution_template": skill.execution_template,
                }
        return None

    def _get_pattern_calls(self, pattern_id: str) -> int:
        """获取模式调用次数"""
        if self._hotspot_detector:
            try:
                return self._hotspot_detector.get_pattern_frequency(pattern_id)
            except Exception:
                pass
        return 0

    def _persist(self) -> None:
        """持久化存储"""
        self._storage_path.mkdir(parents=True, exist_ok=True)
        file_path = self._storage_path / self.OPTIMIZER_FILE

        data = {
            "inline_patterns": self._inline_patterns,
            "total_savings": self._total_savings,
            "savings_history": [r.model_dump() for r in self._savings_history[-10:]],  # 保留最近10个
            "updated_at": time.time(),
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load(self) -> None:
        """加载已有状态"""
        file_path = self._storage_path / self.OPTIMIZER_FILE

        if not file_path.exists():
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._inline_patterns = data.get("inline_patterns", {})
            self._total_savings = data.get("total_savings", 0)

            for report_data in data.get("savings_history", []):
                self._savings_history.append(TokenSavingsReport(**report_data))

        except (json.JSONDecodeError, KeyError, ValueError):
            pass


def create_token_optimizer(
    storage_path: Optional[str] = None,
    **kwargs: Any,
) -> TokenOptimizer:
    """创建 Token 优化器"""
    return TokenOptimizer(storage_path, **kwargs)