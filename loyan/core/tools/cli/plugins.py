"""插件管理 — 列表/安装/更新/卸载"""
import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import typer

from .utils import find_plugins_dir, system_plugins_dir, pip_install


def _scan_dir(plugins_dir: Path, source: str) -> list[dict]:
    if not plugins_dir.is_dir():
        return []
    result = []
    for d in sorted(plugins_dir.iterdir()):
        if not d.is_dir():
            continue
        meta_file = d / "metadata.toml"
        if not meta_file.exists():
            continue
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib
        meta_name = d.name
        try:
            with open(meta_file, "rb") as f:
                raw = tomllib.load(f)
            meta_name = raw.get("plugin", {}).get("name", d.name)
        except Exception:
            pass
        req_file = d / "requirements.txt"
        result.append({
            "name": meta_name,
            "dir": d.name,
            "path": str(d),
            "source": source,
            "has_requirements": req_file.exists(),
        })
    return result


def list_plugins(root: Path) -> list[dict]:
    """扫描 系统 + 用户 双目录所有有效插件"""
    result = _scan_dir(system_plugins_dir(), "system")
    result += _scan_dir(find_plugins_dir(root), "user")
    return result


def _install_deps(target: Path) -> None:
    req = target / "requirements.txt"
    if req.exists():
        typer.echo("   Installing dependencies...")
        pip_install([], req_file=str(req))


def _install_from_store(source: str) -> bool:
    """商店通道安装：user/repo → store_install（codeload zip + 镜像链 + 安全校验）"""
    plugin_id = source.split("/")[-1]
    import asyncio
    from loyan.core.plugin_store import plugin_store
    try:
        asyncio.run(plugin_store.store_install(plugin_id, skip_reload=True))
        typer.echo(f"   Store install complete: {plugin_id}")
        return True
    except Exception as e:
        typer.echo(f"   Store install failed: {e}")
        return False


def install_plugin(root: Path, source: str) -> bool:
    """安装插件

    Args:
        source: 插件目录名 / 本地路径 / GitHub 简写(user/repo) / Git URL
    """
    plugins_dir = find_plugins_dir(root)
    plugins_dir.mkdir(parents=True, exist_ok=True)

    is_plain_name = "/" not in source and not source.startswith(("http", "\\"))
    if is_plain_name:
        existing = plugins_dir / source
        if existing.is_dir():
            req = existing / "requirements.txt"
            if req.exists():
                typer.echo(f"   Installing dependencies from {source}...")
                pip_install([], req_file=str(req))
                typer.echo("   Dependencies installed")
            else:
                typer.echo(f"   No requirements.txt in {source}")
            return True

    # 本地路径（相对/绝对）→ 直接复制
    if os.path.exists(source) and not source.startswith(("http", "\\")) and not source.endswith(".git"):
        src = Path(source).resolve()
        name = src.name
        target = plugins_dir / name
        if target.exists():
            typer.echo(f"   Plugin {name} already exists")
            return False
        shutil.copytree(src, target, ignore=shutil.ignore_patterns(
            "__pycache__", ".git", ".venv", "node_modules"
        ))
        typer.echo(f"   Copied: {name}")
        _install_deps(target)
        typer.echo(f"   Installed to: {plugins_dir / name}")
        return True

    # GitHub 简写: "user/repo" → 优先商店通道
    if "/" in source and not source.startswith(("http", "\\")):
        if _install_from_store(source):
            return True
        source = f"https://github.com/{source}.git"

    try:
        if source.endswith(".git"):
            name = source.rstrip("/").split("/")[-1].replace(".git", "")
            target = plugins_dir / name
            if target.exists():
                typer.echo(f"   Plugin {name} already exists")
                return False
            subprocess.check_call(
                ["git", "clone", source, str(target)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60
            )
            typer.echo(f"   Cloned: {name}")
        else:
            src = Path(source).resolve()
            if not src.exists():
                typer.echo(f"   Path not found: {source}")
                return False
            name = src.name
            target = plugins_dir / name
            if target.exists():
                typer.echo(f"   Plugin {name} already exists")
                return False
            shutil.copytree(src, target, ignore=shutil.ignore_patterns(
                "__pycache__", ".git", ".venv", "node_modules"
            ))
            typer.echo(f"   Copied: {name}")

        _install_deps(target)
        typer.echo(f"   Installed to: {plugins_dir / name}")
        return True
    except subprocess.TimeoutExpired:
        typer.echo("   Operation timed out (network issue?)")
        return False
    except Exception as e:
        typer.echo(f"   Install failed: {e}")
        return False


def update_plugin(root: Path, name: str) -> bool:
    """更新插件（商店插件走 store_update 备份回滚；git 插件提示手动 pull）"""
    plugins_dir = find_plugins_dir(root)
    target = plugins_dir / name
    if not target.is_dir():
        typer.echo(f"   Plugin {name} not found ({plugins_dir})")
        return False
    import asyncio
    from loyan.core.plugin_store import plugin_store
    try:
        asyncio.run(plugin_store.store_update(name, skip_reload=True))
        typer.echo(f"   Update complete: {name}")
        return True
    except FileNotFoundError:
        typer.echo(f"   Plugin {name} not in store (maybe git-installed); run git pull in its directory")
        return False
    except Exception as e:
        typer.echo(f"   Update failed: {e}")
        return False


def remove_plugin(root: Path, name: str) -> bool:
    """卸载插件（仅用户插件；系统内置拒绝删除）"""
    user_dir = find_plugins_dir(root)
    target = user_dir / name
    if not target.exists():
        if (system_plugins_dir() / name).is_dir():
            typer.echo(f"   Plugin {name} is a system plugin, do not remove (restored on upgrade)")
            return False
        typer.echo(f"   Plugin {name} not found")
        return False
    shutil.rmtree(target, ignore_errors=True)
    typer.echo(f"   Deleted: {name}")
    return True
