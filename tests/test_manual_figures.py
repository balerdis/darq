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

import re
import unittest
from pathlib import Path

from pegasus.core import content as content_module

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


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
