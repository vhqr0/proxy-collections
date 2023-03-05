from typing import Optional

from ..defaults import (
    WEIGHT_INITIAL,
    WEIGHT_MINIMAL,
    WEIGHT_MAXIMAL,
    WEIGHT_INCREASE_STEP,
    WEIGHT_DECREASE_STEP,
)
from ..decorators import override
from ..connections import BaseConnection


class BaseConnector:
    name: str
    weight: float

    def __init__(self,
                 name: Optional[str] = None,
                 weight: float = WEIGHT_INITIAL):
        self.name = name if name is not None else type(self).__name__
        self.weight = weight

    def __str__(self) -> str:
        return f'{self.name} W{self.weight}'

    def weight_increase(self):
        self.weight = min(self.weight + WEIGHT_INCREASE_STEP, WEIGHT_MAXIMAL)

    def weight_decrease(self):
        self.weight = max(self.weight - WEIGHT_DECREASE_STEP, WEIGHT_MINIMAL)

    async def connect_to(
        self,
        addr: str,
        port: int,
        unwrite: bytes = b'',
    ) -> BaseConnection:
        raise NotImplementedError


class WrappedConnector(BaseConnector):
    base_connector: BaseConnector
    addr: str
    port: int

    def __init__(self,
                 base_connector: BaseConnector,
                 addr: str = '',
                 port: int = -1,
                 **kwargs):
        super().__init__(**kwargs)
        self.base_connector = base_connector
        self.addr = addr
        self.port = port

    async def connect(self, unwrite: bytes = b'') -> BaseConnection:
        return await self.base_connector.connect_to(self.addr, self.port,
                                                    unwrite)

    @override(BaseConnector)
    async def connect_to(
        self,
        addr: str,
        port: int,
        unwrite: bytes = b'',
    ) -> BaseConnection:
        return await self.connect(unwrite)
