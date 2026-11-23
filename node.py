import socket
from struct import unpack, pack
import logging
from typing import Optional, Union
from msgtype import MsgType
import multiprocessing
from config import *

logger = logging.getLogger(__name__)

with open("index.html", 'rb') as f:
    # todo maybe make this configurable or smth
    default_get_req_html = f.read()


def pack_error(errormsg: bytes):
    return pack(f"<HQ{len(errormsg)}s", MsgType.ERROR, len(errormsg), errormsg)


class Node:
    def __init__(self, conf):
        self.conf = conf

    def listen(self):
        s = None
        sa: Union[tuple[int, int, int, int], tuple[int, int], None] = None
        conf = self.conf
        for res in socket.getaddrinfo(conf.get('host'), conf.get('port', DEFAULT_PORT), socket.AF_UNSPEC,
                                      socket.SOCK_STREAM, 0, socket.AI_PASSIVE):
            af, socktype, proto, canonname, sa = res
            try:
                s = socket.socket(af, socktype, proto)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            except OSError:
                s = None
                continue
            try:
                logger.debug(f'attempting to bind on host {sa[0]} port {sa[1]}')
                s.bind(sa)
                s.listen()
            except OSError:
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
            addr_str = f"{addr[0]}:{addr[1]}" if len(addr) == 2 else f"[{addr[0]}]:{addr[1]}"
            logger.info(f'accepted connection from {addr_str}')
            proc = multiprocessing.Process(
                target=NodeConnectionHandler.handle_client,
                args=(conn, addr_str),
                daemon=True
            )
            proc.start()
            conn.close()


class NodeConnectionHandler:
    special_handle = {}

    def __init__(self, conf, addr_str: str):
        self.conf = conf
        self.addr_str = addr_str

    @staticmethod
    def handle_client(conn, addr_str):
        self = NodeConnectionHandler(conn, addr_str)
        with conn:
            while True:
                msgtype_b = conn.recv(2)
                if (not msgtype_b) or len(msgtype_b) < 2: break
                msgtype = unpack("<H", msgtype_b)[0]
                msglength_b = conn.recv(8)
                if (not msglength_b) or len(msglength_b) < 8: break
                msglength = unpack("<Q", msglength_b)[0]

                if msgtype in MsgType.by_value:
                    logger.debug(f"received msg type {MsgType.by_value[msgtype]} length {msglength}")
                else:
                    logger.debug(f"received msg type UNKNOWN ({msgtype}) length {msglength}")

                # special handling
                if msgtype in NodeConnectionHandler.special_handle:
                    if NodeConnectionHandler.special_handle[msgtype](self, conn, msglength):
                        conn.shutdown(socket.SHUT_WR)
                        break

                # regular handling
                if (msgdata := self.recv_chunked(conn, msglength)) is not None:
                    if self.handle(conn, msgtype, msglength, msgdata):
                        conn.shutdown(socket.SHUT_WR)
                        break
                else:
                    conn.shutdown(socket.SHUT_WR)
                    break
        logger.info(f'disconnected from {addr_str}')

    def recv_chunked(self, conn, amt):
        if amt == 0:
            return b""
        conf = self.conf
        chunk_size = conf.get('chunk_size', DEFAULT_CHUNK_SIZE)
        msgdata_l = []
        len_data_read = 0
        while chunk := conn.recv(min(amt-len_data_read, chunk_size)):
            msgdata_l.append(chunk)
            len_data_read += len(chunk)
        if len_data_read == 0:
            return None
        if len_data_read != amt:
            return None
        return b"".join(msgdata_l)

    def handle(self, conn, msgtype, msglength, msgdata):
        match msgtype:
            case MsgType.PING_C2N:
                conn.send(pack('<HQ', MsgType.PONG_N2C, 0))
            case _:
                conn.send(pack_error(b"unknown type"))
                return True
        return False

    def http_get(self, conn, msglength):
        conn.send(b"HTTP/1.1 200 OK\nContent-Type: text/html; charset=UTF-8\n\n" + default_get_req_html)
        return True
    special_handle[MsgType.HTTP_GET] = http_get

