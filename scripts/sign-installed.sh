#!/system/bin/sh
# Run ON OHOS after unpacking a cross-built native OHOS toolchain.
set -eu
task_go="${1:?usage: sign-installed.sh /absolute/path/to/go}"
test -x /system/bin/param || { echo 'run this installer on OHOS' >&2; exit 1; }
command -v binary-sign-tool >/dev/null
for task_file in "$task_go"/bin/* "$task_go"/pkg/tool/openharmony_*/* "$task_go"/ohos-scripts/cc-* "$task_go"/ohos-scripts/cxx-*; do
    test -f "$task_file" || continue
    # All supported OHOS targets are little-endian ELF. Sign ET_EXEC/ET_DYN.
    set -- $(od -An -tx1 -N4 "$task_file")
    test "$*" = '7f 45 4c 46' || continue
    set -- $(od -An -tu2 -j16 -N2 "$task_file")
    case "${1:-}" in
        2|3)
            binary-sign-tool sign -inFile "$task_file" -outFile "$task_file" -selfSign 1
            chmod 755 "$task_file"
            ;;
    esac
done
