from client import Client
from node import listen_new_node_with_conf
from config import Config
from textwrap import dedent
import pytest
import multiprocessing
from tempfile import TemporaryDirectory


def new_client(config_txt):
    return Client(Config.load_str(dedent(config_txt.removeprefix("\n"))))


all_node_processes = []


def new_node(config_txt, ephemeral_storage=True):
    conf = Config.load_str(dedent(config_txt.removeprefix("\n")))
    tempdir = TemporaryDirectory()
    if ephemeral_storage:
        conf.set_ephemeral_storage_dir(tempdir)
    start_event = multiprocessing.Event()
    proc = multiprocessing.Process(
        target=listen_new_node_with_conf,
        args=(conf, start_event),
        name=f"{conf.get('name', 'unnamed-node')}"
    )
    proc.start()
    if not start_event.wait(timeout=10.0):
        raise TimeoutError("testing node took too long to start")
    all_node_processes.append(proc)
    return proc


def terminate_all_nodes():
    for node in all_node_processes:
        node.terminate()
