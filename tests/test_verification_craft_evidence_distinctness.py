"""A named split is a claim about what ran, not proof of it.

In a real session an `sdd-apply` agent reported that it had split its tests
into three scenario groups and run each one. Verification later found that
the selectors it used only changed the NAMES printed in the output: one group
of tests ran three times under three different labels, while the other two
scenarios were never exercised at all. The report was true about the labels
and false about the work, and it cost two full re-implementation rounds
before the gap was caught.

`verification-craft.md` already says "Execute relevant tests; static analysis
alone is never verification," but it says nothing about what to do when the
same execution is reported under several names. This module pins the fix: a
sentence naming the general failure (identical runs under different labels
are one run), and, separately, the imperative telling a verifier what to do
about it (resolve each claimed group to what it actually ran, not to its
label, before crediting it).

The two are pinned as separate assertions on purpose. This codebase has lost
a guard this shape before by checking only the diagnosis sentence and never
the order itself, so deleting the one actual instruction left every assertion
green (`tests/test_sub_delegation_scope.py`'s
`test_the_order_itself_is_pinned_not_only_its_diagnosis`, and the more recent
`tests/test_strict_tdd_red_evidence.py`, are the established precedent).
"""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CRAFT = ROOT / "src" / "darq" / "content" / "skills" / "_shared" / "verification-craft.md"

#: The diagnosis: what makes a report's named groups unreliable on their own.
#: Explains the failure but orders nothing.
DIAGNOSIS = "the names are a claim, not the evidence"

#: The imperative itself: what a verifier must actually do before crediting a
#: claimed split. Proven by deletion: removing only this sentence and leaving
#: the diagnosis above intact must turn this test red while the diagnosis
#: test stays green.
IMPERATIVE = (
    "resolve every claimed group to the actual command or selector it ran, "
    "never to the label attached to it"
)

#: The second half of the imperative: what to do once two groups resolve to
#: the same selection. Without this, a verifier could resolve the selectors
#: and still not know what follows from finding a match.
CREDIT_RULE = "credit only the first execution and treat the rest as not executed"


def read() -> str:
    return CRAFT.read_text(encoding="utf-8")


class DistinctExecutionTest(unittest.TestCase):
    def setUp(self):
        self.text = read()
        self.collapsed = " ".join(self.text.split())

    def test_the_file_exists_and_is_still_phase_less(self):
        self.assertTrue(CRAFT.is_file())
        self.assertIn("An agent with no SDD context can", self.text)

    def test_the_diagnosis_names_the_general_failure(self):
        """A description, not an order: identical runs under different labels
        are one run, and the names alone do not prove otherwise."""
        self.assertIn(DIAGNOSIS, self.collapsed)

    def test_the_imperative_is_pinned_not_only_its_diagnosis(self):
        """The actual order a verifier must follow, independent of the
        sentence that merely explains why it matters."""
        self.assertIn(IMPERATIVE, self.collapsed)
        self.assertIn(CREDIT_RULE, self.collapsed)

    def test_executed_evidence_strength_is_tied_to_distinctness(self):
        """The general rule the whole section hangs on, stated once as a
        principle so it reads as general craft rather than as one incident's
        post-mortem."""
        self.assertIn(
            "Executed evidence is only as strong as the distinctness of what executed",
            self.collapsed,
        )


if __name__ == "__main__":
    unittest.main()
