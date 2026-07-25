"""生命周期计时与钩子性能的指标收集"""

import time
import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

_logger = logging.getLogger("Core.Lifecycle.Health.Metrics")


@dataclass
class TimingRecord:
    name: str
    started_at: float
    finished_at: float
    duration: float
    success: bool
    metadata: dict = field(default_factory=dict)


class MetricsCollector:
    def __init__(self, max_history: int = 1000):
        self._records: deque[TimingRecord] = deque(maxlen=max_history)
        self._phase_times: dict[str, float] = {}
        self._start_wall: float = 0.0

    def start_wall_clock(self):
        self._start_wall = time.time()

    @property
    def wall_elapsed(self) -> float:
        if self._start_wall == 0:
            return 0.0
        return round(time.time() - self._start_wall, 2)

    def record_phase(self, phase_name: str, duration: float, success: bool):
        rec = TimingRecord(
            name=phase_name,
            started_at=time.time() - duration,
            finished_at=time.time(),
            duration=duration,
            success=success,
        )
        self._records.append(rec)
        self._phase_times[phase_name] = duration

    def record_hook(self, hook_name: str, duration: float, success: bool, meta: Optional[dict] = None):
        rec = TimingRecord(
            name=hook_name,
            started_at=time.time() - duration,
            finished_at=time.time(),
            duration=duration,
            success=success,
            metadata=meta or {},
        )
        self._records.append(rec)

    def phase_duration(self, phase_name: str) -> float:
        return self._phase_times.get(phase_name, 0.0)

    def total_phase_time(self) -> float:
        return sum(self._phase_times.values())

    def phase_summary(self) -> dict[str, float]:
        return dict(self._phase_times)

    def hook_summary(self) -> dict:
        hooks = [r for r in self._records if "hook" in r.name.lower() or r.metadata.get("type") == "hook"]
        if not hooks:
            return {"count": 0, "total_time": 0.0, "avg_time": 0.0}
        total = sum(r.duration for r in hooks)
        return {
            "count": len(hooks),
            "total_time": round(total, 4),
            "avg_time": round(total / len(hooks), 4),
            "max_time": round(max(r.duration for r in hooks), 4),
        }

    def timeline(self) -> list[dict]:
        return [
            {
                "name": r.name,
                "duration": r.duration,
                "success": r.success,
            }
            for r in self._records
        ]

    def latency_p95(self) -> float:
        durations = sorted(r.duration for r in self._records)
        if not durations:
            return 0.0
        idx = int(len(durations) * 0.95)
        return round(durations[min(idx, len(durations) - 1)], 4)

    def summary(self) -> dict:
        return {
            "wall_time": self.wall_elapsed,
            "total_phases": len(self._phase_times),
            "total_records": len(self._records),
            "phase_time": self.total_phase_time(),
            "phase_breakdown": self.phase_summary(),
            "hooks": self.hook_summary(),
            "latency_p95": self.latency_p95(),
        }

    def clear(self):
        self._records.clear()
        self._phase_times.clear()
        self._start_wall = 0.0
