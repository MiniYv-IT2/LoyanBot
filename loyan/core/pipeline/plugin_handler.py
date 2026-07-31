"""Stage: PluginHandler — 插件执行、权限校验、计时、审计"""

import asyncio
import inspect
import logging
import time
from typing import Optional

from loyan.core.pipeline import Stage
from loyan.core.decorators.context import PluginContext
from loyan.core.decorators.logger import _log_attrs_ctx

_logger = logging.getLogger("Core.Pipeline")


class PluginHandler(Stage):
    """插件执行器

    职责:
        - 调用 plugin_manager.get_matched_plugin 获取完整插件信息
        - 执行 handler_func
        - 计时 + 监控上报
        - 异常捕获 + 审计日志
    """

    timeout: float = 300.0  # LLM 请求可能较慢，给 5 分钟

    async def process(self, ctx: PluginContext) -> Optional[PluginContext]:
        handler_func = ctx.extra.get("handler_func", None)
        if not handler_func:
            return ctx

        start_time = time.time()
        plugin_name = ctx.plugin_name

        # ── 注入 ctx.send / ctx.reply（公共函数，BuiltinCommands 同样使用） ──
        from loyan.core.pipeline.helpers import inject_send_reply
        inject_send_reply(ctx)

        try:
            priority = ctx.extra.get("priority")
            _log_token = None
            if priority is not None:
                _log_token = _log_attrs_ctx.set({"priority": f"P{priority}"})

            try:
                sig = inspect.signature(handler_func)
                params = list(sig.parameters.keys())

                if len(params) == 1 and params[0] in ("ctx", "self"):
                    if inspect.iscoroutinefunction(handler_func):
                        await handler_func(ctx)
                    else:
                        loop = asyncio.get_running_loop()
                        await loop.run_in_executor(None, handler_func, ctx)
                else:
                    _logger.debug(f"[PluginHandler] 旧风格调用: {plugin_name}")
                    async def _ph_send(*args, **kwargs):
                        return await loyan_send_msg(*args, **kwargs, tag=ctx.adapter_tag)
                    result = handler_func(
                        ctx.plugin_manager,
                        _ph_send,
                        self._build_plugin_data(ctx),
                        ctx.sender_id,
                        ctx.chat_type,
                        "all",
                        _logger,
                    )
                    if inspect.iscoroutine(result):
                        await result
            finally:
                if _log_token is not None:
                    _log_attrs_ctx.reset(_log_token)
                    _log_token = None

            elapsed = time.time() - start_time
            _logger.info(
                f"[PluginHandler] 成功: {plugin_name} "
                f"命令={ctx.command} 耗时={elapsed:.3f}s"
            )

        except Exception as e:
            elapsed = time.time() - start_time
            _logger.error(
                f"[PluginHandler] 异常: {plugin_name} "
                f"命令={ctx.command} 耗时={elapsed:.3f}s 错误={e}",
                exc_info=True,
            )

        return None

    def _build_plugin_data(self, ctx: PluginContext) -> dict:
        return {
            "text": ctx.text or ctx.raw_text,
            "nickname": ctx.nickname,
            "images": ctx.images,
            "ats": ctx.ats,
            "target_id": ctx.target_id,
            "chat_type": ctx.chat_type,
            "raw_data": ctx.raw_data,
            "is_at_bot": ctx.is_at_bot,
        }
