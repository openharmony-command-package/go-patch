# Go OHOS 三架构补丁

[English](README.md) | 简体中文

以 **Go 1.27.3** 为基线，为 `openharmony/arm64`、`openharmony/arm`（ARMv7，`GOARM=7`）和 `openharmony/amd64` 提供可复用的适配补丁与脚本。Go、SDK、参考源码和 QEMU 镜像的版本固定在 [manifest.json](manifest.json)。

## 仓库新增能力

- 三种 OHOS 目标的交叉编译与原生 Go 工具链。
- 动态 TLS 与 musl 适配，支持 cgo 可执行文件、Go 共享库、C 静态库及 C 线程回调。
- Linux、macOS、Windows 和 OHOS 的 SDK C/C++ 包装程序；Windows 使用原生 `.exe`。
- 在 OHOS 上运行的 Go 自动为生成的可执行文件和共享库自签名。
- HiLog 镜像与 log/slog 接口、OHOS CA/时区发现、libc socket 钩子和应用 Context 配置。
- 可复用补丁、构建脚本、全系统 QEMU 验证及与受测补丁对应的报告。

| 工具链宿主 | 架构 |
|---|---|
| Linux | arm64、amd64 |
| macOS | arm64、amd64 |
| Windows | arm64、amd64 |
| OHOS | arm64、ARMv7、amd64 |

工具链在本地生成；压缩包、构建缓存、设备镜像和产物元数据不纳入 Git。每份工具链归档的 `go/ohos-port/` 携带完整可复用补丁与脚本，`go/BUILD-INFO.json` 记录补丁身份。

从源码构建工具链或为已有 Go 源码应用补丁，请阅读独立的 [构建说明](docs/BUILD.zh-CN.md)。

## 使用适配后的工具链

先解压适合当前宿主的工具链，将 `GOROOT` 指向其中的 `go/`。以下命令在你的应用项目中执行。

```sh
export GOROOT=/absolute/path/to/go
export PATH="$GOROOT/bin:$PATH"
export GOTOOLCHAIN=local
GOOS=openharmony GOARCH=arm64 CGO_ENABLED=0 go build -o hello ./hello.go
```

`GOOS` 使用 `openharmony`；`ohos` 不是别名。目标架构设置如下：

| 目标 | 设置 |
|---|---|
| ARM64 | `GOARCH=arm64` |
| ARMv7 | `GOARCH=arm GOARM=7` |
| x64 | `GOARCH=amd64` |

纯 Go 交叉编译无需 OHOS SDK。保留 `GOTOOLCHAIN=local`，确保使用这份适配工具链；官方自动下载的工具链不包含本补丁。

### cgo、共享库与 C 静态库

将 `OHOS_NDK_HOME` 指向适合当前构建宿主的 OpenHarmony **native SDK**。本地验证使用 SDK 26.0.0.105（API 26）。

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

共享库和静态库的 Go 包应为 `main` 包，并按需声明 C 导出接口。切换 `GOARCH` 后，同步更新 `CC` 和 `CXX`。

Windows 可在 PowerShell 中使用原生包装程序。将包装程序目录加入 `PATH`，也适用于 Go 安装路径包含空格的情况：

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

若直接把包含空格的完整路径填入 `CC`/`CXX`，环境变量值内需保留路径引号。

### 部署交叉编译的可执行文件

通过 HDC 连接设备，并在设备 shell 的 `PATH` 中安装真正的 `binary-sign-tool` 后：

```sh
hdc file send hello /data/local/tmp/hello
hdc shell 'binary-sign-tool sign -inFile /data/local/tmp/hello -outFile /data/local/tmp/hello -selfSign 1 && chmod 755 /data/local/tmp/hello && /data/local/tmp/hello'
```

### OHOS 原生 Go 与自动自签名

先在设备的 `PATH` 中安装真正的 `binary-sign-tool`，传入匹配设备架构的工具链归档，然后**在 OHOS 上**执行以下命令（以 ARM64 为例）：

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

安装脚本为原生 Go 工具和包装程序签名。后续原生构建会在最终 build ID 写入后、产物进入构建缓存前，为 OHOS ELF 可执行文件和共享库签名；签名失败会导致构建失败。直接调用 `go tool link` 也会处理。

自动签名条件是**运行 Go 的宿主和输出目标均为 OHOS**，包括 OHOS 跨架构输出。Linux/macOS/Windows 上的交叉编译，以及输出其他操作系统的构建，不会自动签名。静态 `.a` 和可重定位 `.o` 不签名。交叉编译的应用需在部署时签名并设置执行权限；应用包内动态库遵守应用的打包与签名流程。

原生纯 Go 构建可使用 `CGO_ENABLED=0`；原生 cgo 还需要能在设备上运行的 C/C++ 编译器。SDK 和签名工具属于独立依赖，签名工具的准备方式见 [构建说明](docs/BUILD.zh-CN.md)。

### 在运行时判断 OHOS

`go env GOOS GOHOSTOS` 和工具目录使用 `openharmony`。为兼容已有第三方代码，`runtime.GOOS` 保持 `linux`；使用新增的 `runtime.IsOpenharmony` 常量判断 OHOS。引用该常量的代码需要使用本适配工具链编译。

### 系统服务与应用 Context

Go 标准输出和 runtime 诊断会额外进入 HiLog。`log/hilog` 可指定日志元数据，
`os/openharmony.Configure` 用于在业务启动前传入应用私有目录。系统 CA、时区、
网络、HDC 测试及 cgo/沙箱边界见 [系统与应用集成](docs/INTEGRATION.zh-CN.md)。

## gomobile 绑定

[gomobile 配套适配](mobile/README.zh-CN.md) 支持三架构 HAR、带类型的 ArkTS
调用、N-API 双向回调及 Context 目录初始化。gomobile/gobind 工具包与 Go 保持
相同九种宿主组合，并提供可复用补丁与脚本。构建方式、独立 ArkTS 调用工程和
实际通过范围分别见 [构建说明](mobile/docs/BUILD.zh-CN.md)、
[应用示例](mobile/examples/arkts/README.zh-CN.md) 和
[验证记录](mobile/docs/VALIDATION.zh-CN.md)。本次确认先交付 HAR 绑定与三架构，
QEMU 内暂缓签名 HAP 验证。

## 验证状态

ABI revision 2 新增系统与应用集成，正在进行新一轮验证，报告必须匹配新补丁。
上一版 C18 三架构完整测试结果保留在 [历史记录](docs/test-results/history/c18/summary.json)。
当前归档在各自验收门槛通过前保持候选状态，见 [验证记录](docs/VALIDATION.md)
和 [当前总报告](docs/test-results/summary.json)。

## 文档与参考

- [构建、补丁与验证说明](docs/BUILD.zh-CN.md) / [English build guide](docs/BUILD.md)
- [系统与应用集成](docs/INTEGRATION.zh-CN.md) / [System/application integration](docs/INTEGRATION.md)
- [仓库维护](CONTRIBUTING.zh-CN.md) / [Contributing](CONTRIBUTING.md)
- [完整 QEMU 配置](docs/QEMU.md) 与 [issue 审计](docs/ISSUES.md)
- 参考 [golang/go PR 75048](https://github.com/golang/go/pull/75048) 和 [OpenHarmony Go 仓库](https://gitcode.com/openharmony-sig/ohos_golang_go)。固定版本与来源说明见 [manifest.json](manifest.json) 及 [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md)。
