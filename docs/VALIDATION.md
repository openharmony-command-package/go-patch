# 本地验证记录

基线：官方 go1.27.3；记录日期：2026-10-22。当前补丁 SHA256：`58bc568264a43a993ba6a9156a2916259fb599b91a0869f937a62702338a5bb3`。

**当前 C18 补丁的三架构完整 QEMU 测试已全部通过，总报告已生成；本轮归档仍为候选包，补充签名边界及原生九组合未全部完成。** C17 的 ARMv7/x86_64 完整测试暴露了并发 vfork 对父进程 OHOS 信号链的破坏：全局 `inForkedChild` 被另一个子进程清零后，尚在清理信号的子进程会调用 libc sigaction，改写共享内存中的 sigchain。C18 将状态移到对应 M，避免相互覆盖，并添加 16 个并发执行者、1024 次 exec 及逐次故障恢复的原生回归。下表为当前 C18 进度；C17 的结果单独保留在历史记录中，不计作 C18 验收。原始日志保存在 `.work/logs/`；最终报告只接受与当前补丁匹配的完整运行。

| 当前 C18 检查 | arm64 | arm（ARMv7） | amd64 |
|---|---|---|---|
| SDK 纯 Go/cgo/exe/c-shared/c-archive 构建 | 通过 | 通过 | 通过 |
| OHOS QEMU 冒烟、dlopen、C 线程回调、GC、动态环境 | 通过 | 通过 | 通过 |
| 原生标准库及工具链 dist | r11 通过：450 pass/245 skip/0 fail | r5 通过：439 pass/243 skip/0 fail | r5 通过：441 pass/246 skip/0 fail |
| 官方全部 Go/test 语言用例 | r11：2733，2673 pass/60 skip | 2733，2656 pass/77 skip | 2733，2686 pass/47 skip |
| 原生自签名边界 | 通过 | 本轮未完成 | 通过 |
| 原生 Go 构建并运行三种目标 | 3/3 通过 | 本轮未完成 | 本轮未完成 |

C18 ARMv7/x86_64 的语言测试已完整通过，均实际注册 2733 个用例，分别完成 1240/1250 次目标执行，无过滤、失败或基础设施错误。报告：[ARMv7](test-results/language-arm-full-c18.json)、[x86_64](test-results/language-amd64-full-c18.json)。

C18 ARM64 r9 的 runtime 包通过（83.799 秒），新增并发 exec 回归通过（1.21 秒），语言 2733 个用例完整通过。其后 shared/plugin/工具链构建耗尽磁盘，整轮失败，报告保留于 `.work/logs/qemu/arm64/arm64-cgo1-r9/`。专用 Go 缓存累积约 19 GiB，待该轮结束并收集日志后清理，恢复约 20 GiB 空间，再以 r10 重跑 full。r10 的 SSA 编译进程与语言 rangegen 编译进程被杀死，整轮失败；当时磁盘仍有约 16 GiB 空间，内核日志尚未确认 OOM。已保留 r10 全部日志，ARM64 r11 将 QEMU 内存从 4 GiB 增至 8 GiB，并采用 GOFLAGS=-p=1 控制构建并发，保持全量用例与原有工作量。r11 已完整通过，退出状态 0：450 个包通过、245 个跳过、无失败，语言用例 2733 个（2673 pass/60 skip），见 [r11 报告](test-results/arm64-cgo1-r11.json)。启动脚本现有默认 8 GiB 可用空间检查。

信号修复的独立前后对照见 [vfork-signal-regression.json](test-results/vfork-signal-regression.json)：C17 在并发 exec 后父进程 SIGSEGV 处理器变为 0，退出状态 2；C18 对同一回归完成 1024 次 exec 与故障恢复，输出 OK、退出状态 0。未修改 C17 原生 runtime 二进制的 ptrace 重复运行也捕获了第三遍 TestSetPanicOnFault 从正常故障地址转而跳到处理器地址 0 的过程，见 [信号诊断](test-results/runtime-signal-diagnostics.json)。独立对照不替代完整套件。

amd64 r5 已通过原生标准库及工具链（441 pass/246 skip/0 fail，退出状态 0），与同补丁的全部语言用例共同构成完整覆盖，见 [amd64 r5 报告](test-results/amd64-cgo1-r5.json)。日志已收集，QEMU 于 2026-10-22 02:08（Asia/Shanghai）关闭；ARM64 也已按要求关闭。ARMv7 r5 随后以 439 pass/243 skip/0 fail 通过，退出状态 0，见 [ARMv7 r5 报告](test-results/arm-cgo1-r5.json)，QEMU 于 2026-10-22 03:15（Asia/Shanghai）关闭。全部本任务实例均已关闭，镜像保留，见 [关机记录](test-results/qemu-shutdown.json)。

