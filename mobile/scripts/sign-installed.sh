#!/system/bin/sh
# Bootstrap signing for commands cross-built on another host.
set -eu
prefix=${1:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}
signer=${BINARY_SIGN_TOOL:-binary-sign-tool}
for command in gomobile gobind; do
  "$signer" sign -inFile "$prefix/bin/$command" -outFile "$prefix/bin/$command" -selfSign 1
  chmod 755 "$prefix/bin/$command"
done
