#!/system/bin/sh
# Missing built-in tools must be rebuilt for the actual OHOS host and signed,
# even when GOOS selects a different application target.
set -eu
task_root="${GO_OHOS_TEST_ROOT:-/data/local/tmp/go-patch}"
export GOROOT="$task_root/go" GOTOOLCHAIN=local GOENV=off CGO_ENABLED=0
export GOCACHE="$task_root/go-cache" TMPDIR="$task_root/tmp"
export PATH="$task_root/bin:$GOROOT/bin:$PATH"
task_dir=$(go env GOTOOLDIR)
task_cover="$task_dir/cover"
task_backup="$task_cover.go-patch-backup"
test -f "$task_cover"
test ! -e "$task_backup"
mv "$task_cover" "$task_backup"
trap 'mv "$task_backup" "$task_cover"' EXIT
task_built=$(GOOS=linux go tool -n cover)
go version -m "$task_built" > "$task_root/lazy-tool-buildinfo.log"
grep -q 'GOOS=openharmony' "$task_root/lazy-tool-buildinfo.log"
binary-sign-tool display-sign -inFile "$task_built" > "$task_root/lazy-tool-signature.log"
echo NATIVE_LAZY_TOOL_PASS