当前三架构 SDK/QEMU 冒烟已通过。ARM64/amd64 自签名边界和 ARM64 宿主的三种目标构建已通过，按用户要求，当前套件结束即关机，不再追加验证；ARM 自签名边界和其余六种原生构建组合本轮未完成；对应报告只有补丁 SHA256 与页首一致时才是当前证据。[summary.json](test-results/summary.json) 已由 verify-validation.py 校验当前补丁、三架构完整覆盖、原始日志与实际目标执行审计后生成，accepted=true。该报告表示完整测试通过；严格发布仍要求签名边界和原生九组合也全部通过。

## 覆盖与运行条件

ARMv7/x86_64 原生执行 `go tool dist test -no-rebuild -k -json`，仅明确排除 `cmd/internal/testdir`。语言部分采用官方 runOnHost / `-target` 驱动，在宿主编译、对应完整 OHOS QEMU 中签名并执行；全部 2733 个语言文件均注册，禁止过滤。原生及语言两个阶段必须同时通过，并匹配同一补丁 SHA256。未使用 Linux sysroot 加 user-mode QEMU 代替 OHOS。

ARMv7 固定镜像在运行 Go 之前，会因图形服务反复崩溃触发 kernel panic。使用 [QEMU 文档](QEMU.md) 中的 POSIX 配置，只修改私有镜像中两个图形服务的 critical 标志，保留 inode、权限及 SELinux 属性，不修改系统库。该结果不能描述为 stock 桌面系统通过。ARM64/x86_64 使用 stock 镜像。测试实例停止 powermgr，避免无图形输入时自动深度休眠；该运行配置单独记录。

套件采用官方默认 short 设置和 `CGO_ENABLED=1`。Cgo=0 另有三架构构建/运行冒烟及跨 OS 签名边界验证，不将它们称作 cgo=0 全套。OHOS 未提供 pthread_cancel，对应专属用例明确 skip；race、MSan、ASan、TSan 及内部 cgo 链接按平台能力判定。TestSetgidStress 保持启用。

原生运行采用 `GOMAXPROCS=2`，TCG 超时倍率 20、ARM64 为 5。`dist -maxbg=1` 串行调度测试命令，单个命令内仍可并行；与默认调度的注册清单一致，未删减测试工作量。ARM64 r11 另设置 GOFLAGS=-p=1，串行安排包的构建与测试，包内并发用例保持启用；ARM/amd64 r5 使用的原始脚本按 SHA256 保存在 docs/test-inputs/。ARM64 r11 与 x86_64 QEMU 均为 8192 MiB；ARMv7 固定内核可利用约 3 GiB，使用 4096 MiB QEMU。HDC 后代恢复 `oom_score_adj=0`，避免继承 init 的 OOM 保护而导致系统服务被杀、内核崩溃。实际条件记录在每轮 environment.txt 和 QEMU state 中。

C 回溯 helper 在 Go 启动前清除 OHOS 预装 DFX 的 SIGSEGV 用户处理器，以验证 Go 自身回溯；专用 C 信号转发用例保留。生产 Go 继续转发已有 C 处理器。测试 C 驱动使用 4KB 链接页大小，匹配固定 SDK 并验证性能采样符号解析。

## 宿主、归档及源码复现

C18 九种工具链已生成：Linux/macOS/Windows 各 amd64、arm64，OHOS 原生 arm64、arm、amd64。本轮统一重包并使用 `scripts/verify-release.py --require-tested-toolchains`，核对完整 QEMU 证据、版本、补丁、源码、完整官方 test 目录、独立补丁/脚本包及 ELF/PE/Mach-O 架构。原生测试所用归档中 72 个工具/包装程序文件的 SHA256 已留存，重包必须与其一致。当前 [归档状态](test-results/packaging-status.json) 明确为 candidate；签名边界/原生九组合的当前聚合报告 accepted=false，旧 C17 聚合记录移至 test-results/history/c17/，不用于本轮验收。`--require-validation` 的严格门槛保持不变。

macOS arm64 和 amd64（Rosetta）均实际运行当前工具链，使用归档中的 SDK 包装程序完成三种目标的纯 Go、cgo、c-shared、c-archive 构建。Linux arm64/amd64（Docker）均实际运行当前工具链并构建三种 OHOS 纯 Go 目标。C18 报告：[macOS arm64](test-results/host-darwin-arm64.json)、[macOS amd64](test-results/host-darwin-amd64.json)、[Linux arm64](test-results/host-linux-arm64.json)、[Linux amd64](test-results/host-linux-amd64.json)。最终归档须匹配这四份报告的 Go 二进制 SHA256。

