# gomobile for OpenHarmony

[中文](README.zh-CN.md) · [Build](docs/BUILD.md)

This companion port adds OHOS HAR bindings to the pinned official
`golang.org/x/mobile` revision in [manifest.json](manifest.json). It uses the
patched Go toolchains from the parent repository. Android and Apple use their
existing backends.

The OHOS backend generates a typed ArkTS API, N-API library and a HAR containing
`arm64-v8a`, `armeabi-v7a` and `x86_64` binaries. Both `gomobile` and `gobind` are
packaged for the same nine hosts as Go: Linux/Windows/macOS arm64 and amd64,
and native OHOS arm64, ARMv7 and amd64. Archives stay under local
`dist/gomobile/`; build outputs are not committed.

```sh
export PATH=/path/to/patched-go/bin:/path/to/gomobile/bin:$PATH
export OHOS_NDK_HOME=/path/to/openharmony/native
gomobile init -target=openharmony
gomobile bind -target=openharmony -o hello.har ./hello
# One ABI: -target=openharmony/arm64; alias: -target=ohos
```

Install `hello.har` as a local OHPM dependency and call the generated package:

```ts
import { initialize, hello } from '@gomobile/bindings';
import i18n from '@ohos.i18n';

// In UIAbility, before business calls:
await initialize(this.context, { timezone: i18n.getTimeZone().getID() });
const message = await hello.Hello('OpenHarmony');
```

`initialize` receives `filesDir`, `cacheDir`, and `tempDir` from the application
Context. It delegates to Go's `os/openharmony.Configure`; optional approved CA
directories can be passed as `trustedCertDirs`. Go package initialization runs
when the library loads, before this call. Keep directory-dependent work out of
Go `init` functions. Go's HiLog integration applies to the generated library.

All exported calls, methods, field accessors and variable accessors return
Promises. Strings use UTF-8, `int64`/`uint64` use `bigint`, byte slices use
`Uint8Array`, and Go objects have `dispose()` plus native GC finalizers. Interface
methods can be implemented by ArkTS objects and may return a value or Promise.
Callbacks may invoke Go again. Errors reject the Promise. Bind all Go packages
in one invocation so the application uses one Go runtime library per process.

This backend provides library bindings for an ArkUI application. The existing
pure Go `x/mobile/app` window/input/OpenGL backend and `gomobile build/install`
HAP generation are a separate application-port scope. Build and sign the caller
HAP with the application's SDK tooling. See [validation](docs/VALIDATION.md)
for actual test evidence and remaining limits; a compiled HAR alone does not
prove execution in an OHOS application.

Use `dispose(value)` for returned Go interface objects. Go `int`/`uint` map to safe JavaScript integers; use `int64`/`uint64` for the full bigint range. Non-finite floating-point values are preserved. Unsupported maps, channels, variadic and generic APIs fail during generation.


Native OHOS tool archives include `scripts/sign-installed.sh` for initial
installation signing. The generated HAR example and an independent ArkTS
caller are described in [the example](examples/arkts/README.md).
Current artifacts are candidates; see the exact [validation matrix](docs/VALIDATION.md).
