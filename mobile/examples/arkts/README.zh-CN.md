# ArkTS 调用示例

[English](README.md)

这是调用示例 HAR 的最小 Stage 应用。将 HAR 复制到本文件旁的
`gomobile-ohos-example.har`，安装 `entry` 的 OHPM 依赖，使用安装了 API 26
的 DevEco Studio 打开。在 `local.properties` 配置本机 SDK 根目录；也可以
从 mobile 目录使用 `scripts/test-hap-build.py` 将示例复制到被忽略的工作目录构建。

`EntryAbility` 等待 `initialize(this.context)`，检查 Go 收到的 files/cache/temp
路径，通过 Go 写入私有文件，调用 UTF-8 和对象接口，并验证再次调用 Go 的
异步回调。结果写到 `this.context.filesDir/gomobile-result.txt`，并输出到
`GoMobileTest` HiLog。成功标记为 `GOMOBILE_OHOS_HAP_PASS`。

最终 HAP 使用应用正常签名身份签名，安装系统需具备对应代码签名驱动和证书服务。
当前固定 QEMU 没有 `/dev/code_sign`，因此编译成功和安装执行成功分别记录。
示例不会关闭信任或签名校验。
