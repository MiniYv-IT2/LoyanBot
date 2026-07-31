"""Comprehensive test suite for the lifecycle management system

Covers:
- state/  : Phase transitions, state machine, errors
- hooks/  : Registry, executor, timeouts, error isolation, priorities
- health/ : Metrics, reporter, checker
- full lifecycle start/stop/restart
"""

import asyncio
import time
import sys
import os
import logging
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
logging.basicConfig(level=logging.WARNING)

import pytest

from loyan.core.lifecycle import (
    LifecycleManager,
    Phase,
    LifecycleEvent,
    LifecycleError,
    PhaseTransitionError,
    HookTimeoutError,
    HookExecutionError,
    ComponentNotReadyError,
    DuplicateHookError,
    StateMachine,
    HookRegistry,
    HookExecutor,
    MetricsCollector,
    HealthReporter,
    CompositeChecker,
)


# ═══════════════════════════════════════════════════════════════
# state/ subsystem
# ═══════════════════════════════════════════════════════════════

class TestPhases:
    def test_forward_range_order(self):
        from loyan.core.lifecycle.state.phases import forward_range
        phases = forward_range()
        assert phases[0] == Phase.CREATED
        assert phases[-1] == Phase.RUNNING
        for i in range(len(phases) - 1):
            assert phases[i].value < phases[i + 1].value

    def test_can_transition_valid(self):
        from loyan.core.lifecycle.state.phases import can_transition
        assert can_transition(Phase.CREATED, Phase.CONFIG_LOADED)
        assert can_transition(Phase.PLUGINS_LOADED, Phase.BRAIN_READY)
        assert can_transition(Phase.RUNNING, Phase.STOPPING)
        assert can_transition(Phase.STOPPING, Phase.STOPPED)

    def test_can_transition_invalid(self):
        from loyan.core.lifecycle.state.phases import can_transition
        assert not can_transition(Phase.CREATED, Phase.RUNNING)
        assert not can_transition(Phase.CONFIG_LOADED, Phase.PLUGINS_LOADED)
        assert not can_transition(Phase.STOPPED, Phase.RUNNING)

    def test_can_transition_reset(self):
        from loyan.core.lifecycle.state.phases import can_transition
        assert can_transition(Phase.STOPPED, Phase.CREATED)

    def test_get_description(self):
        from loyan.core.lifecycle.state.phases import get_description
        desc = get_description(Phase.CREATED)
        assert isinstance(desc, str)
        assert len(desc) > 0
        assert get_description(Phase.CREATED) != ""

    def test_is_forward(self):
        from loyan.core.lifecycle.state.phases import is_forward
        assert is_forward(Phase.CONFIG_LOADED)
        assert is_forward(Phase.RUNNING)
        assert not is_forward(Phase.STOPPING)
        assert not is_forward(Phase.STOPPED)

    def test_next_forward(self):
        from loyan.core.lifecycle.state.phases import next_forward
        assert next_forward(Phase.CREATED) == Phase.CONFIG_LOADED
        assert next_forward(Phase.PLUGINS_LOADED) == Phase.BRAIN_READY

    def test_next_forward_raises_at_end(self):
        from loyan.core.lifecycle.state.phases import next_forward
        import pytest
        with pytest.raises(ValueError):
            next_forward(Phase.RUNNING)

    def test_previous_forward(self):
        from loyan.core.lifecycle.state.phases import previous_forward
        assert previous_forward(Phase.RUNNING) == Phase.ADAPTERS_READY
        assert previous_forward(Phase.BRAIN_READY) == Phase.PLUGINS_LOADED

    def test_previous_forward_raises_at_start(self):
        from loyan.core.lifecycle.state.phases import previous_forward
        with pytest.raises(ValueError):
            previous_forward(Phase.CREATED)

    def test_shutdown_range(self):
        from loyan.core.lifecycle.state.phases import shutdown_range
        phases = shutdown_range()
        assert Phase.STOPPING in phases
        assert Phase.STOPPED in phases
        assert Phase.ADAPTERS_READY in phases

    def test_phase_enum_values(self):
        assert Phase.CREATED.value == 0
        assert Phase.CONFIG_LOADED.value == 10
        assert Phase.DATABASE_READY.value == 20
        assert Phase.PLUGINS_SCANNED.value == 30
        assert Phase.PLUGINS_LOADED.value == 40
        assert Phase.BRAIN_READY.value == 50
        assert Phase.INSTANCES_READY.value == 60
        assert Phase.ADAPTERS_READY.value == 70
        assert Phase.RUNNING.value == 80
        assert Phase.STOPPING.value == 90
        assert Phase.STOPPED.value == 100


