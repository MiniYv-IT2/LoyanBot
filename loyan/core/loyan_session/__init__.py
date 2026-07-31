
"""LoyanBot 会话管理模块 - 统一管理AI对话上下文

提供:
- 会话数据类: LoyanSession
- 会话管理器: LoyanSessionManager
- 便捷函数: loyan_get_session, loyan_get_or_create_session, loyan_add_context 等

特点:
- 不绑定任何插件
- 跨平台兼容
- 不依赖通信层
- JSON配置驱动
- 只管AI对话，不冗余
"""

from .loyan_session import LoyanSession
from .loyan_session_manager import (
    LoyanSessionManager,
    loyan_get_session_manager,
    loyan_init_session_manager,
    loyan_get_session,
    loyan_get_or_create_session,
    loyan_create_session,
    loyan_destroy_session,
    loyan_add_context,
    loyan_get_context,
    loyan_clear_context,
    loyan_set_state,
    loyan_get_state,
    loyan_session,
)
from .loyan_session_handler import handle_session_command

__all__ = [
    "LoyanSession",
    "LoyanSessionManager",
    "loyan_get_session_manager",
    "loyan_get_session",
    "loyan_get_or_create_session",
    "loyan_create_session",
    "loyan_destroy_session",
    "loyan_add_context",
    "loyan_get_context",
    "loyan_clear_context",
    "loyan_set_state",
    "loyan_get_state",
    "loyan_session",
    "handle_session_command",
]
