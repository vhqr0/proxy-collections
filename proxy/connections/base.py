class BaseConnection:
    unread: bytes

    def __init__(self):
        self.unread = b''

    async def close(self):
        raise NotImplementedError

    async def read(self) -> bytes:
        raise NotImplementedError

    def read_nonblock(self) -> bytes:
        raise NotImplementedError

    async def write(self, buf: bytes):
        raise NotImplementedError

    async def write_eof(self):
        raise NotImplementedError
