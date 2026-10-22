# 全系统 QEMU 验证

ABI revision 2 正在重新验证；当前进度见 [VALIDATION.md](VALIDATION.md)。系统服务专项运行 `scripts/test-platform.py`，上一轮 C18 记录只作历史参考。

使用 manifest 固定的 OpenHarmony 镜像和完整系统 QEMU。标准库和工具链由 guest 原生编译测试；语言用例可由官方跨平台驱动编译，并在 guest 执行。标准 dist 自带 `-count=1`，每次完整运行都执行测试，不使用上次测试结果缓存。不是 Linux sysroot 加 user-mode QEMU。所有磁盘、端口、状态都属于本任务；不复用其他开发者正在运行的 QEMU。

依赖：`qemu-system-aarch64`、`qemu-system-arm`、`qemu-system-x86_64`、HDC、e2fsprogs（resize2fs/e2fsck）、足够存储空间。每架构 userdata 默认 24GB，测试 cache 可能超过 5GB；建议 `.work/qemu` 放在有余量的本地或外置盘。暂停实例后才能移动镜像，完成后用 `--reuse-images` 恢复。扩容前会离线重放 ext4 journal 并检查文件系统。

历史 C18 的 ARM64 r11、ARMv7 r5、amd64 r5 完整测试已通过，[历史总报告](test-results/history/c18/summary.json) 已生成。当时收集日志后关闭三个实例并保留镜像；当轮未追加 ARM 签名边界及剩余六个原生构建组合。以下命令用于独立复现，不表示这些补充组合本轮已完成。

## 启动

```sh
python3 scripts/qemu.py --arch arm64 --port 5569 --server 18769 --memory-mib 8192 \
  --packages /path/to/pinned-qemu-archives --hdc /path/to/hdc boot
```

armv7a 使用 5570，x86_64 使用 5571；可以共用本任务的 HDC server 18769。HDC 私有进程的 TMPDIR 隔离其 singleton lock。macOS arm64 上的 ARM64 默认使用 HVF，其余使用 TCG。

长时间无图形输入时，固定镜像的电源服务会将整个 guest 深度休眠，即使 Go 进程仍在计算。测试实例启动后通过 begetctl 停止 powermgr，保持系统唤醒；只改变此私有 VM 的运行状态，不修改镜像内核或库。power.log/state.json 记录该设置。这里的 stock 指未修改的系统镜像，测试运行期间仍采用上述电源配置。

新实例提供私有 Unix QMP socket。必要时可用 `python3 scripts/qemu.py --arch x86_64 wake` 恢复已休眠的实例；命令也能查询已经运行的实例。旧实例未配置控制 socket 时无法使用该恢复路径。

当前固定 ARMv7 镜像在 Go 安装前会因 foundation 服务反复崩溃而主动触发 kernel panic。VNC scanout 仍不能消除此镜像问题。ARMv7 的 Go 验证使用显式的 POSIX 配置：

```sh
python3 scripts/qemu.py --arch armv7a --port 5570 --server 18769 \
  --profile posix --vnc-display 71 --packages /path/to/archives --hdc /path/to/hdc boot
```

该配置先在私有离线 system.img 中将 `/etc/init/foundation.cfg` 和 `/etc/init/graphic.cfg` 的 `critical[0]` 改为 0，再通过 begetctl 停止 foundation/render_service。两个图形服务反复崩溃会触发 init 的主动内核 panic，与 Go 无关。修改仅替换配置中的标志字节，保留 inode、权限和 SELinux xattrs，不修改系统库或 Go 测试。`profile.json` 记录配置文件修改前后的 SHA256，`state.json` 和 `profile.log` 记录运行配置。报告不能将此结果描述成 stock 桌面系统通过。ARM64/x86_64 默认 stock。

## 真实签名工具

测试使用官方 `binary-sign-tool`，不使用返回成功的替身。从固定 hapsigner checkout 和 OpenHarmony 源码的 third_party 目录构建，需要 CMake/Ninja、Perl/make。脚本生成 OpenSSL 头文件和 CMake 项目到独立 work 目录，不修改输入源码。

