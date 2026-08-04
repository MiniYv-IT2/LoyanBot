"""plugin_store 单元测试 — 聚合 / likes 合并 / 版本对比

不访问真实服务器：refresh 与 plugin_stats 全部 mock。
"""

import pytest

from loyan.core.plugin_store import PluginStore

_PAYLOAD = {
    "updated_at": "2026-08-01T00:00:00",
    "sources": [
        {
            "name": "官方",
            "store_url": "http://127.0.0.1:1/store.json",
            "plugins": [
                {"id": "Music_Plugin", "name": "音乐插件", "version": "1.2.0",
                 "author": "a", "description": "d", "category": "娱乐", "tags": [],
                 "repo": "x/Music_Plugin", "branch": "main"},
                {"id": "Weather_Plugin", "name": "天气插件", "version": "0.9.0",
                 "author": "a", "description": "d", "category": "工具", "tags": [],
                 "repo": "x/Weather_Plugin", "branch": "main"},
            ],
        }
    ],
}


@pytest.fixture
def store(tmp_path, monkeypatch):
    s = PluginStore()
    monkeypatch.setattr(s, "refresh", _async_payload)
    monkeypatch.setattr(s, "_local_state", lambda: {})
    return s


async def _async_payload(force: bool = False):
    return _PAYLOAD


@pytest.mark.asyncio
async def test_store_list_merges_likes(store, monkeypatch):
    from loyan.core import plugin_stats as stats_module
    from loyan.core.plugin_stats import PluginStats

    fake = PluginStats()
    monkeypatch.setattr(fake, "get_likes", _fake_get_likes)
    monkeypatch.setattr(stats_module, "plugin_stats", fake)

    result = await store.store_list()
    by_id = {p["id"]: p for p in result}
    assert by_id["Music_Plugin"]["likes"] == 5
    assert by_id["Weather_Plugin"]["likes"] == 0
    assert by_id["Music_Plugin"]["source"] == "官方"
    assert by_id["Music_Plugin"]["update_available"] is False


async def _fake_get_likes(ids):
    return {"likes": {"Music_Plugin": 5}, "stats_ok": True, "liked": {}}


@pytest.mark.asyncio
async def test_store_list_update_available(store, monkeypatch):
    monkeypatch.setattr(
        store, "_local_state",
        lambda: {"Music_Plugin": {"name": "Music_Plugin", "version": "1.1.0",
                                  "enabled": True, "source": "local", "path": "/tmp"}},
    )
    result = await store.store_list()
    by_id = {p["id"]: p for p in result}
    assert by_id["Music_Plugin"]["installed"] is True
    assert by_id["Music_Plugin"]["update_available"] is True
    assert by_id["Music_Plugin"]["local_version"] == "1.1.0"


@pytest.mark.asyncio
async def test_store_list_dedup_keeps_higher_version(store, monkeypatch):
    payload = {
        "updated_at": "t",
        "sources": [
            {"name": "A", "plugins": [{"id": "P", "name": "p", "version": "1.0.0"}]},
            {"name": "B", "plugins": [{"id": "P", "name": "p", "version": "1.5.0"}]},
        ],
    }
    monkeypatch.setattr(store, "refresh", _make_payload(payload))
    result = await store.store_list()
    assert len(result) == 1
    assert result[0]["version"] == "1.5.0"
    assert result[0]["source"] == "B"


def _make_payload(payload):
    import asyncio

    async def _refresh(force: bool = False):
        await asyncio.sleep(0)
        return payload

    return _refresh
