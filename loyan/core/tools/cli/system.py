"""系统管理 — 自启/卸载/备份/进程控制"""
import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import typer

from .utils import find_project_root, get_platform_label, has_systemd, make_archive


def setup_autostart(root: Path, enable: bool = True) -> bool:
    """设置开机自启

    策略:
      - Windows: schtasks（无需管理员，当前用户级）
      - Linux + systemd → systemctl --user
      - Linux + Termux → ~/.bashrc
      - macOS → launchctl plist
      - 其他 → ~/.bashrc
    """
    plat = get_platform_label()
    python = sys.executable
    script = str(root / "bot.py")

    if enable:
        return _enable_autostart(plat, python, script, root)
    else:
        return _disable_autostart(plat, python, script, root)


def _enable_autostart(plat: str, python: str, script: str, root: Path) -> bool:
    try:
        if plat == "windows":
            name = "LoyanBot"
            username = os.environ.get("USERNAME", "")
            # 方式1：启动文件夹（无需管理员，推荐）
            startup = Path(os.environ.get(
                "APPDATA", ""
            )) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
            if startup.exists():
                bat = startup / f"{name}.bat"
                # Windows CMD 读取 .bat 使用系统默认编码（中文环境为 GBK）
                # cd /d 确保切到项目目录，否则 CWD 为 C:\Windows\System32
                bat.write_text(
                    f'@cd /d "{root}"\n@start "" "{python}" "{script}"\n',
                    encoding="gbk"
                )
                typer.echo("   Autostart enabled (Startup folder)")
                return True
            # 方式2：schtasks（需管理员，降级）
            task = f'''schtasks /create /tn "{name}" /tr "\"{python}\" \"{script}\"" /sc onlogon /f'''
            subprocess.check_call(task, shell=True, timeout=10)
            typer.echo("   Autostart enabled (Windows Task Scheduler)")
            return True

        elif plat == "linux" and has_systemd():
            unit = f"""[Unit]
Description=LoyanBot
After=network.target

[Service]
Type=simple
ExecStart={python} {script}
WorkingDirectory={root}
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
"""
            unit_path = Path.home() / ".config" / "systemd" / "user" / "loyan.service"
            unit_path.parent.mkdir(parents=True, exist_ok=True)
            unit_path.write_text(unit, encoding="utf-8")
            subprocess.check_call(["systemctl", "--user", "daemon-reload"], timeout=10)
            subprocess.check_call(["systemctl", "--user", "enable", "loyan"], timeout=10)
            typer.echo("   Autostart enabled (systemd --user)")
            return True

        elif plat == "termux":
            bashrc = Path.home() / ".bashrc"
            line = f"(cd {root} && {python} {script} &)"
            if line not in bashrc.read_text(encoding="utf-8"):
                with open(bashrc, "a", encoding="utf-8") as f:
                    f.write(f"\n# LoyanBot autostart\n{line}\n")
            typer.echo("   Autostart enabled (Termux ~/.bashrc)")
            return True

        elif plat == "macos":
            label = "com.loyan.runner"
            plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>{label}</string>