先从同一架构 guest 提取 libcrypto（ARMv7 路径为 `/system/lib/platformsdk/`，其他为 `/system/lib64/platformsdk/`）：

```sh
python3 scripts/qemu.py --arch arm64 recv \
  /system/lib64/platformsdk/libcrypto_openssl.z.so /path/to/libcrypto-arm64.so
python3 scripts/build-signer.py --arch arm64 --sdk "$OHOS_NDK_HOME" \
  --hapsigner /path/to/developtools_hapsigner --third-party /path/to/openharmony/third_party \
  --libcrypto /path/to/libcrypto-arm64.so --work .work/signer-arm64
```

ARMv7 构建还会将 `patch/hapsigner-arm32.patch` 应用到私有源文件副本：上游 `2L*1024L*1024L*1024L` 在 32 位 long 上溢出，导致有效缓冲区被拒绝。修复改用 64 位常量；不改签名格式。源码来源和固定提交见 manifest/THIRD-PARTY-NOTICES。动态 libcrypto 必须与 guest 匹配；签名工具 ELF 使用对应系统目录的 rpath。

## 部署并运行完整测试

需要匹配架构的 OHOS 原生 Zig prefix，含 `zig` 和 `lib/`（本地验证版本 0.17.0）。`tests/native-cc` 用 Zig 的原生 Clang 前端与 LLD，结合未修改的 SDK 头文件/CRT/库。原因是高层 `zig cc` 强制 PIE，不能代表 Go 显式 exe 的链接需求。此驱动只用于测试，不是发布版 Go 的隐式依赖。

```sh
python3 scripts/test-qemu.py --arch arm64 --run-id arm64-cgo1-r1 provision \
  --sdk "$OHOS_NDK_HOME" --zig /path/to/native-ohos-zig-prefix \
  --signer .work/signer-arm64/build/binary-sign-tool
python3 scripts/test-qemu.py --arch arm64 --run-id arm64-cgo1-r1 start
python3 scripts/test-qemu.py --arch arm64 --run-id arm64-cgo1-r1 status
python3 scripts/test-qemu.py --arch arm64 --run-id arm64-cgo1-r1 collect
```

`start` 通过原生 launcher 脱离 HDC shell，立即返回 PID。`run-native.sh` 使用 `go tool dist test -no-rebuild -k -json`，设置非空 builder 名称，避免 c-shared/c-archive 因本地 short 模式整包跳过；遵守官方套件中对不支持特性的判定。全套默认 cgo=1，额外验证 cgo=0 用 `start --cgo 0` 和不同 run-id。

部署阶段先用真实签名工具签名工具链的 Go、编译器、链接器和 SDK 包装程序。安装脚本仅依赖 OHOS 自带 shell、od、chmod，无需 tr。启动记录同时保存实际 guest 中 Go 构建元数据、归档、原生 C 驱动、Zig、签名工具和 launcher 的 SHA256，避免将不同轮次的测试混为同一版本。

启动前默认要求 `/data` 至少有 8 GiB 空间，可用 `start --min-free-gib N` 明确调整。跨多轮源码修改会使专用构建缓存持续增长。先 collect 保存已完成的结果，并确认原生/语言任务均已结束，再清理本任务的缓存：

```sh
python3 scripts/qemu.py --arch arm64 shell \
  'test ! -d /data/local/tmp/go-patch/test-running && test ! -d /data/local/tmp/go-patch/language-running && GOCACHE=/data/local/tmp/go-patch/go-cache GOTOOLCHAIN=local GOENV=off /data/local/tmp/go-patch/go/bin/go clean -cache'
```

不要在活动套件中删除缓存。空间不足的失败轮次保留为失败，以新 run-id 重新执行完整套件。

