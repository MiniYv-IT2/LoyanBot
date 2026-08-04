"""插件管理 — 列表/安装/更新/卸载"""
import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Optional

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
        print(f"   安装依赖...")
        pip_install([], req_file=str(req))


def _install_from_store(source: str) -> bool:
    """商店通道安装：user/repo → store_install（codeload zip + 镜像链 + 安全校验）"""
    plugin_id = source.split("/")[-1]
    import asyncio
    from loyan.core.plugin_store import plugin_store
    try:
        asyncio.run(plugin_store.store_install(plugin_id, skip_reload=True))
        print(f"   商店安装完成: {plugin_id}")
        return True
    except Exception as e:
        print(f"   商店安装失败: {e}")
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
                print(f"   安装 {source} 的依赖...")
                pip_install([], req_file=str(req))
                print(f"   依赖安装完成")
            else:
                print(f"   {source} 没有 requirements.txt")
            return True

    # 本地路径（相对/绝对）→ 直接复制
    if os.path.exists(source) and not source.startswith(("http", "\\")) and not source.endswith(".git"):
        src = Path(source).resolve()
        name = src.name
        target = plugins_dir / name
        if target.exists():
            print(f"   插件 {name} 已存在")
            return False
        shutil.copytree(src, target, ignore=shutil.ignore_patterns(
            "__pycache__", ".git", ".venv", "node_modules"
        ))
        print(f"   复制完成: {name}")
        _install_deps(target)
        print(f"   已安装到: {plugins_dir / name}")
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
                print(f"   插件 {name} 已存在")
                return False
            subprocess.check_call(
                ["git", "clone", source, str(target)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60
            )
            print(f"   克隆完成: {name}")
        else:
            src = Path(source).resolve()
            if not src.exists():
                print(f"   路径不存在: {source}")
                return False
            name = src.name
            target = plugins_dir / name
            if target.exists():
                print(f"   插件 {name} 已存在")
                return False
            shutil.copytree(src, target, ignore=shutil.ignore_patterns(
                "__pycache__", ".git", ".venv", "node_modules"
            ))
            print(f"   复制完成: {name}")

        _install_deps(target)
        print(f"   已安装到: {plugins_dir / name}")
        return True
    except subprocess.TimeoutExpired:
        print(f"   操作超时（网络不佳？）")
        return False
    except Exception as e:
        print(f"   安装失败: {e}")
        return False


def update_plugin(root: Path, name: str) -> bool:
    """更新插件（商店插件走 store_update 备份回滚；git 插件提示手动 pull）"""
    plugins_dir = find_plugins_dir(root)
    target = plugins_dir / name
    if not target.is_dir():
        print(f"   插件 {name} 不存在（{plugins_dir}）")
        return False
    import asyncio
    from loyan.core.plugin_store import plugin_store
    try:
        asyncio.run(plugin_store.store_update(name, skip_reload=True))
        print(f"   更新完成: {name}")
        return True
    except FileNotFoundError:
        print(f"   插件 {name} 不在商店中（可能是 git 安装），请在插件目录内执行 git pull")
        return False
    except Exception as e:
        print(f"   更新失败: {e}")
        return False


def remove_plugin(root: Path, name: str) -> bool:
    """卸载插件（仅用户插件；系统内置拒绝删除）"""
    user_dir = find_plugins_dir(root)
    target = user_dir / name
    if not target.exists():
        if (system_plugins_dir() / name).is_dir():
            print(f"   插件 {name} 是系统内置插件，请勿删除（升级会还原）")
            return False
        print(f"   插件 {name} 不存在")
        return False
    shutil.rmtree(target, ignore_errors=True)
    print(f"   已删除: {name}")
    return True
