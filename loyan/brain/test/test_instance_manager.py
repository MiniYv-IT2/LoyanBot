"""Test InstanceManager — CRUD + ProviderManager integration"""

import asyncio
import sys
import os
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
logging.basicConfig(level=logging.WARNING)

import pytest

from loyan.brain.provider.types.instance import InstanceManager


async def _with_mgr(test_fn):
    m = InstanceManager()
    await m.init()
    try:
        return await test_fn(m)
    finally:
        await m.clear()


@pytest.mark.asyncio
async def test_init_creates_table():
    async def _run(m):
        rows = await m.list()
        assert isinstance(rows, list)
    await _with_mgr(_run)


@pytest.mark.asyncio
async def test_add_and_list():
    async def _run(m):
        await m.add({"id": "test1", "type": "openai", "model": "gpt-4", "api_key": "sk-test"})
        all_ = await m.list()
        ids = [r["id"] for r in all_]
        assert "test1" in ids
    await _with_mgr(_run)


@pytest.mark.asyncio
async def test_add_duplicate_raises():
    async def _run(m):
        await m.add({"id": "dup", "type": "openai"})
        with pytest.raises(Exception):
            await m.add({"id": "dup", "type": "openai"})
    await _with_mgr(_run)


@pytest.mark.asyncio
async def test_add_empty_id_raises():
    async def _run(m):
        with pytest.raises(ValueError):
            await m.add({"id": "", "type": "openai"})
    await _with_mgr(_run)


@pytest.mark.asyncio
async def test_get_existing():
    async def _run(m):
        await m.add({"id": "get_me", "type": "ollama"})
        item = await m.get("get_me")
        assert item is not None
        assert item["type"] == "ollama"
        assert item["enabled"] is True
    await _with_mgr(_run)


@pytest.mark.asyncio
async def test_get_missing():
    async def _run(m):
        item = await m.get("nonexistent")
        assert item is None
    await _with_mgr(_run)


@pytest.mark.asyncio
async def test_update():
    async def _run(m):
        await m.add({"id": "upd", "type": "openai", "model": "gpt-3"})
        await m.update("upd", {"model": "gpt-4", "api_base": "https://custom.com"})
        item = await m.get("upd")
        assert item["model"] == "gpt-4"
        assert item["api_base"] == "https://custom.com"
    await _with_mgr(_run)


@pytest.mark.asyncio
async def test_update_partial():
    async def _run(m):
        await m.add({"id": "partial", "type": "openai", "model": "gpt-3"})
        await m.update("partial", {"model": "gpt-4"})
        item = await m.get("partial")
        assert item["model"] == "gpt-4"
        assert item["type"] == "openai"
    await _with_mgr(_run)


@pytest.mark.asyncio
async def test_update_empty_noop():
    async def _run(m):
        await m.add({"id": "noop", "type": "openai"})
        await m.update("noop", {})
    await _with_mgr(_run)


@pytest.mark.asyncio
async def test_delete():
    async def _run(m):
        await m.add({"id": "del_me", "type": "anthropic"})
        await m.delete("del_me")
        item = await m.get("del_me")
        assert item is None
    await _with_mgr(_run)


@pytest.mark.asyncio
async def test_delete_nonexistent():
    async def _run(m):
        await m.delete("nope")
    await _with_mgr(_run)


@pytest.mark.asyncio
async def test_get_by_type():
    async def _run(m):
        await m.add({"id": "a1", "type": "openai"})
        await m.add({"id": "a2", "type": "openai"})
        await m.add({"id": "b1", "type": "ollama"})
        openai_list = await m.get_by_type("openai")
        assert len(openai_list) == 2
        ollama_list = await m.get_by_type("ollama")
        assert len(ollama_list) == 1
        empty = await m.get_by_type("nonexistent")
        assert empty == []
    await _with_mgr(_run)