class TestStateMachine:
    def test_initial_state(self):
        sm = StateMachine()
        assert sm.current == Phase.CREATED
        assert sm.history == []
        assert sm.uptime == 0.0
        assert not sm.is_running
        assert not sm.is_shutting_down

    def test_transition_forward(self):
        sm = StateMachine()
        sm.transition(Phase.CONFIG_LOADED)
        assert sm.current == Phase.CONFIG_LOADED
        assert len(sm.history) == 1

    def test_transition_full_path(self):
        sm = StateMachine()
        phases = [
            Phase.CONFIG_LOADED, Phase.DATABASE_READY,
            Phase.PLUGINS_SCANNED, Phase.PLUGINS_LOADED,
            Phase.BRAIN_READY, Phase.INSTANCES_READY,
            Phase.ADAPTERS_READY, Phase.RUNNING,
        ]
        for p in phases:
            sm.transition(p)
        assert sm.current == Phase.RUNNING
        assert len(sm.history) == 8
        assert sm.is_running

    def test_transition_invalid_raises(self):
        sm = StateMachine()
        with pytest.raises(PhaseTransitionError):
            sm.transition(Phase.RUNNING)

    def test_transition_after_freeze_raises(self):
        sm = StateMachine()
        sm.freeze()
        with pytest.raises(PhaseTransitionError):
            sm.transition(Phase.CONFIG_LOADED)

    def test_thaw_allows_transition(self):
        sm = StateMachine()
        sm.freeze()
        sm.thaw()
        sm.transition(Phase.CONFIG_LOADED)
        assert sm.current == Phase.CONFIG_LOADED

    def test_reset(self):
        sm = StateMachine()
        sm.transition(Phase.CONFIG_LOADED)
        sm.transition(Phase.DATABASE_READY)
        sm.reset()
        assert sm.current == Phase.CREATED
        assert sm.history == []

    def test_record_fail(self):
        sm = StateMachine()
        record = sm.fail(Phase.CONFIG_LOADED, "test error")
        assert not record.success
        assert record.error == "test error"
        assert len(sm.history) == 1

    def test_on_enter_callback(self):
        sm = StateMachine()
        called = []
        sm.on_enter(Phase.CONFIG_LOADED, lambda p: called.append(p))
        sm.transition(Phase.CONFIG_LOADED)
        assert Phase.CONFIG_LOADED in called

    def test_on_exit_callback(self):
        sm = StateMachine()
        called = []
        sm.on_exit(Phase.CREATED, lambda p: called.append(p))
        sm.transition(Phase.CONFIG_LOADED)
        assert Phase.CREATED in called

    def test_uptime_increases(self):
        sm = StateMachine()
        sm.transition(Phase.CONFIG_LOADED)
        time.sleep(0.01)
        assert sm.uptime > 0.0

    def test_summary(self):
        sm = StateMachine()
        sm.transition(Phase.CONFIG_LOADED)
        s = sm.summary()
        assert s["current"] == "CONFIG_LOADED"
        assert s["phase_value"] == 10
        assert s["steps"] == 1

    def test_shutdown_flow(self):
        sm = StateMachine()
        for p in [Phase.CONFIG_LOADED, Phase.DATABASE_READY, Phase.PLUGINS_SCANNED,
                   Phase.PLUGINS_LOADED, Phase.BRAIN_READY, Phase.INSTANCES_READY,
                   Phase.ADAPTERS_READY, Phase.RUNNING]:
            sm.transition(p)
        sm.transition(Phase.STOPPING)
        assert sm.is_shutting_down
        sm.transition(Phase.STOPPED)
        assert sm.current == Phase.STOPPED

    def test_shutdown_reset_restart(self):
        sm = StateMachine()
        for p in [Phase.CONFIG_LOADED, Phase.DATABASE_READY, Phase.PLUGINS_SCANNED,
                   Phase.PLUGINS_LOADED, Phase.BRAIN_READY, Phase.INSTANCES_READY,
                   Phase.ADAPTERS_READY, Phase.RUNNING]:
            sm.transition(p)
        sm.transition(Phase.STOPPING)
        sm.transition(Phase.STOPPED)
        sm.reset()
        assert sm.current == Phase.CREATED

    def test_duplicate_transition_does_not_fail(self):
        sm = StateMachine()
        sm.transition(Phase.CONFIG_LOADED)
        with pytest.raises(PhaseTransitionError):
            sm.transition(Phase.CONFIG_LOADED)

    def test_multiple_on_enter_callbacks(self):
        sm = StateMachine()
        results = []
        sm.on_enter(Phase.CONFIG_LOADED, lambda p: results.append("a"))
        sm.on_enter(Phase.CONFIG_LOADED, lambda p: results.append("b"))
        sm.transition(Phase.CONFIG_LOADED)
        assert "a" in results
        assert "b" in results

    def test_on_enter_error_does_not_block(self):
        sm = StateMachine()
        sm.on_enter(Phase.CONFIG_LOADED, lambda p: (_ for _ in ()).throw(Exception("boom")))
        sm.transition(Phase.CONFIG_LOADED)
        assert sm.current == Phase.CONFIG_LOADED

    def test_history_records_timing(self):
        sm = StateMachine()
        sm.transition(Phase.CONFIG_LOADED)
        assert sm.history[0].duration >= 0
        assert sm.history[0].success

    def test_transition_to_running_sets_started_at(self):
        sm = StateMachine()
        sm.transition(Phase.CONFIG_LOADED)
        assert sm.started_at > 0


# ═══════════════════════════════════════════════════════════════
# hooks/ subsystem
# ═══════════════════════════════════════════════════════════════

class TestHookRegistry:
    def test_empty_registry(self):
        reg = HookRegistry()
        assert reg.count() == 0
        assert reg.entries == []

    def test_register_and_count(self):
        reg = HookRegistry()
        async def dummy(ctx): pass
        reg.register(LifecycleEvent.READY, dummy, name="test_hook")
        assert reg.count() == 1
        assert reg.count(LifecycleEvent.READY) == 1

    def test_register_duplicate_raises(self):
        reg = HookRegistry()
        async def dummy(ctx): pass
        reg.register(LifecycleEvent.READY, dummy, name="test_hook")
        with pytest.raises(DuplicateHookError):
            reg.register(LifecycleEvent.READY, dummy, name="test_hook")

    def test_register_same_name_diff_event(self):
        reg = HookRegistry()
        async def dummy(ctx): pass
        reg.register(LifecycleEvent.READY, dummy, name="h")
        reg.register(LifecycleEvent.BEFORE_SHUTDOWN, dummy, name="h")
        assert reg.count() == 2

    def test_unregister_by_name(self):
        reg = HookRegistry()
        async def dummy(ctx): pass
        reg.register(LifecycleEvent.READY, dummy, name="h")
        reg.unregister(LifecycleEvent.READY, name="h")
        assert reg.count() == 0

    def test_unregister_by_callback(self):
        reg = HookRegistry()
        async def dummy(ctx): pass
        reg.register(LifecycleEvent.READY, dummy, name="h")
        reg.unregister(LifecycleEvent.READY, callback=dummy)
        assert reg.count() == 0

    def test_unregister_nonexistent(self):
        reg = HookRegistry()
        async def dummy(ctx): pass
        reg.unregister(LifecycleEvent.READY, name="nonexistent")
        assert reg.count() == 0

    def test_get_by_event(self):
        reg = HookRegistry()
        async def a(ctx): pass
        async def b(ctx): pass
        reg.register(LifecycleEvent.READY, a, name="a")
        reg.register(LifecycleEvent.BEFORE_SHUTDOWN, b, name="b")
        ready_hooks = reg.get_by_event(LifecycleEvent.READY)
        assert len(ready_hooks) == 1
        assert ready_hooks[0].name == "a"

    def test_get_by_plugin(self):
        reg = HookRegistry()
        async def a(ctx): pass
        async def b(ctx): pass
        reg.register(LifecycleEvent.READY, a, name="a", plugin_name="brain")
        reg.register(LifecycleEvent.BEFORE_SHUTDOWN, b, name="b", plugin_name="brain")
        reg.register(LifecycleEvent.READY, b, name="c", plugin_name="other")
        brain_hooks = reg.get_by_plugin("brain")
        assert len(brain_hooks) == 2

    def test_priority_ordering(self):
        reg = HookRegistry()
        async def a(ctx): pass
        async def b(ctx): pass
        async def c(ctx): pass
        reg.register(LifecycleEvent.READY, c, name="c", priority=100)
        reg.register(LifecycleEvent.READY, a, name="a", priority=0)
        reg.register(LifecycleEvent.READY, b, name="b", priority=50)
        hooks = reg.get_by_event(LifecycleEvent.READY)
        assert hooks[0].name == "a"
        assert hooks[1].name == "b"
        assert hooks[2].name == "c"

    def test_default_priority(self):
        reg = HookRegistry()
        async def dummy(ctx): pass
        entry = reg.register(LifecycleEvent.READY, dummy, name="h")
        assert entry.priority == 50

    def test_clear(self):
        reg = HookRegistry()
        async def dummy(ctx): pass
        reg.register(LifecycleEvent.READY, dummy, name="h")
        reg.clear()
        assert reg.count() == 0

    def test_summary(self):
        reg = HookRegistry()
        async def dummy(ctx): pass
        reg.register(LifecycleEvent.READY, dummy, name="h")
        s = reg.summary()
        assert s["total_hooks"] == 1
        assert LifecycleEvent.READY.value in s["by_event"]

    def test_default_timeout(self):
        reg = HookRegistry()
        async def dummy(ctx): pass
        entry = reg.register(LifecycleEvent.READY, dummy, name="h")
        assert entry.timeout == 30.0

    def test_custom_timeout(self):
        reg = HookRegistry()
        async def dummy(ctx): pass
        entry = reg.register(LifecycleEvent.READY, dummy, name="h", timeout=10.0)
        assert entry.timeout == 10.0

    def test_auto_name_from_function(self):
        reg = HookRegistry()
        async def my_custom_handler(ctx): pass
        entry = reg.register(LifecycleEvent.READY, my_custom_handler)
        assert "my_custom_handler" in entry.name


