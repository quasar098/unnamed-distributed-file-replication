class MsgType:
    # c2n
    PING_C2N = 0
    UPLOAD_FILE_C2N = 1
    DOWNLOAD_FILE_C2N = 2
    GET_STATUS_C2N = 3

    # n2c
    PONG_N2C = 10000
    UPLOAD_FILE_ACK_N2C = 10001
    DOWNLOAD_FILE_N2C = 10002
    GET_STATUS_N2C = 10003

    # n2n
    PING_N2N = 20000
    PONG_N2N = 20001
    UPLOAD_FILE_N2N = 20002
    UPLOAD_FILE_ACK_N2N = 20003
    CHALLENGE_N2N = 20004
    PROOF_N2N = 20005
    ADD_NODE_N2N = 20006
    ADD_NODE_ACK_N2N = 20007
    # todo: announce disconnectedness

    # special
    HTTP_GET = 17735  # int.from_bytes(b'GE', 'little')
    AUTH_REJECT = 65534
    ERROR = 65535

    # mappings
    by_name: dict[str, int] = {}
    by_value: dict[int, str] = {}


# mappings

for attr in dir(MsgType):
    if attr in ("by_name", "by_value"):
        continue
    if not attr.startswith("_"):
        value = getattr(MsgType, attr)
        MsgType.by_name[attr] = value
        MsgType.by_value[value] = attr
