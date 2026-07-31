"""Provider 实例管理器 — SQLite CRUD，api_key 经 keystore 加密存储，支持配置迁移"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

from loyan.core.db_manager import get_db
from loyan.brain.provider.keystore import keystore
from loyan.brain.provider.paths import get_schemas_dir

_logger = logging.getLogger("Brain.provider.instance")


class InstanceManager:
    def __init__(self):
        self._db = None

    async def init(self):
        self._db = await get_db("provider_instances")
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS provider_instances (
                id       TEXT PRIMARY KEY,
                type     TEXT NOT NULL,
                model    TEXT DEFAULT '',
                api_base TEXT DEFAULT '',
                api_key  TEXT DEFAULT '',
                extra    TEXT DEFAULT '{}',
                enabled  INTEGER DEFAULT 1
            )
        """)
        _logger.debug("Instance manager initialized")

    async def _ensure(self):
        if self._db is None:
            await self.init()

    # ── 加密 / 解密 api_key ──

    async def _encrypt_key(self, plain: str) -> str:
        if not plain:
            return ""
        try:
            return keystore.encrypt(plain)
        except Exception:
            return plain

    async def _decrypt_key(self, cipher: str) -> str:
        if not cipher:
            return ""
        try:
            return keystore.decrypt(cipher)
        except Exception:
            return cipher

    # ── CRUD ──

    async def list(self) -> list[dict]:
        await self._ensure()
        rows = await self._db.fetchall(
            "SELECT id, type, model, api_base, api_key, extra, enabled "
            "FROM provider_instances ORDER BY type, id",
        )
        return [await self._row_to_dict(r) for r in rows]

    async def get(self, instance_id: str) -> Optional[dict]:
        await self._ensure()
        row = await self._db.fetchone(
            "SELECT id, type, model, api_base, api_key, extra, enabled "
            "FROM provider_instances WHERE id = ?",
            instance_id,
        )
        return await self._row_to_dict(row) if row else None

    async def add(self, data: dict) -> str:
        await self._ensure()
        inst_id = data.get("id", "").strip()
        if not inst_id:
            raise ValueError("id is required")
        api_key = await self._encrypt_key(data.get("api_key", ""))
        extra_json = json.dumps(data.get("extra", {}), ensure_ascii=False)
        await self._db.execute(
            "INSERT INTO provider_instances "
            "(id, type, model, api_base, api_key, extra, enabled) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            inst_id, data.get("type", ""), data.get("model", ""),
            data.get("api_base", ""), api_key, extra_json,
            1 if data.get("enabled", True) else 0,
        )
        _logger.info("Added provider instance: %s (%s)", inst_id, data.get("type"))
        return inst_id

    async def update(self, instance_id: str, data: dict):
        await self._ensure()
        fields = []
        values = []
        for key in ("type", "model", "api_base", "enabled"):
            if key in data:
                fields.append(f"{key} = ?")
                values.append(data[key])
        if "api_key" in data:
            fields.append("api_key = ?")
            values.append(await self._encrypt_key(data["api_key"]))
        if "extra" in data:
            fields.append("extra = ?")
            values.append(json.dumps(data["extra"], ensure_ascii=False))
        if not fields:
            return
        values.append(instance_id)
        await self._db.execute(
            f"UPDATE provider_instances SET {', '.join(fields)} WHERE id = ?",
            *values,
        )
        _logger.info("Updated provider instance: %s", instance_id)

    async def delete(self, instance_id: str):
        await self._ensure()
        await self._db.execute(
            "DELETE FROM provider_instances WHERE id = ?", instance_id,
        )

    async def get_by_type(self, provider_type: str) -> list[dict]:
        await self._ensure()
        rows = await self._db.fetchall(
            "SELECT id, type, model, api_base, api_key, extra, enabled "
            "FROM provider_instances WHERE type = ? ORDER BY id",
            provider_type,
        )
        return [await self._row_to_dict(r) for r in rows]

    async def _row_to_dict(self, row) -> dict:
        api_key = await self._decrypt_key(row[4] or "")
        return {
            "id": row[0],
            "type": row[1],
            "model": row[2] or "",
            "api_base": row[3] or "",
            "api_key": api_key,
            "extra": json.loads(row[5]) if row[5] else {},
            "enabled": bool(row[6]),
        }

    async def clear(self):
        await self._ensure()
        await self._db.execute("DELETE FROM provider_instances")

    # ── 从旧 provider_{name}.json 迁移 ──

    async def migrate_from_config(self, schemas_dir: Optional[str] = None):
        schemas_dir = schemas_dir or get_schemas_dir()
        if not os.path.isdir(schemas_dir):
            return

        from loyan.core.tools.paths import get_plugin_config_global_dir

        migrated = 0
        for fname in sorted(os.listdir(schemas_dir)):
            if not fname.endswith(".schema_conf.json"):
                continue
            ptype = fname.replace(".schema_conf.json", "")
            cfg_path = os.path.join(get_plugin_config_global_dir(), f"provider_{ptype}", "config.json")
            if not os.path.isfile(cfg_path):
                _logger.debug("No config file for %s, skip", ptype)
                continue

            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            if not cfg.get("api_key"):
                _logger.debug("No api_key in %s config, skip", ptype)
                continue

            inst_id = cfg.get("id", ptype)
            existing = await self.get(inst_id)
            if existing:
                _logger.debug("Instance %s already exists, skip", inst_id)
                continue

            await self.add({
                "id": inst_id,
                "type": ptype,
                "model": cfg.get("model", ""),
                "api_base": cfg.get("api_base", ""),
                "api_key": cfg.get("api_key", ""),
                "extra": {k: v for k, v in cfg.items()
                          if k not in ("id", "type", "model", "api_base", "api_key", "enabled")},
            })
            _logger.info("Migrated %s -> instance '%s'", fname, inst_id)
            migrated += 1

        if migrated:
            _logger.info("Migration complete: %d instances created", migrated)
        else:
            _logger.debug("No configs to migrate")
