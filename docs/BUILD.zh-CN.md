# 构建与验证 OHOS Go 工具链

ABI revision 2 正在重新验证，C18 结果仅为历史记录。系统集成和设备专项见 [INTEGRATION.zh-CN.md](INTEGRATION.zh-CN.md)。


[English](BUILD.md) | 简体中文 | [使用说明](../README.zh-CN.md)

本文说明适配工具链的源码构建、补丁维护与本地产物核验。使用解压后的工具链开发应用，请阅读 [README](../README.zh-CN.md)。

## 前置依赖

- 在 arm64 或 amd64 的 macOS/Linux 上运行构建脚本。
- Python 3.11+、Git、Bash 及宿主常规开发工具。
- 首次下载 Go 源码与引导工具链需要网络；版本与 SHA256 固定在 [manifest.json](../manifest.json)。
- cgo 应用测试需要适合当前构建宿主的 OpenHarmony native SDK；纯 Go 目标构建无需 SDK。
- 运行验证另需完整 OHOS QEMU 镜像、HDC、e2fsprogs、原生 OHOS C/C++ 编译器测试依赖及真正的 `binary-sign-tool`。部署细节见 [QEMU.md](QEMU.md)。

SDK、QEMU 镜像、原生 Zig 和签名工具属于独立依赖，不随 Go 归档分发。

## 1. 准备源码并应用补丁

```sh
git clone https://github.com/openharmony-command-package/go-patch.git
cd go-patch
python3 scripts/manage.py prepare
```

脚本下载固定版本的官方源码和引导工具链，检查 SHA256、源码版本，再应用 [Go 补丁](../patch/go-ohos-1.27.3.patch)。重复应用不会重复修改源码。

| 本地路径 | 内容 |
|---|---|
| `.work/upstream/go/` | 应用补丁后的 Go 源码 |
| `.work/bootstrap/go/` | 引导工具链 |
| `.work/logs/` | 构建与测试日志 |
| `.work/products/` | 打包前展开的工具链目录 |
| `dist/` | 压缩包及校验文件 |

以上生成目录和本地 `artifacts/` 目录均被 Git 忽略。

为已有、版本匹配的 Go checkout 应用补丁：

```sh
python3 scripts/manage.py --source /absolute/path/to/go apply
```

## 2. 构建工具链与压缩包

```sh
python3 scripts/manage.py build
```

脚本先从适配源码构建宿主工具链，再交叉构建配置中的宿主/原生工具，生成九份归档：

| 宿主 | `--targets` 名称 | 格式 |
|---|---|---|
| Linux | `linux-arm64`、`linux-amd64` | `.tar.gz` |
| macOS | `darwin-arm64`、`darwin-amd64` | `.tar.gz` |
| Windows | `windows-arm64`、`windows-amd64` | `.zip` |
| OHOS | `openharmony-arm64`、`openharmony-arm`、`openharmony-amd64` | `.tar.gz` |

可只构建部分目标，或指定输出目录：

```sh
python3 scripts/manage.py build --targets linux-amd64,windows-amd64,darwin-arm64
python3 scripts/manage.py build --targets openharmony-arm --output /absolute/path/to/output
```

仅当宿主工具链与当前适配源码一致时使用 `--skip-host`；源码变化后应先重建宿主。

归档顶层统一为 `go/`，附独立 `.sha256` 文件，默认文件名为 `go1.27.3.<target>.tar.gz` 或 `.zip`。每份归档包含：

- 完整的官方 `test/` 语言用例目录。
- 记录补丁和依赖身份的 `BUILD-INFO.json`、`OHOS-MANIFEST.json`。
- `ohos-scripts/` 下的原生 SDK CC/CXX 包装程序。
- `ohos-port/` 下的中英文 README、构建/维护文档、补丁、脚本、测试与验证报告。

