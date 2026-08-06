"""LiteLLMProvider 单元测试 — chat/流式/embedding 归一化、thinking 剥离、错误映射

不访问真实服务器：litellm.acompletion / aembedding 全部 mock。
"""

import pytest

from loyan.brain.provider.errors import AuthError, RateLimitError, TimeoutError
from loyan.brain.provider.types.litellm import (
    LiteLLMProvider,
    ThinkStrip,
    ToolCallBuffer,
    normalize_usage,
    strip_think_block,
)


@pytest.fixture
def prov(monkeypatch):
    p = LiteLLMProvider({"api_key": "sk-test", "strip_think": True})
    return p


class _Msg:
    def __init__(self, content=None):
        self.content = content


class _Choice:
    def __init__(self, content=None):
        self.message = _Msg(content)


class _Resp:
    def __init__(self, content="hello", usage=None):
        self.choices = [_Choice(content)]
        self.model = "openai/gpt-4o"
        self.usage = usage


class _Usage:
    prompt_tokens = 10
    completion_tokens = 5
    total_tokens = 15


@pytest.mark.asyncio
async def test_chat_returns_normalized_dict(prov, monkeypatch):
    async def fake_acompletion(**kwargs):
        return _Resp(content="hi", usage=_Usage())

    monkeypatch.setattr("litellm.acompletion", fake_acompletion)
    result = await prov.chat([{"role": "user", "content": "x"}], "gpt-4o")
    assert result["content"] == "hi"
    assert result["usage"] == {"prompt": 10, "completion": 5, "total": 15}
    assert result["model"] == "openai/gpt-4o"
    assert "time" in result


@pytest.mark.asyncio
async def test_chat_strips_think_block(prov, monkeypatch):
    async def fake_acompletion(**kwargs):
        return _Resp(content="<thinking>推理</thinking>答案")

    monkeypatch.setattr("litellm.acompletion", fake_acompletion)
    result = await prov.chat([{"role": "user", "content": "x"}], "deepseek-r1")
    assert "<thinking>" not in result["content"]
    assert result["content"].strip() == "答案"


@pytest.mark.asyncio
async def test_chat_stream_yields_text_and_done(prov, monkeypatch):
    class _Delta:
        content = "你"

    class _Chunk:
        def __init__(self, content, usage=None):
            self.choices = [_DeltaChoice(content)]
            self.usage = usage

    class _DeltaChoice:
        def __init__(self, content):
            self.delta = _DeltaContent(content)

    class _DeltaContent:
        def __init__(self, content):
            self.content = content
            self.tool_calls = None

    chunks = [_Chunk("你"), _Chunk("好"), _Chunk(None, usage=_Usage())]

    async def fake_acompletion(**kwargs):
        async def gen():
            for c in chunks:
                yield c
        return gen()

    monkeypatch.setattr("litellm.acompletion", fake_acompletion)
    out = []
    async for item in prov.chat_stream([{"role": "user", "content": "x"}], "gpt-4o"):
        out.append(item)
    texts = [i["content"] for i in out if i["type"] == "text"]
    assert "".join(texts) == "你好"
    done = [i for i in out if i["type"] == "done"]
    assert done and done[0]["usage"]["total"] == 15


@pytest.mark.asyncio
async def test_embedding_returns_vectors(prov, monkeypatch):
    class _Data:
        embedding = [0.1, 0.2, 0.3]

    class _EmbResp:
        data = [_Data(), _Data()]

    async def fake_aembedding(**kwargs):
        return _EmbResp()

    monkeypatch.setattr("litellm.aembedding", fake_aembedding)
    vecs = await prov.embedding(["a", "b"], "text-embedding-3-small")
    assert len(vecs) == 2 and len(vecs[0]) == 3


@pytest.mark.asyncio
async def test_error_mapping(prov, monkeypatch):
    from litellm.exceptions import (
        AuthenticationError as LitAuthError,
        RateLimitError as LitRateLimit,
        Timeout as LitTimeout,
    )

    async def fake_auth(**kwargs):
        raise LitAuthError("bad key", "openai", "gpt-4o")

    async def fake_rate(**kwargs):
        raise LitRateLimit("limit", "openai", "gpt-4o")

    async def fake_timeout(**kwargs):
        raise LitTimeout("timeout", "openai", "gpt-4o")

    for fake, expected in ((fake_auth, AuthError), (fake_rate, RateLimitError), (fake_timeout, TimeoutError)):
        monkeypatch.setattr("litellm.acompletion", fake)
        with pytest.raises(expected):
            await prov.chat([{"role": "user", "content": "x"}], "gpt-4o")


def test_think_strip_state_machine():
    ts = ThinkStrip(remove=True)
    out = []
    out += ts.feed("前")
    out += ts.feed("<thinking>思考")
    out += ts.feed("中</thinking>后")
    out += ts.feed("续")
    tail = ts.flush()
    pieces = out + ([tail] if tail else [])
    text = "".join(t for k, t in pieces)
    assert text == "前后续"
    assert "思考" not in text


def test_think_strip_emit_reasoning():
    ts = ThinkStrip(remove=False, emit_reasoning=True)
    out = []
    out += ts.feed("答")
    out += ts.feed("<thinking>推理")
    out += ts.feed("中</thinking>完")
    tail = ts.flush()
    pieces = out + ([tail] if tail else [])
    kinds = [k for k, _ in pieces]
    assert "reasoning" in kinds
    text = "".join(t for k, t in pieces)
    assert "推理中" in text and "答" in text and "完" in text


def test_strip_think_block_fn():
    assert strip_think_block("a<thinking>x</thinking>b").strip() == "a\nb".strip() or "ab"


def test_tool_call_buffer_assembles():
    class _Fn:
        name = ""
        arguments = ""

    class _TC:
        index = 0
        id = "call_1"

        def __init__(self):
            self.function = _Fn()

    buf = ToolCallBuffer()
    tc = _TC()
    tc.function.name = "get_"
    buf.feed([tc])
    tc.function.name = "weather"
    tc.function.arguments = '{"city": "北京"}'
    buf.feed([tc])
    calls = buf.collect()
    assert len(calls) == 1
    assert calls[0]["function"]["name"] == "get_weather"
    assert "北京" in calls[0]["function"]["arguments"]


def test_usage_normalize_forms():
    assert normalize_usage(None) == {"prompt": 0, "completion": 0, "total": 0}
    assert normalize_usage({"prompt_tokens": 1, "completion_tokens": 2}) == {"prompt": 1, "completion": 2, "total": 3}
    assert normalize_usage({"input_tokens": 4, "output_tokens": 6}) == {"prompt": 4, "completion": 6, "total": 10}
