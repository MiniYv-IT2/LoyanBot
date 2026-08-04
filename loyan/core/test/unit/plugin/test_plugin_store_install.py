"""plugin_store 安装链路回归测试 — _reload_plugin / _enable_if_disabled / skip_reload

回归背景：_reload_plugin 漏 self 导致 TypeError、_enable_if_disabled 引用未定义
_plugin_manager、_plugin_manager 函数不存在——安装链路曾被这三个 bug 中断。
本文件确保安装链路不再抛参数/引用错误。
"""
import asyncio
import pytest

from loyan.core.plugin_store import PluginStore
from loyan.core.plugin_manager import plugin_manager


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("GRACYBOT_HOME", str(tmp_path))
    from loyan.core.tools import paths
    paths.invalidate_cache()
    monkeypatch.setattr(plugin_manager, "reload_plugin", lambda name: True)
    monkeypatch.setattr(plugin_manager, "load_disabled_plugins", lambda: set())
    monkeypatch.setattr(plugin_manager, "save_disabled_plugins", lambda s: None)
    s = PluginStore()
    return s


def test_reload_plugin_accepts_one_arg(store):
    assert store._reload_plugin("Music_Plugin") is True


def test_enable_if_disabled_no_undefined_name(store):
    store._enable_if_disabled("Music_Plugin")


def test_emit_async_from_thread_without_loop_does_not_raise(monkeypatch):
    """回归：store_install 经 to_thread 在无 loop 线程调 reload → _emit_async 不再报错"""
    from loyan.core.plugin_manager import plugin_manager
    import threading

    async def _noop_emit(event_name, payload):
        pass

    monkeypatch.setattr(plugin_manager, "_emit", _noop_emit)
    plugin_manager._main_loop = None
    errors = []

    def _run():
        try:
            plugin_manager._emit_async("PLUGIN_LOADED", {"name": "X"})
        except Exception as e:
            errors.append(e)

    t = threading.Thread(target=_run)
    t.start()
    t.join()
    assert errors == []


@pytest.mark.asyncio
async def test_store_install_skip_reload_skips_reload_call(store, monkeypatch):
    entry = {"id": "Demo_Plugin", "version": "1.0.0", "repo": "x/Demo_Plugin"}
    monkeypatch.setattr(store, "_find_entry", _async_entry(entry))
    monkeypatch.setattr(store, "_download_with_mirrors", _async_none)
    monkeypatch.setattr(store, "_extract_zip", _fake_extract)
    monkeypatch.setattr(store, "_emit", lambda *a, **k: None)
    monkeypatch.setattr(store, "_record_download", lambda *a, **k: None)
    reloaded = []

    def _fake_reload(plugin_id):
        reloaded.append(plugin_id)
        return True

    monkeypatch.setattr(store, "_reload_plugin", _fake_reload)

    result = await store.store_install("Demo_Plugin", skip_reload=True)
    assert result["success"] is True
    assert reloaded == []

    import shutil
    shutil.rmtree(store._plugin_dir("Demo_Plugin"))
    result = await store.store_install("Demo_Plugin", skip_reload=False)
    assert result["success"] is True
    assert reloaded == ["Demo_Plugin"]


def _async_entry(entry):
    async def _find(plugin_id):
        return dict(entry)
    return _find


async def _async_none(*args, **kwargs):
    return None


def _fake_extract(zip_path, tmp_root, plugin_id):
    import os
    root = os.path.join(tmp_root, "extracted")
    os.makedirs(root, exist_ok=True)
    return "extracted"