<key>ProgramArguments</key><array><string>{python}</string><string>{script}</string></array>
<key>WorkingDirectory</key><string>{root}</string>
<key>RunAtLoad</key><true/>
<key>KeepAlive</key><true/>
<key>StandardOutPath</key><string>{root}/logs/stdout.log</string>
<key>StandardErrorPath</key><string>{root}/logs/stderr.log</string>
</dict></plist>"""
            plist_path = Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"
            plist_path.parent.mkdir(parents=True, exist_ok=True)
            plist_path.write_text(plist, encoding="utf-8")
            subprocess.check_call(["launchctl", "load", str(plist_path)], timeout=10)
            typer.echo("   Autostart enabled (macOS LaunchAgent)")
            return True

        else:
            # 降级 ~/.bashrc / ~/.zshrc
            for rc in [Path.home() / ".bashrc", Path.home() / ".zshrc"]:
                if rc.exists():
                    text = rc.read_text(encoding="utf-8")
                    line = f"(cd {root} && {python} {script} &)"
                    if line not in text:
                        with open(rc, "a", encoding="utf-8") as f:
                            f.write(f"\n# LoyanBot autostart\n{line}\n")
                    break
            typer.echo("   Autostart enabled (~/.bashrc)")
            return True

    except Exception as e:
        typer.echo(f"   Autostart setup failed: {e}")
        typer.echo(f"   Add autostart manually: {python} {script}")
        return False


def _disable_autostart(plat: str, python: str, script: str, root: Path) -> bool:
    try:
        if plat == "windows":
            # 删启动文件夹脚本
            startup = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "LoyanBot.bat"
            if startup.exists():
                startup.unlink()
            # 删 schtasks（可能不存在，容错）
            try:
                subprocess.check_call("schtasks /delete /tn LoyanBot /f", shell=True, timeout=10)
            except Exception:
                pass
            typer.echo("   Autostart removed")
            return True
        elif plat == "linux" and has_systemd():
            subprocess.check_call(["systemctl", "--user", "disable", "loyan"], timeout=10)
            unit = Path.home() / ".config" / "systemd" / "user" / "loyan.service"
            if unit.exists():
                unit.unlink()
            subprocess.check_call(["systemctl", "--user", "daemon-reload"], timeout=10)
            typer.echo("   systemd autostart removed")
            return True
        elif plat == "macos":
            label = "com.loyan.runner"
            plist_path = Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"
            subprocess.check_call(["launchctl", "unload", str(plist_path)], timeout=10)
            if plist_path.exists():
                plist_path.unlink()
            typer.echo("   macOS autostart removed")
            return True
        else:
            typer.echo("   Remove the LoyanBot startup line from ~/.bashrc manually")
            return False
    except Exception as e:
        typer.echo(f"   Autostart removal failed: {e}")
        return False


def uninstall_bot(root: Path, backup_first: bool = True):
    """卸载 LoyanBot

    步骤:
      1. 可选备份
      2. 移除自启
      3. 删除目录
    """
    if backup_first:
        typer.echo("   Backing up first...")
        bak_dir = Path.cwd() / "loyan_backup"
        bak_dir.mkdir(exist_ok=True)
        archive = make_archive(root, bak_dir)
        if archive:
            typer.echo(f"   Backup complete: {archive}")
    _disable_autostart(get_platform_label(), sys.executable, str(root / "bot.py"), root)
    typer.echo(f"   Removing {root} ...")
    shutil.rmtree(root, ignore_errors=True)
    typer.echo("   LoyanBot uninstalled")


def backup_bot(root: Path) -> Optional[Path]:
    """备份机器人（数据 + 代码）"""
    bak_dir = Path.cwd() / "loyan_backup"
    bak_dir.mkdir(exist_ok=True)
    archive = make_archive(root, bak_dir)
    if archive:
        typer.echo(f"   Backup complete: {archive}")
    else:
        typer.echo("   Backup failed")
    return archive


def stop_bot_process():
    """停止运行中的 LoyanBot（通过进程名 + 命令行匹配）"""
    plat = get_platform_label()
    current_pid = os.getpid()

    try:
        if plat == "windows":
            # 用 PowerShell Get-CimInstance 按命令行匹配 bot.py 进程，跳过自己
            killed = False
            ps_script = (
                'Get-CimInstance -Query "SELECT ProcessId,CommandLine FROM Win32_Process '
                "WHERE Name='python.exe'\" | "
                f"Where-Object {{ $_.CommandLine -match 'bot\\.py' -and $_.ProcessId -ne {current_pid} }} | "
                'ForEach-Object { $_.ProcessId }'
            )
            r = subprocess.run(
                ['powershell', '-NoProfile', '-Command', ps_script],
                capture_output=True, text=True, timeout=10
            )
            for pid_str in r.stdout.strip().split("\n"):
                pid_str = pid_str.strip()
                if not pid_str.isdigit():
                    continue
                subprocess.run(f'taskkill /f /pid {pid_str} 2>nul', shell=True, timeout=5)
                killed = True
            if killed:
                typer.echo("   Stopped")
            else:
                typer.echo("   No running LoyanBot found")
        else:
            subprocess.check_call(
                ["pkill", "-f", "python.*bot.py"],
                timeout=5,
            )
            typer.echo("   Stopped")
    except Exception as e:
        typer.echo(f"   Stop failed: {e}")
