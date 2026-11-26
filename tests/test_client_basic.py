from client import Client
from msgtype import MsgType
from node import Node
from config import Config
from textwrap import dedent
import pytest
from helpers import *


def test_one_node_connect_success():
    client1 = new_client("""
    version = 1
    entry_endpoints = ["[::1]:33603"]
    """)
    node = new_node("""
    version = 1
    name = "a-node"
    host = "::1"
    port = 33603
    """)
    assert client1.connect_to_entry_endpoints()

    pong_type, _ = client1.send_msg(MsgType.PING_C2N, b'')
    assert pong_type is not None
    node.terminate()


# todo do this
