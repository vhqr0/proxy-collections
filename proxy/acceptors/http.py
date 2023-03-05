import re
import struct
import socket

from ..decorators import override
from ..connections import BaseConnection
from .base import BaseAcceptor


class HTTPAcceptor(BaseAcceptor):

    http_req_re = re.compile(r'^(\w+) [^ ]+ (HTTP/[^ \r\n]+)\r\n')
    http_host_re = re.compile(
        r'\r\nHost: ([^ :\[\]\r\n]+|\[[:0-9a-fA-F]+\])(:([0-9]+))?')

    @override(BaseAcceptor)
    async def accept(self, conn: BaseConnection) -> tuple[str, int, bytes]:
        buf = await conn.read()
        if buf[0] == 5:
            return await self.accept_dispatch_socks5(buf, conn)
        else:
            return await self.accept_dispatch_http(buf, conn)

    async def accept_dispatch_socks5(
        self,
        buf: bytes,
        conn: BaseConnection,
    ) -> tuple[str, int, bytes]:
        nmeths = buf[1]
        ver, nmeths, meths = struct.unpack(f'!BB{nmeths}s', buf)
        if ver != 5 or 0 not in meths:
            raise RuntimeError('invalid socks5 request')
        await conn.write(b'\x05\x00')
        buf = await conn.read()
        if buf[3] == 3:  # domain
            ver, cmd, rsv, _, _, addr_bytes, port = struct.unpack(
                f'!BBBBB{buf[4]}sH', buf)
            addr = addr_bytes.decode()
        elif buf[3] == 1:  # ipv4
            ver, cmd, rsv, _, addr_bytes, port = struct.unpack('!BBBB4sH', buf)
            addr = socket.inet_ntop(socket.AF_INET, addr_bytes)
        elif buf[3] == 4:  # ipv6
            ver, cmd, rsv, _, addr_bytes, port = struct.unpack(
                '!BBBB16sH', buf)
            addr = socket.inet_ntop(socket.AF_INET6, addr_bytes)
        else:
            raise RuntimeError('invalid socks5 header')
        if ver != 5 or cmd != 1 or rsv != 0:
            raise RuntimeError('invalid socks5 header')
        await conn.write(b'\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00')
        return addr, port, b''

    async def accept_dispatch_http(
        self,
        buf: bytes,
        conn: BaseConnection,
    ) -> tuple[str, int, bytes]:
        headers_bytes, unwrite = buf.split(b'\r\n\r\n', 1)
        headers = headers_bytes.decode()
        req = self.http_req_re.search(headers)
        host = self.http_host_re.search(headers)
        if req is None or host is None:
            raise RuntimeError('invalid http request')
        meth, ver, addr = req[1], req[2], host[1]
        assert meth is not None and ver is not None and addr is not None
        port = 80 if host[3] is None else int(host[3])
        if addr[0] == '[':
            addr = addr[1:-1]
        if meth == 'CONNECT':
            res = \
                f'{ver} 200 Connection Established\r\nConnection close\r\n\r\n'
            await conn.write(res.encode())
        else:
            headers = '\r\n'.join(header for header in headers.split('\r\n')
                                  if not header.startswith('Proxy-'))
            unwrite = headers.encode() + b'\r\n\r\n' + unwrite
        return addr, port, unwrite
