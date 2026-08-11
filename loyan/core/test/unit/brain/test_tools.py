"""brain_tool AI 工具单元测试 — 注册/查询/调用/权限/循环/回落

不访问真实服务器：provider 全部用 Fake 替代。
"""

import asyncio
import inspect

import pytest

from loyan.core.decorators.registration import (
    AI_TOOL_REGISTRY,
    _register_ai_tool_function,
    brain_tool,
    call_brain_tool,
    clear_registry,
    list_brain_tools,
)
from loyan.brain.tools.agent import LoyanAgent


@pytest.fixture(autouse=True)
def _clean_registry():
    clear_registry()
    yield
    clear_registry()


@brain_tool(name="test_weather", description="查询天气",
            params={"city": {"type": "string", "required": True, "description": "城市"}},
            permission="master")
async def _weather(ctx, city: str) -> str:
    return f"{city}: 晴"


@brain_tool(name="test_math", description="加法",
            params={"a": {"type": "number", "required": True},
                    "b": {"type": "number", "required": True}},
            permission="all")
def _math(ctx, a: int, b: int) -> str:
    return str(a + b)


def test_brain_tool_marker():
    assert hasattr(_weather, "_loyan_ai_tool")
    assert _weather._loyan_ai_tool["name"] == "test_weather"
    assert _weather._loyan_ai_tool["permission"] == "master"


def test_register_and_normalize_permission():
    _register_ai_tool_function(_weather, plugin_name="TestPlugin")
    assert len(AI_TOOL_REGISTRY) == 1
    entry = AI_TOOL_REGISTRY[0]
    assert entry["name"] == "test_weather"
    assert entry["permission"] == "admin", "master 应归一化为 admin"
    assert entry["plugin_name"] == "TestPlugin"


def test_register_duplicate_overwrites():
    _register_ai_tool_function(_weather, plugin_name="A")

    @brain_tool(name="test_weather", description="dup")
    async def _dup(ctx, city: str) -> str:
        return "dup"

    _register_ai_tool_function(_dup, plugin_name="B")
    assert len(AI_TOOL_REGISTRY) == 1, "重名应覆盖而非累积"
    assert AI_TOOL_REGISTRY[0]["plugin_name"] == "B"


def test_list_brain_tools():
    _register_ai_tool_function(_weather, plugin_name="A")
    _register_ai_tool_function(_math, plugin_name="A")
    tools = list_brain_tools()
    assert len(tools) == 2
    names = {t["name"] for t in tools}
    assert names == {"test_weather", "test_math"}


@pytest.mark.asyncio
async def test_call_brain_tool_async_and_sync():
    _register_ai_tool_function(_weather, plugin_name="A")
    _register_ai_tool_function(_math, plugin_name="A")
    r1 = await call_brain_tool("test_weather", {"city": "北京"})
    assert r1 == "北京: 晴"
    r2 = await call_brain_tool("test_math", {"a": 1, "b": 2})
    assert r2 == "3"


@pytest.mark.asyncio
async def test_call_brain_tool_not_found():
    r = await call_brain_tool("nonexistent", {})
    assert "not found" in r


def test_build_tools_schema():
    _register_ai_tool_function(_weather, plugin_name="A")
    _register_ai_tool_function(_math, plugin_name="A")
    agent = LoyanAgent(engine=None)
    schema = agent._build_tools_schema()
    assert len(schema) == 2
    fn = next(s for s in schema if s["function"]["name"] == "test_weather")
    assert fn["function"]["parameters"]["required"] == ["city"]
    assert fn["function"]["parameters"]["properties"]["city"]["type"] == "string"


class _FakeProv:
    """支持 tools 的假 provider: 第一轮返回 tool_calls, 第二轮返回文本"""

    def __init__(self):
        self.round = 0
        self.calls = []

    def supports_tools(self, model):
        return True

    async def chat(self, messages, model, **kwargs):
        self.calls.append(kwargs)
        self.round += 1
        if self.round == 1:
            return {
                "content": "",
                "tool_calls": [{
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "test_math", "arguments": '{"a": 1, "b": 2}'},
                }],
            }
        return {"content": "结果是 3", "usage": {"total": 10}}


class _FakeProvNoTools:
    """不支持 tools: supports_tools 返回 False"""

    def supports_tools(self, model):
        return False

    async def chat(self, messages, model, **kwargs):
        assert "tools" not in kwargs, "不支持 tools 时不应传 tools"
        return {"content": "普通回复", "usage": {}}


class _FakeProvRejectTools:
    """模型库误判支持, 实际 API 拒绝 tools"""

    def supports_tools(self, model):
        return True

    async def chat(self, messages, model, **kwargs):
        if "tools" in kwargs:
            raise Exception("Function call is not supported for this model")
        return {"content": "回落回复", "usage": {}}


class _Engine:
    def __init__(self, prov):
        self.providers = _Providers(prov)

    async def _build_messages(self, message, persona="", session_id=""):
        return [{"role": "user", "content": message}]


class _Providers:
    def __init__(self, prov):
        self._prov = prov
        self.models = ["m1"]

    def resolve(self, provider=""):
        return ("inst", self._prov)


@pytest.mark.asyncio
async def test_chat_with_tools_full_loop():
    _register_ai_tool_function(_math, plugin_name="A")
    agent = LoyanAgent(_Engine(_FakeProv()))
    reply = await agent.chat_with_tools("1+2?", ctx=None)
    assert reply == "结果是 3"


@pytest.mark.asyncio
async def test_chat_with_tools_no_support_fallback():
    _register_ai_tool_function(_math, plugin_name="A")
    agent = LoyanAgent(_Engine(_FakeProvNoTools()))
    reply = await agent.chat_with_tools("hi", ctx=None)
    assert reply == "普通回复"


@pytest.mark.asyncio
async def test_chat_with_tools_api_reject_fallback():
    _register_ai_tool_function(_math, plugin_name="A")
    agent = LoyanAgent(_Engine(_FakeProvRejectTools()))
    reply = await agent.chat_with_tools("hi", ctx=None)
    assert reply == "回落回复"


@pytest.mark.asyncio
async def test_chat_stream_with_tools_events():
    _register_ai_tool_function(_math, plugin_name="A")
    agent = LoyanAgent(_Engine(_FakeProv()))
    events = [e async for e in agent.chat_stream_with_tools("1+2?", ctx=None)]
    types = [e["type"] for e in events]
    assert "tool_call" in types
    assert "tool_result" in types
    assert "text" in types
    assert "done" in types
    tc = next(e for e in events if e["type"] == "tool_call")
    assert tc["name"] == "test_math"
