from .adapter import TelegramAdapter


def create_adapter(config: dict) -> "TelegramAdapter":
    if not config.get("token"):
        raise ValueError("Telegram 适配器缺少必填字段: token")
    adapter = TelegramAdapter(
        token=config["token"],
        proxy_url=config.get("proxy_url", ""),
        webhook_url=config.get("webhook_url", ""),
        webhook_port=config.get("webhook_port", 8443),
        config_path=config.get("_config_path", ""),
    )
    adapter.conn_type_display = "长轮询"
    return adapter
