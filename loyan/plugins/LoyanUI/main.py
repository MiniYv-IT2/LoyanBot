"""LoyanUI 管理面板 — Web 可视化机器人管理

命令：
  /panel           — 查看面板访问地址
  /panel pwd <旧密码> <新密码> — 修改面板密码（主人可用）
"""

import asyncio
import os
import re
import socket
import threading
import tomllib
from typing import Optional

import httpx

from graci import (
    on_command, plugin_handler, PluginContext, get_logger,
    require_master, Quart, send_from_directory, request, Config, serve,
)

from .auth import (
    create_token, get_port, verify_password, verify_token,
    change_password, validate_password, get_username,
    generate_captcha, verify_captcha,
)

from loyan.core.tools.schema_i18n import (
    build_adapter_schema_response,
    list_adapter_types,
)

logger = get_logger("LoyanUI")

PANEL_DIST = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "panel-dist",
)

_t: Optional[threading.Thread] = None

_METADATA_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "metadata.toml",
)

def _get_version() -> str:
    try:
        with open(_METADATA_PATH, "rb") as f:
            data = tomllib.load(f)
        return data.get("plugin", {}).get("version", "0.0.0")
    except Exception:
        return "0.0.0"


def _get_ip_addresses():
    ips = []
    try:
        import psutil
        for name, addrs in psutil.net_if_addrs().items():
            if name.startswith(("docker", "br-", "veth", "lo")):
                continue
            for addr in addrs:
                ip = addr.address
                if ip in ("127.0.0.1", "::1", "127.0.1.1"):
                    continue
                if ip.startswith("fe80") or ip.startswith("169.254."):
                    continue
                if "." in ip and not ip.startswith("127."):
                    ips.append(("IPv4", ip))
                elif ":" in ip:
                    ips.append(("IPv6", ip))
    except Exception:
        pass
    return ips


def _get_public_ip():
    try:
        resp = httpx.get("https://api.ipify.org?format=json", timeout=3)
        return resp.json().get("ip", "")
    except Exception:
        return ""


def _create_app():
    app = Quart("LoyanUI")

    @app.route("/api/loyanui/auth/login", methods=["POST"])
    async def login():
        data = await request.get_json()
        username = data.get("username", "")
        password = data.get("password", "")
        captcha_id = data.get("captcha_id", "")
        captcha_code = data.get("captcha_code", "")

        if not verify_captcha(captcha_id, captcha_code):
            return {"success": False, "error": "captcha.invalid"}, 400

        if username == get_username() and verify_password(password):
            token = create_token()
            return {"success": True, "token": token}
        return {"success": False, "error": "login.wrong"}, 401

    @app.route("/api/loyanui/auth/captcha")
    async def captcha():
        captcha_id, code = generate_captcha()
        return {"success": True, "data": {"id": captcha_id, "code": code}}

    @app.route("/api/loyanui/version")
    async def version():
        return {"success": True, "data": {"version": _get_version()}}

    @app.route("/api/loyanui/adapter/types")
    async def adapter_types():
        return {"success": True, "data": list_adapter_types()}

    @app.route("/api/loyanui/adapter/schema/<adapter_type>")
    async def adapter_schema(adapter_type):
        result = build_adapter_schema_response(adapter_type)
        if result is None:
            return {"success": False, "error": "adapter.not_found"}, 404
        return {"success": True, "data": result}

    @app.route("/api/loyanui/auth/verify")
    async def verify():
        token = request.args.get("token", "")
        if verify_token(token):
            return {"success": True}
        return {"success": False}, 401

    # ── Provider 实例 API ──

    @app.route("/api/loyanui/providers/types")
    async def list_provider_types():
        from graci import list_provider_types
        return {"success": True, "data": list_provider_types()}

    @app.route("/api/loyanui/providers", methods=["GET"])
    async def list_instances():
        from graci import list_providers
        instances = await list_providers()
        return {"success": True, "data": instances}

    @app.route("/api/loyanui/providers", methods=["POST"])
    async def add_instance():
        data = await request.get_json()
        if not data or not data.get("id") or not data.get("type"):
            return {"success": False, "message": "id 和 type 必填"}, 400
        from graci import add_provider
        try:
            inst_id = await add_provider(data)
            return {"success": True, "data": {"id": inst_id}}
        except Exception as e:
            return {"success": False, "message": str(e)}, 400

    @app.route("/api/loyanui/providers/<inst_id>", methods=["PUT"])
    async def update_instance(inst_id):
        data = await request.get_json()
        if not data:
            return {"success": False, "message": "请求体为空"}, 400
        from graci import update_provider
        try:
            await update_provider(inst_id, data)
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}, 400

    @app.route("/api/loyanui/providers/<inst_id>", methods=["DELETE"])
    async def delete_instance(inst_id):
        from graci import delete_provider
        await delete_provider(inst_id)
        return {"success": True}

    @app.route("/api/loyanui/providers/<inst_id>/models")
    async def list_instance_models(inst_id):
        from graci import list_models
        try:
            models = await list_models(inst_id)
            return {"success": True, "data": models}
        except Exception as e:
            return {"success": False, "message": str(e)}, 400

    @app.route("/api/loyanui/providers/usage")
    async def get_usage():
        from graci import get_usage_summary
        hours = request.args.get("hours", 24, type=int)
        summary = await get_usage_summary(hours=hours)
        return {"success": True, "data": summary}

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    async def serve_panel(path):
        if not path:
            return await send_from_directory(PANEL_DIST, "index.html")
        file_path = os.path.join(PANEL_DIST, path)
        if os.path.exists(file_path):
            return await send_from_directory(PANEL_DIST, path)
        return await send_from_directory(PANEL_DIST, "index.html")

    return app


