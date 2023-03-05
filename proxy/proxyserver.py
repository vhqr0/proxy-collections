import asyncio
import logging

from typing import Optional
from asyncio import Task, StreamReader, StreamWriter

from .defaults import (
    SERVER_ADDR,
    SERVER_PORT,
)
from .proxydispatcher import ProxyDispatcher
from .connections import BaseConnection, TCPConnection
from .acceptors import BaseAcceptor


class ProxyServer:
    acceptor: BaseAcceptor
    dispatcher: ProxyDispatcher
    server_addr: str
    server_port: int

    logger = logging.getLogger('proxy_server')

    tasks: set[Task] = set()

    def __init__(
        self,
        acceptor: BaseAcceptor,
        dispatcher: ProxyDispatcher,
        server_addr: str = SERVER_ADDR,
        server_port: int = SERVER_PORT,
    ):
        self.acceptor = acceptor
        self.dispatcher = dispatcher
        self.server_addr = server_addr
        self.server_port = server_port

    def run(self):
        try:
            asyncio.run(self.start_server())
        except Exception as e:
            self.logger.error('error while serving: %s', e)

    async def start_server(self):
        server = await asyncio.start_server(self.open_connection,
                                            self.server_addr,
                                            self.server_port,
                                            reuse_address=True)
        addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
        self.logger.info('server start at %s', addrs)
        async with server:
            await server.serve_forever()

    async def open_connection(self, reader: StreamReader,
                              writer: StreamWriter):
        try:
            client = TCPConnection(reader, writer)
            addr, port, unwrite = await self.acceptor.accept(client)
            connector = self.dispatcher.dispatch(addr, port)
        except Exception as e:
            self.logger.warning('except while accepting: %.40s', e)
            return

        try:
            peer = await connector.connect_to(addr, port, unwrite)
            await self.proxy(client, peer)
            connector.weight_increase()
        except Exception as e:
            self.logger.warning('except while connecting via %s: %.40s',
                                connector, e)
            connector.weight_decrease()
            return

    @classmethod
    async def proxy(cls, client: BaseConnection, peer: BaseConnection):
        task1 = asyncio.create_task(cls.io_copy(client, peer))
        task2 = asyncio.create_task(cls.io_copy(peer, client))
        for task in (task1, task2):
            cls.tasks.add(task)
            task.add_done_callback(cls.tasks.discard)

        exc: Optional[Exception] = None

        try:
            await asyncio.gather(task1, task2)
        except Exception as e:
            exc = e
            for task in (task1, task2):
                if not task.cancelled():
                    task.done()

        for conn in (client, peer):
            try:
                await conn.close()
            except Exception as e:
                if exc is not None:
                    exc = e

        if exc is not None:
            raise exc

    @staticmethod
    async def io_copy(reader: BaseConnection, writer: BaseConnection):
        while True:
            buf = await reader.read()
            if len(buf) == 0:
                await writer.write_eof()
                break
            await writer.write(buf)
