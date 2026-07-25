"""Brain — AI 能力模块

提供模型调用、对话引擎、记忆等 AI 基础设施。
模块导入时自动注册命令并自启初始化，与 core 平级。
"""

import asyncio
import logging
from typing import Optional

from loyan.brain.provider.manager import ProviderManager
from loyan.brain.chat.engine import ChatEngine

_logger = logging.getLogger("Brain")

_brain: Optional["Brain"] = None


class Brain:
    def __init__(self):
        self.provider = ProviderManager()
        self.chat = ChatEngine(self.provider)

    async def start(self):
        _logger.info("Brain 初始化中...")
        from loyan.brain.chat.persona import persona_mgr
        await persona_mgr.init()
        from loyan.brain.provider.keystore import keystore
        await keystore.init()
        await self.provider.load_all()
        _logger.info(f"Brain 已就绪，{len(self.provider.registry)} 个提供商注册")

    async def stop(self):
        _logger.info("Brain 正在关闭...")
        await self.provider.close_all()
        _logger.info("Brain 已关闭")

    @property
    def ready(self) -> bool:
        return len(self.provider.registry) > 0


def get_brain() -> Brain:
    global _brain
    if _brain is None:
        _brain = Brain()
    return _brain


# ── 模块导入时自动注册命令到 DECORATOR_COMMAND_REGISTRY ──
from loyan.brain.commands import chat as _chat_cmds  # noqa: F402
from loyan.brain.commands import persona as _persona_cmds  # noqa: F402


# ── 模块导入时自启 ──
_b = get_brain()
asyncio.ensure_future(_b.start())
