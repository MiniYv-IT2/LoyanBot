"""本体更新命令 — loyan update check / apply / rollback"""

import asyncio
import sys

import typer

from loyan import __version__ as CURRENT_VERSION

update_cli = typer.Typer(help="机器人本体更新")


@update_cli.command("check")
def cmd_update_check():
    """检查是否有新版本"""
    from loyan.core.update_manager import update_manager

    async def _run():
        info = await update_manager.check()
        await update_manager.close()
        return info

    info = asyncio.run(_run())
    if info.get("error"):
        typer.echo(f"  检查失败: {info['error']}")
        return
    typer.echo(f"  当前版本: v{info.get('current') or CURRENT_VERSION}")
    typer.echo(f"  最新版本: v{info['latest']}")
    if info.get("available"):
        typer.echo("  发现新版本!")
        changelog = (info.get("changelog") or "").strip()
        if changelog:
            typer.echo("  ── 更新日志 ──")
            for line in changelog.splitlines()[:40]:
                typer.echo(f"  {line}")
        typer.echo("  执行 `loyan update apply` 开始更新")
    else:
        typer.echo("  已是最新版本")


@update_cli.command("apply")
def cmd_update_apply():
    """下载并应用更新（校验失败不执行；完成后需重启）"""
    from loyan.core.update_manager import update_manager

    async def _run():
        result = await update_manager.apply()
        await update_manager.close()
        return result

    result = asyncio.run(_run())
    if result.get("success"):
        typer.echo(f"  ✅ {result['message']}")
        if result.get("pip"):
            return
        if typer.confirm("  立即重启机器人?"):
            _restart()
    else:
        typer.echo(f"  ❌ 更新失败: {result.get('message')}")


@update_cli.command("rollback")
def cmd_update_rollback():
    """回滚到上一个版本（从备份恢复）"""
    from loyan.core.update_manager import update_manager

    result = update_manager.rollback()
    if result.get("success"):
        typer.echo(f"  ✅ {result['message']}")
        if typer.confirm("  立即重启机器人?"):
            _restart()
    else:
        typer.echo(f"  ❌ 回滚失败: {result.get('message')}")


def _restart():
    import subprocess
    try:
        subprocess.run(["systemctl", "restart", "loyan"], check=True)
        typer.echo("  已触发重启")
    except Exception:
        typer.echo("  请手动重启服务")
