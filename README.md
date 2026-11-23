# unnamed-distributed-file-replication

**NOTE: only cpython 3.11 and later is supported**

## design

Many servers (nodes) are connected into a mesh network for the purpose of a distributed file system.

Assumptions:
- nodes have have dubious uptime (independent of other nodes, however)
- nodes have relatively weak processing capabilities
- nodes have relatively low storage capabilities (lower bound of 20MB)
- nodes may be compromised or become untrusted
- nodes have CPython 3.11 or higher installed
- nodes are running Linux
- the network of nodes form a connected graph

Requirements:
- no single points of failure except for cryptography, given that clients are able to connect to the internet
- 100% availability of files (defined as enough nodes being online to be able to retrieve all files)
- backwards compatibility for node software
- backwards compatibility for client software

## cryptography

All data stored on nodes should be encrypted-at-rest. All data transfer over the network should be completely encrypted by default.

Ideally ECC+PQ is used everywhere.

## todo requirements

- proxy requests through arbitrary nodes
- arbitrary voluntary extensibility
- invitation for others without sacrificing security
- invitation for others without sacrificing privacy
- high throughput (lesser priority)
