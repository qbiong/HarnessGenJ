"""
Tech Stack Detector - 技术栈自动检测系统

根据项目文件自动检测技术栈，并生成适配的 agents/*.md 模板。

支持的检测类型:
- Python (pip/poetry/uv)
- Java/Android (Gradle/Maven)
- Node.js/TypeScript (npm/yarn/pnpm)
- Go
- Rust
- Flutter/Dart
- React/Vue/Angular
- FastAPI/Django/Flask
- Spring Boot

使用示例:
    from harnessgenj.harness.tech_detector import detect_tech_stack

    tech_info = detect_tech_stack("/path/to/project")
    print(tech_info.main_language)
    print(tech_info.frameworks)
"""

import os
import re
import json
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field
from harnessgenj.utils.exception_handler import log_exception


class TechStackInfo(BaseModel):
    """技术栈信息"""

    main_language: str = Field(default="Unknown", description="主要语言")
    frameworks: list[str] = Field(default_factory=list, description="框架列表")
    build_tools: list[str] = Field(default_factory=list, description="构建工具")
    package_managers: list[str] = Field(default_factory=list, description="包管理器")
    databases: list[str] = Field(default_factory=list, description="数据库")
    testing_frameworks: list[str] = Field(default_factory=list, description="测试框架")
    deployment: list[str] = Field(default_factory=list, description="部署方式")
    platforms: list[str] = Field(default_factory=list, description="平台")
    version_info: dict[str, str] = Field(default_factory=dict, description="版本信息")
    confidence: float = Field(default=0.0, description="检测置信度 (0-1)")

    # 语言特定信息
    java_version: str | None = Field(default=None, description="Java 版本")
    kotlin_version: str | None = Field(default=None, description="Kotlin 版本")
    python_version: str | None = Field(default=None, description="Python 版本")
    node_version: str | None = Field(default=None, description="Node.js 版本")

    # Android 特定信息
    android_sdk_version: str | None = Field(default=None, description="Android SDK 版本")
    min_sdk_version: str | None = Field(default=None, description="Android minSdkVersion")
    target_sdk_version: str | None = Field(default=None, description="Android targetSdkVersion")


# 技术栈检测指示器
TECH_INDICATORS = {
    # 文件指示器
    "files": {
        "Python": [
            "requirements.txt", "setup.py", "pyproject.toml", "setup.cfg",
            "Pipfile", "poetry.lock", "uv.lock", ".python-version",
        ],
        "Java": [
            "pom.xml", "build.gradle", "build.gradle.kts", "gradlew", "gradlew.bat",
            "gradle.properties", "settings.gradle", "settings.gradle.kts",
        ],
        "Kotlin": [
            "*.kt", "*.kts", "build.gradle.kts",
        ],
        "Android": [
            "AndroidManifest.xml", "gradle/wrapper", "app/build.gradle",
            "app/src/main/res", "local.properties",
        ],
        "Node.js": [
            "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
            ".npmrc", ".yarnrc", "node_modules",
        ],
        "TypeScript": [
            "tsconfig.json", "tsconfig.*.json", "*.ts", "*.tsx",
        ],
        "Go": [
            "go.mod", "go.sum", "*.go", "Gopkg.toml", "Gopkg.lock",
        ],
        "Rust": [
            "Cargo.toml", "Cargo.lock", "*.rs", ".rustfmt.toml",
        ],
        "Flutter": [
            "pubspec.yaml", "pubspec.lock", "*.dart", ".flutter-plugins",
        ],
        "React": [
            "package.json", "src/**/*.jsx", "src/**/*.tsx",
        ],
        "Vue": [
            "package.json", "vite.config.*", "vue.config.*", "*.vue",
        ],
        "Angular": [
            "angular.json", "package.json", "*.component.ts", "ng-package.json",
        ],
    },

    # 内容关键词指示器
    "keywords": {
        "FastAPI": ["fastapi", "FastAPI", "from fastapi"],
        "Django": ["django", "Django", "from django"],
        "Flask": ["flask", "Flask", "from flask"],
        "Spring Boot": ["spring-boot", "SpringBootApplication", "@SpringBootApplication"],
        "Spring MVC": ["spring-mvc", "@Controller", "@RequestMapping"],
        "Ktor": ["ktor", "io.ktor"],
        "Express": ["express", "Express"],
        "NestJS": ["nestjs", "@nestjs"],
        "React": ["react", "React", "from react"],
        "Vue": ["vue", "Vue", "createApp"],
        "AndroidX": ["androidx", "AndroidX"],
        "Jetpack Compose": ["compose", "Jetpack Compose", "androidx.compose"],
        "Material Design": ["material", "Material Design", "com.google.android.material"],
        "JUnit": ["junit", "JUnit", "@Test"],
        "pytest": ["pytest", "@pytest", "test_"],
        "Mockito": ["mockito", "Mockito", "@Mock"],
        "Docker": ["docker", "Dockerfile", "docker-compose"],
        "Kubernetes": ["kubernetes", "k8s", "kubectl"],
    },

    # 数据库指示器
    "databases": {
        "PostgreSQL": ["postgresql", "postgres", "pg"],
        "MySQL": ["mysql", "MySQL"],
        "MongoDB": ["mongodb", "mongo", "mongoose"],
        "Redis": ["redis", "Redis"],
        "SQLite": ["sqlite", "SQLite"],
        "Room": ["room", "RoomDatabase", "@Entity"],
    },
}


