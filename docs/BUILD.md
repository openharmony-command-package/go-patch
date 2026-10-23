# Build and validate the OHOS Go toolchains

ABI revision 2 is undergoing fresh validation. C18 results are historical. System integration and device verification are described in [INTEGRATION.md](INTEGRATION.md).


English | [简体中文](BUILD.zh-CN.md) | [Usage](../README.md)

This guide covers building the patched Go distribution, maintaining the patch, and verifying local archives. For application development with an extracted toolchain, see [README](../README.md).

## Prerequisites

- macOS or Linux on arm64 or amd64 to run the build scripts.
- Python 3.11+, Git, Bash, and the host's normal development tools.
- Network access for the initial Go source and bootstrap downloads; versions and SHA256 values are pinned in [manifest.json](../manifest.json).
- An OpenHarmony native SDK for cgo application tests. The SDK must run on your build host; pure Go target builds do not need it.
- For runtime validation: the full-system OHOS QEMU images, HDC, e2fsprogs, native OHOS C/C++ compiler fixtures, and a real `binary-sign-tool`. Detailed provisioning is in [QEMU.md](QEMU.md) (Chinese).

SDKs, QEMU images, native Zig, and the signing tool are separate dependencies and are not distributed in the Go archives.

## 1. Prepare source and apply the patch

```sh
git clone https://github.com/openharmony-command-package/go-patch.git
cd go-patch
python3 scripts/manage.py prepare
```

The script downloads the fixed official source/bootstrap archives, checks their SHA256 values and source version, then applies the [Go patch](../patch/go-ohos-1.27.3.patch). Applying it again is idempotent.

| Local path | Contents |
|---|---|
| `.work/upstream/go/` | Patched Go source |
| `.work/bootstrap/go/` | Bootstrap toolchain |
| `.work/logs/` | Build and test logs |
| `.work/products/` | Expanded toolchain trees before packaging |
| `dist/` | Archives and checksum files |

These generated directories are ignored by Git, as is any local `artifacts/` directory.

To apply the patch to an existing checkout with the pinned Go version:

```sh
python3 scripts/manage.py --source /absolute/path/to/go apply
```

## 2. Build toolchains and archives

```sh
python3 scripts/manage.py build
```

This builds the host toolchain from the patched source, cross-builds all configured host/native tools, and produces nine archives:

| Host | `--targets` names | Format |
|---|---|---|
| Linux | `linux-arm64`, `linux-amd64` | `.tar.gz` |
| macOS | `darwin-arm64`, `darwin-amd64` | `.tar.gz` |
| Windows | `windows-arm64`, `windows-amd64` | `.zip` |
| OHOS | `openharmony-arm64`, `openharmony-arm`, `openharmony-amd64` | `.tar.gz` |

Choose a subset or an output directory:

```sh
python3 scripts/manage.py build --targets linux-amd64,windows-amd64,darwin-arm64
python3 scripts/manage.py build --targets openharmony-arm --output /absolute/path/to/output
```

Use `--skip-host` only when the host toolchain already matches the current patched source. After a source change, rebuild the host first.

Every archive has a top-level `go/` directory and a separate `.sha256` file. The default filenames are `go1.27.3.<target>.tar.gz` or `.zip`. Each archive includes:

- The full official `test/` language directory.
- `BUILD-INFO.json` and `OHOS-MANIFEST.json` for patch and dependency provenance.
- Native SDK CC/CXX wrappers in `ohos-scripts/`.
- The Chinese/English README, build/contribution guides, patches, scripts, tests, and validation reports in `ohos-port/`.

