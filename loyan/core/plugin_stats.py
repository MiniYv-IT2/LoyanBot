"""插件统计服务 — 点赞上传/查询降级/下载上报

与 plugin_store 零耦合：stats_url 读 config_manager.get_store_config()，
本地已点状态存 storage/data/plugin_likes.json（asyncio.Lock 保护读写）。
远端失败永不 raise（降级/静默），本地文件读写失败可 raise。
"""

import asyncio
import hashlib
import json
import logging
import os
from typing import Dict, List, Tuple

import httpx

from loyan.core.config_manager import config_manager
from loyan.core.tools.paths import get_data_dir

_logger = logging.getLogger("Core.PluginStats")

DEFAULT_STATS_URL = "http://38.55.145.10:16385"
_TIMEOUT = 3.0


# ── 路径与配置 ──

def _likes_path() -> str:
    return os.path.join(get_data_dir(), "plugin_likes.json")


def _read_stats_url() -> str:
    try:
        url = config_manager.get_store_config().get("stats_url")
        if isinstance(url, str) and url:
            return url
    except Exception:
        pass
    return DEFAULT_STATS_URL


def _stable_fake_count(plugin_id: str) -> int:
    return int(hashlib.md5(plugin_id.encode()).hexdigest(), 16) % 1001


class PluginStats:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._bg_tasks: set = set()

    @property
    def stats_url(self) -> str:
        return _read_stats_url()

    async def _load_liked(self) -> List[str]:
        path = _likes_path()
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        liked = data.get("liked", []) if isinstance(data, dict) else []
        return [str(i) for i in liked] if isinstance(liked, list) else []

    async def _save_liked(self, ids: List[str]) -> None:
        path = _likes_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"liked": ids}, f, ensure_ascii=False)

    # ── 点赞 ──

    async def store_like(self, plugin_id: str) -> bool:
        """已点则 no-op（不去 toggle）并返回 False；上传失败仍记本地，返回 True。"""
        async with self._lock:
            liked = await self._load_liked()
            if plugin_id in liked:
                return False
            liked.append(plugin_id)
            await self._save_liked(liked)
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                await client.post(f"{self.stats_url}/likes/{plugin_id}")
        except httpx.HTTPError:
            _logger.warning("like upload failed, keep local: %s", plugin_id)
        return True

    # ── 查询 ──

    async def get_likes(self, plugin_ids: List[str]) -> Dict:
        """远端成功用远端；失败降级稳定随机（同 id 恒同值），合并本地已点。"""
        ids = [str(i) for i in plugin_ids]
        async with self._lock:
            liked = await self._load_liked()
        liked_set = set(liked)
        counts, stats_ok = await self._fetch_counts()
        if not stats_ok:
            counts = {pid: _stable_fake_count(pid) for pid in ids}
        likes = {}
        for pid in ids:
            count = counts.get(pid, 0)
            if pid in liked_set:
                count = max(count, 1)
            likes[pid] = count
        return {
            "likes": likes,
            "stats_ok": stats_ok,
            "liked": {pid: pid in liked_set for pid in ids},
        }

    async def _fetch_counts(self) -> Tuple[Dict, bool]:
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(f"{self.stats_url}/likes")
            data = resp.json() if resp.status_code == 200 else {}
            counts = {}
            for k, v in data.items():
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    counts[str(k)] = int(v)
            return counts, True
        except (httpx.HTTPError, ValueError):
            _logger.warning("stats server unreachable, degraded: %s", self.stats_url)
            return {}, False

    # ── 下载上报 ──

    async def get_downloads(self, plugin_ids: List[str]) -> Dict:
        """远端成功用远端；失败降级为 0（stats_ok 标记）"""
        ids = [str(i) for i in plugin_ids]
        counts, stats_ok = await self._fetch_download_counts()
        downloads = {pid: counts.get(pid, 0) for pid in ids}
        return {"downloads": downloads, "stats_ok": stats_ok}

    async def _fetch_download_counts(self) -> Tuple[Dict, bool]:
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(f"{self.stats_url}/downloads")
            data = resp.json() if resp.status_code == 200 else {}
            counts = {}
            for k, v in data.items():
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    counts[str(k)] = int(v)
            return counts, True
        except (httpx.HTTPError, ValueError):
            _logger.warning("stats server unreachable, downloads degraded: %s", self.stats_url)
            return {}, False

    def record_download(self, plugin_id: str) -> None:
        """fire-and-forget 上报，失败仅记 debug，不阻塞调用方。"""
        task = asyncio.create_task(self._post_download(plugin_id))
        self._bg_tasks.add(task)
        task.add_done_callback(self._bg_tasks.discard)

    async def _post_download(self, plugin_id: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                await client.post(f"{self.stats_url}/downloads/{plugin_id}")
        except httpx.HTTPError:
            _logger.debug("download report failed: %s", plugin_id)


# ── 全局单例 ──
plugin_stats = PluginStats()
