# OHOS system and application integration

English | [简体中文](INTEGRATION.zh-CN.md)

This guide describes ABI revision 2 of this port. It covers services beyond the
Linux syscall ABI. Test reports identify the exact patch; previous revision
results do not certify new binaries.

## Logs

Go writes to the original stdout/stderr and additionally mirrors complete lines
to HiLog (`LOG_APP`, domain `0`, tag `Go`). Stdout uses INFO; stderr and runtime
diagnostics use ERROR. `print`, `println`, panic and stack traces use the same
runtime transport, including `CGO_ENABLED=0`. The optional native HiLog API also
receives pre-runtime `runtime/cgo` fatal diagnostics.

The Go transport uses the pinned packed HilogMsg protocol over the local datagram
socket. It allocates no memory, takes no Go mutex, uses bounded buffers and never
blocks a crashing process. Missing/congested hilogd or reentrant logging can drop
the additional copy; stdout/stderr and `debug.SetCrashOutput` remain available.
Partial stream lines are buffered until a newline or buffer boundary. Native C
stdio is outside Go's os.File mirror; C/Native code should call its HiLog API.

Use `GO_OHOS_HILOG=0` to disable automatic mirroring at startup. For explicit
levels, domain and tag, use the new standard-library package:

```go
import (
    "log"
    "log/hilog"
    "log/slog"
)

log.SetOutput(hilog.Writer{Domain: 0x1234, Tag: "MyApp", Level: hilog.Info})
logger := slog.New(hilog.NewHandler(0x1234, "MyApp", nil))
logger.With("component", "network").Warn("connection interrupted")
```

These APIs receive already formatted text and publish that text and its
attributes. They do not interpret native `%{private}` format directives. The
daemon's filtering and quotas still apply. Check logs with `hdc shell hilog -x
-T Go,MyApp`; `-t` selects log types, not tags.

## Trust anchors and timezone

`crypto/x509` additionally searches `/etc/security/certificates` and
`/system/etc/security/certificates`. `SSL_CERT_FILE` and `SSL_CERT_DIR` retain
their standard override behavior. The application can explicitly supply
Certificate Manager-approved CA directories through `Config.TrustedCertDirs`.
The port does not recursively import other users' certificate stores or replace
application trust policy with all certificates found on the device.

An explicit `TZ` takes priority. Otherwise the port queries
`persist.time.timezone` through an optional runtime/cgo parameter bridge. A pure
Go shell executable can use the fixed `/bin/param` utility, with bounded output
and a bounded wait. If the service/utility is inaccessible, `/etc/localtime` and
UTC remain fallbacks. The existing OHOS tzdata parser handles named zones.

Like upstream Go, `time.Local` initializes once. Configure a supplied timezone
before its first use. An application that must follow live timezone changes
should observe platform changes and load/use the new `time.Location` explicitly.

## Application Context

The application obtains paths from its own Context and passes them through its
Native/N-API initialization function. Go does not infer a bundle name, storage
level or user ID from a hardcoded path. Call before starting business goroutines:

```go
import "os/openharmony"

err := openharmony.Configure(openharmony.Config{
    FilesDir: filesDir,
    CacheDir: cacheDir,
    TempDir: tempDir,
    Timezone: timezone,
})
```

All three directories must exist and be absolute paths. Configure sets `HOME`,
`XDG_CONFIG_HOME` (the `.config` child of FilesDir), `XDG_CACHE_HOME` and `TMPDIR`.
It does not create directories or expand their permissions. Context values also
reach C's environment when runtime/cgo is linked. Shell binaries retain
`/data/local/tmp` as their default temporary directory. `os/user.Current` can
represent an application UID absent from passwd; UID/GID remain the real IDs.

## Networking

Use `CGO_ENABLED=1` for applications needing system DNS, interface enumeration,
application network selection and VPN protection. DNS defaults to libc;
interfaces use libc getifaddrs; socket creation now calls libc so OHOS's socket
hook can apply its network selection. `netgo` changes DNS selection but does not
disable the libc socket/interface integration when cgo is enabled.

`CGO_ENABLED=0` remains available for SDK-independent Go programs. Its networking
uses Linux syscalls and resolv.conf/netlink conventions; it does not acquire
OHOS network services, permissions, or application network binding automatically.
An application can provide an explicit `net.Resolver` for its own DNS transport.
Do not assume that successful compilation grants network permissions.

## ELF and runtime boundaries

Executable, PIE, c-shared and c-archive are distinct modes. Use `-buildmode=pie`
with the configured SDK for an explicitly PIE executable; HAP Native libraries
use c-shared/PIC and the HAP's packaging/signature process. Native Go ELF
self-signing remains a deployment capability, not HAP authorization.

ARM64 byte/string scans now use MTE-safe read boundaries. This code change does
not claim hardware MTE validation. The pinned QEMU images use 4 KiB pages;
different page-size kernels and SDKs require their own ELF/runtime checks.
Android-specific bionic TLS slots, JNI startup and chipset workarounds are not
used. OHOS keeps the musl TLS and sigchain implementation already in this port.

## Verification and devices

`scripts/test-platform.py` builds cgo=0/1, netgo and PIE variants for a selected
full-system QEMU. It checks native CA loading, default timezone, Context paths,
socket interposition, normal/panic/C-fatal HiLog output, long records and opt-out.
The interposition test proves the libc entry path; physical VPN and network
selection behavior still requires an application/device scenario.

`scripts/hdc-exec.py` supports noninteractive `go test -exec` on a selected real
device. It uses a unique private directory, real deployment signing, separate
stdout/stderr and the remote exit code. Example:

```sh
go test -exec "python3 /path/to/go/ohos-port/scripts/hdc-exec.py --target DEVICE_ID" ./...
```

Set `GO_OHOS_HDC`, `GO_OHOS_HDC_SERVER` or `--signer` when needed. This runner
requires shell deployment rights and a real signer. A device shell test does not
substitute for HAP loading, Native/N-API callbacks, Context lifecycle or sandbox
permission tests. Results must state which environment actually ran them.