结果在 guest 的 `/data/local/tmp/go-patch/results/` 和宿主 `.work/logs/qemu/ARCH/RUN_ID/`。包含完整 JSON、go env、退出状态、失败列表和日志 SHA256。`collect` 只有退出码为 0 且没有 fail/build-fail 才返回成功。重试使用新 run-id，不覆盖旧失败记录。请先完成 collect，再停止或替换实例。

```sh
python3 scripts/qemu.py --arch arm64 stop
# 使用已有的本任务磁盘再次启动：在原 boot 参数中加 --reuse-images。
```

这套 QEMU 验证覆盖语言/工具链/POSIX 接口，不能代替 HiShell 真机和应用沙箱的部署测试。

## Go 语言测试覆盖

产物必须包含官方 `test/`；仅依赖标准发行包缺省目录会使 cmd/internal/testdir 静默跳过，这不计为本项目的完整验收。

ARM64 使用默认 `--scope full` 原生 dist。TCG 架构使用原生 `--scope stdlib-tools`（明确只排除 cmd/internal/testdir），语言用例采用 Go 官方为跨平台测试提供的 runOnHost / `-target` 驱动：

```sh
python3 scripts/test-language.py --arch armv7a --sdk "$OHOS_NDK_HOME" --run-id full-r1
python3 scripts/test-language.py --arch x86_64 --sdk "$OHOS_NDK_HOME" --run-id full-r1
```

驱动运行在宿主，执行文件逐个传输到对应完整系统 QEMU，调用真实签名工具并运行，保留目标退出码与二进制输出。此处签名是测试的显式部署步骤，Go 在其他宿主交叉构建时仍不自动签名。独立 language-goroot 保存完整 test 数据，避免改变正在运行的原生标准库测试源码。每次目标执行写入审计日志；任何传输/签名故障均使总验收失败，即使用例本身预期程序失败也不掩盖基础设施错误。

会自行调用编译器/链接器的语言程序使用 guest 的原生 Go。驱动预先部署匹配目标的标准库导入归档，重写 importcfg 中的宿主缓存路径，并传入 STDLIB_IMPORTCFG 和原生 CC/CXX/AR；归档 SHA256 进入验收报告。这样验证编译器诊断和链接行为时仍在目标系统执行。

完整语言验收禁止 `--run` 过滤，要求注册数量与固定官方源码的全部语言用例完全一致（本版本 2733 个），且实际在 QEMU 执行目标程序。原始事件、执行审计、失败列表和 SHA256 保存在 `.work/logs/language/`。两个阶段必须全部成功；只通过其中一个不计完整通过。测试期间补丁、驱动源码或执行包装程序变化会导致验收失败。

TCG 压力用例保留全部工作量。单次目标执行默认允许 7200 秒（可用 `--exec-timeout` 调整），官方 recipe 超时倍率为 20；语言驱动总时限默认 4 小时。目标进程使用独立 session，超时/中断时先核对私有执行路径，再终止对应进程组。真实超时进程的清理已做反向验证，不将运行器超时计为测试通过。

三架构全部完成并 collect 后，用以下命令检查源代码版本、完整覆盖、运行状态和原始日志校验值。脚本只在全部满足时生成总验收报告：

```sh
python3 scripts/verify-validation.py \
  --arm64 .work/logs/qemu/arm64/arm64-cgo1-r11/summary.json \
  --arm .work/logs/qemu/armv7a/arm-cgo1-r5/summary.json \
  --amd64 .work/logs/qemu/x86_64/amd64-cgo1-r5/summary.json \
  --arm-language .work/logs/language/armv7a/full-c18/summary.json \
  --amd64-language .work/logs/language/x86_64/full-c18/summary.json
```

更换 Go 归档但保留相同测试依赖时可用 `test-qemu.py --arch ARCH update-go`；它重新安装并签名 Go，保留 SDK、原生 C 驱动和 Zig。provision/update-go 均拒绝替换正在运行的原生或语言测试源码。

## 原生工具链的三目标构建

三架构实例均已启动且完成部署后，可以检查每种原生 Go 对三种 OHOS 目标的纯 Go 构建，共九个组合：

