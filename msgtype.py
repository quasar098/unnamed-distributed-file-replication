from enum import IntEnum
from struct import pack, unpack


class MsgType(IntEnum):
    # c2n
    UPLOAD_FILE_C2N = 0  # todo
    DOWNLOAD_FILE_C2N = 1  # todo
    GET_STATUS_C2N = 2  # todo
    AUTH_C2N = 3  # todo
    GET_NODES = 4  # todo

    # n2c
    UPLOAD_FILE_ACK_N2C = 10000  # todo
    DOWNLOAD_FILE_N2C = 10001  # todo
    GET_STATUS_N2C = 10002  # todo
    AUTH_SUCCESS_N2C = 10003  # todo
    AUTH_FAIL_N2C = 10004  # todo

    # n2n
    UPLOAD_FILE_N2N = 20000  # todo
    UPLOAD_FILE_ACK_N2N = 20001  # todo
    CHALLENGE_N2N = 20002  # todo
    PROOF_N2N = 20003  # todo
    EXCHANGE_NODES_N2N = 20004  # todo

    # special
    PING = 65530
    PONG = 65531
    HTTP_GET = 17735  # int.from_bytes(b'GE', 'little')
    BEGIN_SECURE_CONNECTION = 65532
    CONFIRM_SECURE_CONNECTION = 65533
    REJECT_SECURE_CONNECTION = 65534
    ERROR = 65535



