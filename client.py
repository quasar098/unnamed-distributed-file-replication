from typing import Optional, Union
from cryptosocket import *
import socket
from struct import unpack, pack
import logging
from msgtype import MsgType
from config import *

logger = logging.getLogger(__name__)


class Client:
    def __init__(self, conf: Config):
        self.conf: Config = conf
        self.sock: Optional[CryptoSocket] = None

    def cli_help(self):
        print(*[msgtype.name for msgtype in MsgType], sep="\n")
        print("help\nconnect\nquit\nexit\n")

    def cli_connect(self):
        host = input("host (default ::1) > ") or "::1"
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
                    if self.conf.get("force_insecure_connection", False):
                        s = InsecureConnection(self.conf, af, socktype, proto)
                    else:
                        s = SecureConnection(self.conf, af, socktype, proto)
                    s.settimeout(5)
                    s.connect(sa)
                    connect_success = True
                    break
                except OSError:
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
        if self.sock.send_chunked(pack(f"<HQ{len(data)}s", MsgType[msgtype], len(data), data)) is None:
            if self.sock is not None:
                logger.error("disconnected from server (failed to send)")
                self.sock = None
            return

        msgtype, msglength = self.sock.recv_msg_header()
        if msgtype is None:
            if self.sock is not None:
                logger.error("disconnected from server (msgtype is None)")
                self.sock = None
            return
        if msglength is None:
            if self.sock is not None:
                logger.error("disconnected from server (msglength is None)")
                self.sock = None
            return

        data = self.sock.recv_chunked(msglength)
        if data is None:
            if self.sock is not None:
                logger.error("disconnected from server (incomplete data)")
                self.sock = None
            return

        if msgtype in MsgType._value2member_map_:
            logger.info(f"received msg type {MsgType(msgtype).name} length {msglength}: {data}")
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
                    if msgtype in MsgType.__members__:
                        if self.sock is not None:
                            self.debug_send_msgtype(msgtype)
                        else:
                            print("socket is None")
                    else:
                        print("unrecognized command (use `help` for help)")
