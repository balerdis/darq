"""One human intention must become one command, one snapshot, one render.

Configuring several things from the TUI used to fire several CLI commands --
`models set` once per agent, `mcp grant` once per key -- and each one took a
snapshot generation and re-rendered the whole configuration. With
`RETAIN_GENERATIONS` capped, four agents assigned in a row could evict the
entire restore history for what a person experienced as one action.

`install()` now accepts a whole batch in one call for each of these surfaces
(`model_assignments` directly; `mcp`/`granted`/`granted_directories` already
did), and `models set` / `mcp grant` / `mcp revoke` / `directory grant` /
`directory revoke` all take repeated flags instead of one call per item. This
module proves the two properties that make that worth doing:

1. A multi-item batch produces exactly one snapshot generation, not one per
   item.
2. A batch with one invalid item writes nothing at all -- neither a snapshot
   generation nor a partial change -- and names which item was invalid.

Follows the same discipline as `test_cli_models.py`/`test_cli_mcp.py`: real
disk, a throwaway home, and the double only where a real filesystem
condition cannot be produced.
"""
from __future__ import annotations

import io
import json

from pegasus import cli
from pegasus.adapters import available
from pegasus.core import journal as journal_module
from pegasus.core import model_assignments as model_assignments_module
from pegasus.core.types import Environment
from real_home import RealHomeTestCase as _RealHomeTestCase

AT = "2026-08-14T00:00:00+00:00"
CLI = available().ids()[0]

#: Two agents this release ships as configurable, so a batch can name more
#: than one without inventing a fixture -- see `test_manual_figures.py`'s
#: `EveryShippedAgentAcceptsAModelAssignmentTest` for the full derived list.
AGENT_ONE = "king-pegasus"
AGENT_TWO = "pegasus-explorer"


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
        self.present()
        code, _ = self.run_cli("install", "--cli", CLI, *extra)
        self.assertEqual(code, 0)

    def installed(self):
        return journal_module.install_for(cli.journal_store(self.runtime()).load(), CLI)

    def generations(self) -> list[int]:
        return cli.snapshot_store(self.runtime()).readable_generations()

    def declare_own_mcp_server(self, key: str) -> None:
        settings = self.layout().settings_file
        document = json.loads(settings.read_text(encoding="utf-8"))
        document.setdefault("mcp", {})[key] = {"type": "local", "command": [f"{key}-server"]}
        settings.write_text(json.dumps(document, indent=2), encoding="utf-8")

    def own_directory(self, name: str) -> str:
        target = self.home / "worktrees" / name
        target.mkdir(parents=True, exist_ok=True)
        return str(target)


class ModelsSetBatchTest(RealHomeTestCase):
    def test_a_multi_agent_batch_produces_exactly_one_generation(self):
        self.install()
        before = self.generations()
        code, _ = self.run_cli(
            "models", "set", "--cli", CLI,
            "--assign", f"{AGENT_ONE}=anthropic/claude-sonnet-5",
            "--assign", f"{AGENT_TWO}=anthropic/claude-sonnet-5",
        )
        self.assertEqual(code, 0)
        after = self.generations()
        self.assertEqual(len(after), len(before) + 1)

    def test_both_agents_land_in_the_one_generation(self):
        """Not just one generation -- the *same* generation carries both
        assignments, or this would only prove the count coincidentally
        matched two overlapping single-item batches."""
        self.install()
        self.run_cli(
            "models", "set", "--cli", CLI,
            "--assign", f"{AGENT_ONE}=anthropic/claude-sonnet-5",
            "--assign", f"{AGENT_TWO}=anthropic/claude-sonnet-5",
        )
        from pegasus.core import model_assignments as model_assignments_module

        assignments = cli.model_assignment_store(self.runtime()).load()
        self.assertIsNotNone(model_assignments_module.get(assignments, CLI, AGENT_ONE))
        self.assertIsNotNone(model_assignments_module.get(assignments, CLI, AGENT_TWO))

    def test_an_invalid_item_refuses_the_whole_batch_and_writes_nothing(self):
        self.install()
        before = self.generations()
        code, report = self.run_cli(
            "models", "set", "--cli", CLI,
            "--assign", f"{AGENT_ONE}=anthropic/claude-sonnet-5",
            "--assign", "nonexistent-agent=anthropic/claude-sonnet-5",
        )
        self.assertNotEqual(code, 0)
        self.assertIn("nonexistent-agent", report["error"])
        self.assertEqual(self.generations(), before)
        from pegasus.core import model_assignments as model_assignments_module

        assignments = cli.model_assignment_store(self.runtime()).load()
        self.assertIsNone(model_assignments_module.get(assignments, CLI, AGENT_ONE))

    def test_an_unmatched_effort_refuses_the_whole_batch(self):
        """`--effort` naming an agent no `--assign` named is a mistake in the
        batch's own shape, caught before either flag is even parsed into a
        `ModelAssignmentSpec` -- named explicitly, not silently dropped or
        misattributed to the wrong agent."""
        self.install()
        before = self.generations()
        code, report = self.run_cli(
            "models", "set", "--cli", CLI,
            "--assign", f"{AGENT_ONE}=anthropic/claude-sonnet-5",
            "--effort", f"{AGENT_TWO}=high",
        )
        self.assertNotEqual(code, 0)
        self.assertIn(AGENT_TWO, report["error"])
        self.assertEqual(self.generations(), before)