def _start():
    for attempt in range(3):
        try:
            app = _create_app()
            port = get_port()
            cfg = Config()
            cfg.bind = [f"0.0.0.0:{port}"]
            cfg.loglevel = "warning"

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.add_signal_handler = lambda *_, **__: None

            logger.info(f"LoyanUI 面板已启动: http://0.0.0.0:{port}")
            loop.run_until_complete(serve(app, cfg))
            return
        except OSError:
            logger.warning(f"端口 {port} 被占用，重试 ({attempt+1}/3)")
            threading.Event().wait(2)
        except Exception as e:
            logger.error(f"面板启动失败: {e}")
            return


@on_command("/panel")
@require_master
@plugin_handler
async def handle_panel(ctx: PluginContext):
    """查看面板地址 / 修改密码"""
    text = ctx.raw_text.strip()
    if text.startswith("/panel pwd"):
        args = text[len("/panel pwd"):].strip().split(maxsplit=1)
        if len(args) != 2:
            await ctx.reply("用法：/panel pwd <旧密码> <新密码>")
            return
        old_pw, new_pw = args
        if not verify_password(old_pw):
            await ctx.reply("❌ 旧密码错误")
            return
        ok, msg = validate_password(new_pw)
        if not ok:
            await ctx.reply(f"❌ {msg}")
            return
        change_password(old_pw, new_pw)
        await ctx.reply("✅ 面板密码已修改")
        logger.info(f"用户 {ctx.sender_id} 修改了面板密码")
        return

    port = get_port()
    lines = ["🖥️ LoyanUI 管理面板", ""]
    lines.append(f"  端口    {port}")
    lines.append(f"  本地  http://127.0.0.1:{port}")

    seen = set()
    for kind, addr in _get_ip_addresses():
        if addr in seen:
            continue
        seen.add(addr)
        label = "  IPv6" if kind == "IPv6" else "  局域网"
        url = f"http://[{addr}]:{port}" if kind == "IPv6" else f"http://{addr}:{port}"
        lines.append(f"{label}  {url}")

    pub = _get_public_ip()
    if pub:
        lines.append(f"  公网  http://{pub}:{port}")
    await ctx.reply("\n".join(lines))
    logger.info(f"用户 {ctx.sender_id} 查询面板地址")


def start_panel():
    global _t
    if _t and _t.is_alive():
        return
    _t = threading.Thread(target=_start, daemon=True, name="LoyanUI-Quart")
    _t.start()


start_panel()