def detect_tech_stack(project_path: str | Path) -> TechStackInfo:
    """
    检测项目技术栈

    Args:
        project_path: 项目根目录路径

    Returns:
        TechStackInfo: 技术栈信息
    """
    if isinstance(project_path, str):
        project_path = Path(project_path)

    info = TechStackInfo()
    detected_languages: dict[str, float] = {}
    detected_frameworks: list[str] = []
    detected_build_tools: list[str] = []
    detected_package_managers: list[str] = []
    detected_databases: list[str] = []
    detected_testing: list[str] = []
    detected_deployment: list[str] = []
    detected_platforms: list[str] = []

    # 1. 文件检测
    for language, indicators in TECH_INDICATORS["files"].items():
        match_count = 0
        for indicator in indicators:
            # 处理 glob 模式
            if "*" in indicator:
                matches = list(project_path.glob(indicator))
                if matches:
                    match_count += len(matches)
            else:
                if (project_path / indicator).exists():
                    match_count += 1

        if match_count > 0:
            # 根据匹配数量计算权重
            weight = min(match_count / 3, 1.0)  # 至少3个匹配才算高置信度
            detected_languages[language] = max(detected_languages.get(language, 0), weight)

    # 2. 文件内容分析（读取关键配置文件）
    content_keywords = _extract_keywords_from_files(project_path)

    for framework, keywords in TECH_INDICATORS["keywords"].items():
        for kw in keywords:
            if kw in content_keywords:
                detected_frameworks.append(framework)
                break

    for db, keywords in TECH_INDICATORS["databases"].items():
        for kw in keywords:
            if kw in content_keywords:
                detected_databases.append(db)
                break

    # 3. 解析配置文件获取版本信息
    version_info = _extract_version_info(project_path)
    info.version_info = version_info

    # 4. 确定 main_language
    language_priority = ["Java", "Kotlin", "Python", "TypeScript", "JavaScript", "Go", "Rust", "Dart"]
    for lang in language_priority:
        if detected_languages.get(lang, 0) > 0.3:
            info.main_language = lang
            break

    if info.main_language == "Unknown" and detected_languages:
        # 选择置信度最高的
        info.main_language = max(detected_languages.keys(), key=lambda k: detected_languages[k])

    # 5. 平台检测
    if "Android" in detected_languages or any(
        (project_path / f).exists() for f in ["AndroidManifest.xml", "app/build.gradle"]
    ):
        detected_platforms.append("Android")
        info.main_language = "Java/Android" if "Java" in detected_languages else "Kotlin/Android"

    if any(f.endswith(".dart") for f in os.listdir(project_path) if os.path.isfile(project_path / f)):
        if (project_path / "pubspec.yaml").exists():
            detected_platforms.append("Flutter")
            info.main_language = "Flutter/Dart"

    if "package.json" in content_keywords and "React" in detected_frameworks:
        detected_platforms.append("Web")

    # 6. 包管理器和构建工具
    if (project_path / "gradlew").exists() or (project_path / "build.gradle").exists():
        detected_build_tools.append("Gradle")
        detected_package_managers.append("Gradle")

    if (project_path / "pom.xml").exists():
        detected_build_tools.append("Maven")
        detected_package_managers.append("Maven")

    if (project_path / "requirements.txt").exists():
        detected_package_managers.append("pip")

    if (project_path / "pyproject.toml").exists():
        detected_package_managers.append("poetry")

    if (project_path / "package.json").exists():
        if (project_path / "yarn.lock").exists():
            detected_package_managers.append("yarn")
        elif (project_path / "pnpm-lock.yaml").exists():
            detected_package_managers.append("pnpm")
        else:
            detected_package_managers.append("npm")

    # 7. 测试框架
    if "pytest" in content_keywords or any(
        kw in content_keywords for kw in ["test_", "pytest"]
    ):
        detected_testing.append("pytest")

    if "JUnit" in detected_frameworks or "junit" in content_keywords:
        detected_testing.append("JUnit")

    if "Mockito" in detected_frameworks or "mockito" in content_keywords:
        detected_testing.append("Mockito")

    # 8. 部署方式
    if (project_path / "Dockerfile").exists():
        detected_deployment.append("Docker")

    if (project_path / "docker-compose.yml").exists() or (project_path / "docker-compose.yaml").exists():
        detected_deployment.append("Docker Compose")

    # 9. Android 特定版本
    if "Android" in detected_platforms:
        android_info = _extract_android_info(project_path)
        info.android_sdk_version = android_info.get("compileSdk")
        info.min_sdk_version = android_info.get("minSdk")
        info.target_sdk_version = android_info.get("targetSdk")
        info.java_version = android_info.get("javaVersion")

    # 10. 设置结果
    info.frameworks = list(set(detected_frameworks))
    info.build_tools = list(set(detected_build_tools))
    info.package_managers = list(set(detected_package_managers))
    info.databases = list(set(detected_databases))
    info.testing_frameworks = list(set(detected_testing))
    info.deployment = list(set(detected_deployment))
    info.platforms = list(set(detected_platforms))

    # 计算置信度
    total_indicators = len(detected_languages) + len(detected_frameworks)
    info.confidence = min(total_indicators / 10, 1.0)

    return info


