"""UpdateManager — 机器人本体更新（检查/下载/校验/解压覆盖/回滚）

更新包格式（GitHub Release asset）:
    loyan-update-{version}.tar.gz      — loyan/ + updates/ + requirements.txt
    loyan-update-{version}.tar.gz.sha256 — SHA256 校验和（强制校验，不匹配拒绝更新）

安全:
    - 下载后强制 SHA256 校验，校验失败不执行任何覆盖
    - 解压前校验包内路径（拒绝绝对路径/../ 穿越）
    - 覆盖前备份当前 loyan/，失败可回滚
    - storage/（配置/实例/插件/数据）永不触碰
"""

import hashlib
import json
import logging
import os
import shutil
import tarfile
import tempfile
from typing import Optional

import httpx

from loyan import __version__ as CURRENT_VERSION

_logger = logging.getLogger("Core.Update")

# GitHub Releases API（可被配置 update_url 覆盖，支持镜像/代理）
DEFAULT_RELEASE_API = "https://api.github.com/repos/MiniYv-IT2/LoyanBot/releases/latest"

# 备份保留数量
_BACKUP_KEEP = 3


def _version_gt(v1: str, v2: str) -> bool:
    from loyan.core.plugin_manager import plugin_manager
    return plugin_manager.compare_versions(v1 or "0", v2 or "0") > 0


def _is_pip_install() -> bool:
    """是否 pip 安装（loyan 在 site-packages 而非项目源码目录）"""
    import loyan
    pkg_dir = os.path.dirname(os.path.abspath(loyan.__file__))
    return "site-packages" in pkg_dir or "dist-packages" in pkg_dir


