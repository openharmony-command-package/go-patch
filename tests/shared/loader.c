#include <dlfcn.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int64_t (*answer)(int64_t);
static void *call_go(void *unused) {
    for (int i = 0; i < 32; i++) {
        if (answer(i) != i * 2 + 1) abort();
    }
    return NULL;
}
int main(int argc, char **argv) {
    if (argc != 2) return 2;
    char value[16385]; memset(value, 'x', 16384); value[16384] = 0;
    if (setenv("GO_OHOS_LONG_ENV", value, 1)) return 6;
    void *h = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (!h) { fprintf(stderr, "%s\n", dlerror()); return 3; }
    answer = (int64_t (*)(int64_t))dlsym(h, "GoAnswer");
    int (*envlen)(void) = (int (*)(void))dlsym(h, "GoEnvironmentLength");
    if (!answer || !envlen || envlen() != 16384) return 4;
    pthread_t threads[4];
    for (int i = 0; i < 4; i++) if (pthread_create(&threads[i], NULL, call_go, NULL)) return 5;
    for (int i = 0; i < 4; i++) pthread_join(threads[i], NULL);
    puts("GO_OHOS_DLOPEN_OK");
    return 0;
}