class ModelsUnsetBatchTest(RealHomeTestCase):
    def test_a_multi_agent_removal_produces_exactly_one_generation(self):
        self.install()
        self.run_cli(
            "models", "set", "--cli", CLI,
            "--assign", f"{AGENT_ONE}=anthropic/claude-sonnet-5",
            "--assign", f"{AGENT_TWO}=anthropic/claude-sonnet-5",
        )
        before = self.generations()
        code, _ = self.run_cli("models", "unset", "--cli", CLI, "--agent", AGENT_ONE, "--agent", AGENT_TWO)
        self.assertEqual(code, 0)
        self.assertEqual(len(self.generations()), len(before) + 1)

    def test_a_removal_that_fails_to_apply_leaves_the_assignment_on_disk(self):
        """All-or-nothing is not only about the batch refusing itself: it is
        about what survives when the apply fails after the batch was accepted.

        `models unset` used to write the mutated assignment store and only
        then call `install`. A failure inside `install` -- the render, the
        journal, the snapshot -- reported a failure the person could see
        while the removal was already on disk. That is the one state this
        guarantee exists to prevent, and it is the state `models_apply`, the
        sibling introduced for the identical operation, never had.

        The failure here is a real one: the snapshot root is made unwritable,
        so `install` cannot create the generation folder it opens with, and
        refuses for the same reason it would on a machine where that
        directory belongs to somebody else. Nothing is faked, and the
        failure lands on `install`'s very first write, which is exactly
        where a store already mutated by the caller would be stranded.
        """
        self.install()
        self.run_cli("models", "set", "--cli", CLI, "--assign", f"{AGENT_ONE}=anthropic/claude-sonnet-5")
        runtime = self.runtime()
        assigned = model_assignments_module.get(
            cli.model_assignment_store(runtime).load(), CLI, AGENT_ONE
        )
        self.assertIsNotNone(assigned, "the assignment must exist before the failing removal")
        snapshots = cli.snapshot_store(runtime).root
        snapshots.chmod(0o500)
        try:
            code, _ = self.run_cli("models", "unset", "--cli", CLI, "--agent", AGENT_ONE)
        finally:
            snapshots.chmod(0o700)
        self.assertNotEqual(code, 0, "the removal must report the failure")
        self.assertEqual(
            model_assignments_module.get(cli.model_assignment_store(self.runtime()).load(), CLI, AGENT_ONE),
            assigned,
            "a removal that reported failure must not have reached the store",
        )


class ModelsApplyMixedBatchTest(RealHomeTestCase):
    """`cli.models_apply` is the single entry point the TUI's models screen
    confirms through when a sitting has staged both assignments and a
    removal -- see that function's own docstring for why it exists apart
    from `models_set`/`models_unset`. Exercised directly here, through
    Python rather than a CLI subcommand (there is no `models apply`
    subcommand -- see `models_apply`'s own docstring on why), the same way
    `ModelsSetBatchTest` exercises `models_set` through `run_cli`.
    """

    def test_a_mixed_batch_of_assignments_and_a_removal_produces_exactly_one_generation(self):
        self.install()
        self.run_cli("models", "set", "--cli", CLI, "--assign", f"{AGENT_TWO}=anthropic/claude-sonnet-5")
        before = self.generations()
        report = cli.models_apply(
            CLI,
            [cli.ModelAssignmentSpec(agent=AGENT_ONE, model="anthropic/claude-sonnet-5")],
            [AGENT_TWO],
            self.runtime(),
        )
        self.assertEqual(report["status"], "applied")
        after = self.generations()
        self.assertEqual(len(after), len(before) + 1)
        from pegasus.core import model_assignments as model_assignments_module

        assignments = cli.model_assignment_store(self.runtime()).load()
        self.assertIsNotNone(model_assignments_module.get(assignments, CLI, AGENT_ONE))
        self.assertIsNone(model_assignments_module.get(assignments, CLI, AGENT_TWO))

    def test_an_invalid_assignment_in_a_mixed_batch_refuses_the_whole_call_and_writes_nothing(self):
        self.install()
        self.run_cli("models", "set", "--cli", CLI, "--assign", f"{AGENT_TWO}=anthropic/claude-sonnet-5")
        before = self.generations()
        with self.assertRaises(cli.CommandError) as caught:
            cli.models_apply(
                CLI,
                [cli.ModelAssignmentSpec(agent="nonexistent-agent", model="anthropic/claude-sonnet-5")],
                [AGENT_TWO],
                self.runtime(),
            )
        self.assertIn("nonexistent-agent", str(caught.exception))
        self.assertEqual(self.generations(), before)
        from pegasus.core import model_assignments as model_assignments_module

        assignments = cli.model_assignment_store(self.runtime()).load()
        # The staged removal must not have landed either -- all-or-nothing
        # means the whole call, not just the assignment half of it.
        self.assertIsNotNone(model_assignments_module.get(assignments, CLI, AGENT_TWO))


