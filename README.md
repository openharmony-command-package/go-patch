# Go OHOS 三架构补丁

以官方 **go1.27.3** 为基线，为 `openharmony/arm64`、`openharmony/arm`（ARMv7，`GOARM=7`）、`openharmony/amd64` 添加工具链支持。版本号保持官方值。源码、SDK、参考 PR 和 QEMU 镜像版本固定在 [manifest.json](manifest.json)。

**三架构完整 QEMU 测试已通过：ARM64 450 pass/245 skip、ARMv7 439 pass/243 skip、amd64 441 pass/246 skip，均无失败；每架构覆盖全部 2733 个语言用例。** 九种本地产物覆盖 Linux/macOS/Windows 各两架构及 OHOS 三架构。所有本任务 QEMU 均已关闭，镜像及原始日志保留。

本轮交付为**候选归档**：当前补丁的 ARM64/amd64 自签名边界、ARM64 原生三目标构建已通过；ARM 签名边界及其余六种原生交叉构建组合未补做，严格发布门槛尚未满足。Windows 产物仅完成构建及静态核验。完整结果和运行条件见 [验证记录](docs/VALIDATION.md)、[总报告](docs/test-results/summary.json) 与 [归档状态](docs/test-results/packaging-status.json)；全部 72 个参考 issue 的处理见 [审计表](docs/ISSUES.md)。

| 工具链宿主 | 架构 | 归档 |
|---|---|---|
| Linux | amd64、arm64 | `go1.27.3.linux-*.tar.gz` |
| macOS | amd64、arm64 | `go1.27.3.darwin-*.tar.gz` |
| Windows | amd64、arm64 | `go1.27.3.windows-*.zip` |
| OHOS 原生 | amd64、arm64、arm | `go1.27.3.openharmony-*.tar.gz` |

每种工具链都包含三种 OHOS 目标的源码支持。`GOOS` 使用参考仓库的正式名称 **`openharmony`**；`ohos` 不是别名。为兼容已有第三方代码，OHOS 的 `runtime.GOOS` 保持 `linux`，通过 `runtime.IsOpenharmony` 判断 OHOS；`go env GOOS GOHOSTOS` 和工具目录使用 `openharmony`。

## 获取源码、应用补丁和构建

构建宿主为 macOS/Linux，需要 Python 3.11+、Git、Bash。首次下载需要网络。补丁应用会校验源码版本和 SHA256，重复运行不会重复打补丁。

```sh
python3 scripts/manage.py prepare
python3 scripts/manage.py build
```

默认源码在 `.work/upstream/go`，引导工具链在 `.work/bootstrap/go`，产物在 `dist/`，完整构建日志在 `.work/logs/`。可以选择目标：

```sh
python3 scripts/manage.py build --targets linux-amd64,windows-amd64,darwin-arm64
python3 scripts/manage.py --source /absolute/path/to/go apply
```

`--skip-host` 只用于宿主工具链已与当前源码同步的情形。所有归档顶层为 `go/`，附 SHA256 文件。`go/ohos-port/` 同时携带完整补丁、构建/测试脚本、issue 审计及验证报告，可独立复用；归档中的 `BUILD-INFO.json` 记录补丁校验值，`OHOS-MANIFEST.json` 记录依赖版本。SDK 和 QEMU、Zig、签名工具不包含在 Go 归档中。

完整测试通过并更新文档后，可重新封包并执行最终发布校验：

```sh
python3 scripts/manage.py build --skip-host
python3 scripts/verify-release.py --require-validation
```

最终校验要求三架构完整 QEMU 验收、签名边界及原生九组合验证均通过，并逐项核对归档中的补丁、文档、源码、可执行文件格式及实测工具链的二进制校验值。本轮签名边界/九组合尚不完整，`--require-validation` 会明确拒绝。候选包使用以下命令核对完整 QEMU 报告、72 个原生工具及包装文件、四种实测宿主的 Go 二进制，以及归档内容：

```sh
python3 scripts/verify-release.py --require-tested-toolchains
```

校验成功后生成 `dist/release-manifest.json` 和 `dist/SHA256SUMS`。清单中的 `release_status=candidate`、`validation_required=false` 表示尚未通过严格发布门槛；`tested_toolchains_required=true` 表示实际执行了受测二进制一致性核验。Windows 保持静态格式检查。单独检查归档结构可省略两个选项。

修改源码后，在官方 Git checkout 中运行 `refresh`；用官方 tar 包初始化的临时 Git 仓库必须显式提供其干净基线提交：

```sh
python3 scripts/manage.py --source /path/to/go refresh
python3 scripts/manage.py --source /path/to/archive-checkout refresh --base PRISTINE_COMMIT
```

仅导出 [source-paths.txt](patch/source-paths.txt) 列出的修改，新增补丁文件需同步清单。避免把宿主自动生成的默认编译器配置和版本文件混入补丁。

## 交叉编译 OHOS

纯 Go 无需 SDK：

