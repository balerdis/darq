"""`models set` / `unset` / `list`: the CLI surface for a per-agent preference.

Follows the same discipline as `test_cli.py`: real disk, a throwaway home, and
the double only where a real filesystem condition cannot be produced.
"""
from __future__ import annotations

import io
import json
import unittest
from dataclasses import replace
from pathlib import PurePosixPath
from unittest.mock import patch

from pegasus import cli
from pegasus.adapters import available
from pegasus.core import content as content_module
from pegasus.core import journal as journal_module
from pegasus.core.content import AgentMode, Agent, Content
from pegasus.core.types import Environment
from pegasus.infra.model_assignment_store_file import model_assignment_path
from real_home import RealHomeTestCase as _RealHomeTestCase

AT = "2026-08-14T00:00:00+00:00"
CLI = available().ids()[0]
CONFIGURABLE_AGENT = "sdd-apply"


class RealHomeTestCase(_RealHomeTestCase):
    def runtime(self) -> cli.Runtime:
        return cli.Runtime(filesystem=self.filesystem, home=self.home, now=AT, out=io.StringIO())

    def run_cli(self, *argv) -> tuple[int, dict]:
        context = self.runtime()
        code = cli.main([*argv, "--json"], runtime=context)
        return code, json.loads(context.out.getvalue())

    def layout(self):
        return available().get(CLI).layout(Environment(home=self.home))

    def present(self) -> None:
        self.layout().config_dir.mkdir(parents=True, exist_ok=True)

    def install(self, *extra) -> None:
        """A real installation to reapply.

        `models set` and `models unset` render what they record, so they
        refuse a CLI with nothing installed the same way `mcp grant` and
        `directory grant` already do -- every test below that expects one of
        them to succeed has to stand on an installation."""
        self.present()
        code, _ = self.run_cli("install", "--cli", CLI, *extra)
        self.assertEqual(code, 0)


class SetTest(RealHomeTestCase):
    def test_setting_a_configurable_agent_succeeds_and_reports_it(self):
        self.install()
        code, report = self.run_cli(
            "models", "set", "--cli", CLI, "--assign", f"{CONFIGURABLE_AGENT}=anthropic/claude-sonnet-5", "--effort", f"{CONFIGURABLE_AGENT}=high",
        )
        self.assertEqual(code, 0)
        self.assertEqual(report["action"], "set")
        self.assertEqual(report["cli"], CLI)
        self.assertEqual(
            report["assignments"],
            [{"agent": CONFIGURABLE_AGENT, "model": "anthropic/claude-sonnet-5", "effort": "high"}],
        )

    def test_setting_persists_to_the_store(self):
        self.install()
        self.run_cli(
            "models", "set", "--cli", CLI, "--assign", f"{CONFIGURABLE_AGENT}=anthropic/claude-sonnet-5",
        )
        loaded = cli.model_assignment_store(self.runtime()).load()
        from pegasus.core import model_assignments as model_assignments_module

        assignment = model_assignments_module.get(loaded, CLI, CONFIGURABLE_AGENT)
        self.assertIsNotNone(assignment)
        self.assertEqual(assignment.full_id, "anthropic/claude-sonnet-5")

    def test_an_unknown_agent_is_refused_with_a_clear_reason(self):
        code, report = self.run_cli(
            "models", "set", "--cli", CLI, "--assign", "nonexistent-agent=anthropic/claude-sonnet-5",
        )
        self.assertNotEqual(code, 0)
        self.assertEqual(report["status"], "failed")
        self.assertIn("nonexistent-agent", report["error"])
        self.assertFalse(model_assignment_path(self.filesystem, self.home).exists())

    def test_a_non_configurable_agent_is_refused_with_a_clear_reason(self):
        not_configurable = Agent(
            name="static-agent",
            description="an agent nothing ever lets configure a model",
            body="body",
            mode=AgentMode.SUBAGENT,
            source=PurePosixPath("agents/static-agent.md"),
            model_configurable=False,
        )
        with patch("pegasus.core.content.load", return_value=Content(agents=(not_configurable,))):
            code, report = self.run_cli(
                "models", "set", "--cli", CLI, "--assign", "static-agent=anthropic/claude-sonnet-5",
            )
        self.assertNotEqual(code, 0)
        self.assertEqual(report["status"], "failed")
        self.assertIn("static-agent", report["error"])
        self.assertFalse(model_assignment_path(self.filesystem, self.home).exists())

    def test_a_malformed_model_spec_is_refused(self):
        code, report = self.run_cli(
            "models", "set", "--cli", CLI, "--assign", f"{CONFIGURABLE_AGENT}=not-a-provider-slash-model",
        )
        self.assertNotEqual(code, 0)
        self.assertEqual(report["status"], "failed")


