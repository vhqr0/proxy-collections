import asyncio

from typing import Any

from ..decorators import override
from ..connections import BaseConnection, TCPConnection
from .base import BaseConnector


class TCPConnector(BaseConnector):
    tcp_kwargs: dict[str, Any]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tcp_kwargs = dict()

    def set_tcp_kwargs(self, **kwargs):
        self.tcp_kwargs = kwargs

    @override(BaseConnector)
    async def connect_to(
        self,
        addr: str,
        port: int,
        unwrite: bytes = b'',
    ) -> BaseConnection:
        reader, writer = await \
            asyncio.open_connection(addr, port, **self.tcp_kwargs)
        conn = TCPConnection(reader, writer)
        if len(unwrite) != 0:
            await conn.write(unwrite)
        return conn
