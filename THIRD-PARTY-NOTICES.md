# 来源与许可证

- Go 官方源码及本补丁中保留的 Go 源码版权头：[Go](https://go.dev/)，BSD 3-Clause，见 [LICENSE](LICENSE)。发布基线、源归档 SHA256 和官方提交见 [manifest.json](manifest.json)。
- musl 动态 TLS 参考：[golang/go PR 75048](https://github.com/golang/go/pull/75048)，固定 head `1a087d05b5cf9573876b18812d8d5516f16bbe57`；代码按 Go 项目许可证保留原版权头。补丁保留的 `doc/design/cshared-musl-tls.md` 是该 PR 的原始设计提案，架构状态及实现细节反映提案当时的内容；本次 OHOS 移植的实际范围与验证结果以 README 和 docs/VALIDATION.md 为准。
- OHOS 适配参考：[openharmony-sig/ohos_golang_go](https://gitcode.com/openharmony-sig/ohos_golang_go)，`release-branch.go1.24`，提交 `302a5306b6fad2f47196360b82561d1db1f954cf`。未把该仓库旧版完整源码作为新版本发布。
- 测试使用的签名工具：[developtools_hapsigner](https://gitcode.com/openharmony/developtools_hapsigner)，提交 `f5f158687ccbaafb683662f62cc6da77ec3c80ee`，Apache-2.0。ARMv7 构建使用本仓库的 `hapsigner-arm32.patch` 修复 32 位 long 溢出。其构建读取 OpenHarmony 第三方 OpenSSL、cJSON、ELFIO、bounds_checking_function 源码及同一 QEMU 的 libcrypto；这些依赖和签名工具不包含在 Go 发布归档中。
- 测试使用的原生 Zig、OpenHarmony SDK、全系统 QEMU 镜像为外部输入，保留各自许可证。QEMU 镜像校验值固定在 manifest；SDK 不随 Go 重分发。原生 C 测试驱动只组合现有编译前端和未修改 SDK 的 CRT/库，不替换系统 ABI。
- HiLog 线协议参考：[OpenHarmony hiviewdfx_hilog](https://github.com/openharmony/hiviewdfx_hilog)，提交 `393d7e9a690edb76ed27e710b472623daf650dc8`，Apache-2.0。Go 传输实现独立编写，按该版本的 28 字节 HilogMsg 布局与日志服务通信；不随产物重分发 HiLog 库。

每个 Go 发布归档保留上游 LICENSE/PATENTS 文件及源版权头。本地测试结果不表示上述项目为本补丁背书。


- gomobile 配套适配固定官方 x/mobile `19777044486779222400e9ca16c4306f9c6dbfa9`，
  保留 BSD 3-Clause 和 PATENTS；Ark 测试入口使用固定版本的 OpenHarmony
  Ability Runtime 头文件，保留 Apache-2.0 头及完整许可证。详见
  [mobile 来源声明](mobile/THIRD-PARTY-NOTICES.md)。SDK 测试凭据不进入仓库或归档。