class UnsetTest(RealHomeTestCase):
    def test_unsetting_something_never_set_is_a_no_op_not_an_error(self):
        self.install()
        code, report = self.run_cli("models", "unset", "--cli", CLI, "--agent", CONFIGURABLE_AGENT)
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "already-unset")

    def test_unsetting_a_set_assignment_removes_it(self):
        self.install()
        self.run_cli(
            "models", "set", "--cli", CLI, "--assign", f"{CONFIGURABLE_AGENT}=anthropic/claude-sonnet-5",
        )
        code, report = self.run_cli("models", "unset", "--cli", CLI, "--agent", CONFIGURABLE_AGENT)
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "unset")

        from pegasus.core import model_assignments as model_assignments_module

        loaded = cli.model_assignment_store(self.runtime()).load()
        self.assertIsNone(model_assignments_module.get(loaded, CLI, CONFIGURABLE_AGENT))


class AppliesTest(RealHomeTestCase):
    """Recording an assignment and rendering it are one step, like every sibling.

    `mcp grant`, `mcp revoke` and `directory grant` all record a decision and
    reapply the configuration in the same command; `models set` and `models
    unset` used to record and then tell the person to reinstall. Everything
    below reads the rendered configuration back off real disk, because "the
    assignment reached the configuration" is a claim about the file OpenCode
    opens -- a return value saying so would only be a proxy for it.
    """

    AGENT = CONFIGURABLE_AGENT
    MODEL = "anthropic/claude-sonnet-5"
    #: A server the user administers under a key of their own. Its selection
    #: cannot be recovered from the rendered configuration (a binding writes
    #: no `/mcp/<id>` key), so it is exactly what an internal `install` that
    #: forgot to reconstruct the recorded selection would retire.
    BOUND = ("cbm", "codebase-memory-mcp")

    def install(self, *extra) -> None:
        """The base's own installation, plus the catalog that makes an
        assignment honourable at all."""
        self.write_models_catalog()
        super().install(*extra)

    def write_models_catalog(self) -> None:
        """What a machine with a reachable provider looks like, written the
        same way `tests/test_cli.py` writes one -- without it no assignment
        is ever honoured and every guard below would measure nothing."""
        path = self.home / ".cache" / "opencode" / "models.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {"anthropic": {"builtin": True, "models": {"claude-sonnet-5": {"tool_call": True, "reasoning": True}}}}
            ),
            encoding="utf-8",
        )

    def installed(self):
        return journal_module.install_for(cli.journal_store(self.runtime()).load(), CLI)

    def rendered_agent(self) -> dict:
        document = json.loads(self.layout().settings_file.read_text(encoding="utf-8"))
        return document["agent"][self.AGENT]

    def convention_path(self):
        return self.layout().skills_dir / content_module.mcp_convention_path(self.BOUND[0])

    def drop_mcp_bindings(self) -> None:
        """An install predating `mcp_bindings` (or one that otherwise lost
        it): a bound convention with no recorded key, the same fixture
        `tests/test_cli_update.py` and `tests/test_cli_mcp.py` already use."""
        store = cli.journal_store(self.runtime())
        journal = store.load()
        install = journal_module.install_for(journal, CLI)
        store.save(journal_module.with_install(journal, replace(install, mcp_bindings={})))

    def test_an_assignment_reaches_the_rendered_agent_with_no_further_command(self):
        self.install()
        code, _ = self.run_cli(
            "models", "set", "--cli", CLI, "--assign", f"{self.AGENT}={self.MODEL}", "--effort", f"{self.AGENT}=high",
        )
        self.assertEqual(code, 0)
        value = self.rendered_agent()
        self.assertEqual(value["model"], self.MODEL)
        self.assertEqual(value["variant"], "high")

    def test_removing_an_assignment_takes_it_back_out_of_the_rendered_agent(self):
        self.install()
        self.run_cli("models", "set", "--cli", CLI, "--assign", f"{self.AGENT}={self.MODEL}")
        self.assertEqual(self.rendered_agent()["model"], self.MODEL)
        code, _ = self.run_cli("models", "unset", "--cli", CLI, "--agent", self.AGENT)
        self.assertEqual(code, 0)
        self.assertNotIn("model", self.rendered_agent())

    def test_setting_against_a_cli_with_nothing_installed_is_refused_and_writes_nothing(self):
        self.present()
        self.write_models_catalog()
        code, report = self.run_cli(
            "models", "set", "--cli", CLI, "--assign", f"{self.AGENT}={self.MODEL}",
        )
        self.assertNotEqual(code, 0)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["error"], f"{CLI} has nothing installed; run install first")
        self.assertFalse(model_assignment_path(self.filesystem, self.home).exists())
        self.assertFalse(self.layout().settings_file.exists())

    def test_removing_against_a_cli_with_nothing_installed_is_refused_and_writes_nothing(self):
        self.present()
        self.write_models_catalog()
        code, report = self.run_cli("models", "unset", "--cli", CLI, "--agent", self.AGENT)
        self.assertNotEqual(code, 0)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["error"], f"{CLI} has nothing installed; run install first")
        self.assertFalse(model_assignment_path(self.filesystem, self.home).exists())
        self.assertFalse(self.layout().settings_file.exists())

    def test_a_bound_mcp_server_survives_an_assignment(self):
        """The regression that matters most: the internal `install` has to
        reconstruct the recorded selection, not drop it."""
        self.install("--mcp", "=".join(self.BOUND))
        self.assertTrue(self.convention_path().exists(), "the fixture never bound a server")
        code, _ = self.run_cli(
            "models", "set", "--cli", CLI, "--assign", f"{self.AGENT}={self.MODEL}",
        )
        self.assertEqual(code, 0)
        self.assertEqual(self.rendered_agent()["model"], self.MODEL)
        self.assertTrue(
            self.convention_path().exists(), "assigning a model retired the bound server's convention"
        )
        self.assertEqual(self.installed().mcp_bindings, {self.BOUND[0]: self.BOUND[1]})

    def test_a_bound_mcp_server_survives_a_removal(self):
        self.install("--mcp", "=".join(self.BOUND))
        self.run_cli("models", "set", "--cli", CLI, "--assign", f"{self.AGENT}={self.MODEL}")
        # Or the removal below would have nothing to take back out and this
        # would approve a configuration that never carried the model at all.
        self.assertEqual(self.rendered_agent()["model"], self.MODEL)
        code, _ = self.run_cli("models", "unset", "--cli", CLI, "--agent", self.AGENT)
        self.assertEqual(code, 0)
        self.assertNotIn("model", self.rendered_agent())
        self.assertTrue(
            self.convention_path().exists(), "removing an assignment retired the bound server's convention"
        )
        self.assertEqual(self.installed().mcp_bindings, {self.BOUND[0]: self.BOUND[1]})

    def test_an_unresolved_binding_is_refused_the_way_its_siblings_refuse_it(self):
        self.install("--mcp", "=".join(self.BOUND))
        self.drop_mcp_bindings()
        code, report = self.run_cli(
            "models", "set", "--cli", CLI, "--assign", f"{self.AGENT}={self.MODEL}",
        )
        self.assertNotEqual(code, 0)
        self.assertEqual(
            report["error"],
            cli.unresolved_bindings_message(
                CLI, [self.BOUND[0]], program_name=cli.default_identity().program_name
            ),
        )
        self.assertFalse(model_assignment_path(self.filesystem, self.home).exists())

    def test_what_is_left_to_do_is_the_adapters_own_activation_step(self):
        """The old note said the installation did not carry the assignment
        yet and told the person to reinstall. It carries it now, so the only
        step left is the one every other write already reports."""
        self.install()
        code, report = self.run_cli(
            "models", "set", "--cli", CLI, "--assign", f"{self.AGENT}={self.MODEL}",
        )
        self.assertEqual(code, 0)
        self.assertEqual(tuple(report["activation"]), available().get(CLI).activation_steps())


