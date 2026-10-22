# 仓库维护

[English](CONTRIBUTING.md) | 简体中文

应用用法见 [README](README.zh-CN.md)，工具链构建、补丁导出与归档校验见独立的 [构建说明](docs/BUILD.zh-CN.md)。

## 目录

| 路径 | 内容 |
|---|---|
| `manifest.json` | Go、SDK、参考源码、QEMU 及测试依赖的固定版本 |
| `patch/` | 可复用 Go/OHOS 补丁、签名工具补丁及 SHA256 |
| `scripts/` | 源码准备、构建、签名、QEMU 与验收脚本 |
| `tests/` | 目标构建、共享库、回调及原生自签名验证程序 |
| `docs/` | 中英文构建说明、issue 审计及完整与历史验证摘要 |
| `.work/`、`dist/`、`artifacts/` | 本地生成数据，被 Git 忽略 |

原始 QEMU 日志较大，保存在产出报告的本地工作目录。仓库中的报告记录了日志 SHA256、输入及运行条件；新克隆仓库需复现测试取得原始日志，不能仅凭摘要重新执行原始日志校验。

## 修改补丁

1. 使用 `python3 scripts/manage.py prepare` 获取固定源码。
2. 在 `.work/upstream/go` 修改源码，同步 `patch/source-paths.txt`。
3. 按 [refresh 流程](docs/BUILD.zh-CN.md#6-维护或刷新补丁) 导出补丁及 SHA256。若基线或依赖改变，同步 manifest。
4. 重新构建并验证。测试报告必须匹配当前补丁 SHA256；旧补丁的结果只作历史证据。

源码归档初始化的 Git 仓库需要显式指定其干净基线提交。不要将上游 checkout、生成文件、签名密钥或设备镜像加入 Git。

## 保留验证依据

完整测试包括三架构原生标准库/工具链与全部官方语言用例。ARMv7 使用文档记录的 POSIX 镜像配置；Windows 当前只有构建和静态格式证据。

`verify-release.py --require-validation` 要求完整 QEMU、自签名边界和原生九组合均通过。`--require-tested-toolchains` 核对受测二进制与归档内容，不替代尚未完成的补充验证，也不会将候选包提升为最终发布。

归档内携带当次构建的 `ohos-port/` 文档和脚本快照。修改其中的文件后，应重包并校验，使新文档对应新的归档校验和；重包须保留受测工具的二进制内容。

## 生成文件

不要提交 `artifacts/`、`dist/` 或 `.work/`。压缩包、校验和、清单、缓存和原始日志保留本地；二进制发布是独立操作。生成元数据时保留候选/最终发布状态，校验和以实际通过验证的压缩包为准。

同步维护 README、构建说明及维护说明的中英文版本。调整归档中的根文档清单时，需同时修改打包和归档校验脚本。
