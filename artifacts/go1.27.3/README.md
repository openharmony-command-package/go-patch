# go1.27.3 本地产物元数据

此目录记录 2026-10-22 生成的九份本地压缩包，不包含压缩包本身：

- Linux：arm64、amd64，`.tar.gz`。
- macOS：arm64、amd64，`.tar.gz`。
- Windows：arm64、amd64，`.zip`。
- OHOS：arm64、ARMv7（arm）、amd64，`.tar.gz`。

[SHA256SUMS](SHA256SUMS) 用于校验压缩包；[release-manifest.json](release-manifest.json) 记录大小、目标架构、补丁 SHA256 及 Go 二进制指纹。本地文件位于仓库根目录 `dist/`，未上传到 Git 或 GitHub Release。

状态为 **candidate**。三架构完整 QEMU 测试已通过，重包后的 72 个原生工具/包装文件及四种实测宿主的 Go 二进制均与受测版本一致。ARM 自签名边界及另外六种原生交叉构建组合本轮未完成；Windows 仅静态核验，ARMv7 使用 POSIX 镜像配置。

完整报告见 [VALIDATION.md](../../docs/VALIDATION.md)。这些校验和对应当次构建快照；之后对仓库文档的整理不改变已有压缩包的身份。
