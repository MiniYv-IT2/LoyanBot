"""CLI 插件命令集成测试 — 本地安装 → 列表 → 卸载 全链路（tmp 隔离，无网络）"""
import pytest

from loyan.core.tools.cli import plugins as cli_plugins
from loyan.core.tools import paths


@pytest.fixture
def iso_home(tmp_path, monkeypatch):
    monkeypatch.setenv("GRACYBOT_HOME", str(tmp_path))
    paths.invalidate_cache()
    yield tmp_path
    paths.invalidate_cache()


def _make_plugin(dirpath, name):
    d = dirpath / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "metadata.toml").write_text(
        f'[plugin]\nname = "{name}"\nversion = "1.0.0"\n', encoding="utf-8"
    )
    (d / "main.py").write_text("", encoding="utf-8")
    return d


def test_install_list_remove_chain(iso_home):
    src = _make_plugin(iso_home / "src", "ChainOne")

    assert cli_plugins.install_plugin(iso_home, str(src)) is True
    assert (iso_home / "storage" / "plugins" / "ChainOne" / "main.py").exists()

    names = [p["dir"] for p in cli_plugins.list_plugins(iso_home)]
    assert "ChainOne" in names

    assert cli_plugins.remove_plugin(iso_home, "ChainOne") is True
    assert not (iso_home / "storage" / "plugins" / "ChainOne").exists()
    names = [p["dir"] for p in cli_plugins.list_plugins(iso_home)]
    assert "ChainOne" not in names


def test_reinstall_after_remove(iso_home):
    src = _make_plugin(iso_home / "src", "ReOne")
    cli_plugins.install_plugin(iso_home, str(src))
    cli_plugins.remove_plugin(iso_home, "ReOne")
    assert cli_plugins.install_plugin(iso_home, str(src)) is True
    assert (iso_home / "storage" / "plugins" / "ReOne").is_dir()
