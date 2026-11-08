"""Which engram binary the OpenCode plugin starts `serve` with.

The plugin used to take `engram` from PATH while the MCP entry ran the binary
DARQ downloads and pins, so two versions could run side by side (and with no
engram on PATH nothing started at all). The installer now writes the managed
path to `engram-bin.json` next to the plugin; the plugin prefers it.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path, PurePosixPath

from darq.adapters.opencode import Adapter
from darq.core.content import Distribution, Mcp
from darq.core.dependencies import program_path
from darq.core.types import Environment, FileArtifact

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "src/darq/adapters/opencode/assets/plugins/engram.ts"
HARNESS = ROOT / "tests/fixtures/engram_port_harness.mjs"
HOME = Path("/home/probe")


def _engram(distribution=Distribution.DOWNLOAD, name="engram") -> Mcp:
    return Mcp(
        name=name,
        description="d",
        body="# Convention\n",
        distribution=distribution,
        endpoint="https://example.test/releases/engram-linux-x64",
        source=PurePosixPath("mcp/engram.md"),
        version="1.2.3",
        checksum="sha256:" + "a" * 64,
    )


class SidecarRenderTest(unittest.TestCase):
    def setUp(self):
        self.adapter = Adapter()
        self.layout = self.adapter.layout(Environment(home=HOME, data_dir=HOME / ".local" / "share" / "darq"))

    def _sidecars(self, mcp):
        return [
            a for a in self.adapter.render_mcp(self.layout, mcp)
            if isinstance(a, FileArtifact) and a.path.name == "engram-bin.json"
        ]

    def test_a_downloaded_engram_writes_its_managed_path_beside_the_plugin(self):
        mcp = _engram()
        (sidecar,) = self._sidecars(mcp)
        self.assertEqual(sidecar.path, self.layout.plugins_dir / "engram-bin.json")
        self.assertEqual(
            json.loads(sidecar.content),
            {"engram_bin": str(program_path(self.layout.dependencies_dir, mcp))},
        )

    def test_another_server_or_a_bound_engram_writes_nothing(self):
        self.assertEqual(self._sidecars(_engram(name="probe")), [])
        self.assertEqual(self._sidecars(replace(_engram(), bound_to="engram")), [])


class PluginResolutionNodeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if shutil.which("node") is None:
            raise unittest.SkipTest("node is not installed")

    def _serve_cmd(self, managed, path_engram, sidecar=True):
        """What the installed plugin spawns for `serve`, given the managed path and the PATH engram."""
        with tempfile.TemporaryDirectory() as tmp:
            plugins = Path(tmp) / "plugins"
            plugins.mkdir()
            shutil.copy(PLUGIN, plugins / "engram.ts")
            if sidecar:
                (plugins / "engram-bin.json").write_text(json.dumps({"engram_bin": str(managed)}))
            env = {**os.environ, "FAKE_WHICH_ENGRAM": path_engram}
            env.pop("ENGRAM_BIN", None)
            if path_engram == "":
                env.pop("FAKE_WHICH_ENGRAM")
            result = subprocess.run(
                ["node", "--experimental-strip-types", str(HARNESS), str(plugins / "engram.ts")],
                input=json.dumps([{"env": {}}]),
                cwd=ROOT, env=env, capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            (scenario,) = json.loads(result.stdout)
            return scenario["spawned"][0]["cmd"][0]

    def _executable(self, tmp, name):
        path = Path(tmp) / name
        path.write_text("#!/bin/sh\n")
        path.chmod(0o755)
        return path

    def test_serve_uses_the_managed_binary_even_with_another_engram_on_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            managed = self._executable(tmp, "managed-engram")
            self.assertEqual(self._serve_cmd(managed, "/usr/bin/other-engram"), str(managed))

    def test_serve_falls_back_to_path_without_a_sidecar_or_with_a_missing_binary(self):
        with tempfile.TemporaryDirectory() as tmp:
            managed = self._executable(tmp, "managed-engram")
            self.assertEqual(self._serve_cmd(managed, "/usr/bin/other-engram", sidecar=False), "/usr/bin/other-engram")
            self.assertEqual(self._serve_cmd(Path(tmp) / "gone", "/usr/bin/other-engram"), "/usr/bin/other-engram")
            self.assertEqual(self._serve_cmd(Path(tmp) / "gone", "", sidecar=False), "engram")


if __name__ == "__main__":
    unittest.main()
