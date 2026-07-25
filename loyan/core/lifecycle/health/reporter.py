"""从生命周期状态生成健康报告并持久化到 storage/health/"""

import json
import os
import time
import logging
from datetime import datetime
from typing import Optional

from ..state.state_machine import StateMachine
from ..hooks.registry import HookRegistry
from ..hooks.executor import HookExecutor
from .metrics import MetricsCollector

_logger = logging.getLogger("Core.Lifecycle.Health.Reporter")

_HEALTH_DIR = "storage/health"
_LATEST_JSON = "latest.json"
_LATEST_TXT = "latest.txt"


class HealthReporter:
    def __init__(
        self,
        state_machine: StateMachine,
        hook_registry: HookRegistry,
        hook_executor: HookExecutor,
        metrics: MetricsCollector,
    ):
        self._state = state_machine
        self._registry = hook_registry
        self._executor = hook_executor
        self._metrics = metrics
        self._extra_checks: dict[str, callable] = {}
        self._save_dir: str = _HEALTH_DIR
        self._auto_save: bool = False
        os.makedirs(self._save_dir, exist_ok=True)

    def register_check(self, name: str, check_fn: callable):
        self._extra_checks[name] = check_fn

    def unregister_check(self, name: str):
        self._extra_checks.pop(name, None)

    @property
    def save_dir(self) -> str:
        return self._save_dir

    @save_dir.setter
    def save_dir(self, path: str):
        self._save_dir = path

    @property
    def auto_save(self) -> bool:
        return self._auto_save

    @auto_save.setter
    def auto_save(self, enabled: bool):
        self._auto_save = enabled

    def generate(self) -> dict:
        state_summary = self._state.summary()
        hook_summary = self._registry.summary()
        metrics_summary = self._metrics.summary()
        executor_results = self._executor.results()

        component_status = self._check_components()
        all_ok = all(v.get("ok", True) for v in component_status.values())

        report = {
            "status": "healthy" if all_ok else "degraded",
            "overall_ok": all_ok,
            "uptime": state_summary["uptime"],
            "wall_time": metrics_summary["wall_time"],
            "phase": state_summary["current"],
            "phase_value": state_summary["phase_value"],
            "phases_passed": state_summary["steps"],
            "phase_history": [
                {
                    "phase": h["phase"],
                    "duration": h["duration"],
                    "success": h["success"],
                    "error": h.get("error"),
                }
                for h in state_summary.get("history", [])
            ],
            "phase_timing": metrics_summary["phase_breakdown"],
            "hooks": {
                "registered": hook_summary["total_hooks"],
                "by_event": hook_summary.get("by_event", {}),
                "performance": metrics_summary["hooks"],
            },
            "executor_results": executor_results,
            "components": component_status,
            "latency_p95": metrics_summary["latency_p95"],
            "generated_at": time.time(),
            "generated_at_iso": datetime.now().isoformat(),
        }

        if self._auto_save:
            self.save(report)

        return report

    def _check_components(self) -> dict[str, dict]:
        status = {}
        for name, check_fn in self._extra_checks.items():
            try:
                result = check_fn()
                if isinstance(result, dict):
                    status[name] = result
                else:
                    status[name] = {"ok": bool(result), "detail": str(result)}
            except Exception as e:
                status[name] = {"ok": False, "error": str(e)}
        status["state_machine"] = {
            "ok": self._state.current.value >= 0,
            "phase": self._state.current.name,
            "phase_value": self._state.current.value,
            "is_running": self._state.is_running,
        }
        return status

    def text_summary(self, report: Optional[dict] = None) -> str:
        if report is None:
            report = self.generate()
        lines = [
            f"Lifecycle Health Report",
            f"{'=' * 40}",
            f"Status:      {report['status']}",
            f"Phase:       {report['phase']}",
            f"Uptime:      {report['uptime']}s",
            f"Wall time:   {report['wall_time']}s",
            f"Phases done: {report['phases_passed']}",
            f"Hooks reg:   {report['hooks']['registered']}",
            f"Latency P95: {report['latency_p95']}s",
            f"Components:  {sum(1 for v in report['components'].values() if v.get('ok'))}/"
            f"{len(report['components'])} ok",
        ]
        for name, c in report["components"].items():
            ok = "OK" if c.get("ok") else "FAIL"
            err = f"  ({c.get('error', '')})" if c.get("error") else ""
            lines.append(f"  [{ok}] {name}{err}")
        lines.append(f"\nGenerated: {report['generated_at_iso']}")
        return "\n".join(lines)

    def save(self, report: Optional[dict] = None):
        if report is None:
            report = self.generate()
        os.makedirs(self._save_dir, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = os.path.join(self._save_dir, f"report_{ts}.json")
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            _logger.debug("Health report saved: %s", json_path)
        except Exception as e:
            _logger.warning("Failed to save health report JSON: %s", e)

        latest_json = os.path.join(self._save_dir, _LATEST_JSON)
        try:
            with open(latest_json, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
        except Exception as e:
            _logger.warning("Failed to save latest health report: %s", e)

        latest_txt = os.path.join(self._save_dir, _LATEST_TXT)
        try:
            txt = self.text_summary(report=report)
            with open(latest_txt, "w", encoding="utf-8") as f:
                f.write(txt)
        except Exception as e:
            _logger.warning("Failed to save health report text: %s", e)

    def load_latest(self) -> Optional[dict]:
        path = os.path.join(self._save_dir, _LATEST_JSON)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            _logger.warning("Failed to load latest health report: %s", e)
            return None

    def list_reports(self, max_count: int = 10) -> list[dict]:
        if not os.path.isdir(self._save_dir):
            return []
        reports = []
        try:
            for fname in sorted(os.listdir(self._save_dir), reverse=True):
                if fname.startswith("report_") and fname.endswith(".json"):
                    fpath = os.path.join(self._save_dir, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            reports.append({
                                "file": fname,
                                "time": data.get("generated_at_iso", ""),
                                "status": data.get("status", ""),
                                "phase": data.get("phase", ""),
                            })
                    except Exception:
                        continue
                    if len(reports) >= max_count:
                        break
        except Exception as e:
            _logger.warning("Failed to list health reports: %s", e)
        return reports

    def reset(self):
        self._extra_checks.clear()
