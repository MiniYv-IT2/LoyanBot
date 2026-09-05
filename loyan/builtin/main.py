"""Builtin Plugin - 框架内置命令入口"""
import os
import sys

_PLUGINS_DIR = os.path.dirname(os.path.abspath(__file__))
_MODULES_DIR = os.path.join(_PLUGINS_DIR, "modules")
sys.path.insert(0, _MODULES_DIR)

# 导入所有模块
from .modules import help
from .modules import xiaoyu
from .modules import chat
from .modules import persona
from .modules import system
from .modules import about

__all__ = ["chat", "persona", "help", "xiaoyu", "system", "about"]


async def handle_main(ctx):
    """主入口"""
    pass
