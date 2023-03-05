from ..decorators import override
from ..connections import BaseConnection, NULLConnection
from .base import BaseConnector


class NULLConnector(BaseConnector):

    @override(BaseConnector)
    async def connect_to(
        self,
        addr: str,
        port: int,
        unwrite: bytes = b'',
    ) -> BaseConnection:
        return NULLConnection()
