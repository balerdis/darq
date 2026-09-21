"""A count of shipped things, typed into the manual by hand, goes false alone.

`MANUAL.md` explains what happens when a key a person granted themselves
collides with the same key a later release ships. It said `mcp grant` "alcanza
a los trece agentes" and that a person's "alcance baja de trece agentes a
ocho". Both halves of that were broken, in the two different ways a
hand-written figure breaks:

* `grant_mcp` never reached thirteen agents. It reaches EVERY agent -- it is a
  single `replace(agent, granted_mcp=kept)` over `content.agents`, with no
  filter of any kind -- so the sentence named a subset where there is none.
* Thirteen was also simply out of date; the tree ships sixteen. It is the same
  stale figure `tests/test_architecture_debt_figures.py` was written for, in a
  second document, and it went stale the same silent way.

So this file is that one's sibling, and deliberately the same shape. The
paragraph's CLAIM is now the rule -- every agent, whatever the number -- which
stays true as agents come and go. The figures survive beside it because scale
is what a reader is actually asking for, and they are derived here: the whole
count from the content tree, the narrowed one from the shipped descriptor's own
`reaches` list.

The rule is proven by RUNNING `grant_mcp`, never by reading it. "Every agent"
is a claim about what the function does to a real content tree, and a guard
that matched the source for the absence of a filter would be approving by a
proxy: it would stay green the day somebody adds one.

The prose around the figures is deliberately NOT pattern-matched. What is read
out of the document is a bolded figure and the names of this module and this
class -- machine-shaped tokens somebody has to edit on purpose -- plus one
negative check that a count has not crawled back into the sentence as a Spanish
number word, which is the exact form the stale claim took.
"""
from __future__ import annotations

import io
import json
import re
import tomllib
import unittest
from pathlib import Path

import pegasus
from pegasus import cli
from pegasus.adapters import available
from pegasus.core import content as content_module
from pegasus.core.types import Environment
from pegasus.infra.fs_posix import PosixFileSystem
from real_home import RealHomeTestCase

REPOSITORY = Path(__file__).resolve().parents[1]
MANUAL = REPOSITORY / "MANUAL.md"

#: The paragraph, found by a literal it quotes from the product's own report
#: payload. Technical, unique, and not something a rewording of the Spanish
#: moves.
PARAGRAPH_ANCHOR = "grant_warnings"

#: The server key the manual's own example collides on. Named here because the
#: example is about a specific shipped server, and asserted below to still be
#: one and to still be the key the paragraph talks about.
EXAMPLE_KEY = "jira"

#: The other server the paragraph leans on to describe that reach in words
#: ("los mismos que llevan Context7"). The day the two stop agreeing, the
#: sentence is false even though its figure is right.
COMPANION_KEY = "context7"

#: A figure, as a bolded count of agents.
FIGURE = re.compile(r"\*\*(\d+) agentes\*\*")

#: This module and its guard, derived rather than retyped, so renaming either
#: fails here and names the document that has to follow.
GUARD_MODULE = Path(__file__).relative_to(REPOSITORY).as_posix()

#: The shape the stale claim took: a count written out as a Spanish word, where
#: nothing can compare it to anything.
COUNTED_IN_PROSE = re.compile(
    r"\b(?:seis|siete|ocho|nueve|diez|once|doce|trece|catorce|quince|diecis[eé]is|"
    r"diecisiete|dieciocho|diecinueve|veinte)\b",
    re.IGNORECASE,
)


def the_collision_paragraph() -> str:
    """The one paragraph of the manual this file is about."""
    lines = [
        line
        for line in MANUAL.read_text(encoding="utf-8").splitlines()
        if PARAGRAPH_ANCHOR in line
    ]
    return lines[0] if len(lines) == 1 else ""


def agents_reached_by(key: str) -> frozenset[str]:
    """Every agent a shipped server's own descriptor reaches.

    Read off `reaches`, which is where that fact lives now: `optional_mcp` is
    derived from these lists, so this is the same set the render works from.
    """
    server = next((item for item in content_module.load().mcp if item.name == key), None)
    return frozenset(server.reaches) if server is not None else frozenset()


class GrantMcpReachesEveryAgentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paragraph = the_collision_paragraph()
        cls.content = content_module.load()
        cls.all_agents = {agent.name for agent in cls.content.agents}
        cls.narrowed = agents_reached_by(EXAMPLE_KEY)

    def test_the_paragraph_is_found_exactly_once(self):
        """Everything below reads this paragraph; two of them, or none, proves
        nothing."""
        self.assertTrue(
            self.paragraph, f"no single line of {MANUAL.name} quotes {PARAGRAPH_ANCHOR}"
        )

    def test_granting_a_key_reaches_every_single_agent(self):
        """The rule the paragraph now states, run rather than read.

        A source-level check for "no filter" would keep passing the day a
        filter appears. This grants a key against the real content tree and
        looks at what every agent came back holding."""
        granted, dropped = content_module.grant_mcp(self.content, ("a-key-of-your-own",))
        self.assertEqual(dropped, ())
        reached = {
            agent.name for agent in granted.agents if "a-key-of-your-own" in agent.granted_mcp
        }
        self.assertEqual(reached, self.all_agents)

    def test_the_narrowed_reach_is_a_real_subset(self):
        """Or the paragraph would be describing a narrowing that is not one,
        and its second figure would be the first one in disguise."""
        self.assertTrue(self.narrowed, f"{EXAMPLE_KEY} is not a shipped server any more")
        self.assertLess(len(self.narrowed), len(self.all_agents))
        self.assertTrue(self.narrowed < self.all_agents)

    def test_the_paragraph_still_talks_about_the_server_measured_here(self):
        """The example is about one key; measuring another would be measuring
        something the reader was never told about."""
        self.assertIn(f"`{EXAMPLE_KEY}`", self.paragraph)

    def test_the_narrowed_reach_is_the_one_the_paragraph_describes_in_words(self):
        """The paragraph names that set as the agents carrying Context7. The
        figure can be right while that sentence has gone false, so the two sets
        are compared and not just their sizes."""
        self.assertEqual(self.narrowed, agents_reached_by(COMPANION_KEY))

    def test_the_paragraph_states_both_figures_exactly_once_each(self):
        stated = FIGURE.findall(self.paragraph)
        self.assertEqual(
            len(stated),
            2,
            "the paragraph must state its two agent counts once each, as bolded figures",
        )

    def test_the_figures_are_the_counts_the_tree_yields(self):
        """The whole point. It said thirteen where the tree said sixteen, and
        nothing anywhere noticed."""
        stated = [int(value) for value in FIGURE.findall(self.paragraph)]
        self.assertEqual(
            stated,
            [len(self.all_agents), len(self.narrowed)],
            f"the paragraph's figures disagree with the tree: "
            f"{len(self.all_agents)} agents, {sorted(self.narrowed)} reached by {EXAMPLE_KEY}",
        )

    def test_the_paragraph_says_where_the_figures_are_measured(self):
        """A figure without its measurement is the state this paragraph was
        already in. Both names come from this module, never from a literal
        typed twice."""
        self.assertIn(f"`{type(self).__name__}`", self.paragraph)
        self.assertIn(f"`{GUARD_MODULE}`", self.paragraph)

    def test_no_count_lives_in_the_prose(self):
        """"Los trece" was unfalsifiable: no number to compare, no way to
        notice. A spelled-out count is that defect coming back."""
        found = COUNTED_IN_PROSE.findall(self.paragraph)
        self.assertEqual(found, [], f"the paragraph counts in prose again: {found}")


#: The entry-point paragraph, found by the tree's own name for the artifact it
#: builds. `zipapp` is what `tools/build_zipapp.py` produces and what the
#: architecture registry calls it -- machine-shaped, and not a word a rewording
#: of the Spanish moves.
ENTRY_POINT_ANCHOR = "zipapp"

