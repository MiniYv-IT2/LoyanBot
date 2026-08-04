"""插件商店源服务 — 配置读写 / 拉取缓存 / 聚合 / 压缩包安装 / 更新回滚"""

import asyncio
import json
import logging
import os
import re
import shutil
import tempfile
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import httpx

from loyan.core.config_manager import config_manager
from loyan.core.plugin_manager import plugin_manager
from loyan.core.tools.paths import get_storage_dir, get_user_plugins_dir

_logger = logging.getLogger("Core.Store")

# ── 常量 ──────────────────────────────────────────────

_CACHE_TTL = timedelta(minutes=5)

# ── 工具函数 ──────────────────────────────────────────

def _version_gt(v1: str, v2: str) -> bool:
    try:
        from packaging.version import Version
        return Version(v1 or "0") > Version(v2 or "0")
    except Exception:
        return plugin_manager.compare_versions(v1 or "0", v2 or "0") > 0


def _read_toml_version(path: str) -> Optional[str]:
    try:
        import tomllib
        with open(path, "rb") as f:
            return tomllib.load(f).get("version")
    except Exception:
        return None


class PluginStore:
    """商店源服务单例 — 配置、缓存、聚合、安装、更新回滚"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self._config: dict = {}
        self._cache_lock = asyncio.Lock()
        self._op_lock = asyncio.Lock()

    # ── 配置 ──

    def get_config(self) -> dict:
        config = config_manager.get_store_config()
        self._config = config
        return config

    def save_config(self, config: dict) -> bool:
        if not config_manager.save_store_config(config):
            _logger.error("save store config failed")
            return False
        self._config = config_manager.get_store_config()
        return True

    # ── 拉取 + 缓存 ──

    @staticmethod
    def _cache_path() -> str:
        return os.path.join(get_storage_dir(), "cache", "store.json")

    @staticmethod
    def _read_cache() -> Optional[dict]:
        try:
            with open(PluginStore._cache_path(), "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    @staticmethod
    def _write_cache(payload: dict) -> None:
        try:
            path = PluginStore._cache_path()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except OSError as e:
            _logger.error("write store cache failed: %s", e)

    @staticmethod
    def _cache_fresh(cached: Optional[dict]) -> bool:
        if not cached:
            return False
        try:
            updated = datetime.fromisoformat(cached.get("updated_at", ""))
            return datetime.now() - updated < _CACHE_TTL
        except ValueError:
            return False

    async def refresh(self, force: bool = False) -> dict:
        async with self._cache_lock:
            cached = await asyncio.to_thread(self._read_cache)
            if not force and self._cache_fresh(cached):
                return cached
            config = self.get_config()
            sources = [s for s in config.get("sources", []) if s.get("enabled")]
            payload = {"updated_at": datetime.now().isoformat(timespec="seconds"), "sources": []}
            failures = 0
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                for src in sources:
                    try:
                        resp = await client.get(src.get("store_url", ""))
                        resp.raise_for_status()
                        data = resp.json()
                        payload["sources"].append({
                            "name": src.get("name", ""),
                            "store_url": src.get("store_url", ""),
                            "plugins": data.get("plugins", []),
                        })
                    except Exception as e:
                        failures += 1
                        _logger.error("fetch store source %s failed: %s", src.get("store_url"), e)
            if sources and failures == len(sources):
                if cached:
                    _logger.warning("all store sources failed, fall back to cached data")
                    return cached
                raise RuntimeError("all store sources failed and no cache available")
            await asyncio.to_thread(self._write_cache, payload)
            return payload

    # ── 聚合 ──

    async def store_list(self, force: bool = False) -> List[dict]:
        payload = await self.refresh(force=force)
        merged: Dict[str, dict] = {}
        for src in payload.get("sources", []):
            src_name = src.get("name", "")
            for p in src.get("plugins", []) or []:
                item = dict(p)
                item["source"] = src_name
                pid = item.get("id", "")
                if not pid:
                    continue
                existing = merged.get(pid)
                if existing is None or _version_gt(item.get("version", ""), existing.get("version", "")):
                    merged[pid] = item
        local = self._local_state()
        likes_data = await self._get_likes(list(merged.keys()))
        likes = likes_data.get("likes", {}) if isinstance(likes_data, dict) else {}
        liked_map = likes_data.get("liked", {}) if isinstance(likes_data, dict) else {}
        downloads = await self._get_downloads(list(merged.keys()))
        result = []
        for pid, item in merged.items():
            inst = local.get(pid)
            installed = inst is not None
            local_version = (inst or {}).get("version", "")
            result.append({
                **item,
                "installed": installed,
                "local_version": local_version,
                "update_available": installed and bool(local_version) and _version_gt(item.get("version", ""), local_version),
                "enabled": bool(inst.get("enabled", True)) if inst else False,
                "likes": likes.get(pid, 0),
                "downloads": downloads.get(pid, 0),
                "liked": bool(liked_map.get(pid, False)),
            })
        return result

    def _local_state(self) -> Dict[str, dict]:
        state: Dict[str, dict] = {}
        list_fn = getattr(plugin_manager, "list_plugins", None)
        if callable(list_fn):
            try:
                for item in list_fn() or []:
                    name = item.get("name")
                    if name:
                        state[name] = dict(item)
                if state:
                    return state
            except Exception as e:
                _logger.error("plugin_manager.list_plugins failed: %s", e)
        disabled = set()
        try:
            disabled = plugin_manager.load_disabled_plugins()
        except Exception:
            pass
        for p in getattr(plugin_manager, "registry", []) or []:
            name = p.get("name", "")
            if name:
                state[name] = {
                    "name": name,
                    "version": p.get("version", ""),
                    "enabled": name not in disabled,
                    "source": "local",
                    "path": p.get("plugin_path", ""),
                }
        for name, ver in (getattr(plugin_manager, "versions", {}) or {}).items():
            entry = state.setdefault(name, {"name": name, "enabled": name not in disabled, "source": "local"})
            entry["version"] = ver
        base = get_user_plugins_dir()
        if os.path.isdir(base):
            for pid in os.listdir(base):
                if pid in state:
                    continue
                meta_path = os.path.join(base, pid, "metadata.toml")
                ver = _read_toml_version(meta_path) if os.path.isfile(meta_path) else None
                if ver is None:
                    continue
                state[pid] = {
                    "name": pid,
                    "version": ver,
                    "enabled": pid not in disabled,
                    "source": "local",
                    "path": os.path.join(base, pid),
                }
        return state

    async def _get_likes(self, ids: List[str]) -> dict:
        try:
            from loyan.core.plugin_stats import plugin_stats
            fn = getattr(plugin_stats, "get_likes", None)
            if fn is None:
                return {}
            if asyncio.iscoroutinefunction(fn):
                return await fn(ids)
            return await asyncio.to_thread(fn, ids)
        except Exception as e:
            _logger.error("plugin_stats unavailable, likes omitted: %s", e)
            return {}

    async def _get_downloads(self, ids: List[str]) -> dict:
        try:
            from loyan.core.plugin_stats import plugin_stats
            fn = getattr(plugin_stats, "get_downloads", None)
            if fn is None:
                return {}
            if asyncio.iscoroutinefunction(fn):
                result = await fn(ids)
            else:
                result = await asyncio.to_thread(fn, ids)
            return result.get("downloads", {}) if isinstance(result, dict) else {}
        except Exception as e:
            _logger.error("plugin_stats downloads unavailable: %s", e)
            return {}

    # ── 下载 / 解压 ──

    
    def _zip_url(self, entry: dict) -> str:
        repo = entry.get("repo", "")
        branch = entry.get("branch") or "main"
        base = (self.get_config().get("download_base") or "").rstrip("/")
        if base:
            return f"{base}/plugins/{repo}"
        return f"https://codeload.github.com/{repo}/zip/refs/heads/{branch}"

    async def _download_with_mirrors(self, url: str, dest: str) -> None:
        mirrors = self.get_config().get("git_mirrors", [])
        attempts = [url] + [m.rstrip("/") + "/" + url.lstrip("/") for m in mirrors if m]
        last_err = None
        for attempt in attempts:
            try:
                async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
                    async with client.stream("GET", attempt) as resp:
                        resp.raise_for_status()
                        os.makedirs(os.path.dirname(dest), exist_ok=True)
                        with open(dest, "wb") as f:
                            async for chunk in resp.aiter_bytes():
                                f.write(chunk)
                return
            except Exception as e:
                last_err = e
                _logger.error("download %s failed: %s", attempt, e)
        raise RuntimeError(f"download failed for {url}: {last_err}")

    @staticmethod
    def _extract_zip(zip_path: str, dest_dir: str, plugin_id: str) -> str:
        with zipfile.ZipFile(zip_path) as zf:
            for info in zf.infolist():
                name = info.filename.replace("\\", "/")
                if ".." in Path(name).parts or name.startswith("/") or re.match(r"^[A-Za-z]:", name):
                    raise ValueError(f"zip entry path traversal rejected: {info.filename}")
            os.makedirs(dest_dir, exist_ok=True)
            zf.extractall(dest_dir)
        entries = [e for e in os.listdir(dest_dir) if e not in ("__MACOSX", os.path.basename(zip_path))]
        if len(entries) == 1 and os.path.isdir(os.path.join(dest_dir, entries[0])):
            return entries[0]
        if plugin_id in entries and os.path.isdir(os.path.join(dest_dir, plugin_id)):
            return plugin_id
        raise ValueError(f"zip root dir mismatch: expected single root or '{plugin_id}', got {entries}")

    # ── 本地操作 ──

    def _enable_if_disabled(self, plugin_id: str) -> None:
        """安装成功后自动启用：从禁用集合移除（否则禁用过的插件重装后不会加载）"""
        try:
            disabled = plugin_manager.load_disabled_plugins()
            if plugin_id in disabled:
                disabled.discard(plugin_id)
                plugin_manager.save_disabled_plugins(disabled)
                _logger.info("plugin %s re-enabled after install", plugin_id)
        except Exception as e:
            _logger.error("enable %s failed: %s", plugin_id, e)

    @staticmethod
    def _reload_plugin(plugin_id: str) -> bool:
        try:
            return bool(plugin_manager.reload_plugin(plugin_id))
        except Exception as e:
            _logger.error("reload plugin %s failed: %s", plugin_id, e)
            return False

    def _emit(self, event_name: str, payload: dict) -> None:
        try:
            from loyan.core.event import EventType, BusinessEvent, event_bus
            asyncio.create_task(event_bus.publish_business(
                BusinessEvent(type=getattr(EventType, event_name), payload=payload, source="plugin_store")
            ))
        except Exception as e:
            _logger.error("emit %s failed: %s", event_name, e)

    @staticmethod
    def _plugin_dir(plugin_id: str) -> str:
        return os.path.join(get_user_plugins_dir(), plugin_id)

    @staticmethod
    def _backup_dir(plugin_id: str) -> str:
        return os.path.join(get_storage_dir(), "backups", "plugins", plugin_id)

    # ── 安装 ──

    async def _find_entry(self, plugin_id: str) -> Optional[dict]:
        payload = await self.refresh()
        for src in payload.get("sources", []):
            for p in src.get("plugins", []) or []:
                if p.get("id") == plugin_id:
                    return dict(p)
        return None

    async def store_install(self, plugin_id: str, skip_reload: bool = False) -> dict:
        async with self._op_lock:
            entry = await self._find_entry(plugin_id)
            if entry is None:
                raise LookupError(f"plugin {plugin_id} not found in store")
            dest = self._plugin_dir(plugin_id)
            if os.path.exists(dest):
                raise FileExistsError(f"plugin {plugin_id} already installed, use store_update")
            return await self._install_entry(entry, skip_reload=skip_reload)

    async def _install_entry(self, entry: dict, skip_reload: bool = False) -> dict:
        plugin_id = entry["id"]
        dest = self._plugin_dir(plugin_id)
        tmp_root = tempfile.mkdtemp(prefix="loyan_store_")
        zip_path = os.path.join(tmp_root, "plugin.zip")
        try:
            await self._download_with_mirrors(self._zip_url(entry), zip_path)
            root = await asyncio.to_thread(self._extract_zip, zip_path, tmp_root, plugin_id)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            await asyncio.to_thread(shutil.move, os.path.join(tmp_root, root), dest)
            if not skip_reload:
                if not await asyncio.to_thread(self._reload_plugin, plugin_id):
                    raise RuntimeError(f"reload plugin {plugin_id} failed after install")
        finally:
            await asyncio.to_thread(shutil.rmtree, tmp_root, ignore_errors=True)
        self._enable_if_disabled(plugin_id)
        self._record_download(plugin_id)
        self._emit("PLUGIN_INSTALLED", {"name": plugin_id, "version": entry.get("version", "")})
        _logger.info("plugin %s v%s installed", plugin_id, entry.get("version", ""))
        return {"success": True, "message": f"plugin {plugin_id} installed", "version": entry.get("version", "")}

    def _record_download(self, plugin_id: str) -> None:
        try:
            from loyan.core.plugin_stats import plugin_stats
            fn = getattr(plugin_stats, "record_download", None)
            if fn is None:
                return
            if asyncio.iscoroutinefunction(fn):
                async def fire():
                    try:
                        await fn(plugin_id)
                    except Exception:
                        pass
                asyncio.create_task(fire())
            else:
                fn(plugin_id)
        except Exception as e:
            _logger.debug("record_download skipped: %s", e)

    # ── 更新 + 回滚 ──

    async def store_update(self, plugin_id: str, skip_reload: bool = False) -> dict:
        async with self._op_lock:
            entry = await self._find_entry(plugin_id)
            if entry is None:
                raise LookupError(f"plugin {plugin_id} not found in store")
            dest = self._plugin_dir(plugin_id)
            backup = self._backup_dir(plugin_id)
            if not os.path.isdir(dest):
                raise FileNotFoundError(f"plugin {plugin_id} not installed")
            old_version = (self._local_state().get(plugin_id) or {}).get("version", "")
            tmp_root = tempfile.mkdtemp(prefix="loyan_store_")
            zip_path = os.path.join(tmp_root, "plugin.zip")
            try:
                os.makedirs(os.path.dirname(backup), exist_ok=True)
                await asyncio.to_thread(shutil.copytree, dest, backup)
                await self._download_with_mirrors(self._zip_url(entry), zip_path)
                root = await asyncio.to_thread(self._extract_zip, zip_path, tmp_root, plugin_id)
                await asyncio.to_thread(shutil.rmtree, dest)
                await asyncio.to_thread(shutil.move, os.path.join(tmp_root, root), dest)
                if not skip_reload:
                    if not await asyncio.to_thread(self._reload_plugin, plugin_id):
                        raise RuntimeError(f"reload plugin {plugin_id} failed after update")
            except Exception as e:
                rollback_err = None
                try:
                    await asyncio.to_thread(shutil.rmtree, dest, ignore_errors=True)
                    await asyncio.to_thread(shutil.copytree, backup, dest)
                    if not skip_reload:
                        if not await asyncio.to_thread(self._reload_plugin, plugin_id):
                            rollback_err = RuntimeError("rollback reload failed")
                except Exception as re_exc:
                    rollback_err = re_exc
                finally:
                    await asyncio.to_thread(shutil.rmtree, tmp_root, ignore_errors=True)
                if rollback_err is not None:
                    _logger.error("update rollback failed for %s: %s", plugin_id, rollback_err)
                    raise RuntimeError(f"update {plugin_id} failed: {e}; rollback failed: {rollback_err}") from e
                raise RuntimeError(f"update {plugin_id} failed: {e}; rolled back to previous version") from e
            finally:
                await asyncio.to_thread(shutil.rmtree, backup, ignore_errors=True)
            self._record_download(plugin_id)
            _logger.info("plugin %s updated %s -> %s", plugin_id, old_version, entry.get("version", ""))
            return {
                "success": True,
                "message": f"plugin {plugin_id} updated",
                "old_version": old_version,
                "new_version": entry.get("version", ""),
            }


plugin_store = PluginStore()
