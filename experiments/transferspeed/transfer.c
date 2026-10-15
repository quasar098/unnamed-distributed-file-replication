/* gcc transfer.c -o transfer */

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netdb.h>

#define MAX_CHUNK_SIZE 262144
#define max(a, b) ((a) > (b) ? (a) : (b))
#define min(a, b) ((a) > (b) ? (b) : (a))

int main(int argc, char** argv) {
    if (argc != 5) {
        printf("Usage: %s {server|client} <host> <port> <infile>\n", argv[0]);
        return 1;
    }

    bool is_client = false;
    if (strcmp(argv[1], "client") == 0) {
        is_client = true;
    } else if (strcmp(argv[1], "server") != 0) {
        printf("Usage: %s {server|client} <host> <port> <infile>\n", argv[0]);
        return 1;
    }

    if (!is_client) {
        printf("Server not implemented\n");  // todo do this
        return 1;
    }

    FILE* infile = fopen(argv[4], "rb");
    if (infile == NULL) {
        printf("Error opening file\n");
        return 1;
    }
    fseek(infile, 0L, SEEK_END);
    long size = ftell(infile);
    fseek(infile, 0L, SEEK_SET);

    struct addrinfo *res;
    struct addrinfo hints;
    memset(&hints, 0, sizeof(hints));
    hints.ai_family = AF_INET;
    hints.ai_socktype = SOCK_STREAM;
    hints.ai_flags |= AI_CANONNAME;
    if (getaddrinfo(argv[2], argv[3], &hints, &res) != 0) {
        printf("getaddrinfo() failure\n");
        return 1;
    }
    if (res->ai_family != AF_INET) {
        printf("Host is not IPv4\n");
        return 1;
    }

    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock == -1) {
        printf("Error creating socket\n");
        return 1;
    }
    if (connect(sock, (struct sockaddr*)res->ai_addr, sizeof(struct sockaddr_in)) != 0) {
        printf("Failure to connect: %s\n", strerror(errno));
        return 1;
    }
    printf("Connected\n");

    while (size > 0) {
        long chunk_size = min(MAX_CHUNK_SIZE, size);
        char chunk[MAX_CHUNK_SIZE];
        if (fread(chunk, chunk_size, 1, infile) != 1) {
            printf("File read error\n");
            return 1;
        }
        long sent_bytes = send(sock, chunk, chunk_size, 0);
        if (sent_bytes == -1) {
            // todo maybe better error handling
            printf("Error sending bytes\n");
            return 1;
        }
        size -= sent_bytes;
        fseek(infile, sent_bytes-chunk_size, SEEK_CUR);
    }
    printf("File sent\n");

    if (shutdown(sock, SHUT_RDWR) != 0) {
        printf("Failed to shutdown socket\n");
        return 1;
    }
    freeaddrinfo(res);
    return 0;
}

