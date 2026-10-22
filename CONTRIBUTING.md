# Contributing

English | [简体中文](CONTRIBUTING.zh-CN.md)

Application usage is in [README](README.md). Toolchain build, patch export, and archive validation are in the separate [build guide](docs/BUILD.md).

## Repository layout

| Path | Contents |
|---|---|
| `manifest.json` | Pinned Go, SDK, reference sources, QEMU, and test dependencies |
| `patch/` | Reusable Go/OHOS and signer patches with SHA256 files |
| `scripts/` | Source preparation, build, signing, QEMU, and verification scripts |
| `tests/` | Target builds, shared libraries, callbacks, and native signing checks |
| `docs/` | Bilingual build guides, issue audit, and current/historical test summaries |
| `.work/`, `dist/`, `artifacts/` | Local generated data; ignored by Git |

Large raw QEMU logs remain in the local workspace that produced the reports. Committed reports record their SHA256 values, inputs, and conditions. A fresh clone must reproduce the tests to obtain raw logs; summaries alone cannot rerun the raw-log checks.

## Change the patch

1. Run `python3 scripts/manage.py prepare` to obtain the pinned source.
2. Edit `.work/upstream/go` and update `patch/source-paths.txt`.
3. Export the patch and SHA256 using the [refresh workflow](docs/BUILD.md#6-maintain-or-refresh-the-patch). Update the manifest if the baseline/dependencies change.
4. Rebuild and validate. Reports must match the current patch SHA256; previous patch results are historical evidence only.

A repository initialized from a source archive needs an explicit pristine baseline commit. Keep upstream checkouts, generated files, signing keys, and device images out of Git.

## Preserve validation provenance

Full testing includes the three native standard-library/toolchain suites and all official language cases. ARMv7 uses the documented POSIX image profile. Windows currently has build/static-format evidence only.

`verify-release.py --require-validation` requires complete QEMU, signing-boundary, and native nine-combination evidence. `--require-tested-toolchains` checks the tested binary identities as well as archive contents, but does not replace incomplete supplemental checks or promote a candidate archive.

Archives embed the build's `ohos-port/` document and script snapshot. After changing bundled files, repackage and verify to associate the new docs with new archive checksums. Packaging must preserve the tested tool bytes.

## Generated files

Do not commit `artifacts/`, `dist/`, or `.work/`. Store archives, checksums, manifests, caches, and raw logs locally. Binary release publication is a separate action. Preserve candidate/final status in generated metadata and derive checksums from the actual verified archives.

Keep the Chinese and English README/build/contribution guides aligned. Update both the packager and archive verifier when changing the list of bundled root documents.
