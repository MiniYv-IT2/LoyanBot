"""LoyanBot 组合根（Composition Root）— 轻量依赖容器

所有组件通过 Container 注册并按需（惰性）构建。
Container 不是服务定位器：业务代码不 import Container，
只在装配点（main.py 与测试）使用。

用法:
    container = build_container()
    pool = container.get("adapter_pool")

设计：
    - 手写轻量实现，不引入第三方 DI 库
    - 工厂收一个参数（Container 自身），在工厂里声明依赖
    - 惰性构建 + 缓存，get 同一组件返回同一实例（单例语义）
    - threading.Lock 保护并发构建（框架有线程场景）
"""

from __future__ import annotations

import threading
from typing import Any, Callable, Dict

# 模块级默认实例保留（兼容现有 import），类本身不自杀单例（可测试）


class Container:
    """轻量依赖容器：注册 + 惰性构建 + 持有。"""

    def __init__(self) -> None:
        self._registry: Dict[str, Callable[[Container], Any]] = {}
        self._instances: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def register(self, name: str, factory: Callable[[Container], Any]) -> None:
        """注册组件工厂，factory 收一个参数（Container 自身）。"""
        self._registry[name] = factory

    def get(self, name: str) -> Any:
        """惰性构建：首次 get 时调 factory(self) 并缓存，返回同一实例。"""
        if name not in self._instances:
            with self._lock:
                if name not in self._instances:
                    if name not in self._registry:
                        raise KeyError(f"组件未注册: {name}")
                    self._instances[name] = self._registry[name](self)
        return self._instances[name]

    def has(self, name: str) -> bool:
        """组件是否已注册。"""
        return name in self._registry

    def build(self) -> None:
        """预构建所有已注册组件（供启动时提前暴露错误）。"""
        for name in self._registry:
            self.get(name)

    def __contains__(self, name: str) -> bool:
        return self.has(name)


def build_container() -> Container:
    """构建默认容器，注册叶子组件工厂。

    叶子阶段直接返回已有模块级单例，后续逐步迁移为真构造。
    """
    from loyan.core.config_manager import config_manager
    from loyan.core.event import event_bus
    from loyan.core.logger_manager import logger_manager
    from loyan.core.loyan_adapter.pool import adapter_pool
    from loyan.core.plugin_manager import plugin_manager
    from loyan.core.runtime import RuntimeRegistry

    container = Container()
    container.register("adapter_pool", lambda _c: adapter_pool)
    container.register("event_bus", lambda _c: event_bus)
    container.register("config_manager", lambda _c: config_manager)
    container.register("runtime_registry", lambda _c: RuntimeRegistry())
    container.register("logger_manager", lambda _c: logger_manager)
    container.register("plugin_manager", lambda _c: plugin_manager)
    return container


_default_container: Container | None = None


def get_container() -> Container:
    """返回全局默认容器；未设置时惰性构建 build_container()。

    业务调用方（send.py / http_routes.py 等）通过它统一获取依赖，
    测试可用 set_container() 注入 Fake 依赖后复位。
    """
    global _default_container
    if _default_container is None:
        _default_container = build_container()
    return _default_container


def set_container(container: Container) -> None:
    """替换全局默认容器（供测试注入依赖，正常流程不调用）。"""
    global _default_container
    _default_container = container
