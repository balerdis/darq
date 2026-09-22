"""Reconnaissance is the missing upstream half of "a brief is compression in
the wrong direction".

Observed in a real session: `darq-orchestrator` decided to delegate and
wrote the brief without first establishing the facts that would make the
brief worth anything, so a subagent rediscovered what two targeted reads
would have settled. The Direct Work Threshold's file-count rule ("read up to
3 yourself, delegate 4 or more") is correct for reading in order to DO the
work; applying it to reading in order to KNOW WHAT TO ASK FOR is circular,
because delegating that exploration itself requires a brief, which is the
thing not yet known well enough to write.

The fix has to be decidable and bounded, or it becomes another "compress" --
a virtue word applied wherever a model likes. This module pins:

1.  The trigger itself (a yes/no question, answerable with zero tool calls),
    as an actual imperative -- not only the diagnosis that explains why it
    exists. Pinned separately in BOTH files, because both now carry a full,
    self-sufficient copy of the rule (see point 3). This codebase has been
    bitten three times by guards that pinned only explanatory prose and let
    the real order go unprotected (`tests/test_sub_delegation_scope.py`'s
    `test_the_order_itself_is_pinned_not_only_its_diagnosis`,
    `tests/test_strict_tdd_red_evidence.py`,
    `tests/test_verification_craft_evidence_distinctness.py`).
2.  The stop condition specifically -- reconnaissance ends the moment the
    brief can be written; it is never license to quietly do the work that
    was supposed to be handed out.
3.  DELIBERATE duplication, not restatement-by-reference. The first version
    of this change had `darq-orchestrator.md` point at
    `sub-delegation-criterion.md`'s reconnaissance rule with a WHEN clause
    borrowed from an unrelated invariant
    (`tests/test_content.py::test_the_criterion_reference_is_never_loaded_unconditionally`,
    which requires every line naming that file to carry "divides into
    genuinely independent parts" -- the fan-out loading condition). That
    borrowed clause was FALSE for reconnaissance: a single delegation never
    "divides into genuinely independent parts", so the rule was stated as
    conditional on a case that never holds for the very scenario the change
    exists to fix -- an orchestrator delegating ONE thing without having
    looked. The fix is the one already used in this codebase for a contract
    two audiences both need (`tests/test_phase_less_specialists.py`'s
    `WhatEachOneReturnsTest::test_each_contract_is_advertised_where_a_caller_reads_it_too`,
    "the one place a contract legitimately lives twice"): the orchestrator's
    bullet is now self-sufficient and never names the criterion file, and the
    criterion file keeps its own copy for the other delegating agents, who
    read it only when fan-out is already on the table. Two audiences, two
    loading conditions, restated on purpose rather than pointed at falsely.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "src" / "darq" / "content"
CRITERION = CONTENT / "skills" / "_shared" / "sub-delegation-criterion.md"
ORCHESTRATOR = CONTENT / "agents" / "darq-orchestrator.md"

#: The decidable trigger in the shared criterion file, worded for its own
#: audience (agents already fanning out several briefs at once).
CRITERION_TRIGGER = (
    "can I name the files the executor will touch, and the specific thing "
    "wrong or missing in each?"
)

#: The criterion file's actual order to look, bounded to the gap and nothing
#: wider. Proven by deletion: removing only this sentence and leaving the
#: trigger question and the value paragraph intact must turn this assertion
#: red while the diagnosis-only assertions stay green.
CRITERION_IMPERATIVE = "look only at it, nothing wider"

#: The criterion file's stop condition, pinned separately from the imperative
#: to look. Without this a rule that says "look before you delegate" has no
#: boundary, and reconnaissance becomes license to do the work yourself under
#: cover of "just checking a fact first".
CRITERION_STOP = "The moment you can name them, stop"
CRITERION_STOP_SCOPE = (
    "you are not reading to solve the problem, only to know enough to hand it off complete"
)

#: The orchestrator's own decidable trigger -- worded for ITS audience (a
#: single delegation decision, before any fan-out is even on the table), and
#: never sourced from the criterion file by reference.
ORCHESTRATOR_TRIGGER = "can I name the files the executor will touch and what is wrong in each?"

#: The orchestrator's own imperative: the gap, and nothing wider. Proven by
#: deletion the same way as the criterion file's copy.
ORCHESTRATOR_IMPERATIVE = "that gap is what you read for, nothing wider"

#: The orchestrator's own stop condition, pinned separately from the
#: imperative above.
ORCHESTRATOR_STOP = "until you can name them, then stop"

#: The circularity this bullet exists to name: applying the file-count rule
#: to reading-in-order-to-brief is circular, because writing that
#: exploration's own brief needs the very knowledge being sought.
ORCHESTRATOR_CIRCULARITY = "you cannot write the brief that spares you the reading"

#: Both files must agree reconnaissance sits at the SAME four-file line as
#: the existing delegate-a-narrow-exploration rule, not a second threshold.
SHARED_THRESHOLD_NUMBER = "four files"
ORCHESTRATOR_THRESHOLD_AGREEMENT = "four files or more to answer it is that same rule"
CRITERION_THRESHOLD_AGREEMENT = "that already IS the threshold in force elsewhere"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def orchestrator_reconnaissance_bullet(text: str) -> str:
    """The single physical line carrying the orchestrator's own reconnaissance
    bullet, isolated so a check for "does this bullet name the criterion
    file" cannot be confused by the UNRELATED, legitimate reference to that
    same file two bullets down (the concurrency bullet, gated correctly on
    "divides into genuinely independent parts")."""
    for line in text.splitlines():
        if line.strip().startswith("- Reading to decide what to delegate"):
            return line
    raise AssertionError("reconnaissance bullet not found in darq-orchestrator.md")


class ReconnaissanceCriterionTest(unittest.TestCase):
    """The general half: every fan-out agent writes briefs, so the rule that
    completes "a brief is compression in the wrong direction" belongs beside
    it in the shared criterion file, read only when fan-out is already on the
    table -- never eagerly, per the file's own Scope section."""

    def setUp(self):
        self.text = read(CRITERION)
        self.collapsed = " ".join(self.text.split())

    def test_the_file_still_owns_the_compression_section_this_completes(self):
        self.assertIn("A brief is compression in the wrong direction", self.text)

    def test_the_trigger_question_is_decidable_and_present(self):
        self.assertIn(CRITERION_TRIGGER, self.collapsed)

    def test_the_order_itself_is_pinned_not_only_its_diagnosis(self):
        """The trigger question and the value paragraph are both
        DESCRIPTION -- what the check is and what it buys. The section's
        actual COMMAND is a separate sentence telling the reader what to do
        when the answer is no. Deleting only that sentence must not leave
        every other assertion in this file still passing."""
        self.assertIn(CRITERION_IMPERATIVE, self.collapsed)

    def test_the_stop_condition_is_pinned_specifically(self):
        """A rule to look before delegating, with no boundary, is the exact
        failure the owner warned about: it licenses quietly doing the work
        instead of handing it out. This pins the boundary as its own
        sentence, distinct from the imperative to look."""
        self.assertIn(CRITERION_STOP, self.collapsed)
        self.assertIn(CRITERION_STOP_SCOPE, self.collapsed)

    def test_reconnaissance_is_bounded_below_the_shared_threshold(self):
        self.assertIn(SHARED_THRESHOLD_NUMBER, self.collapsed)
        self.assertIn(CRITERION_THRESHOLD_AGREEMENT, self.collapsed)

    def test_the_value_is_stated_concretely_not_as_inflation(self):
        """The owner asked for what it buys "concretely and without
        inflation" -- a claim tied to the evidence the brief supplied, not a
        vague virtue statement."""
        self.assertIn("deleted a planned signature change", self.collapsed)


