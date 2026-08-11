"""LoyanBot CLI 主入口 — Typer 应用"""
import os
import sys
from pathlib import Path
from typing import Optional

# Windows 终端编码修复（避免 CP936 崩 emoji/特殊字符）
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
sys._called_from_cli = True  # 标记 CLI 入口，让 logger_manager 跳过 chcp 65001

import typer

from .plugins import (
    list_plugins,
    install_plugin,
    update_plugin,
    remove_plugin,
)
from .system import (
    setup_autostart,
    uninstall_bot,
    backup_bot,
    stop_bot_process,
)
from loyan.core.tools.paths import get_config_path, get_plugins_dir
from .instances import instance_cli
from .update import update_cli
from .utils import find_project_root, is_local_project, get_platform_label, in_venv, pip_install
from loyan.core.plugin_manager import plugin_manager
import json

# ── Typer App ──
loyan_cli = typer.Typer(
    name="loyan",
    help="LoyanBot 命令行管理工具",
    no_args_is_help=True,
    add_completion=True,
)

# ── 子命令组 ──
plugin_cli = typer.Typer(help="插件管理")
config_cli = typer.Typer(help="配置管理")
loyan_cli.add_typer(plugin_cli, name="plugin")
loyan_cli.add_typer(config_cli, name="config")
loyan_cli.add_typer(instance_cli, name="instance")
loyan_cli.add_typer(update_cli, name="update")


# ── 共用函数 ──
def _ensure_root() -> Path:
    """获取项目根目录（本地项目或 pip 安装后的当前工作目录）"""
    root = find_project_root()
    if root:
        return root
    # pip 安装模式：当前目录作为工作目录
    return Path.cwd()


def _ensure_local_root() -> Path:
    """仅限本地项目（需要 bot.py 和 plugins/ 目录）"""
    root = find_project_root()
    if root and is_local_project(root):
        return root
    typer.echo(" This command must be run in the LoyanBot project directory")
    typer.echo("   cd to the directory containing bot.py, or clone the project repository")
    raise typer.Exit(1)


# ═══════════════════════════ 核心命令 ═══════════════════════════


@loyan_cli.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """无参数时显示帮助"""
    if ctx.invoked_subcommand is None:
        typer.echo(loyan_cli.get_help())


@loyan_cli.command("run")
def cmd_run(
    debug: bool = typer.Option(False, "--debug", "-d", help="调试模式"),
    no_webui: bool = typer.Option(False, "--no-webui", help="不启动 Web 面板"),
):
    """启动机器人"""
    import asyncio
    from loyan.core.main import run_bot

    if debug:
        os.environ["GRACY_DEBUG"] = "1"
    elif "GRACY_DEBUG" in os.environ:
        del os.environ["GRACY_DEBUG"]
    if no_webui:
        os.environ["GRACY_NO_WEBUI"] = "1"
    elif "GRACY_NO_WEBUI" in os.environ:
        del os.environ["GRACY_NO_WEBUI"]

    typer.echo("   Starting LoyanBot ...")
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        typer.echo("\n   Stopped")
    except Exception as e:
        typer.echo(f"   Startup failed: {e}")
        sys.exit(1)


@loyan_cli.command("stop")
def cmd_stop():
    """停止机器人"""
    stop_bot_process()


@loyan_cli.command("restart")
def cmd_restart(
    debug: bool = typer.Option(False, "--debug", "-d", help="调试模式"),
    no_webui: bool = typer.Option(False, "--no-webui", help="不启动 Web 面板"),
):
    """重启机器人"""
    cmd_stop()
    cmd_run(debug=debug, no_webui=no_webui)


