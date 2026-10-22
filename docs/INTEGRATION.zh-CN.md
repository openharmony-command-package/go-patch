# OHOS 系统与应用集成

[English](INTEGRATION.md) | 简体中文

本文对应补丁 ABI revision 2，说明 Linux 系统调用之外的 OHOS 系统服务对接。
验证报告必须匹配实际补丁；上一版通过记录不能认证新二进制。

## 日志

Go 保留原 stdout/stderr，并将完整行额外写入 HiLog：`LOG_APP`、domain `0`、
tag `Go`。stdout 对应 INFO，stderr 和 runtime 诊断对应 ERROR。内置
`print/println`、panic、堆栈使用相同的 runtime 通道，支持 `CGO_ENABLED=0`。
尚未进入 Go runtime 的 runtime/cgo fatal 诊断另通过可选 Native HiLog API 输出。

Go 通道使用固定版本的 HilogMsg 数据报协议，不分配堆内存、不获取 Go 互斥锁，
使用有界缓冲区，不阻塞崩溃进程。服务缺失、拥塞或日志重入时可能丢弃额外副本；
stdout/stderr 与 `debug.SetCrashOutput` 仍可用。流式输出在换行或缓冲区满时发送。
原生 C stdio 不经过 Go 的 os.File 镜像；C/Native 代码应使用其 HiLog API。

启动时设置 `GO_OHOS_HILOG=0` 可关闭自动镜像。需要指定级别、domain 和 tag 时，
使用新增标准库包：

```go
import (
    "log"
    "log/hilog"
    "log/slog"
)

log.SetOutput(hilog.Writer{Domain: 0x1234, Tag: "MyApp", Level: hilog.Info})
logger := slog.New(hilog.NewHandler(0x1234, "MyApp", nil))
logger.With("component", "network").Warn("connection interrupted")
```

这些接口接收已经格式化的文本，文本及属性按公开内容输出，不解析 Native
`%{private}` 格式指示符。日志服务的过滤和配额仍然生效。查看命令为
`hdc shell hilog -x -T Go,MyApp`；`-t` 选择日志类型，`-T` 才是 tag。

## 根证书与时区

`crypto/x509` 增加搜索 `/etc/security/certificates` 和
`/system/etc/security/certificates`。`SSL_CERT_FILE`、`SSL_CERT_DIR` 保留标准覆盖
行为。应用可通过 `Config.TrustedCertDirs` 明确传入经过 Certificate Manager
确认的 CA 目录；不会递归导入其他用户证书，也不会用“设备上所有证书”替代应用信任策略。

显式 `TZ` 优先；未设置时，通过可选 runtime/cgo 系统参数桥查询
`persist.time.timezone`。没有 libc 的纯 Go shell 程序可回退到固定的 `/bin/param`
工具，输出和等待时间均有上限。服务或工具不可访问时，继续回退 `/etc/localtime`
和 UTC。原有 OHOS tzdata 解析器负责加载时区规则。

`time.Local` 与上游一样只初始化一次。应用传入时区时应在首次使用之前配置。
需要跟随系统实时切换时区的应用，应监听平台变更并显式加载、使用新的 `time.Location`。

## 应用 Context

由应用从自身 Context 获取目录，通过 Native/N-API 初始化函数传入 Go。
不猜测包名、存储级别或用户 ID，不拼接固定私有路径。启动业务 goroutine 前调用：

```go
import "os/openharmony"

err := openharmony.Configure(openharmony.Config{
    FilesDir: filesDir,
    CacheDir: cacheDir,
    TempDir: tempDir,
    Timezone: timezone,
})
```

三个目录均须已存在且使用绝对路径。配置会设置 `HOME`、`XDG_CONFIG_HOME`
（FilesDir 下的 `.config`）、`XDG_CACHE_HOME` 和 `TMPDIR`；不会创建目录或扩大权限。
链接 runtime/cgo 时，环境也同步到 C。shell 程序默认临时目录仍为 `/data/local/tmp`。
`os/user.Current` 可以表示 passwd 中不存在的应用 UID，UID/GID 保持真实进程身份。

## 网络

需要系统 DNS、网卡枚举、应用指定网络及 VPN 保护的应用，应使用 `CGO_ENABLED=1`。
DNS 默认经 libc，网卡经 getifaddrs；socket 创建也经 libc，让 OHOS socket hook
执行系统网络选择。cgo 开启时，`netgo` 只改变 DNS 选择，不关闭 socket/网卡桥接。

仍可使用 `CGO_ENABLED=0` 构建不依赖 SDK 的 Go 程序。其网络遵循 Linux syscall、
resolv.conf 和 netlink 约定，不会自动获得 OHOS 系统网络服务、权限或应用网络绑定。
应用可为自己的 DNS 通道配置显式 `net.Resolver`。编译成功不代表具备网络权限。

## ELF 与运行边界

exe、PIE、c-shared 和 c-archive 是不同模式。需要 PIE 可执行文件时，使用已配置 SDK
并指定 `-buildmode=pie`；HAP 的 Native 库使用 c-shared/PIC 和应用打包签名流程。
原生 Go ELF 自签名属于部署能力，不替代 HAP 授权。

ARM64 字符串/字节扫描已采用 MTE 安全的读取边界；代码修改不等于已经完成硬件 MTE
验收。固定 QEMU 内核使用 4 KiB 页；其他页大小和 SDK 需要独立核查 ELF 与 runtime。
不使用 Android 的 bionic TLS 槽位、JNI 启动或特定芯片规避代码，保留本补丁已有的
OHOS musl TLS 和信号链处理。

## 验证与设备

`scripts/test-platform.py` 为选定全系统 QEMU 构建 cgo=0/1、netgo 和 PIE 变体，
检查系统 CA、默认时区、Context、socket 入口、普通/panic/C-fatal HiLog、长记录和关闭
镜像。受控 socket interposition 验证调用经过 libc；实际 VPN、网络选择仍需相应应用
与设备场景。

`scripts/hdc-exec.py` 可对指定真实设备执行非交互式 `go test -exec`，使用唯一私有目录、
真实部署签名、独立 stdout/stderr 和设备退出状态。例如：

```sh
go test -exec "python3 /path/to/go/ohos-port/scripts/hdc-exec.py --target DEVICE_ID" ./...
```

按需设置 `GO_OHOS_HDC`、`GO_OHOS_HDC_SERVER` 或 `--signer`。运行器需要 shell 部署
权限和真实签名工具。设备 shell 测试不能替代 HAP 加载、Native/N-API 回调、Context
生命周期或沙箱权限测试；结果中必须记录真正执行的环境。
