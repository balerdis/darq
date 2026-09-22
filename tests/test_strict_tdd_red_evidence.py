"""RED must be an observation, not a declaration.

Two users in a row signed a "historical Strict-TDD evidence" exception because
verification discovered, at the very end, that RED evidence did not exist and
could not be reconstructed. The root cause was textual: the apply protocol's
RED column was defined as a constant --  "Always '(check) Written'" -- so an
agent that skipped the RED run wrote the same cell an agent that ran it would
have written. A column whose value never varies carries no information, and
the RED step itself never required execution ("this guarantees failure -- no
need to execute to confirm"). Verify then checked for the presence of that
same constant string, so the two files agreed with each other about a fact
that proved nothing.

This module pins the fix: RED must be a recorded observation (a command that
was run and the failure it produced), the apply protocol must say -- as an
order, not just a diagnosis -- that the run happens before production code,
and verify must check the observation rather than a fixed string. The last
test derives the required fields once and checks both files against that same
list, so the two sides cannot drift apart the way they just did.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[1] / "src" / "darq" / "content" / "skills"
APPLY_PATH = SKILLS / "sdd-apply" / "strict-tdd.md"
VERIFY_PATH = SKILLS / "sdd-verify" / "strict-tdd-verify.md"

#: The two fields a real RED observation must carry. Sourced once and checked
#: against BOTH files below, so a change that drops one from either file fails
#: immediately instead of silently drifting from the other.
RED_EVIDENCE_FIELDS = ("command", "failure")

#: The literal licence sentence that let RED be claimed without a run.
EXECUTION_LICENCE = "no need to execute to confirm"

#: The constant the RED column used to always evaluate to. Its presence
#: anywhere near the column definition means the column still carries no
#: information regardless of what surrounding prose says.
FIXED_RED_VALUE = '"✅ Written"'


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def red_column_definition(apply_text: str) -> str:
    """The bullet defining the RED column in the Column definitions list."""
    match = re.search(r"\*\*RED\*\*:.*(?:\n(?!- \*\*).*)*", apply_text)
    assert match, "no '**RED**:' column definition found in the apply protocol"
    return match.group(0)


def red_step_block(apply_text: str) -> str:
    """The '2. RED' step of the TDD Implementation Cycle diagram."""
    match = re.search(r"├── 2\. RED.*?(?=\n├── 3\.)", apply_text, re.DOTALL)
    assert match, "no '2. RED' step found in the TDD Implementation Cycle"
    return match.group(0)


def verify_red_check_block(verify_text: str) -> str:
    """The RED-column sub-block of Step 5a's TDD Compliance Check."""
    match = re.search(r"RED column:.*?(?=├── GREEN column:)", verify_text, re.DOTALL)
    assert match, "no 'RED column:' block found in verify's Step 5a"
    return match.group(0)


def collapse(block: str) -> str:
    """Strip ASCII tree-drawing characters and rejoin wrapped lines.

    The cycle diagram wraps prose across multiple `│`-prefixed lines for
    readability. A prose claim ("does NOT individually prove...") can land
    split across two such lines, so substring checks on the raw block are
    fragile to reflow. Collapsing removes the tree furniture and normalizes
    whitespace, checking the CONTENT of the claim rather than its line breaks.
    """
    no_tree = re.sub(r"[│├└─]+", " ", block)
    return re.sub(r"\s+", " ", no_tree).strip()


def evidence_table_rows(apply_text: str) -> list[list[str]]:
    """Parse the example rows of the TDD Cycle Evidence table."""
    lines = apply_text.splitlines()
    rows = []
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if cells and re.match(r"^\d+\.\d+$", cells[0]):
            rows.append(cells)
    return rows


