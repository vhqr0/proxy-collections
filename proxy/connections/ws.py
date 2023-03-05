import random
import struct

from ..decorators import override
from .base import BaseConnection


class WSConnection(BaseConnection):
    base_connection: BaseConnection
    mask_payload: bool

    def __init__(self,
                 base_connection: BaseConnection,
                 mask_paload: bool = True,
                 **kwargs):
        super().__init__(**kwargs)
        self.base_connection = base_connection
        self.mask_payload = mask_paload

    async def _write(self, flags: int, buf: bytes):
        if self.mask_payload:
            m = 0x80
            mask = random.randbytes(4)
            buf = bytes(c ^ mask[i % 4] for i, c in enumerate(buf))
        else:
            m = 0
            mask = b''
        blen = len(buf)
        if blen <= 125:
            header = struct.pack('!BB', flags, m + blen)
        elif blen <= 65535:
            header = struct.pack('!BBH', flags, m + 126, blen)
        else:
            header = struct.pack('!BBQ', flags, m + 127, blen)
        buf = header + mask + buf
        await self.base_connection.write(buf)

    @override(BaseConnection)
    async def close(self):
        await self._write(0x88, b'')

    @override(BaseConnection)
    async def read(self) -> bytes:
        if len(self.unread) != 0:
            return self.read_nonblock()
        buf = await self.base_connection.read()
        flags, blen = struct.unpack_from('!BB', buffer=buf, offset=0)
        buf = buf[2:]
        m, blen = blen & 0x80, blen & 0x7f
        if blen == 126:
            blen = struct.unpack_from('!H', buffer=buf, offset=0)
            buf = buf[2:]
        elif blen == 127:
            blen = struct.unpack_from('!Q', buffer=buf, offset=0)
            buf = buf[8:]
        if m != 0:
            mask, buf = buf[:4], buf[4:]
        while len(buf) < blen:
            buf += await self.base_connection.read()
        if len(buf) > blen:
            buf, self.base_connection.unread = buf[:blen], buf[blen:]
        if m != 0:
            buf = bytes(c ^ mask[i % 4] for i, c in enumerate(buf))
        op = flags & 0xf
        if op == 8:  # close
            return b''
        if op in (1, 2):  # text or binary
            return buf
        if op == 9:  # ping
            await self._write(0x8a, buf)
        if op in (0, 9, 0xa):  # continue, ping, pong
            return await self.read()
        raise RuntimeError('invalid server data')

    @override(BaseConnection)
    def read_nonblock(self) -> bytes:
        buf, self.unread = self.unread, b''
        return buf

    @override(BaseConnection)
    async def write(self, buf: bytes):
        await self._write(0x82, buf)

    @override(BaseConnection)
    async def write_eof(self):
        pass
