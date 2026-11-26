import pytest
import logging
import multiprocessing
from helpers import terminate_all_nodes
from multiprocess_logging import install_mp_handler


@pytest.fixture(scope="session", autouse=True)
def setup_before_all_tests():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)8s %(name)s: %(message)s",
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    multiprocessing.set_start_method("fork")
    install_mp_handler()

    yield

    terminate_all_nodes()
