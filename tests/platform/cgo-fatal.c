// Exercise the same pre-runtime diagnostic helper linked into runtime/cgo.
#include "gcc_fatalf.c"
int main(void) { fatalf("GO_OHOS_CGO_FATAL %s", getenv("GO_OHOS_PLATFORM_RUN")); }
