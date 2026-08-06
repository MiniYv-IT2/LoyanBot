"""后台聊天任务包 — 面板 SSE 对话的后台化执行

设计: ChatTask (task/chat_task.py) 描述单次生成任务,
      TaskManager (task/manager.py) 全局单例管理创建/查询/取消/恢复。
任务在 asyncio 后台运行, 与 SSE 订阅解耦 — 关闭页面/断线不中断生成,
重开页面可订阅 events 续收。事件累积在 task.events (断线重连全量补发),
完成置 done 事件, 随后落库 (面板/IM 分表按 session_id 前缀路由)。
"""

from .chat_task import ChatTask
from .manager import task_manager

__all__ = ["ChatTask", "task_manager"]
