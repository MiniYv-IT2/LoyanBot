"""plugin_stats 单元测试 — 点赞去重 / 降级稳定 / 远端失败隔离

不访问真实服务器：stats_url 指向不可达地址，本地文件重定向到 tmp。
"""

import asyncio
import hashlib

import pytest

from loyan.core.plugin_stats import PluginStats


@pytest.fixture
def stats(tmp_path, monkeypatch):
    from loyan.core import plugin_stats as module
    monkeypatch.setattr(module, "get_data_dir", lambda: str(tmp_path))
    monkeypatch.setattr(module, "_read_stats_url", lambda: "http://127.0.0.1:1")
    return PluginStats()


@pytest.mark.asyncio
async def test_like_dedup(stats, tmp_path):
    assert await stats.store_like("Music_Plugin") is True
    assert await stats.store_like("Music_Plugin") is False
    liked_file = tmp_path / "plugin_likes.json"
    import json
    data = json.loads(liked_file.read_text(encoding="utf-8"))
    assert data["liked"] == ["Music_Plugin"]


@pytest.mark.asyncio
async def test_get_likes_degrade_stable(stats):
    r1 = await stats.get_likes(["Music_Plugin", "Weather_Plugin"])
    r2 = await stats.get_likes(["Music_Plugin", "Weather_Plugin"])
    assert r1["stats_ok"] is False
    assert r1["likes"]["Music_Plugin"] == r2["likes"]["Music_Plugin"]
    assert 0 <= r1["likes"]["Music_Plugin"] <= 1000
    expected = int(hashlib.md5(b"Music_Plugin").hexdigest(), 16) % 1001
    assert r1["likes"]["Music_Plugin"] == expected
    assert "liked" in r1


@pytest.mark.asyncio
async def test_get_likes_returns_likes_key(stats):
    result = await stats.get_likes(["Music_Plugin"])
    assert isinstance(result, dict)
    assert "likes" in result
    assert "stats_ok" in result
    assert "liked" in result


@pytest.mark.asyncio
async def test_record_download_no_raise(stats):
    stats.record_download("Music_Plugin")
    await asyncio.sleep(0.1)
