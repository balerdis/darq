"""`pegasus-general`'s fan-out permission becomes a checkpoint with a moment.

The permission used to be one long sentence at the end of a section, phrased as
a passive escape ("When your own brief divides into genuinely independent parts,
read ..."). The observed behaviour was that the agent never fanned out and
worked everything sequentially. This product already knows how to write
something it wants to happen every time -- `system-prompt/AGENTS.md` uses
"**Self-check BEFORE every response**", a checkpoint with a defined moment --
and that is the shape the permission takes now.

The guard here is structural rather than lexical, because "the body mentions
fanning out" was already true of the version that never fanned out. What has to
be true is that the instruction is a section of its own, carrying a trigger, and
that the prose where it used to hide no longer carries it.

The second half is the rule the owner asked for: a general that distributes its
whole assignment has stopped being a worker. `_shared/sub-delegation-criterion.md`
owns the general form ("Fan-out is help, never offloading"); this body states the
agent-specific half and points there for the rest.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from pegasus.core import content as content_module

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "src" / "pegasus" / "content"
AGENTS = CONTENT / "agents"
SKILLS = CONTENT / "skills"

GENERAL = AGENTS / "pegasus-general.md"
CRITERION = SKILLS / "_shared" / "sub-delegation-criterion.md"
CRITERION_REFERENCE = "_shared/sub-delegation-criterion.md"

#: The general form of the keep-the-work rule. Owned by the criterion file, so
#: finding it in a second place means this body restated instead of pointing.
OFFLOADING_SECTION = "Fan-out is help, never offloading"

#: 42 lines before this change. Two short sections traded against one long
#: sentence must not turn into a second body.
GENERAL_LINE_CEILING = 46


def sections(text: str) -> dict[str, str]:
    """Split a body into `## heading -> section text`, preamble under `""`."""
    found: dict[str, str] = {}
    heading = ""
    buffer: list[str] = []
    for line in text.splitlines():
        match = re.match(r"^##\s+(.*)$", line)
        if match:
            found[heading] = "\n".join(buffer)
            heading = match.group(1).strip()
            buffer = []
        else:
            buffer.append(line)
    found[heading] = "\n".join(buffer)
    return found


def content_documents() -> dict[Path, str]:
    return {
        path: path.read_text(encoding="utf-8")
        for path in sorted([*SKILLS.rglob("*.md"), *AGENTS.rglob("*.md")])
        if "__pycache__" not in path.parts
    }


def occurrences(needle: str) -> list[Path]:
    return [path for path, text in content_documents().items() if needle in text]


class CheckpointIsASectionWithATriggerTest(unittest.TestCase):
    def setUp(self):
        self.text = GENERAL.read_text(encoding="utf-8")
        self.sections = sections(self.text)

    def test_the_fan_out_instruction_owns_a_section_of_its_own(self):
        owning = [name for name, text in self.sections.items() if CRITERION_REFERENCE in text]
        self.assertEqual(
            len(owning), 1, f"the criterion is referenced from {owning or 'nowhere'}"
        )
        self.assertNotEqual(owning[0], "", "the criterion still sits in the untitled preamble")

    def test_that_section_is_a_self_check(self):
        owning = [name for name, text in self.sections.items() if CRITERION_REFERENCE in text][0]
        self.assertIn("self-check", owning.lower())

    def test_the_checkpoint_names_the_moment_it_fires(self):
        """A checkpoint without a moment is a permission. The moment is the
        brief arriving, before any work starts."""
        owning = [name for name, text in self.sections.items() if CRITERION_REFERENCE in text][0]
        moment = (owning + "\n" + self.sections[owning]).lower()
        self.assertIn("before you start", moment)
        self.assertIn("once", moment)

    def test_the_preamble_no_longer_carries_the_permission(self):
        """Where it used to hide: the last sentence of the untitled prose at
        the top. The old wording is gone with it."""
        self.assertNotIn(CRITERION_REFERENCE, self.sections[""])
        self.assertNotIn("When your own brief divides into genuinely independent parts, read", self.text)


class KeepTheCentralWorkTest(unittest.TestCase):
    def setUp(self):
        self.text = GENERAL.read_text(encoding="utf-8")

    def test_the_agent_states_the_rule_in_its_own_voice(self):
        self.assertIn("has stopped being a worker", self.text)

    def test_it_distributes_parts_and_never_the_whole(self):
        lowered = self.text.lower()
        self.assertIn("never the whole", lowered)

    def test_the_general_form_is_pointed_at_and_not_restated(self):
        self.assertEqual(occurrences(OFFLOADING_SECTION), [CRITERION])


class WidenedTargetsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = content_module.load()
        cls.by_name = {agent.name: agent for agent in cls.content.agents}

    def test_the_targets_are_the_two_readers_plus_itself(self):
        self.assertEqual(
            self.by_name["pegasus-general"].may_delegate_to,
            ("pegasus-general", "pegasus-explorer", "pegasus-verifier"),
        )

    def test_every_target_is_a_shipped_agent(self):
        for name in self.by_name["pegasus-general"].may_delegate_to:
            with self.subTest(target=name):
                self.assertIn(name, self.by_name)

    def test_it_does_not_hand_its_writing_to_another_writer(self):
        """Gate 2's hand-off: the general already writes, so reaching a second
        writer transfers the work rather than distributing it."""
        self.assertNotIn("pegasus-implementer", self.by_name["pegasus-general"].may_delegate_to)


class BodyStaysShortTest(unittest.TestCase):
    def test_the_body_did_not_become_a_second_document(self):
        lines = len(GENERAL.read_text(encoding="utf-8").splitlines())
        self.assertLessEqual(lines, GENERAL_LINE_CEILING, "pegasus-general.md grew past its budget")


if __name__ == "__main__":
    unittest.main()
