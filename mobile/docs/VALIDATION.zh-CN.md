# 验证记录

[English](VALIDATION.md)

用户于 2026-10-23 确认本次交付范围为 **HAR 绑定与 OHOS 三架构**，QEMU 内先
跳过签名 HAP 验证，见 [范围记录](test-results/delivery-scope.json)。上级 Go 的
发行验收仍在运行，因此组合产物仍标为候选。gomobile 补丁 SHA256：
`5a8ce153a45eb0abf4a8e9bc553ab70908335e4dce4de98377903d904b988923`。
示例 HAR 使用 Go 1.27.3，Go 补丁 SHA256：
`cb9c9199b60e78fcb052526b86dcb657c11b07e4dbd3d13b757ddfa583cb8d69`。
Go 自身的完整套件、签名和原生构建门槛独立验收，gomobile 的通过不能替代。

| 检查 | 实际结果 |
|---|---|
| 全新固定上游源码应用补丁 | 全部适配文件一致 |
| 生成器与 OHOS 目标解析测试 | 通过 |
| 生成的 TypeScript | 严格类型检查通过 |
| Node 24.14.1 宿主 N-API | 27 项通过 |
| OHOS ARM64 Ark/N-API | 29 项通过 |
| OHOS ARMv7 Ark/N-API | 29 项通过 |
| OHOS x64 Ark/N-API | 29 项通过 |
| 工具命令实际执行 | macOS/Linux 各两架构、OHOS 三架构均通过 |
| Windows arm64/amd64 工具 | 完成构建与格式检查；未执行 |
| ArkTS 调用方 HAP | 编译通过，三架构库与受测 HAR 逐字节一致 |
| 签名 HAP 安装和应用 UID 执行 | 用户确认 QEMU 内暂缓；仍为未验 |

Ark 的 29 项由首个运行时的 27 项功能测试及第二个运行时的两项清理测试组成，
覆盖 UTF-8/NUL、字节、大整数边界、对象、error/panic、接口返回值、保留和并发
回调、回调再次调用 Go、外部命名类型、非有限浮点数、负零和环境关闭。Go 侧可读取
传入的 files/cache/temp 路径，且成功写入指定 files 目录。这里使用显式 shell
沙箱目录，不能据此声称已验证安装应用的私有目录权限。

测试在真实 OHOS Ark 环境中调用生成的 N-API 库。仅测试入口使用固定版本的
内部运行时初始化接口，生成的绑定使用公开 N-API。每份 [报告](test-results/)
绑定 HAR、动态库、Go/gomobile 补丁、测试输入及原始日志校验和。原始日志和
二进制仅保留在本地 `.work/`、`dist/`。

当前镜像缺少 `/dev/code_sign` 和 `/dev/xpm`，正常安装签名 HAP 在添加证书路径时
返回 9568404。用户确认本轮 QEMU 可跳过此项，仅在显式 HAR 验证范围中排除。
没有修改信任根、关闭签名验证或提升应用权限。签名 HAP 执行、
真实应用 UID/私有目录权限及生命周期仍需完整镜像或 HDC 真机补验，参见
[调用示例](../examples/arkts/README.zh-CN.md)。

对固定上游原版和补丁版运行了同一完整测试命令，两者有相同六项失败，涉及本机
Foundation 头文件/clang、Android aapt 测试夹具、Apple/模块夹具差异。
不宣称完整上游测试通过，详见 [源码测试记录](test-results/source-tests.json)。
Linux/Windows 使用对应 SDK 构建 HAR、HiShell 真机、其他 API 镜像及纯 Go
窗口/输入/OpenGL 应用后端尚未验证。

`python3 mobile/scripts/verify.py` 检查九种归档与示例 HAR。本次确认的范围使用：

```sh
python3 mobile/scripts/verify.py --require-validation --validation-scope har
```

该命令要求当前三架构 Ark、Node/严格 TypeScript、七种宿主命令运行证据，
以及调用方 HAP 编译和库逐字节比对；不声称签名应用已运行。默认的
`--require-validation` 仍要求签名 HAP 应用通过报告，证据缺失时继续拒绝。
Go 原生自签名验收仍保留。