```sh
python3 scripts/test-native-targets.py
# 可分批执行，最后一批会合并相同补丁的全部九项结果：
python3 scripts/test-native-targets.py --hosts arm64
python3 scripts/test-native-targets.py --hosts arm,amd64
```

该脚本使用独立构建缓存，核对 guest Go 的版本、架构和补丁 SHA256，验证输出 ELF 架构，再送到对应实例执行。部署过程不再次签名，用于检验原生 Go 构建时的自动签名，包括跨架构 OHOS 输出。建议在完整原生套件结束后运行 TCG 宿主构建，避免争用测试资源。日志保存在 `.work/logs/native-targets/`，九个组合全通过后保存 `docs/test-results/native-targets.json`。

## 原生自签名边界

完整套件结束后，运行以下验证。它会依次检查三种原生 Go：缺少签名工具时仍能构建 Linux 目标，构建 OHOS 目标时明确失败，恢复签名工具后生成的 OHOS 程序可直接执行。

```sh
python3 scripts/test-signing-boundary.py
# 可分批运行；最后一批合并同一补丁、同一测试脚本的三份报告：
python3 scripts/test-signing-boundary.py --hosts arm64,amd64
python3 scripts/test-signing-boundary.py --hosts arm
```

每次尝试使用独立日志，失败输出也会保留；原生或语言套件仍在运行时拒绝启动。使用独立构建缓存和 GOMAXPROCS=2。全部通过后生成 `docs/test-results/signing-boundary.json`，发布验收还会核对实际受测 Go 二进制的 SHA256。

## TCG 资源配置

原生运行脚本默认 GOMAXPROCS=2、GOFLAGS=-p=1；ARMv7/x86_64 的 GO_TEST_TIMEOUT_SCALE=20，ARM64 为 5。保持官方 short 模式及全部注册用例，未减少压力测试工作量。补丁为 dist 增加 -maxbg，0 保持官方默认调度，正数限制同时运行的测试命令。QEMU 脚本使用 GO_TEST_DIST_MAXBG=1，避免多个 SIMD/runtime 大内存变体并发；单个命令内的并行测试继续运行。

HDC 继承的 oom_score_adj=-1000 会让测试进程免于 OOM 回收，原生脚本将自身及后代恢复为 0，并记录实际值。启动 x86_64 建议增加 --memory-mib 8192；默认 4096。ARMv7 固定内核只可利用约 3 GiB，增加 QEMU RAM 无法替代限制并发。所有这些运行条件均须随测试证据保留。

原生构建默认 `GOFLAGS=-p=1`，串行安排包的构建与测试；单个包内部的并发用例保持启用，注册清单和测试工作量均不变。可用 `GO_OHOS_BUILD_PARALLELISM` 明确调整。ARM64/x86_64 完整套件建议至少 8 GiB QEMU 内存，ARMv7 固定内核可用约 3 GiB，尤需控制构建并发。早期完整运行使用的原始 run-native.sh 按 SHA256 保存在 docs/test-inputs/，可对应报告中的启动脚本校验值。


## 本轮系统/应用验证边界

C20 ARM64 完整套件及三架构 SDK 共享库/静态库冒烟已经通过；ARM/x64 的旧
原生和语言套件结束后收集真实结果，再部署修正版复验。不要覆盖运行中的 Go、
SDK、语言驱动或日志目录。每轮使用独立 run-id；原始日志与输入校验和保留，
最终关闭本任务 QEMU，其他任务的端口、HDC server 和实例不操作。

配套 gomobile 的三架构各 29 项在真实 Ark 环境中执行，独立 harness 仅为测试
配置运行时；这些是 shell 沙箱验证。当前镜像缺少 `/dev/code_sign`、`/dev/xpm`，
正常签名 HAP 安装返回 9568404。不能把 standalone Ark 或构建成功描述成已安装
应用通过；不得通过修改信任根或关闭签名校验来替代缺失的系统能力。
