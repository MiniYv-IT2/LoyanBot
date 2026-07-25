"""带转换验证的阶段状态机"""

import time
import logging
from dataclasses import dataclass, field
from typing import Optional

from .errors import PhaseTransitionError
from .phases import Phase, can_transition, get_description, is_shutdown

_logger = logging.getLogger("Core.Lifecycle.State")


@dataclass
class PhaseRecord:
    phase: Phase
    entered_at: float
    duration: float
    success: bool
    error: Optional[str] = None


class StateMachine:
    def __init__(self):
        self._current: Phase = Phase.CREATED
        self._history: list[PhaseRecord] = []
        self._frozen: bool = False
        self._started_at: float = 0.0
        self._on_enter_callbacks: dict[Phase, list[callable]] = {}
        self._on_exit_callbacks: dict[Phase, list[callable]] = {}

    @property
    def current(self) -> Phase:
        return self._current

    @property
    def history(self) -> list[PhaseRecord]:
        return list(self._history)

    @property
    def started_at(self) -> float:
        return self._started_at

    @property
    def uptime(self) -> float:
        if self._started_at == 0:
            return 0.0
        return time.time() - self._started_at

    @property
    def is_running(self) -> bool:
        return self._current == Phase.RUNNING

    @property
    def is_shutting_down(self) -> bool:
        return is_shutdown(self._current)

    def transition(self, target: Phase) -> PhaseRecord:
        if self._frozen:
            raise PhaseTransitionError(self._current, target)

        if not can_transition(self._current, target):
            raise PhaseTransitionError(self._current, target)

        entered = time.time()
        self._trigger_exit(self._current)
        old = self._current
        self._current = target
        self._trigger_enter(target)

        record = PhaseRecord(
            phase=target,
            entered_at=entered,
            duration=round(time.time() - entered, 4),
            success=True,
        )
        self._history.append(record)
        _logger.info(
            "Phase transition: %s -> %s  (%s)",
            old.name, target.name, get_description(target),
        )
        if old == Phase.CREATED and target != Phase.CREATED:
            self._started_at = entered
        return record

    def fail(self, phase: Phase, error: str) -> PhaseRecord:
        record = PhaseRecord(
            phase=phase,
            entered_at=time.time(),
            duration=0.0,
            success=False,
            error=error,
        )
        self._history.append(record)
        _logger.error("Phase failed: %s  error=%s", phase.name, error)
        return record

    def freeze(self):
        self._frozen = True

    def thaw(self):
        self._frozen = False

    def reset(self):
        self._current = Phase.CREATED
        self._history.clear()
        self._frozen = False
        self._started_at = 0.0
        _logger.info("State machine reset to CREATED")

    def on_enter(self, phase: Phase, callback: callable):
        self._on_enter_callbacks.setdefault(phase, []).append(callback)

    def on_exit(self, phase: Phase, callback: callable):
        self._on_exit_callbacks.setdefault(phase, []).append(callback)

    def _trigger_enter(self, phase: Phase):
        for cb in self._on_enter_callbacks.get(phase, []):
            try:
                cb(phase)
            except Exception as e:
                _logger.warning("on_enter callback failed for %s: %s", phase.name, e)

    def _trigger_exit(self, phase: Phase):
        for cb in self._on_exit_callbacks.get(phase, []):
            try:
                cb(phase)
            except Exception as e:
                _logger.warning("on_exit callback failed for %s: %s", phase.name, e)

    def summary(self) -> dict:
        return {
            "current": self._current.name,
            "phase_value": self._current.value,
            "uptime": round(self.uptime, 2),
            "steps": len(self._history),
            "history": [
                {
                    "phase": r.phase.name,
                    "duration": r.duration,
                    "success": r.success,
                    "error": r.error,
                }
                for r in self._history
            ],
        }