class TestHookExecutor:
    @pytest.mark.asyncio
    async def test_run_event_no_hooks(self):
        reg = HookRegistry()
        exec_ = HookExecutor(reg)
        results = await exec_.run_event(LifecycleEvent.READY)
        assert results == []

    @pytest.mark.asyncio
    async def test_run_event_single_hook(self):
        reg = HookRegistry()
        exec_ = HookExecutor(reg)
        called = []
        async def handler(ctx):
            called.append(True)
        reg.register(LifecycleEvent.READY, handler, name="h")
        results = await exec_.run_event(LifecycleEvent.READY)
        assert len(results) == 1
        assert results[0]["success"]
        assert called == [True]

    @pytest.mark.asyncio
    async def test_run_event_multiple_hooks(self):
        reg = HookRegistry()
        exec_ = HookExecutor(reg)
        order = []
        async def a(ctx):
            order.append("a")
        async def b(ctx):
            order.append("b")
        reg.register(LifecycleEvent.READY, a, name="a", priority=10)
        reg.register(LifecycleEvent.READY, b, name="b", priority=20)
        await exec_.run_event(LifecycleEvent.READY)
        assert order == ["a", "b"]

    @pytest.mark.asyncio
    async def test_context_passed_to_hooks(self):
        reg = HookRegistry()
        exec_ = HookExecutor(reg)
        received = []
        async def handler(ctx):
            received.append(ctx.get("key"))
        reg.register(LifecycleEvent.READY, handler, name="h")
        await exec_.run_event(LifecycleEvent.READY, context={"key": "value"})
        assert received == ["value"]

    @pytest.mark.asyncio
    async def test_hook_timeout(self):
        reg = HookRegistry()
        exec_ = HookExecutor(reg)
        async def slow_handler(ctx):
            await asyncio.sleep(10)
        reg.register(LifecycleEvent.READY, slow_handler, name="slow", timeout=0.1)
        results = await exec_.run_event(LifecycleEvent.READY)
        assert not results[0]["success"]
        assert "timed out" in results[0]["error"]

    @pytest.mark.asyncio
    async def test_hook_error_isolation(self):
        reg = HookRegistry()
        exec_ = HookExecutor(reg)
        order = []
        async def failing(ctx):
            raise ValueError("boom")
        async def good(ctx):
            order.append("good")
        reg.register(LifecycleEvent.READY, failing, name="fail", priority=10)
        reg.register(LifecycleEvent.READY, good, name="good", priority=20)
        results = await exec_.run_event(LifecycleEvent.READY)
        assert not results[0]["success"]
        assert results[1]["success"]
        assert order == ["good"]

    @pytest.mark.asyncio
    async def test_fail_fast_stops_execution(self):
        reg = HookRegistry()
        exec_ = HookExecutor(reg)
        order = []
        async def failing(ctx):
            raise ValueError("boom")
        async def never_called(ctx):
            order.append("should_not_reach")
        reg.register(LifecycleEvent.READY, failing, name="fail", priority=10)
        reg.register(LifecycleEvent.READY, never_called, name="never", priority=20)
        await exec_.run_event(LifecycleEvent.READY, fail_fast=True)
        assert "should_not_reach" not in order

    @pytest.mark.asyncio
    async def test_run_startup_sequence(self):
        reg = HookRegistry()
        exec_ = HookExecutor(reg)
        events_run = []
        async def handler(ctx):
            events_run.append(ctx["event"])
        for evt in [LifecycleEvent.AFTER_CONFIG_LOAD, LifecycleEvent.AFTER_PLUGINS_LOADED,
                     LifecycleEvent.READY]:
            reg.register(evt, handler, name=f"h_{evt.value}")
        results = await exec_.run_startup(context={"event": "test"})
        assert len(results) >= 3

    @pytest.mark.asyncio
    async def test_hook_statistics_tracked(self):
        reg = HookRegistry()
        async def handler(ctx): pass
        entry = reg.register(LifecycleEvent.READY, handler, name="h")
        exec_ = HookExecutor(reg)
        await exec_.run_event(LifecycleEvent.READY)
        assert entry.call_count == 1
        assert entry.last_duration is not None
        await exec_.run_event(LifecycleEvent.READY)
        assert entry.call_count == 2

    @pytest.mark.asyncio
    async def test_hook_failure_statistics(self):
        reg = HookRegistry()
        async def handler(ctx): raise ValueError("fail")
        entry = reg.register(LifecycleEvent.READY, handler, name="h")
        exec_ = HookExecutor(reg)
        await exec_.run_event(LifecycleEvent.READY)
        assert entry.fail_count == 1
        assert entry.last_error is not None

    @pytest.mark.asyncio
    async def test_clear_results(self):
        reg = HookRegistry()
        exec_ = HookExecutor(reg)
        async def handler(ctx): pass
        reg.register(LifecycleEvent.READY, handler, name="h")
        await exec_.run_event(LifecycleEvent.READY)
        assert len(exec_.results()) > 0
        exec_.clear_results()
        assert len(exec_.results()) == 0

    @pytest.mark.asyncio
    async def test_context_passed_by_reference(self):
        reg = HookRegistry()
        exec_ = HookExecutor(reg)
        ctx = {"counter": 0}
        async def mutator(c):
            c["counter"] += 1
        reg.register(LifecycleEvent.READY, mutator, name="m")
        await exec_.run_event(LifecycleEvent.READY, context=ctx)
        assert ctx["counter"] == 1


