/* Print how many bytes of the given files are resident in the page cache (mincore).
 * Used to check that a "cold" benchmark run really starts cold.
 * build: gcc -O2 pagecache_resident.c -o bin/pagecache_resident
 * usage: pagecache_resident <file>...   -> "<resident_bytes> <total_bytes>" */
#define _GNU_SOURCE
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

int main(int argc, char **argv) {
    long pg = sysconf(_SC_PAGESIZE);
    unsigned long long res = 0, tot = 0;
    for (int i = 1; i < argc; i++) {
        int fd = open(argv[i], O_RDONLY);
        if (fd < 0) { perror(argv[i]); return 1; }
        struct stat st;
        if (fstat(fd, &st) || st.st_size == 0) { close(fd); continue; }
        void *p = mmap(NULL, (size_t)st.st_size, PROT_READ, MAP_SHARED, fd, 0);
        if (p == MAP_FAILED) { perror("mmap"); return 1; }
        size_t np = ((size_t)st.st_size + pg - 1) / pg;
        unsigned char *v = malloc(np);
        if (!v || mincore(p, (size_t)st.st_size, v)) { perror("mincore"); return 1; }
        for (size_t k = 0; k < np; k++) res += (v[k] & 1) ? (unsigned long long)pg : 0;
        tot += (unsigned long long)st.st_size;
        free(v); munmap(p, (size_t)st.st_size); close(fd);
    }
    printf("%llu %llu\n", res, tot);
    return 0;
}
