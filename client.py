import socket
from struct import unpack, pack
import logging
from msgtype import MsgType
from config import *
from typing import Optional, Union

logger = logging.getLogger(__name__)


class Client:
    def __init__(self, conf):
        self.conf = conf
        self.sock: Optional[socket.socket] = None

    def cli_help(self):
        print(*MsgType.by_name, sep="\n")
        print("help\nconnect\ndebugsend\nquit\nexit\n")

    def cli_connect(self):
        host = input("host > ")
        try:
            port = int(input("port (default 33603) > ") or DEFAULT_PORT)
        except ValueError:
            print("invalid port")
            return
        self.connect(host, port)

    def connect(self, host: str, port: int):
        logger.debug(f"attempting to connect to host {host} port {port}")
        s = None
        sa: Union[tuple[int, int, int, int], tuple[int, int], None] = None
        connect_success = False
        try:
            for res in socket.getaddrinfo(host, port, socket.AF_UNSPEC,
                                          socket.SOCK_STREAM, 0, 0):
                af, socktype, proto, canonname, sa = res
                try:
                    s = socket.socket(af, socktype, proto)
                    s.settimeout(5)
                    s.connect(sa)
                    connect_success = True
                    break
                except OSError as msg:
                    s = None
                    continue
        except socket.gaierror:
            print("host not found")
            return
        if not connect_success:
            logger.critical('could not connect to node')
            exit(1)
        logger.info(f'connected to host {sa[0]} port {sa[1]}')
        self.sock = s

    def debug_send_msgtype(self, msgtype: str):
        data = bytes.fromhex(input("data (hex) > "))
        self.sock.send(pack(f"<HQ{len(data)}s", MsgType.by_name[msgtype], len(data), data))
        msgtype_b = self.recv_chunked(2)
        if (not msgtype_b) or len(msgtype_b) < 2:
            print(f"malformed message type ({msgtype_b})")
            return
        msgtype = unpack("<H", msgtype_b)[0]
        msglength_b = self.recv_chunked(8)
        if (not msglength_b) or len(msglength_b) < 8:
            print(f"malformed message length ({msglength_b})")
            return
        msglength = unpack("<Q", msglength_b)[0]

        data = self.recv_chunked(msglength)
        if data is None:
            print("incomplete data")
            return

        if msgtype in MsgType.by_value:
            logger.info(f"received msg type {MsgType.by_value[msgtype]} length {msglength}: {data}")
        else:
            logger.info(f"received msg type UNKNOWN ({msgtype}) length {msglength}: {data}")

    def cli(self):
        running = True
        while running:
            inp = input("cmd > ")
            match inp:
                case "help":
                    self.cli_help()
                case "connect":
                    self.cli_connect()
                case "quit" | "exit":
                    running = False
                case msgtype:
                    if msgtype in MsgType.by_name:
                        if self.sock is not None:
                            self.debug_send_msgtype(msgtype)
                        else:
                            print("socket is None")
                    else:
                        print("unrecognized command (use `help` for help)")

    def recv_chunked(self, amt):
        if amt == 0:
            return b""
        conf = self.conf
        chunk_size = conf.get('chunk_size', DEFAULT_CHUNK_SIZE)
        msgdata_l = []
        len_data_read = 0
        while chunk := self.sock.recv(min(amt-len_data_read, chunk_size)):
            msgdata_l.append(chunk)
            len_data_read += len(chunk)
        if len_data_read == 0:
            raise ConnectionError("disconnected from node")
        if len_data_read != amt:
            return None
        return b"".join(msgdata_l)
