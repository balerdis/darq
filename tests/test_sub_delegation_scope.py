"""`sub-delegation-criterion.md` governs fan-out by any agent, not only an SDD phase.

The file used to scope itself to "whether and how an SDD phase agent fans work
out to `pegasus-general`". That is wrong on two counts: any agent at any level
may fan out, and there will be more than one fan-out target over time. This
generalizes the Scope/Authority wording, keeps every gate and test exactly as
they are, adds the "fan-out is help, never offloading" paragraph, and adds the
runtime operational note about a refused `task` call.
"""
from __future__ import annotations

import unittest
from pathlib import Path

SHARED = Path(__file__).resolve().parents[1] / "src" / "pegasus" / "content" / "skills" / "_shared"
CRITERION = SHARED / "sub-delegation-criterion.md"


class ScopeIsGeneralTest(unittest.TestCase):
    def setUp(self):
        self.text = CRITERION.read_text(encoding="utf-8")

    def test_scope_no_longer_names_only_sdd_phase_agents(self):
        self.assertNotIn("an SDD phase agent fans", self.text)

    def test_scope_says_any_agent_any_level(self):
        self.assertIn("any agent", self.text.lower())
        self.assertIn("any level", self.text.lower())

    def test_scope_no_longer_hardcodes_a_single_target(self):
        """The old scope named `pegasus-general` as THE fan-out target. The new
        scope must speak of whatever targets an agent's own descriptor permits,
        not a fixed name."""
        self.assertNotIn("fans work out to `pegasus-general`", self.text)


class GatesAndTestsUnchangedTest(unittest.TestCase):
    """The three gates, tests 3 and 4, "How many parts", "Writers in parallel"
    and the fail-closed departure section are correct and must survive the
    rewrite verbatim."""

    def setUp(self):
        self.text = CRITERION.read_text(encoding="utf-8")

    def test_gate_0_survives(self):
        self.assertIn("is there already a tool that returns the compressed answer?", self.text)

    def test_gate_1_survives(self):
        self.assertIn("can I write each part's brief without naming another part's result?", self.text)

    def test_gate_2_survives(self):
        self.assertIn("do I have at least two genuinely independent parts?", self.text)

    def test_test_3_survives(self):
        self.assertIn("does my report to my parent name what I had to read", self.text)

    def test_test_4_survives(self):
        self.assertIn("can I write my children's output schema before launching them?", self.text)

    def test_how_many_parts_survives(self):
        self.assertIn("## How many parts", self.text)

    def test_writers_in_parallel_survives(self):
        self.assertIn("## Writers in parallel", self.text)

    def test_fail_closed_departure_survives(self):
        self.assertIn("## Fail-closed behavior (deliberate departure)", self.text)
        self.assertIn("an unreadable or missing copy of this file does not", self.text)


class FanOutIsHelpTest(unittest.TestCase):
    def setUp(self):
        self.text = CRITERION.read_text(encoding="utf-8")

    def test_fan_out_is_help_never_offloading(self):
        self.assertIn("fan-out is help, never offloading", self.text.lower())

    def test_names_the_prevented_failure(self):
        self.assertIn("has become an orchestrator it was not asked to be", self.text)


class RuntimeDepthNoteTest(unittest.TestCase):
    def setUp(self):
        self.text = CRITERION.read_text(encoding="utf-8")

    def test_names_the_recoverable_error(self):
        self.assertIn("Subagent depth limit reached", self.text)

    def test_states_the_fallback_without_restating_the_config_value(self):
        self.assertIn("do the work yourself", self.text.lower())
        # The config key's value (10) is Piece 1's business, not this file's.
        self.assertNotIn("subagent_depth", self.text)


class ReferencesUpdatedTest(unittest.TestCase):
    """A reference elsewhere that assumed the old, single-target scope must be
    updated in step with this file."""

    def test_sdd_phase_common_does_not_claim_a_permanent_single_target(self):
        text = (SHARED / "sdd-phase-common.md").read_text(encoding="utf-8")
        self.assertNotIn("the only agent you may fan out to", text)


class ParallelIssuanceMechanicTest(unittest.TestCase):
    """Concluding two parts are independent (the gates) is not the same as
    running them concurrently (how the calls are issued). The file must state
    the actual mechanic — every independent call emitted in the same reply,
    before any result returns — not just gesture at the word "parallel"."""

    def setUp(self):
        self.text = CRITERION.read_text(encoding="utf-8")

    def test_states_same_reply_before_any_result_returns(self):
        self.assertIn("in the same reply", self.text)
        self.assertIn("before any of their results has come back", self.text)

    def test_names_issue_one_then_next_as_sequential_regardless_of_gates(self):
        """A bare keyword like "parallel" proves nothing — this pins the
        actual claim: issuing calls one at a time IS sequential execution,
        even when the gates concluded the parts were independent."""
        self.assertIn(
            "you have picked sequential execution regardless of what the gates\nconcluded",
            self.text,
        )


if __name__ == "__main__":
    unittest.main()