@loyan_cli.command("status")
def cmd_status():
    """查看运行状态"""
    root = _ensure_root()
    plat = get_platform_label()

    # 懒加载避免触发机器人日志系统
    from loyan.core.config import BOT_VERSION, MASTER_ID
    from loyan.core.loyan_adapter.pool import adapter_pool

    default = adapter_pool.get_default()
    robot_id = getattr(default, '_instance_robot_id', '') if default else ''

    typer.echo(f"  LoyanBot {BOT_VERSION}")
    typer.echo(f"  Project path: {root}")
    typer.echo(f"  Bot ID: {robot_id or '(not set)'}  |  Master: {MASTER_ID}")
    typer.echo(f"  Platform: {plat}  |  Virtualenv: {'yes' if in_venv() else 'no'}")
    typer.echo(f"  Python: {sys.version.split()[0]}")

    # 检查进程
    import subprocess
    try:
        from loyan.core.config import config_manager
        port = config_manager.get("http_port", 3002)

        if plat == "windows":
            r = subprocess.run(
                f'netstat -ano | findstr ":{port}" 2>nul',
                capture_output=True, text=True, shell=True, timeout=5
            )
            running = bool(r.stdout.strip())
        else:
            r = subprocess.run(
                f'netstat -tlnp 2>/dev/null | grep ":{port} "',
                capture_output=True, text=True, shell=True, timeout=5
            )
            running = bool(r.stdout.strip())
        typer.echo(f"  Status: {'running' if running else '⏹  not running'}")
    except Exception:
        typer.echo("  Status: cannot detect")


@loyan_cli.command("version")
def cmd_version():
    """显示版本"""
    from loyan.core.config import BOT_VERSION as v
    typer.echo(f"LoyanBot {v}")


# ═══════════════════════════ 快捷命令 ═══════════════════════════


@loyan_cli.command("ins")
def cmd_ins(
    package: str = typer.Argument(..., help="包名或插件目录名"),
    is_plugin: bool = typer.Option(False, "--plugin", "-p", help="安装插件依赖"),
):
    """快速安装包 / 插件依赖"""
    # 先检查是否是已有插件目录名
    if not is_plugin:
        root = find_project_root() or Path.cwd()
        plugins_dir = root / "plugins"
        existing = plugins_dir / package
        if existing.is_dir() and (existing / "requirements.txt").exists():
            # 自动走插件依赖安装
            req = existing / "requirements.txt"
            typer.echo(f"   Plugin {package} detected, installing dependencies...")
            pip_install([], req_file=str(req))
            typer.echo("   Installation complete")
            return

    # 普通 Python 包安装
    typer.echo(f"   Installing {package}...")
    pip_install([package])
    typer.echo("   Installation complete")


@loyan_cli.command("set")
def cmd_set(
    key: str = typer.Argument(..., help="配置项 (master / bot)"),
    value: str = typer.Argument(..., help="配置值"),
):
    """快捷设置配置"""
    cfg_file = Path(get_config_path())

    key_map = {
        "master": "master_id",
        "bot": "robot_id",
        "master_id": "master_id",
        "robot_id": "robot_id",
    }
    real_key = key_map.get(key, key)
    if real_key not in ("master_id", "robot_id"):
        typer.echo(f"   Unsupported config key: {key}")
        typer.echo("  Supported: master, bot (robot)")
        raise typer.Exit(1)

    cfg = {}
    if cfg_file.exists():
        cfg = json.loads(cfg_file.read_text(encoding="utf-8"))

    cfg[real_key] = value
    cfg_file.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    typer.echo(f"   {real_key} = {value}")


# ═══════════════════════════ 插件管理 ═══════════════════════════


@plugin_cli.command("list")
def cmd_plugin_list():
    """列出已安装插件（系统内置 + 用户安装）"""
    root = _ensure_root()
    plugins = list_plugins(root)
    if not plugins:
        typer.echo("  ℹ  No plugins installed")
        return
    typer.echo(f"  {len(plugins)} plugins in total:")
    for p in plugins:
        mark = "[系统]" if p["source"] == "system" else "[用户]"
        deps = " " if p["has_requirements"] else ""
        typer.echo(f"    {mark} {p['name']}{deps}")


@plugin_cli.command("install")
def cmd_plugin_install(
    source: str = typer.Argument(..., help="user/repo / 本地路径 / Git URL"),
):
    """安装插件（商店优先，失败回退 git clone；自动安装依赖）"""
    root = _ensure_root()
    install_plugin(root, source)


@plugin_cli.command("update")
def cmd_plugin_update(
    name: str = typer.Argument(..., help="插件名称（目录名）"),
):
    """更新插件（商店插件自动备份回滚）"""
    root = _ensure_root()
    update_plugin(root, name)


@plugin_cli.command("remove")
def cmd_plugin_remove(
    name: str = typer.Argument(..., help="插件名称（目录名）"),
):
    """卸载用户插件"""
    root = _ensure_root()
    remove_plugin(root, name)