Native OHOS toolchains built on another host require installation signing on the device. See [native use](../README.md#native-ohos-go-and-automatic-self-signing).

## 3. Validate application builds

After setting up the SDK for your host:

```sh
export OHOS_NDK_HOME=/absolute/path/to/openharmony/native
python3 scripts/test-cross.py --sdk "$OHOS_NDK_HOME"
python3 scripts/test-host.py --toolchain /absolute/path/to/extracted/go --sdk "$OHOS_NDK_HOME"
```

The cross-build checks cover all three OHOS architectures, pure Go and cgo executables, shared libraries, C archives, and C callers. Run host checks on the actual host OS/architecture being certified; generating a Windows archive alone does not establish Windows runtime support.

## 4. Prepare the real signer and run full-system tests

The signer helper builds from the pinned OpenHarmony hapsigner source and OpenHarmony `third_party` sources. It needs CMake/Ninja, Perl/make, the native SDK, and a `libcrypto` extracted from the matching OHOS image. ARMv7 uses the included [32-bit hapsigner patch](../patch/hapsigner-arm32.patch) to fix an overflowing buffer-size constant.

```sh
python3 scripts/build-signer.py --arch arm64 --sdk "$OHOS_NDK_HOME" \
  --hapsigner /path/to/developtools_hapsigner --third-party /path/to/openharmony/third_party \
  --libcrypto /path/to/libcrypto-arm64.so --work .work/signer-arm64
```

Use the pinned full-system QEMU images and the provisioning steps in [QEMU.md](QEMU.md). The architecture names used by QEMU helpers differ from Go target names:

| Go target | QEMU helper `--arch` | Native test scope |
|---|---|---|
| `arm64` | `arm64` | `full` |
| `arm` (`GOARM=7`) | `armv7a` | `stdlib-tools`, plus the full language driver |
| `amd64` | `x86_64` | `stdlib-tools`, plus the full language driver |

The TCG language driver uses the official cross-platform test machinery, compiles on the host, and signs/runs target programs in the matching full OHOS guest. All 2,733 language cases must be registered, without a diagnostic filter. Native and language results must match the same patch. ARMv7 requires the documented POSIX image profile; ARM64/x64 use stock images with the recorded headless power configuration.

After each suite finishes, collect raw logs before stopping that task's VM:

```sh
python3 scripts/test-qemu.py --arch armv7a --run-id arm-cgo1-c20-r1 collect
python3 scripts/qemu.py --arch armv7a stop
```

The commands below identify the retained complete runs for the current patch. For a new run, replace paths/run IDs with its actual collected results; the verifier requires the raw logs and target-execution audits, not just committed summaries:

```sh
python3 scripts/verify-validation.py \
  --arm64 .work/logs/qemu/arm64/arm64-cgo1-c20-r1/summary.json \
  --arm .work/logs/qemu/armv7a/arm-cgo1-c20-r1/summary.json \
  --amd64 .work/logs/qemu/x86_64/amd64-cgo1-c20-r1/summary.json \
  --arm-language .work/logs/language/armv7a/full-c20/summary.json \
  --amd64-language .work/logs/language/x86_64/full-c20/summary.json
```

Additional native checks are available while the three provisioned guests are running, after their full suites finish:

```sh
python3 scripts/test-signing-boundary.py
python3 scripts/test-native-targets.py
```

These certify signing boundaries and the nine native host/target combinations. They are independent of the full-suite gate. C20 signing boundaries and all nine native combinations have passed. ARM64 full validation passed; ARMv7/x64 C20 full validation is running, as recorded in [packaging-status.json](test-results/packaging-status.json). Do not substitute historical success from another patch.

## 5. Repackage and verify

After the docs and reports are finalized, repackage from the same tested source. Preserve the bytes of the tested tools:

```sh
python3 scripts/manage.py build --skip-host --skip-tools
python3 scripts/verify-release.py --require-tested-toolchains
```

`--skip-tools` requires `--skip-host`, checks the existing patch/source identity, and repacks without recompiling or replacing executable tools. `--skip-host` alone still rebuilds target tools.

This checks archive structure, versions, patch, source, bilingual port bundle, executable formats, complete QEMU evidence, 72 native tool/wrapper files, and the four tested Linux/macOS Go binaries. It writes `dist/release-manifest.json` and `dist/SHA256SUMS`. Files must match their recorded binary fingerprints; repackaging documentation does not authorize changing the tested tools.

For final release certification, the signing boundaries and all nine native combinations must also be complete:

```sh
python3 scripts/verify-release.py --require-validation
```

This strict command currently rejects the incomplete ARMv7/x64 C20 full-suite evidence. `--require-tested-toolchains` does not bypass it: a manifest produced without `--require-validation` retains `release_status=candidate` and `validation_required=false`. Running the verifier without either option checks archive contents/structure only.

Archives and artifact metadata remain local and are excluded from Git. Publishing binary releases is a separate step. Current coverage and limitations are in [VALIDATION.md](VALIDATION.md) (Chinese) and the [JSON summary](test-results/summary.json).

## 6. Maintain or refresh the patch

Edit the pinned Go source and update [source-paths.txt](../patch/source-paths.txt) for intentional additions/deletions. With an official Git checkout:

```sh
python3 scripts/manage.py --source /path/to/go refresh
```

If using a Git repository initialized from an official source tarball, first retain its pristine baseline commit and pass that commit explicitly:

```sh
python3 scripts/manage.py --source /path/to/archive-checkout refresh --base PRISTINE_COMMIT
```

Only listed source paths are exported, with a refreshed patch SHA256. Avoid exporting build-generated host configuration or unrelated generated files. Changing the baseline/dependencies also requires updating `manifest.json` and rerunning the matching builds and tests. Contribution workflow: [CONTRIBUTING.md](../CONTRIBUTING.md).
