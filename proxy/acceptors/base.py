from ..connections import BaseConnection


class BaseAcceptor:

    async def accept(self, conn: BaseConnection) -> tuple[str, int, bytes]:
        raise NotImplementedError
