from asyncio import StreamReader, StreamWriter

from ..decorators import override
from .base import BaseConnection


class TCPConnection(BaseConnection):
    reader: StreamReader
    writer: StreamWriter

    def __init__(self, reader: StreamReader, writer: StreamWriter, **kwargs):
        super().__init__(**kwargs)
        self.reader = reader
        self.writer = writer

    @override(BaseConnection)
    async def close(self):
        self.writer.close()
        await self.writer.wait_closed()

    @override(BaseConnection)
    async def read(self) -> bytes:
        if len(self.unread) != 0:
            return self.read_nonblock()
        return await self.reader.read(4096)

    @override(BaseConnection)
    def read_nonblock(self) -> bytes:
        buf, self.unread = self.unread, b''
        return buf

    @override(BaseConnection)
    async def write(self, buf: bytes):
        self.writer.write(buf)
        await self.writer.drain()

    @override(BaseConnection)
    async def write_eof(self):
        if self.writer.can_write_eof():
            self.writer.write_eof()
