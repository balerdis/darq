"""How the orchestrator decides: concurrently, at a cost, and only sometimes SDD.

Three reported frictions, one file:

1.  Concurrency was never mentioned, so independent delegations went out one at
    a time and the person waited for each round trip. OpenCode dispatches every
    tool call in a single assistant response concurrently, with no limit, so the
    rule is a real capability rather than an aspiration.
2.  The threshold read as permission. The file opened by telling the agent to
    launch work through its delegation primitive, and "Narrating the Work"
    opened by calling delegation the visible proof of coordinating -- nothing
    named what delegating something small COSTS. The observed behaviour was that
    it delegated everything, trivia included.
3.  Nothing in the product owned whether a request IS an SDD request, so
    everything was routed into the SDD flow and a person who wanted one thing
    looked at was asked to run `sdd-init` and resolve preflight first.
    `_shared/sdd-applicability.md` now owns that question; the orchestrator
    keeps the compact IF.

The assertions hold FACTS rather than proxies: the old framings must be gone
from the file that produced the behaviour (not merely balanced by new text
elsewhere), Gate 1's own wording must live in exactly one file across the whole
shipped tree, and the preflight gate must still be intact for work that IS SDD.
"""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "src" / "pegasus" / "content"
AGENTS = CONTENT / "agents"
SKILLS = CONTENT / "skills"
SHARED = SKILLS / "_shared"

ORCHESTRATOR = AGENTS / "pegasus-orchestrator.md"
APPLICABILITY = SHARED / "sdd-applicability.md"
CRITERION = SHARED / "sub-delegation-criterion.md"

#: Gate 1's own wording. The orchestrator must point at it, never restate it.
GATE_1 = "can I write each part's brief without naming another part's result?"

#: The two sentences that framed delegation as permission and as visible proof
#: of coordinating. Their removal is the change; new text alongside them would
#: not have been one.
PERMISSION_FRAMINGS = (
    "Above the threshold below, launch the work through your runtime's native delegation primitive",
    "Delegation is the part of your job the user can actually see",
)

#: A distinctive instruction from the new shared file. Finding it in a second
#: place means the compact IF swallowed the HOW it was supposed to point at.
APPLICABILITY_NEEDLE = "Name the moment out loud, propose the switch, and resolve preflight then"

#: 97 lines before this change. "Trade text for text" as a measurable fact.
ORCHESTRATOR_LINE_CEILING = 104


def content_documents() -> dict[Path, str]:
    return {
        path: path.read_text(encoding="utf-8")
        for path in sorted([*SKILLS.rglob("*.md"), *AGENTS.rglob("*.md")])
        if "__pycache__" not in path.parts
    }


def occurrences(needle: str) -> list[Path]:
    return [path for path, text in content_documents().items() if needle in text]


class ConcurrencyTest(unittest.TestCase):
    def setUp(self):
        self.text = ORCHESTRATOR.read_text(encoding="utf-8")

    def test_the_orchestrator_names_launching_in_one_response(self):
        """The rule has to name the mechanism, not merely praise parallelism:
        what makes two delegations concurrent is landing in the SAME response."""
        lowered = self.text.lower()
        self.assertIn("same response", lowered)
        self.assertIn("independent", lowered)

    def test_it_points_at_gate_1_for_what_independent_means(self):
        self.assertIn("Gate 1", self.text)
        self.assertIn("_shared/sub-delegation-criterion.md", self.text)

    def test_gate_1_is_pointed_at_rather_than_restated(self):
        """The fact, over the whole shipped tree: Gate 1's wording lives in the
        file that owns it and nowhere else."""
        self.assertEqual(occurrences(GATE_1), [CRITERION])


class ThresholdReadsAsCostTest(unittest.TestCase):
    def setUp(self):
        self.text = ORCHESTRATOR.read_text(encoding="utf-8")

    def test_the_permission_framings_are_gone(self):
        for framing in PERMISSION_FRAMINGS:
            with self.subTest(framing=framing):
                self.assertNotIn(framing, self.text)

    def test_the_cost_of_a_delegation_is_named(self):
        """A brief to write, a round trip, a report to read, a person waiting --
        the four the old framing left unsaid."""
        lowered = self.text.lower()
        for cost in ("a brief to write", "a round trip", "a report to read", "waiting"):
            with self.subTest(cost=cost):
                self.assertIn(cost, lowered)

    def test_the_default_is_doing_it_yourself(self):
        self.assertIn("inflate your own context", self.text)


class SddApplicabilityTest(unittest.TestCase):
    def test_the_shared_file_exists_and_follows_the_house_conventions(self):
        self.assertTrue(APPLICABILITY.is_file())
        text = APPLICABILITY.read_text(encoding="utf-8")
        self.assertIn("## Scope", text)
        self.assertIn("## Authority", text)

    def test_the_shared_file_owns_the_cases_the_compact_if_does_not(self):
        text = APPLICABILITY.read_text(encoding="utf-8")
        lowered = text.lower()
        self.assertIn("ambiguous", lowered)
        self.assertIn("mid-flight", lowered)
        self.assertIn(APPLICABILITY_NEEDLE, text)

    def test_the_shared_file_fails_open(self):
        text = APPLICABILITY.read_text(encoding="utf-8")
        self.assertIn("missing or unreadable", text)

    def test_the_shared_file_points_instead_of_restating_preflight(self):
        """Preflight's own owner keeps owning WHAT preflight is and WHEN it
        runs; this file only decides whether the request is SDD at all."""
        text = APPLICABILITY.read_text(encoding="utf-8")
        self.assertIn("_shared/sdd-session-preflight.md", text)
        self.assertNotIn("Execution mode", text)
        self.assertNotIn("Review budget", text)

    def test_the_orchestrator_carries_the_compact_if(self):
        text = ORCHESTRATOR.read_text(encoding="utf-8")
        self.assertIn("_shared/sdd-applicability.md", text)
        lowered = text.lower()
        self.assertIn("not every request is sdd", lowered)

    def test_the_orchestrator_does_not_swallow_the_how(self):
        self.assertEqual(occurrences(APPLICABILITY_NEEDLE), [APPLICABILITY])

    def test_the_non_sdd_path_names_the_three_specialists(self):
        """Scanned below the front matter on purpose: `may_delegate_to` already
        names all three, so a whole-file search would pass without the prose
        ever telling the agent where non-SDD work goes."""
        prose = ORCHESTRATOR.read_text(encoding="utf-8").split("---\n", 2)[2]
        for name in ("pegasus-explorer", "pegasus-verifier", "pegasus-implementer"):
            with self.subTest(agent=name):
                self.assertIn(name, prose)


class PreflightStaysStrictTest(unittest.TestCase):
    """What changes is that the gate stops firing for work that is not SDD --
    never that it got softer for work that is."""

    def setUp(self):
        self.text = ORCHESTRATOR.read_text(encoding="utf-8")

    def test_the_gate_still_stops_the_turn(self):
        self.assertIn("_shared/sdd-session-preflight.md", self.text)
        self.assertIn("and STOP", self.text)
        self.assertIn("Do not run the requested phase in the same turn", self.text)

    def test_the_gate_is_still_eager_for_a_natural_language_request(self):
        self.assertIn("a natural-language request never loads a command file", self.text)


class OrchestratorStaysSmallTest(unittest.TestCase):
    def test_the_body_traded_text_for_text(self):
        lines = len(ORCHESTRATOR.read_text(encoding="utf-8").splitlines())
        self.assertLessEqual(lines, ORCHESTRATOR_LINE_CEILING, "the orchestrator body grew")


if __name__ == "__main__":
    unittest.main()
