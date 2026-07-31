import pytest
from loyan.core.loyan_adapter.platform.telegram.adapter import TelegramAdapter
from loyan.core.loyan_adapter.message import LoyanText


class TestTelegramAdapter:
    def test_init(self):
        adapter = TelegramAdapter(token="test:token")
        assert adapter._token == "test:token"

    @pytest.mark.asyncio
    async def test_get_platform_info_default(self):
        adapter = TelegramAdapter(token="test:token")
        info = await adapter.get_platform_info()
        assert info["platform"] == "Telegram"
        assert info["protocol_version"] == "Bot API 8.x"

    @pytest.mark.asyncio
    async def test_call_api_default(self):
        adapter = TelegramAdapter(token="test:token")
        result = await adapter.call_api("test", {})
        assert result is None
