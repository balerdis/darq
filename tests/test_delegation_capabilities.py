"""A delegating agent needs to know what its target can actually do.

An incident showed the gap: `pegasus-orchestrator` sent git shell commands to
`pegasus-explorer` when it had no `bash` tool, then a browser-measurement brief
to an agent with no Playwright MCP. Nothing told the delegator what the target
could actually reach, so it wrote a brief demanding capabilities the target
never had.

The fix is one generated reference -- every delegation target's real tools and
MCP reach, derived from the content core after `select_mcp`/`grant_mcp` have
already pruned and granted -- plus a one-line lazy-load pointer in the body of
every agent that delegates to someone other than itself. This module proves
five things about that fix:

1. The file is DERIVED from `Content`, not a hand-typed table that merely
   happens to agree with it today.
2. It respects MCP pruning: a server the user did not select never appears.
3. Every agent whose `may_delegate_to` names someone other than itself
   carries the pointer, and no agent that only delegates to itself does.
4. The pointer path a body references and the path the artifact is actually
   written at are the same path, derived from one source rather than two
   hand-typed literals that could drift apart.
5. No unsubstituted `{{` placeholder survives into a rendered body.
"""
from __future__ import annotations

import dataclasses
import unittest
from pathlib import Path, PurePosixPath

from pegasus import cli
from pegasus.adapters.opencode import Adapter
from pegasus.core import catalog as catalog_module
from pegasus.core import content as content_module
from pegasus.core.content import Agent, AgentMode, Content, Distribution, Mcp
from pegasus.core.types import Environment, FileArtifact

ROOT = Path(__file__).resolve().parents[1]
AGENTS_DIR = ROOT / "src" / "pegasus" / "content" / "agents"

HOME = Path("/home/probe")
ENVIRONMENT = Environment(home=HOME, data_dir=HOME / ".local" / "share" / "pegasus-harness")
IDENTITY = cli.default_identity()

#: Today's shipped set, pinned as a drift guard: a seventh delegating agent
#: added tomorrow must fail this pin until its body carries the pointer too.
EXPECTED_QUALIFYING_AGENTS = frozenset(
    {
        "king-pegasus",
        "pegasus-general",
        "pegasus-implementer",
        "pegasus-orchestrator",
        "sdd-explore",
        "sdd-verify",
    }
)


def _agent(name, *, may_delegate_to=(), requires_tools=(), optional_tools=(), optional_mcp=(), granted_mcp=()):
    return Agent(
        name=name,
        description="d",
        body="Body.\n",
        mode=AgentMode.PRIMARY if not may_delegate_to else AgentMode.SUBAGENT,
        source=PurePosixPath(f"agents/{name}.md"),
        requires_tools=requires_tools,
        optional_tools=optional_tools,
        optional_mcp=optional_mcp,
        granted_mcp=granted_mcp,
        may_delegate_to=may_delegate_to,
    )


def _mcp(name, *, withheld_tools=(), bound_to=None, reaches=()):
    """A minimal `remote`-shaped descriptor -- `remote` needs no dependencies
    directory or version to render, so this fixture stays free of unrelated
    machinery; only `withheld_tools`/`bound_to` matter to this file's rendering."""
    return Mcp(
        name=name,
        description="d",
        body="Body.\n",
        distribution=Distribution.REMOTE,
        endpoint="https://example.invalid/mcp",
        source=PurePosixPath(f"mcp/{name}.md"),
        withheld_tools=withheld_tools,
        bound_to=bound_to,
        reaches=reaches,
    )


def _root_agent(may_delegate_to):
    """A default (session-starting) primary agent naming `may_delegate_to`."""
    return Agent(
        name=content_module.SESSION_STARTS_IN,
        description="d",
        body="Body.\n",
        mode=AgentMode.PRIMARY,
        source=PurePosixPath("agents/root.md"),
        may_delegate_to=may_delegate_to,
    )


def _generated_text(content):
    """Render the real adapter's whole catalog and return the generated file's text."""
    catalog_artifacts = _artifacts_for(content)
    match = _find_delegation_artifact(catalog_artifacts)
    return match.content.decode("utf-8")


def _artifacts_for(content):
    layout = Adapter().layout(ENVIRONMENT)
    orchestrator_name = catalog_module._orchestrator_name(content)
    return catalog_module.render(content, Adapter(), ENVIRONMENT, IDENTITY), layout, orchestrator_name