class UpdateManager:
    def __init__(self, release_api: str = ""):
        self._release_api = release_api or DEFAULT_RELEASE_API
        self._http = None

    # ── HTTP ──

    async def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=15, follow_redirects=True)
        return self._http

    async def close(self):
        if self._http is not None:
            await self._http.aclose()
            self._http = None

    # ── 检查更新 ──

    async def check(self) -> dict:
        """查询最新版本，返回 {available, current, latest, changelog}"""
        try:
            client = await self._client()
            resp = await client.get(self._release_api, headers={"Accept": "application/vnd.github+json"})
            if resp.status_code != 200:
                return {"available": False, "error": f"HTTP {resp.status_code}"}
            data = resp.json()
            latest = (data.get("tag_name") or "").lstrip("v")
            changelog = data.get("body") or ""
            return {
                "available": _version_gt(latest, CURRENT_VERSION),
                "current": CURRENT_VERSION,
                "latest": latest,
                "changelog": changelog,
                "assets": [a.get("name") for a in data.get("assets", [])],
            }
        except Exception as e:
            return {"available": False, "error": f"{type(e).__name__}: {str(e)[:100]}"}

    def _asset_url(self, release: dict, name: str) -> Optional[str]:
        for a in release.get("assets", []):
            if a.get("name") == name:
                return a.get("browser_download_url")
        return None

    async def _fetch(self, url: str, dest: str) -> bool:
        try:
            client = await self._client()
            async with client.stream("GET", url) as resp:
                if resp.status_code != 200:
                    _logger.error("download failed: HTTP %s (%s)", resp.status_code, url)
                    return False
                with open(dest, "wb") as f:
                    async for chunk in resp.aiter_bytes():
                        f.write(chunk)
            return True
        except Exception as e:
            _logger.error("download failed: %s", e)
            return False

    # ── 校验 ──

    @staticmethod
    def _sha256(path: str) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def _safe_members(tar: tarfile.TarFile):
        """拒绝绝对路径与 .. 穿越成员"""
        for m in tar.getmembers():
            name = m.name
            if name.startswith("/") or ".." in name.split("/"):
                raise ValueError(f"unsafe path in update package: {name}")
            yield m

    # ── 应用更新 ──

    async def apply(self) -> dict:
        """下载 → SHA256 校验 → 备份 → 解压覆盖项目根（storage/ 永不触碰）

        源码部署：更新包为完整项目树，覆盖整个项目根（排除 storage/）。
        pip 安装形态：提示走 pip install -U，不执行解压覆盖。
        校验失败/下载失败/解压异常 → 中止，不执行任何覆盖。
        """
        if _is_pip_install():
            return {
                "success": False,
                "message": "pip installed, use `pip install -U loyan` (or `uv pip install -U loyan`)",
                "pip": True,
            }

        info = await self.check()
        if not info.get("available"):
            return {"success": False, "message": info.get("error") or "no update available"}

        release = None
        try:
            client = await self._client()
            resp = await client.get(self._release_api, headers={"Accept": "application/vnd.github+json"})
            release = resp.json()
        except Exception as e:
            return {"success": False, "message": f"{type(e).__name__}: {str(e)[:100]}"}

        latest = (release.get("tag_name") or "").lstrip("v")
        tar_name = f"loyan-update-{latest}.tar.gz"
        sha_name = tar_name + ".sha256"
        tar_url = self._asset_url(release, tar_name)
        sha_url = self._asset_url(release, sha_name)
        if not tar_url or not sha_url:
            return {"success": False, "message": f"update assets missing ({tar_name})"}

        tmp = tempfile.mkdtemp(prefix="loyan_update_")
        tar_path = os.path.join(tmp, tar_name)
        sha_path = os.path.join(tmp, sha_name)
        try:
            # 下载 + 强制 SHA256 校验
            if not await self._fetch(tar_url, tar_path):
                return {"success": False, "message": "download failed"}
            if not await self._fetch(sha_url, sha_path):
                return {"success": False, "message": "checksum file missing"}
            with open(sha_path, "r") as f:
                expected = (f.read().strip().split()[0] or "").lower()
            actual = self._sha256(tar_path)
            if not expected or actual != expected:
                _logger.error("checksum mismatch: expected %s, got %s", expected, actual)
                return {"success": False, "message": "checksum mismatch, update package corrupted"}

            # 解压到临时目录（路径安全校验）
            extract_dir = os.path.join(tmp, "extracted")
            os.makedirs(extract_dir, exist_ok=True)
            with tarfile.open(tar_path, "r:gz") as tar:
                tar.extractall(extract_dir, members=self._safe_members(tar))

            # 项目根：源码部署 = loyan/ 的父目录
            import loyan
            pkg_dir = os.path.dirname(os.path.abspath(loyan.__file__))
            project_root = os.path.dirname(pkg_dir)

            # 校验包内容：必须有 loyan/；不应包含 storage/
            if not os.path.isdir(os.path.join(extract_dir, "loyan")):
                return {"success": False, "message": "invalid package: loyan/ missing"}
            if os.path.isdir(os.path.join(extract_dir, "storage")):
                return {"success": False, "message": "invalid package: storage/ must not be shipped"}

            # 备份当前项目根（排除运行数据/环境）
            backup_dir = os.path.join(project_root, "storage", "backups", "loyan")
            os.makedirs(backup_dir, exist_ok=True)
            backup_name = f"loyan-{CURRENT_VERSION}.tar.gz"
            backup_path = os.path.join(backup_dir, backup_name)
            if not os.path.exists(backup_path):
                self._backup_project(project_root, backup_path)
                _logger.info("backup created: %s", backup_path)
            self._prune_backups(backup_dir)

            # 覆盖整个项目根（storage/ 跳过——包内已确认不含，且备份目录在 storage 下不受影响）
            for entry in os.listdir(extract_dir):
                s = os.path.join(extract_dir, entry)
                d = os.path.join(project_root, entry)
                if os.path.isdir(s):
                    shutil.rmtree(d, ignore_errors=True)
                    shutil.copytree(s, d)
                else:
                    os.makedirs(os.path.dirname(d), exist_ok=True)
                    shutil.copy2(s, d)

            _logger.info("update applied: %s -> %s", CURRENT_VERSION, latest)
            return {"success": True, "message": f"updated to v{latest}, restart required", "version": latest}
        except Exception as e:
            _logger.error("update failed: %s", e)
            return {"success": False, "message": f"{type(e).__name__}: {str(e)[:120]}"}
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    @staticmethod
    def _backup_project(project_root: str, dest: str):
        """备份项目根（排除运行数据/环境目录）"""
        excludes = {
            "storage", ".venv", "venv", "node_modules", "__pycache__",
            ".git", ".pytest_cache", ".idea", ".vscode", ".env", "dist", "build",
        }
        with tarfile.open(dest, "w:gz") as tar:
            for entry in sorted(os.listdir(project_root)):
                if entry in excludes:
                    continue
                path = os.path.join(project_root, entry)
                tar.add(path, arcname=entry, filter=UpdateManager._tar_filter)

    @staticmethod
    def _tar_filter(info):
        name = info.name
        if any(seg in ("__pycache__", ".git", "node_modules", ".venv", "venv") for seg in name.split("/")):
            return None
        return info

    def _prune_backups(self, backup_dir: str):
        backups = sorted(
            (f for f in os.listdir(backup_dir) if f.endswith(".tar.gz")),
            reverse=True,
        )
        for old in backups[_BACKUP_KEEP:]:
            try:
                os.remove(os.path.join(backup_dir, old))
            except OSError:
                pass

    # ── 回滚 ──

    def rollback(self) -> dict:
        """从备份恢复最近一个版本"""
        import loyan
        pkg_dir = os.path.dirname(os.path.abspath(loyan.__file__))
        project_root = os.path.dirname(pkg_dir)
        backup_dir = os.path.join(project_root, "storage", "backups", "loyan")
        backups = sorted((f for f in os.listdir(backup_dir) if f.endswith(".tar.gz")), reverse=True)
        if not backups:
            return {"success": False, "message": "no backup available"}
        latest_backup = backups[0]
        tmp = tempfile.mkdtemp(prefix="loyan_rollback_")
        try:
            with tarfile.open(os.path.join(backup_dir, latest_backup), "r:gz") as tar:
                tar.extractall(tmp, members=self._safe_members(tar))
            src = os.path.join(tmp, "loyan")
            for entry in os.listdir(src):
                s = os.path.join(src, entry)
                d = os.path.join(pkg_dir, entry)
                if os.path.isdir(s):
                    shutil.rmtree(d, ignore_errors=True)
                    shutil.copytree(s, d)
                else:
                    os.makedirs(os.path.dirname(d), exist_ok=True)
                    shutil.copy2(s, d)
            _logger.info("rollback done: %s", latest_backup)
            return {"success": True, "message": f"rolled back from {latest_backup}, restart required"}
        except Exception as e:
            return {"success": False, "message": f"{type(e).__name__}: {str(e)[:120]}"}
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


update_manager = UpdateManager()