@loyan_cli.command("disable")
def cmd_disable(
    name: str = typer.Argument(..., help="插件目录名"),
):
    """禁用插件（下次启动生效）"""
    root = find_project_root() or Path.cwd()
    plugins_dir = Path(get_plugins_dir())
    target = plugins_dir / name
    if not target.is_dir():
        typer.echo(f"   Plugin {name} not found (dir: {plugins_dir})")
        raise typer.Exit(1)

    disabled = plugin_manager.load_disabled_plugins()
    if name in disabled:
        typer.echo(f"   Plugin {name} is disabled")
        return
    disabled.add(name)
    plugin_manager.save_disabled_plugins(disabled)
    typer.echo(f"   Disabled plugin {name} (takes effect on next start)")
    typer.echo("   If the bot is running, restart it or use the panel")


@loyan_cli.command("enable")
def cmd_enable(
    name: str = typer.Argument(..., help="插件目录名"),
):
    """启用插件（下次启动生效）"""
    disabled = plugin_manager.load_disabled_plugins()
    if name not in disabled:
        typer.echo(f"  ℹ Plugin {name} is not disabled")
        return
    disabled.discard(name)
    plugin_manager.save_disabled_plugins(disabled)
    typer.echo(f"   Enabled plugin {name} (takes effect on next start)")


@loyan_cli.command("disabled")
def cmd_disabled():
    """查看已禁用的插件"""
    disabled = plugin_manager.load_disabled_plugins()
    if not disabled:
        typer.echo("  ℹ No disabled plugins")
        return
    typer.echo(f"  {len(disabled)} disabled plugins in total:")
    for p in sorted(disabled):
        typer.echo(f"    • {p}")


# ═══════════════════════════ 配置管理 ═══════════════════════════


@config_cli.command("show")
def cmd_config_show():
    """查看配置"""
    cfg_file = Path(get_config_path())
    if cfg_file.exists():
        import json
        cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
        for k, v in cfg.items():
            v_str = str(v)
            if len(v_str) > 60:
                v_str = v_str[:57] + "..."
            typer.echo(f"  {k}: {v_str}")
    else:
        typer.echo("  ℹ  Config file not found")


@config_cli.command("edit")
def cmd_config_edit():
    """编辑配置（打开系统编辑器）"""
    cfg_file = Path(get_config_path())
    if not cfg_file.exists():
        cfg_file.write_text("{\n  \n}\n", encoding="utf-8")
    plat = get_platform_label()
    try:
        if plat == "windows":
            subprocess.run(["notepad", str(cfg_file)], check=True)
        elif plat == "macos":
            subprocess.run(["open", str(cfg_file)], check=True)
        else:
            editor = (subprocess.run(
                ["which", "nano", "vim", "vi"],
                capture_output=True, text=True
            ).stdout.split()[0])
            subprocess.run([editor, str(cfg_file)], check=True)
        typer.echo("   Config saved")
    except Exception as e:
        typer.echo(f"   Cannot open editor: {e}")
        typer.echo(f"   Edit manually: {cfg_file}")


# ═══════════════════════════ 系统管理 ═══════════════════════════


@loyan_cli.command("autostart")
def cmd_autostart(
    enable: bool = typer.Argument(True, help="true=启用, false=禁用"),
):
    """设置开机自启"""
    root = _ensure_local_root()
    setup_autostart(root, enable=enable)


@loyan_cli.command("backup")
def cmd_backup():
    """备份机器人（代码 + 数据）"""
    root = _ensure_local_root()
    backup_bot(root)


@loyan_cli.command("uninstall")
def cmd_uninstall(
    no_backup: bool = typer.Option(False, "--no-backup", help="不备份直接卸载"),
):
    """卸载机器人"""
    root = _ensure_local_root()
    typer.echo(f"   About to uninstall LoyanBot: {root}")
    if not no_backup:
        typer.echo("   A backup will be created first")
    if typer.confirm("  确定继续？"):
        uninstall_bot(root, backup_first=not no_backup)
    else:
        typer.echo("   Cancelled")


@loyan_cli.command("info")
def cmd_info():
    """显示系统环境信息"""
    import platform
    typer.echo(f"  System: {platform.system()} {platform.release()}")
    typer.echo(f"  Python: {sys.version}")
    typer.echo(f"  Virtualenv: {in_venv()}")
    typer.echo(f"  Current dir: {Path.cwd()}")
    root = find_project_root()
    typer.echo(f"  Project root: {root or 'not found (pip mode)'}")


# ── 直接运行入口 ──
if __name__ == "__main__":
    loyan_cli()
