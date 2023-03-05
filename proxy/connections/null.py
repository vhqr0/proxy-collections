from ..decorators import override
from .base import BaseConnection


class NULLConnection(BaseConnection):
    @override(BaseConnection)
    async def close(self):
        pass

    @override(BaseConnection)
    async def read(self) -> bytes:
        return b''

    @override(BaseConnection)
    def read_nonblock(self) -> bytes:
        return b''

    @override(BaseConnection)
    async def write(self, buf: bytes):
        pass

    @override(BaseConnection)
    async def write_eof(self):
        pass
