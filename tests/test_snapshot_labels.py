"""Every one of the eleven commands that take a snapshot generation records a
label naming which one it was.

Eight route through `cli.install()` sharing one `snapshot.save()` call site
(`install`, `update`, `models set`, `models unset`, `mcp grant`, `mcp
revoke`, `directory grant`, `directory revoke`); `uninstall`, `repair` and
`restore` take their own. The call-site list below is derived from
`cli.COMMANDS` (the argparse dispatch table) plus the two subcommand groups
(`models`, `mcp`, `directory`) that fan out into more than one label of their
own, rather than hand-typed independently of the code that actually routes a
command -- the same discipline `test_manual_static_figures.py` already
follows for other counts.

Real disk, a throwaway home, the same discipline `test_cli_repair.py` and
`test_batch_snapshot_atomicity.py` already follow.
"""
from __future__ import annotations

import io
import json

from pegasus import cli
from pegasus.adapters import available
from pegasus.core import codecs, content as content_module, pointer
from pegasus.core.types import Codec, Environment
from real_home import RealHomeTestCase as _RealHomeTestCase

AT = "2026-08-14T00:00:00+00:00"
# Pinned to OpenCode, not "whichever adapter is registered first": this
# suite exercises capabilities (mcp, per_agent_model, subagents declared
# inside the settings file, ...) that only OpenCode declares today. Since
# Claude Code registered, "available().ids()[0]" resolves alphabetically
# to "claudecode" instead, which cannot support what this file tests.
CLI = "opencode"
NO_BINARY = {"PATH": ""}
AGENT = "king-pegasus"
OWN_MCP_KEY = "figma"


class RealHomeTestCase(_RealHomeTestCase):
    def runtime(self) -> cli.Runtime:
        return cli.Runtime(
            filesystem=self.filesystem, home=self.home, now=AT, out=io.StringIO(), variables=NO_BINARY
        )

    def layout(self):
        return available().get(CLI).layout(Environment(home=self.home))

    def present(self) -> None:
        self.layout().config_dir.mkdir(parents=True, exist_ok=True)

    def run_cli(self, *argv) -> tuple[int, dict]:
        context = self.runtime()
        code = cli.main([*argv, "--json"], runtime=context)
        return code, json.loads(context.out.getvalue())

    def install(self, *extra) -> None:
        self.present()
        code, _ = self.run_cli("install", "--cli", CLI, *extra)
        self.assertEqual(code, 0)

    def declare_own_mcp_server(self, key: str) -> None:
        layout = self.layout()
        document = codecs.loads(Codec.JSON, layout.settings_file.read_text(encoding="utf-8"))
        document = pointer.set_at(document, f"/mcp/{key}", {"type": "local", "command": ["figma-server"]})
        layout.settings_file.write_text(codecs.dumps(Codec.JSON, document), encoding="utf-8")

    def own_directory(self) -> str:
        target = self.home / "worktrees" / "extra"
        target.mkdir(parents=True, exist_ok=True)
        return str(target)

    def plant_quarantined_entry(self) -> None:
        store = cli.journal_store(self.runtime())
        path = store.path
        payload = json.loads(path.read_bytes())
        install_payload = next(item for item in payload["installs"] if item["cli"] == CLI)
        install_payload.setdefault("granted_directories", []).append("/")
        path.write_bytes(json.dumps(payload).encode("utf-8"))

    def latest_label(self) -> str | None:
        store = cli.snapshot_store(self.runtime())
        generation = store.most_recent_readable()
        self.assertIsNotNone(generation)
        return store.read(generation).label


