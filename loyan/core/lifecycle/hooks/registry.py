"""带优先级排序和生命周期管理的钩子注册表"""

import time
import logging
from dataclasses import dataclass, field
from typing import Callable, Awaitable, Optional

from .events import LifecycleEvent, all_events
from ..state.errors import DuplicateHookError

_logger = logging.getLogger("Core.Lifecycle.Hooks.Registry")

HookCallback = Callable[..., Awaitable[None]]


@dataclass
class HookEntry:
    event: LifecycleEvent
    callback: HookCallback
    name: str
    priority: int = 50
    timeout: float = 30.0
    plugin_name: str = ""
    registered_at: float = 0.0
    call_count: int = 0
    fail_count: int = 0
    last_duration: Optional[float] = None
    last_error: Optional[str] = None


_HOOK_PRIORITY_EARLIEST = 0
_HOOK_PRIORITY_EARLY = 25
_HOOK_PRIORITY_NORMAL = 50
_HOOK_PRIORITY_LATE = 75
_HOOK_PRIORITY_LATEST = 100


def hook_priority(earliest: int = 0, early: int = 25, normal: int = 50,
                  late: int = 75, latest: int = 100) -> dict:
    return {
        "EARLIEST": earliest,
        "EARLY": early,
        "NORMAL": normal,
        "LATE": late,
        "LATEST": latest,
    }


class HookRegistry:
    def __init__(self):
        self._entries: list[HookEntry] = []

    @property
    def entries(self) -> list[HookEntry]:
        return list(self._entries)

    def register(
        self,
        event: LifecycleEvent,
        callback: HookCallback,
        name: str = "",
        priority: int = 50,
        timeout: float = 30.0,
        plugin_name: str = "",
    ) -> HookEntry:
        cb_name = name or getattr(callback, "__name__", str(callback))
        for existing in self._entries:
            if existing.event == event and existing.name == cb_name:
                raise DuplicateHookError(
                    f"Hook '{cb_name}' already registered for event {event.value}"
                )
        entry = HookEntry(
            event=event,
            callback=callback,
            name=cb_name,
            priority=priority,
            timeout=timeout,
            plugin_name=plugin_name,
            registered_at=time.time(),
        )
        self._entries.append(entry)
        self._entries.sort(key=lambda e: (e.event.value, e.priority, e.registered_at))
        _logger.debug(
            "Hook registered: event=%s  name=%s  priority=%d  plugin=%s",
            event.value, cb_name, priority, plugin_name or "-",
        )
        return entry

    def unregister(self, event: LifecycleEvent, callback: HookCallback = None, name: str = ""):
        cb_name = name or (getattr(callback, "__name__", "") if callback else "")
        before = len(self._entries)
        self._entries = [
            e for e in self._entries
            if not (e.event == event and (e.name == cb_name or (callback and e.callback == callback)))
        ]
        removed = before - len(self._entries)
        if removed:
            _logger.debug("Hook unregistered: event=%s  name=%s", event.value, cb_name or "*")

    def get_by_event(self, event: LifecycleEvent) -> list[HookEntry]:
        return [e for e in self._entries if e.event == event]

    def get_by_plugin(self, plugin_name: str) -> list[HookEntry]:
        return [e for e in self._entries if e.plugin_name == plugin_name]

    def count(self, event: LifecycleEvent = None) -> int:
        if event is None:
            return len(self._entries)
        return len(self.get_by_event(event))

    def clear(self):
        self._entries.clear()
        _logger.debug("Hook registry cleared")

    def summary(self) -> dict:
        groups = {}
        for e in all_events():
            hooks = self.get_by_event(e)
            if hooks:
                groups[e.value] = [
                    {
                        "name": h.name,
                        "priority": h.priority,
                        "timeout": h.timeout,
                        "plugin": h.plugin_name,
                        "calls": h.call_count,
                        "failures": h.fail_count,
                        "last_duration": h.last_duration,
                    }
                    for h in hooks
                ]
        return {
            "total_hooks": len(self._entries),
            "by_event": groups,
        }
