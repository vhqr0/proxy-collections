import random
import base64

from ..decorators import override
from ..connections import BaseConnection, WSConnection
from .base import BaseConnector


class WSConnector(BaseConnector):
    base_connector: BaseConnector
    path: str
    host: str

    def __init__(self, path: str = '/', host: str = 'localhost', **kwargs):
        super().__init__(**kwargs)
        self.path = path
        self.host = host

    @override(BaseConnector)
    async def connect_to(
        self,
        addr: str,
        port: int,
        unwrite: bytes = b'',
    ) -> BaseConnection:
        req = ('GET {} HTTP/1.1\r\n'
               'Host: {}\r\n'
               'Upgrade: websocket\r\n'
               'Connection: Upgrade\r\n'
               'Sec-WebSocket-Key: {}\r\n'
               'Sec-WebSocket-version: 13\r\n\r\n').format(
                   self.path, self.host,
                   base64.b64encode(random.randbytes(16)).decode())
        base_conn = await self.base_connector.connect_to(
            addr, port, req.encode())
        buf = await base_conn.read()
        headers, base_conn.unread = buf.split(b'\r\n\r\n', 1)
        if not headers.startswith(b'HTTP/1.1 101'):
            raise RuntimeError('invalid ws response')
        conn = WSConnection(base_connection=base_conn)
        if len(unwrite) != 0:
            await conn.write(unwrite)
        return conn