def _find_delegation_artifact(rendered):
    artifacts, layout, _ = rendered
    expected_path = layout.skills_dir / content_module.delegation_capabilities_path()
    for artifact in artifacts:
        if isinstance(artifact, FileArtifact) and artifact.path == expected_path:
            return artifact
    raise AssertionError("no delegation-capabilities artifact was rendered at the expected path")


class TheFileIsDerivedNotASnapshotTest(unittest.TestCase):
    """Mutate a target's declared capabilities and watch the generated file follow."""

    def _content_with(self, target_agent):
        return Content(agents=(_root_agent(("target",)), target_agent))

    def test_a_tool_or_mcp_added_to_the_target_shows_up_in_the_generated_file(self):
        before = self._content_with(
            _agent("target", requires_tools=("read", "bash"), optional_mcp=("alpha",))
        )
        before_text = _generated_text(before)
        self.assertIn("alpha", before_text)
        self.assertNotIn("beta", before_text)
        self.assertIn("bash", before_text)

        after_agent = dataclasses.replace(
            before.agents[1],
            optional_mcp=("alpha", "beta"),
            requires_tools=("read", "bash", "grep"),
        )
        after = Content(agents=(before.agents[0], after_agent))
        after_text = _generated_text(after)

        self.assertIn("beta", after_text)
        self.assertIn("grep", after_text)
        self.assertNotEqual(before_text, after_text)

    def test_a_target_dropped_from_every_may_delegate_to_disappears_from_the_file(self):
        content = self._content_with(_agent("target", requires_tools=("read",)))
        with_target = _generated_text(content)
        self.assertIn("`target`", with_target)

        no_delegation = Content(agents=(_root_agent(()), content.agents[1]))
        without_target = _generated_text(no_delegation)
        self.assertNotIn("`target`", without_target)


class RespectsMcpPruningTest(unittest.TestCase):
    """A server the user never selected must never be advertised as reachable."""

    def test_a_deselected_server_does_not_appear_anywhere_in_the_generated_file(self):
        full_content = content_module.load()
        # `jira` reaches `pegasus-explorer`, a real delegation target, in the
        # shipped content -- see `src/pegasus/content/mcp/jira.md`. Selecting
        # only `context7` must prune it away before this file is ever built.
        selected = content_module.select_mcp(full_content, ["context7"])
        still_optional = {mcp_id for agent in selected.agents for mcp_id in agent.optional_mcp}
        self.assertNotIn("jira", still_optional, "fixture drifted: selection did not prune jira")

        text = _generated_text(selected)
        self.assertNotIn("jira", text)


class CoverageIsDerivedTest(unittest.TestCase):
    """Every real delegator gets the pointer; a self-only delegator never does."""

    @classmethod
    def setUpClass(cls):
        cls.content = content_module.load()
        cls.pointer = f"{{{{skills_root}}}}/{content_module.delegation_capabilities_path().as_posix()}"

    def _qualifying_agents(self):
        return {
            agent.name
            for agent in self.content.agents
            if any(target != agent.name for target in agent.may_delegate_to)
        }

    def test_the_derived_qualifying_set_is_exactly_todays_six_agents(self):
        self.assertEqual(self._qualifying_agents(), set(EXPECTED_QUALIFYING_AGENTS))

    def test_every_qualifying_agent_carries_the_pointer(self):
        qualifying = self._qualifying_agents()
        for agent in self.content.agents:
            body_text = (AGENTS_DIR / f"{agent.name}.md").read_text(encoding="utf-8")
            with self.subTest(agent=agent.name):
                if agent.name in qualifying:
                    self.assertIn(self.pointer, body_text, f"{agent.name} delegates but lacks the pointer")
                else:
                    self.assertNotIn(
                        self.pointer, body_text, f"{agent.name} does not delegate but carries the pointer"
                    )


class PointerAndArtifactPathsAgreeTest(unittest.TestCase):
    """The path a body references and the path the artifact lands at must be one path."""

    def test_the_referenced_path_matches_where_the_artifact_is_actually_written(self):
        content = content_module.load()
        artifacts, layout, _ = _artifacts_for(content)
        artifact = _find_delegation_artifact((artifacts, layout, None))
        expected_pointer = f"{{{{skills_root}}}}/{content_module.delegation_capabilities_path().as_posix()}"

        orchestrator_body = (AGENTS_DIR / "pegasus-orchestrator.md").read_text(encoding="utf-8")
        self.assertIn(expected_pointer, orchestrator_body)
        # The artifact really exists at the exact path the pointer names, relative to
        # the layout's own skills root -- not two hand-typed strings that merely agree.
        self.assertEqual(artifact.path, layout.skills_dir / content_module.delegation_capabilities_path())


