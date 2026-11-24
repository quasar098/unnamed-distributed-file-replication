# https://cryptography.io/en/latest/hazmat/primitives/asymmetric/mlkem/
from cryptography.hazmat.primitives.asymmetric.mlkem import MLKEM768PrivateKey, MLKEM768PublicKey
# https://cryptography.io/en/latest/hazmat/primitives/asymmetric/x25519/
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
# https://cryptography.io/en/latest/hazmat/primitives/key-derivation-functions/#cryptography.hazmat.primitives.kdf.hkdf.HKDF
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
# https://cryptography.io/en/latest/cobblestone/
from cryptography.cobblestone import Cobblestone256Decryptor, Cobblestone256Encryptor
import socket
from typing import Optional
import logging
from collections import deque
from config import *
from msgtype import *
from struct import pack, unpack

logger = logging.getLogger(__name__)

DEFAULT_CHUNK_SIZE = 2048


# private_key = MLKEM768PrivateKey.generate()
# public_key = private_key.public_key()
# shared_secret, ciphertext = public_key.encapsulate()
# recovered_secret = private_key.decapsulate(ciphertext)
# assert shared_secret == recovered_secret
# print(shared_secret, recovered_secret, private_key, public_key)


class CryptoSocket(socket.socket):
    def __init__(self, conf: Config, family=-1, type_=-1, proto=-1, fileno=None):
        super().__init__(family=family, type=type_, proto=proto, fileno=fileno)
        self.conf = conf

    def accept(self):
        # noinspection PyUnresolvedReferences,PyProtectedMember
        fd, addr = super()._accept()
        sock = type(self)(self.conf, self.family, self.type, self.proto, fileno=fd)
        if socket.getdefaulttimeout() is None and self.gettimeout():
            sock.setblocking(True)
        return sock, addr

    def recv_msg_header(self):
        """
        Returns (msgtype: MsgType, msglength: int) on successful message header parse. Returns (None, None) otherwise
        """
        recved = self.recv(10)
        if len(recved) < 10:
            return None, None
        assert len(recved) == 10, recved
        msgtype, msglength = unpack("<HQ", recved)
        if msgtype in MsgType._value2member_map_:
            logger.debug(f"received msg type {MsgType(msgtype).name} length {msglength}")
        else:
            logger.debug(f"received msg type UNKNOWN ({msgtype}) length {msglength}")
        return MsgType(msgtype), msglength


    def recv_chunked(self, amt: int):
        """
        recv() but it is guaranteed to either return a bytes object of length ``amt`` (success) or ``None`` (failure).
        """
        msgdata_l = []
        len_data_read = 0
        while len_data_read < amt:
            chunk = self.recv(min(amt - len_data_read, DEFAULT_CHUNK_SIZE))
            if len(chunk) == 0:
                return None
            msgdata_l.append(chunk)
            len_data_read += len(chunk)
        return b"".join(msgdata_l)

    def send_chunked(self, data: bytes):
        """
        send() but it is guaranteed to either return ``len(data)`` (success) or ``None`` (failure)
        """
        len_data_sent = 0
        # noinspection PyTypeChecker,PyUnresolvedReferences
        data_mv: "memoryview[bytes]" = memoryview(data)
        while len_data_sent < len(data):
            sent = self.send(data_mv[len_data_sent:])
            if sent == 0:
                return None
            len_data_sent += sent
        return len_data_sent


class InsecureConnection(CryptoSocket):
    """No encryption"""

    def __init__(self, conf: Config, family=-1, type_=-1, proto=-1, fileno=None):
        super().__init__(conf=conf, family=family, type_=type_, proto=proto, fileno=fileno)

        self.doing_secure_connection_rejection = False

    def send(self, data, flags=0):
        return super().send(data, flags)

    def recv_msg_header(self):
        msgtype, msglength = super().recv_msg_header()
        if msgtype == MsgType.BEGIN_SECURE_CONNECTION and msglength is not None:
            if not self.doing_secure_connection_rejection:
                self.doing_secure_connection_rejection = True
                import time
                if (msgdata := self.recv_chunked(msglength)) is None:
                    return None, None
                if self.send_chunked(pack("<HQ", MsgType.REJECT_SECURE_CONNECTION, 0)) is None:
                    return None, None
                self.doing_secure_connection_rejection = False

                msgtype, msglength = super().recv_msg_header()
        return msgtype, msglength

    def recv(self, bufsize, flags=0):
        return super().recv(bufsize, flags)