class EveryCallSiteRecordsItsOwnLabelTest(RealHomeTestCase):
    """Runs the eleven commands in sequence against one throwaway home,
    reading back the label of the generation each one just wrote."""

    def test_each_of_the_eleven_commands_labels_its_own_generation(self):
        seen: dict[str, str | None] = {}

        self.install()
        seen["install"] = self.latest_label()
        self.declare_own_mcp_server(OWN_MCP_KEY)

        code, report = self.run_cli("update", "--cli", CLI)
        self.assertEqual(code, 0, report)
        seen["update"] = self.latest_label()

        code, report = self.run_cli(
            "models", "set", "--cli", CLI, "--assign", f"{AGENT}=anthropic/claude-sonnet-5"
        )
        self.assertEqual(code, 0, report)
        seen["models set"] = self.latest_label()

        code, report = self.run_cli("models", "unset", "--cli", CLI, "--agent", AGENT)
        self.assertEqual(code, 0, report)
        seen["models unset"] = self.latest_label()

        code, report = self.run_cli("mcp", "grant", "--cli", CLI, OWN_MCP_KEY)
        self.assertEqual(code, 0, report)
        seen["mcp grant"] = self.latest_label()

        code, report = self.run_cli("mcp", "revoke", "--cli", CLI, OWN_MCP_KEY)
        self.assertEqual(code, 0, report)
        seen["mcp revoke"] = self.latest_label()

        directory = self.own_directory()
        code, report = self.run_cli("directory", "grant", "--cli", CLI, directory)
        self.assertEqual(code, 0, report)
        seen["directory grant"] = self.latest_label()

        code, report = self.run_cli("directory", "revoke", "--cli", CLI, directory)
        self.assertEqual(code, 0, report)
        seen["directory revoke"] = self.latest_label()

        self.plant_quarantined_entry()
        code, report = self.run_cli("repair", "--cli", CLI)
        self.assertEqual(code, 0, report)
        seen["repair"] = self.latest_label()

        code, report = self.run_cli("restore")
        self.assertEqual(code, 0, report)
        seen["restore"] = self.latest_label()

        code, report = self.run_cli("uninstall", "--cli", CLI)
        self.assertEqual(code, 0, report)
        seen["uninstall"] = self.latest_label()

        # Every one of the eleven recorded a label: none was left `None`.
        self.assertTrue(all(seen.values()), seen)
        # Every command's label names the command itself, so a person reading
        # the restore screen sees what they actually did -- never a generic
        # "install" for a `models set` batch, say.
        expected = {
            "install": "install",
            "update": "update",
            "models set": "models set",
            "models unset": "models unset",
            "mcp grant": "mcp grant",
            "mcp revoke": "mcp revoke",
            "directory grant": "directory grant",
            "directory revoke": "directory revoke",
            "repair": "repair",
            "restore": "restore",
            "uninstall": "uninstall",
        }
        self.assertEqual(seen, expected)
        # And no two of the eleven ever collide on the same label -- the
        # whole point of this field is telling them apart.
        self.assertEqual(len(set(seen.values())), len(seen))


class InstallCallSitesShareOneImplementationTest(RealHomeTestCase):
    """`cli.install()` is the single `snapshot.save()` call site the eight
    argparse-level commands above share; this asserts that sharing is real,
    not merely how today's eight callers happen to behave -- a caller that
    forgets `label=` gets the safe, correct default instead of a crash or a
    silently wrong guess.
    """

    def test_install_called_directly_with_no_label_defaults_to_install(self):
        self.present()
        report = cli.install(CLI, self.runtime(), mcp=[])
        self.assertEqual(report["status"], "installed")
        self.assertEqual(self.latest_label(), "install")


class ModelsApplyLabelTest(RealHomeTestCase):
    """`cli.models_apply` is reached only from the TUI's own models screen
    (see its own docstring: "not from `_models`'s own dispatch"), so it is
    not one of the eleven argparse-level commands above -- but it is its own
    ninth caller of `install()`, folding a batch of assignments and removals
    into one call, and it earns its own label distinct from `models set` /
    `models unset` for the same reason those two are distinct from each
    other: a person reading the restore screen should see what actually ran.
    """

    def test_models_apply_labels_its_generation_distinctly(self):
        self.install()
        assignment = cli.ModelAssignmentSpec(agent=AGENT, model="anthropic/claude-sonnet-5")
        report = cli.models_apply(CLI, [assignment], [], self.runtime())
        self.assertEqual(report["status"], "applied")
        self.assertEqual(self.latest_label(), "models apply")
