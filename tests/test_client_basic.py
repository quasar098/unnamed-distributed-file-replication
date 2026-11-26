from helpers import *
from msgtype import *


def test_one_entry_node_connect_success():
    client1 = new_client("""
    version = 1
    entry_endpoints = ["[::1]:33603"]
    """)
    node = new_node("""
    version = 1
    name = "node"
    host = "::1"
    port = 33603
    """)
    assert client1.connect_to_entry_endpoints()

    pong_type, _ = client1.send_msg(MsgType.PING, b'')
    assert pong_type == MsgType.PONG



    node.terminate()
    node.join()


# def test_two_entry_nodes_connect_success():
#     client1 = new_client("""
#     version = 1
#     entry_endpoints = ["[::1]:33603", "[::1]:33604"]
#     """)
#     node_1 = new_node("""
#     version = 1
#     name = "node-1"
#     host = "::1"
#     port = 33603
#     entry_endpoints = ["[::1]:33604"]
#     """)
#     node_2 = new_node("""
#     version = 1
#     name = "node-2"
#     host = "::1"
#     port = 33604
#     entry_endpoints = []
#     """)
#     assert client1.connect_to_entry_endpoints()
#
#     pong_type, _ = client1.send_msg(MsgType.PING, b'')
#     assert pong_type is not None
#     node_1.terminate()
#     node_1.join()
