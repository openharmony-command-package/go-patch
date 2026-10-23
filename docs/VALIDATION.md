# Go OHOS 验证进度

本轮验证基线为 Go 1.27.3、ABI revision 2。修正版 C20 补丁 SHA256：
`cb9c9199b60e78fcb052526b86dcb657c11b07e4dbd3d13b757ddfa583cb8d69`。
主工作树和本地产物已同步 C20；旧 C19 输入及二进制保存在本地历史目录，
对应报告仅作历史，不计入当前验收。

| C20 项目 | ARM64 | ARMv7 | x64 |
|---|---|---|---|
| SDK 纯 Go/cgo/c-shared/c-archive 构建运行 | 通过 | 通过 | 通过 |
| 系统集成 28 项 | 通过 | 待补验 | 通过 |
| 完整标准库、工具链、语言套件 | 通过 | 待旧套件结束后补验 | 已部署 C20，待完整补验 |
| 自签名边界 | 通过 | 待补验 | 通过 |
| 原生宿主构建三目标并直接执行 | 通过 | 待补验 | 待补验 |

ARM64 C20 完整套件为 **450 pass / 249 skip / 0 fail**，退出状态 0；官方语言
文件全部 2733 个注册，其中 2673 pass、60 skip。见
[C20 ARM64](test-results/arm64-cgo1-c20-r1.json)。运行时 HiLog 的 NOSPLIT
路径已改为独立浅调用链及三架构叶汇编入口；debug `-N -l` 和标准库中禁用内联
的构建不再超出系统栈限制。新增关闭 stdout/stderr、显式空 TZ、debug 构建三项
系统检查。系统接口说明见 [中英文集成文档](INTEGRATION.zh-CN.md)。

macOS arm64/amd64（含 Rosetta）已运行 C20 Go，构建三目标 pure/cgo/c-shared/
c-archive。Linux arm64/amd64（容器）已运行 C20 Go 并构建三目标纯 Go 程序。
Windows 两架构构建完成，仍只有静态格式证据；不计为 Windows 实际运行通过。
九种候选归档已在本地 dist 生成；重包必须保持 [72 项原生文件及四种宿主 Go
校验和](test-results/tested-toolchains.json) 不变。

C20 补丁已在全新官方归档基线上应用，全部 190 个适配源码逐文件一致，见
[补丁复现](test-results/source-reproduction.json)。本轮该检查没有额外运行
一次 make，不能将历史 C18 的 clean make 证据重标为 C20。

C19 ARM64 全套失败于 time.TestEnvTZUsage 和三个 debug 构建；x64 语言套件
2733 个完整执行，2682 pass、47 skip、4 fail，均为 HiLog NOSPLIT 构建限制。
失败轮次及原始输入不覆盖为通过，汇总位于
[history/c19-integration-1c](test-results/history/c19-integration-1c/)。ARMv7 语言套件已通过 2656 pass/77 skip；其旧原生套件仍在正常执行。
x64 旧原生套件已结束，为 437 pass/250 skip/4 fail；失败涉及旧版时区用例及
HiLog NOSPLIT 构建限制，报告已归档。x64 已部署 C20，28 项系统检查和签名边界
通过，完整套件尚待执行。不混用旧补丁结果。只有三架构 C20 全部通过，才能生成当前 accepted=true 的总报告。

所有完整套件使用官方 short 模式、CGO_ENABLED=1。ARM64 运行完整 native dist；
ARM/x64 的原生标准库/工具链及全部 2733 个官方语言用例分开执行，语言采用
官方 runOnHost/-target，产物仍在对应完整 OHOS QEMU 内签名执行，不使用
user-mode QEMU 代替系统。Cgo=0、netgo、PIE、debug 和日志/CA/时区/Context/
libc socket 路径另有专项覆盖，不能描述成 cgo=0 全套。

ARMv7 使用固定镜像的 POSIX 配置，停止故障图形服务并仅修改私有镜像的两个
critical 标志，保留 inode、权限和 SELinux 属性，不修改系统库。ARM64/x64
使用 stock 镜像；测试停止 powermgr，采用 GOMAXPROCS=2、GOFLAGS=-p=1、
dist -maxbg=1，包内并发用例保留。具体输入、页大小、内存和超时倍率随每轮报告
保存，详见 [QEMU](QEMU.md)。测试结束后收集日志并关闭本任务实例。

签名边界和原生九组合必须与 C20 完整套件的受测 Go 二进制一致。
`scripts/verify-release.py --require-validation` 门槛保持不变。当前为候选产物，
完整复测及原生矩阵尚未完成。HiShell 真机、应用 UID/私有目录、其他 API 版本、
真实 MTE/不同页大小内核仍未验证。

配套 gomobile 已完成三架构真实 Ark 各 29 项和宿主 Node 27 项，HAP 编译及库
一致性检查通过；镜像缺少 `/dev/code_sign`、`/dev/xpm`，签名 HAP 正常安装返回
9568404，应用执行不计通过。用户于 2026-10-23 确认先完成 HAR 绑定与三架构交付，
QEMU 内暂缓签名 HAP 验证，使用显式 `--validation-scope har` 验收绑定链路；
默认完整应用门槛不变，Go 原生自签名验证继续保留。见
[gomobile 验证矩阵](../mobile/docs/VALIDATION.zh-CN.md)。

C18 完整通过与当时关机记录保留为 [历史说明](test-results/history/c18/VALIDATION.md)，
不用于本轮补丁验收。
