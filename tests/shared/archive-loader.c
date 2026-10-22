#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>

extern int64_t GoAnswer(int64_t);
static void *call_go(void *unused) {
    for (int i = 0; i < 32; i++) if (GoAnswer(i) != i * 2 + 1) abort();
    return NULL;
}
int main(void) {
    pthread_t t[4];
    for (int i = 0; i < 4; i++) if (pthread_create(&t[i], NULL, call_go, NULL)) return 1;
    for (int i = 0; i < 4; i++) pthread_join(t[i], NULL);
    puts("GO_OHOS_CARCHIVE_OK");
    return 0;
}
