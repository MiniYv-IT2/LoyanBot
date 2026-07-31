"""/panel 聊天命令 — 查看面板地址 / 修改密码"""

import httpx

from graci import PluginContext, get_logger, on_command, plugin_handler, require_master

from loyan.core.webserv.panel.auth import (
    change_password, get_port, validate_password, verify_password,
)

logger = get_logger("Panel")


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


@on_command("/panel")
@require_master
@plugin_handler
async def handle_panel(ctx: PluginContext):
    """查看面板地址 / 修改密码"""
    text = ctx.raw_text.strip()
    if text.startswith("/panel pwd"):
        args = text[len("/panel pwd"):].strip().split(maxsplit=1)
        if len(args) != 2:
            await ctx.reply("Usage: /panel pwd <old> <new>")
            return
        old_pw, new_pw = args
        if not verify_password(old_pw):
            await ctx.reply("Old password incorrect")
            return
        ok, msg = validate_password(new_pw)
        if not ok:
            await ctx.reply(f" {msg}")
            return
        change_password(old_pw, new_pw)
        await ctx.reply("Panel password updated")
        logger.info(f"User {ctx.sender_id} changed panel password")
        return

    port = get_port()
    lines = ["LoyanUI Panel", ""]
    lines.append(f"  Port    {port}")
    lines.append(f"  Local  http://127.0.0.1:{port}")

    seen = set()
    for kind, addr in await _get_ip_addresses():
        if addr in seen:
            continue
        seen.add(addr)
        label = "  IPv6" if kind == "IPv6" else "  LAN"
        url = f"http://[{addr}]:{port}" if kind == "IPv6" else f"http://{addr}:{port}"
        lines.append(f"{label}  {url}")

    pub = await _get_public_ip()
    if pub:
        lines.append(f"  Public  http://{pub}:{port}")
    await ctx.reply("\n".join(lines))
    logger.info(f"User {ctx.sender_id} queried panel address")
