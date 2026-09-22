"""A number in a debt row nobody recalculates is a claim that goes false alone.

`docs/arquitectura/arquitectura.md` carries a debt row about `apply_patch`
arriving with every agent that can edit. It counted those agents in Spanish
prose -- "todo agente con `edit` o `write` --los trece--" -- and the day
`darq-implementer` shipped there were fourteen. Nothing said so. The same
registry had already been bitten once the same way: the row about published
releases claimed 33 tags when there were 51, and it only came out when somebody
counted by hand.

Two things fix it and only the second is a guard. The row's CLAIM is now the
rule -- every agent this product grants `edit` or `write` to -- which stays true
whatever the count is. The figure survives beside it because scale is useful to
a reader, and it is the figure this file holds honest, derived from the content
tree the way the rest of this suite derives its facts rather than retyped here
as a list of agent names.

The derivation goes through `render._tools`, not through the frontmatter: what
reaches the runtime is the rendered tool map, and that map is what the debt is
about. If a future agent gains editing through some other field, the count moves
with it and the row has to move too.

The prose itself is deliberately NOT pattern-matched. The only things read out
of the document are a bolded figure and a fenced command -- both machine-shaped
tokens somebody has to edit on purpose -- plus one negative check that the count
has not crawled back into the sentence as a Spanish number word, which is the
exact form the stale claim took.

The same row now also names a MECHANISM: the bundled OpenCode plugin that
appends a scope paragraph to `apply_patch`'s own description, which is the
strongest mitigation this debt has because it corrects the misreading on the
channel the misread sentence travels on. A named mechanism goes stale the same
way a figure does, so it gets the same treatment:
`ApplyPatchScopeIsCorrectedOnTheToolChannelTest` finds that plugin in the tree
BY WHAT IT DOES -- the one bundled plugin that registers the hook writing a tool
definition's description and narrows itself to `apply_patch` -- and requires the
row to name that file. Rename it and this says which document has to follow;
delete it and the row's claim fails the day it stops being true.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from darq.adapters.opencode import adapter as adapter_module
from darq.adapters.opencode import render as render_module
from darq.core import content as content_module

REPOSITORY = Path(__file__).resolve().parents[1]
ARCHITECTURE = REPOSITORY / "docs" / "arquitectura" / "arquitectura.md"

#: Where the bundled OpenCode plugins live, derived from the adapter module's
#: own location rather than retyped as a path this file would have to be told
#: about twice.
PLUGIN_ASSETS = Path(adapter_module.__file__).resolve().parent / "assets" / "plugins"

#: What makes a plugin the one this row is about: it registers the single hook
#: that writes the description shipped with a tool definition, and it narrows
#: itself to `apply_patch`. Both are the plugin's own load-bearing literals,
#: already fixed by `test_the_apply_patch_scope_plugin_declares_its_hook_and_
#: guards_the_tool_id` in `tests/test_opencode_adapter.py`.
CORRECTS_THE_TOOL_DESCRIPTION = ('"tool.definition"', 'input.toolID !== "apply_patch"')

#: The debt row, found by a literal it quotes from the runtime's own source.
#: Technical, unique, and not something a rewording of the Spanish moves.
ROW_ANCHOR = 'const edits = ["edit", "write", "apply_patch"]'

#: The figure, as a bolded count of agents.
FIGURE = re.compile(r"\*\*(\d+) agentes\*\*")

#: Where the figure is measured. The published-releases row names a `git`
#: command; a shell one-liner cannot be quoted inside a Markdown table cell here
#: (the alternation this measurement needs is a `|`, which splits the cell), so
#: the row names the guard instead -- exactly the way it already names
#: `ApplyPatchPermissionFoldTest` two sentences later. Both strings below are
#: derived from this module rather than retyped, so renaming either one fails
#: here and says which document has to follow.
GUARD_MODULE = Path(__file__).relative_to(Path(__file__).resolve().parents[1]).as_posix()

#: The shape the stale claim took: the count written out as a Spanish word, where
#: nothing can compare it to anything. Any of these inside the row means the
#: number has crawled back into the prose.
COUNTED_IN_PROSE = re.compile(
    r"\b(?:diez|once|doce|trece|catorce|quince|diecis[eé]is|diecisiete)\b", re.IGNORECASE
)


def the_debt_row() -> str:
    """The one table row this file is about."""
    rows = [
        line
        for line in ARCHITECTURE.read_text(encoding="utf-8").splitlines()
        if ROW_ANCHOR in line
    ]
    return rows[0] if len(rows) == 1 else ""


def plugins_correcting_the_apply_patch_description() -> list[str]:
    """Every bundled plugin that amends what `apply_patch` tells the model.

    Found by behaviour, never by filename: the day somebody renames the file the
    set follows it and the document is told, and the day somebody deletes the
    mechanism the set empties and the row stops being able to claim it.
    """
    return sorted(
        candidate.relative_to(REPOSITORY).as_posix()
        for candidate in PLUGIN_ASSETS.glob("*.ts")
        if all(token in candidate.read_text(encoding="utf-8") for token in CORRECTS_THE_TOOL_DESCRIPTION)
    )


def agents_granted_editing() -> set[str]:
    """Every shipped agent whose RENDERED tool map turns `edit` or `write` on.

    Derived, never listed: `render._tools` is the same function the adapter
    calls, so this counts what the runtime is actually handed.
    """
    editing = {render_module.TOOL_NAME[name] for name in ("edit", "write")}
    return {
        agent.name
        for agent in content_module.load().agents
        if any(render_module._tools(agent).get(name) for name in editing)
    }


class ApplyPatchReachesEveryEditingAgentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.row = the_debt_row()
        cls.granted = agents_granted_editing()
        cls.all_agents = {agent.name for agent in content_module.load().agents}

    def test_the_debt_row_is_found_exactly_once(self):
        """Everything below reads this row; two of them, or none, proves nothing."""
        self.assertTrue(self.row, f"no single row in {ARCHITECTURE.name} quotes {ROW_ANCHOR}")

    def test_the_derivation_is_not_vacuous(self):
        """It must be a real subset: neither every agent nor none of them, or the
        figure it holds honest would be a constant dressed up as a measurement."""
        self.assertLess(len(self.granted), len(self.all_agents))
        self.assertGreater(len(self.granted), 1)
        self.assertNotIn("darq-verifier", self.granted)
        self.assertIn("darq-implementer", self.granted)

    def test_the_row_states_the_figure_exactly_once(self):
        self.assertEqual(
            len(FIGURE.findall(self.row)),
            1,
            "the row must state its agent count once, as a bolded figure",
        )

    def test_the_figure_in_the_row_is_the_count_the_tree_yields(self):
        """The whole point. `darq-implementer` shipped and the row said
        thirteen; if that happens again this fails on the same day."""
        stated = FIGURE.search(self.row)
        self.assertIsNotNone(stated, "the row states no agent count at all")
        self.assertEqual(
            int(stated.group(1)),
            len(self.granted),
            f"the row's figure disagrees with the tree: {sorted(self.granted)}",
        )

    def test_the_row_says_where_the_figure_is_measured(self):
        """A figure without its measurement is the state this row was already in.

        Both names come from this module, never from a literal typed twice: a
        rename fails here and names the document that has to follow."""
        self.assertIn(f"`{type(self).__name__}`", self.row)
        self.assertIn(f"`{GUARD_MODULE}`", self.row)

    def test_the_count_does_not_live_in_the_prose(self):
        """"Los trece" was unfalsifiable: no number to compare, no way to notice.
        A spelled-out count is that defect coming back."""
        found = COUNTED_IN_PROSE.findall(self.row)
        self.assertEqual(found, [], f"the row counts agents in prose again: {found}")


class ApplyPatchScopeIsCorrectedOnTheToolChannelTest(unittest.TestCase):
    """The row names a mechanism, so the mechanism has to be there.

    The row's own reason for naming it: text that ships with the tool
    definitions outweighs text that ships as a prompt, which is why two
    prompt-side attempts did not stop the refusal and a `tool.definition` hook
    did. A row that kept claiming that after the plugin was renamed or dropped
    would be the same defect as the stale count, in prose instead of digits.
    """

    @classmethod
    def setUpClass(cls):
        cls.row = the_debt_row()
        cls.correcting = plugins_correcting_the_apply_patch_description()
        cls.bundled = sorted(path.name for path in PLUGIN_ASSETS.glob("*.ts"))

    def test_the_derivation_is_not_vacuous(self):
        """Exactly one plugin may answer to this, and it must not be every
        plugin: a filter that matched the whole directory would be naming the
        directory, not the mechanism."""
        self.assertTrue(self.bundled, f"no bundled plugin found under {PLUGIN_ASSETS}")
        self.assertEqual(
            len(self.correcting),
            1,
            f"exactly one bundled plugin writes `apply_patch`'s description: {self.correcting}",
        )
        self.assertLess(len(self.correcting), len(self.bundled))

    def test_the_row_names_the_plugin_that_carries_the_correction(self):
        """The claim and its mechanism, kept in the same place."""
        self.assertIn(
            self.correcting[0],
            self.row,
            f"the row must name the plugin that makes its claim true: {self.correcting[0]}",
        )

    def test_the_row_says_where_that_claim_is_held_honest(self):
        """Same shape as the figure two tests up: the row names its guard, and
        the name comes from this module rather than a literal typed twice."""
        self.assertIn(f"`{type(self).__name__}`", self.row)
        self.assertIn(f"`{GUARD_MODULE}`", self.row)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
