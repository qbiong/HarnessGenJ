"""
py_ha MCP Server - Harness Engineering Edition

将 py_ha 的角色协作和工作流能力暴露为 MCP Tools

核心能力:
- 角色管理: 创建和管理开发团队角色
- 工作流执行: 驱动开发流程自动执行
- 记忆管理: JVM风格的上下文存储
- 状态追踪: 项目进度和健康监控
"""

import json
import sys
from typing import Any

from py_ha import (
    # Roles
    RoleType,
    Developer,
    Tester,
    ProductManager,
    Architect,
    DocWriter,
    ProjectManager,
    # Workflow
    WorkflowPipeline,
    WorkflowStage,
    WorkflowCoordinator,
    WorkflowContext,
    create_standard_pipeline,
    create_feature_pipeline,
    create_bugfix_pipeline,
    # Memory
    MemoryManager,
    # Storage
    create_storage,
    # Session
    SessionManager,
    SessionType,
    MessageRole,
)


class PyHAMCPServer:
    """
    py_ha MCP Server - Harness Engineering Edition

    提供:
    - 角色管理工具: 创建开发团队
    - 工作流工具: 启动和管理开发流程
    - 记忆工具: 上下文管理
    - 状态工具: 进度追踪
    """

    def __init__(self, name: str = "py_ha") -> None:
        self.name = name
        self.version = "0.2.0"

        # 初始化核心组件
        self.coordinator = WorkflowCoordinator()
        self.memory = MemoryManager()
        self.storage = create_storage()
        self.sessions = SessionManager()  # 多会话管理

        # 注册标准工作流
        self.coordinator.register_workflow("standard", create_standard_pipeline())
        self.coordinator.register_workflow("feature", create_feature_pipeline())
        self.coordinator.register_workflow("bugfix", create_bugfix_pipeline())

        # 默认团队
        self._setup_default_team()

        # MCP Tools
        self._tools = self._define_tools()

    def _setup_default_team(self) -> None:
        """设置默认开发团队"""
        self.coordinator.create_role(RoleType.PRODUCT_MANAGER, "pm_1", "产品经理")
        self.coordinator.create_role(RoleType.ARCHITECT, "arch_1", "架构师")
        self.coordinator.create_role(RoleType.DEVELOPER, "dev_1", "开发人员")
        self.coordinator.create_role(RoleType.TESTER, "test_1", "测试人员")
        self.coordinator.create_role(RoleType.DOC_WRITER, "doc_1", "文档管理员")
        self.coordinator.create_role(RoleType.PROJECT_MANAGER, "mgr_1", "项目经理")

    def _define_tools(self) -> list[dict[str, Any]]:
        """定义 MCP Tools"""
        return [
            # ==================== 角色管理 ====================
            {
                "name": "team_list",
                "description": "列出当前开发团队所有角色",
                "inputSchema": {"type": "object", "properties": {}, "required": []},
            },
            {
                "name": "team_add_role",
                "description": "添加新角色到团队。可选: developer, tester, product_manager, architect, doc_writer, project_manager",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "role_type": {"type": "string", "description": "角色类型"},
                        "name": {"type": "string", "description": "角色名称"},
                    },
                    "required": ["role_type"],
                },
            },
            {
                "name": "role_get_skills",
                "description": "获取指定角色的技能列表",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "role_id": {"type": "string", "description": "角色ID"},
                    },
                    "required": ["role_id"],
                },
            },
            {
                "name": "role_assign_task",
                "description": "向指定角色分配任务",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "role_id": {"type": "string", "description": "角色ID"},
                        "task_type": {"type": "string", "description": "任务类型"},
                        "description": {"type": "string", "description": "任务描述"},
                    },
                    "required": ["role_id", "task_type"],
                },
            },
            {
                "name": "role_execute",
                "description": "执行角色当前任务",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "role_id": {"type": "string", "description": "角色ID"},
                    },
                    "required": ["role_id"],
                },
            },
            # ==================== 工作流管理 ====================
            {
                "name": "workflow_list",
                "description": "列出可用的工作流模板",
                "inputSchema": {"type": "object", "properties": {}, "required": []},
            },
            {
                "name": "workflow_start",
                "description": "启动工作流。standard=完整流程, feature=功能开发, bugfix=Bug修复",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workflow_type": {"type": "string", "description": "工作流类型", "default": "feature"},
                        "project_name": {"type": "string", "description": "项目名称"},
                        "initial_request": {"type": "string", "description": "初始需求"},
                    },
                    "required": ["initial_request"],
                },
            },
            {
                "name": "workflow_status",
                "description": "查询工作流执行状态",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workflow_id": {"type": "string", "description": "工作流ID"},
                    },
                    "required": ["workflow_id"],
                },
            },
            {
                "name": "workflow_run_stage",
                "description": "执行工作流的指定阶段",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workflow_id": {"type": "string", "description": "工作流ID"},
                        "stage_name": {"type": "string", "description": "阶段名称"},
                    },
                    "required": ["workflow_id", "stage_name"],
                },
            },
            {
                "name": "workflow_run_all",
                "description": "运行完整工作流（自动执行所有阶段）",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workflow_id": {"type": "string", "description": "工作流ID"},
                    },
                    "required": ["workflow_id"],
                },
            },
            # ==================== 快速开发 ====================
            {
                "name": "quick_feature",
                "description": "快速功能开发：需求→开发→测试 一键完成",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "feature_request": {"type": "string", "description": "功能需求描述"},
                    },
                    "required": ["feature_request"],
                },
            },
            {
                "name": "quick_bugfix",
                "description": "快速Bug修复：分析→修复→验证 一键完成",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "bug_description": {"type": "string", "description": "Bug描述"},
                    },
                    "required": ["bug_description"],
                },
            },
            # ==================== 记忆与存储 ====================
            {
                "name": "memory_save",
                "description": "保存重要上下文到记忆系统",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "键名"},
                        "content": {"type": "string", "description": "内容"},
                        "importance": {"type": "integer", "description": "重要性(0-100)", "default": 50},
                    },
                    "required": ["key", "content"],
                },
            },
            {
                "name": "memory_recall",
                "description": "从记忆系统召回上下文",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "键名"},
                    },
                    "required": ["key"],
                },
            },
            # ==================== 状态监控 ====================
            {
                "name": "system_status",
                "description": "获取系统整体状态",
                "inputSchema": {"type": "object", "properties": {}, "required": []},
            },
            {
                "name": "project_summary",
                "description": "获取项目执行摘要",
                "inputSchema": {"type": "object", "properties": {}, "required": []},
            },
            # ==================== 多会话管理 ====================
            {
                "name": "session_switch",
                "description": "切换对话会话。可切换到: development(主开发), product_manager(产品经理), project_manager(项目经理), architect(架构师), tester(测试)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "session_type": {"type": "string", "description": "会话类型"},
                    },
                    "required": ["session_type"],
                },
            },
            {
                "name": "session_chat",
                "description": "在当前会话中发送消息。不同会话的消息历史相互独立。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "消息内容"},
                    },
                    "required": ["message"],
                },
            },
            {
                "name": "session_list",
                "description": "列出所有对话会话",
                "inputSchema": {"type": "object", "properties": {}, "required": []},
            },
            {
                "name": "session_history",
                "description": "获取当前会话的对话历史",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "description": "消息数量限制", "default": 20},
                    },
                    "required": [],
                },
            },
            {
                "name": "session_report",
                "description": "获取所有会话的报告",
                "inputSchema": {"type": "object", "properties": {}, "required": []},
            },
        ]

    def get_tools(self) -> list[dict[str, Any]]:
        return self._tools

    def handle_tool_call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            result = self._execute_tool(name, arguments)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """执行工具"""

        # ==================== 角色管理 ====================
        if name == "team_list":
            roles = self.coordinator.list_roles()
            return {
                "team_size": len(roles),
                "members": [
                    {"id": r["role_id"], "name": r["name"], "type": r["role_type"], "skills": r["skills"]}
                    for r in roles
                ],
            }

        if name == "team_add_role":
            role_type_map = {
                "developer": RoleType.DEVELOPER,
                "tester": RoleType.TESTER,
                "product_manager": RoleType.PRODUCT_MANAGER,
                "architect": RoleType.ARCHITECT,
                "doc_writer": RoleType.DOC_WRITER,
                "project_manager": RoleType.PROJECT_MANAGER,
            }
            role_type_str = arguments["role_type"].lower()
            role_type = role_type_map.get(role_type_str)
            if not role_type:
                return {"error": f"Unknown role type: {role_type_str}"}

            import uuid
            role_id = f"{role_type_str}_{uuid.uuid4().hex[:6]}"
            name_arg = arguments.get("name", role_type_str)
            role = self.coordinator.create_role(role_type, role_id, name_arg)
            return {"created": True, "role_id": role_id, "type": role_type_str}

        if name == "role_get_skills":
            role_id = arguments["role_id"]
            role = self.coordinator.get_role(role_id)
            if role:
                return {"role_id": role_id, "skills": [s.model_dump() for s in role.list_skills()]}
            return {"error": "Role not found"}

        if name == "role_assign_task":
            role_id = arguments["role_id"]
            task_type = arguments["task_type"]
            description = arguments.get("description", "")

            role = self.coordinator.get_role(role_id)
            if not role:
                return {"error": "Role not found"}

            task = {"type": task_type, "description": description, "inputs": {}}
            success = role.assign_task(task)
            return {"assigned": success, "role_id": role_id, "task_type": task_type}

        if name == "role_execute":
            role_id = arguments["role_id"]
            role = self.coordinator.get_role(role_id)
            if not role:
                return {"error": "Role not found"}
            result = role.execute_task()
            return {"role_id": role_id, "result": result}

        # ==================== 工作流管理 ====================
        if name == "workflow_list":
            return {
                "workflows": [
                    {"id": "standard", "name": "标准开发流程", "stages": ["需求", "设计", "开发", "测试", "文档", "发布"]},
                    {"id": "feature", "name": "功能开发流程", "stages": ["需求", "开发", "测试"]},
                    {"id": "bugfix", "name": "Bug修复流程", "stages": ["分析", "修复", "验证"]},
                ],
            }

        if name == "workflow_start":
            workflow_type = arguments.get("workflow_type", "feature")
            project_name = arguments.get("project_name", "项目")
            initial_request = arguments["initial_request"]

            result = self.coordinator.start_workflow(
                workflow_type,
                {"user_request": initial_request, "project_name": project_name},
            )
            return result

        if name == "workflow_status":
            workflow_id = arguments["workflow_id"]
            status = self.coordinator.get_workflow_status(workflow_id)
            return status or {"error": "Workflow not found"}

        if name == "workflow_run_stage":
            workflow_id = arguments["workflow_id"]
            stage_name = arguments["stage_name"]
            return self.coordinator.execute_stage(workflow_id, stage_name)

        if name == "workflow_run_all":
            workflow_id = arguments["workflow_id"]
            pipeline = self.coordinator.get_workflow(workflow_id)
            if not pipeline:
                return {"error": "Workflow not found"}

            results = []
            while True:
                ready = pipeline.get_ready_stages()
                if not ready:
                    break
                for stage in ready:
                    r = self.coordinator.execute_stage(workflow_id, stage.name)
                    results.append(r)

            return {"completed": True, "results": results}

        # ==================== 快速开发 ====================
        if name == "quick_feature":
            feature_request = arguments["feature_request"]

            # 启动功能开发流程
            start_result = self.coordinator.start_workflow(
                "feature",
                {"feature_request": feature_request},
            )

            workflow_id = start_result.get("workflow_id", "feature")
            if start_result["status"] != "started":
                return start_result

            # 自动运行
            run_result = self.coordinator.run_workflow("feature", {"feature_request": feature_request})
            return {
                "status": "completed",
                "request": feature_request,
                "pipeline_result": run_result,
            }

        if name == "quick_bugfix":
            bug_description = arguments["bug_description"]

            run_result = self.coordinator.run_workflow("bugfix", {"bug_report": bug_description})
            return {
                "status": "completed",
                "bug": bug_description,
                "fix_result": run_result,
            }

        # ==================== 记忆与存储 ====================
        if name == "memory_save":
            key = arguments["key"]
            content = arguments["content"]
            importance = arguments.get("importance", 50)

            if importance >= 80:
                self.memory.store_important_knowledge(key, content)
            else:
                self.memory.store_conversation(content, importance=importance)

            return {"saved": True, "key": key, "importance": importance}

        if name == "memory_recall":
            key = arguments["key"]
            content = self.memory.get_knowledge(key)
            if content is None:
                content = self.storage.load(key)
            return {"key": key, "content": content, "found": content is not None}

        # ==================== 状态监控 ====================
        if name == "system_status":
            return {
                "version": self.version,
                "team": {"size": len(self.coordinator.list_roles())},
                "workflows": self.coordinator.get_stats().model_dump(),
                "memory": {"status": self.memory.get_health_report()["status"]},
            }

        if name == "project_summary":
            stats = self.coordinator.get_stats()
            return {
                "workflows_started": stats.workflows_started,
                "workflows_completed": stats.workflows_completed,
                "stages_executed": stats.stages_executed,
                "team_members": len(self.coordinator.list_roles()),
            }

        # ==================== 多会话管理 ====================
        if name == "session_switch":
            session_type_str = arguments["session_type"].lower()
            type_map = {
                "development": SessionType.DEVELOPMENT,
                "product_manager": SessionType.PRODUCT_MANAGER,
                "project_manager": SessionType.PROJECT_MANAGER,
                "architect": SessionType.ARCHITECT,
                "tester": SessionType.TESTER,
                "doc_writer": SessionType.DOC_WRITER,
                "general": SessionType.GENERAL,
            }
            st = type_map.get(session_type_str)
            if not st:
                return {"switched": False, "error": f"Unknown session type: {session_type_str}"}

            session = self.sessions.switch_session(st)
            return {
                "switched": True,
                "session": session.get_summary() if session else None,
            }

        if name == "session_chat":
            message = arguments["message"]
            msg = self.sessions.chat(message, MessageRole.USER)
            return {
                "message_id": msg.id if msg else None,
                "session_id": self.sessions._active_session_id,
                "sent": msg is not None,
            }

        if name == "session_list":
            return {"sessions": self.sessions.list_sessions()}

        if name == "session_history":
            limit = arguments.get("limit", 20)
            messages = self.sessions.get_conversation_history(limit=limit)
            return {
                "messages": [
                    {
                        "id": msg.id,
                        "role": msg.role.value,
                        "content": msg.content,
                        "timestamp": msg.timestamp,
                    }
                    for msg in messages
                ],
                "count": len(messages),
            }

        if name == "session_report":
            sessions = self.sessions.list_sessions()
            report_lines = ["# 会话报告\n", "## 所有会话\n"]
            for session in sessions:
                active_mark = " (当前)" if session.get("is_active") else ""
                report_lines.append(f"### {session['name']}{active_mark}")
                report_lines.append(f"- 类型: {session['type']}")
                report_lines.append(f"- 消息数: {session['message_count']}")
                report_lines.append("")
            return {"report": "\n".join(report_lines)}

        raise ValueError(f"Unknown tool: {name}")

    # ==================== MCP Protocol ====================

    def run_stdio(self) -> None:
        """STDIO 方式运行"""
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break

                request = json.loads(line)
                response = self._handle_mcp_request(request)
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()

            except json.JSONDecodeError:
                sys.stdout.write(json.dumps({"error": "Invalid JSON"}) + "\n")
                sys.stdout.flush()
            except Exception as e:
                sys.stdout.write(json.dumps({"error": str(e)}) + "\n")
                sys.stdout.flush()

    def _handle_mcp_request(self, request: dict[str, Any]) -> dict[str, Any]:
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": self.name, "version": self.version},
                },
            }

        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"tools": self._tools},
            }

        if method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            result = self.handle_tool_call(tool_name, tool_args)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]},
            }

        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}


def create_mcp_server(name: str = "py_ha") -> PyHAMCPServer:
    return PyHAMCPServer(name=name)


def main() -> None:
    server = create_mcp_server()
    server.run_stdio()


if __name__ == "__main__":
    main()