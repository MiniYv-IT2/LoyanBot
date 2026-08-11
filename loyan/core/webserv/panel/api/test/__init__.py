"""消息注入测试接口 — 伪造用户事件走完整管线, 机器人回复到该用户

用法(脚本 scripts/test_send.py 调用):
    POST /api/loyanui/test/send
    {"platform": "qq_official", "sender": "<OpenID>", "text": "现在几点"}
"""

from loyan.core.webserv.quart import request, jsonify


def register_routes(app) -> None:
    @app.route("/api/loyanui/test/send", methods=["POST"])
    async def test_send():
        data = await request.get_json() or {}
        platform = (data.get("platform") or "").strip()
        sender = (data.get("sender") or "").strip()
        text = (data.get("text") or "").strip()
        bot = (data.get("bot") or "").strip()
        if not platform or not sender or not text:
            return jsonify({"success": False, "message": "platform/sender/text required"}), 400

        from loyan.core.event import event_bus
        from loyan.core.loyan_adapter.event import LoyanEvent
        from loyan.core.loyan_adapter.message import LoyanText
        from loyan.core.loyan_adapter.identity import IdentityTag

        tag = IdentityTag(platform=platform, bot_name=bot or "default")
        event = LoyanEvent(
            sender_id=sender,
            target_id=sender,
            chat_type="private",
            segments=[LoyanText(text=text)],
            raw_text=text,
            message_id=f"test_send_{sender}",
            nickname="脚本测试",
            is_at_bot=False,
            source=tag,
        )
        # 面板跑在独立 loop, 需把事件丢到 bot 主 loop 执行(避免跨 loop 使用 aiohttp session)
        from loyan.core.plugin_manager import plugin_manager
        main_loop = getattr(plugin_manager, "_main_loop", None)
        if main_loop is None or main_loop.is_closed():
            return jsonify({"success": False, "message": "bot main loop unavailable"}), 500
        import asyncio as _asyncio
        fut = _asyncio.run_coroutine_threadsafe(event_bus.publish(event), main_loop)
        try:
            fut.result(timeout=5)
        except Exception as e:
            return jsonify({"success": False, "message": f"publish failed: {e}"}), 500
        return jsonify({"success": True, "message": f"event published: {platform}/{sender}"})