#: A product major, as the manual spells one.
PRODUCT_MAJOR = re.compile(r"\bPegasus (\d+)\b")

#: The mechanisms the 4.x entry point was made of. Every one of them was
#: retired whole when the package lost its last dependency (see the dissolved
#: debt in `docs/arquitectura/arquitectura.md`), so a user manual that still
#: names one is describing a product that is not there -- which is exactly the
#: state this paragraph was found in, promising a venv at
#: `$XDG_DATA_HOME/pegasus-harness/venv` and a launcher on the PATH. Retyped
#: here because a thing that no longer exists leaves nothing in the tree to
#: derive its name from; that is the whole reason the claim could go stale
#: unnoticed.
RETIRED_ENTRY_POINT = re.compile(r"\bvenv\b|\bshim\b|\blanzador\b|pegasus setup", re.IGNORECASE)


def the_entry_point_paragraph() -> str:
    """The one paragraph of the manual that says what gets installed."""
    lines = [
        line
        for line in MANUAL.read_text(encoding="utf-8").splitlines()
        if ENTRY_POINT_ANCHOR in line
    ]
    return lines[0] if len(lines) == 1 else ""


def installed_destination() -> str:
    """Where this distribution's own binary lands, spelled the way a person
    reads it.

    Both halves come from the tree: the directory from the filesystem port
    that answers it (`bin_dir`, the same function `install.sh` and the manual
    installation both target), the file name from this binary's own identity.
    Neither is a literal typed twice.
    """
    identity = cli.default_identity()
    filesystem = PosixFileSystem(product_id=identity.product_id)
    return (filesystem.bin_dir(Path("~")) / identity.program_name).as_posix()


def declared_dependencies() -> list[str]:
    """What the package declares it needs, read off the project metadata."""
    document = tomllib.loads((REPOSITORY / "pyproject.toml").read_text(encoding="utf-8"))
    return list(document["project"]["dependencies"])


class ManualNamesTheEntryPointThisReleaseShipsTest(unittest.TestCase):
    """`MANUAL.md` opened by describing an entry point that was removed.

    It said Pegasus "es un paquete de Python que vive en un venv privado
    (`$XDG_DATA_HOME/pegasus-harness/venv` ...), con un lanzador `pegasus` en
    tu PATH", and three paragraphs later told the reader to work "con el venv
    ya armado". None of that exists: the package lost its last third-party
    dependency, a venv stopped isolating anything, and `pegasus setup`, the
    venv, the shim and `setup-sources/` were retired whole -- the entry point
    has been one executable `zipapp` since. Three other user documents were
    brought to that truth and this one was not, which is the same silent way
    a hand-typed figure goes stale: nothing anywhere compared the sentence to
    the tree.

    So the paragraph's CLAIM is now what the tree actually builds, and its
    figure -- the product major -- is derived here from `pegasus.__version__`
    rather than typed into the prose, the same treatment
    `GrantMcpReachesEveryAgentTest` gives its agent counts.

    What is NOT re-asserted here is that the built artifact really is one
    executable file with a shebang: `test_build_zipapp.BuildTest` already
    proves that against a real build, and repeating it would be a guard held
    up by another mechanism. What is missing until this file exists is the
    link -- that the document a person reads describes that artifact and not
    the one before it.

    The negative check is the same shape as `test_no_count_lives_in_the_prose`
    below: the stale claim took one specific form, naming mechanisms that are
    gone, and this fails the day one of those names comes back anywhere in the
    manual.
    """

    @classmethod
    def setUpClass(cls):
        cls.manual = MANUAL.read_text(encoding="utf-8")
        cls.paragraph = the_entry_point_paragraph()

    def test_the_paragraph_is_found_exactly_once(self):
        """Everything below reads this paragraph; two of them, or none, proves
        nothing."""
        self.assertTrue(
            self.paragraph, f"no single line of {MANUAL.name} names the {ENTRY_POINT_ANCHOR} it ships"
        )

    def test_the_major_the_manual_documents_is_the_major_the_tree_is(self):
        """The figure. It said four where the tree said five, in the sentence
        that told a reader which product this manual is even about."""
        major = pegasus.__version__.split(".")[0]
        stated = PRODUCT_MAJOR.findall(self.manual)
        self.assertTrue(stated, f"{MANUAL.name} never says which major of the product it documents")
        self.assertEqual(
            sorted(set(stated)),
            [major],
            f"{MANUAL.name} documents a major the tree is not: tree is {pegasus.__version__}",
        )

    def test_the_paragraph_names_where_the_binary_actually_lands(self):
        """A destination is the one fact a reader checks against their own
        machine, so it is derived from the port that answers it rather than
        quoted from a guide."""
        self.assertIn(installed_destination(), self.paragraph)

    def test_nothing_is_left_for_a_venv_to_isolate(self):
        """The paragraph's reason, not just its conclusion. It says there is no
        venv *because* there is nothing to isolate; the day the package
        declares a dependency that reason is gone, whatever the entry point
        still looks like."""
        self.assertEqual(
            declared_dependencies(),
            [],
            "the package now declares a dependency, so the manual's reason for having no venv is false",
        )

    def test_the_retired_entry_point_is_described_nowhere(self):
        """The exact form the stale claim took."""
        found = RETIRED_ENTRY_POINT.findall(self.manual)
        self.assertEqual(found, [], f"{MANUAL.name} still describes a retired entry point: {found}")

    def test_the_paragraph_says_where_its_figure_is_measured(self):
        """A figure without its measurement is the state this paragraph was
        already in. Both names come from this module, never from a literal
        typed twice."""
        self.assertIn(f"`{type(self).__name__}`", self.paragraph)
        self.assertIn(f"`{GUARD_MODULE}`", self.paragraph)