class NoPlaceholderLeaksIntoAnyQualifyingBodyTest(unittest.TestCase):
    """Every rendered qualifying body must be fully substituted."""

    def test_no_unsubstituted_double_brace_survives_rendering(self):
        content = content_module.load()
        adapter = Adapter()
        layout = adapter.layout(ENVIRONMENT)
        by_name = {agent.name: agent for agent in content.agents}
        for name in EXPECTED_QUALIFYING_AGENTS:
            with self.subTest(agent=name):
                agent = by_name[name]
                rendered = adapter.render_prompt(layout, agent)[0].content.decode("utf-8")
                self.assertNotIn("{{", rendered)


class WithheldToolsSurfaceInTheTableTest(unittest.TestCase):
    """A server with `withheld_tools` must show them in the generated table.

    Every expectation here reads the descriptor's own `withheld_tools`
    (never a hardcoded literal like `"cbm_delete_project"`), so a future
    change to which tools a server withholds keeps this test honest instead
    of it quietly proving nothing.
    """

    def _content_with_withheld(self, withheld_tools):
        server = _mcp("alpha", withheld_tools=withheld_tools)
        target = _agent("target", requires_tools=("read",), optional_mcp=("alpha",))
        return Content(agents=(_root_agent(("target",)), target), mcp=(server,))

    def test_a_withheld_tool_named_by_the_descriptor_appears_in_the_row(self):
        withheld_tools = ("delete_project", "ingest_traces")
        content = self._content_with_withheld(withheld_tools)
        text = _generated_text(content)
        for tool in withheld_tools:
            with self.subTest(tool=tool):
                self.assertIn(tool, text, f"withheld tool {tool!r} is missing from the generated table")

    def test_a_server_with_no_withheld_tools_names_none(self):
        content = self._content_with_withheld(())
        text = _generated_text(content)
        self.assertNotIn("delete_project", text)

    def test_a_bound_key_containing_an_underscore_is_not_misparsed(self):
        """`denied_mcp_tools` is `<key>_<tool>`; a key that itself contains an
        underscore (a realistic bound key, e.g. `my_alpha`) must still be
        matched by its exact resolved key, never by splitting the qualified
        string on the first or last underscore."""
        server = _mcp("alpha", withheld_tools=("delete_project",), bound_to="my_alpha")
        target = _agent("target", requires_tools=("read",), optional_mcp=("my_alpha",))
        content = Content(agents=(_root_agent(("target",)), target), mcp=(server,))
        text = _generated_text(content)
        self.assertIn("delete_project", text)
        self.assertIn("my_alpha", text)


class WithheldToolsAreDerivedNotSnapshottedTest(unittest.TestCase):
    """Prove the withheld-tools column tracks the descriptor, not a fixed string.

    Mutation run: start from the real shipped content, select only `cbm`
    (whose descriptor declares `withheld_tools: [delete_project,
    ingest_traces]` and reaches `pegasus-explorer`, a real delegation
    target), render, and observe both withheld tools present. Then mutate
    the in-memory `cbm` descriptor's `withheld_tools` to a different pair of
    made-up names and re-render: the old names must disappear and the new
    ones must appear -- proof the table is computed from the descriptor on
    every render, not cached or hand-typed.
    """

    def test_mutating_withheld_tools_changes_the_rendered_row(self):
        content = content_module.load()
        selected = content_module.select_mcp(content, ["cbm"])
        before_text = _generated_text(selected)
        self.assertIn("delete_project", before_text)
        self.assertIn("ingest_traces", before_text)
        self.assertNotIn("mutated_tool_one", before_text)

        mutated_mcp = tuple(
            dataclasses.replace(server, withheld_tools=("mutated_tool_one", "mutated_tool_two"))
            if server.name == "cbm"
            else server
            for server in selected.mcp
        )
        mutated = dataclasses.replace(selected, mcp=mutated_mcp)
        after_text = _generated_text(mutated)

        self.assertNotIn("delete_project", after_text)
        self.assertNotIn("ingest_traces", after_text)
        self.assertIn("mutated_tool_one", after_text)
        self.assertIn("mutated_tool_two", after_text)
        self.assertNotEqual(before_text, after_text)


if __name__ == "__main__":
    unittest.main()
