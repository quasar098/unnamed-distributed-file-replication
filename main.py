import argparse
import logging
from config import Config
from node import Node
from client import Client
from multiprocess_logging import install_mp_handler
import multiprocessing

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='miscellaneous distributed network')
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    nparser = subparsers.add_parser('node')
    nparser.add_argument('config_file')
    nparser.add_argument('-v', '--verbose', action='store_true')

    cparser = subparsers.add_parser('client')
    cparser.add_argument('config_file')
    cparser.add_argument('-v', '--verbose', action='store_true')

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)8s %(name)s: %(message)s",
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logger.debug('args: %s', args)
    
    conf = Config.load(args.config_file)
    logger.info('config loaded')

    if args.cmd == 'node':
        multiprocessing.set_start_method("fork")
        install_mp_handler()
        node = Node(conf)
        node.listen()
    elif args.cmd == 'client':
        client = Client(conf)
        client.cli()


if __name__ == '__main__':
    main()

