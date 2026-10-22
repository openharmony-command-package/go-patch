# ArkTS caller example

[中文](README.zh-CN.md)

This minimal Stage application calls the generated example HAR. Copy the HAR
to `gomobile-ohos-example.har` beside this file, install the `entry` OHPM
dependencies, and open the project in DevEco Studio with API 26 installed.
Set `local.properties` to your SDK root, or use `scripts/test-hap-build.py` from
the mobile directory to copy and build the example in an ignored workspace.

`EntryAbility` awaits `initialize(this.context)`, verifies that Go sees the
Context files/cache/temp directories, writes a private file through Go, calls
UTF-8 and object APIs, and tests an asynchronous callback that calls Go again.
It writes `gomobile-result.txt` into `this.context.filesDir` and a `GoMobileTest`
HiLog message. `GOMOBILE_OHOS_HAP_PASS` is the success marker.

Build and sign the final HAP using your normal application signing identity.
Install it on a system with the code-sign drivers and certificate services
required by that image. The current pinned QEMU lacks `/dev/code_sign`, so
HAP compilation is recorded separately from successful installation/execution.
No trust or signature checks are disabled by this example.
