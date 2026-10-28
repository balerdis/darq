"""The engram port resolution, three implementations, one set of vectors.

`core/engram_port.py` (used by `doctor`), `engram-hook.py` (Claude Code) and
`engram.ts` (OpenCode) each carry their own copy of the same rule, because the
hook is a standalone stdlib script and the plugin is TypeScript. The shared
vectors in `tests/fixtures/engram_port_vectors.json` are synthetic /proc tables
(never a real /proc), so the three cannot drift apart.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from darq.adapters.claudecode import render as render_module
from darq.adapters.claudecode import Adapter
from darq.core import engram_port, listeners
from darq.core.types import Environment
from test_claudecode_engram_hooks import engram

ROOT = Path(__file__).resolve().parent.parent
VECTORS = json.loads((ROOT / "tests/fixtures/engram_port_vectors.json").read_text())["vectors"]
PLUGIN = ROOT / "src/darq/adapters/opencode/assets/plugins/engram.ts"
HARNESS = ROOT / "tests/fixtures/engram_port_harness.mjs"
OWN = os.getuid()
FOREIGN = OWN + 1


def _port(token, uid, base=17437):
    if token == "default":
        return 7437
    if token == "fallback":
        return base + uid % 10000
    return token


def _table(rows, uid, header=True):
    lines = ["  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode"] if header else []
    for index, row in enumerate(rows):
        if isinstance(row, str):
            lines.append(row)
            continue
        address, port, state, owner = row
        lines.append(
            f"  {index:>2}: {address}:{_port(port, uid):04X} 00000000:0000 {state} 00000000:00000000 "
            f"00:00000000 00000000 {OWN if owner == 'own' else FOREIGN:>5}        0 {1000 + index} 1 0000000000000000 100 0 0 10 0"
        )
    return "\n".join(lines) + "\n"


def _expected(vector, uid):
    expect = vector["expect"]
    base = int(vector.get("fallback_base", 17437))
    return None if expect is None else _port(expect, uid, base)


class Scenario:
    """One vector written to disk as the pair of tables the three implementations read."""

    def __init__(self, test: unittest.TestCase, vector: dict):
        directory = tempfile.TemporaryDirectory()
        test.addCleanup(directory.cleanup)
        root = Path(directory.name)
        self.tcp4 = root / "tcp"
        self.tcp6 = root / "tcp6"
        for path, rows in ((self.tcp4, vector["tcp4"]), (self.tcp6, vector["tcp6"])):
            if rows is not None:
                path.write_text(_table(rows, OWN, vector.get("header", True)))
        self.env = {"ENGRAM_PORT_PROC_TCP4": str(self.tcp4), "ENGRAM_PORT_PROC_TCP6": str(self.tcp6)}
        if vector["env_port"] is not None:
            self.env["ENGRAM_PORT"] = vector["env_port"]
        if "fallback_base" in vector:
            self.env["ENGRAM_PORT_FALLBACK_BASE"] = vector["fallback_base"]


def load_hook(test: unittest.TestCase):
    directory = tempfile.TemporaryDirectory()
    test.addCleanup(directory.cleanup)
    tmp = Path(directory.name)
    layout = Adapter().layout(Environment(home=tmp, data_dir=tmp / "data"))
    script = tmp / "engram-hook.py"
    script.write_bytes(render_module.render_engram_hook_script(layout, engram()))
    spec = importlib.util.spec_from_file_location("engram_hook_under_test", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CoreResolutionTest(unittest.TestCase):
    def test_every_vector(self):
        for vector in VECTORS:
            with self.subTest(vector["name"]):
                scenario = Scenario(self, vector)
                resolution = engram_port.resolve(scenario.env, OWN, tcp4=scenario.tcp4, tcp6=scenario.tcp6)
                self.assertEqual(resolution.port, _expected(vector, OWN))

    def test_the_fallback_formula(self):
        self.assertEqual(engram_port.fallback_port(0), 17437)
        self.assertEqual(engram_port.fallback_port(1000), 18437)
        self.assertEqual(engram_port.fallback_port(9999), 27436)
        self.assertEqual(engram_port.fallback_port(10000), 17437)
        self.assertEqual(engram_port.fallback_port(65534), 17437 + 5534)
        self.assertEqual(engram_port.fallback_port(1000, {"ENGRAM_PORT_FALLBACK_BASE": "20000"}), 21000)
        # A base that would push the port past 65535 is ignored.
        self.assertEqual(engram_port.fallback_port(9999, {"ENGRAM_PORT_FALLBACK_BASE": "60000"}), 27436)

    def test_proc_paths_follow_the_environment(self):
        self.assertEqual(engram_port.proc_paths({}), (listeners.TCP4, listeners.TCP6))
        self.assertEqual(
            engram_port.proc_paths({engram_port.TCP4_ENV: "/x/4", engram_port.TCP6_ENV: "/x/6"}),
            (Path("/x/4"), Path("/x/6")),
        )


class HookResolutionTest(unittest.TestCase):
    def test_every_vector(self):
        hook = load_hook(self)
        for vector in VECTORS:
            with self.subTest(vector["name"]):
                scenario = Scenario(self, vector)
                self.assertEqual(hook.resolve_port(scenario.env, OWN), _expected(vector, OWN))

    def test_the_formula_for_other_uids(self):
        hook = load_hook(self)
        scenario = Scenario(self, {"env_port": None, "tcp4": [["0100007F", "default", "0A", "foreign"]], "tcp6": []})
        for uid in (0, 1000, 10000, 12345):
            # The table's holder is FOREIGN, a uid that is never `uid` here except by luck.
            if uid == FOREIGN:
                continue
            self.assertEqual(hook.resolve_port(scenario.env, uid), 17437 + uid % 10000)


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class PluginResolutionTest(unittest.TestCase):
    def run_plugin(self, scenarios: list[Scenario]) -> list[dict]:
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                ["node", "--experimental-strip-types", "--no-warnings", str(HARNESS), str(PLUGIN)],
                input=json.dumps([{"env": scenario.env} for scenario in scenarios]),
                capture_output=True,
                text=True,
                timeout=120,
                env={"PATH": os.environ.get("PATH", ""), "HOME": directory},
                cwd=directory,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_every_vector(self):
        # One Node process for all of them: the plugin keeps nothing between runs.
        scenarios = [Scenario(self, vector) for vector in VECTORS]
        for vector, outcome in zip(VECTORS, self.run_plugin(scenarios), strict=True):
            with self.subTest(vector["name"]):
                expected = _expected(vector, OWN)
                if expected is None:
                    self.assertEqual(outcome, {"fetched": [], "spawned": []})
                else:
                    self.assertEqual(outcome["fetched"], [expected])
                    self.assertEqual([s["port"] for s in outcome["spawned"]], [str(expected)])


if __name__ == "__main__":
    unittest.main()
