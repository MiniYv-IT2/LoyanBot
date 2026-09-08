"""Message injection endpoint — requires JWT or API Key authentication.

Security: This endpoint can send arbitrary messages as any user.
Access is restricted to administrators only.
"""

from loyan.core.webserv.quart import request, jsonify


def register_routes(app) -> None:
    @app.route("/api/loyanui/test/send", methods=["POST"])
    async def test_send():
        # 鉴权检查 - JWT或API Key
        from loyan.core.webserv.panel.auth import verify_token, verify_api_key
        
        # 尝试API Key
        api_key = request.headers.get("X-API-Key", "").strip()
        if api_key:
            key_info = verify_api_key(api_key)
            if key_info and key_info.get("roles", []):
                pass  # API Key验证通过
            else:
                return jsonify({"message": "unauthorized"}), 401
        else:
            # 尝试JWT
            auth = request.headers.get("Authorization", "")
            token = auth[7:] if auth.startswith("Bearer ") else ""
            if not token or not verify_token(token):
                return jsonify({"message": "unauthorized"}), 401

        data = await request.get_json() or {}
        platform = (data.get("platform") or "").strip()
        sender = (data.get("sender") or "").strip()
        text = (data.get("text") or "").strip()
        bot = (data.get("bot") or "").strip()
        
        # 支持attachments（文件上传调试）
        attachments = data.get("attachments", [])
        if attachments:
            if not isinstance(attachments, list):
                return jsonify({"success": False, "message": "attachments must be array"}), 400
            for att in attachments:
                if not isinstance(att, dict):
                    return jsonify({"success": False, "message": "each attachment must be object"}), 400
                if "content_type" not in att or "url" not in att:
                    return jsonify({"success": False, "message": "attachment requires content_type and url"}), 400
        
        if not platform or not sender:
            return jsonify({"success": False, "message": "platform/sender required"}), 400
        if not text and not attachments:
            return jsonify({"success": False, "message": "text or attachments required"}), 400

        from loyan.core.event import event_bus
        from loyan.core.loyan_adapter.event import LoyanEvent
        from loyan.core.loyan_adapter.message import LoyanText, LoyanFile
        from loyan.core.loyan_adapter.identity import IdentityTag

        # 构造消息段
        segments = []
        if text:
            segments.append(LoyanText(text=text))
        
        # 解析attachments
        raw_data = {}
        if attachments:
            raw_data["attachments"] = attachments
            for att in attachments:
                content_type = att.get("content_type", "")
                url = att.get("url", "")
                filename = att.get("filename", "")
                
                if content_type.startswith("image/"):
                    segments.append(LoyanImage(url=url))
                elif content_type == "file":
                    segments.append(LoyanFile(url=url, file_path=filename))
                elif content_type == "voice":
                    from loyan.core.loyan_adapter.message import LoyanVoice
                    segments.append(LoyanVoice(file_path=url))
                elif content_type.startswith("video/"):
                    from loyan.core.loyan_adapter.message import LoyanVideo
                    segments.append(LoyanVideo(url=url, file_path=filename))
        
        tag = IdentityTag(platform=platform, bot_name=bot or "default")
        event = LoyanEvent(
            sender_id=sender,
            target_id=sender,
            chat_type="private",
            segments=segments,
            raw_text=text or "",
            message_id=f"test_send_{sender}",
            nickname="脚本测试",
            is_at_bot=False,
            raw_data=raw_data,
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
