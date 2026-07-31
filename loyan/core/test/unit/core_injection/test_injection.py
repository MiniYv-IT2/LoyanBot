"""核心组件构造注入单元测试 — PluginManager / SecurityManager / MonitorManager

验证：
1. 显式传入 fake 依赖可构造独立实例（构造注入，生产级可测试）
2. 无参构造等价模块级默认实例（向后兼容，调用方零改动）
3. 模块级单例 is 关系保持不变，注入不污染单例
"""

from loyan.core.monitor import MonitorManager, monitor_manager
from loyan.core.plugin_manager import PluginManager, plugin_manager
from loyan.core.security_manager import SecurityManager, UserRole, security_manager


class FakeConfig:
    def __init__(self, data=None):
        self._data = data or {}

    def get(self, key, default=None):
        return self._data.get(key, default)


class FakeLogger:
    def __init__(self):
        self.messages = []

    def debug(self, msg, *args, **kwargs):
        self.messages.append(("debug", msg))

    def info(self, msg, *args, **kwargs):
        self.messages.append(("info", msg))

    def warning(self, msg, *args, **kwargs):
        self.messages.append(("warning", msg))

    def error(self, msg, *args, **kwargs):
        self.messages.append(("error", msg))


class FakeLoggerManager:
    def __init__(self, logger=None):
        self._logger = logger or FakeLogger()

    def get_logger(self, name):
        return self._logger

    def log_with_context(self, logger, level, msg, context=None):
        logger.info(msg)


class TestPluginManagerInjection:
    def test_inject_config_manager(self):
        cfg = FakeConfig()
        pm = PluginManager(config_manager=cfg)
        assert pm is not plugin_manager
        assert pm.config_manager is cfg

    def test_inject_logger_and_logger_manager(self):
        logger = FakeLogger()
        lm = FakeLoggerManager(logger)
        pm = PluginManager(logger=logger, logger_manager=lm)
        assert pm is not plugin_manager
        assert pm.logger is logger
        assert pm.logger_manager is lm

    def test_full_injection(self):
        cfg = FakeConfig()
        logger = FakeLogger()
        lm = FakeLoggerManager(logger)
        pm = PluginManager(config_manager=cfg, logger=logger, logger_manager=lm)
        assert pm.config_manager is cfg
        assert pm.logger is logger
        assert pm.logger_manager is lm

    def test_default_construct_equals_singleton(self):
        assert PluginManager() is plugin_manager

    def test_module_singleton_identity_preserved(self):
        before = plugin_manager
        PluginManager(config_manager=FakeConfig())
        assert plugin_manager is before
        assert PluginManager() is before

    def test_injection_does_not_pollute_singleton(self):
        PluginManager(config_manager=FakeConfig(), logger=FakeLogger())
        assert plugin_manager.config_manager is not None
        from loyan.core.config_manager import config_manager as global_cm

        assert plugin_manager.config_manager is global_cm


class TestSecurityManagerInjection:
    def test_inject_config_manager(self):
        cfg = FakeConfig()
        sm = SecurityManager(config_manager=cfg)
        assert sm is not security_manager
        assert sm.config_manager is cfg

    def test_inject_logger_manager(self):
        logger = FakeLogger()
        lm = FakeLoggerManager(logger)
        sm = SecurityManager(logger_manager=lm)
        assert sm is not security_manager
        assert sm.logger_manager is lm
        assert sm.logger is logger

    def test_inject_config_used_by_role_loading(self):
        cfg = FakeConfig({"master_id": "123"})
        sm = SecurityManager(config_manager=cfg)
        assert sm.get_user_role("123") == UserRole.ADMIN

    def test_default_construct_equals_singleton(self):
        assert SecurityManager() is security_manager

    def test_module_singleton_identity_preserved(self):
        before = security_manager
        SecurityManager(config_manager=FakeConfig())
        assert security_manager is before
        assert SecurityManager() is before

    def test_injection_does_not_pollute_singleton(self):
        SecurityManager(config_manager=FakeConfig(), logger_manager=FakeLoggerManager())
        from loyan.core.config_manager import config_manager as global_cm

        assert security_manager.config_manager is global_cm


class TestMonitorManagerInjection:
    def test_inject_logger(self):
        logger = FakeLogger()
        mm = MonitorManager(logger=logger)
        assert mm is not monitor_manager
        assert mm.logger is logger

    def test_default_construct_equals_singleton(self):
        assert MonitorManager() is monitor_manager

    def test_module_singleton_identity_preserved(self):
        before = monitor_manager
        MonitorManager(logger=FakeLogger())
        assert monitor_manager is before
        assert MonitorManager() is before

    def test_injection_does_not_pollute_singleton(self):
        MonitorManager(logger=FakeLogger())
        from loyan.core.utils import logger as global_logger

        assert monitor_manager.logger is global_logger
