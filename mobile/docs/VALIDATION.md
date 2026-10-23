# Validation

[中文](VALIDATION.zh-CN.md)

The confirmed delivery scope is **HAR bindings for three OHOS ABIs**. The user
confirmed this scope on 2026-10-23 and deferred signed HAP validation in QEMU;
see the [scope record](test-results/delivery-scope.json). The parent Go release
validation is still running, so the combined artifacts remain candidates.
The mobile patch SHA256 is
`5a8ce153a45eb0abf4a8e9bc553ab70908335e4dce4de98377903d904b988923`.
The example HAR was built with Go 1.27.3 and Go patch
`cb9c9199b60e78fcb052526b86dcb657c11b07e4dbd3d13b757ddfa583cb8d69`.
The parent Go port has its own full-suite and signing gates; passing mobile
checks does not replace those gates.

| Check | Actual result |
|---|---|
| Fresh pinned upstream + patch | All adapted sources match |
| Generator and OHOS target tests | Passed |
| Generated TypeScript | Strict type checking passed |
| Host Node 24.14.1 N-API tests | 27 passed |
| OHOS ARM64 Ark/N-API | 29 passed |
| OHOS ARMv7 Ark/N-API | 29 passed |
| OHOS x64 Ark/N-API | 29 passed |
| Tool command execution | macOS/Linux arm64+amd64 and OHOS all three passed |
| Windows arm64+amd64 tools | Built; executable formats checked; not executed |
| ArkTS caller HAP | Built; all three libraries equal the tested HAR byte for byte |
| Signed caller HAP installation and application UID execution | Deferred in QEMU by the user; unverified |

The 29 Ark checks cover 27 functional cases and two checks in a second runtime
environment. They exercise UTF-8/NUL, bytes, bigint limits, objects, errors and
panic rejection, interface values, retained and concurrent callbacks, nested Go
calls, external named types, non-finite floats and negative zero, and environment cleanup. Go
observes the exact Context files/cache/temp paths and writes a file into the
provided files directory. These are explicit shell sandbox paths, not evidence
of an installed application's private directory permissions.

The Ark harness creates real OHOS runtime environments and calls the generated
N-API library. Its pinned inner runtime setup is test-only; generated bindings
use public N-API. Reports in [test-results](test-results/) bind the HAR, native
library, Go/mobile patches, test inputs, and raw log hashes. Raw logs and binaries
stay local under `.work/` and `dist/`.

The current QEMU image lacks `/dev/code_sign` and `/dev/xpm`. Normal installation
of the signed HAP fails with 9568404 while adding the certificate path. No trust
roots, code-sign checks, or application privileges were bypassed. The user
authorized deferring this QEMU check; it is excluded only from the explicit HAR
validation scope. A compatible image or real HDC device is still needed for signed HAP execution, application
UID/private directory permissions, and application lifecycle validation. Use
[the caller example](../examples/arkts/README.md) for that next step.

The same full upstream test command was run on pristine and patched x/mobile.
Both have the same six failing tests: local Foundation header/clang, Android
`aapt` fixture, and Apple/module fixture differences. The full upstream
suite is **not** claimed as passed. See [source tests](test-results/source-tests.json).
Linux/Windows SDK-driven HAR builds, HiShell devices, other API images, and the
pure Go window/input/OpenGL application backend have not been validated.

`python3 mobile/scripts/verify.py` checks the nine archives and example HAR.
For the confirmed scope, run:

```sh
python3 mobile/scripts/verify.py --require-validation --validation-scope har
```

This requires current three-ABI Ark evidence, Node/TypeScript tests, seven host
command reports, and caller HAP compilation with byte-identical libraries. It
does not claim signed application execution. The default `--require-validation`
continues to require a successful signed HAP application report and still fails
while that evidence is missing. Go native self-signing remains required.
