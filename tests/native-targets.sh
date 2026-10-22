#!/system/bin/sh
# Run a packaged native OHOS Go against every supported OHOS target.
set -eu
task_root="${GO_OHOS_TEST_ROOT:-/data/local/tmp/go-patch}"
task_dir="$task_root/native-targets"
mkdir -p "$task_dir" "$task_root/tmp"
export GOROOT="$task_root/go" GOTOOLCHAIN=local GOENV=off GOOS=openharmony
export GOARM=7 CGO_ENABLED=0 GOMAXPROCS=2 TMPDIR="$task_root/tmp"
export GOCACHE="$task_dir/cache"
export PATH="$task_root/bin:$GOROOT/bin:$PATH"
task_host="$("$GOROOT/bin/go" env GOHOSTARCH)"
cat > "$task_dir/main.go" <<'GO'
package main
import (
    "fmt"
    "runtime"
)
func main() {
    if !runtime.IsOpenharmony { panic("wrong target OS") }
    fmt.Println("NATIVE_TARGET_OK", runtime.GOARCH)
}
GO
for task_arch in arm64 arm amd64; do
    GOARCH="$task_arch" "$GOROOT/bin/go" build -o "$task_dir/from-$task_host-to-$task_arch" "$task_dir/main.go"
    echo "NATIVE_BUILD_OK $task_host $task_arch"
done
