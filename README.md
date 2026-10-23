# Go OHOS Patch

English | [简体中文](README.zh-CN.md)

Reusable patches and scripts for adding OpenHarmony support to **Go 1.27.3**. The port supports `openharmony/arm64`, `openharmony/arm` (ARMv7, `GOARM=7`), and `openharmony/amd64`. Upstream Go, SDK, source references, and QEMU images are pinned in [manifest.json](manifest.json).

## What this repository adds

- Three OHOS targets for cross compilation and native Go toolchains.
- Dynamic TLS and musl integration for cgo executables, Go shared libraries, C archives, and callbacks from C threads.
- SDK C/C++ wrappers for Linux, macOS, Windows, and OHOS; Windows wrappers are native `.exe` programs.
- Automatic self-signing of executables and shared libraries built by Go running on OHOS.
- HiLog mirroring and explicit log/slog adapters, OHOS CA/timezone discovery,
  libc socket hooks, and application Context configuration.
- Reusable patch files, build scripts, full-system QEMU validation, and reports that identify the exact tested patch.

| Toolchain host | Architectures |
|---|---|
| Linux | arm64, amd64 |
| macOS | arm64, amd64 |
| Windows | arm64, amd64 |
| OHOS | arm64, ARMv7, amd64 |

The toolchains are generated locally; archives, build caches, device images, and artifact metadata are excluded from Git. Each toolchain archive contains the reusable port under `go/ohos-port/` and records its patch identity in `go/BUILD-INFO.json`.

To build the toolchains or apply the patch to your own Go source, see the separate [build guide](docs/BUILD.md).

## Use a patched toolchain

The commands below run in your application project after extracting a toolchain for your host. Set `GOROOT` to that extracted `go/` directory.

```sh
export GOROOT=/absolute/path/to/go
export PATH="$GOROOT/bin:$PATH"
export GOTOOLCHAIN=local
GOOS=openharmony GOARCH=arm64 CGO_ENABLED=0 go build -o hello ./hello.go
```

Use `GOOS=openharmony`; `ohos` is not an alias. Select the target with:

| Target | Settings |
|---|---|
| ARM64 | `GOARCH=arm64` |
| ARMv7 | `GOARCH=arm GOARM=7` |
| x64 | `GOARCH=amd64` |

Pure Go builds do not require an OHOS SDK. Keep `GOTOOLCHAIN=local` so the command uses the patched toolchain; upstream automatic toolchain downloads do not include this port.

### cgo, shared libraries, and C archives

Set `OHOS_NDK_HOME` to an OpenHarmony **native SDK** for your build host. SDK 26.0.0.105 (API 26) was used for validation.

```sh
export OHOS_NDK_HOME=/absolute/path/to/openharmony/native
export GOOS=openharmony GOARCH=arm64 GOARM=7 CGO_ENABLED=1
export CC="$GOROOT/ohos-scripts/cc-$GOARCH"
export CXX="$GOROOT/ohos-scripts/cxx-$GOARCH"
export AR="$OHOS_NDK_HOME/llvm/bin/llvm-ar"
go build -o hello ./hello.go
go build -buildmode=c-shared -o libhello.so ./library
go build -buildmode=c-archive -o libhello.a ./library
```

The shared-library/archive package must be a Go `main` package with the appropriate C exports. After changing `GOARCH`, update `CC` and `CXX` too.

On Windows, use the native wrappers from PowerShell. Adding the wrapper directory to `PATH` also handles Go installations whose paths contain spaces:

```powershell
$env:GOROOT = 'C:\go-ohos'
$env:PATH = "$env:GOROOT\bin;$env:GOROOT\ohos-scripts;$env:PATH"
$env:GOTOOLCHAIN = 'local'
$env:OHOS_NDK_HOME = 'C:\OpenHarmony\Sdk\native'
$env:GOOS = 'openharmony'
$env:GOARCH = 'arm64'
$env:GOARM = '7'
$env:CGO_ENABLED = '1'
$env:CC = "cc-$($env:GOARCH).exe"
$env:CXX = "cxx-$($env:GOARCH).exe"
$env:AR = "$env:OHOS_NDK_HOME\llvm\bin\llvm-ar.exe"
go build -o hello ./hello.go
```

When setting `CC`/`CXX` to a full path containing spaces instead of a wrapper name, preserve quotes inside the environment value.

### Deploy a cross-built executable