class ReconnaissanceOrchestratorTest(unittest.TestCase):
    """The orchestrator-specific half: self-sufficient, because naming the
    criterion file here would force a WHEN clause ("divides into genuinely
    independent parts") that is false for a single delegation -- exactly the
    case this rule exists to fix. See the module docstring, point 3."""

    def setUp(self):
        self.text = read(ORCHESTRATOR)
        self.collapsed = " ".join(self.text.split())
        self.bullet = orchestrator_reconnaissance_bullet(self.text)

    def test_names_the_circularity_of_the_existing_file_count_rule(self):
        """The actual bug: applying "read up to 3 yourself" to reading in
        order to know what to delegate is circular, because writing the
        exploration's own brief needs the very knowledge being sought."""
        self.assertIn(ORCHESTRATOR_CIRCULARITY, self.bullet)

    def test_states_its_own_trigger_question(self):
        self.assertIn(ORCHESTRATOR_TRIGGER, self.bullet)

    def test_the_order_itself_is_pinned_not_only_its_diagnosis(self):
        """Mirrors the criterion file's own guard: the trigger question and
        the circularity diagnosis are DESCRIPTION. The actual COMMAND --
        look only at the gap, nothing wider -- is a separate clause. Deleting
        only it must not leave the diagnosis assertions passing."""
        self.assertIn(ORCHESTRATOR_IMPERATIVE, self.bullet)

    def test_the_stop_condition_is_pinned_specifically(self):
        """Pinned separately from the imperative to look, so a boundary-free
        "look before you delegate" rule cannot silently ship here either."""
        self.assertIn(ORCHESTRATOR_STOP, self.bullet)

    def test_does_not_name_the_criterion_file_in_this_bullet(self):
        """Naming `sub-delegation-criterion.md` on this line would put it
        under the same mechanical invariant that requires every such line to
        also carry "divides into genuinely independent parts" -- a WHEN
        clause that does not hold for a single delegation. The bullet must
        stand on its own instead of acquiring a false loading condition.
        (The concurrency bullet elsewhere in this file legitimately keeps
        that reference, correctly gated -- this check is scoped to THIS
        bullet only.)
        """
        self.assertNotIn("sub-delegation-criterion.md", self.bullet)

    def test_the_shared_criterion_file_is_still_referenced_elsewhere_correctly(self):
        """The file-wide reference to the criterion is not gone -- only moved
        out of the reconnaissance bullet. The concurrency bullet's own,
        correctly-gated reference must survive untouched."""
        self.assertIn("{{skills_root}}/_shared/sub-delegation-criterion.md", self.text)
        self.assertIn("divides into genuinely independent parts", self.collapsed)