@pytest.mark.asyncio
async def test_extra_field():
    async def _run(m):
        await m.add({"id": "extra_test", "type": "openai", "extra": {"proxy": "http://proxy:8080", "timeout": 120}})
        item = await m.get("extra_test")
        assert item["extra"]["proxy"] == "http://proxy:8080"
        assert item["extra"]["timeout"] == 120
    await _with_mgr(_run)


@pytest.mark.asyncio
async def test_enabled_default_true():
    async def _run(m):
        await m.add({"id": "en", "type": "openai"})
        item = await m.get("en")
        assert item["enabled"] is True
    await _with_mgr(_run)


@pytest.mark.asyncio
async def test_disabled_instance():
    async def _run(m):
        await m.add({"id": "dis", "type": "openai", "enabled": False})
        item = await m.get("dis")
        assert item["enabled"] is False
    await _with_mgr(_run)


@pytest.mark.asyncio
async def test_list_order():
    async def _run(m):
        await m.add({"id": "z", "type": "ollama"})
        await m.add({"id": "a", "type": "openai"})
        all_ = await m.list()
        types = [r["type"] for r in all_]
        assert types == sorted(types)
    await _with_mgr(_run)


@pytest.mark.asyncio
async def test_multiple_instances_same_type():
    async def _run(m):
        await m.add({"id": "work", "type": "openai", "api_key": "sk-work"})
        await m.add({"id": "personal", "type": "openai", "api_key": "sk-personal"})
        items = await m.get_by_type("openai")
        keys = {r["id"]: r["api_key"] for r in items}
        assert keys["work"] == "sk-work"
        assert keys["personal"] == "sk-personal"
        assert len(keys) == 2
    await _with_mgr(_run)


@pytest.mark.asyncio
async def test_update_extra():
    async def _run(m):
        await m.add({"id": "ext_upd", "type": "openai", "extra": {"a": 1}})
        await m.update("ext_upd", {"extra": {"b": 2}})
        item = await m.get("ext_upd")
        assert item["extra"]["b"] == 2
    await _with_mgr(_run)


@pytest.mark.asyncio
async def test_model_field():
    async def _run(m):
        await m.add({"id": "mod", "type": "openai", "model": "gpt-4-turbo"})
        item = await m.get("mod")
        assert item["model"] == "gpt-4-turbo"
    await _with_mgr(_run)


@pytest.mark.asyncio
async def test_discover_skips_instance_dir():
    from loyan.brain.provider.manager import ProviderManager
    pm = ProviderManager()
    pm._auto_discover()
    from loyan.brain.provider.base import _registry
    assert "openai" in _registry
    assert "ollama" in _registry
    assert "instance" not in _registry


@pytest.mark.asyncio
async def test_load_all_no_instances():
    from loyan.brain.provider.manager import ProviderManager
    pm = ProviderManager()
    await pm.load_all()
    assert pm.registry == {}


@pytest.mark.asyncio
async def test_load_all_with_instance():
    from loyan.brain.provider.keystore import keystore as _ks
    await _ks.init()
    from loyan.brain.provider.manager import ProviderManager
    pm = ProviderManager()
    await pm.instance_manager.clear()
    await pm.instance_manager.add({"id": "test_ollama", "type": "ollama", "api_base": "http://localhost:11434", "model": "llama3"})
    await pm.load_all()
    assert pm.get("test_ollama") is not None
    await pm.close_all()


@pytest.mark.asyncio
async def test_disabled_instance_skipped():
    from loyan.brain.provider.keystore import keystore as _ks
    await _ks.init()
    from loyan.brain.provider.manager import ProviderManager
    pm = ProviderManager()
    await pm.instance_manager.clear()
    await pm.instance_manager.add({"id": "off", "type": "ollama", "enabled": False})
    await pm.load_all()
    assert pm.get("off") is None
    await pm.close_all()


@pytest.mark.asyncio
async def test_unknown_type_skipped():
    from loyan.brain.provider.manager import ProviderManager
    pm = ProviderManager()
    await pm.instance_manager.clear()
    await pm.instance_manager.add({"id": "ghost", "type": "nonexistent"})
    await pm.load_all()
    assert pm.get("ghost") is None
    await pm.close_all()
