from loyan.brain import get_brain
from loyan.brain.chat.engine import ChatEngine
from loyan.brain.provider.manager import ProviderManager
from loyan.brain.provider.types.instance import InstanceManager
from loyan.brain.provider.monitor.stats import stats as usage_stats
from loyan.brain.provider.base import _registry as _provider_registry
from loyan.brain.provider.types.litellm import list_vendors

def list_provider_types():
    return list(_provider_registry.keys())

def list_vendor_types():
    return list_vendors()


def _provider_mgr():
    from loyan.brain import get_brain
    return get_brain().provider


async def list_providers():
    return await _provider_mgr().instance_manager.list()


async def add_provider(data: dict) -> str:
    return await _provider_mgr().instance_manager.add(data)


async def update_provider(instance_id: str, data: dict):
    return await _provider_mgr().instance_manager.update(instance_id, data)


async def delete_provider(instance_id: str):
    return await _provider_mgr().instance_manager.delete(instance_id)


async def list_models(instance_id: str) -> list:
    return await _provider_mgr().get_models(instance_id)


async def get_usage_summary(hours: int = 24) -> dict:
    return await _provider_mgr().get_usage_summary(hours=hours)


__all__ = [
    "get_brain",
    "ChatEngine",
    "ProviderManager",
    "InstanceManager",
    "usage_stats",
    "list_provider_types",
    "list_vendor_types",
    "list_providers",
    "add_provider",
    "update_provider",
    "delete_provider",
    "list_models",
    "get_usage_summary",
]