With the device connected through HDC and a real `binary-sign-tool` available in its shell `PATH`:

```sh
hdc file send hello /data/local/tmp/hello
hdc shell 'binary-sign-tool sign -inFile /data/local/tmp/hello -outFile /data/local/tmp/hello -selfSign 1 && chmod 755 /data/local/tmp/hello && /data/local/tmp/hello'
```

### Native OHOS Go and automatic self-signing

Install a real `binary-sign-tool` in the OHOS device's `PATH`. Transfer the archive matching the device, then run these commands **on OHOS** (ARM64 example):

```sh
cd /data/local/tmp
tar -xzf go1.27.3.openharmony-arm64.tar.gz
sh go/ohos-scripts/sign-installed.sh "$PWD/go"
export GOROOT="$PWD/go"
export PATH="$GOROOT/bin:$PATH"
export GOTOOLCHAIN=local
go version
CGO_ENABLED=0 go build -o hello /path/to/hello.go
./hello
```

The installation script signs the native Go tools and wrappers. Subsequent native builds sign OHOS ELF executables/shared libraries after the final build ID is written, before they enter the build cache. A signing failure fails the build. Direct `go tool link` is covered too.

Automatic signing applies when **both the running Go host and the output target are OHOS**. It includes OHOS cross-architecture outputs. Builds from Linux/macOS/Windows and outputs targeting another OS are not automatically signed. Static `.a` archives and relocatable `.o` files are not signed. Cross-built applications require deployment signing and executable permissions; application-packaged libraries follow the application's packaging/signing process.

Pure Go native builds can use `CGO_ENABLED=0`. Native cgo also needs a C/C++ compiler that runs on the device. SDKs and the signing tool are separate dependencies; signer preparation is documented in the [build guide](docs/BUILD.md).

### Detect OHOS at runtime

The toolchain uses `openharmony` for `go env GOOS GOHOSTOS` and tool directories. For compatibility with existing packages, `runtime.GOOS` remains `linux`; use the added `runtime.IsOpenharmony` constant to identify OHOS. Code referencing that constant requires this patched Go toolchain.

### System services and application Context

Go stdout/stderr and runtime diagnostics additionally appear in HiLog. Use
`log/hilog` for explicit metadata and `os/openharmony.Configure` to pass an
application's private directories before starting business goroutines. See
[system/application integration](docs/INTEGRATION.md) for examples, system CA,
timezone, network behavior, HDC testing and exact cgo/sandbox boundaries.

## gomobile bindings

The [gomobile companion port](mobile/README.md) adds three-ABI HAR generation,
typed ArkTS calls, N-API callbacks and Context directory initialization. It
provides gomobile/gobind for the same nine tool hosts, plus reusable patch and
build scripts. See its independent [build guide](mobile/docs/BUILD.md),
[ArkTS caller example](mobile/examples/arkts/README.md) and
[validation record](mobile/docs/VALIDATION.md). The confirmed scope is HAR
bindings and three-ABI delivery; signed HAP validation in QEMU is deferred.

## Validation status

ABI revision 2 adds system/application integration and is undergoing fresh
validation. C20 ARM64 full validation, the three platform integration checks
(28 cases each), native signing boundaries, and all nine native host/target
combinations have passed. ARMv7/x64 C20 full validation is running; the task
ARM64 QEMU has been closed. Reports must match the current patch. Previous C18 three-architecture
full-suite results are retained as [history](docs/test-results/history/c18/summary.json).
Current archives remain candidates until their own gates pass. See the
[validation record](docs/VALIDATION.md) and [current summary](docs/test-results/summary.json).

## Documentation and references

- [Build, patch, and validate](docs/BUILD.md) / [中文构建说明](docs/BUILD.zh-CN.md)
- [System/application integration](docs/INTEGRATION.md) / [系统与应用集成](docs/INTEGRATION.zh-CN.md)
- [Contributing](CONTRIBUTING.md) / [仓库维护](CONTRIBUTING.zh-CN.md)
- [Detailed QEMU setup](docs/QEMU.md) and [issue audit](docs/ISSUES.md) (Chinese)
- References: [golang/go PR 75048](https://github.com/golang/go/pull/75048) and [OpenHarmony Go](https://gitcode.com/openharmony-sig/ohos_golang_go). Exact revisions and attribution are in [manifest.json](manifest.json) and [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).