Windows 两架构完成构建；最终归档执行静态检查。本机 Wine 受 Rosetta invalid gdt selector index 5 限制，未计为 Windows 运行通过。HiShell 真机、应用沙箱和其他系统镜像版本尚未验证。

C18 补丁在全新官方源码上独立应用并完成 make.bash；工作树与该副本的 src/、test/ 共 15588 个文件逐文件一致，见[源码复现核验](test-results/source-reproduction.json)。

与参考 issue 对应的 archive/tar、encoding/pem、encoding/asn1、crypto/x509、net/http、net/textproto、net/url、net/mail、crypto/tls、database/sql 在宿主 short 测试下全部通过。最初非 short 测试访问公网代理和远端 TLS 服务失败，其记录保留，不计为通过。

## 已复现并修复的问题

以下 C17 定向诊断均保留原始日志；当前补丁的完整验收仍以上表为准，摘要见 [c17-diagnostics.json](test-results/c17-diagnostics.json)。

- ARMv7 TLS GD 的 SP 写回添加与现有 ARM 运行时一致的 NOP R13 标记，修复汇编 vet 对栈访问的误判；此前定向 `go vet runtime` 通过。
- ARMv7 通过 libc sigaction 接入 OHOS 信号链，明确 Go/C sigaction 布局，并在信号入口保存 C 的 R11 帧指针。六组原生定向回归全部通过，包括 C 信号转发、panic 回调和 Go 回溯，共 723.961 秒。
- amd64 共享库从 `R_X86_64_RELATIVE` 恢复 GCData 附加值；TestTestInstalledShared、TestGCData 及 `clobberfree=1` 的实际 GC 程序均通过。
- time 的压力用例遵守 GO_TEST_TIMEOUT_SCALE，保留 50000×20 个队列工作项。原工作量以 169.23 秒完成，倍率 5 下整个 time 包通过。
- cmd/go 的 TestLinkSysoFiles 保留 cgo=0/1 基础检查，仅按正式平台能力决定 MSan 分支；amd64 原生回归通过。
- DWARF 5 先收集编译单元基址，再解析 addrx/strx/rnglistx。ARMv7 对同一真实大二进制，旧读取器在 0x5b7e7a 失败，新读取器遍历全部 391334 个条目；宿主和 ARMv7 debug/dwarf 全包通过。新增公开 API 回归在修复前失败；原 SSA 语句行测试保持启用。

## 历史记录

C17（`df5494a401403fa9464d8d3e5f9f2d9a56f5eb21b7f0cbea4b7d3aef43f5a2bc`）ARM64 r8 完整通过；ARMv7/x86_64 r4 仅 runtime 失败，由上述并发 vfork 信号链问题导致。C17 记录与当前 C18 不混用。

历史 C15 补丁为 `c15f9e9c88326816f9f37aec711426afbaa80f474cfddb058b1660e3169ed94a`。其 ARM64 r7 完整通过，ARMv7/x86_64 的 full-r6 语言阶段也分别通过全部 2733 个用例，但不能将这些结果重标为当前补丁通过。

| 轮次 | 结果及处理 |
|---|---|
| ARM64 r1–r4 | 定位接口、平台条件、临时目录、C 回溯和采样问题；失败日志保留。 |
| ARM64 r5 | 450/245/0，但缺少官方 test/，不算完整验收。 |
| ARM64 r6 | 实跑 2733 个语言用例，发现直接链接 CC 和假工具链版本污染问题。 |
| ARM64 r7（C15） | 450/245/0，2733 个语言用例完整覆盖；为历史完整通过记录。 |
| ARMv7 初轮 | 修正 Zig ARMv7 CPU 参数及签名工具的 32 位 long 溢出，失败轮次不计通过。 |
| ARMv7 r3（C15） | runtime 汇编 vet、SSA DWARF 失败，testshared 累计触及 50 分钟包级时限。已中断、保存日志并修复；未计通过。 |
| x86_64 r2（C15） | 系统深度休眠，离线提取日志后重新配置电源策略；未计通过。 |
| x86_64 r3（C15） | time、GCData、MSan 条件失败，后续大内存变体并发触发 OOM panic。原始 JSON、输入和串口已离线保存；未计通过。 |
| 语言 full-r6（C15） | ARMv7：2656 pass/77 skip、1240 次目标执行；amd64：2686 pass/47 skip、1250 次目标执行。当前版本重新全量执行。 |

所有重试使用独立 run-id，保留失败、超时和中断证据，不覆盖为成功记录。
