"""生命周期阶段定义与转换规则"""

from enum import IntEnum


class Phase(IntEnum):
    CREATED = 0
    CONFIG_LOADED = 10
    DATABASE_READY = 20
    PLUGINS_SCANNED = 30
    PLUGINS_LOADED = 40
    BRAIN_READY = 50
    INSTANCES_READY = 60
    ADAPTERS_READY = 70
    RUNNING = 80
    STOPPING = 90
    STOPPED = 100


PHASE_META = {
    Phase.CREATED: "Initial object created, nothing initialized",
    Phase.CONFIG_LOADED: "Configuration manager finished loading",
    Phase.DATABASE_READY: "Database connection established",
    Phase.PLUGINS_SCANNED: "Plugin directories scanned, metadata collected",
    Phase.PLUGINS_LOADED: "All plugins loaded and registered",
    Phase.BRAIN_READY: "Brain module initialized (providers, keystore, persona)",
    Phase.INSTANCES_READY: "Bot instances created with pipelines",
    Phase.ADAPTERS_READY: "Adapters connected to platforms",
    Phase.RUNNING: "Fully operational, accepting messages",
    Phase.STOPPING: "Shutdown in progress",
    Phase.STOPPED: "Fully stopped, all resources released",
}


_TRANSITION_TABLE = {
    Phase.CREATED: [Phase.CONFIG_LOADED],
    Phase.CONFIG_LOADED: [Phase.DATABASE_READY],
    Phase.DATABASE_READY: [Phase.PLUGINS_SCANNED],
    Phase.PLUGINS_SCANNED: [Phase.PLUGINS_LOADED],
    Phase.PLUGINS_LOADED: [Phase.BRAIN_READY],
    Phase.BRAIN_READY: [Phase.INSTANCES_READY],
    Phase.INSTANCES_READY: [Phase.ADAPTERS_READY],
    Phase.ADAPTERS_READY: [Phase.RUNNING],
    Phase.RUNNING: [Phase.STOPPING],
    Phase.STOPPING: [Phase.STOPPED],
    Phase.STOPPED: [Phase.CREATED],
}

_FORWARD_PATH = [
    Phase.CREATED,
    Phase.CONFIG_LOADED,
    Phase.DATABASE_READY,
    Phase.PLUGINS_SCANNED,
    Phase.PLUGINS_LOADED,
    Phase.BRAIN_READY,
    Phase.INSTANCES_READY,
    Phase.ADAPTERS_READY,
    Phase.RUNNING,
]

_REVERSE_PATH = [Phase.STOPPING] + list(reversed(_FORWARD_PATH[:-1])) + [Phase.STOPPED]


def can_transition(current: Phase, target: Phase) -> bool:
    if current == Phase.STOPPED and target == Phase.CREATED:
        return True
    allowed = _TRANSITION_TABLE.get(current, [])
    return target in allowed


def is_forward(phase: Phase) -> bool:
    return phase in _FORWARD_PATH


def is_shutdown(phase: Phase) -> bool:
    return phase in (Phase.STOPPING, Phase.STOPPED)


def is_running(phase: Phase) -> bool:
    return phase == Phase.RUNNING


def get_description(phase: Phase) -> str:
    return PHASE_META.get(phase, "")


def next_forward(current: Phase) -> Phase:
    idx = _FORWARD_PATH.index(current) if current in _FORWARD_PATH else -1
    if idx >= 0 and idx + 1 < len(_FORWARD_PATH):
        return _FORWARD_PATH[idx + 1]
    raise ValueError(f"No forward phase after {current.name}")


def previous_forward(current: Phase) -> Phase:
    idx = _FORWARD_PATH.index(current) if current in _FORWARD_PATH else -1
    if idx > 0:
        return _FORWARD_PATH[idx - 1]
    raise ValueError(f"No phase before {current.name}")


def forward_range() -> list[Phase]:
    return list(_FORWARD_PATH)


def shutdown_range() -> list[Phase]:
    return list(_REVERSE_PATH)
