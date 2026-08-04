"""CLI 插件命令单元测试 — 路径定位 / 双目录列表 / 本地安装 / 商店通道 / 卸载安全

GRACYBOT_HOME 指向 tmp_path 隔离全部路径，不触碰真实插件。
"""
import pytest

from loyan.core.tools.cli import plugins as cli_plugins
from loyan.core.tools.cli.utils import find_plugins_dir, system_plugins_dir
from loyan.core.tools import paths


@pytest.fixture
def iso_home(tmp_path, monkeypatch):
    """隔离环境：GRACYBOT_HOME → tmp_path，并清空 paths 缓存"""
    monkeypatch.setenv("GRACYBOT_HOME", str(tmp_path))
    paths.invalidate_cache()
    yield tmp_path
    paths.invalidate_cache()


def _make_plugin(dirpath, name, meta_name=None):
    d = dirpath / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "metadata.toml").write_text(
        f'[plugin]\nname = "{meta_name or name}"\nversion = "1.0.0"\n', encoding="utf-8"
    )
    return d


def test_find_plugins_dir_points_to_user_dir(iso_home):
    assert find_plugins_dir(iso_home) == iso_home / "storage" / "plugins"
    assert system_plugins_dir() == iso_home / "loyan" / "plugins"


def test_list_plugins_scans_both_dirs(iso_home):
    _make_plugin(iso_home / "loyan" / "plugins", "SysOne")
    _make_plugin(iso_home / "storage" / "plugins", "UserOne")
    result = cli_plugins.list_plugins(iso_home)
    by_dir = {p["dir"]: p for p in result}
    assert by_dir["SysOne"]["source"] == "system"
    assert by_dir["UserOne"]["source"] == "user"


def test_list_plugins_skips_non_plugin_dirs(iso_home):
    (iso_home / "storage" / "plugins" / "no_meta").mkdir(parents=True)
    assert cli_plugins.list_plugins(iso_home) == []


def test_install_local_path_copies_to_user_dir(iso_home):
    src = _make_plugin(iso_home / "src_plugins", "LocalOne")
    assert cli_plugins.install_plugin(iso_home, str(src)) is True
    dest = iso_home / "storage" / "plugins" / "LocalOne"
    assert dest.is_dir()
    assert (dest / "metadata.toml").exists()


def test_install_store_channel_uses_skip_reload(iso_home, monkeypatch):
    from loyan.core.plugin_store import plugin_store

    captured = {}

    async def fake_store_install(plugin_id, skip_reload=False):
        captured["plugin_id"] = plugin_id
        captured["skip_reload"] = skip_reload
        return {"success": True}

    monkeypatch.setattr(plugin_store, "store_install", fake_store_install)
    assert cli_plugins.install_plugin(iso_home, "Vway-yw/loyan-config") is True
    assert captured["plugin_id"] == "loyan-config"
    assert captured["skip_reload"] is True


def test_remove_user_plugin_deletes(iso_home):
    _make_plugin(iso_home / "storage" / "plugins", "UserOne")
    assert cli_plugins.remove_plugin(iso_home, "UserOne") is True
    assert not (iso_home / "storage" / "plugins" / "UserOne").exists()


def test_remove_system_plugin_refused(iso_home, capsys):
    _make_plugin(iso_home / "loyan" / "plugins", "SysOne")
    assert cli_plugins.remove_plugin(iso_home, "SysOne") is False
    assert (iso_home / "loyan" / "plugins" / "SysOne").is_dir()
    assert "系统内置" in capsys.readouterr().out


def test_remove_missing_plugin_returns_false(iso_home):
    assert cli_plugins.remove_plugin(iso_home, "NotExist") is False
