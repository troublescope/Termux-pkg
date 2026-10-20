"""Unit tests for workerd Android patching script."""
import tempfile
import unittest
from pathlib import Path
import subprocess
import sys


PATCH_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "patch_workerd_android.py"


class PatchWorkerdAndroidTests(unittest.TestCase):
    def test_pyodide_patching(self):
        with tempfile.TemporaryDirectory() as td:
            tree = Path(td)
            # Create minimal workerd skeleton needed by patch_workerd_android.py
            (tree / "MODULE.bazel").write_text('module(name = "workerd")\n', encoding="utf-8")
            (tree / "BUILD.bazel").write_text(
                '# Detect whether we use Linux/macOS/either, used to configure whether tcmalloc/perfetto should be\n'
                '# used.\n'
                'config_setting(\n'
                '    name = "is_macos",\n'
                '    constraint_values = ["@platforms//os:macos"],\n'
                '    visibility = ["//visibility:public"],\n'
                ')\n'
                '    match_any = [\n'
                '        ":is_linux",\n'
                '        ":is_macos",\n'
                '    ],\n',
                encoding="utf-8",
            )
            (tree / "build").mkdir()
            (tree / "build" / "BUILD.zlib").write_text(
                'selects.config_setting_group(\n'
                '    name = "arm64_linux",\n'
                '    match_all = [\n'
                '        "@platforms//cpu:aarch64",\n'
                '        "@platforms//os:linux",\n'
                '    ],\n'
                ')\n'
                '        "@platforms//os:linux": ["ARMV8_OS_LINUX"],\n'
                '        "@platforms//os:macos": ["ARMV8_OS_MACOS"],\n'
                '        "@platforms//os:windows": ["ARMV8_OS_WINDOWS"],\n'
                '        ":arm64_linux": ["ARMV8_OS_LINUX"],\n',
                encoding="utf-8",
            )
            (tree / "build" / "deps").mkdir()
            (tree / "build" / "deps" / "gen").mkdir()
            (tree / "build" / "deps" / "gen" / "deps.MODULE.bazel").write_text(
                'http.archive(\n    name = "capnp-cpp",\n',
                encoding="utf-8",
            )
            (tree / "src" / "workerd" / "jsg").mkdir(parents=True)
            (tree / "src" / "workerd" / "jsg" / "modules-new.c++").write_text(
                '#include <simdutf.h>\n', encoding="utf-8"
            )
            (tree / "patches" / "v8").mkdir(parents=True)
            (tree / "build" / "deps" / "v8.MODULE.bazel").write_text(
                'PATCHES = [\n    "0001-v8.patch",\n]\n', encoding="utf-8"
            )
            (tree / "build" / "wd_js_bundle.bzl").write_text(
                '        "_tool": attr.label(\n'
                '            executable = True,\n'
                '            allow_single_file = True,\n'
                '            cfg = "target",\n'
                '            default = "//src/rust/gen-compile-cache",\n'
                '        ),\n',
                encoding="utf-8",
            )
            (tree / "src" / "workerd" / "api" / "crypto").mkdir(parents=True)
            (tree / "src" / "workerd" / "api" / "crypto" / "endianness.c++").write_text(
                '#if defined(__linux__) || defined(__CYGWIN__)\n\n#include <endian.h>\n',
                encoding="utf-8",
            )
            (tree / "build" / "config").mkdir()
            (tree / "build" / "config" / "BUILD.bazel").write_text(
                'config_setting(\n'
                '    name = "rust_cc_common_link",\n'
                '    values = {"define": "never_match=true"},  # This will never match\n'
                '    visibility = ["//visibility:public"],\n'
                ')\n',
                encoding="utf-8",
            )
            (tree / "build" / "deps" / "rust.MODULE.bazel").write_text(
                '    "aarch64-unknown-linux-gnu",\n'
                '        "aarch64-unknown-linux-gnu": ["-Ctarget-feature=+crc"],\n',
                encoding="utf-8",
            )
            (tree / ".bazelrc").write_text(
                'build --color=yes\n', encoding="utf-8"
            )

            # Pyodide files
            (tree / "src" / "pyodide" / "tools").mkdir(parents=True)
            helpers_file = tree / "src" / "pyodide" / "helpers.bzl"
            helpers_file.write_text(
                'def run_patch():\n'
                '    js_run_binary(\n'
                '        name = "run_patch",\n'
                '        tool = Label("//src/pyodide/tools:patch_pyodide_asm"),\n'
                '    )\n',
                encoding="utf-8",
            )
            tools_file = tree / "src" / "pyodide" / "tools" / "BUILD.bazel"
            tools_file.write_text(
                'js_binary(\n'
                '    name = "patch_pyodide_asm",\n'
                '    entry_point = "patch_pyodide_asm.ts",\n'
                ')\n',
                encoding="utf-8",
            )

            res = subprocess.run([sys.executable, str(PATCH_SCRIPT), str(tree)], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

            # Check helpers.bzl was patched with use_execroot_entry_point = False
            self.assertIn("use_execroot_entry_point = False", helpers_file.read_text(encoding="utf-8"))

            # Check tools BUILD.bazel was untouched (js_binary does not have use_execroot_entry_point)
            self.assertNotIn("use_execroot_entry_point", tools_file.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