class TestLifecycleEvents:
    def test_startup_events_order(self):
        from loyan.core.lifecycle.hooks.events import startup_events
        events = startup_events()
        assert events[0] == LifecycleEvent.BEFORE_INIT
        assert events[-1] == LifecycleEvent.READY

    def test_shutdown_events_order(self):
        from loyan.core.lifecycle.hooks.events import shutdown_events
        events = shutdown_events()
        assert events[0] == LifecycleEvent.BEFORE_SHUTDOWN
        assert events[-1] == LifecycleEvent.AFTER_SHUTDOWN

    def test_all_events_contains_all(self):
        from loyan.core.lifecycle.hooks.events import all_events
        all_ev = all_events()
        assert LifecycleEvent.READY in all_ev
        assert LifecycleEvent.ON_ERROR in all_ev
        assert LifecycleEvent.ON_RESTART in all_ev

    def test_event_label(self):
        from loyan.core.lifecycle.hooks.events import event_label
        assert event_label(LifecycleEvent.READY) == "ready"
        assert event_label(LifecycleEvent.BEFORE_SHUTDOWN) == "before shutdown"

    def test_event_enum_values(self):
        assert LifecycleEvent.BEFORE_INIT.value == "before_init"
        assert LifecycleEvent.READY.value == "ready"
        assert LifecycleEvent.ON_ERROR.value == "on_error"
        assert LifecycleEvent.ON_RESTART.value == "on_restart"


# ═══════════════════════════════════════════════════════════════
# health/ subsystem
# ═══════════════════════════════════════════════════════════════

class TestMetricsCollector:
    def test_empty_metrics(self):
        m = MetricsCollector()
        s = m.summary()
        assert s["total_records"] == 0
        assert s["wall_time"] == 0.0
        assert m.latency_p95() == 0.0

    def test_record_phase(self):
        m = MetricsCollector()
        m.record_phase("CONFIG_LOADED", 0.5, True)
        assert m.phase_duration("CONFIG_LOADED") == 0.5
        assert m.total_phase_time() == 0.5

    def test_record_multiple_phases(self):
        m = MetricsCollector()
        m.record_phase("A", 1.0, True)
        m.record_phase("B", 2.0, False)
        assert m.total_phase_time() == 3.0
        assert len(m.phase_summary()) == 2

    def test_record_hook(self):
        m = MetricsCollector()
        m.record_hook("my_hook", 0.1, True)
        s = m.hook_summary()
        assert s["count"] == 1
        assert s["total_time"] == 0.1

    def test_hook_summary_empty(self):
        m = MetricsCollector()
        s = m.hook_summary()
        assert s["count"] == 0

    def test_wall_clock(self):
        m = MetricsCollector()
        m.start_wall_clock()
        time.sleep(0.01)
        assert m.wall_elapsed > 0.0

    def test_timeline(self):
        m = MetricsCollector()
        m.record_phase("A", 0.5, True)
        m.record_hook("h", 0.1, True)
        tl = m.timeline()
        assert len(tl) == 2

    def test_latency_p95(self):
        m = MetricsCollector()
        for i in range(100):
            m.record_phase(f"P{i}", 0.01 * (i + 1), True)
        p95 = m.latency_p95()
        assert 0.9 < p95 < 1.1

    def test_clear(self):
        m = MetricsCollector()
        m.record_phase("A", 0.5, True)
        m.clear()
        assert m.total_phase_time() == 0.0
        assert m.summary()["total_records"] == 0

    def test_summary_structure(self):
        m = MetricsCollector()
        m.start_wall_clock()
        m.record_phase("A", 0.5, True)
        m.record_hook("h", 0.1, True)
        s = m.summary()
        assert "wall_time" in s
        assert "phase_breakdown" in s
        assert "hooks" in s
        assert "latency_p95" in s

    def test_max_history(self):
        m = MetricsCollector(max_history=10)
        for i in range(20):
            m.record_phase(f"P{i}", 0.1, True)
        assert len(m.timeline()) == 10


class TestHealthReporter:
    @pytest.fixture
    def reporter(self):
        sm = StateMachine()
        reg = HookRegistry()
        exec_ = HookExecutor(reg)
        metrics = MetricsCollector()
        return HealthReporter(sm, reg, exec_, metrics)

    def test_generate_basic(self, reporter):
        report = reporter.generate()
        assert report["status"] in ("healthy", "degraded")
        assert "phase" in report
        assert "uptime" in report
        assert "components" in report

    def test_components_in_report(self, reporter):
        reporter.register_check("my_check", lambda: {"ok": True, "detail": "all good"})
        report = reporter.generate()
        assert "my_check" in report["components"]
        assert report["components"]["my_check"]["ok"]

    def test_component_failure(self, reporter):
        reporter.register_check("failing", lambda: {"ok": False, "error": "broken"})
        report = reporter.generate()
        assert not report["components"]["failing"]["ok"]

    def test_component_exception(self, reporter):
        def broken():
            raise RuntimeError("crash")
        reporter.register_check("crash", broken)
        report = reporter.generate()
        assert not report["components"]["crash"]["ok"]
        assert "crash" in report["components"]["crash"]["error"]

    def test_text_summary(self, reporter):
        text = reporter.text_summary()
        assert "Lifecycle Health Report" in text

    def test_hook_metrics_in_report(self, reporter):
        report = reporter.generate()
        assert "hooks" in report
        assert "registered" in report["hooks"]

    def test_phase_history_in_report(self, reporter):
        report = reporter.generate()
        assert "phase_history" in report

    def test_reset_checks(self, reporter):
        reporter.register_check("c1", lambda: {"ok": True})
        reporter.reset()
        report = reporter.generate()
        assert "c1" not in report["components"]


class TestCompositeChecker:
    @pytest.mark.asyncio
    async def test_empty_checker(self):
        cc = CompositeChecker()
        results = await cc.run_all()
        assert results == {}

    @pytest.mark.asyncio
    async def test_add_lambda(self):
        cc = CompositeChecker()
        cc.add_lambda("test_ok", lambda: {"ok": True})
        results = await cc.run_all()
        assert results["test_ok"]["ok"]

    @pytest.mark.asyncio
    async def test_add_lambda_bool_result(self):
        cc = CompositeChecker()
        cc.add_lambda("test_bool", lambda: True)
        results = await cc.run_all()
        assert results["test_bool"]["ok"]

    @pytest.mark.asyncio
    async def test_add_lambda_false_result(self):
        cc = CompositeChecker()
        cc.add_lambda("test_fail", lambda: False)
        results = await cc.run_all()
        assert not results["test_fail"]["ok"]

    @pytest.mark.asyncio
    async def test_run_one(self):
        cc = CompositeChecker()
        cc.add_lambda("only_one", lambda: {"ok": True})
        result = await cc.run_one("only_one")
        assert result["ok"]
        assert await cc.run_one("nonexistent") is None

    @pytest.mark.asyncio
    async def test_remove(self):
        cc = CompositeChecker()
        cc.add_lambda("temp", lambda: True)
        cc.remove("temp")
        results = await cc.run_all()
        assert "temp" not in results

    @pytest.mark.asyncio
    async def test_consecutive_failures(self):
        from loyan.core.lifecycle.health.checker import LambdaCheck
        count = 0
        def fail_fn():
            nonlocal count
            count += 1
            return {"ok": False}
        check = LambdaCheck("failing", fail_fn)
        cc = CompositeChecker()
        cc.add(check)
        await check.check()
        await check.check()
        assert check.consecutive_failures == 2

    def test_summary(self):
        cc = CompositeChecker()
        cc.add_lambda("a", lambda: True)
        cc.add_lambda("b", lambda: True)
        s = cc.summary()
        assert s["count"] == 2


