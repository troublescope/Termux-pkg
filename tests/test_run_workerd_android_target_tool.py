"""Unit tests for run_workerd_android_target_tool.sh argument handling."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


RUNNER_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_workerd_android_target_tool.sh"


class AndroidTargetToolRunnerTests(unittest.TestCase):
    def test_manifest_argument_parsing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tool = root / "fake_tool"
            tool.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            tool.chmod(0o755)

            manifest = root / "manifest.txt"
            in_file = root / "input.js"
            in_file.write_text("console.log('hi');\n", encoding="utf-8")
            out_file = root / "output.cache"

            manifest.write_text(f"{in_file} {out_file}\n", encoding="utf-8")

            # We create a fake docker command that simulates successful tool execution
            # by writing to staged output files.
            fake_bin = root / "bin"
            fake_bin.mkdir()
            fake_docker = fake_bin / "docker"
            fake_docker.write_text(
                '#!/bin/sh\n'
                '# Find manifest from arguments and create outputs\n'
                'for arg in "$@"; do\n'
                '  if [ -f "$arg" ]; then\n'
                '    while read -r in out; do\n'
                '      echo "cached" > "$out"\n'
                '    done < "$arg"\n'
                '  fi\n'
                'done\n'
                'exit 0\n',
                encoding="utf-8",
            )
            fake_docker.chmod(0o755)

            env = dict(os.environ)
            env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"

            # Test 1: older style -> tool manifest
            res1 = subprocess.run(
                ["bash", str(RUNNER_SCRIPT), str(tool), str(manifest)],
                cwd=td, env=env, capture_output=True, text=True,
            )
            self.assertEqual(res1.returncode, 0, res1.stderr)
            self.assertTrue(out_file.exists())
            self.assertEqual(out_file.read_text(encoding="utf-8").strip(), "cached")
            out_file.unlink()

            # Test 2: newer style -> tool --kind function manifest
            res2 = subprocess.run(
                ["bash", str(RUNNER_SCRIPT), str(tool), "--kind", "function", str(manifest)],
                cwd=td, env=env, capture_output=True, text=True,
            )
            self.assertEqual(res2.returncode, 0, res2.stderr)
            self.assertTrue(out_file.exists())
            self.assertEqual(out_file.read_text(encoding="utf-8").strip(), "cached")


if __name__ == "__main__":
    unittest.main()
