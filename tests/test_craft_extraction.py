"""The three SDD phase skills point at a craft reference instead of restating it.

`sdd-explore`, `sdd-verify` and `sdd-apply` used to mix craft (how to explore,
verify, or implement well) with chain (the SDD artifact envelope, persistence,
the archive verdict). The craft moved out to `_shared/exploration-craft.md`,
`_shared/verification-craft.md` and `_shared/implementation-craft.md`; the phase
skills keep only the chain-bound parts and point at the craft file for the rest.

Each assertion below is about a FACT (a distinctive sentence lives in exactly one
file across the whole shipped content tree), not about a filename string being
present somewhere -- a phase skill could name its craft file in prose while still
silently restating the craft it is supposed to point at instead.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from test_phase_less_specialists import PHASE_MARKERS

SKILLS = Path(__file__).resolve().parents[1] / "src" / "darq" / "content" / "skills"

#: The phase-result headings, derived from the set the specialist guard already
#: forbids in a phase-less agent body rather than retyped here -- a future phase
#: marker that is a heading is covered without anyone remembering this file.
#: Filtered to the heading-shaped members: `PHASE_MARKERS` also carries
#: "Required loading gate" and "return `blocked`", which are not envelopes.
ENVELOPE_HEADINGS = tuple(marker for marker in PHASE_MARKERS if marker.startswith("## "))


def all_text() -> dict[Path, str]:
    return {
        path: path.read_text(encoding="utf-8")
        for path in SKILLS.rglob("*.md")
        if "__pycache__" not in path.parts
    }


def occurrences(needle: str) -> list[Path]:
    return [path for path, text in all_text().items() if needle in text]


class CraftFilesExistTest(unittest.TestCase):
    def test_exploration_craft_exists(self):
        self.assertTrue((SKILLS / "_shared" / "exploration-craft.md").is_file())

    def test_verification_craft_exists(self):
        self.assertTrue((SKILLS / "_shared" / "verification-craft.md").is_file())

    def test_implementation_craft_exists(self):
        self.assertTrue((SKILLS / "_shared" / "implementation-craft.md").is_file())


class PhaseSkillsPointAtCraftTest(unittest.TestCase):
    def test_sdd_explore_points_at_exploration_craft(self):
        text = (SKILLS / "sdd-explore" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("_shared/exploration-craft.md", text)

    def test_sdd_verify_points_at_verification_craft(self):
        text = (SKILLS / "sdd-verify" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("_shared/verification-craft.md", text)

    def test_sdd_apply_points_at_implementation_craft(self):
        text = (SKILLS / "sdd-apply" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("_shared/implementation-craft.md", text)


class CraftIsNotRestatedTest(unittest.TestCase):
    """A distinctive instruction from each craft file must live nowhere else.

    Proves the fact the extraction promises -- the phase skill no longer
    restates the craft -- rather than merely proving the pointer exists.
    """

    def test_the_investigation_checklist_lives_only_in_exploration_craft(self):
        found = occurrences("INVESTIGATE:")
        self.assertEqual(found, [SKILLS / "_shared" / "exploration-craft.md"])

    def test_the_comparison_order_lives_only_in_verification_craft(self):
        found = occurrences("Compare specs first, design second, task completion third.")
        self.assertEqual(found, [SKILLS / "_shared" / "verification-craft.md"])

    def test_the_work_unit_evidence_gate_lives_only_in_implementation_craft(self):
        found = occurrences("MUST produce a **Work Unit Evidence** table")
        self.assertEqual(found, [SKILLS / "_shared" / "implementation-craft.md"])


class CraftOwnsNoPhaseEnvelopeTest(unittest.TestCase):
    """A craft file owns the shape of a good report; a phase skill owns the
    envelope its phase must emit.

    `exploration-craft.md` used to reproduce the literal heading
    `## Exploration: {topic}` inside its `## Report Shape` fence -- the exact
    string a phase-less specialist is forbidden to emit -- so `pegasus-explorer`
    was pointed at a ready-made template of the one thing it may not produce.
    The agent body's prose mitigation ("borrow the sections that fit") is
    advisory and untestable; this is the fact instead.

    What is forbidden is REPRODUCING the envelope as a heading -- a line that
    starts with `## ` and carries the marker -- not mentioning it. The
    distinction is load-bearing and it is why `verification-craft.md` passes:
    its `## Output Contract` says "Return `## Verification Report` with
    change/subject, mode, ..." inline in prose. Naming the output contract is
    exactly what a craft file should do; handing over a heading to copy is not.
    """

    def craft_files(self) -> list[Path]:
        return sorted(SKILLS.glob("_shared/*-craft.md"))

    def test_the_craft_files_are_found(self):
        """Without this the scan below would pass by finding nothing."""
        self.assertEqual(
            [path.name for path in self.craft_files()],
            ["exploration-craft.md", "implementation-craft.md", "verification-craft.md"],
        )

    def test_the_forbidden_set_is_derived_and_non_empty(self):
        self.assertTrue(ENVELOPE_HEADINGS, "no heading-shaped marker was derived")
        self.assertIn("## Exploration: {topic}", ENVELOPE_HEADINGS)
        self.assertIn("## Verification Report", ENVELOPE_HEADINGS)

    def test_no_craft_file_reproduces_a_phase_envelope_heading(self):
        for path in self.craft_files():
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if not line.strip().startswith("## "):
                    continue
                for heading in ENVELOPE_HEADINGS:
                    if heading in line:
                        self.fail(f"{path.name}:{number} reproduces the phase envelope {heading!r}")

    def test_the_phase_skill_still_owns_the_envelope_it_must_emit(self):
        """Moved, not deleted: `sdd-explore` emits exactly the envelope it
        emitted before this change."""
        text = (SKILLS / "sdd-explore" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("## Exploration: {topic}", text)

    def test_the_craft_still_owns_the_sections_that_report_carries(self):
        """The requirement moved house; it did not evaporate."""
        text = (SKILLS / "_shared" / "exploration-craft.md").read_text(encoding="utf-8")
        for section in ("Current State", "Affected Areas", "Approaches", "Recommendation", "Risks"):
            with self.subTest(section=section):
                self.assertIn(section, text)


if __name__ == "__main__":
    unittest.main()
