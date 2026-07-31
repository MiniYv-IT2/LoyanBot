"""Container 组合根单元测试 — 注册/惰性构建/线程安全/叶子工厂"""

import threading

from loyan.core.container import Container, build_container


class TestRegisterGet:
    def test_get_returns_same_instance(self):
        container = Container()
        container.register("x", lambda _c: object())
        assert container.get("x") is container.get("x")

    def test_factory_receives_container_itself(self):
        container = Container()
        seen = {}

        def factory(c):
            seen["container"] = c
            return "value"

        container.register("x", factory)
        container.get("x")
        assert seen["container"] is container

    def test_unregistered_raises_keyerror(self):
        container = Container()
        try:
            container.get("missing")
        except KeyError:
            pass
        else:
            raise AssertionError("expected KeyError")


class TestLazyBuild:
    def test_factory_not_called_until_get(self):
        container = Container()
        calls = []

        def factory(_c):
            calls.append(1)
            return "value"

        container.register("x", factory)
        assert calls == []
        container.get("x")
        assert calls == [1]

    def test_factory_called_once(self):
        container = Container()
        calls = []

        def factory(_c):
            calls.append(1)
            return "value"

        container.register("x", factory)
        container.get("x")
        container.get("x")
        assert len(calls) == 1


class TestBuild:
    def test_build_prebuilds_all(self):
        container = Container()
        built = []

        def factory_a(_c):
            built.append("a")
            return 1

        def factory_b(_c):
            built.append("b")
            return 2

        container.register("a", factory_a)
        container.register("b", factory_b)
        container.build()
        assert set(built) == {"a", "b"}
        assert container.get("a") == 1
        assert container.get("b") == 2


class TestContains:
    def test_contains_registered(self):
        container = Container()
        container.register("x", lambda _c: 1)
        assert "x" in container
        assert container.has("x")

    def test_not_contains_missing(self):
        container = Container()
        assert "missing" not in container
        assert not container.has("missing")


class TestThreadSafety:
    def test_concurrent_get_builds_once(self):
        container = Container()
        calls = []

        def factory(_c):
            calls.append(1)
            return "value"

        container.register("x", factory)

        results = []
        errors = []

        def worker():
            try:
                results.append(container.get("x"))
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(16)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        assert len(calls) == 1
        assert len(results) == 16
        assert all(r == "value" for r in results)


class TestBuildContainer:
    def test_leaf_components_same_as_module_singletons(self):
        from loyan.core.config_manager import config_manager
        from loyan.core.event import event_bus
        from loyan.core.logger_manager import logger_manager
        from loyan.core.loyan_adapter.pool import adapter_pool
        from loyan.core.plugin_manager import plugin_manager

        container = build_container()
        assert container.get("adapter_pool") is adapter_pool
        assert container.get("event_bus") is event_bus
        assert container.get("config_manager") is config_manager
        assert container.get("logger_manager") is logger_manager
        assert container.get("plugin_manager") is plugin_manager

    def test_build_container_has_all_leafs(self):
        container = build_container()
        for name in (
            "adapter_pool",
            "event_bus",
            "config_manager",
            "runtime_registry",
            "logger_manager",
            "plugin_manager",
        ):
            assert name in container
