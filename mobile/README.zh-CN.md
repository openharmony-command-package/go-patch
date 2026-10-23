# OpenHarmony gomobile

[English](README.md) · [构建说明](docs/BUILD.zh-CN.md)

本目录在 [manifest.json](manifest.json) 固定的官方 `golang.org/x/mobile`
版本上增加 OHOS HAR 绑定，配合上级仓库的 Go 工具链使用。Android 和 Apple
继续使用各自的后端。

OHOS 后端生成 ArkTS 类型接口、N-API 库及包含 `arm64-v8a`、`armeabi-v7a`、
`x86_64` 三种 ABI 的 HAR。`gomobile` 和 `gobind` 的工具包与 Go 保持相同九种
宿主组合：Linux/Windows/macOS 各 arm64、amd64，以及 OHOS arm64、ARMv7、amd64。
压缩包保留在本地 `dist/gomobile/`，构建产物不提交。

```sh
export PATH=/path/to/patched-go/bin:/path/to/gomobile/bin:$PATH
export OHOS_NDK_HOME=/path/to/openharmony/native
gomobile init -target=openharmony
gomobile bind -target=openharmony -o hello.har ./hello
# 只构建一架构：-target=openharmony/arm64；别名：-target=ohos
```

通过 OHPM 将 HAR 加为本地依赖，在 UIAbility 内初始化后调用：

```ts
import { initialize, hello } from '@gomobile/bindings';
import i18n from '@ohos.i18n';

await initialize(this.context, { timezone: i18n.getTimeZone().getID() });
const message = await hello.Hello('OpenHarmony');
```

`initialize` 从应用 Context 获取 `filesDir`、`cacheDir`、`tempDir`，交给 Go
的 `os/openharmony.Configure`。可通过 `trustedCertDirs` 显式传入应用认可的
证书目录。Go 包初始化在库加载时执行，早于此调用；依赖应用目录的业务应放到
初始化之后。生成的 Go 库会使用 Go 适配中的 HiLog 能力。

导出函数、方法、字段访问器和变量访问器均返回 Promise。字符串使用 UTF-8，
`int64`/`uint64` 使用 `bigint`，字节切片使用 `Uint8Array`。Go 对象提供
`dispose()`，同时有原生 GC 释放机制。接口可由 ArkTS 对象实现，方法可同步返回
或返回 Promise，也能在回调中再次调用 Go；Go error 会拒绝 Promise。多个 Go 包
应在同一次 bind 中绑定，应用每个进程使用一个 Go 运行库。

这里提供供 ArkUI 应用调用的库绑定。纯 Go `x/mobile/app` 的窗口、输入、OpenGL
后端，以及 `gomobile build/install` 直接生成 HAP 不在本次确认的 HAR 交付范围内。
调用方 HAP 由应用的 SDK 工具构建和签名。实际验证及限制见
[验证说明](docs/VALIDATION.zh-CN.md)，HAR 构建成功不能替代 OHOS 应用执行证据。

返回的 Go 接口对象通过 `dispose(value)` 释放。Go `int`/`uint` 使用 JavaScript 安全整数范围，完整大整数范围使用 `int64`/`uint64`。浮点 NaN/Infinity 和负零可往返传递；map、channel、可变参数和泛型 API 会在生成时明确报错。


OHOS 原生工具包包含 `scripts/sign-installed.sh`，供首次安装时为命令签名。
示例 HAR 和独立 ArkTS 调用工程见 [应用示例](examples/arkts/README.zh-CN.md)。
本次已确认 HAR 绑定与三架构交付，QEMU 内的签名 HAP 验证暂缓，Go 发行验收
仍在运行。实际通过范围及 HAR 验证命令见 [验证矩阵](docs/VALIDATION.zh-CN.md)。