class SecureConnection(CryptoSocket):
    """ECC (X25519) + PQ (MLKEM768)"""

    def __init__(self, conf: Config, family=-1, type_=-1, proto=-1, fileno=None):
        super().__init__(conf=conf, family=family, type_=type_, proto=proto, fileno=fileno)

        self.has_exchanged_keys = False
        self.has_checked_supports_secure = False
        self.doing_secure_connection_setup = False

        self.encryption_key: Optional[bytes] = None

        self.bytes_queue: deque[bytes] = deque()
        self.bytes_queue_len = 0

    def send(self, data: bytes, flags: int = 0):
        if (self.encryption_key is None) and (not self.has_checked_supports_secure) and (not self.doing_secure_connection_setup):
            self.doing_secure_connection_setup = True
            self.has_checked_supports_secure = True

            # generate keypairs
            bob_ecc_priv_key = X25519PrivateKey.generate()
            bob_ecc_pub_key = bob_ecc_priv_key.public_key()
            bob_pq_priv_key = MLKEM768PrivateKey.generate()
            bob_pq_pub_key = bob_pq_priv_key.public_key()

            # step 1: bob sends public keys to alice
            bob_ecc_pub_key_b = bob_ecc_pub_key.public_bytes_raw()
            bob_pq_pub_key_b = bob_pq_pub_key.public_bytes_raw()
            keyderiv_part_1 = pack(
                f"<HQII{len(bob_ecc_pub_key_b)}s{len(bob_pq_pub_key_b)}s",
                MsgType.BEGIN_SECURE_CONNECTION, len(bob_ecc_pub_key_b) + len(bob_pq_pub_key_b) + 8,
                len(bob_ecc_pub_key_b),
                len(bob_pq_pub_key_b),
                bob_ecc_pub_key_b,
                bob_pq_pub_key_b
            )
            if self.send_chunked(keyderiv_part_1) is None:
                print("fail1")
                return 0

            # step 3: bob does ecdh and mlkem key decapsulation
            msgtype, msglength = self.recv_msg_header()
            if msgtype is None or msglength is None:
                print("fail2")
                return 0
            if msgtype == MsgType.REJECT_SECURE_CONNECTION:
                logger.warning("peer has refused to encrypt the connection")
                self.doing_secure_connection_setup = False
                return super().send(data, flags)
            elif msgtype != MsgType.CONFIRM_SECURE_CONNECTION:
                print("fail3", msgtype)
                return 0
            if (msgdata := self.recv_chunked(msglength)) is None:
                self.doing_secure_connection_setup = False
                print("fail4")
                return 0
            alice_ecc_pub_key_b_len, pq_ct_b_len = unpack("<II", msgdata[:8])
            if alice_ecc_pub_key_b_len + pq_ct_b_len != msglength - 8:
                self.doing_secure_connection_setup = False
                print("fail5")
                return 0
            alice_ecc_pub_key_b, pq_ct_b = unpack(f"<{alice_ecc_pub_key_b_len}s{pq_ct_b_len}s", msgdata[8:])

            alice_ecc_pub_key = X25519PublicKey.from_public_bytes(alice_ecc_pub_key_b)

            ss_ecc_bob = bob_ecc_priv_key.exchange(alice_ecc_pub_key)
            ss_pq_bob = bob_pq_priv_key.decapsulate(pq_ct_b)

            self.encryption_key = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=None,
                info=(b"x25519mlkem768" + alice_ecc_pub_key.public_bytes_raw() + bob_ecc_pub_key.public_bytes_raw()),
            ).derive(ss_ecc_bob + ss_pq_bob)
            logger.info("key exchange with peer complete")

            self.has_exchanged_keys = True
            self.doing_secure_connection_setup = False
        if self.encryption_key is None:
            return super().send(data, flags)
        else:
            encryptor = Cobblestone256Encryptor(self.encryption_key, context=b"unnamed-distributed-file-replication")
            ct = encryptor.update(data)
            ct += encryptor.finalize()
            return super().send(pack("<Q", len(ct)) + ct, flags)

    def recv_msg_header(self):
        msgtype, msglength = super().recv_msg_header()
        if msgtype == MsgType.BEGIN_SECURE_CONNECTION and msglength is not None:
            if not self.doing_secure_connection_setup:
                self.doing_secure_connection_setup = True

                # step 2: alice receives pub keys and does ecdh and mlkem key encapsulation
                if (msgdata := self.recv_chunked(msglength)) is None:
                    self.doing_secure_connection_setup = False
                    return None, None
                bob_ecc_pub_key_b_len, bob_pq_pub_key_b_len = unpack("<II", msgdata[:8])
                if bob_ecc_pub_key_b_len + bob_pq_pub_key_b_len != msglength - 8:
                    self.doing_secure_connection_setup = False
                    return None, None
                bob_ecc_pub_key_b, bob_pq_pub_key_b = unpack(f"<{bob_ecc_pub_key_b_len}s{bob_pq_pub_key_b_len}s",
                                                             msgdata[8:])
                bob_ecc_pub_key = X25519PublicKey.from_public_bytes(bob_ecc_pub_key_b)
                bob_pq_pub_key = MLKEM768PublicKey.from_public_bytes(bob_pq_pub_key_b)

                alice_ecc_priv_key = X25519PrivateKey.generate()
                alice_ecc_pub_key = alice_ecc_priv_key.public_key()
                ecc_shared_secret = alice_ecc_priv_key.exchange(bob_ecc_pub_key)
                pq_shared_secret, pq_ct_b = bob_pq_pub_key.encapsulate()

                alice_ecc_pub_key_b = alice_ecc_pub_key.public_bytes_raw()
                part2 = pack(
                    f"<HQII{len(alice_ecc_pub_key_b)}s{len(pq_ct_b)}s",
                    MsgType.CONFIRM_SECURE_CONNECTION, len(alice_ecc_pub_key_b) + len(pq_ct_b) + 8,
                    len(alice_ecc_pub_key_b), len(pq_ct_b),
                    alice_ecc_pub_key_b, pq_ct_b
                )
                if self.send_chunked(part2) is None:
                    self.doing_secure_connection_setup = False
                    return None, None

                self.doing_secure_connection_setup = False
                self.has_exchanged_keys = True

                self.encryption_key = HKDF(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=None,
                    info=(b"x25519mlkem768" + alice_ecc_pub_key.public_bytes_raw() + bob_ecc_pub_key.public_bytes_raw())
                ).derive(ecc_shared_secret + pq_shared_secret)
                logger.info("key exchange with peer complete")

                msgtype, msglength = super().recv_msg_header()
        return msgtype, msglength

    def recv(self, bufsize: int, flags: int = 0):
        if self.encryption_key is None:
            return super().recv(bufsize, flags)
        else:
            # print("decrypting bytes of pt size", bufsize)
            while self.bytes_queue_len < bufsize:
                ct_size_b = super().recv(8, flags)
                if ct_size_b == b'':
                    return b''
                ct_size = unpack("<Q", ct_size_b)[0]

                len_data_read = 0
                chunks = []
                while len_data_read < ct_size:
                    chunk = super().recv(min(ct_size - len_data_read, DEFAULT_CHUNK_SIZE))
                    if len(chunk) == 0:
                        return b''
                    chunks.append(chunk)
                    len_data_read += len(chunk)

                recved = b''.join(chunks)
                decryptor = Cobblestone256Decryptor(
                    self.encryption_key, context=b"unnamed-distributed-file-replication"
                )
                res = decryptor.update(recved) + decryptor.finalize()
                self.bytes_queue_len += len(res)
                self.bytes_queue.append(res)
            assert self.bytes_queue_len >= bufsize, f"{self.bytes_queue_len=} vs {bufsize=}"
            total = b''
            while len(total) < bufsize:
                total += self.bytes_queue.popleft()
            if len(total) > bufsize:
                total, remainder = total[:bufsize], total[bufsize:]
                self.bytes_queue.appendleft(remainder)
            self.bytes_queue_len -= bufsize
            # print("res:", res)
            return total
