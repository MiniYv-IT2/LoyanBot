"""BaseProvider — 模型提供商抽象基类"""

import logging
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Optional

from loyan.brain.provider.keystore import keystore

_logger = logging.getLogger("Brain.provider")

_registry: dict[str, type["BaseProvider"]] = {}


def register_provider(name: str):
    """装饰器：将 Provider 类注册到全局注册表"""
    def wrapper(cls):
        _registry[name] = cls
        cls._provider_name = name
        _logger.debug(f"注册提供商: {name}")
        return cls
    return wrapper


def get_provider_class(name: str) -> Optional[type["BaseProvider"]]:
    return _registry.get(name)


class BaseProvider(ABC):
    """模型提供商基类"""

    name: str = ""
    models: list[str] = []

    def __init__(self, config: dict):
        self.config = config
        self._client: Any = None
        self._api_key: str = ""
        self._api_base: str = ""

    async def open(self):
        """初始化连接，从 config 或 keystore 读取密钥"""
        self._api_key = self.config.get("api_key", "")
        if not self._api_key:
            self._api_key = await keystore.get(f"{self.name}.api_key") or ""
        self._api_base = self.config.get("api_base", "")
        if not self._api_base:
            self._api_base = await keystore.get(f"{self.name}.api_base") or ""

    async def close(self):
        """释放连接"""
        if self._client:
            try:
                await self._client.close()
            except Exception:
                pass
            self._client = None

    @abstractmethod
    async def chat(self, messages: list, model: str, **kwargs) -> str:
        """非流式对话"""

    @abstractmethod
    async def chat_stream(self, messages: list, model: str, **kwargs) -> AsyncIterator[str]:
        """流式对话"""

    @abstractmethod
    async def list_models(self) -> list[str]:
        """获取可用模型列表"""

    @property
    def api_key(self) -> str:
        return self._api_key

    @property
    def api_base(self) -> str:
        return self._api_base
