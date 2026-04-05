"""
Guide Module - 首次使用引导系统

当用户第一次使用 py_ha 时，引导用户完成：
- 项目基础信息配置
- 团队角色设置
- 使用方式介绍
- 首次接入提示词模板
- 快速上手演示

使用示例:
    from py_ha import Harness

    # 检测是否首次使用
    harness = Harness()
    if harness.is_first_time():
        harness.start_onboarding()

    # 或直接启动引导
    harness.start_onboarding()
"""

from typing import Any
from pydantic import BaseModel, Field
import time
import json
import os


class ProjectConfig(BaseModel):
    """项目配置"""

    project_name: str = Field(default="", description="项目名称")
    project_description: str = Field(default="", description="项目描述")
    tech_stack: str = Field(default="", description="技术栈")
    team_config: dict[str, str] = Field(default_factory=dict, description="团队配置")
    created_at: float = Field(default_factory=time.time, description="创建时间")
    onboarding_completed: bool = Field(default=False, description="引导是否完成")


class OnboardingGuide:
    """
    首次使用引导系统

    提供:
    - 项目信息收集
    - 团队角色配置
    - 使用方式介绍
    - 首次接入提示词模板
    - 快速上手演示

    引导流程:
    1. 检测是否首次使用（检查配置文件）
    2. 引导输入项目信息
    3. 配置团队角色
    4. 展示使用方式
    5. 提供首次接入提示词
    6. 提供快速上手示例
    """

    # 首次接入提示词模板
    ENABLE_PYHA_PROMPT = """
请启用 py_ha 框架协助本项目的开发。

执行以下初始化步骤：

1. 读取项目文档
   - 扫描项目目录下的 README.md、requirements.md、design.md 等文档
   - 提取项目名称、描述、技术栈信息

2. 初始化 py_ha
   - 运行 Python 代码：
     ```python
     from py_ha import Harness

     # 从当前项目目录初始化
     harness = Harness.from_project(".")

     # 获取初始化提示
     init_prompt = harness.get_init_prompt()
     print(init_prompt)
     ```

3. 查看初始化结果
   - 确认 `.py_ha/` 目录已创建
   - 确认项目信息已正确导入

完成后，请汇报初始化结果，包括：
- 项目名称
- 技术栈
- 已导入的文档列表
- 当前项目状态
"""

    ACTIVATE_PM_PROMPT = """
我现在要求你按照 py_ha 框架规范，进入项目经理角色。

作为项目经理，你需要：

【核心职责】
1. 作为用户与开发团队的唯一对接窗口
2. 接收所有用户请求，自动识别意图并分配任务
3. 维护项目文档（requirements、design、development、testing、progress）
4. 调度其他角色（产品经理、架构师、开发者、测试员）执行任务
5. 追踪任务进度，确认任务完成

【工作规范】
- 每次对话开始时，调用 `harness.get_init_prompt()` 获取上下文
- 用户提出需求 → 调用 `harness.receive_request()`
- 用户要求开发 → 调用 `harness.develop()`
- 用户报告 Bug → 调用 `harness.fix_bug()`
- 用户询问状态 → 调用 `harness.get_status()`

【角色调度流程】
需求分析（产品经理）→ 架构设计（架构师）→ 开发实现（开发者）→ 测试验证（测试员）→ 文档更新（项目经理确认）

【渐进式披露原则】
- 调度其他角色时，只传递最小必要上下文
- 开发者只获取：项目基本信息 + 当前需求 + 相关设计
- 产品经理只获取：项目信息 + 需求文档 + 用户对话历史

【回复格式】
每次回复需包含：
1. 任务识别（这是什么类型的请求？）
2. 处理动作（调用了哪个方法？）
3. 任务分配（分配给谁？优先级？）
4. 下一步计划

现在请确认进入项目经理角色，并汇报当前项目状态。
"""

    # 简化版提示词
    QUICK_ENABLE_PROMPT = "启用 py_ha 框架。执行 Harness.from_project('.') 初始化，汇报项目状态。"
    QUICK_ACTIVATE_PM_PROMPT = "进入 py_ha 项目经理角色。作为用户对接窗口，接收请求、分配任务、调度角色、追踪进度。确认并汇报当前状态。"

    # 使用方式提示文本
    USAGE_GUIDE = """
## 💬 开始使用 py_ha

py_ha 提供多种使用方式，你可以选择最适合你的方式：

### 方式一：对话式使用（推荐）

通过自然对话与框架交互，无需记忆复杂命令：

```
# 直接描述你的需求
harness.chat("我想开发一个用户登录功能")

# 框架会自动理解并执行
# 你也可以切换到不同角色的对话
harness.switch_session("product_manager")
harness.chat("登录功能需要支持哪些方式？")

# 切回主开发继续
harness.switch_session("development")
harness.chat("好的，开始实现登录功能")
```

### 方式二：快速开发

一行代码完成完整开发流程：

```
# 开发功能
harness.develop("实现购物车功能")

# 修复 Bug
harness.fix_bug("支付页面偶尔超时")
```

### 方式三：工作流控制

精细控制每个开发阶段：

```
# 启动工作流
harness.run_pipeline("feature", feature_request="用户登录")

# 查看状态
harness.get_pipeline_status()
```

### 方式四：记忆系统

保存重要信息，永不丢失：

```
# 保存重要知识
harness.remember("api_key", "your-api-key", important=True)

# 回忆信息
harness.recall("api_key")
```
"""

    # 快速上手示例
    QUICK_START_EXAMPLES = """
## 🚀 快速上手示例

以下是几个常见场景的对话示例：

### 场景一：开发新功能

```
你: harness.chat("我需要开发一个用户注册功能，支持邮箱注册")
框架: [自动启动开发流程，完成需求分析、开发实现、测试验证]

你: harness.switch_session("product_manager")
你: harness.chat("注册需要支持手机号吗？")
框架: [记录需求讨论，等待确认]

你: harness.switch_session("development")
你: harness.chat("好的，需求已确认，继续开发")
```

### 场景二：修复 Bug

```
你: harness.chat("发现登录页面验证码无法显示")
框架: [自动分析 Bug 并修复]
```

### 场景三：技术讨论

```
你: harness.switch_session("architect")
你: harness.chat("数据库应该选 MySQL 还是 PostgreSQL？")
框架: [架构师角色给出专业建议]

你: harness.switch_session("development")
你: harness.chat("根据架构师建议，我选择 PostgreSQL")
```

### 场景四：进度汇报

```
你: harness.switch_session("project_manager")
你: harness.chat("登录功能已开发完成，准备测试")
框架: [记录进度，更新状态]
```
"""

    def __init__(self, config_path: str | None = None) -> None:
        """
        初始化引导系统

        Args:
            config_path: 配置文件路径，默认为当前目录下的 .py_ha/config.json
        """
        if config_path:
            self.config_path = config_path
        else:
            # 默认配置路径
            self.config_path = os.path.join(os.getcwd(), ".py_ha", "config.json")

        self.config: ProjectConfig | None = None

    def is_first_time(self) -> bool:
        """
        检测是否首次使用

        Returns:
            True 如果没有找到配置文件或引导未完成
        """
        if not os.path.exists(self.config_path):
            return True

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.config = ProjectConfig(**data)
                return not self.config.onboarding_completed
        except (json.JSONDecodeError, KeyError):
            return True

    def load_config(self) -> ProjectConfig | None:
        """
        加载现有配置

        Returns:
            项目配置，如果不存在返回 None
        """
        if self.config:
            return self.config

        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.config = ProjectConfig(**data)
                    return self.config
            except (json.JSONDecodeError, KeyError):
                pass

        return None

    def save_config(self, config: ProjectConfig) -> bool:
        """
        保存配置到文件

        Args:
            config: 项目配置

        Returns:
            是否保存成功
        """
        # 确保目录存在
        config_dir = os.path.dirname(self.config_path)
        if config_dir and not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)

        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config.model_dump(), f, ensure_ascii=False, indent=2)
            self.config = config
            return True
        except Exception:
            return False

    def start(self, harness_instance: Any = None) -> ProjectConfig:
        """
        启动引导流程

        Args:
            harness_instance: Harness 实例（可选）

        Returns:
            完成的项目配置
        """
        print("\n" + "=" * 60)
        print("欢迎使用 py_ha - Python Harness for AI Agents")
        print("=" * 60)
        print("\n这是一个首次使用引导，帮助你快速上手框架。")
        print("让我们开始配置你的项目...\n")

        # 步骤 1: 项目信息
        print("【步骤 1】项目基础信息")
        print("-" * 40)

        project_name = self._prompt_input(
            "项目名称",
            default="我的项目",
        )

        project_description = self._prompt_input(
            "项目描述（一句话介绍）",
            default="一个使用 py_ha 框架的项目",
        )

        tech_stack = self._prompt_input(
            "技术栈（如: Python + FastAPI）",
            default="Python",
        )

        print("\n[OK] 项目信息已记录\n")

        # 步骤 2: 团队配置
        print("【步骤 2】团队角色配置")
        print("-" * 40)
        print("py_ha 提供以下角色，你可以自定义名称或使用默认值：")
        print("  - product_manager: 产品经理")
        print("  - architect: 架构师")
        print("  - developer: 开发人员")
        print("  - tester: 测试人员")
        print("  - doc_writer: 文档管理员")
        print("  - project_manager: 项目经理")
        print()

        use_default = self._prompt_confirm("使用默认团队配置？", default=True)

        if use_default:
            team_config = {
                "product_manager": "产品经理",
                "architect": "架构师",
                "developer": "开发人员",
                "tester": "测试人员",
                "doc_writer": "文档管理员",
                "project_manager": "项目经理",
            }
        else:
            team_config = {}
            role_defaults = {
                "product_manager": "产品经理",
                "architect": "架构师",
                "developer": "开发人员",
                "tester": "测试人员",
                "doc_writer": "文档管理员",
                "project_manager": "项目经理",
            }
            for role_type, default_name in role_defaults.items():
                name = self._prompt_input(f"{role_type} 名称", default=default_name)
                team_config[role_type] = name

        print("\n[OK] 团队配置完成\n")

        # 创建配置
        config = ProjectConfig(
            project_name=project_name,
            project_description=project_description,
            tech_stack=tech_stack,
            team_config=team_config,
            onboarding_completed=True,
        )

        # 步骤 3: 展示使用方式
        print("【步骤 3】使用方式介绍")
        print("-" * 40)
        print(self.USAGE_GUIDE)

        # 步骤 4: 快速上手示例
        print("\n【步骤 4】快速上手示例")
        print("-" * 40)
        print(self.QUICK_START_EXAMPLES)

        # 步骤 5: 保存配置
        print("\n【步骤 5】保存配置")
        print("-" * 40)

        if self.save_config(config):
            print(f"[OK] 配置已保存到: {self.config_path}")
        else:
            print("[!] 配置保存失败，但你可以继续使用框架")

        # 步骤 6: 初始化 Harness（如果提供了实例）
        if harness_instance:
            print("\n【步骤 6】初始化项目")
            print("-" * 40)

            # 设置项目名称
            harness_instance.project_name = project_name

            # 设置团队
            harness_instance.setup_team(team_config)

            # 保存到记忆
            harness_instance.remember("project_name", project_name, important=True)
            harness_instance.remember("project_description", project_description, important=True)
            harness_instance.remember("tech_stack", tech_stack)

            print("[OK] 项目已初始化")
            print(f"\n项目状态:")
            print(harness_instance.get_report())

        # 完成
        print("\n" + "=" * 60)
        print("引导完成！你现在可以开始使用 py_ha 了")
        print("=" * 60)
        print("\n提示:")
        print("  - 使用 harness.chat('你的需求') 开始对话")
        print("  - 使用 harness.develop('功能描述') 快速开发")
        print("  - 使用 harness.switch_session('角色') 切换对话")
        print("  - 使用 harness.get_status() 查看项目状态")
        print("\n祝你使用愉快！\n")

        return config

    def show_quick_help(self) -> None:
        """
        显示快速帮助信息
        """
        print("\n" + "=" * 50)
        print("py_ha 快速帮助")
        print("=" * 50)
        print("\n核心方法:")
        print("  harness.chat('消息')           - 开始对话")
        print("  harness.develop('功能')        - 快速开发")
        print("  harness.fix_bug('Bug描述')     - 快速修复")
        print("  harness.switch_session('角色') - 切换对话")
        print("  harness.get_status()           - 查看状态")
        print("  harness.remember('key', 'val') - 保存记忆")
        print("\n会话类型:")
        print("  development        - 主开发对话")
        print("  product_manager    - 产品经理对话")
        print("  project_manager    - 项目经理对话")
        print("  architect          - 架构师对话")
        print("  tester             - 测试人员对话")
        print("=" * 50)

    def _prompt_input(self, prompt: str, default: str = "") -> str:
        """
        提示用户输入

        Args:
            prompt: 提示文本
            default: 默认值

        Returns:
            用户输入的值
        """
        default_hint = f" [{default}]" if default else ""
        try:
            user_input = input(f"{prompt}{default_hint}: ").strip()
            if not user_input and default:
                return default
            return user_input
        except (EOFError, KeyboardInterrupt):
            return default

    def _prompt_confirm(self, prompt: str, default: bool = True) -> bool:
        """
        提示用户确认

        Args:
            prompt: 提示文本
            default: 默认值

        Returns:
            用户确认结果
        """
        default_hint = " [Y/n]" if default else " [y/N]"
        try:
            user_input = input(f"{prompt}{default_hint}: ").strip().lower()
            if not user_input:
                return default
            return user_input in ("y", "yes", "是")
        except (EOFError, KeyboardInterrupt):
            return default


def create_guide(config_path: str | None = None) -> OnboardingGuide:
    """
    创建引导系统实例

    Args:
        config_path: 配置文件路径

    Returns:
        OnboardingGuide 实例
    """
    return OnboardingGuide(config_path=config_path)