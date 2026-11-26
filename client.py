from typing import Optional, Union
from cryptosocket import *
import socket
from struct import unpack, pack
import logging
from msgtype import MsgType
from config import *
import re

logger = logging.getLogger("client")


class Client:
    def __init__(self, conf: Config):
        self.conf: Config = conf
        self.sock: Optional[CryptoSocket] = None

    def connect_to_entry_endpoints(self):
        logger.info("attempting to connect to entry endpoints")
        s = None
        success_host, success_port = None, None
        connect_success = False
        endpoints = self.conf.get("entry_endpoints", [])
        for endpoint in endpoints:
            host, port_s = re.fullmatch(r'^\[?([^\[\]]+?)]?(?::(\d+))?$', endpoint).groups()
            port = int(port_s or 33603)
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
            except socket.gaierror as e:
                logger.warning(f"host {host} not found")
                continue
            if connect_success:
                success_host = host
                success_port = port
                break
            logger.warning(f"could not connect to host {host} port {port}")
        if not connect_success:
            logger.error('could not connect to any endpoint')
            if len(endpoints) == 0:
                logger.info("maybe try specifying entry_endpoints in the client config?")
            return False
        logger.info(f'connected to host {success_host} port {success_port}')
        self.sock = s
        return True

    def connect(self, host: str, port: int):
        logger.info(f"attempting to connect to host {host} port {port}")
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
                    s.connect(sa)
                    connect_success = True
                    break
                except OSError:
                    s = None
                    continue
        except socket.gaierror:
            logger.warning(f"host {host} not found")
        if not connect_success:
            logger.error('could not connect to node')
            return False
        logger.info(f'connected to host {host} port {port}')
        self.sock = s
        return True

    def send_msg(self, msgtype: MsgType, data: bytes):
        if self.sock.send_chunked(pack(f"<HQ{len(data)}s", msgtype, len(data), data)) is None:
            if self.sock is not None:
                logger.error("disconnected from server (failed to send)")
                self.sock = None
            return None, None

        msgtype, msglength = self.sock.recv_msg_header()
        if msgtype is None:
            if self.sock is not None:
                logger.error("disconnected from server (msgtype is None)")
                self.sock = None
            return None, None
        if msglength is None:
            if self.sock is not None:
                logger.error("disconnected from server (msglength is None)")
                self.sock = None
            return None, None

        data = self.sock.recv_chunked(msglength)
        if data is None:
            if self.sock is not None:
                logger.error("disconnected from server (incomplete data)")
                self.sock = None
            return None, None

        if msgtype in MsgType._value2member_map_:
            logger.info(f"received msg type {MsgType(msgtype).name} length {msglength}: {data}")
            return MsgType(msgtype), data
        else:
            logger.info(f"received msg type UNKNOWN ({msgtype}) length {msglength}: {data}")
            return None, None

    def cli_help(self):
        print(*[msgtype.name for msgtype in MsgType], sep="\n")
        print("help\nconnect\nquit\nexit\n")

    def cli_connect_to(self):
        host = input("host (default ::1) > ") or "::1"
        try:
            port = int(input("port (default 33603) > ") or DEFAULT_PORT)
        except ValueError:
            print("invalid port")
            return
        self.connect(host, port)

    def cli(self):
        running = True
        while running:
            inp = input("cmd > ")
            match inp:
                case "help":
                    self.cli_help()
                case "connect_to":
                    self.cli_connect_to()
                case "connect":
                    self.connect_to_entry_endpoints()
                case "quit" | "exit":
                    running = False
                case msgtype:
                    if msgtype in MsgType.__members__:
                        if self.sock is not None:
                            data = bytes.fromhex(input("data (hex) > "))
                            self.send_msg(MsgType[msgtype], data)
                        else:
                            print("socket is None")
                    else:
                        print("unrecognized command (use `help` for help)")