从其他宿主构建的 OHOS 原生工具链，须先在设备上进行安装签名，见 [原生使用说明](../README.zh-CN.md#ohos-原生-go-与自动自签名)。

## 3. 验证应用构建

配置当前宿主使用的 SDK：

```sh
export OHOS_NDK_HOME=/absolute/path/to/openharmony/native
python3 scripts/test-cross.py --sdk "$OHOS_NDK_HOME"
python3 scripts/test-host.py --toolchain /absolute/path/to/extracted/go --sdk "$OHOS_NDK_HOME"
```

交叉构建检查覆盖 OHOS 三架构的纯 Go/cgo 可执行文件、共享库、C 静态库及 C 调用程序。宿主验证应在需要验收的实际操作系统和架构上执行；生成 Windows 归档本身不等于完成 Windows 运行验证。

## 4. 准备真实签名工具并运行全系统测试

签名工具构建使用 manifest 固定的 OpenHarmony hapsigner 源码、OpenHarmony `third_party` 源码，需要 CMake/Ninja、Perl/make、native SDK，以及从匹配 OHOS 镜像提取的 `libcrypto`。ARMv7 使用仓库中的 [32 位 hapsigner 补丁](../patch/hapsigner-arm32.patch) 修复缓冲区大小常量溢出。

```sh
python3 scripts/build-signer.py --arch arm64 --sdk "$OHOS_NDK_HOME" \
  --hapsigner /path/to/developtools_hapsigner --third-party /path/to/openharmony/third_party \
  --libcrypto /path/to/libcrypto-arm64.so --work .work/signer-arm64
```

按 [QEMU.md](QEMU.md) 使用固定的完整系统镜像并部署依赖。QEMU 脚本的架构名称与 Go 目标名称不同：

| Go 目标 | QEMU 脚本 `--arch` | 原生测试范围 |
|---|---|---|
| `arm64` | `arm64` | `full` |
| `arm`（`GOARM=7`） | `armv7a` | `stdlib-tools`，另跑完整语言驱动 |
| `amd64` | `x86_64` | `stdlib-tools`，另跑完整语言驱动 |

TCG 语言驱动采用官方跨平台测试机制，在宿主编译，将目标程序送到对应的完整 OHOS guest 签名并执行。全部 2,733 个语言用例必须注册，禁止诊断过滤。原生与语言报告必须匹配同一补丁。ARMv7 使用文档记录的 POSIX 镜像配置；ARM64/x64 使用 stock 镜像及记录在案的无图形输入电源配置。

每轮测试结束后，先收集原始日志，再关闭本任务对应实例：

```sh
python3 scripts/test-qemu.py --arch armv7a --run-id arm-cgo1-r5 collect
python3 scripts/qemu.py --arch armv7a stop
```

下列命令对应当前补丁已保留的完整测试轮次。新一轮应替换成实际收集的 run-id 与路径；核验需要原始日志和目标执行审计，不能只靠仓库里的摘要：

```sh
python3 scripts/verify-validation.py \
  --arm64 .work/logs/qemu/arm64/arm64-cgo1-r11/summary.json \
  --arm .work/logs/qemu/armv7a/arm-cgo1-r5/summary.json \
  --amd64 .work/logs/qemu/x86_64/amd64-cgo1-r5/summary.json \
  --arm-language .work/logs/language/armv7a/full-c18/summary.json \
  --amd64-language .work/logs/language/x86_64/full-c18/summary.json
```

当三个实例均已部署、完整套件结束且仍在运行时，可另行验证：

```sh
python3 scripts/test-signing-boundary.py
python3 scripts/test-native-targets.py
```

它们检查自签名边界和原生九种主机/目标组合，与完整套件门槛分别计算。当前三架构完整套件通过，但 ARM 签名边界及六种原生组合尚未完成，见 [packaging-status.json](test-results/packaging-status.json)。不能用其他补丁的历史通过记录替代。

## 5. 重包与核验

文档和报告定稿后，用同一份已测试源码重包，保留受测工具的二进制内容：

```sh
python3 scripts/manage.py build --skip-host --skip-tools
python3 scripts/verify-release.py --require-tested-toolchains
```

`--skip-tools` 必须与 `--skip-host` 一起使用，检查已有补丁和源码身份后直接重包，不重新编译或替换可执行工具。仅使用 `--skip-host` 仍会重建目标工具。

该检查覆盖归档结构、版本、补丁、源码、中英文可复用文档包、可执行文件格式、完整 QEMU 证据、72 个原生工具/包装文件和四种已实测 Linux/macOS 宿主的 Go 二进制，生成 `dist/release-manifest.json` 与 `dist/SHA256SUMS`。受测二进制必须匹配已有指纹；文档重包不允许替换受测工具。

最终发布还要求自签名边界与原生九组合全部通过：

```sh
python3 scripts/verify-release.py --require-validation
```

当前补充覆盖不完整，该严格检查会明确拒绝。`--require-tested-toolchains` 不替代该门槛；未使用 `--require-validation` 生成的清单保持 `release_status=candidate` 和 `validation_required=false`。不带两个选项时，仅校验归档内容与结构。

压缩包和产物元数据保留本地，不提交 Git；上传二进制发布是独立步骤。具体覆盖及限制见 [VALIDATION.md](VALIDATION.md) 和 [JSON 总报告](test-results/summary.json)。

## 6. 维护或刷新补丁

修改固定 Go 源码时，将有意新增/删除的路径同步到 [source-paths.txt](../patch/source-paths.txt)。使用官方 Git checkout 时：

```sh
python3 scripts/manage.py --source /path/to/go refresh
```

如果 Git 仓库由官方源码 tar 包初始化，应先保留其干净基线提交，再明确传入该提交：

```sh
python3 scripts/manage.py --source /path/to/archive-checkout refresh --base PRISTINE_COMMIT
```

脚本只导出清单内路径，并更新补丁 SHA256。不要导出宿主构建生成的配置或其他无关生成文件。变更基线/依赖后，还需要更新 `manifest.json` 并重跑匹配的构建与测试。协作维护流程见 [CONTRIBUTING.zh-CN.md](../CONTRIBUTING.zh-CN.md)。
