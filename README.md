# unnamed-distributed-file-replication

## todo requirements

0. no voluntarily allowing single points of failure other than the breaking of cryptography
1. file upload/replication with 100% uptime
2. proxy requests through arbitrary nodes
3. arbitrary voluntary extensibility
4. invitation for others without sacrificing security
5. invitation for others without sacrificing privacy
6. backwards compatibility
7. high throughput (lesser priority)

## system design

each "node" is a copy of `main.py` running

each node can listen on 1 or more ip/port combinations, including ipv6 addresses



