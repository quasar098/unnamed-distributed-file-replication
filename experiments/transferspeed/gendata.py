from random import randbytes

SIZE = 2**24
CHUNK_SIZE = 2**15

with open('data1', 'wb') as f:
    for i in range(0, SIZE, CHUNK_SIZE):
        f.write(randbytes(min(SIZE-i, CHUNK_SIZE)))