class ApplyProtocolTest(unittest.TestCase):
    def setUp(self):
        self.apply_text = read(APPLY_PATH)

    def test_licence_to_skip_execution_is_gone(self):
        """Pins the deletion the whole brief hinges on.

        This exact sentence is what let an agent write RED evidence for a
        test it never ran: "the test references code that doesn't exist,
        therefore it is guaranteed to fail, therefore running it is not
        necessary". Any equivalent phrasing would recreate the same hole, but
        this is the wording that actually shipped, so it is what gets pinned.
        """
        self.assertNotIn(
            EXECUTION_LICENCE,
            self.apply_text,
            "the licence to skip execution before claiming RED must be removed",
        )

    def test_red_column_is_not_a_constant(self):
        """The column definition must not resolve to the same string always.

        Checks two independent things: the literal constant phrase from the
        old definition is gone, AND the definition names something that only
        a real run produces (a command, and the failure it produced) rather
        than a checkbox a reader cannot tell apart from a fabricated one.
        """
        definition = red_column_definition(self.apply_text)
        self.assertNotIn(
            f'Always {FIXED_RED_VALUE}',
            definition,
            "the RED column must not always evaluate to the same fixed string",
        )
        for field in RED_EVIDENCE_FIELDS:
            self.assertIn(
                field,
                definition.lower(),
                f"RED column definition must require recording the {field!r} — "
                "otherwise a fabricated cell is as easy to write as a real one",
            )

    def test_evidence_table_example_shows_varying_red_observations(self):
        """A column that can only ever hold one value teaches agents to fill
        it in without looking. The worked example must demonstrate real
        variance: at least two rows must show DIFFERENT RED cells, each
        naming a specific command or failure, not an identical checkmark.
        """
        rows = evidence_table_rows(self.apply_text)
        self.assertGreaterEqual(len(rows), 2, "expected at least two example rows in the evidence table")
        red_cells = [row[4] for row in rows]  # Task | Test File | Layer | Safety Net | RED | ...
        self.assertNotEqual(
            len(set(red_cells)),
            1,
            "every example RED cell is identical — the column still reads as a constant",
        )
        for cell in red_cells:
            self.assertNotEqual(
                cell,
                FIXED_RED_VALUE.strip('"').join(["✅ ", ""]).strip(),
                "an example RED cell still uses the old bare checkmark",
            )

    def test_red_run_before_code_is_an_order_not_only_a_diagnosis(self):
        """Pins the imperative itself, not the prose explaining why it matters.

        This codebase has twice lost a guard because it pinned only the
        explanation surrounding a rule and not the rule's own sentence,
        so deleting the one actual instruction left every assertion green
        (tests/test_sub_delegation_scope.py::...::test_the_order_itself_is_pinned_not_only_its_diagnosis
        is the established precedent for this shape). The gate here must
        say, as a command, that the test is run and its failure observed
        BEFORE production code for the task is written.
        """
        step = collapse(red_step_block(self.apply_text))
        self.assertIn(
            "RUN the test",
            step,
            "the RED step must order the agent to run the test, not merely write it",
        )
        self.assertIn(
            "before writing any production code for this task",
            step,
            "the RED step must order that the run happens before production code — "
            "this is the instruction itself, not commentary about it",
        )

    def test_the_rules_summary_demands_the_run_the_way_it_does_for_green(self):
        """The compressed rules list is where the licence survives a fix.

        The tree diagram above is the full protocol; this list at the end of
        the file is its summary, and a summary is what an agent scanning for
        "the rule" actually reads. It shipped with the two halves spelled
        asymmetrically: the GREEN rule said "you MUST run tests and confirm
        they pass", while the RED rule -- the one the list itself calls the
        ONE rule that cannot be broken -- was satisfied by *writing* a test.
        An agent reading only this list therefore got the old, executionless
        RED back, whatever the diagram above says.

        Derived rather than matched against a fixed sentence: whichever line
        states the RED rule must demand a run in the same way the GREEN line
        does, so the two cannot drift apart again. Rewording either is fine;
        letting the RED half stop requiring a run is not.
        """
        rules = self.apply_text.split("## Rules (Strict TDD specific)", 1)
        self.assertEqual(len(rules), 2, "the Strict TDD rules list is gone")
        lines = [line for line in rules[1].splitlines() if line.startswith("- ")]
        red_rule = next(
            (line for line in lines if "production code" in line and "test" in line), None
        )
        self.assertIsNotNone(red_rule, "the rules list no longer states the RED rule")
        self.assertRegex(
            red_rule.lower(),
            r"\brun\b|\bobserv",
            "the RED rule must demand the test be run and seen to fail, not merely written -- "
            "the GREEN rule beside it already says 'you MUST run tests and confirm they pass'",
        )

    def test_gate_requires_observed_failure_not_merely_written_test(self):
        """The GATE line is the enforcement point; it must not still read
        'until the test is written' — that phrasing is satisfied by a test
        that was never executed."""
        step = collapse(red_step_block(self.apply_text))
        self.assertNotIn(
            "GATE: Do NOT proceed to GREEN until the test is written",
            step,
            "the gate must require an observed failure, not just a written test",
        )
        self.assertIn("OBSERVED", step, "the gate must require the failure to have been observed")

    def test_blanket_missing_symbol_failure_does_not_prove_other_scenarios(self):
        """Pins the nuance surfaced in the real session: a run that dies on
        'method/module does not exist' is legitimate RED for the task that
        introduces that symbol, but the same blanket error can mask several
        other untested scenarios, and does not individually prove any of them."""
        step = collapse(red_step_block(self.apply_text))
        self.assertIn("does not exist", step.lower())
        self.assertIn(
            "does not individually prove the other scenarios",
            step.lower(),
            "must state that a shared missing-symbol failure does not prove each scenario on its own",
        )

    def test_broken_fixture_is_not_red(self):
        """A failure caused by setup/environment, not by the behavior under
        test, must be named as disqualifying — it is a broken fixture, not RED."""
        step = collapse(red_step_block(self.apply_text))
        self.assertIn("broken fixture", step.lower())