class ListTest(RealHomeTestCase):
    def test_no_agent_starts_with_an_assignment(self):
        code, report = self.run_cli("models", "list")
        self.assertEqual(code, 0)
        self.assertEqual(report["assignments"], [])

    def test_listing_shows_what_was_set(self):
        self.install()
        self.run_cli(
            "models", "set", "--cli", CLI, "--assign", f"{CONFIGURABLE_AGENT}=anthropic/claude-sonnet-5",
        )
        code, report = self.run_cli("models", "list")
        self.assertEqual(code, 0)
        self.assertEqual(len(report["assignments"]), 1)
        self.assertEqual(report["assignments"][0]["agent"], CONFIGURABLE_AGENT)

    def test_listing_can_be_narrowed_to_one_cli(self):
        code, report = self.run_cli("models", "list", "--cli", CLI)
        self.assertEqual(code, 0)
        self.assertEqual(report["assignments"], [])

    def test_listing_with_an_unknown_cli_is_refused(self):
        code, report = self.run_cli("models", "list", "--cli", "nonesuch")
        self.assertNotEqual(code, 0)
        self.assertEqual(report["status"], "failed")


class ProseTest(RealHomeTestCase):
    def test_set_reads_as_prose(self):
        self.install()
        context = self.runtime()
        cli.main(
            ["models", "set", "--cli", CLI, "--assign", f"{CONFIGURABLE_AGENT}=anthropic/claude-sonnet-5"],
            runtime=context,
        )
        self.assertIn(CONFIGURABLE_AGENT, context.out.getvalue())

    def test_missing_subcommand_is_an_error(self):
        code, report = self.run_cli("models")
        self.assertNotEqual(code, 0)
        self.assertEqual(report["status"], "failed")


if __name__ == "__main__":
    unittest.main()