```sh
export GOROOT=/absolute/path/to/go
export PATH="$GOROOT/bin:$PATH"
export GOTOOLCHAIN=local
GOOS=openharmony GOARCH=arm64 CGO_ENABLED=0 go build -o hello ./hello.go
```

cgo、`c-shared`、`c-archive` 使用 OpenHarmony **native SDK**。已验证 SDK 26.0.0.105（API 26）。归档提供原生 CC/CXX 包装程序，避免单个可执行文件的编译器探测丢失目标参数；Windows 提供 `.exe`，不依赖 Bash/Python。

```sh
export OHOS_NDK_HOME=/absolute/path/to/openharmony/native
export GOOS=openharmony GOARCH=arm64 CGO_ENABLED=1 GOARM=7
export CC="$GOROOT/ohos-scripts/cc-$GOARCH"
export CXX="$GOROOT/ohos-scripts/cxx-$GOARCH"
export AR="$OHOS_NDK_HOME/llvm/bin/llvm-ar"
go build -o hello ./hello.go
go build -buildmode=c-shared -o libhello.so ./library
```

切换 `GOARCH=arm` 或 `amd64` 后同步设置 CC/CXX。Windows PowerShell 对应设置 `$env:GOOS` 等环境变量。将 `go/ohos-scripts` 加入 PATH 后，CC/CXX 使用 `cc-arm64.exe`/`cxx-arm64.exe`，AR 使用 SDK 的 `llvm-ar.exe`。这样也适用于包含空格的 Go 安装路径；直接设置含空格的 CC/CXX 路径时，环境变量值内还需保留引号。SDK 本身必须适合当前宿主。

固定补丁工具链的工作流使用 `GOTOOLCHAIN=local`。官方自动工具链分发尚不提供本补丁的 OHOS 工具链；升级时重新选择官方 release tag 并移植、验证补丁。

独立构建回归覆盖三架构纯 Go、cgo 可执行文件、共享库、静态库及 C 调用程序：

```sh
python3 scripts/test-cross.py --sdk "$OHOS_NDK_HOME"
# 在实际 Linux/macOS/Windows 宿主验证解包后的产物：
python3 scripts/test-host.py --toolchain /absolute/path/to/go --sdk "$OHOS_NDK_HOME"
```

## 原生签名与运行

自动自签名条件同时满足：**运行 Go 的宿主是 OHOS、构建目标也是 OHOS、输出是 ELF 可执行文件或动态库**。Linux/macOS/Windows 交叉编译 OHOS，以及 OHOS 交叉编译其他平台，都不会自动签名。静态 `.a` 和可重定位 `.o` 不签名。

原生纯 Go 构建可设置 `CGO_ENABLED=0`；原生 cgo 构建需要设备上可运行的 C/C++ 编译器。完整测试使用的原生编译器配置见 [QEMU 文档](docs/QEMU.md)。

在 OHOS 的 PATH 中安装真正的 `binary-sign-tool`。Go 在最终 build ID 更新之后、进入构建缓存之前执行：

```sh
binary-sign-tool sign -inFile OUTPUT -outFile OUTPUT -selfSign 1
```

签名失败会导致构建失败。直接 `go tool link` 同样处理 OHOS ELF；由 `go build` 调用链接器时延迟到最终 build ID 写入后签名，避免签名失效。不要在应用环境手动设置内部变量 `GOOHOS_SIGN_DEFER`。

从其他宿主构建的原生 OHOS 工具链需要先在设备安装阶段签名。这与原生构建输出的自动签名是两个阶段：

```sh
hdc file send dist/go1.27.3.openharmony-arm64.tar.gz /data/local/tmp/go.tar.gz
hdc shell 'cd /data/local/tmp && tar -xzf go.tar.gz'
hdc file send scripts/sign-installed.sh /data/local/tmp/sign-installed.sh
# 先把 binary-sign-tool 安装到设备 PATH；在 OHOS shell 内执行：
sh /data/local/tmp/sign-installed.sh /data/local/tmp/go
export PATH=/data/local/tmp/go/bin:$PATH
go version
```

交叉编译的应用也应在部署阶段按设备要求签名，再以 HDC 传输并 `chmod 755` 后运行。需要具备设备 shell 的相应权限。应用包内的动态库按应用签名/打包流程处理。

真实签名工具可由 [build-signer.py](scripts/build-signer.py) 从固定的 OpenHarmony hapsigner 源码构建；测试流程与依赖说明见 [QEMU 文档](docs/QEMU.md)。

## 补丁来源

参考 [golang/go PR 75048](https://github.com/golang/go/pull/75048) 的 musl 动态 TLS 方案，以及 [OpenHarmony Go 仓库](https://gitcode.com/openharmony-sig/ohos_golang_go) 的 OHOS 适配。原 PR 尚未合并；本补丁额外处理 ARMv7、最新官方源码变化、原生签名、网络接口及测试。来源与许可证见 [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md)。