class VerifyProtocolTest(unittest.TestCase):
    def setUp(self):
        self.verify_text = read(VERIFY_PATH)

    def test_fixed_string_is_not_accepted_as_red_evidence(self):
        block = verify_red_check_block(self.verify_text)
        self.assertNotIn(
            f'Must say {FIXED_RED_VALUE}',
            block,
            "verify must not accept the fixed string as sufficient RED evidence",
        )

    def test_red_check_states_its_own_limit(self):
        """Verify cannot reconstruct chronology after the fact — it can only
        check that an observation was recorded and is internally consistent.
        That limit must be stated, or the next verifier will demand
        something nobody can produce (exactly what cost this user two
        signed exceptions)."""
        block = verify_red_check_block(self.verify_text)
        self.assertIn("cannot reconstruct", block.lower())

    def test_test_file_existence_is_named_as_insufficient(self):
        block = verify_red_check_block(self.verify_text)
        self.assertIn("not sufficient", block.lower())


class ApplyVerifyAgreementTest(unittest.TestCase):
    """The two files must agree on what counts as RED evidence.

    Both sides are checked against the SAME field list (RED_EVIDENCE_FIELDS)
    instead of two independently hand-written assertions, so a future edit
    that drops a field from one file — without touching the other — fails
    here rather than shipping a verifier that demands evidence apply never
    produces.
    """

    def setUp(self):
        self.apply_definition = red_column_definition(read(APPLY_PATH))
        self.verify_block = verify_red_check_block(read(VERIFY_PATH))

    def test_required_red_fields_match_across_both_files(self):
        for field in RED_EVIDENCE_FIELDS:
            self.assertIn(
                field,
                self.apply_definition.lower(),
                f"apply's RED column definition must require {field!r}",
            )
            self.assertIn(
                field,
                self.verify_block.lower(),
                f"verify's RED check must validate the recorded {field!r} — "
                "otherwise it can demand evidence apply was never told to produce",
            )

    def test_neither_file_treats_the_fixed_string_as_sufficient(self):
        for text in (self.apply_definition, self.verify_block):
            self.assertNotIn(f"Always {FIXED_RED_VALUE}", text)
            self.assertNotIn(f"Must say {FIXED_RED_VALUE}", text)


if __name__ == "__main__":
    unittest.main()
