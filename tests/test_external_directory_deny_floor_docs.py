"""A directory name spelled by hand in two documents goes stale in silence.

`EXTERNAL_DIRECTORY_DENY_FLOOR` (`render.py`) is the one place that actually
decides which directories `external_directory`'s baseline flip cannot reach.
`MANUAL.md` and `docs/arquitectura/arquitectura.md` both explain that floor in
prose, and both spell out its five names by hand: `.ssh/`, `.aws/`,
`.credentials/`, `.config/gh/`, `secrets/`. Nothing tied those five words to
the dict they describe -- add a sixth entry to the floor and both documents
would keep claiming the old five, silently wrong the same way
`ApplyPatchReachesEveryEditingAgentTest` and `ManualSaysWhichMcpSubcommandsRewriteTheConfigurationTest`
were already bitten by a hand-typed figure that drifted from the tree.

This file checks BOTH directions, because one direction is exactly how this
repository was bitten before: every name the floor holds must appear in each
document (nothing added to the floor goes undocumented), and every name each
document claims is always-denied must actually be in the floor (nothing
claimed is aspirational or stale). A one-directional check would have let
either kind of drift through.

The name extracted from a floor pattern is the wildcard's own shape --
`f"*/{name}/*"` -- stripped of the two literal edges the loop below already
knows about (`*/` in front, `/*` behind), never retyped. The name extracted
from a document is a backtick-quoted, slash-terminated token from the one
paragraph or row that describes the floor, found by an anchor unique to that
prose rather than by scanning the whole document -- a floor-shaped token
appearing in an unrelated sentence elsewhere must never count.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from darq.adapters.opencode import render as render_module

REPOSITORY = Path(__file__).resolve().parents[1]
MANUAL = REPOSITORY / "MANUAL.md"
ARCHITECTURE = REPOSITORY / "docs" / "arquitectura" / "arquitectura.md"

#: The one line of `MANUAL.md` that spells out the floor's five names. Found
#: by a phrase unique to that sentence, not by the names themselves -- the
#: names are exactly what this file must not assume are already right.
MANUAL_ANCHOR = "deniega en su grafía canónica"

#: The one row of `arquitectura.md` that carries the same claim, found by the
#: constant it names -- unique to this row, and a rename of the constant
#: fails here rather than silently orphaning the row's own citation.
ARCHITECTURE_ANCHOR = "EXTERNAL_DIRECTORY_DENY_FLOOR"

#: A backtick-quoted, slash-terminated directory token, e.g. `` `.ssh/` `` or
#: `` `.config/gh/` ``. This is the shape both documents use to spell out the
#: floor's names, and the only shape read out of either one.
DOCUMENTED_DIRECTORY = re.compile(r"`((?:\.?[\w-]+/)+)`")


def floor_names() -> set[str]:
    """Every directory name the floor itself holds, derived from its keys.

    Each key is `f"*/{name}/*"`; stripping the two fixed edges is the same
    shape the dict comprehension in `render._permission` builds them with,
    never a second, independently-typed list of the same five words.
    """
    names = set()
    for pattern in render_module.EXTERNAL_DIRECTORY_DENY_FLOOR:
        assert pattern.startswith("*/") and pattern.endswith("/*"), pattern
        names.add(pattern[len("*/") : -len("/*")])
    return names


def the_manual_sentence() -> str:
    lines = [line for line in MANUAL.read_text(encoding="utf-8").splitlines() if MANUAL_ANCHOR in line]
    return lines[0] if len(lines) == 1 else ""


def the_architecture_row() -> str:
    lines = [
        line for line in ARCHITECTURE.read_text(encoding="utf-8").splitlines() if ARCHITECTURE_ANCHOR in line
    ]
    return lines[0] if len(lines) == 1 else ""


def documented_names(text: str) -> set[str]:
    """Every directory name a document spells out, stripped of its trailing
    slash so `.config/gh/` compares equal to the floor's own `.config/gh`."""
    return {token.rstrip("/") for token in DOCUMENTED_DIRECTORY.findall(text)}


class TheFloorAndBothDocumentsNameTheSameDirectoriesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.floor = floor_names()
        cls.manual_sentence = the_manual_sentence()
        cls.architecture_row = the_architecture_row()

    def test_the_manual_sentence_is_found_exactly_once(self):
        self.assertTrue(self.manual_sentence, f"no single line of {MANUAL.name} names the deny floor's directories")

    def test_the_architecture_row_is_found_exactly_once(self):
        self.assertTrue(
            self.architecture_row, f"no single row of {ARCHITECTURE.name} names {ARCHITECTURE_ANCHOR}"
        )

    def test_the_derivation_is_not_vacuous(self):
        """The floor must actually hold more than one name, or a set
        comparison below would pass by triviality rather than by agreement."""
        self.assertGreater(len(self.floor), 1)

    def test_every_floor_directory_is_named_in_the_manual(self):
        documented = documented_names(self.manual_sentence)
        missing = self.floor - documented
        self.assertFalse(missing, f"{MANUAL.name} does not name: {sorted(missing)}")

    def test_the_manual_names_no_directory_the_floor_does_not_hold(self):
        documented = documented_names(self.manual_sentence)
        extra = documented - self.floor
        self.assertFalse(extra, f"{MANUAL.name} claims always-denied directories the floor does not hold: {sorted(extra)}")

    def test_every_floor_directory_is_named_in_the_architecture_row(self):
        documented = documented_names(self.architecture_row)
        missing = self.floor - documented
        self.assertFalse(missing, f"{ARCHITECTURE.name} does not name: {sorted(missing)}")

    def test_the_architecture_row_names_no_directory_the_floor_does_not_hold(self):
        documented = documented_names(self.architecture_row)
        extra = documented - self.floor
        self.assertFalse(
            extra, f"{ARCHITECTURE.name} claims always-denied directories the floor does not hold: {sorted(extra)}"
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
