# Building gomobile OHOS

[中文](BUILD.zh-CN.md)

Use Python 3.12+, Git, the parent repository's Go 1.27.3 toolchain, and an OHOS
native SDK whose compiler runs on your build host. The upstream revision and
patch are pinned in `mobile/manifest.json` and `mobile/patch/`.

From the parent repository root:

```sh
python3 mobile/scripts/manage.py prepare
python3 mobile/scripts/manage.py check
python3 mobile/scripts/manage.py build
```

`prepare` creates or checks `.work/upstream/mobile` and applies the reusable
patch. `check` applies it to a fresh upstream snapshot and compares every port
source. `build` creates both commands for all nine platforms and records binary
SHA256, upstream revision, mobile patch SHA256 and Go patch SHA256 in each
archive. `--go /path/to/go/bin/go` selects an unpacked patched Go release.
`--targets darwin-arm64` selects a subset. `build --skip-build` repacks
existing matching binaries after documentation changes.

For source development, edit `.work/upstream/mobile`, then export with
`python3 mobile/scripts/manage.py refresh`. Add every new source to
`mobile/patch/source-paths.txt`. Build wrappers through the patched Go package;
OHOS bind requires its `ohos-scripts` compiler executables. Explicit CC, CXX and
AR can select a native OHOS compiler environment.

Do not run an upstream `gomobile init` that installs an unpatched `gobind@latest`.
Use `gomobile init -target=openharmony`, which checks the paired tools and SDK.
The OHOS binder checks that both tools have the same patch revision.

The generated HAR is a gzip tar containing `package/`, consumed by OHPM. The
application HAP build must include and sign its native libraries. Linux and
Windows need the matching host SDK compiler for HAR construction; cross-built
tool executables alone are not evidence of those host SDKs running.


A separate `gomobile-ohos-port-<commit>.tar.gz` contains the reusable patch,
scripts, bilingual documentation, tests and ArkTS example. The same sources
are included in each tool archive. Run `python3 mobile/scripts/verify.py` after
packaging to check all nine executable formats, binary hashes and HAR ABIs.
The strict `--require-validation` gate currently rejects the missing signed
HAP application execution evidence.

Native OHOS installation needs the matching patched Go in `PATH` and a real
`binary-sign-tool`. Before executing cross-built commands, run on the device:

```sh
BINARY_SIGN_TOOL=/path/to/binary-sign-tool sh gomobile/scripts/sign-installed.sh "$PWD/gomobile"
export PATH=/path/to/go/bin:$PWD/gomobile/bin:$PATH
```

The caller example is under `mobile/examples/arkts/`. Its debug build keeps
native symbols so the HAP libraries can be compared byte for byte with the
validated HAR. Application signing is a separate final packaging step.

Reproducible validation scripts:

- `test-host.py`: pass `--go`, `--gobind`, `--node`, `--node-include`,
  `--typescript`; performs strict TS checking and the 27 Node transport checks.
- `test-ark.py`: pass `--arch arm64|arm|amd64`, `--har`, `--go`, `--sdk`,
  `--node`, `--typescript`, `--es2abc`, and a unique `--run-id`. Reuses only the
  task's existing full-system QEMU. It runs 29 real Ark checks and records raw
  evidence; it does not install an application or change its permissions.
- `test-tools.py`: pass `--host`, optionally `--product`; Linux also requires
  an existing matching `--image` and `--go-toolchain`. Executes the paired
  commands; it is not a full SDK bind matrix.
- `test-hap-build.py`: pass `--har`, `--sdk-home`, `--node`, `--ohpm`, `--hvigor`,
  and a new `--output` directory. Builds the caller and verifies all three
  embedded libraries against the HAR. Produces an unsigned HAP.

`--typescript` is the path to the compiler's `lib/typescript.js`; `--es2abc`
is the SDK bytecode compiler. Do not reuse an old run's evidence after a Go,
mobile patch, fixture, or HAR change. JSON reports may be committed; raw logs,
archives, SDKs, images and generated projects remain ignored.
