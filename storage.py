from multiprocessing import Value, Lock


class StorageLocks:
    def __init__(self):
        self.nodes_directory_file = Lock()
        self.nodes_directory_file_version = Value('Q')


class Storage:
    def __init__(self, node):
        self.locks = StorageLocks()
        self.node = node
        # todo finish


# todo: store all files in trie by file sha256 hash
# todo: store list of other nodes and related recon info
