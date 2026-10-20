# Native Cloudflare Wrangler builds for Termux aarch64

[![Weekly Termux aarch64 Wrangler build](https://github.com/troublescope/Termux-pkg/actions/workflows/daily-build.yml/badge.svg)](https://github.com/troublescope/Termux-pkg/actions/workflows/daily-build.yml)
[![Validate repository](https://github.com/troublescope/Termux-pkg/actions/workflows/validate.yml/badge.svg)](https://github.com/troublescope/Termux-pkg/actions/workflows/validate.yml)

This repository builds native Android/Termux packages for Cloudflare **`wrangler`** on **64-bit ARM (`aarch64`)** and publishes them in uniquely tagged GitHub Releases.

It produces:

- A native Cloudflare `wrangler` Termux `.deb`, with Wrangler built from its matching `workers-sdk` tag plus matching Android/Bionic `workerd` and `esbuild` binaries compiled from source.
- `SHA256SUMS`, JSON, and TSV release indexes containing immutable asset URLs.

## Signed APT repository (`pkg install`)

The project also publishes the tested `.deb` outputs through a signed third-party Termux APT repository. The repository is served from the Oracle VM repository server, while the repository signing key is kept only on that server. The server polls immutable public GitHub Releases, verifies GitHub-published SHA-256 digests and package metadata, and then signs/publishes locally; no server deployment private key is stored in GitHub Actions.

Enable it once from native Termux:

```bash
curl -fsSL --retry 5 --retry-all-errors https://raw.githubusercontent.com/troublescope/Termux-pkg/main/scripts/setup_apt_repo.sh | bash
```

The bootstrap verifies the repository key fingerprint before adding the source:

```text
2E44CCEEA39C350159D5A77F8C9A482AAD291541
```

After that, install `wrangler` like a normal Termux package:

```bash
pkg install wrangler
```

Repository endpoint:

```text
http://144.21.61.111/termux
```

## Direct installation

To install directly using the checksum-verifying installer:

```bash
curl -fsSL https://raw.githubusercontent.com/troublescope/Termux-pkg/main/install.sh | bash
```

The Wrangler package includes the exact `workerd` and `esbuild` versions selected by that Wrangler release, compiled from source for native Android `aarch64`. It has no foreign dependencies and runs inside Termux without emulation, proot, or glibc wrappers.

## How the native Wrangler build works

1. The Wrangler job resolves the newest stable `wrangler` release from npm and checks out its exact `workers-sdk` tag.
2. The matching `esbuild` version is compiled from source for Android `aarch64` (to ship in the package). For the Linux-side Wrangler source build, CI discovers every esbuild API version in Wrangler's filtered dependency graph and compiles each exact version from its upstream source tag before running the workspace build, avoiding prebuilt host esbuild binaries and cross-version protocol mismatches.
3. The matching `workerd` source is cross-compiled with the Android NDK and Bazel for `aarch64-linux-android`, including Bionic compatibility patches for upstream assumptions that currently treat Android as ordinary glibc Linux. Linux host/exec C++ actions use the same LLVM 19 baseline as workerd upstream CI and explicitly link `libatomic` for V8 generator executables when LLVM emits out-of-line atomic helpers, while Android target C/C++ remains on the NDK API-24 toolchain. Workerd's Rust `gen-compile-cache` helper is linked through that Android C++ toolchain so the NDK compiler-rt builtins (including the AArch64 instruction-cache helper used by V8) are present even though rules_rust's ordinary final-link path suppresses default runtime libraries. Build-time Android target executables that must run during the cross-build are executed under an aarch64 Termux/QEMU container instead of being silently rebuilt against glibc.
4. CI installs the finished Wrangler `.deb` into an emulated aarch64 Termux environment, runs a Wrangler dry-run plus the distinct `cf-wrangler build` delegate to exercise the Android packaging paths, launches `wrangler dev`, and fetches a real local Worker response through Android workerd.
5. Successful outputs are indexed with SHA-256 hashes and published in the immutable release.

## Repository layout

```text
.github/workflows/daily-build.yml   Wrangler build and release workflow
.github/workflows/validate.yml      Syntax, packaging, and index validation
.github/workflows/apt-repo-smoke.yml APT repository smoke test
install.sh                          Checksum-verifying Termux installer
patches/capnp-android.patch         Cap'n Proto Android patches for workerd
scripts/generate_release_index.py   Immutable URLs and SHA-256 indexes
scripts/package_wrangler_android.py Assemble self-contained Wrangler Termux .deb
scripts/patch_workerd_android.py    Android/Bionic workerd dependency/toolchain patcher
scripts/run_workerd_android_target_tool.sh Execute Android build-time tools under Termux/QEMU
scripts/setup_apt_repo.sh           Bootstrap signed Termux APT repository
scripts/test_wrangler_termux.sh     Wrangler/esbuild/workerd Termux smoke test
server/                             Repository sync, sign, and publish daemon scripts
tests/                              Unit and patch characterization tests
```

## Limitations

- Only Android/Termux `aarch64` is currently built.
- Packages target the standard `com.termux` prefix, `/data/data/com.termux/files/usr`.
- This is an independent project, not an official Cloudflare, Wrangler, workerd, or esbuild distribution.

## Sources and licensing

Wrangler, workerd, esbuild, and their dependencies retain their respective upstream licenses. This repository's original automation code is available under the MIT License.
