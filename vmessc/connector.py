import time
import random
import struct
import functools
import ssl
from hashlib import md5
from hmac import HMAC
from uuid import UUID

from cryptography.hazmat.primitives.ciphers import Cipher
from cryptography.hazmat.primitives.ciphers.algorithms import AES
from cryptography.hazmat.primitives.ciphers.modes import CFB

from proxy import (
    override,
    BaseConnector,
    WrappedConnector,
    BaseConnection,
    TCPConnector,
    WSConnector,
)

from .connection import VmessConnection, VmessCryptor, VmessResponseValidator


class VmessConnector(BaseConnector):
    uuid: UUID
    base_connector: WrappedConnector

    def __init__(self, base_connector: WrappedConnector, uuid: UUID, **kwargs):
        super().__init__(**kwargs)
        self.base_connector = base_connector
        self.uuid = uuid

    @functools.cached_property
    def req_key(self) -> bytes:
        h = md5()
        h.update(self.uuid.bytes)
        h.update(self.REQ_KEY_SUFFIX)
        return h.digest()

    @override(BaseConnector)
    async def connect_to(
        self,
        addr: str,
        port: int,
        unwrite: bytes = b'',
    ) -> BaseConnection:
        key = random.randbytes(16)
        iv = random.randbytes(16)
        rv = random.getrandbits(8)
        rkey = md5(key).digest()
        riv = md5(iv).digest()
        read_cryptor = VmessCryptor(rkey, riv[2:12])
        write_cryptor = VmessCryptor(key, iv[2:12])
        response_validator = VmessResponseValidator(rkey, riv, rv)
        buf = self.get_req(addr, port, key, iv, rv)
        if len(unwrite) != 0:
            buf += write_cryptor.encrypt(unwrite)
        base_conn = await self.base_connector.connect(buf)
        conn = VmessConnection(base_connection=base_conn,
                               read_cryptor=read_cryptor,
                               write_cryptor=write_cryptor,
                               response_validator=response_validator)
        return conn

    def get_req(self, addr_str: str, port: int, key: bytes, iv: bytes,
                rv: int) -> bytes:
        ts = int(time.time()).to_bytes(8, 'big')
        addr = addr_str.encode()
        alen = len(addr)
        plen = random.getrandbits(4)

        # ver(B)          : 1
        # iv(16s)         : iv
        # key(16s)        : key
        # rv(B)           : rv
        # opts(B)         : 1
        # plen|secmeth(B) : plen|3
        # res(B)          : 0
        # cmd(B)          : 1
        # port(H)         : port
        # atype(B)        : 2
        # alen(B)         : alen
        # addr({alen}s)   : addr
        # random({plen}s) : randbytes
        req = struct.pack(
            f'!B16s16sBBBBBHBB{alen}s{plen}s',
            1,
            iv,
            key,
            rv,
            1,
            (plen << 4) + 3,
            0,
            1,
            port,
            2,
            alen,
            addr,
            random.randbytes(plen),
        )
        req += self.fnv32a(req)
        cipher = Cipher(AES(self.req_key), CFB(md5(4 * ts).digest()))
        encryptor = cipher.encryptor()
        req = encryptor.update(req) + encryptor.finalize()
        auth = HMAC(key=self.uuid.bytes, msg=ts, digestmod='md5').digest()
        return auth + req

    @staticmethod
    def fnv32a(buf: bytes) -> bytes:
        r, p, m = 0x811c9dc5, 0x01000193, 0xffffffff
        for c in buf:
            r = ((r ^ c) * p) & m
        return r.to_bytes(4, 'big')


class VmessSerConnector(VmessConnector):
    net: str
    addr: str
    port: int
    tls_host: str
    ws_path: str
    ws_host: str

    def __init__(self, net: str, addr: str, port: str, tls_host: str,
                 ws_path: str, ws_host: str, **kwargs):
        self.net = net
        self.addr = addr
        self.port = port
        self.tls_host = tls_host
        self.ws_path = ws_path
        self.ws_host = ws_host

        if net not in ('tcp', 'tls', 'ws', 'wss'):
            raise ValueError

        base_connector: BaseConnector
        tcp_connector = TCPConnector()
        if net in ('tls', 'wss'):
            tcp_connector.set_tcp_kwargs(
                ssl=ssl.create_default_context(),
                server_hostname=tls_host,
            )
        if net in ('ws', 'wss'):
            base_connector = WSConnector(
                base_connector=tcp_connector,
                path=ws_path,
                host=ws_host,
            )
        else:
            base_connector = tcp_connector
        wrapped_connector = WrappedConnector(
            base_connector=base_connector,
            addr=addr,
            port=port,
        )
        super().__init__(base_connector=wrapped_connector, **kwargs)