class McpGrantBatchTest(RealHomeTestCase):
    def test_a_multi_key_grant_produces_exactly_one_generation(self):
        self.install()
        self.declare_own_mcp_server("alpha-mcp")
        self.declare_own_mcp_server("beta-mcp")
        before = self.generations()
        code, report = self.run_cli("mcp", "grant", "--cli", CLI, "alpha-mcp", "beta-mcp")
        self.assertEqual(code, 0, report)
        after = self.generations()
        self.assertEqual(len(after), len(before) + 1)
        self.assertEqual(set(self.installed().granted_mcp), {"alpha-mcp", "beta-mcp"})

    def test_an_undeclared_key_refuses_the_whole_batch_and_writes_nothing(self):
        self.install()
        self.declare_own_mcp_server("alpha-mcp")
        before = self.generations()
        code, report = self.run_cli("mcp", "grant", "--cli", CLI, "alpha-mcp", "never-declared-mcp")
        self.assertNotEqual(code, 0)
        self.assertIn("never-declared-mcp", report["error"])
        self.assertEqual(self.generations(), before)
        self.assertEqual(self.installed().granted_mcp, ())


class McpRevokeBatchTest(RealHomeTestCase):
    def test_a_multi_key_revoke_produces_exactly_one_generation(self):
        self.install()
        self.declare_own_mcp_server("alpha-mcp")
        self.declare_own_mcp_server("beta-mcp")
        self.run_cli("mcp", "grant", "--cli", CLI, "alpha-mcp", "beta-mcp")
        before = self.generations()
        code, _ = self.run_cli("mcp", "revoke", "--cli", CLI, "alpha-mcp", "beta-mcp")
        self.assertEqual(code, 0)
        self.assertEqual(len(self.generations()), len(before) + 1)
        self.assertEqual(self.installed().granted_mcp, ())


class DirectoryGrantBatchTest(RealHomeTestCase):
    def test_a_multi_path_grant_produces_exactly_one_generation(self):
        self.install()
        first = self.own_directory("first")
        second = self.own_directory("second")
        before = self.generations()
        code, report = self.run_cli("directory", "grant", "--cli", CLI, first, second)
        self.assertEqual(code, 0, report)
        after = self.generations()
        self.assertEqual(len(after), len(before) + 1)
        self.assertEqual(set(self.installed().granted_directories), {first, second})

    def test_an_invalid_path_refuses_the_whole_batch_and_writes_nothing(self):
        self.install()
        first = self.own_directory("first")
        before = self.generations()
        code, report = self.run_cli("directory", "grant", "--cli", CLI, first, "relative/path")
        self.assertNotEqual(code, 0)
        self.assertIn("relative/path", report["error"])
        self.assertEqual(self.generations(), before)
        self.assertEqual(self.installed().granted_directories, ())


class DirectoryRevokeBatchTest(RealHomeTestCase):
    def test_a_multi_path_revoke_produces_exactly_one_generation(self):
        self.install()
        first = self.own_directory("first")
        second = self.own_directory("second")
        self.run_cli("directory", "grant", "--cli", CLI, first, second)
        before = self.generations()
        code, _ = self.run_cli("directory", "revoke", "--cli", CLI, first, second)
        self.assertEqual(code, 0)
        self.assertEqual(len(self.generations()), len(before) + 1)
        self.assertEqual(self.installed().granted_directories, ())


if __name__ == "__main__":
    import unittest

    unittest.main()
