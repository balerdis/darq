"""`doctor` and the engram port held by another OS user."""
from __future__ import annotations

import io
import json
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from darq import cli
from darq.adapters import available
from darq.core import engram_port, listeners
from darq.core.types import Environment
from real_home import RealHomeTestCase

AT = "2026-08-14T00:00:00+00:00"
HEADER = "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode\n"
FOREIGN = os.getuid() + 1


def table(path: Path, *held: tuple[int, int]) -> dict[str, str]:
    rows = "".join(
        f"   {i}: 0100007F:{port:04X} 00000000:0000 0A 00000000:00000000 00:00000000 00000000 {uid:>5} 0 {i + 1} 1 0 100 0 0 10 0\n"
        for i, (port, uid) in enumerate(held)
    )
    path.write_text(HEADER + rows)
    return {engram_port.TCP4_ENV: str(path), engram_port.TCP6_ENV: str(path.parent / "tcp6")}


class WarningWording(unittest.TestCase):
    def test_nothing_refused_says_nothing(self):
        self.assertIsNone(engram_port.warning(engram_port.Resolution(7437), 1000))

    def test_the_fallback_is_named(self):
        text = engram_port.warning(engram_port.Resolution(18437, 7437, (4242,)), 1000)
        self.assertNotIn("reserved", text)
        self.assertIn("uid 4242", text)
        self.assertIn("port 7437", text)
        self.assertIn("port 18437 instead", text)

    def test_an_explicit_port_disables_the_memory(self):
        text = engram_port.warning(engram_port.Resolution(None, 9999, (4242,), explicit=True), 1000)
        self.assertIn("ENGRAM_PORT", text)
        self.assertIn("engram memory is disabled until you set ENGRAM_PORT to a free port", text)

    def test_both_ports_held_disables_the_memory(self):
        text = engram_port.warning(engram_port.Resolution(None, 7437, (4242,)), 1000)
        self.assertIn("(18437)", text)
        self.assertIn("engram memory is disabled", text)
        self.assertNotIn("reserved", text)
        self.assertIn("10000 apart", text)


class DoctorTest(RealHomeTestCase):
    def runtime(self) -> cli.Runtime:
        return cli.Runtime(
            filesystem=self.filesystem, home=self.home, now=AT, out=io.StringIO(), variables={"PATH": ""}
        )

    def install(self) -> None:
        layout = available().get("opencode").layout(Environment(home=self.home))
        layout.config_dir.mkdir(parents=True, exist_ok=True)
        argv = ["install", "--cli", "opencode", "--json"]
        self.assertEqual(cli.main(argv, runtime=self.runtime()), cli.OK)

    def doctor(self, env: dict[str, str], *, text: bool = False) -> dict | str:
        context = self.runtime()
        with mock.patch.dict(os.environ, env):
            if "ENGRAM_PORT" not in env:
                os.environ.pop("ENGRAM_PORT", None)
            self.assertEqual(cli.main(["doctor"] + ([] if text else ["--json"]), runtime=context), cli.OK)
        out = context.out.getvalue()
        if text:
            return out
        return next(item for item in json.loads(out)["clis"] if item["cli"] == "opencode")

    def test_a_foreign_default_port_is_reported_with_the_fallback(self):
        self.install()
        env = table(self.home / "tcp", (7437, FOREIGN))
        entry = self.doctor(env)
        warning = entry["engram_port_warning"]
        self.assertIn(f"uid {FOREIGN}", warning)
        self.assertIn(f"port {17437 + os.getuid() % 10000} instead", warning)

    def test_the_text_output_carries_the_warning(self):
        self.install()
        out = self.doctor(table(self.home / "tcp", (7437, FOREIGN)), text=True)
        self.assertIn("Warning: port 7437 on 127.0.0.1 is held by a process of another OS user", out)

    def test_an_explicit_foreign_port_says_the_memory_is_disabled(self):
        self.install()
        env = {**table(self.home / "tcp", (9999, FOREIGN)), "ENGRAM_PORT": "9999"}
        self.assertIn("disabled", self.doctor(env)["engram_port_warning"])

    def test_silent_when_this_user_holds_the_port(self):
        self.install()
        self.assertNotIn("engram_port_warning", self.doctor(table(self.home / "tcp", (7437, os.getuid()))))

    def test_silent_when_nobody_listens(self):
        self.install()
        self.assertNotIn("engram_port_warning", self.doctor(table(self.home / "tcp")))

    def test_silent_without_proc(self):
        self.install()
        env = {engram_port.TCP4_ENV: str(self.home / "nowhere")}
        self.assertNotIn("engram_port_warning", self.doctor(env))

    def test_only_the_plugin_and_the_hook_script_count_as_the_integration(self):
        def install(*ids):
            return SimpleNamespace(entries=tuple(SimpleNamespace(id=i, target=Path("/x")) for i in ids))

        # Real record ids: the MCP server and its convention exist without either.
        self.assertFalse(cli._has_engram_integration(install("mcp-server:engram", "mcp-convention:engram")))
        self.assertTrue(cli._has_engram_integration(install("own:plugins/engram.ts")))
        self.assertTrue(cli._has_engram_integration(install("mcp-hook-script:engram", "mcp-hook:engram:SessionStart")))


class SharedLookupTest(unittest.TestCase):
    def test_the_lookup_reads_listeners_only(self):
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tcp"
            table(path, (7437, 11), (7437, 22))
            self.assertEqual(listeners.listener_uids(path, 7437, listeners.LOOPBACK_V4), {11, 22})
            self.assertEqual(listeners.listener_uids(path, 7438, listeners.LOOPBACK_V4), set())
            self.assertEqual(listeners.listener_uids(path.parent / "missing", 7437, listeners.LOOPBACK_V4), set())


if __name__ == "__main__":
    unittest.main()
