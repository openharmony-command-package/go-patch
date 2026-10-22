# 仓库维护

```sh
git clone git@github.com:openharmony-command-package/go-patch.git
cd go-patch
```

构建及部署入口见 [README](README.md)，完整系统测试步骤见 [QEMU 文档](docs/QEMU.md)。

## 目录

| 路径 | 内容 |
|---|---|
| `manifest.json` | Go、SDK、参考源码、QEMU 及测试依赖的固定版本 |
| `patch/` | 可重复应用的 Go/OHOS 补丁、签名工具补丁及 SHA256 |
| `scripts/` | 下载、应用补丁、构建、签名、QEMU 与验收脚本 |
| `tests/` | 三架构构建、动态库、回调及原生自签名验证程序 |
| `docs/` | 复现步骤、issue 审计及完整与历史验证摘要 |
| `artifacts/` | 已生成压缩包的校验元数据；不包含二进制压缩包 |
| `.work/` | 本地源码、缓存、QEMU 镜像及原始日志；不纳入 Git |
| `dist/` | 本地生成的工具链压缩包；不纳入 Git |

原始 QEMU 日志较大，保存在产出报告的本地工作目录。仓库中的报告记录了日志 SHA256、输入及运行条件；新克隆仓库不能仅凭摘要重新执行原始日志校验，需按文档复现测试。

## 修改补丁

1. 使用 `python3 scripts/manage.py prepare` 下载并校验固定源码。
2. 在 `.work/upstream/go` 修改源码，同步 `patch/source-paths.txt`。
3. 按 README 的 `refresh` 流程导出补丁及校验和。若基线或依赖改变，同步 manifest。
4. 重新构建并验证。测试报告必须匹配当前补丁 SHA256；不能沿用旧补丁的通过记录。

源码归档初始化的临时 Git 仓库需要显式指定其干净基线。不要将 `.work/` 中的上游 checkout、生成文件、签名密钥或设备镜像加入本仓库。

## 验证及产物

完整测试包括三架构原生标准库/工具链和全部官方语言用例。ARMv7 使用文档记录的 POSIX 镜像配置；Windows 当前只完成构建及静态格式检查。

`verify-release.py --require-validation` 是严格发布门槛，要求完整 QEMU、自签名边界和原生九种主机/目标组合均通过。`--require-tested-toolchains` 额外核对受测二进制一致性，但不替代上述补充验证，也不会将候选包提升为最终发布。

归档内包含当次构建的 `ohos-port/` 补丁、脚本和验证文档快照。修改这些文件后，需要重包并重新校验，才能将新文档与新压缩包对应。生成的二进制默认只存本地；发布 Release 或上传压缩包需要独立执行。

本次 go1.27.3 的九份本地归档元数据见 [artifacts/go1.27.3](artifacts/go1.27.3/README.md)。更新该目录时，应从实际通过校验的 `dist/` 复制清单与校验和，保留候选/最终发布状态，不手工修改已有压缩包的 SHA256。
