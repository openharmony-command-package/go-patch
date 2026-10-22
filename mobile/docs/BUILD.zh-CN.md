# 构建 gomobile OHOS

[English](BUILD.md)

需要 Python 3.12+、Git、上级仓库的 Go 1.27.3，以及编译器可在当前宿主运行的
OHOS 原生 SDK。上游版本和补丁固定在 `mobile/manifest.json`、`mobile/patch/`。

在仓库根目录执行：

```sh
python3 mobile/scripts/manage.py prepare
python3 mobile/scripts/manage.py check
python3 mobile/scripts/manage.py build
```

`prepare` 创建或检查 `.work/upstream/mobile` 并应用补丁；`check` 对干净的上游
快照应用补丁，逐文件比较适配源码；`build` 为九种平台构建两个命令并归档，记录
二进制 SHA256、上游版本、mobile 补丁及 Go 补丁的 SHA256。可使用
`--targets darwin-arm64` 指定子集，文档更新后通过 `build --skip-build` 保留已有
匹配二进制重新打包。

开发时修改 `.work/upstream/mobile`，再执行
`python3 mobile/scripts/manage.py refresh` 导出补丁。新源码须加入
`mobile/patch/source-paths.txt`。构建 HAR 使用 Go 包内的 `ohos-scripts` 编译器
包装程序，也可显式设置 CC、CXX、AR 指向 OHOS 原生编译环境。

初始化使用 `gomobile init -target=openharmony`，检查同版本的工具和 SDK；
上游的 init 会安装未适配的 `gobind@latest`。OHOS bind 会检查两个工具的补丁
版本一致。

HAR 使用 gzip tar 的 `package/` 结构，通过 OHPM 引入。调用方 HAP 构建须纳入
并签名原生库。Linux 和 Windows 构建 HAR 需要相应宿主版本的 SDK 编译器；工具
压缩包交叉构建成功不代表这些 SDK 已实际执行。


`build --go /path/to/go/bin/go` 可选择已解压的适配 Go 工具链。构建还会生成独立
的 `gomobile-ohos-port-<commit>.tar.gz`，包含补丁、脚本、中英文文档、测试与
ArkTS 示例，每份工具包也携带这些文件。重包后执行
`python3 mobile/scripts/verify.py`，核对九种工具格式、二进制校验和及 HAR 三种 ABI。
严格的 `--require-validation` 当前会因签名 HAP 应用执行证据缺失而拒绝发布。

OHOS 原生使用时，`PATH` 需有匹配的适配 Go 和真正的 `binary-sign-tool`。
首次执行交叉构建的命令前，在设备内运行：

```sh
BINARY_SIGN_TOOL=/path/to/binary-sign-tool sh gomobile/scripts/sign-installed.sh "$PWD/gomobile"
export PATH=/path/to/go/bin:$PWD/gomobile/bin:$PATH
```

调用示例位于 `mobile/examples/arkts/`。示例 debug 构建保留原生符号，使 HAP
内的动态库能与受测 HAR 逐字节比较，最终应用签名单独完成。

可复现验证脚本：

- `test-host.py`：传入 `--go`、`--gobind`、`--node`、`--node-include`、
  `--typescript`，执行严格 TS 类型检查及 27 项 Node 绑定检查。
- `test-ark.py`：传入 `--arch arm64|arm|amd64`、`--har`、`--go`、`--sdk`、
  `--node`、`--typescript`、`--es2abc` 和独立 `--run-id`，使用本任务已启动的
  完整 QEMU，执行 29 项真实 Ark 检查；不会安装应用或修改应用权限。
- `test-tools.py`：传入 `--host`，可指定 `--product`；Linux 还需本地匹配的
  `--image` 和 `--go-toolchain`。验证两个工具实际执行，不表示完整 SDK 构建矩阵。
- `test-hap-build.py`：传入 `--har`、`--sdk-home`、`--node`、`--ohpm`、`--hvigor`
  及新 `--output` 目录，构建调用方并比对 HAP 中的三架构库，产出未签名 HAP。

`--typescript` 指向编译器的 `lib/typescript.js`，`--es2abc` 指向 SDK 字节码编译器。
Go、mobile 补丁、测试夹具或 HAR 变化后必须重新验证。JSON 报告可以提交，
原始日志、归档、SDK、镜像和生成项目均保留在被忽略的本地目录。
