"""LoyanBot 适配器抽象基类 — 所有平台适配器必须实现此接口

设计原则：
- 适配层只定义契约，不关心具体协议
- 新增平台：只需新建一个平台目录，实现 LoyanAdapter 接口
- 无需修改本文件或上层框架代码
"""

from abc import ABC, abstractmethod
from typing import Callable, List, Optional

from loyan.core.loyan_adapter.event import LoyanEvent
from loyan.core.loyan_adapter.identity import IdentityTag
from loyan.core.loyan_adapter.message import LoyanMsg


class LoyanAdapter(ABC):
    """适配器抽象基类

    每个平台各有一个实现类。
    每个适配器实例应包含一个 IdentityTag，由调用方在 AdapterPool.register() 时设置。
    """

    @abstractmethod
    async def start(self, on_event: Callable[[LoyanEvent], None]) -> None:
        ...

    @abstractmethod
    async def send(self, target: str, segments: List[LoyanMsg], chat_type: str) -> bool:
        ...

    @abstractmethod
    async def stop(self) -> None:
        ...

    async def call_api(self, action: str, params: dict = None) -> Optional[dict]:
        return None

    @abstractmethod
    async def get_platform_info(self) -> dict:
        """获取平台/机器人统计信息（所有平台必须实现）

        返回统一结构，各平台自行填充：
        {
            "friend_count": int | None,     # 好友/联系人数量，不支持返回 None
            "group_count": int | None,      # 群组/频道数量，不支持返回 None
            "platform": str,                # 平台标识
            "protocol_version": str | None, # 协议端版本，不支持返回 None
        }
        """

    def parse_http_request(self, body: dict) -> Optional[LoyanEvent]:
        """将 HTTP 请求体解析为 LoyanEvent（可选，仅支持 HTTP 入站的适配器实现）

        默认返回 None，表示不支持 HTTP 入站。

        Args:
            body: HTTP 请求体（已解析为 dict）

        Returns:
            解析成功返回 LoyanEvent，失败或不支持返回 None
        """
        return None

    def parse_business_event(self, raw: dict) -> Optional["BusinessEvent"]:
        """平台事件 → BusinessEvent；不认识/不支持返回 None（可选实现）

        可选实现：不实现则业务事件被忽略（默认行为）。
        实现位置不限：adapter.py 内联或拆 business.py re-export。
        """
        return None

    @property
    def tag(self) -> Optional[IdentityTag]:
        """获取适配器身份标签

        由 AdapterPool.register() 在注册时设置。
        子类可以覆盖此属性返回固定 tag。
        """
        return getattr(self, '_tag', None)

    @tag.setter
    def tag(self, value: IdentityTag) -> None:
        """设置适配器身份标签"""
        self._tag = value

    @property
    def is_connected(self) -> bool:
        """是否已连接

        各平台根据自身协议判断连通性。
        如果子类有 is_ws_connected 方法则调用它，否则返回 True。
        """
        ws_check = getattr(self, 'is_ws_connected', None)
        if ws_check is not None:
            return ws_check()
        return False

    def register_routes(self, app) -> None:
        """注册 HTTP 路由到框架应用（可选，仅需 HTTP 入站的适配器实现）

        默认空实现。

        Args:
            app: Quart 应用实例
        """
        pass
