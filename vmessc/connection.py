import struct

from cryptography.hazmat.primitives.ciphers import Cipher
from cryptography.hazmat.primitives.ciphers.algorithms import AES
from cryptography.hazmat.primitives.ciphers.modes import CFB
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from proxy import override, BaseConnection


class VmessCryptor:
    gcm: AESGCM
    iv: bytes
    count: int

    def __init__(self, key: bytes, iv: bytes):
        self.gcm = AESGCM(key)
        self.iv = iv
        self.count = 0

    def encrypt(self, buf: bytes) -> bytes:
        return self.gcm.encrypt(self.get_iv(), buf, b'')

    def decrypt(self, buf: bytes) -> bytes:
        return self.gcm.decrypt(self.get_iv(), buf, b'')

    def get_iv(self) -> bytes:
        return struct.pack('!H', self.count) + self.iv


class VmessResponseValidator:
    cipher: Cipher
    expect: bytes

    def __init__(self, key: bytes, iv: bytes, rv: int):
        self.cipher = Cipher(AES(key), CFB(iv))
        self.expect = struct.pack('!BBBB', rv, 0, 0, 0)

    def valid(self, buf: bytes):
        decryptor = self.cipher.decryptor()
        buf = decryptor.update(buf) + decryptor.finalize()
        return buf == self.expect


class VmessConnection(BaseConnection):
    base_connection: BaseConnection
    read_cryptor: VmessCryptor
    write_cryptor: VmessCryptor
    response_validator: VmessResponseValidator
    validated: bool

    def __init__(self, base_connection: BaseConnection,
                 read_cryptor: VmessCryptor, write_cryptor: VmessCryptor,
                 response_validator: VmessResponseValidator, **kwargs):
        super().__init__(**kwargs)
        self.base_connection = base_connection
        self.read_cryptor = read_cryptor
        self.write_cryptor = write_cryptor
        self.response_validator = response_validator
        self.is_validated = False

    @override(BaseConnection)
    async def close(self):
        await self.base_connection.close()

    @override(BaseConnection)
    async def read(self) -> bytes:
        if len(self.unread) != 0:
            return self.read_nonblock()
        buf = await self.base_connection.read()
        if not self.is_validated:
            auth, buf = buf[:4], buf[4:]
            if not self.response_validator.valid(auth):
                raise RuntimeError('invalid vmess response')
            self.is_validated = True
        blen, = struct.unpack_from('!H', buffer=buf, offset=0)
        buf = buf[2:]
        while len(buf) < blen:
            buf += await self.base_connection.read()
        if len(buf) > blen:
            buf, self.base_connection.unread = buf[:blen], buf[blen:]
        return self.read_cryptor.decrypt(buf)

    @override(BaseConnection)
    def read_nonblock(self) -> bytes:
        if len(self.unread) != 0:
            buf, self.unread = self.unread, b''
            return buf
        buf = self.base_connection.read_nonblock()
        blen, = struct.unpack_from('!H', buffer=buf, offset=0)
        if len(buf) != blen + 2:
            self.base_connection.unread = buf
            return b''
        self.read_cryptor.decrypt(buf)

    @override(BaseConnection)
    async def write(self, buf: bytes):
        buf = self.write_cryptor.encrypt(buf)
        await self.base_connection.write(buf)

    @override(BaseConnection)
    async def write_eof(self):
        await self.write(b'')