class ThresholdAgreementTest(unittest.TestCase):
    """The two files must not contradict each other on the 3/4-file
    threshold. Agreement is derived from one shared number, not asserted
    independently in both places, and each file states the relationship in
    its own words because each is now self-sufficient for its own audience."""

    def test_both_files_anchor_reconnaissance_to_the_same_number(self):
        criterion_collapsed = " ".join(read(CRITERION).split())
        orchestrator_collapsed = " ".join(read(ORCHESTRATOR).split())
        self.assertIn(SHARED_THRESHOLD_NUMBER, criterion_collapsed)
        self.assertIn(SHARED_THRESHOLD_NUMBER, orchestrator_collapsed)

    def test_orchestrator_states_the_rule_bounds_not_replaces_the_threshold(self):
        """The relationship must be spelled out where the circularity
        actually occurs: reconnaissance is the SAME rule at the four-file
        line, not a second, competing threshold."""
        collapsed = " ".join(read(ORCHESTRATOR).split())
        self.assertIn(ORCHESTRATOR_THRESHOLD_AGREEMENT, collapsed)

    def test_neither_file_introduces_a_different_number(self):
        """A guard against silent drift: if either file's threshold sentence
        ever names a different count, the two contradict each other on when
        reconnaissance IS the existing delegate-a-narrow-exploration rule."""
        criterion_collapsed = " ".join(read(CRITERION).split())
        orchestrator_collapsed = " ".join(read(ORCHESTRATOR).split())
        self.assertIn("genuinely needs four files or more", criterion_collapsed)
        self.assertIn("four files or more to answer it", orchestrator_collapsed)


if __name__ == "__main__":
    unittest.main()