AT = "2026-08-14T00:00:00+00:00"
# Pinned to OpenCode, not "whichever adapter is registered first": this
# suite exercises capabilities (mcp, per_agent_model, subagents declared
# inside the settings file, ...) that only OpenCode declares today. Since
# Claude Code registered, "available().ids()[0]" resolves alphabetically
# to "claudecode" instead, which cannot support what this file tests.
CLI = "opencode"

#: A model a person could type. Nothing here renders it, so it only has to be
#: a shape `ModelAssignment.parse` accepts.
A_MODEL = "anthropic/claude-sonnet-5"

#: A name no release ships, to prove the acceptance measured below is the
#: product's own gate answering and not an absence of one.
NOT_AN_AGENT = "an-agent-nobody-ships"


def paragraph_naming(guard: str) -> str:
    """The one line of the manual that names ``guard``.

    Empty when there is not exactly one, so every assertion built on it fails
    loudly instead of proving something about nothing -- the same finder, and
    the same reason, as `tests/test_manual_command_surface.py`'s.
    """
    lines = [line for line in MANUAL.read_text(encoding="utf-8").splitlines() if f"`{guard}`" in line]
    return lines[0] if len(lines) == 1 else ""


class EveryShippedAgentAcceptsAModelAssignmentTest(RealHomeTestCase):
    """"Un agente configurable de la línea SDD" was a narrowing of a rule.

    Every agent this release ships is `model_configurable` -- the
    orchestrator, `king-pegasus` and the phase-less specialists included --
    so the sentence named a subset where there is none, the exact defect
    `GrantMcpReachesEveryAgentTest` was written for, in a second paragraph of
    the same document. A reader with a model to assign to their orchestrator
    read that they could not.

    So the paragraph's CLAIM is now the rule -- every agent, whatever the
    number -- and the figure survives beside it because scale is what a
    reader is actually asking for. It is derived here from the content tree,
    never typed into the prose.

    The rule is proven by RUNNING `models set` against every shipped agent
    and looking at what came back, never by reading `model_configurable` off
    the descriptors: the flag is not the claim, `_require_configurable_agent`
    is, and a guard that summed the flags would keep passing the day the two
    stop agreeing. A name no release ships is put through the same command so
    the acceptance is the gate answering and not the gate being gone.

    What is deliberately NOT here is a check that the sentence stops saying
    "SDD". Naming the SDD line is not false -- those agents are configurable
    too -- and a regex over that phrase would fail for the wrong reason the
    first time somebody legitimately mentions it. The count check below is
    the negative this paragraph can honestly carry, and it is the exact form
    the stale claim in its sibling took.
    """

    def setUp(self):
        super().setUp()
        self.content = content_module.load()
        self.agents = sorted(agent.name for agent in self.content.agents)
        self.paragraph = paragraph_naming(type(self).__name__)
        self.install()

    def run_cli(self, *argv) -> tuple[int, dict]:
        out = io.StringIO()
        context = cli.Runtime(filesystem=self.filesystem, home=self.home, now=AT, out=out)
        code = cli.main([*argv, "--json"], runtime=context)
        return code, json.loads(out.getvalue())

    def install(self) -> None:
        """A real installation under every assignment measured below.

        `models set` renders what it records, so it refuses a CLI with nothing
        installed. The claim this class holds is about which agents the
        command ACCEPTS, so an installation has to be there or every agent
        would be "refused" for a reason that has nothing to do with the
        paragraph.
        """
        layout = available().get(CLI).layout(Environment(home=self.home))
        layout.config_dir.mkdir(parents=True, exist_ok=True)
        code, _ = self.run_cli("install", "--cli", CLI)
        self.assertEqual(code, 0)

    def assign_to(self, agent: str) -> tuple[int, dict]:
        return self.run_cli("models", "set", "--cli", CLI, "--assign", f"{agent}={A_MODEL}")

    def test_the_release_ships_agents_to_measure(self):
        """Or every assertion below would pass over an empty list."""
        self.assertTrue(self.agents, "this release ships no agent at all")

    def test_every_shipped_agent_accepts_an_assignment(self):
        """The rule the paragraph now states, run rather than read."""
        refused = {}
        for agent in self.agents:
            code, report = self.assign_to(agent)
            if code != 0:
                refused[agent] = report.get("error")
        self.assertEqual(refused, {}, f"these agents refused a model assignment: {refused}")

    def test_a_name_this_release_does_not_ship_is_refused(self):
        """Or the acceptance above would prove only that nothing is checked."""
        code, report = self.assign_to(NOT_AN_AGENT)
        self.assertNotEqual(code, 0)
        self.assertIn(NOT_AN_AGENT, report["error"])

    def test_the_paragraph_is_found_exactly_once(self):
        """Everything below reads this paragraph; two of them, or none, proves
        nothing."""
        self.assertTrue(
            self.paragraph, f"no single line of {MANUAL.name} names {type(self).__name__}"
        )

    def test_the_paragraph_states_its_figure_exactly_once(self):
        self.assertEqual(
            len(FIGURE.findall(self.paragraph)),
            1,
            "the paragraph must state its agent count once, as a bolded figure",
        )

    def test_the_figure_is_the_count_the_tree_yields(self):
        stated = [int(value) for value in FIGURE.findall(self.paragraph)]
        self.assertEqual(
            stated,
            [len(self.agents)],
            f"the paragraph's figure disagrees with the tree: {len(self.agents)} agents",
        )

    def test_no_count_lives_in_the_prose(self):
        """A spelled-out count is a figure nothing can compare to anything --
        the shape the stale claim in this file's other paragraph took."""
        found = COUNTED_IN_PROSE.findall(self.paragraph)
        self.assertEqual(found, [], f"the paragraph counts in prose: {found}")

    def test_the_paragraph_says_where_its_figure_is_measured(self):
        """A figure without its measurement is the state this paragraph was
        already in. Both names come from this module, never from a literal
        typed twice."""
        self.assertIn(f"`{type(self).__name__}`", self.paragraph)
        self.assertIn(f"`{GUARD_MODULE}`", self.paragraph)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
