"""ProviderManager — 提供商类型注册、实例加载、生命周期、模型管理"""

import importlib
import json
import logging
import os
import pkgutil
from typing import Optional

from loyan.brain.provider.base import BaseProvider, _registry
from loyan.brain.provider.keystore import keystore
from loyan.brain.provider.paths import get_schemas_dir, get_types_dir
from loyan.brain.provider.router.circuit import CircuitBreaker
from loyan.brain.provider.types.instance import InstanceManager

_logger = logging.getLogger("Brain.provider")


class ProviderManager:
    def __init__(self):
        self._providers: dict[str, BaseProvider] = {}
        self._default: Optional[str] = None
        self._circuits: dict[str, CircuitBreaker] = {}
        self._instances = InstanceManager()

    @property
    def registry(self) -> dict[str, BaseProvider]:
        return dict(self._providers)

    @property
    def instance_manager(self) -> InstanceManager:
        return self._instances

    async def load_all(self):
        self._auto_discover()
        await self._instances.init()
        await self._instances.migrate_from_config()

        for row in await self._instances.list():
            inst_id = row["id"]
            if not row.get("enabled", True):
                _logger.debug("Skipping disabled provider: %s", inst_id)
                continue
            cls = _registry.get(row["type"])
            if not cls:
                _logger.warning(
                    "Unknown provider type '%s' for instance '%s', skipping",
                    row["type"], inst_id,
                )
                continue
            try:
                cfg = {
                    "id": row["id"],
                    "type": row["type"],
                    "model": row.get("model", ""),
                    "api_base": row.get("api_base", ""),
                    "api_key": row.get("api_key", ""),
                    **row.get("extra", {}),
                }
                prov = cls(cfg)
                await prov.open()
                self._providers[inst_id] = prov
                self._circuits[inst_id] = CircuitBreaker(inst_id)
                _logger.info("Loaded provider: %s (%s)", inst_id, row["type"])
            except Exception as e:
                _logger.warning("Skipped provider '%s': %s", inst_id, e)

        if not self._default and self._providers:
            self._default = next(iter(self._providers))

    def _auto_discover(self):
        pkg_path = get_types_dir()
        for imp, name, _ in pkgutil.iter_modules([pkg_path]):
            if name == "instance":
                continue
            try:
                importlib.import_module(f"loyan.brain.provider.types.{name}")
                _logger.debug("Discovered provider type: %s", name)
            except Exception as e:
                _logger.warning("Skipping provider type '%s': %s", name, e)

    def get(self, instance_id: Optional[str] = None) -> Optional[BaseProvider]:
        instance_id = instance_id or self._default
        return self._providers.get(instance_id)

    async def close_all(self):
        for inst_id, prov in self._providers.items():
            try:
                await prov.close()
            except Exception:
                pass
        self._providers.clear()

    # ── 模型管理 ──

    async def get_models(self, instance_id: str) -> list[str]:
        inst = self.get(instance_id)
        if not inst:
            return []
        models = await inst.list_models()
        disabled = await self._load_disabled(instance_id)
        return [m for m in models if m not in disabled]

    async def enable_model(self, instance_id: str, model: str):
        disabled = await self._load_disabled(instance_id)
        if model in disabled:
            disabled.remove(model)
            await self._save_disabled(instance_id, disabled)

    async def disable_model(self, instance_id: str, model: str):
        disabled = await self._load_disabled(instance_id)
        if model not in disabled:
            disabled.append(model)
            await self._save_disabled(instance_id, disabled)

    async def add_custom_model(self, instance_id: str, model: str):
        custom = await self._load_custom(instance_id)
        if model not in custom:
            custom.append(model)
            await self._save_custom(instance_id, custom)

    async def remove_custom_model(self, instance_id: str, model: str):
        custom = await self._load_custom(instance_id)
        if model in custom:
            custom.remove(model)
            await self._save_custom(instance_id, custom)

    async def _load_disabled(self, instance_id: str) -> list[str]:
        raw = await keystore.get(f"{instance_id}.disabled_models")
        return json.loads(raw) if raw else []

    async def _save_disabled(self, instance_id: str, models: list[str]):
        await keystore.set(f"{instance_id}.disabled_models", json.dumps(models))

    async def _load_custom(self, instance_id: str) -> list[str]:
        raw = await keystore.get(f"{instance_id}.custom_models")
        return json.loads(raw) if raw else []

    async def _save_custom(self, instance_id: str, models: list[str]):
        await keystore.set(f"{instance_id}.custom_models", json.dumps(models))

    # ── 用量统计 ──

    async def get_usage_summary(self, hours: int = 24) -> dict:
        from loyan.brain.provider.monitor.stats import stats as _stats
        return await _stats.summary(hours=hours)