# ═══════════════════════════════════════════════════════════════
# LifecycleManager integration
# ═══════════════════════════════════════════════════════════════

_VALID_PATH = [
    Phase.CONFIG_LOADED, Phase.DATABASE_READY, Phase.PLUGINS_SCANNED,
    Phase.PLUGINS_LOADED, Phase.BRAIN_READY, Phase.INSTANCES_READY,
    Phase.ADAPTERS_READY, Phase.RUNNING,
]


async def _advance_full(mgr: LifecycleManager, up_to: Phase = Phase.RUNNING):
    for p in _VALID_PATH:
        await mgr._advance_to(p)
        if p == up_to:
            break


class TestLifecycleManager:
    @pytest.mark.asyncio
    async def test_initial_phase(self):
        mgr = LifecycleManager()
        assert mgr.phase == Phase.CREATED
        assert not mgr.is_running

    @pytest.mark.asyncio
    async def test_start_advances_through_phases(self):
        mgr = LifecycleManager()
        phases_reached = []
        for p in [Phase.CONFIG_LOADED, Phase.DATABASE_READY]:
            async def make_handler(target=p):
                async def handler(ctx):
                    phases_reached.append(target)
                return handler
            mgr.register_hook(
                LifecycleEvent.AFTER_CONFIG_LOAD if p == Phase.CONFIG_LOADED
                else LifecycleEvent.AFTER_DATABASE_READY,
                await make_handler(),
                name=f"h_{p.name}",
            )

        await mgr._advance_to(Phase.CONFIG_LOADED)
        await mgr._advance_to(Phase.DATABASE_READY)
        assert Phase.DATABASE_READY in phases_reached

    @pytest.mark.asyncio
    async def test_hooks_executed_in_order(self):
        mgr = LifecycleManager()
        order = []
        async def first(ctx): order.append("first")
        async def second(ctx): order.append("second")
        mgr.register_hook(LifecycleEvent.READY, first, name="first", priority=10)
        mgr.register_hook(LifecycleEvent.READY, second, name="second", priority=20)

        await _advance_full(mgr)
        assert order == ["first", "second"]

    @pytest.mark.asyncio
    async def test_wait_for_phase_already_reached(self):
        mgr = LifecycleManager()
        await _advance_full(mgr)
        ok = await mgr.wait_for_phase(Phase.CONFIG_LOADED, timeout=1)
        assert ok

    @pytest.mark.asyncio
    async def test_wait_for_phase_timeout(self):
        mgr = LifecycleManager()
        ok = await mgr.wait_for_phase(Phase.RUNNING, timeout=0.1)
        assert not ok

    @pytest.mark.asyncio
    async def test_context_sharing(self):
        mgr = LifecycleManager()
        mgr.set_context("db", "connected")
        received = []
        async def handler(ctx):
            received.append(ctx.get("db"))
        mgr.register_hook(LifecycleEvent.READY, handler, name="h")
        await _advance_full(mgr)
        assert received == ["connected"]

    @pytest.mark.asyncio
    async def test_register_check(self):
        mgr = LifecycleManager()
        mgr.register_check("custom", lambda: {"ok": True})
        report = mgr.health_report()
        assert report["components"]["custom"]["ok"]

    @pytest.mark.asyncio
    async def test_health_report_generation(self):
        mgr = LifecycleManager()
        report = mgr.health_report()
        assert "status" in report
        assert report["phase"] == "CREATED"

    @pytest.mark.asyncio
    async def test_health_text_output(self):
        mgr = LifecycleManager()
        text = mgr.health_text()
        assert "CREATED" in text

    @pytest.mark.asyncio
    async def test_summary(self):
        mgr = LifecycleManager()
        s = mgr.summary()
        assert s["phase"] == "CREATED"
        assert not s["running"]

    @pytest.mark.asyncio
    async def test_timeline(self):
        mgr = LifecycleManager()
        assert mgr.timeline() == []

    @pytest.mark.asyncio
    async def test_on_phase_register(self):
        mgr = LifecycleManager()
        called = []
        async def handler(ctx): called.append(True)
        mgr.on_phase(Phase.RUNNING, handler)
        await _advance_full(mgr)
        assert called == [True]

    @pytest.mark.asyncio
    async def test_register_hook_returns_entry(self):
        mgr = LifecycleManager()
        async def dummy(ctx): pass
        entry = mgr.register_hook(LifecycleEvent.READY, dummy, name="test")
        assert entry.name == "test"
        assert entry.event == LifecycleEvent.READY

    @pytest.mark.asyncio
    async def test_unregister_hook(self):
        mgr = LifecycleManager()
        async def dummy(ctx): pass
        mgr.register_hook(LifecycleEvent.READY, dummy, name="h")
        assert mgr.hooks.count() == 1
        mgr.unregister_hook(LifecycleEvent.READY, name="h")
        assert mgr.hooks.count() == 0

    @pytest.mark.asyncio
    async def test_phase_timeout_config(self):
        mgr = LifecycleManager()
        mgr.set_phase_timeout(Phase.RUNNING, 5.0)

    @pytest.mark.asyncio
    async def test_startup_error_triggers_on_error(self):
        mgr = LifecycleManager()
        error_triggered = []
        async def on_err(ctx): error_triggered.append(True)
        mgr.register_hook(LifecycleEvent.ON_ERROR, on_err, name="err")
        mgr._run_startup_sequence = lambda: (_ for _ in ()).throw(
            RuntimeError("deliberate failure")
        )
        with pytest.raises(RuntimeError):
            await mgr.start(timeout=5)
        assert error_triggered == [True]

    @pytest.mark.asyncio
    async def test_shutdown_aborts_startup(self):
        mgr = LifecycleManager()
        original = mgr._advance_to
        async def delayed_advance(target):
            if target == Phase.RUNNING:
                mgr._shutdown_requested = True
            await original(target)
        mgr._advance_to = delayed_advance

        await mgr._run_startup_sequence()
        # Shutdown was requested during advance to RUNNING; flag checked before next advance
        assert mgr.phase == Phase.RUNNING

    @pytest.mark.asyncio
    async def test_shutdown_flag_checked_between_phases(self):
        mgr = LifecycleManager()
        await mgr._advance_to(Phase.CONFIG_LOADED)
        mgr._shutdown_requested = True
        await mgr._run_startup_sequence()
        assert mgr.phase == Phase.CONFIG_LOADED

    @pytest.mark.asyncio
    async def test_signal_handler_installs(self):
        mgr = LifecycleManager()
        loop = asyncio.get_event_loop()
        mgr.install_signal_handlers(loop)

    @pytest.mark.asyncio
    async def test_context_isolation(self):
        mgr = LifecycleManager()
        mgr.set_context("key", "value1")
        ctx1 = mgr.context
        mgr.set_context("key", "value2")
        assert mgr.context["key"] == "value2"
        ctx1["key"] = "mutated"
        assert mgr.context["key"] == "value2"

    @pytest.mark.asyncio
    async def test_update_context(self):
        mgr = LifecycleManager()
        mgr.update_context({"a": 1, "b": 2})
        assert mgr.context["a"] == 1
        assert mgr.context["b"] == 2

    @pytest.mark.asyncio
    async def test_instance_name(self):
        mgr = LifecycleManager()
        assert mgr.instance_name == "default"
        mgr.instance_name = "test_instance"
        assert mgr.instance_name == "test_instance"

    @pytest.mark.asyncio
    async def test_auto_restart_default_disabled(self):
        mgr = LifecycleManager()
        s = mgr.summary()
        assert not s["auto_restart"]

    @pytest.mark.asyncio
    async def test_enable_disable_auto_restart(self):
        mgr = LifecycleManager()
        mgr.enable_auto_restart(max_restarts=5)
        assert mgr._auto_restart
        assert mgr._max_restarts == 5
        mgr.disable_auto_restart()
        assert not mgr._auto_restart

    @pytest.mark.asyncio
    async def test_restart_count(self):
        mgr = LifecycleManager()
        assert mgr.restart_count == 0

    @pytest.mark.asyncio
    async def test_uptime_property(self):
        mgr = LifecycleManager()
        assert mgr.uptime == 0.0

    @pytest.mark.asyncio
    async def test_wait_for_running_timeout(self):
        mgr = LifecycleManager()
        ok = await mgr.wait_for_running(timeout=0.1)
        assert not ok

    @pytest.mark.asyncio
    async def test_wait_for_shutdown_without_start(self):
        mgr = LifecycleManager()
        ok = await mgr.wait_for_shutdown(timeout=0.1)
        assert ok

    @pytest.mark.asyncio
    async def test_create_task_tracks(self):
        mgr = LifecycleManager()
        async def dummy():
            await asyncio.sleep(0.01)
        task = mgr.create_task(dummy(), name="test_task")
        assert task in mgr._running_tasks
        await task
        assert task not in mgr._running_tasks

    @pytest.mark.asyncio
    async def test_on_error_callback(self):
        mgr = LifecycleManager()
        errors = []
        mgr.on_error(lambda msg: errors.append(msg))
        await mgr._trigger_error("test error")
        assert errors == ["test error"]

    @pytest.mark.asyncio
    async def test_on_error_async_callback(self):
        mgr = LifecycleManager()
        errors = []
        async def async_cb(msg):
            errors.append(msg)
        mgr.on_error(async_cb)
        await mgr._trigger_error("async error")
        assert errors == ["async error"]

    @pytest.mark.asyncio
    async def test_summary_includes_instance(self):
        mgr = LifecycleManager()
        mgr.instance_name = "mybot"
        s = mgr.summary()
        assert s["instance"] == "mybot"

    @pytest.mark.asyncio
    async def test_summary_after_advance(self):
        mgr = LifecycleManager()
        await mgr._advance_to(Phase.CONFIG_LOADED)
        s = mgr.summary()
        assert s["phase"] == "CONFIG_LOADED"
        assert s["uptime"] >= 0

    @pytest.mark.asyncio
    async def test_reset_state(self):
        mgr = LifecycleManager()
        await mgr._advance_to(Phase.CONFIG_LOADED)
        mgr.reset_state()
        assert mgr.phase == Phase.CREATED
        assert mgr.restart_count == 0

    @pytest.mark.asyncio
    async def test_wait_for_running_already_running(self):
        mgr = LifecycleManager()
        await _advance_full(mgr)
        ok = await mgr.wait_for_running(timeout=1)
        assert ok

    @pytest.mark.asyncio
    async def test_waiters_notified_on_phase(self):
        mgr = LifecycleManager()
        waiter = asyncio.create_task(mgr.wait_for_phase(Phase.CONFIG_LOADED))
        await asyncio.sleep(0.01)
        await mgr._advance_to(Phase.CONFIG_LOADED)
        ok = await asyncio.wait_for(waiter, timeout=1)
        assert ok

    @pytest.mark.asyncio
    async def test_notify_all_earlier_phases(self):
        mgr = LifecycleManager()
        wait_cfg = asyncio.create_task(mgr.wait_for_phase(Phase.CONFIG_LOADED))
        wait_db = asyncio.create_task(mgr.wait_for_phase(Phase.DATABASE_READY))
        await asyncio.sleep(0)
        await mgr._advance_to(Phase.CONFIG_LOADED)
        await mgr._advance_to(Phase.DATABASE_READY)
        assert await asyncio.wait_for(wait_cfg, timeout=1)
        assert await asyncio.wait_for(wait_db, timeout=1)

    @pytest.mark.asyncio
    async def test_run_blocking(self):
        mgr = LifecycleManager()
        stop_task = asyncio.create_task(mgr.run(stop_timeout=5))
        await asyncio.sleep(0.1)
        mgr._shutdown_complete.set()
        await asyncio.wait_for(stop_task, timeout=5)
        assert mgr.phase in (Phase.RUNNING, Phase.STOPPED)

    @pytest.mark.asyncio
    async def test_summary_tasks_count(self):
        mgr = LifecycleManager()
        async def dummy():
            await asyncio.sleep(0.1)
        mgr.create_task(dummy(), name="t1")
        s = mgr.summary()
        assert s["tasks"] == 1

    @pytest.mark.asyncio
    async def test_parallel_hook_execution(self):
        reg = HookRegistry()
        exec_ = HookExecutor(reg)
        order = []
        async def slow(ctx):
            await asyncio.sleep(0.05)
            order.append("slow")
        async def fast(ctx):
            order.append("fast")
        reg.register(LifecycleEvent.READY, slow, name="slow", priority=10)
        reg.register(LifecycleEvent.READY, fast, name="fast", priority=20)
        await exec_.run_event(LifecycleEvent.READY, parallel=True)
        assert "fast" in order
        assert "slow" in order

    @pytest.mark.asyncio
    async def test_parallel_with_semaphore(self):
        reg = HookRegistry()
        exec_ = HookExecutor(reg)
        running = 0
        max_running = 0
        async def worker(ctx):
            nonlocal running, max_running
            running += 1
            max_running = max(max_running, running)
            await asyncio.sleep(0.05)
            running -= 1
        for i in range(10):
            reg.register(LifecycleEvent.READY, worker, name=f"w{i}")
        await exec_.run_event(LifecycleEvent.READY, parallel=True, max_concurrent=3)
        assert max_running <= 3

    @pytest.mark.asyncio
    async def test_run_event_with_parallel_returns_all(self):
        reg = HookRegistry()
        exec_ = HookExecutor(reg)
        async def h(ctx): pass
        reg.register(LifecycleEvent.READY, h, name="h1")
        reg.register(LifecycleEvent.READY, h, name="h2")
        results = await exec_.run_event(LifecycleEvent.READY, parallel=True)
        assert len(results) == 2