def _extract_keywords_from_files(project_path: Path) -> str:
    """
    从项目文件提取关键词

    Args:
        project_path: 项目根目录

    Returns:
        合并后的关键词字符串
    """
    keywords: list[str] = []

    # 读取的关键配置文件
    key_files = [
        "README.md", "readme.md",
        "pyproject.toml", "requirements.txt", "setup.py",
        "build.gradle", "build.gradle.kts", "pom.xml",
        "package.json",
        "go.mod",
        "Cargo.toml",
        "pubspec.yaml",
    ]

    for file_name in key_files:
        file_path = project_path / file_name
        if file_path.exists():
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                keywords.append(content)
            except Exception as e:
                log_exception(e, context=f"_collect_keywords {file_name}", level=30)

    # 读取 AndroidManifest.xml
    manifest_path = project_path / "app" / "src" / "main" / "AndroidManifest.xml"
    if manifest_path.exists():
        try:
            content = manifest_path.read_text(encoding="utf-8", errors="ignore")
            keywords.append(content)
        except Exception as e:
            log_exception(e, context="_collect_keywords AndroidManifest", level=30)

    return " ".join(keywords)


def _extract_version_info(project_path: Path) -> dict[str, str]:
    """
    从配置文件提取版本信息

    Args:
        project_path: 项目根目录

    Returns:
        版本信息字典
    """
    versions: dict[str, str] = {}

    # Python 版本
    pyproject = project_path / "pyproject.toml"
    if pyproject.exists():
        try:
            content = pyproject.read_text(encoding="utf-8")
            # 提取 requires-python
            match = re.search(r'requires-python\s*=\s*"([^"]+)"', content)
            if match:
                versions["python"] = match.group(1)
        except Exception as e:
            log_exception(e, context="_extract_version_info pyproject.toml", level=30)

    # Java 版本（从 build.gradle）
    build_gradle = project_path / "build.gradle"
    if build_gradle.exists():
        try:
            content = build_gradle.read_text(encoding="utf-8")
            match = re.search(r'sourceCompatibility\s*=\s*[\'"]?([^\'"\s]+)', content)
            if match:
                versions["java"] = match.group(1)
        except Exception as e:
            log_exception(e, context="_extract_version_info build.gradle", level=30)

    # Node.js 版本（从 package.json）
    package_json = project_path / "package.json"
    if package_json.exists():
        try:
            with open(package_json, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "engines" in data and "node" in data["engines"]:
                    versions["node"] = data["engines"]["node"]
        except Exception as e:
            log_exception(e, context="_extract_version_info package.json", level=30)

    # Go 版本（从 go.mod）
    go_mod = project_path / "go.mod"
    if go_mod.exists():
        try:
            content = go_mod.read_text(encoding="utf-8")
            match = re.search(r'go\s+(\d+\.\d+)', content)
            if match:
                versions["go"] = match.group(1)
        except Exception as e:
            log_exception(e, context="_extract_version_info go.mod", level=30)

    return versions


def _extract_android_info(project_path: Path) -> dict[str, str]:
    """
    从 Android 项目提取版本信息

    Args:
        project_path: 项目根目录

    Returns:
        Android 版本信息
    """
    info: dict[str, str] = {}

    # 读取 app/build.gradle
    build_gradle = project_path / "app" / "build.gradle"
    if build_gradle.exists():
        try:
            content = build_gradle.read_text(encoding="utf-8")

            # 提取 SDK 版本
            compile_sdk_match = re.search(r'compileSdk\s*[=:]\s*(\d+)', content)
            if compile_sdk_match:
                info["compileSdk"] = compile_sdk_match.group(1)

            min_sdk_match = re.search(r'minSdk\s*[=:]\s*(\d+)', content)
            if min_sdk_match:
                info["minSdk"] = min_sdk_match.group(1)

            target_sdk_match = re.search(r'targetSdk\s*[=:]\s*(\d+)', content)
            if target_sdk_match:
                info["targetSdk"] = target_sdk_match.group(1)

            # Java 版本
            java_match = re.search(r'sourceCompatibility\s*[=:]\s*[\'"]?([^\'"\s]+)', content)
            if java_match:
                info["javaVersion"] = java_match.group(1)

        except Exception as e:
            log_exception(e, context="_extract_android_info build.gradle", level=30)

    # 读取 build.gradle.kts
    build_gradle_kts = project_path / "app" / "build.gradle.kts"
    if build_gradle_kts.exists() and not info:
        try:
            content = build_gradle_kts.read_text(encoding="utf-8")

            compile_sdk_match = re.search(r'compileSdk\s*=\s*(\d+)', content)
            if compile_sdk_match:
                info["compileSdk"] = compile_sdk_match.group(1)

            min_sdk_match = re.search(r'minSdk\s*=\s*(\d+)', content)
            if min_sdk_match:
                info["minSdk"] = min_sdk_match.group(1)

            target_sdk_match = re.search(r'targetSdk\s*=\s*(\d+)', content)
            if target_sdk_match:
                info["targetSdk"] = target_sdk_match.group(1)

        except Exception as e:
            log_exception(e, context="_extract_android_info build.gradle.kts", level=30)

    return info


def generate_tech_md_content(tech_info: TechStackInfo) -> str:
    """
    根据技术栈信息生成 tech.md 内容

    Args:
        tech_info: 技术栈信息

    Returns:
        tech.md 内容
    """
    content = f"""# 技术栈

> 此文件由 HarnessGenJ 自动生成，根据项目文件自动检测
> 检测置信度: {tech_info.confidence:.0%}

## 主要技术

- **语言**: {tech_info.main_language}
"""

    if tech_info.frameworks:
        content += f"- **框架**: {', '.join(tech_info.frameworks)}\n"

    if tech_info.build_tools:
        content += f"- **构建工具**: {', '.join(tech_info.build_tools)}\n"

    if tech_info.package_managers:
        content += f"- **包管理器**: {', '.join(tech_info.package_managers)}\n"

    if tech_info.platforms:
        content += f"- **平台**: {', '.join(tech_info.platforms)}\n"

    # 版本信息
    if tech_info.version_info:
        content += "\n## 版本要求\n\n"
        for name, version in tech_info.version_info.items():
            content += f"- **{name}**: {version}\n"

    # Android 特定信息
    if tech_info.platforms and "Android" in tech_info.platforms:
        content += "\n## Android 配置\n\n"
        if tech_info.android_sdk_version:
            content += f"- **compileSdk**: {tech_info.android_sdk_version}\n"
        if tech_info.min_sdk_version:
            content += f"- **minSdk**: {tech_info.min_sdk_version}\n"
        if tech_info.target_sdk_version:
            content += f"- **targetSdk**: {tech_info.target_sdk_version}\n"
        if tech_info.java_version:
            content += f"- **Java 版本**: {tech_info.java_version}\n"

    # 数据库
    if tech_info.databases:
        content += "\n## 数据库\n\n"
        for db in tech_info.databases:
            content += f"- {db}\n"

    # 测试框架
    if tech_info.testing_frameworks:
        content += "\n## 测试框架\n\n"
        for test in tech_info.testing_frameworks:
            content += f"- {test}\n"

    # 部署方式
    if tech_info.deployment:
        content += "\n## 部署方式\n\n"
        for deploy in tech_info.deployment:
            content += f"- {deploy}\n"

    return content


def generate_conventions_md_content(tech_info: TechStackInfo) -> str:
    """
    根据技术栈信息生成 conventions.md 内容

    Args:
        tech_info: 技术栈信息

    Returns:
        conventions.md 内容
    """
    content = """# 代码约定

> 此文件由 HarnessGenJ 自动生成，根据技术栈自动适配
> 请遵循项目既有的代码风格

"""

    # 根据语言选择编码规范
    language = tech_info.main_language

    if "Java" in language or "Kotlin" in language or "Android" in tech_info.platforms:
        content += """## 编码风格

- 遵循 Java/Kotlin 官方命名规范
- 类名使用 PascalCase，方法名使用 camelCase
- 常量使用 UPPER_SNAKE_CASE
- 包名使用小写，多级包名用点分隔

## Android 特定约定

- Activity/Fragment 呋名应体现功能（如 `MainActivity`、`LoginFragment`）
- 布局文件使用 `activity_*.xml` 或 `fragment_*.xml` 格式
- 资源文件使用小写和下划线（如 `ic_launcher.png`）
- 使用 Material Design 组件优先

## 代码组织

- 使用 MVVM 或 Clean Architecture 架构模式
- 业务逻辑放在 ViewModel 或 UseCase 中
- UI 层只处理视图逻辑
- 使用依赖注入（Hilt/Koin）管理依赖

## 文档

- 公开 API 必须有 KDoc/Javadoc 文档注释
- 复杂逻辑需要内联注释说明
- README 应包含项目介绍和快速上手指南

## 异常处理

- 使用 try-catch 捕获可预见的异常
- 避免空的 catch 块
- 使用日志记录异常信息（Log.e）
"""

    elif language == "Python":
        content += """## 编码风格

- 遵循 PEP 8 规范
- 使用类型注解（Type Hints）
- 函数名使用 snake_case
- 类名使用 PascalCase
- 常量使用 UPPER_SNAKE_CASE

## 代码组织

- 使用模块化设计
- 每个 module 应有明确的职责
- 使用 `__init__.py` 导出公共 API

## 文档

- 函数必须有文档字符串（docstring）
- 使用 Google 或 NumPy 风格的 docstring
- 复杂逻辑需要注释说明

## 类型检查

- 推荐使用 mypy 进行静态类型检查
- 使用 `typing` 模块的泛型类型
"""

    elif "TypeScript" in language or "JavaScript" in language:
        content += """## 编码风格

- 遵循项目配置的 ESLint 规则
- 使用 TypeScript 优先（如果项目支持）
- 变量名使用 camelCase
- 类名使用 PascalCase
- 常量使用 UPPER_SNAKE_CASE 或 camelCase

## 代码组织

- 使用 ES Modules
- 每个 file 应有明确的职责
- 避免循环依赖

## 文档

- 公开 API 必须有 JSDoc/TSDoc 注释
- 复杂逻辑需要注释说明
"""

    elif language == "Go":
        content += """## 编码风格

- 遵循 Go 官方编码规范
- 使用 gofmt 格式化代码
- 使用 golangci-lint 检查代码质量
- 接口名使用动词或形容词（如 Reader、Writer）

## 代码组织

- 每个包应有明确的职责
- 使用 internal 包存放内部实现
- 使用 cmd 包存放命令行工具

## 文档

- 公开函数必须有 godoc 注释
- 注释应以函数名开头
"""

    elif language == "Rust":
        content += """## 编码风格

- 遵循 Rust 官方编码规范
- 使用 rustfmt 格式化代码
- 使用 clippy 检查代码质量
- 变量名使用 snake_case
- 类型名使用 PascalCase

## 代码组织

- 每个 module 应有明确的职责
- 使用 `pub` 控制可见性
- 优先使用 `Result` 和 `Option` 处理错误

## 文档

- 公开 API 必须有文档注释（///）
- 使用 rustdoc 生成文档
"""

    elif "Flutter" in language or "Dart" in language:
        content += """## 编码风格

- 遵循 Dart 官方编码规范
- 使用 dartfmt 格式化代码
- 变量名使用 camelCase
- 类名使用 PascalCase
- 常量使用 lowerCamelCase（Dart 风格）

## Flutter 特定约定

- Widget 命名使用 PascalCase
- 私有成员使用下划线前缀（_）
- 使用 const 构造器优化性能
"""

    else:
        # 通用规范
        content += """## 编码风格

- 遵循项目既有的代码风格
- 保持代码整洁和一致性
- 使用有意义的命名

## 文档

- 公开 API 必须有文档注释
- 复杂逻辑需要注释说明
"""

    # 添加测试约定
    content += """
## 测试约定

- 所有新功能需要添加测试
- 测试文件放在 `test/` 或 `tests/` 目录
- 测试函数名应描述测试场景
- 使用 AAA 模式（Arrange-Act-Assert）
"""

    if tech_info.testing_frameworks:
        content += f"\n推荐使用: {', '.join(tech_info.testing_frameworks)}\n"

    return content


def update_agents_templates(
    workspace: str | Path,
    tech_info: TechStackInfo,
) -> dict[str, Any]:
    """
    更新 agents/*.md 模板以适配技术栈

    Args:
        workspace: 工作空间目录
        tech_info: 技术栈信息

    Returns:
        更新结果
    """
    if isinstance(workspace, str):
        workspace = Path(workspace)

    agents_dir = workspace / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "updated": [],
        "skipped": [],
        "errors": [],
    }

    # 更新 tech.md
    tech_md_path = agents_dir / "tech.md"
    try:
        tech_content = generate_tech_md_content(tech_info)
        tech_md_path.write_text(tech_content, encoding="utf-8")
        result["updated"].append("agents/tech.md")
    except Exception as e:
        result["errors"].append(f"tech.md: {str(e)}")

    # 更新 conventions.md
    conventions_md_path = agents_dir / "conventions.md"
    try:
        conventions_content = generate_conventions_md_content(tech_info)
        conventions_md_path.write_text(conventions_content, encoding="utf-8")
        result["updated"].append("agents/conventions.md")
    except Exception as e:
        result["errors"].append(f"conventions.md: {str(e)}")

    return result