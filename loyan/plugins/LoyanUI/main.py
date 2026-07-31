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
    require_master, Quart, send_from_directory, Config, serve,
)

from .auth import (
    create_token, get_port, verify_password, verify_token,
    change_password, validate_password, get_username,
    generate_captcha, verify_captcha,
)

from loyan.core.tools.schema_i18n import (
    build_schema_response,
    list_source_types,
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

async def _get_version() -> str:
    try:
        loop = asyncio.get_running_loop()
        data = await loop.run_in_executor(None, lambda: _read_toml(_METADATA_PATH))
        return data.get("plugin", {}).get("version", "0.0.0")
    except Exception:
        return "0.0.0"


def _read_toml(path: str) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


async def _get_ip_addresses():
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


async def _get_public_ip():
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get("https://api.ipify.org?format=json")
            return resp.json().get("ip", "")
    except Exception:
        return ""


def _create_app():
    from graci import request
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
        return {"success": True, "data": {"version": await _get_version()}}

    @app.route("/api/loyanui/adapter/types")
    async def adapter_types():
        from loyan.core.tools.schema_i18n import list_adapter_types
        return {"success": True, "data": await list_adapter_types()}

    @app.route("/api/loyanui/adapter/schema/<adapter_type>")
    async def adapter_schema(adapter_type):
        result = await build_schema_response(adapter_type)
        if result is None:
            return {"success": False, "error": "adapter.not_found"}, 404
        return {"success": True, "data": result}

    @app.route("/api/loyanui/stats")
    async def stats():
        try:
            from datetime import datetime
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
            from loyan.core.pipeline.stats_collector import stats_collector
            msg_stats = await stats_collector.get_stats(since=today_start)

            from loyan.core.plugin_manager import plugin_manager
            plugins = plugin_manager.get_plugin_count()

            from loyan.core.decorators.registration import DECORATOR_COMMAND_REGISTRY
            plugin_cmds = sum(len(p.get("commands", [])) for p in plugin_manager.registry)
            decorator_cmds = sum(len(e.get("commands", [])) for e in DECORATOR_COMMAND_REGISTRY)
            builtin_cmds = 4  # /关机 /重启 /开机 /关于
            total_commands = plugin_cmds + decorator_cmds + builtin_cmds

            uptime = 0.0
            try:
                from loyan.core.monitor import monitor_manager
                status = monitor_manager.get_system_status()
                uptime = status.get("uptime_seconds", 0)
            except Exception:
                from loyan.core.lifecycle.state.state_machine import lifecycle_state_machine
                uptime = lifecycle_state_machine.uptime

            return {
                "success": True,
                "data": {
                    "total_messages": msg_stats.get("total_messages", 0),
                    "total_commands": total_commands,
                    "uptime_seconds": uptime,
                    "plugins": plugins,
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}, 500

    # ── 实例管理 API ──

    @app.route("/api/loyanui/instances", methods=["GET"])
    async def panel_list_instances():
        from loyan.core.tools.paths import get_instances_dir
        from loyan.core.loyan_adapter.pool import adapter_pool
        import json
        base = get_instances_dir()
        if not os.path.isdir(base):
            return {"success": True, "data": []}
        items = []
        online_names = set()
        for adp, tg in adapter_pool._adapters.values():
            if getattr(adp, 'is_connected', True):
                online_names.add(tg.bot_name)
        for name in sorted(os.listdir(base)):
            cfg_path = os.path.join(base, name, "config.json")
            if os.path.isfile(cfg_path):
                with open(cfg_path, encoding="utf-8") as f:
                    cfg = json.load(f)
                cfg["_name"] = name
                status = "offline"
                if not cfg.get("enabled", True):
                    status = "disabled"
                elif name in online_names or cfg.get("bot_name", name) in online_names:
                    status = "online"
                cfg["_status"] = status
                items.append(cfg)
        return {"success": True, "data": items}

    @app.route("/api/loyanui/instances", methods=["POST"])
    async def panel_create_instance():
        from loyan.core.tools.paths import get_instances_dir
        from loyan.core.runtime.manager import start_instance
        import json
        data = await request.get_json()
        if not data or not data.get("name"):
            return {"success": False, "error": "name_required"}, 400
        name = data.pop("name")
        base = os.path.join(get_instances_dir(), name)
        os.makedirs(base, exist_ok=True)
        cfg_path = os.path.join(base, "config.json")
        data["enabled"] = data.get("enabled", True)
        data["bot_name"] = data.get("bot_name", name)
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        start_result = await start_instance(name)
        return {"success": start_result["success"]}

    @app.route("/api/loyanui/instances/<name>", methods=["PATCH"])
    async def panel_update_instance(name):
        from loyan.core.tools.paths import get_instances_dir
        from loyan.core.runtime.manager import reload_instance, rename_instance
        import json
        data = await request.get_json()
        if not data:
            return {"success": False, "error": "empty_body"}, 400
        cfg_path = os.path.join(get_instances_dir(), name, "config.json")
        if not os.path.isfile(cfg_path):
            return {"success": False, "error": "not_found"}, 404
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        old_bot_name = cfg.get("bot_name", name)
        new_bot_name = data.get("bot_name", old_bot_name)
        cfg.update(data)
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        if new_bot_name != name and new_bot_name != old_bot_name:
            rename_result = await rename_instance(name, new_bot_name)
            return {"success": rename_result["success"], "renamed": True}
        reload_result = await reload_instance(name)
        return {"success": reload_result["success"]}

    @app.route("/api/loyanui/instances/<name>/reload", methods=["POST"])
    async def panel_reload_instance(name):
        from loyan.core.runtime.manager import reload_instance
        result = await reload_instance(name)
        return result

    @app.route("/api/loyanui/qqbot/qr-login/create", methods=["POST"])
    async def qr_login_create():
        import secrets, base64, httpx
        from Crypto.Cipher import AES
        import logging, traceback
        bind_key = base64.b64encode(secrets.token_bytes(32)).decode("ascii")
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post("https://q.qq.com/lite/create_bind_task", json={"key": bind_key})
                data = resp.json()
            if data.get("retcode") != 0:
                logging.getLogger("LoyanUI").error("QR bind task failed: %s", traceback.format_exc())
                return {"success": False, "error": data.get("msg", "create failed")}, 400
            task_id = str(data.get("data", {}).get("task_id", ""))
            if not task_id:
                logging.getLogger("LoyanUI").error("QR bind task missing task_id: %s", traceback.format_exc())
                return {"success": False, "error": "missing task_id"}, 400
        except Exception:
            logging.getLogger("LoyanUI").error("QR bind task exception: %s", traceback.format_exc())
            return {"success": False, "error": "create exception"}, 500
        qr_url = f"https://q.qq.com/qqbot/openclaw/connect.html?task_id={task_id}&_wv=2"
        data2 = await request.get_json()
        color = (data2 or {}).get("color", "8ecac8")
        bgcolor = (data2 or {}).get("bgcolor", "ffffff")
        img_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={qr_url}&color={color}&bgcolor={bgcolor}"
        return {"success": True, "data": {"task_id": task_id, "bind_key": bind_key, "qr_img": img_url}}

    @app.route("/api/loyanui/qqbot/qr-login/poll", methods=["POST"])
    async def qr_login_poll():
        import base64, httpx
        from Crypto.Cipher import AES
        data = await request.get_json()
        task_id = data.get("task_id", "")
        bind_key = data.get("bind_key", "")
        if not task_id or not bind_key:
            return {"success": False, "error": "missing params"}, 400
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post("https://q.qq.com/lite/poll_bind_result", json={"task_id": task_id})
            poll_data = resp.json()
        if poll_data.get("retcode") != 0:
            return {"success": False, "error": poll_data.get("msg", "poll failed")}
        payload = poll_data.get("data", {})
        status = int(payload.get("status", 0))
        if status == 2:
            appid = str(payload.get("bot_appid", "")).strip()
            encrypted = str(payload.get("bot_encrypt_secret", "")).strip()
            if not appid or not encrypted:
                return {"success": False, "error": "missing credentials"}
            key = base64.b64decode(bind_key)
            raw = base64.b64decode(encrypted)
            nonce, tag, ct = raw[:12], raw[-16:], raw[12:-16]
            cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
            secret = cipher.decrypt_and_verify(ct, tag).decode("utf-8")
            return {"success": True, "data": {"status": "scanned", "appid": appid, "secret": secret}}
        elif status == 3:
            return {"success": True, "data": {"status": "expired"}}
        else:
            return {"success": True, "data": {"status": "pending"}}

    @app.route("/api/loyanui/instances/<name>/rename", methods=["POST"])
    async def panel_rename_instance(name):
        from loyan.core.runtime.manager import rename_instance
        data = await request.get_json()
        new_name = data.get("new_name", "").strip()
        if not new_name:
            return {"success": False, "error": "new_name_required"}, 400
        result = await rename_instance(name, new_name)
        return result

    @app.route("/api/loyanui/instances/<name>", methods=["DELETE"])
    async def panel_delete_instance(name):
        from loyan.core.tools.paths import get_instances_dir
        from loyan.core.runtime.manager import stop_instance
        import shutil
        await stop_instance(name)
        data = await request.get_json()
        a = data.get("a", 0)
        b = data.get("b", 0)
        op = data.get("op", "+")
        user_answer = data.get("answer")
        if op == "+":
            expected = a + b
        elif op == "-":
            expected = a - b
        else:
            return {"success": False, "error": "验证无效"}, 400
        if user_answer != expected:
            return {"success": False, "error": "验证答案错误"}, 400
        path = os.path.join(get_instances_dir(), name)
        if os.path.isdir(path):
            shutil.rmtree(path)
            return {"success": True}
        return {"success": False, "error": "not_found"}, 404

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
            await ctx.reply(" 旧密码错误")
            return
        ok, msg = validate_password(new_pw)
        if not ok:
            await ctx.reply(f" {msg}")
            return
        change_password(old_pw, new_pw)
        await ctx.reply(" 面板密码已修改")
        logger.info(f"用户 {ctx.sender_id} 修改了面板密码")
        return

    port = get_port()
    lines = [" LoyanUI 管理面板", ""]
    lines.append(f"  端口    {port}")
    lines.append(f"  本地  http://127.0.0.1:{port}")

    seen = set()
    for kind, addr in await _get_ip_addresses():
        if addr in seen:
            continue
        seen.add(addr)
        label = "  IPv6" if kind == "IPv6" else "  局域网"
        url = f"http://[{addr}]:{port}" if kind == "IPv6" else f"http://{addr}:{port}"
        lines.append(f"{label}  {url}")

    pub = await _get_public_ip()
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


threading.Timer(1.0, start_panel).start()