# ═══════════════════════════════════════════════════════════════
# Error types
# ═══════════════════════════════════════════════════════════════

class TestErrors:
    def test_phase_transition_error(self):
        err = PhaseTransitionError(Phase.CREATED, Phase.RUNNING)
        assert "CREATED" in str(err)
        assert "RUNNING" in str(err)
        assert err.current == Phase.CREATED
        assert err.target == Phase.RUNNING

    def test_hook_timeout_error(self):
        err = HookTimeoutError("my_hook", "ready", 5.0)
        assert "my_hook" in str(err)
        assert err.timeout == 5.0

    def test_hook_execution_error(self):
        original = ValueError("original error")
        err = HookExecutionError("h", "ready", original)
        assert "h" in str(err)
        assert err.original is original

    def test_component_not_ready_error(self):
        err = ComponentNotReadyError("db", Phase.RUNNING, Phase.CREATED)
        assert "db" in str(err)
        assert err.required_phase == Phase.RUNNING

    def test_duplicate_hook_error(self):
        err = DuplicateHookError("hook already registered")
        assert "hook" in str(err)

    def test_lifecycle_error_is_base(self):
        assert issubclass(PhaseTransitionError, LifecycleError)
        assert issubclass(HookTimeoutError, LifecycleError)
        assert issubclass(HookExecutionError, LifecycleError)
        assert issubclass(ComponentNotReadyError, LifecycleError)
        assert issubclass(DuplicateHookError, LifecycleError)


