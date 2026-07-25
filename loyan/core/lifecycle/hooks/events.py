"""生命周期事件类型定义"""

from enum import Enum


class LifecycleEvent(str, Enum):
    BEFORE_INIT = "before_init"
    AFTER_CONFIG_LOAD = "after_config_load"
    AFTER_DATABASE_READY = "after_database_ready"
    AFTER_PLUGINS_SCANNED = "after_plugins_scanned"
    AFTER_PLUGINS_LOADED = "after_plugins_loaded"
    AFTER_BRAIN_READY = "after_brain_ready"
    AFTER_INSTANCES_READY = "after_instances_ready"
    BEFORE_ADAPTERS_START = "before_adapters_start"
    AFTER_ADAPTERS_START = "after_adapters_start"
    READY = "ready"
    BEFORE_SHUTDOWN = "before_shutdown"
    AFTER_SHUTDOWN = "after_shutdown"
    ON_ERROR = "on_error"
    ON_RESTART = "on_restart"


_EVENT_PHASE_MAP = {
    LifecycleEvent.BEFORE_INIT: None,
    LifecycleEvent.AFTER_CONFIG_LOAD: None,
    LifecycleEvent.AFTER_DATABASE_READY: None,
    LifecycleEvent.AFTER_PLUGINS_SCANNED: None,
    LifecycleEvent.AFTER_PLUGINS_LOADED: None,
    LifecycleEvent.AFTER_BRAIN_READY: None,
    LifecycleEvent.AFTER_INSTANCES_READY: None,
    LifecycleEvent.BEFORE_ADAPTERS_START: None,
    LifecycleEvent.AFTER_ADAPTERS_START: None,
    LifecycleEvent.READY: None,
    LifecycleEvent.BEFORE_SHUTDOWN: None,
    LifecycleEvent.AFTER_SHUTDOWN: None,
    LifecycleEvent.ON_ERROR: None,
    LifecycleEvent.ON_RESTART: None,
}


_STARTUP_EVENTS = [
    LifecycleEvent.BEFORE_INIT,
    LifecycleEvent.AFTER_CONFIG_LOAD,
    LifecycleEvent.AFTER_DATABASE_READY,
    LifecycleEvent.AFTER_PLUGINS_SCANNED,
    LifecycleEvent.AFTER_PLUGINS_LOADED,
    LifecycleEvent.AFTER_BRAIN_READY,
    LifecycleEvent.AFTER_INSTANCES_READY,
    LifecycleEvent.BEFORE_ADAPTERS_START,
    LifecycleEvent.AFTER_ADAPTERS_START,
    LifecycleEvent.READY,
]

_SHUTDOWN_EVENTS = [
    LifecycleEvent.BEFORE_SHUTDOWN,
    LifecycleEvent.AFTER_SHUTDOWN,
]


def startup_events() -> list[LifecycleEvent]:
    return list(_STARTUP_EVENTS)


def shutdown_events() -> list[LifecycleEvent]:
    return list(_SHUTDOWN_EVENTS)


def all_events() -> list[LifecycleEvent]:
    return list(LifecycleEvent)


def event_label(event: LifecycleEvent) -> str:
    labels = {
        LifecycleEvent.BEFORE_INIT: "before init",
        LifecycleEvent.AFTER_CONFIG_LOAD: "config loaded",
        LifecycleEvent.AFTER_DATABASE_READY: "database ready",
        LifecycleEvent.AFTER_PLUGINS_SCANNED: "plugins scanned",
        LifecycleEvent.AFTER_PLUGINS_LOADED: "plugins loaded",
        LifecycleEvent.AFTER_BRAIN_READY: "brain ready",
        LifecycleEvent.AFTER_INSTANCES_READY: "instances ready",
        LifecycleEvent.BEFORE_ADAPTERS_START: "before adapters start",
        LifecycleEvent.AFTER_ADAPTERS_START: "adapters started",
        LifecycleEvent.READY: "ready",
        LifecycleEvent.BEFORE_SHUTDOWN: "before shutdown",
        LifecycleEvent.AFTER_SHUTDOWN: "after shutdown",
        LifecycleEvent.ON_ERROR: "on error",
        LifecycleEvent.ON_RESTART: "on restart",
    }
    return labels.get(event, event.value)
