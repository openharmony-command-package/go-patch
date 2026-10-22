#!/system/bin/sh
# Native OHOS integration: cross-OS output must not invoke the signing helper.
set -eu
task_root="${GO_OHOS_TEST_ROOT:-/data/local/tmp/go-patch}"
task_dir="$task_root/signing-boundary/${GO_OHOS_SIGNING_RUN_ID:-default}"
mkdir -p "$task_dir"
export GOROOT="$task_root/go" GOTOOLCHAIN=local GOENV=off CGO_ENABLED=0 GOARM=7
export GOCACHE="$task_dir/cache" TMPDIR="$task_root/tmp"
cat > "$task_dir/main.go" <<'GO'
package main
func main() { println("SIGN_BOUNDARY_OK") }
GO
task_go="$GOROOT/bin/go"
# No external executable can be found in this path except the Go command.
PATH="$GOROOT/bin" GOOS=linux "$task_go" build -o "$task_dir/linux-output" "$task_dir/main.go"
if PATH="$GOROOT/bin" GOOS=openharmony "$task_go" build -o "$task_dir/must-fail" "$task_dir/main.go" > "$task_dir/missing-signer.log" 2>&1; then
    echo 'OHOS output unexpectedly succeeded without binary-sign-tool' >&2
    exit 1
fi
grep -q 'binary-sign-tool' "$task_dir/missing-signer.log"
PATH="$task_root/bin:$GOROOT/bin:$PATH" GOOS=openharmony "$task_go" build -o "$task_dir/ohos-output" "$task_dir/main.go"
"$task_dir/ohos-output"
echo NATIVE_SIGNING_BOUNDARY_PASS
