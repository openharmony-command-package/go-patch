# Sources and licenses / 来源与许可证

The pinned `golang.org/x/mobile` source and adaptation retain the Go Authors'
BSD 3-Clause license in [LICENSE](LICENSE) and [PATENTS](PATENTS). The linked
`golang.org/x/mod`, `golang.org/x/sync`, and `golang.org/x/tools` dependencies
use the same Go Authors' BSD license. Dependency revisions and checksums remain
in upstream `go.mod`/`go.sum`, fixed by the mobile commit in `manifest.json`.

`tests/ark/runtime.h` is an unmodified OpenHarmony Ability Runtime header,
Apache-2.0, copyright Huawei Device Co., Ltd. Its original copyright and license
notice are retained. The exact source commit is recorded alongside it in
`runtime-header-pin.json`. Only the test harness uses these inner runtime
interfaces; generated bindings use public N-API headers from the caller's SDK.

The independent ArkTS caller example, test fixtures, scripts, and adaptation
code are distributed under this directory's BSD license. The SDK, QEMU images,
Node, TypeScript, Hvigor, OHPM, and signing tools are external test inputs and
are not redistributed. Public SDK test credentials used locally are not stored
in this repository or its archives.

固定的 x/mobile 源码及适配保留 Go Authors 的 BSD 3-Clause 许可证和 PATENTS；
链接的 x/mod、x/sync、x/tools 同样采用该许可证。Ark 测试头文件保留原始
Apache-2.0 声明及精确来源记录。SDK、镜像、测试和签名工具不随工具包分发，
测试凭据不提交。
