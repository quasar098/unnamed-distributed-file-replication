from storage import *
from textwrap import dedent
from typing import Union
from cryptosocket import *
from msgtype import MsgType
import html
import multiprocessing
from config import *

logger = logging.getLogger(__name__)


def pack_error(errormsg: bytes):
    return pack(f"<HQ{len(errormsg)}s", MsgType.ERROR, len(errormsg), errormsg)


def listen_new_node_with_conf(conf: Config, start_event):
    Node(conf).listen(start_event)


class Node:
    def __init__(self, conf: Config):
        self.conf: Config = conf
        self.storage = Storage(self)

    def listen(self, start_event = None):
        s: Optional[socket.socket] = None
        sa: Union[tuple[int, int, int, int], tuple[int, int], None] = None
        conf = self.conf
        for res in socket.getaddrinfo(conf.get('host'), conf.get('port', DEFAULT_PORT), socket.AF_UNSPEC,
                                      socket.SOCK_STREAM, 0, socket.AI_PASSIVE):
            af, socktype, proto, canonname, sa = res
            try:
                if conf.get("force_insecure_connection", False):
                    s = InsecureConnection(conf, af, socktype, proto)
                else:
                    s = SecureConnection(conf, af, socktype, proto)
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
        if start_event is not None:
            start_event.set()
        conn_counter = 0
        while True:
            conn, addr = s.accept()
            addr_str = f"{addr[0]}:{addr[1]}" if len(addr) == 2 else f"[{addr[0]}]:{addr[1]}"
            logger.info(f'accepted connection from {addr_str} ({f"conn-{conn_counter}"})')
            proc = multiprocessing.Process(
                target=NodeConnectionHandler.handle_client,
                args=(conf, self.storage.locks, conn, addr_str),
                daemon=True,
                name=f"conn-{conn_counter}"
            )
            proc.start()
            conn.close()
            conn_counter += 1


class NodeConnectionHandler:
    special_handle = {}

    def __init__(self, conf: Config, locks, conn: CryptoSocket, addr_str: str):
        self.conf: Config = conf
        self.locks: StorageLocks = locks
        self.conn: CryptoSocket = conn
        self.addr_str: str = addr_str
        if not conf.get("http_support", False):
            del NodeConnectionHandler.special_handle[MsgType.HTTP_GET]

    @staticmethod
    def handle_client(conf, locks, conn: CryptoSocket, addr_str):
        handler = NodeConnectionHandler(conf, locks, conn, addr_str)
        handler.handle_messages()
        logger.info(f'disconnected from {addr_str}')

    def handle_messages(self):
        try:
            with self.conn:
                while True:
                    msgtype, msglength = self.conn.recv_msg_header()
                    if msgtype is None or msglength is None:
                        break

                    # special handling
                    if msgtype in NodeConnectionHandler.special_handle:
                        if NodeConnectionHandler.special_handle[msgtype](self, msglength):
                            self.conn.shutdown(socket.SHUT_WR)
                            break

                    # regular handling
                    if (msgdata := self.conn.recv_chunked(msglength)) is not None:
                        if self.handle(msgtype, msglength, msgdata):
                            self.conn.shutdown(socket.SHUT_WR)
                            break
                    else:
                        self.conn.shutdown(socket.SHUT_WR)
                        break
        except ConnectionResetError as e:
            logger.info("connection reset by peer")

    def handle(self, msgtype, msglength, msgdata):
        match msgtype:
            case MsgType.PING:
                if self.conn.send_chunked(pack('<HQ', MsgType.PONG, 0)) is None:
                    return True
            case _:
                self.conn.send(pack_error(b"unknown type"))
                return True
        return False

    def http_get(self, msglength):
        self.conn.send(dedent(f"""
        HTTP/1.1 200 OK
        Content-Type: text/html; charset=UTF-8
        
        <h1>node "{html.escape(self.conf.get("name"))}"</h1>
        <p>version {html.escape(self.conf.get("version"))}</p>
        <p><a href=\"https://github.com/quasar098/unnamed-distributed-file-replication\">unnamed distributed file replication</a></p>
        """).strip().encode())
        return True
    special_handle[MsgType.HTTP_GET] = http_get

    def file_upload(self, conn, msglength):
        pass  # todo
