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

SKILLS = Path(__file__).resolve().parents[1] / "src" / "pegasus" / "content" / "skills"


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


if __name__ == "__main__":
    unittest.main()
