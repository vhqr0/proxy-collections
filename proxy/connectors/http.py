from ..decorators import override
from ..connections import BaseConnection
from .base import BaseConnector, WrappedConnector


class HTTPConnector(BaseConnector):
    base_connector: WrappedConnector

    def __init__(self, base_connector: WrappedConnector, **kwargs):
        super().__init__(**kwargs)
        self.base_connector = base_connector

    @override(BaseConnector)
    async def connect_to(
        self,
        addr: str,
        port: int,
        unwrite: bytes = b'',
    ) -> BaseConnection:
        if addr.find(':') >= 0:
            addr = f'[{addr}]'
        host = f'{addr}:{port}'
        req = 'CONNECT {} HTTP/1.1\r\nHost: {}\r\n\r\n'.format(host, host)
        conn = await self.base_connector.connect(req.encode())
        buf = await conn.read()
        headers, conn.unread = buf.split(b'\r\n\r\n', 1)
        if not headers.startswith(b'HTTP/1.1 200'):
            raise RuntimeError('invalid http response')
        if len(unwrite) != 0:
            await conn.write(unwrite)
        return conn
