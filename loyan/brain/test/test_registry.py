"""注册中心完整性测试 — 确保 brain 命令不被意外清除"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from loyan.core.decorators.registration import DECORATOR_COMMAND_REGISTRY
from loyan.core.plugin_manager import plugin_manager


def test_brain_commands_registered():
    """brain 的核心命令必须存在"""
    all_cmds = set()
    for entry in DECORATOR_COMMAND_REGISTRY:
        for cmd in entry.get("commands", []):
            all_cmds.add(cmd)
    for expect in ("/chat", "/persona", "/chat reset"):
        assert expect in all_cmds, f"缺少 brain 命令: {expect}"


def test_brain_commands_order():
    """验证 brain 命令在 plugin_manager.init() 后仍然存在"""
    before = len(DECORATOR_COMMAND_REGISTRY)
    plugin_manager.init()
    after = len(DECORATOR_COMMAND_REGISTRY)
    assert after >= before, (
        f"plugin_manager.init() 移除了已注册的命令: "
        f"初始化前 {before} → 初始化后 {after}"
    )
    entries = {e["plugin_name"]: e["commands"] for e in DECORATOR_COMMAND_REGISTRY}
    assert "brain" in entries, "plugin_manager.init() 后丢失 brain 命令"
