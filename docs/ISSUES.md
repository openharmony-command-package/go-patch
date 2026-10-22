> ABI revision 2 正在补充系统集成及重新验收。下表原有“三架构通过”描述对应历史 C18，当前补丁结果以 [VALIDATION.md](VALIDATION.md) 为准。

# 参考仓库 issue 审计

快照日期：2026-10-21。来源：[GitCode 全部 issue](https://gitcode.com/openharmony-sig/ohos_golang_go/issues)，公开 API `state=all&per_page=100` 返回 72 条（24 open，48 closed）。原始公开内容保存在 [issues-snapshot.json](issues-snapshot.json)。编号不连续是原仓库现状。

分类汇总：45 条本次适配、19 条官方版本继承、2 条本地脚本替代、2 条上游流程无需代码处理，其余 4 条分别为无需额外兼容、保留测试、文档处理及版本策略。

本表逐条记录处理方式。上游 closed 不是本项目通过测试的证据；“本次适配”表示代码已处理，运行验收状态单独列出。历史 C18 的 ARM64 r11、ARMv7 r5 与 amd64 r5 完整测试已通过，原报告见 [C18 历史总报告](test-results/history/c18/summary.json)。当前 C20 的 ARM64 全套已通过，ARM/x64 尚待补验，以 [验证记录](VALIDATION.md) 为准。这是本地固定镜像下的验证结果，不表示上游所有 issue 已关闭、真机或所有部署场景均已验证。

| Issue | 原状态 | 标题 | 处理 | 代码/理由 | 验证与限制 |
|---|---|---|---|---|---|
| [#1](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/1) | closed | net: set preferCgo to ture on openharmony | 本次适配 | OHOS 默认 preferCgo，通过 libc 解析 DNS。 | 配置已移植；三架构 net 完整包测试通过，外网域名服务不由此补丁保证。 |
| [#2](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/2) | closed | internal/platform: use external link when ohos using cgo | 本次适配 | OHOS cgo 强制外部链接，使用 SDK musl 初始化。 | 三架构外部链接构建与可执行产物 QEMU 冒烟均通过。 |
| [#3](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/3) | closed | runtime: skip registration error for 43 sig | 本次适配 | 仅在 OHOS 的 43 号信号注册失败时继续初始化。 | 三架构启动和 runtime 完整包测试通过。 |
| [#4](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/4) | closed | runtime: hold traceAcquire across casgstatus in injectglist | 官方版本继承 |runtime：injectglist/casgstatus 的 traceAcquire 生命周期；直接采用 go1.27.3，避免重复回移旧版补丁。 [官方源码](https://github.com/golang/go/blob/go1.27.3/src/runtime/proc.go)。 | 已核对当前官方实现；三架构完整套件通过。 |
| [#5](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/5) | closed | proposal: all: support openharmony/arm64 | 本次适配 | 统一 GOOS=openharmony，支持 arm64、arm(GOARM=7)、amd64；版本使用官方 go1.27.3。 | 9 种本地工具链已构建，三架构完整 QEMU 测试通过；归档为候选状态，补充签名/原生九组合覆盖见 VALIDATION.md。 |
| [#6](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/6) | open | runtime: fix crash with musllibc | 本次适配 | GD TLS、FP 保护、非 glibc 初始化共同处理 musl c-shared 崩溃。 | 三架构 release 构建 dlopen+GC+四 C 线程回调均通过；三架构完整套件通过。 |
| [#7](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/7) | closed | crypto/x509: properly check for IPv6 hosts in URIs | 官方版本继承 |crypto/x509：URI 的 IPv6 主机判断；直接采用 go1.27.3，避免重复回移旧版补丁。 [官方源码](https://github.com/golang/go/blob/go1.27.3/src/crypto/x509/verify.go)。 | 已核对当前官方实现；三架构完整套件通过。 |
| [#8](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/8) | open | 有计划将opehharmony的支持合并到官方golang仓库吗？ | 无需代码处理 | 是否合入官方由上游维护流程决定，当前交付为独立可重用补丁。 | 不能以本地适配承诺上游合入时间。 |
| [#9](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/9) | closed | cmd/compile: fix write barrier coalescing | 官方版本继承 |cmd/compile：写屏障合并修复；直接采用 go1.27.3，避免重复回移旧版补丁。 [官方源码](https://github.com/golang/go/blob/go1.27.3/src/cmd/compile/internal/ssa/writebarrier.go)。 | 已核对当前官方实现；三架构完整套件通过。 |
| [#10](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/10) | closed | ci: add build scirpts | 本地脚本替代 | 提供固定版本下载、补丁应用、构建、交叉验证和 QEMU 脚本；旧仓库门禁配置不直接回移。 | 尚未接入远程 CI；本地脚本执行记录见验证报告。 |
| [#11](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/11) | closed | proposal: all: use runtime.IsOpenharmony instead of runtime.GOOS=="openharmony" | 本次适配 | 保持 runtime.GOOS=linux 兼容第三方判断，新增 runtime.IsOpenharmony；go env 仍输出 openharmony。 | 三架构原生工具启动和标准库/工具链构建测试通过。 |
| [#12](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/12) | open | cmd: remove special treatment for elf section named  ".note.ohos.ident"  | 无需额外兼容 | 未加入跳过 .note.ohos.ident 的特殊处理，使用修复后的 SDK/musl。 | 补丁无该特殊跳过逻辑。 |
| [#13](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/13) | closed | cmd/link: function "decodetypeGcmask" read gcdata from shared object file may not correct when use lld link | 本次适配 | 从共享库重定位恢复 GC data 地址；不回移已从新版删除的 Gcprog 表示。 | 三架构 testshared 完整包测试通过。 |
| [#14](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/14) | closed | crypto/internal/fips140/nistec: make p256NegCond constant time on ppc64le | 官方版本继承 |crypto/internal/fips140/nistec：ppc64le 常数时间 p256NegCond（不属 OHOS 三架构专属逻辑）；直接采用 go1.27.3，避免重复回移旧版补丁。 [官方源码](https://github.com/golang/go/blob/go1.27.3/src/crypto/internal/fips140/nistec/p256_asm_ppc64le.s)。 | ppc64le 不属于本次三架构；保持官方常数时间实现，无需额外移植。 |
| [#15](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/15) | closed | net/http: persist header stripping across repeated redirects | 官方版本继承 |net/http：重定向敏感 header 持续剥离；直接采用 go1.27.3，避免重复回移旧版补丁。 [官方源码](https://github.com/golang/go/blob/go1.27.3/src/net/http/client.go)。 | 已核对当前官方实现；三架构完整套件通过。 |
| [#16](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/16) | closed | Add dynamic TLS model for ARM64 | 本次适配 | 参考 PR 75048 实现 GD TLS；补充 ARMv7 TLS 与寄存器保存。 | 三架构构建及 dlopen/C 四线程回调均通过；三架构 QEMU 完整测试通过。 |
| [#17](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/17) | closed | security: fix CVE-2025-22870 | 官方版本继承 |vendored x/net：CVE-2025-22870；直接采用 go1.27.3，避免重复回移旧版补丁。 [官方源码](https://github.com/golang/go/blob/go1.27.3/src/vendor/golang.org/x/net/http/httpproxy/proxy.go)。 | 已核对当前官方实现；三架构完整套件通过。 |
| [#18](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/18) | closed | net/http: reject bare LF in chunked encoding | 官方版本继承 |net/http：拒绝 chunk-size 裸 LF；直接采用 go1.27.3，避免重复回移旧版补丁。 [官方源码](https://github.com/golang/go/blob/go1.27.3/src/net/http/internal/chunked.go)。 | 已核对当前官方实现；三架构完整套件通过。 |
| [#20](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/20) | open | 有时候需要在模拟器上使用，但是没有支持openharmony/amd64，后续可以考虑支持吗 | 本次适配 | 统一 GOOS=openharmony，支持 arm64、arm(GOARM=7)、amd64；版本使用官方 go1.27.3。 | 9 种本地工具链已构建，三架构完整 QEMU 测试通过；归档为候选状态，补充签名/原生九组合覆盖见 VALIDATION.md。 |
| [#22](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/22) | closed | runtime: c-shared lib crash when using release mode to build openharmony app | 本次适配 | GD TLS、FP 保护、非 glibc 初始化共同处理 musl c-shared 崩溃。 | 三架构 release 构建 dlopen+GC+四 C 线程回调均通过；三架构完整套件通过。 |
| [#23](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/23) | closed | ci: add build scirpts | 本地脚本替代 | 提供固定版本下载、补丁应用、构建、交叉验证和 QEMU 脚本；旧仓库门禁配置不直接回移。 | 尚未接入远程 CI；本地脚本执行记录见验证报告。 |
| [#24](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/24) | closed | proposal: all: support openharmony/arm64 | 本次适配 | 统一 GOOS=openharmony，支持 arm64、arm(GOARM=7)、amd64；版本使用官方 go1.27.3。 | 9 种本地工具链已构建，三架构完整 QEMU 测试通过；归档为候选状态，补充签名/原生九组合覆盖见 VALIDATION.md。 |
| [#25](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/25) | open | 验证TestSetgidStress用例 | 保留测试 | TestSetgidStress 保持启用，不按旧参考仓库禁用。 | 三架构 TestSetgidStress 与 cshared 完整包测试通过。 |
| [#26](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/26) | closed | all: use runtime.IsOpenharmony instead of runtime.GOOS=="openharmony" | 本次适配 | 保持 runtime.GOOS=linux 兼容第三方判断，新增 runtime.IsOpenharmony；go env 仍输出 openharmony。 | 三架构原生工具启动和标准库/工具链构建测试通过。 |
| [#27](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/27) | closed | cmd/link: read gcdata address from relocation info in shlib | 本次适配 | 从共享库重定位恢复 GC data 地址；不回移已从新版删除的 Gcprog 表示。 | 三架构 testshared 完整包测试通过。 |
| [#29](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/29) | closed | internal/platform: use external link when ohos using cgo | 本次适配 | OHOS cgo 强制外部链接，使用 SDK musl 初始化。 | 三架构外部链接构建与可执行产物 QEMU 冒烟均通过。 |
| [#30](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/30) | closed | net: set preferCgo=true for openharmony | 本次适配 | OHOS 默认 preferCgo，通过 libc 解析 DNS。 | 配置已移植；三架构 net 完整包测试通过，外网域名服务不由此补丁保证。 |
| [#31](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/31) | closed | runtime: skip registration error for 43 signal | 本次适配 | 仅在 OHOS 的 43 号信号注册失败时继续初始化。 | 三架构启动和 runtime 完整包测试通过。 |
| [#32](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/32) | closed | runtime: fix segfault due to missing argv on musl-linux c-archive | 本次适配 | 非 glibc 路径补齐 argv/envp/auxv 初始化。 | 三架构 c-archive 与 dlopen 大环境变量、四线程回调测试通过。 |
| [#33](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/33) | closed | test: Enable carchive_test.go on openharmony | 本次适配 | 启用 OHOS carchive 测试并修正安装头文件目录。 | 三架构静态库四线程回调通过；三架构 carchive 完整包测试通过。 |
| [#34](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/34) | closed | cmd/asm,cmd/link,cmd/go: Add dynamic TLS model for ARM64 | 本次适配 | 参考 PR 75048 实现 GD TLS；补充 ARMv7 TLS 与寄存器保存。 | 三架构构建及 dlopen/C 四线程回调均通过；三架构 QEMU 完整测试通过。 |
| [#35](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/35) | closed | test: Enable cgo cshared tests on openharmony | 本次适配 | 启用 OHOS cshared 路径与信号测试分支，修正安装头文件目录。 | 三架构 cshared 完整包测试通过。 |
| [#36](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/36) | closed | runtime: get environ from global symbol instead of /proc/self/environ | 本次适配 | cgo 初始化时保存 libc environ 地址，启动时读取当前环境；proc 后备读取无固定 8KB 截断。 | C 先 setenv 16384 字节再 dlopen，Go 正确读到全部内容，三架构均通过。 |
| [#37](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/37) | closed | cmd/link: prefer to use the path specified by the AR environment variable as the path of the ar command | 本次适配 | 外部链接优先读取 AR 环境变量。 | 三架构 c-archive 构建通过；三架构 carchive 完整包测试通过。 |
| [#38](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/38) | closed | cmd/link: add missing fields in Shlibs | 本次适配 | 补齐共享库符号地址与 GC mask 重定位字段；使用当前版本对象表示。 | 三架构 testshared 完整包测试通过。 |
| [#39](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/39) | closed | runtime: move SP to make sure __tlsdesc-stub does not overwrite FP saved at SP-8 | 本次适配 | ARM64 GD TLS 调用前在栈上保存 R1/LR，预留 32 字节，保护 SP-8 的 FP。 | 三架构 C 四线程回调及 runtime 完整包测试通过。 |
| [#40](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/40) | closed | database/sql: avoid closing Rows while scan is in progress | 官方版本继承 |database/sql：Scan 与 Rows 生命周期保护；直接采用 go1.27.3，避免重复回移旧版补丁。 [官方源码](https://github.com/golang/go/blob/go1.27.3/src/database/sql/sql.go)。 | 已核对当前官方实现；三架构完整套件通过。 |
| [#41](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/41) | closed | crypto/tls: quote protocols in ALPN error message | 官方版本继承 |crypto/tls：ALPN 错误使用带引号协议值；直接采用 go1.27.3，避免重复回移旧版补丁。 [官方源码](https://github.com/golang/go/blob/go1.27.3/src/crypto/tls/handshake_server.go)。 | 已核对当前官方实现；三架构完整套件通过。 |
| [#42](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/42) | closed | net/mail: avoid quadratic behavior in mail address parsing | 官方版本继承 |net/mail：域字面量使用子切片；直接采用 go1.27.3，避免重复回移旧版补丁。 [官方源码](https://github.com/golang/go/blob/go1.27.3/src/net/mail/message.go)。 | 已核对当前官方实现；三架构完整套件通过。 |
| [#43](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/43) | closed | net/url: enforce stricter parsing of bracketed IPv6 hostnames | 官方版本继承 |net/url：方括号 IPv6 主机严格解析；直接采用 go1.27.3，避免重复回移旧版补丁。 [官方源码](https://github.com/golang/go/blob/go1.27.3/src/net/url/url.go)。 | 已核对当前官方实现；三架构完整套件通过。 |
| [#44](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/44) | closed | crypto/x509: improve domain name verification | 官方版本继承 |crypto/x509：域名校验（包含 #51 后续修订）；直接采用 go1.27.3，避免重复回移旧版补丁。 [官方源码](https://github.com/golang/go/blob/go1.27.3/src/crypto/x509/verify.go)。 | 已核对当前官方实现；三架构完整套件通过。 |
| [#45](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/45) | closed | crypto/x509: mitigate DoS vector when intermediate certificate contains DSA public key | 官方版本继承 |crypto/x509：不支持的 DSA 中间证书处理；直接采用 go1.27.3，避免重复回移旧版补丁。 [官方源码](https://github.com/golang/go/blob/go1.27.3/src/crypto/x509/x509.go)。 | 已核对当前官方实现；三架构完整套件通过。 |
| [#46](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/46) | closed | net/textproto: avoid quadratic complexity in Reader.ReadResponse | 官方版本继承 |net/textproto：strings.Builder 线性响应拼接；直接采用 go1.27.3，避免重复回移旧版补丁。 [官方源码](https://github.com/golang/go/blob/go1.27.3/src/net/textproto/reader.go)。 | 已核对当前官方实现；三架构完整套件通过。 |
| [#47](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/47) | closed | net/http: add httpcookiemaxnum GODEBUG option to limit number of cookies parsed | 官方版本继承 |net/http：httpcookiemaxnum Cookie 数量限制；直接采用 go1.27.3，避免重复回移旧版补丁。 [官方源码](https://github.com/golang/go/blob/go1.27.3/src/net/http/cookie.go)。 | 已核对当前官方实现；三架构完整套件通过。 |
| [#48](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/48) | closed | encoding/asn1: prevent memory exhaustion when parsing using internal/saferio | 官方版本继承 |encoding/asn1：saferio 分配限制；直接采用 go1.27.3，避免重复回移旧版补丁。 [官方源码](https://github.com/golang/go/blob/go1.27.3/src/encoding/asn1/asn1.go)。 | 已核对当前官方实现；三架构完整套件通过。 |
| [#49](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/49) | closed | encoding/pem: make Decode complexity linear | 官方版本继承 |encoding/pem：线性复杂度 Decode；直接采用 go1.27.3，避免重复回移旧版补丁。 [官方源码](https://github.com/golang/go/blob/go1.27.3/src/encoding/pem/pem.go)。 | 已核对当前官方实现；三架构完整套件通过。 |
| [#50](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/50) | closed | archive/tar: set a limit on the size of GNU sparse file 1.0 regions | 官方版本继承 |archive/tar：GNU sparse 1.0 元数据大小限制；直接采用 go1.27.3，避免重复回移旧版补丁。 [官方源码](https://github.com/golang/go/blob/go1.27.3/src/archive/tar/reader.go)。 | 已核对当前官方实现；三架构完整套件通过。 |
| [#51](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/51) | closed | crypto/x509: rework fix for CVE-2025-58187 | 官方版本继承 |crypto/x509：域名约束缓存和修订后的校验；直接采用 go1.27.3，避免重复回移旧版补丁。 [官方源码](https://github.com/golang/go/blob/go1.27.3/src/crypto/x509/verify.go)。 | 已核对当前官方实现；三架构完整套件通过。 |
| [#52](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/52) | open | 大概什么时候可以将opehharmony合并到官方golang仓库 | 无需代码处理 | 是否合入官方由上游维护流程决定，当前交付为独立可重用补丁。 | 不能以本地适配承诺上游合入时间。 |
| [#53](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/53) | closed | net: add cgo implements for interfaceTable&interfaceAddrTable on openharmony system | 本次适配 | libc getifaddrs 获取接口和地址，释放链表并关闭 ioctl fd；修正 IPv4 16 字节表示。 | 三架构冒烟通过；三架构 net 完整包测试通过。 |
| [#54](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/54) | open | 编译得到的二进制如何在鸿蒙中运行 | 文档处理 | README 提供 SDK 交叉编译、HDC 传输、签名工具与运行方式。 | 仅提供有权限的设备 shell 场景；应用沙箱权限另由部署方管理。 |
| [#55](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/55) | open | 对 golang 官方版本更新跟进的计划 | 版本策略 | 锁定官方最新稳定 release tag；升级时重新生成补丁与验证。 | 当前基线 go1.27.3；长期更新排期由维护者决定。 |
| [#56](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/56) | open | 改用tar.gz等通用压缩格式 | 本次适配 | Unix 工具链使用 tar.gz 保留执行权限；Windows 使用 zip。 | 本地产物使用通用格式及 SHA256；候选归档校验方式与发布覆盖限制见 README。 |
| [#57](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/57) | closed | Add a patch to temporaily replace syscall.Fallocate(), which is not supported on HarmonyOS yet. | 本次适配 | Fallocate 返回 ENOSYS/ENOTSUP 时保留 Truncate 后的 mmap 回退。 | 源码已处理；HiShell 真机未测。 |
| [#58](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/58) | closed | Integrate external-binary signing method into the ohos_golang_go workflow, enabled direct complier usage on HiShell. | 本次适配 | 仅 OHOS 宿主构建 OHOS ELF EXEC/DYN 时调用 binary-sign-tool；最终 build ID 写入后签名。 | 三架构原生完整套件通过并实际签名输出；ARM64/amd64 缺失签名工具时失败及 OHOS→Linux 不签名的边界通过，ARM 边界与其余六种原生交叉组合本轮未完成，HiShell 真机未测。 |
| [#59](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/59) | closed | Add a patch to temporaily replace syscall.Fallocate(), which is not supported on HarmonyOS yet. | 本次适配 | Fallocate 返回 ENOSYS/ENOTSUP 时保留 Truncate 后的 mmap 回退。 | 源码已处理；HiShell 真机未测。 |
| [#60](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/60) | open | go升级到1.26.5 | 本次适配 | 统一 GOOS=openharmony，支持 arm64、arm(GOARM=7)、amd64；版本使用官方 go1.27.3。 | 9 种本地工具链已构建，三架构完整 QEMU 测试通过；归档为候选状态，补充签名/原生九组合覆盖见 VALIDATION.md。 |
| [#61](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/61) | closed | Correction of the directory after bootstrapping. | 本次适配 | GOOSForTools 保证原生工具目录、引导默认平台与运行时 Linux 兼容值分离。 | 三架构原生 go env GOOS/GOHOSTOS=openharmony，完整工具链测试通过。 |
| [#62](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/62) | open | all: Adaptation on openharmony/arm64 platform. | 本次适配 | 统一 GOOS=openharmony，支持 arm64、arm(GOARM=7)、amd64；版本使用官方 go1.27.3。 | 9 种本地工具链已构建，三架构完整 QEMU 测试通过；归档为候选状态，补充签名/原生九组合覆盖见 VALIDATION.md。 |
| [#63](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/63) | open | CMD/Link: read gcdata address from relocation info in shlib | 本次适配 | 从共享库重定位恢复 GC data 地址；不回移已从新版删除的 Gcprog 表示。 | 三架构 testshared 完整包测试通过。 |
| [#64](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/64) | open | internal/platform: use external link when ohos using cgo | 本次适配 | OHOS cgo 强制外部链接，使用 SDK musl 初始化。 | 三架构外部链接构建与可执行产物 QEMU 冒烟均通过。 |
| [#65](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/65) | open | net: set preferCgo=true for openharmony | 本次适配 | OHOS 默认 preferCgo，通过 libc 解析 DNS。 | 配置已移植；三架构 net 完整包测试通过，外网域名服务不由此补丁保证。 |
| [#66](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/66) | open | runtime: skip registration error for 43 signal | 本次适配 | 仅在 OHOS 的 43 号信号注册失败时继续初始化。 | 三架构启动和 runtime 完整包测试通过。 |
| [#67](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/67) | open | runtime: fix segfault due to missing argv on musl-linux c-archive | 本次适配 | 非 glibc 路径补齐 argv/envp/auxv 初始化。 | 三架构 c-archive 与 dlopen 大环境变量、四线程回调测试通过。 |
| [#68](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/68) | open | test: Enabled carchive_test.go on openharmony | 本次适配 | 启用 OHOS carchive 测试并修正安装头文件目录。 | 三架构静态库四线程回调通过；三架构 carchive 完整包测试通过。 |
| [#69](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/69) | open | cmd/asm,cmd/link,cmd/go: Add dynamic TLS model for ARM64 | 本次适配 | 参考 PR 75048 实现 GD TLS；补充 ARMv7 TLS 与寄存器保存。 | 三架构构建及 dlopen/C 四线程回调均通过；三架构 QEMU 完整测试通过。 |
| [#70](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/70) | open | test: Enable cgo cshared tests on openharmony | 本次适配 | 启用 OHOS cshared 路径与信号测试分支，修正安装头文件目录。 | 三架构 cshared 完整包测试通过。 |
| [#71](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/71) | open | runtime: get environ from global symbol instead of /proc/self/environ | 本次适配 | cgo 初始化时保存 libc environ 地址，启动时读取当前环境；proc 后备读取无固定 8KB 截断。 | C 先 setenv 16384 字节再 dlopen，Go 正确读到全部内容，三架构均通过。 |
| [#72](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/72) | open | cmd/link: prefer to use the path specified by the AR enviroment variable as the path of the ar command. | 本次适配 | 外部链接优先读取 AR 环境变量。 | 三架构 c-archive 构建通过；三架构 carchive 完整包测试通过。 |
| [#73](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/73) | open | cmd/link: add missing fields in Shlibs | 本次适配 | 补齐共享库符号地址与 GC mask 重定位字段；使用当前版本对象表示。 | 三架构 testshared 完整包测试通过。 |
| [#74](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/74) | open | runtIme: move SP to makesure __tlsdesc-stub does not overwrite FP saved at SP-8 | 本次适配 | ARM64 GD TLS 调用前在栈上保存 R1/LR，预留 32 字节，保护 SP-8 的 FP。 | 三架构 C 四线程回调及 runtime 完整包测试通过。 |
| [#75](https://gitcode.com/openharmony-sig/ohos_golang_go/issues/75) | open | net: add cgo implements for interfaceTable&interfaceAddrTable on openharmony system | 本次适配 | libc getifaddrs 获取接口和地址，释放链表并关闭 ioctl fd；修正 IPv4 16 字节表示。 | 三架构冒烟通过；三架构 net 完整包测试通过。 |


## 系统与 gomobile 补充审计（2026-10-23）

C20 在系统集成补丁上补齐 HiLog 的 debug/NOSPLIT 浅调用链、三架构原始系统调用
叶入口、关闭标准 fd 后的日志通道，以及显式空 TZ 的测试边界。C19 ARM64 全套
和 x64 语言失败记录保留，不能用 C18 通过报告代替新补丁。C20 ARM64 完整
450 pass/249 skip/0 fail；ARMv7/x64 在旧套件结束后重新验证。

#58 的 C19 三架构签名边界和原生九组合已通过；C20 必须独立重跑，目前 ARM64
边界和三个目标直接执行已通过，其余待补。HiShell 真机仍未验证。

新增 gomobile companion 提供三 ABI HAR/ArkTS/N-API、双向回调、Context 初始化
和九种工具包。真实 Ark 各 29 项、宿主 Node 27 项、HAP 编译通过，签名 HAP
因镜像缺少 code_sign/xpm 设备而安装失败。应用 UID、真实应用私有目录、生命周期
及纯 Go UI 后端不计通过。详见 [gomobile 验证](../mobile/docs/VALIDATION.zh-CN.md)。