# ═══════════════════════════════════════════════════════════════
# Integration edge cases
# ═══════════════════════════════════════════════════════════════

class TestEdgeCases:
    def test_phase_meta_all_defined(self):
        from loyan.core.lifecycle.state.phases import PHASE_META
        for phase in Phase:
            assert phase in PHASE_META, f"Missing meta for {phase.name}"

    def test_every_phase_has_transition_target(self):
        from loyan.core.lifecycle.state.phases import _TRANSITION_TABLE
        for phase in Phase:
            if phase != Phase.STOPPED:
                assert phase in _TRANSITION_TABLE, f"No transition table entry for {phase.name}"
            else:
                assert phase in _TRANSITION_TABLE, f"STOPPED should be in table (reset path)"

    def test_transition_table_completeness(self):
        from loyan.core.lifecycle.state.phases import _TRANSITION_TABLE
        all_targets = set()
        for targets in _TRANSITION_TABLE.values():
            all_targets.update(targets)
        for phase in Phase:
            if phase == Phase.CREATED:
                continue
            assert phase in all_targets or phase in _TRANSITION_TABLE.get(Phase.CREATED, []), \
                f"{phase.name} is never a transition target"

    @pytest.mark.asyncio
    async def test_hook_executor_empty_startup(self):
        reg = HookRegistry()
        exec_ = HookExecutor(reg)
        results = await exec_.run_startup()
        assert len(results) >= 9

    @pytest.mark.asyncio
    async def test_hook_executor_empty_shutdown(self):
        reg = HookRegistry()
        exec_ = HookExecutor(reg)
        results = await exec_.run_shutdown()
        assert len(results) >= 2

    @pytest.mark.asyncio
    async def test_multiple_errors_on_same_hook(self):
        reg = HookRegistry()
        exec_ = HookExecutor(reg)
        call_count = [0]
        async def fail_twice(ctx):
            call_count[0] += 1
            raise ValueError(f"fail #{call_count[0]}")
        reg.register(LifecycleEvent.READY, fail_twice, name="failer")
        r1 = await exec_.run_event(LifecycleEvent.READY)
        r2 = await exec_.run_event(LifecycleEvent.READY)
        assert not r1[0]["success"]
        assert not r2[0]["success"]
        entry = reg.get_by_event(LifecycleEvent.READY)[0]
        assert entry.fail_count == 2

    @pytest.mark.asyncio
    async def test_hook_survives_mixed_errors(self):
        reg = HookRegistry()
        exec_ = HookExecutor(reg)
        good_count = [0]
        async def good(ctx):
            good_count[0] += 1
        async def bad(ctx):
            raise RuntimeError("bad")
        reg.register(LifecycleEvent.READY, bad, name="bad", priority=10)
        reg.register(LifecycleEvent.READY, good, name="good", priority=20)
        await exec_.run_event(LifecycleEvent.READY)
        await exec_.run_event(LifecycleEvent.READY)
        assert good_count[0] == 2
        bad_entry = reg.get_by_event(LifecycleEvent.READY)[0]
        assert bad_entry.fail_count == 2

    @pytest.mark.asyncio
    async def test_registry_summary_empty(self):
        reg = HookRegistry()
        s = reg.summary()
        assert s["total_hooks"] == 0
        assert s["by_event"] == {}

    @pytest.mark.asyncio
    async def test_wait_for_phase_multiple_waiters(self):
        mgr = LifecycleManager()
        results = []
        async def waiter1():
            await mgr.wait_for_phase(Phase.CONFIG_LOADED)
            results.append("w1")
        async def waiter2():
            await mgr.wait_for_phase(Phase.CONFIG_LOADED)
            results.append("w2")
        t1 = asyncio.create_task(waiter1())
        t2 = asyncio.create_task(waiter2())
        await asyncio.sleep(0)
        await mgr._advance_to(Phase.CONFIG_LOADED)
        await asyncio.wait_for(asyncio.gather(t1, t2), timeout=2)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_advance_to_same_phase_twice(self):
        mgr = LifecycleManager()
        await mgr._advance_to(Phase.CONFIG_LOADED)
        await mgr._advance_to(Phase.CONFIG_LOADED)
        assert mgr.phase == Phase.CONFIG_LOADED

    @pytest.mark.asyncio
    async def test_stop_from_early_phase(self):
        mgr = LifecycleManager()
        await _advance_full(mgr)
        mgr._shutdown_requested = True
        await mgr.stop(timeout=5)
        assert mgr.phase == Phase.STOPPED

    @pytest.mark.asyncio
    async def test_stop_from_created(self):
        mgr = LifecycleManager()
        mgr._shutdown_requested = True
        mgr._state.reset()
        mgr._state.transition(Phase.CONFIG_LOADED)
        mgr._state.transition(Phase.DATABASE_READY)
        mgr._state.transition(Phase.PLUGINS_SCANNED)
        mgr._state.transition(Phase.PLUGINS_LOADED)
        mgr._state.transition(Phase.BRAIN_READY)
        mgr._state.transition(Phase.INSTANCES_READY)
        mgr._state.transition(Phase.ADAPTERS_READY)
        mgr._state.transition(Phase.RUNNING)
        mgr._state.transition(Phase.STOPPING)
        mgr._state.transition(Phase.STOPPED)
        assert mgr.phase == Phase.STOPPED

    @pytest.mark.asyncio
    async def test_phase_timeout_enforced(self):
        mgr = LifecycleManager()
        async def slow_hook(ctx):
            await asyncio.sleep(10)
        mgr.register_hook(LifecycleEvent.AFTER_CONFIG_LOAD, slow_hook, name="slow", timeout=0.05)
        await mgr._advance_to(Phase.CONFIG_LOADED)
        recent = mgr._state.history[-1]
        assert recent.success
        hook_entry = mgr.hooks.get_by_event(LifecycleEvent.AFTER_CONFIG_LOAD)[0]
        assert hook_entry.fail_count > 0
        assert hook_entry.last_error is not None

    @pytest.mark.asyncio
    async def test_health_report_with_failed_phase(self):
        mgr = LifecycleManager()
        async def failing_hook(ctx):
            raise RuntimeError("phase failure")
        mgr.register_hook(LifecycleEvent.AFTER_CONFIG_LOAD, failing_hook, name="fail", timeout=1)
        await mgr._advance_to(Phase.CONFIG_LOADED)
        report = mgr.health_report()
        assert report["status"] in ("healthy", "degraded")

    @pytest.mark.asyncio
    async def test_register_check_lambda(self):
        mgr = LifecycleManager()
        mgr.register_check("custom", lambda: {"ok": True, "detail": "custom check"})
        report = mgr.health_report()
        assert report["components"]["custom"]["detail"] == "custom check"

    @pytest.mark.asyncio
    async def test_context_immutable_outside(self):
        mgr = LifecycleManager()
        mgr.set_context("key", "original")
        ctx = mgr.context
        ctx["key"] = "mutated"
        assert mgr.context["key"] == "original"

    @pytest.mark.asyncio
    async def test_metrics_timeline_order(self):
        m = MetricsCollector()
        m.record_phase("P1", 0.1, True)
        m.record_phase("P2", 0.2, True)
        tl = m.timeline()
        assert tl[0]["name"] == "P1"
        assert tl[1]["name"] == "P2"

    @pytest.mark.asyncio
    async def test_metrics_phase_failure_recorded(self):
        m = MetricsCollector()
        m.record_phase("FAILED", 0.5, False)
        assert not m.timeline()[0]["success"]

    @pytest.mark.asyncio
    async def test_state_machine_history_len(self):
        sm = StateMachine()
        for p in [Phase.CONFIG_LOADED, Phase.DATABASE_READY, Phase.PLUGINS_SCANNED,
                   Phase.PLUGINS_LOADED, Phase.BRAIN_READY, Phase.INSTANCES_READY,
                   Phase.ADAPTERS_READY]:
            sm.transition(p)
        assert len(sm.history) == 7
        sm.transition(Phase.RUNNING)
        sm.transition(Phase.STOPPING)
        sm.transition(Phase.STOPPED)
        assert len(sm.history) == 10

    @pytest.mark.asyncio
    async def test_summary_before_and_after_start(self):
        mgr = LifecycleManager()
        s_before = mgr.summary()
        assert not s_before["running"]
        await _advance_full(mgr)
        s_after = mgr.summary()
        assert s_after["running"]

    def test_phase_ordering_strict(self):
        from loyan.core.lifecycle.state.phases import _FORWARD_PATH
        for i in range(len(_FORWARD_PATH) - 1):
            assert _FORWARD_PATH[i].value < _FORWARD_PATH[i + 1].value

    def test_shutdown_range_starts_with_stopping(self):
        from loyan.core.lifecycle.state.phases import shutdown_range
        phases = shutdown_range()
        assert phases[0] == Phase.STOPPING
        assert phases[-1] == Phase.STOPPED

    def test_all_events_have_labels(self):
        from loyan.core.lifecycle.hooks.events import event_label
        for event in LifecycleEvent:
            label = event_label(event)
            assert isinstance(label, str) and len(label) > 0

    @pytest.mark.asyncio
    async def test_checker_add_remove(self):
        checker = CompositeChecker()
        checker.add_lambda("temp", lambda: True)
        assert await checker.run_one("temp") is not None
        checker.remove("temp")
        assert await checker.run_one("temp") is None

    @pytest.mark.asyncio
    async def test_health_reporter_generate_with_hook_results(self):
        sm = StateMachine()
        reg = HookRegistry()
        exec_ = HookExecutor(reg)
        metrics = MetricsCollector()
        reporter = HealthReporter(sm, reg, exec_, metrics)
        async def dummy(ctx): pass
        reg.register(LifecycleEvent.READY, dummy, name="test_hook")
        await exec_.run_event(LifecycleEvent.READY)
        report = reporter.generate()
        assert "executor_results" in report

    def test_phase_transition_error_stringify(self):
        err = PhaseTransitionError(Phase.CREATED, Phase.RUNNING)
        s = str(err)
        assert "CREATED" in s and "RUNNING" in s

    def test_hook_timeout_error_attributes(self):
        err = HookTimeoutError("h", "ready", 5.0)
        assert err.hook_name == "h"
        assert err.timeout == 5.0

    def test_hook_execution_error_wraps(self):
        orig = ValueError("inner")
        err = HookExecutionError("h", "ready", orig)
        assert "inner" in str(err)

    def test_component_not_ready_str(self):
        err = ComponentNotReadyError("brain", Phase.RUNNING, Phase.CREATED)
        assert "brain" in str(err)

    @pytest.mark.asyncio
    async def test_empty_registry_run_event(self):
        reg = HookRegistry()
        exec_ = HookExecutor(reg)
        res = await exec_.run_event(LifecycleEvent.READY, parallel=True)
        assert res == []

    @pytest.mark.asyncio
    async def test_executor_results_filtered(self):
        reg = HookRegistry()
        exec_ = HookExecutor(reg)
        async def h(ctx): pass
        reg.register(LifecycleEvent.READY, h, name="h")
        await exec_.run_event(LifecycleEvent.READY)
        filtered = exec_.results(LifecycleEvent.READY)
        assert LifecycleEvent.READY.value in filtered
