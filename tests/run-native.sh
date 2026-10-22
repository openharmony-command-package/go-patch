#!/bin/sh
# Runs the complete standard dist suite inside a full-system OHOS guest.
set -eu
task_root="${GO_OHOS_TEST_ROOT:-/data/local/tmp/go-patch}"
task_arch="${1:?usage: run-native.sh arm64|arm|amd64 [cgo-enabled]}"
task_cgo="${2:-1}"
task_name="${GO_OHOS_TEST_RUN_ID:-${task_arch}-cgo${task_cgo}}"
task_scope="${GO_OHOS_TEST_SCOPE:-full}"
# HDC inherits init's -1000 OOM protection. Test children should have normal
# eligibility for the OOM killer instead of forcing a system-wide kernel panic.
if test -w /proc/self/oom_score_adj; then
    echo 0 > /proc/self/oom_score_adj
fi
mkdir -p "$task_root/tmp" "$task_root/gopath" "$task_root/results"
mkdir "$task_root/test-running" || { echo 'a native test run is already active' >&2; exit 1; }
trap 'rmdir "$task_root/test-running"' EXIT
export GOROOT="$task_root/go" GOPATH="$task_root/gopath"
export GOCACHE="$task_root/go-cache" TMPDIR="$task_root/tmp"
export GOOS=openharmony GOHOSTOS=openharmony GOARCH="$task_arch" GOARM=7
export GOTOOLCHAIN=local GOENV=off CGO_ENABLED="$task_cgo"
export GO_BUILDER_NAME="openharmony-${task_arch}-qemu"
task_timeout_scale=5
case "$task_arch" in
    arm|amd64) task_timeout_scale=20 ;; # full-system TCG compilation is much slower
esac
export GOMAXPROCS="${GOMAXPROCS:-2}" GO_TEST_TIMEOUT_SCALE="${GO_TEST_TIMEOUT_SCALE:-$task_timeout_scale}"
task_dist_maxbg="${GO_TEST_DIST_MAXBG:-1}"
# dist -maxbg serializes commands; go -p separately bounds package builds.
# Keep all tests while avoiding concurrent large SSA compiler processes.
task_build_parallel="${GO_OHOS_BUILD_PARALLELISM:-1}"
export GOFLAGS="${GOFLAGS:+$GOFLAGS }-p=$task_build_parallel"
export PATH="$task_root/bin:$GOROOT/bin:$PATH"
export ZIG_GLOBAL_CACHE_DIR="$task_root/zig-global" ZIG_LOCAL_CACHE_DIR="$task_root/zig-cache"
export CC="$task_root/bin/cc" CXX="$task_root/bin/cxx" AR="$task_root/bin/ar"
cd "$GOROOT/src"
echo "Test scope: $task_scope" > "$task_root/results/$task_name-environment.txt"
echo "GOMAXPROCS=$GOMAXPROCS GO_TEST_TIMEOUT_SCALE=$GO_TEST_TIMEOUT_SCALE" >> "$task_root/results/$task_name-environment.txt"
echo "GOFLAGS=$GOFLAGS" >> "$task_root/results/$task_name-environment.txt"
echo "dist maxbg=$task_dist_maxbg" >> "$task_root/results/$task_name-environment.txt"
if test -r /proc/self/oom_score_adj; then
    echo "oom_score_adj=$(cat /proc/self/oom_score_adj)" >> "$task_root/results/$task_name-environment.txt"
fi
go version >> "$task_root/results/$task_name-environment.txt"
go env -json >> "$task_root/results/$task_name-environment.txt"
set +e
case "$task_scope" in
    full) go tool dist test -no-rebuild -k -json -maxbg="$task_dist_maxbg" > "$task_root/results/$task_name-dist.json" 2>&1 ;;
    stdlib-tools) go tool dist test -no-rebuild -k -json -maxbg="$task_dist_maxbg" -run '!^cmd/internal/testdir' > "$task_root/results/$task_name-dist.json" 2>&1 ;;
    *) echo "unknown scope: $task_scope" >&2; exit 2 ;;
esac
task_status=$?
echo "$task_status" > "$task_root/results/$task_name-status"
exit "$task_status"
