"""
MCP 模块测试

测试 MCP Server 的核心功能：
- 协议解析和验证
- 工具注册和执行
- 请求处理
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, MagicMock

from harnessgenj.mcp import (
    MCPServer,
    MCPServerConfig,
    MCPRequest,
    MCPResponse,
    MCPError,
    MCPErrorCode,
    MCPTool,
    MCPToolResult,
    MCPToolInfo,
    ToolRegistry,
    parse_request,
    validate_request,
)
from harnessgenj.mcp.tools import MCPTool as BaseMCPTool
from harnessgenj.mcp.tools.memory_tools import MEMORY_TOOLS
from harnessgenj.mcp.tools.task_tools import TASK_TOOLS
from harnessgenj.mcp.tools.system_tools import SYSTEM_TOOLS
from harnessgenj.mcp.tools.storage_tools import STORAGE_TOOLS


# ==================== 测试工具类 ====================

class MockMCPTool(BaseMCPTool):
    """测试用工具"""
    name = "test_tool"
    description = "测试工具"
    input_schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "测试消息"},
        },
        "required": ["message"],
    }
    category = "test"

    def execute(self, params: dict, harness) -> MCPToolResult:
        message = params.get("message", "")
        return MCPToolResult.text_result(f"Received: {message}")


class ErrorTool(BaseMCPTool):
    """会出错的工具"""
    name = "error_tool"
    description = "测试错误处理"
    input_schema = {
        "type": "object",
        "properties": {},
    }
    category = "test"

    def execute(self, params: dict, harness) -> MCPToolResult:
        # 返回错误结果而不是抛出异常
        return MCPToolResult.error_result("Test error")


# ==================== 协议测试 ====================

class TestMCPProtocol:
    """测试 MCP 协议"""

    def test_mcp_request_creation(self):
        """测试 MCP 请求创建"""
        request = MCPRequest(
            method="tools/list",
            params={},
            id=1,
        )
        assert request.jsonrpc == "2.0"
        assert request.method == "tools/list"
        assert request.id == 1

    def test_mcp_request_is_notification(self):
        """测试通知判断"""
        # 有 ID 的不是通知
        request = MCPRequest(method="test", id=1)
        assert not request.is_notification()

        # 无 ID 的是通知
        notification = MCPRequest(method="test")
        assert notification.is_notification()

    def test_mcp_response_success(self):
        """测试成功响应"""
        response = MCPResponse.success({"status": "ok"}, 1)
        assert response.jsonrpc == "2.0"
        assert response.result == {"status": "ok"}
        assert response.error is None
        assert response.id == 1

    def test_mcp_response_error(self):
        """测试错误响应"""
        response = MCPResponse.error_response(
            MCPErrorCode.INVALID_PARAMS,
            "参数错误",
            1,
        )
        assert response.result is None
        assert response.error.code == MCPErrorCode.INVALID_PARAMS
        assert response.error.message == "参数错误"

    def test_parse_request_valid(self):
        """测试有效请求解析"""
        data = {
            "jsonrpc": "2.0",
            "method": "test",
            "params": {"key": "value"},
            "id": 1,
        }
        result = parse_request(data)
        assert isinstance(result, MCPRequest)
        assert result.method == "test"

    def test_parse_request_invalid(self):
        """测试无效请求解析"""
        data = {"invalid": "data"}
        result = parse_request(data)
        assert isinstance(result, MCPError)

    def test_validate_request_valid(self):
        """测试请求验证 - 有效"""
        request = MCPRequest(method="test")
        error = validate_request(request)
        assert error is None

    def test_validate_request_invalid_version(self):
        """测试请求验证 - 无效版本"""
        request = MCPRequest(jsonrpc="1.0", method="test")
        error = validate_request(request)
        assert error is not None
        assert error.code == MCPErrorCode.INVALID_REQUEST

    def test_tool_result_text(self):
        """测试工具结果 - 文本"""
        result = MCPToolResult.text_result("Hello")
        assert result.isError is False
        assert len(result.content) == 1
        assert result.content[0]["type"] == "text"
        assert result.content[0]["text"] == "Hello"

    def test_tool_result_error(self):
        """测试工具结果 - 错误"""
        result = MCPToolResult.error_result("Something went wrong")
        assert result.isError is True
        assert "Something went wrong" in result.content[0]["text"]


# ==================== 工具测试 ====================

class MockMCPTools:
    """测试 MCP 工具"""

    def test_tool_info(self):
        """测试工具信息"""
        tool = MockMCPTool()
        info = tool.get_info()

        assert isinstance(info, MCPToolInfo)
        assert info.name == "test_tool"
        assert info.description == "测试工具"

    def test_tool_validate_params_success(self):
        """测试参数验证 - 成功"""
        tool = MockMCPTool()
        errors = tool.validate_params({"message": "test"})
        assert errors == []

    def test_tool_validate_params_missing_required(self):
        """测试参数验证 - 缺少必需参数"""
        tool = MockMCPTool()
        errors = tool.validate_params({})
        assert len(errors) > 0
        assert "缺少必需参数" in errors[0]

    def test_tool_execute(self):
        """测试工具执行"""
        tool = MockMCPTool()
        mock_harness = Mock()
        result = tool.execute({"message": "Hello"}, mock_harness)

        assert isinstance(result, MCPToolResult)
        assert "Hello" in result.content[0]["text"]

    def test_tool_registry_register(self):
        """测试工具注册"""
        registry = ToolRegistry()
        tool = MockMCPTool()
        registry.register(tool)

        assert registry.has_tool("test_tool")
        assert registry.get("test_tool") == tool

    def test_tool_registry_list(self):
        """测试工具列表"""
        registry = ToolRegistry()
        tool = MockMCPTool()
        registry.register(tool)

        tools = registry.list_tools()
        assert len(tools) == 1
        assert tools[0].name == "test_tool"


# ==================== 内置工具测试 ====================

class TestBuiltinTools:
    """测试内置工具"""

    def test_memory_tools_count(self):
        """测试内存工具数量"""
        assert len(MEMORY_TOOLS) == 6

    def test_task_tools_count(self):
        """测试任务工具数量"""
        assert len(TASK_TOOLS) == 6

    def test_system_tools_count(self):
        """测试系统工具数量"""
        assert len(SYSTEM_TOOLS) == 5

    def test_storage_tools_count(self):
        """测试存储工具数量"""
        assert len(STORAGE_TOOLS) == 4

    def test_memory_store_tool_schema(self):
        """测试内存存储工具 Schema"""
        tool = MEMORY_TOOLS[0]
        assert tool.name == "memory_store"
        assert "key" in tool.input_schema.get("properties", {})
        assert "content" in tool.input_schema.get("properties", {})

    def test_task_create_tool_schema(self):
        """测试任务创建工具 Schema"""
        tool = TASK_TOOLS[0]
        assert tool.name == "task_create"
        assert "request" in tool.input_schema.get("properties", {})

    def test_system_status_tool_schema(self):
        """测试系统状态工具 Schema"""
        tool = SYSTEM_TOOLS[0]
        assert tool.name == "system_status"


# ==================== Server 测试 ====================

class TestMCPServer:
    """测试 MCP Server"""

    def test_server_creation(self):
        """测试服务器创建"""
        server = MCPServer()
        assert server.config.server_name == "harnessgenj"
        assert server.config.version == "1.2.8"

    def test_server_with_config(self):
        """测试自定义配置"""
        config = MCPServerConfig(
            server_name="custom-server",
            version="1.0.0",
        )
        server = MCPServer(config=config)
        assert server.config.server_name == "custom-server"

    def test_server_list_tools(self):
        """测试工具列表"""
        server = MCPServer()
        tools = server.list_tools()
        assert len(tools) >= 19  # 至少有 19 个内置工具

    def test_server_handle_initialize(self):
        """测试初始化请求处理"""
        server = MCPServer()
        request_data = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {},
            "id": 1,
        }
        response = server.handle_request(request_data)

        assert response.result is not None
        assert "capabilities" in response.result
        assert "serverInfo" in response.result

    def test_server_handle_tools_list(self):
        """测试工具列表请求"""
        server = MCPServer()
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 2,
        }
        response = server.handle_request(request_data)

        assert response.result is not None
        assert "tools" in response.result
        assert len(response.result["tools"]) >= 19

    def test_server_handle_tools_call(self):
        """测试工具调用请求"""
        server = MCPServer()
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "system_status",
                "arguments": {},
            },
            "id": 3,
        }
        response = server.handle_request(request_data)

        assert response.result is not None
        assert "content" in response.result

    def test_server_handle_unknown_method(self):
        """测试未知方法"""
        server = MCPServer()
        request_data = {
            "jsonrpc": "2.0",
            "method": "unknown_method",
            "params": {},
            "id": 4,
        }
        response = server.handle_request(request_data)

        assert response.error is not None
        assert response.error.code == MCPErrorCode.METHOD_NOT_FOUND

    def test_server_handle_invalid_json(self):
        """测试无效 JSON"""
        server = MCPServer()
        request_data = {"invalid": "data"}

        response = server.handle_request(request_data)
        assert response.error is not None


# ==================== 工具执行集成测试 ====================

class TestToolExecution:
    """测试工具执行"""

    @pytest.fixture
    def mock_harness(self):
        """创建模拟 Harness"""
        harness = Mock()
        harness.memory = Mock()
        harness.memory.store_knowledge = Mock()
        harness.memory.get_knowledge = Mock(return_value="test content")
        harness.memory.get_stats = Mock(return_value={
            "project": "TestProject",
            "stats": {"features_total": 5},
            "memory": {"eden_size": 10},
        })
        harness.storage = Mock()
        harness.storage.save = Mock()
        harness.storage.load = Mock(return_value="stored content")
        harness.receive_request = Mock(return_value={
            "success": True,
            "task_id": "TASK-001",
            "priority": "P1",
            "category": "功能开发",
        })
        harness.complete_task = Mock(return_value=True)
        harness.get_status = Mock(return_value={
            "project": "TestProject",
            "team": {"size": 3},
            "stats": {"features_developed": 5},
        })
        return harness

    def test_memory_store_execution(self, mock_harness):
        """测试内存存储执行"""
        tool = MEMORY_TOOLS[0]  # memory_store
        result = tool.execute(
            {"key": "test_key", "content": "test_content"},
            mock_harness,
        )
        assert result.isError is False
        mock_harness.memory.store_knowledge.assert_called_once()

    def test_memory_retrieve_execution(self, mock_harness):
        """测试内存检索执行"""
        tool = MEMORY_TOOLS[1]  # memory_retrieve
        result = tool.execute({"key": "test_key"}, mock_harness)
        assert result.isError is False
        mock_harness.memory.get_knowledge.assert_called_once()

    def test_task_create_execution(self, mock_harness):
        """测试任务创建执行"""
        tool = TASK_TOOLS[0]  # task_create
        result = tool.execute(
            {"request": "实现新功能", "request_type": "feature"},
            mock_harness,
        )
        assert result.isError is False
        mock_harness.receive_request.assert_called_once()

    def test_system_status_execution(self, mock_harness):
        """测试系统状态执行"""
        tool = SYSTEM_TOOLS[0]  # system_status
        result = tool.execute({}, mock_harness)
        assert result.isError is False
        mock_harness.get_status.assert_called_once()

    def test_storage_save_execution(self, mock_harness):
        """测试存储保存执行"""
        tool = STORAGE_TOOLS[0]  # storage_save
        result = tool.execute(
            {"key": "test", "content": "content"},
            mock_harness,
        )
        assert result.isError is False
        mock_harness.storage.save.assert_called_once()


# ==================== 错误处理测试 ====================

class TestErrorHandling:
    """测试错误处理"""

    def test_tool_execution_error(self):
        """测试工具执行错误"""
        tool = ErrorTool()
        mock_harness = Mock()
        result = tool.execute({}, mock_harness)
        assert result.isError is True
        assert "Test error" in result.content[0]["text"]

    def test_missing_tool_name(self):
        """测试缺少工具名"""
        server = MCPServer()
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"arguments": {}},
            "id": 1,
        }
        response = server.handle_request(request_data)
        assert response.error is not None
        assert response.error.code == MCPErrorCode.INVALID_PARAMS

    def test_nonexistent_tool(self):
        """测试不存在的工具"""
        server = MCPServer()
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "nonexistent_tool", "arguments": {}},
            "id": 1,
        }
        response = server.handle_request(request_data)
        assert response.error is not None
        assert response.error.code == MCPErrorCode.METHOD_NOT_FOUND


# ==================== 完整集成测试 ====================

class TestMCPIntegration:
    """MCP 完整集成测试"""

    def test_full_workflow(self):
        """测试完整工作流"""
        server = MCPServer()

        # 1. 初始化
        init_response = server.handle_request({
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {},
            "id": 1,
        })
        assert init_response.result is not None

        # 2. 获取工具列表
        list_response = server.handle_request({
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 2,
        })
        assert len(list_response.result["tools"]) >= 19

        # 3. 调用工具
        call_response = server.handle_request({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "system_status",
                "arguments": {},
            },
            "id": 3,
        })
        assert call_response.result is not None

    def test_tool_registration(self):
        """测试工具注册"""
        server = MCPServer()
        custom_tool = MockMCPTool()
        server.register_tool(custom_tool)

        tools = server.list_tools()
        tool_names = [t.name for t in tools]
        assert "test_tool" in tool_names