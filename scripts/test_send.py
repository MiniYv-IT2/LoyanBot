"""通用消息测试脚本 — 向运行中的机器人注入伪造用户事件, 机器人回复到该用户

用法:
    python scripts/test_send.py --platform qq_official --sender <OpenID> --text "现在几点"
    python scripts/test_send.py --platform onebot --sender 123456 --text "/echo hi"
    python scripts/test_send.py --platform telegram --sender 987654321 --text "在吗"

原理: 调 bot 面板 API /api/loyanui/test/send 注入事件
      → bot 进程内 event_bus.publish → Pipeline(命令/AI兜底) → 适配器回复到该用户
"""
import argparse
import json
import sys

import httpx

PANEL_BASE = "http://127.0.0.1:5090"
PLATFORMS = {"onebot", "qq_official", "telegram", "satori"}


def main():
    parser = argparse.ArgumentParser(description="伪造消息事件测试机器人回复")
    parser.add_argument("--platform", required=True, choices=sorted(PLATFORMS), help="平台")
    parser.add_argument("--sender", required=True, help="用户ID(私聊=QQ号/OpenID/Telegram chat_id)")
    parser.add_argument("--text", required=True, help="要发送的消息文本(命令或自然语言)")
    parser.add_argument("--bot", default="", help="实例名(多实例时指定, 默认 default)")
    parser.add_argument("--panel", default=PANEL_BASE, help=f"面板地址(默认 {PANEL_BASE})")
    args = parser.parse_args()

    payload = {
        "platform": args.platform,
        "sender": args.sender,
        "text": args.text,
        "bot": args.bot,
    }
    r = httpx.post(
        f"{args.panel.rstrip('/')}/api/loyanui/test/send",
        json=payload,
        timeout=15,
    )
    print(f"HTTP {r.status_code}: {r.json()}")
    if r.status_code == 200:
        print(f"已注入事件: platform={args.platform} sender={args.sender} text={args.text!r}")
        print("机器人处理中, 查看 storage/logs/loyan.log 确认回复")
    else:
        print("注入失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
