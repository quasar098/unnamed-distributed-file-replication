import socket
import logging
from struct import unpack, pack
from config import Config
import logging
from msgtype import MsgType

logger = logging.getLogger(__name__)

DEFAULT_PORT = 33603
DEFAULT_CHUNK_SIZE = 1024


class Node:
    special_handle = {}

    def listen(self):
        s = None
        conf = Config.instance
        for res in socket.getaddrinfo(conf.get('host'), conf.get('port', DEFAULT_PORT), socket.AF_UNSPEC,
                                      socket.SOCK_STREAM, 0, socket.AI_PASSIVE):
            af, socktype, proto, canonname, sa = res
            try:
                s = socket.socket(af, socktype, proto)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            except OSError as msg:
                s = None
                continue
            try:
                logger.debug(f'attempting to bind on host {sa[0]} port {sa[1]}')
                s.bind(sa)
                s.listen()
            except OSError as msg:
                print(msg)
                s.close()
                s = None
                continue
            break
        if s is None:
            logger.critical('could not open socket')
            exit(1)
        logger.info(f'listening on host {sa[0]} port {sa[1]}')
        while True:
            conn, addr = s.accept()
            logger.info(f'accepted connection from host {addr[0]} port {addr[1]}')
            with conn:
                while True:
                    msgtype_b = conn.recv(2)
                    if (not msgtype_b) or len(msgtype_b) < 2: break
                    msgtype = int.from_bytes(msgtype_b, 'little')
                    msglength_b = conn.recv(8)
                    if (not msglength_b) or len(msglength_b) < 8: break
                    msglength = int.from_bytes(msglength_b, 'little')

                    # special handling
                    if msgtype in Node.special_handle:
                        if Node.special_handle[msgtype](self, conn, msglength):
                            conn.shutdown(socket.SHUT_WR)
                            break

                    # regular handling
                    if (msgdata := self.recv_chunked(conn, msglength)) is not None:
                        if self.handle(conn, msgtype, msglength, msgdata):
                            conn.shutdown(socket.SHUT_WR)
                            break

    def recv_chunked(self, conn, amt):
        conf = Config.instance
        chunk_size = conf.get('chunk_size', DEFAULT_CHUNK_SIZE)
        msgdata_l = []
        len_data_read = 0
        while chunk := conn.recv(chunk_size):
            if len(chunk) < min(amt-len_data_read, chunk_size):
                msgdata_l.append(chunk)
                len_data_read += len(chunk)
        if len_data_read != amt:
            return
        return b"".join(msgdata_l)

    def handle(self, conn, msgtype, msglength, msgdata):
        # avoid using switch case to keep compatibility for python 3.9 and below
        if (msgtype == MsgType.PING_C2N):
            conn.send(pack('<H<Q', MsgType.PONG_N2C, 0))
        else:
            conn.send(pack('<H<Q', MsgType.ERROR, 12, b'unknown type'))

    def http_get(self, conn, msglength):
        conn.send(b"HTTP/1.1 200 OK\nContent-Type: text/html; charset=UTF-8\n\n"
                  b"<p><a href=\"https://github.com/quasar098/unnamed-distributed-file-replication\">distributed file replication</a></p>")
        return True
    special_handle[MsgType.HTTP_GET] = http_get

