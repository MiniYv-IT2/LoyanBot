"""插件商店透传 — 列表 / 安装 / 更新 / 点赞"""


async def _await_maybe(result):
    import inspect
    if inspect.iscoroutine(result):
        return await result
    return result


async def store_list():
    from loyan.core.plugin_store import plugin_store
    return await _await_maybe(plugin_store.store_list())


async def store_install(plugin_id: str):
    from loyan.core.plugin_store import plugin_store
    return await _await_maybe(plugin_store.store_install(plugin_id))


async def store_update(plugin_id: str):
    from loyan.core.plugin_store import plugin_store
    return await _await_maybe(plugin_store.store_update(plugin_id))


async def store_like(plugin_id: str):
    from loyan.core.plugin_stats import plugin_stats
    return await plugin_stats.store_like(plugin_id)


__all__ = ["store_list", "store_install", "store_update", "store_like"]
