"""Three phase-less specialists ship beside the SDD phase agents.

`sdd-explore`, `sdd-verify` and `sdd-apply` each own a phase of a change's
lifecycle: they return a phase-shaped artifact, assume a chain around them, and
block on a required loading gate. A person who only wants one thing looked at,
one check run, or one small change made had no shipped agent to reach, so the
only way in was the whole SDD flow.

`pegasus-explorer`, `pegasus-verifier` and `pegasus-implementer` close that gap.
Each practises the same craft as its SDD namesake -- the craft files are shared,
pointed at, never restated -- and differs in exactly one thing: what it returns.
`sdd-verify` returns a verdict and is an authority; `pegasus-verifier` returns
evidence and says plainly that it declares nothing ready, which is what makes it
safe to reach from an agent that writes.

Every assertion here is about a FACT rather than a proxy for one:

- Read-only is asserted against the RENDERED permission and tool maps the
  runtime actually resolves a call against, not against a word missing from
  front matter.
- "No phase envelope" is asserted with markers proven to still exist in the SDD
  agents they were taken from, so a typo cannot make the guard vacuous.
- "Points at its craft without restating it" is asserted as a uniqueness fact
  over the whole shipped content tree plus a body-size ceiling, because a body
  can name a file and paste its contents underneath.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from pegasus import cli
from pegasus.adapters.opencode import Adapter
from pegasus.adapters.opencode import render as render_module
from pegasus.core import content as content_module
from pegasus.core.content import AgentMode
from pegasus.core.types import ConfigKeyArtifact, Environment

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "src" / "pegasus" / "content"
AGENTS = CONTENT / "agents"
SKILLS = CONTENT / "skills"

HOME = Path("/home/probe")
ENVIRONMENT = Environment(home=HOME, data_dir=HOME / ".local" / "share" / "pegasus-harness")

SPECIALISTS = ("pegasus-explorer", "pegasus-verifier", "pegasus-implementer")

#: Each specialist and the craft reference it must defer to, lazily.
CRAFT = {
    "pegasus-explorer": "_shared/exploration-craft.md",
    "pegasus-verifier": "_shared/verification-craft.md",
    "pegasus-implementer": "_shared/implementation-craft.md",
}

#: A distinctive instruction from each craft file. Restating the craft in an
#: agent body would land one of these in a second file.
CRAFT_NEEDLE = {
    "_shared/exploration-craft.md": "INVESTIGATE:",
    "_shared/verification-craft.md": "Compare specs first, design second, task completion third.",
    "_shared/implementation-craft.md": "MUST produce a **Work Unit Evidence** table",
}

#: What a phase agent carries and a phase-less specialist must not: a
#: phase-shaped result heading, a blocking loading gate, and the artifact chain
#: those two exist to serve. Held against the SDD agents below so a marker that
#: matches nothing anywhere fails loudly instead of passing silently.
PHASE_MARKERS = (
    "## Exploration: {topic}",
    "## Verification Report",
    "Required loading gate",
    "return `blocked`",
)

#: A self-declared "I am THE authority" claim, the same shape
#: `test_readiness_authority_scope.py` refuses outside its owner.
AUTHORITY_CLAIM = re.compile(r"\bsole\b.{0,60}\bauthority\b", re.IGNORECASE | re.DOTALL)

#: A body that carries identity and a compact IF fits in this; a body that
#: inlined the craft it was told to point at does not. Measured against the
#: prose as written (31-32 lines), with room to breathe. Front matter is not
#: counted: it is a fixed declaration block, not the lazy-load contract this
#: budget exists to hold.
BODY_LINE_CEILING = 38


def whole(name: str) -> str:
    """The shipped file, front matter included.

    For ABSENCE checks. A phase envelope or a fail-closed word is just as wrong
    in a `description:` as in the prose, so forbidding it everywhere is strictly
    stronger than forbidding it in one half.
    """
    return (AGENTS / f"{name}.md").read_text(encoding="utf-8")


def prose_of(text: str) -> str:
    """Everything after the front matter block."""
    parts = text.split("---\n", 2)
    return parts[2] if len(parts) == 3 else parts[0]


def description_of(text: str) -> str:
    """The one front-matter line a contract may legitimately also live on."""
    parts = text.split("---\n", 2)
    front = parts[1] if len(parts) == 3 else ""
    return next(
        (
            line.split(":", 1)[1].strip()
            for line in front.splitlines()
            if line.startswith("description:")
        ),
        "",
    )


def body(name: str) -> str:
    """The prose only, for PRESENCE checks.

    This helper used to return the whole file, which made every presence check
    satisfiable by the `description:` line. An adversarial review removed every
    occurrence of "what changed" from `pegasus-implementer.md`'s prose, left its
    description untouched, and `WhatEachOneReturnsTest` stayed fully green. A
    guard about what the agent is told now reads what the agent is told.
    """
    return prose_of(whole(name))


def description(name: str) -> str:
    return description_of(whole(name))


def content_documents() -> dict[Path, str]:
    return {
        path: path.read_text(encoding="utf-8")
        for path in sorted([*SKILLS.rglob("*.md"), *AGENTS.rglob("*.md")])
        if "__pycache__" not in path.parts
    }


def occurrences(needle: str) -> list[Path]:
    return [path for path, text in content_documents().items() if needle in text]


def resolve(rules: dict, name: str):
    """What the runtime lands on: the narrower rule if written, else the baseline."""
    return rules.get(name, rules["*"])


class SpecialistsShipTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = content_module.load()
        cls.by_name = {agent.name: agent for agent in cls.content.agents}

    def test_each_specialist_ships_as_a_subagent(self):
        for name in SPECIALISTS:
            with self.subTest(agent=name):
                self.assertIn(name, self.by_name)
                self.assertIs(self.by_name[name].mode, AgentMode.SUBAGENT)

    def test_each_specialist_declares_the_fan_out_its_work_divides_into(self):
        expected = {
            "pegasus-explorer": ("pegasus-explorer",),
            "pegasus-verifier": ("pegasus-verifier",),
            "pegasus-implementer": ("pegasus-explorer", "pegasus-verifier"),
        }
        for name, targets in expected.items():
            with self.subTest(agent=name):
                self.assertEqual(self.by_name[name].may_delegate_to, targets)


class RenderedPermissionTest(unittest.TestCase):
    """Read-only asserted where the runtime reads it, not where a human wrote it.

    Omitting `write` from front matter is not the fact under test -- the fact is
    that the rendered `permission` and `tools` maps resolve an edit to a refusal.
    `write` and `edit` fold onto one `edit` permission in this runtime, so `edit`
    is the name both must be checked under.
    """

    @classmethod
    def setUpClass(cls):
        cls.layout = Adapter().layout(ENVIRONMENT)
        cls.identity = cli.default_identity()
        cls.by_name = {agent.name: agent for agent in content_module.load().agents}

    def rendered(self, name: str) -> dict:
        artifacts = render_module.agent(self.layout, self.by_name[name])
        return [a for a in artifacts if isinstance(a, ConfigKeyArtifact)][0].value

    def test_the_explorer_and_the_verifier_cannot_write(self):
        for name in ("pegasus-explorer", "pegasus-verifier"):
            with self.subTest(agent=name):
                value = self.rendered(name)
                self.assertEqual(value["permission"]["*"], "deny")
                self.assertEqual(resolve(value["permission"], "edit"), "deny")
                self.assertIs(value["tools"]["*"], False)
                self.assertIs(resolve(value["tools"], "edit"), False)
                self.assertIs(resolve(value["tools"], "write"), False)

    def test_the_two_read_only_agents_still_render_what_they_do_need(self):
        """Without this the assertions above would also pass for an agent that
        was denied everything, including its own trade."""
        explorer = self.rendered("pegasus-explorer")
        self.assertEqual(resolve(explorer["permission"], "read"), "allow")
        self.assertEqual(resolve(explorer["permission"], "grep"), "allow")
        verifier = self.rendered("pegasus-verifier")
        self.assertEqual(resolve(verifier["permission"], "read"), "allow")
        self.assertEqual(resolve(verifier["permission"], "bash"), "allow")

    def test_the_implementer_can_write(self):
        value = self.rendered("pegasus-implementer")
        self.assertEqual(resolve(value["permission"], "edit"), "allow")
        self.assertIs(resolve(value["tools"], "write"), True)


class NoPhaseEnvelopeTest(unittest.TestCase):
    def test_the_markers_still_exist_where_they_were_taken_from(self):
        """Drift guard: a marker nothing matches would make the test below
        pass while checking nothing at all."""
        sdd = "\n".join(
            (AGENTS / f"{name}.md").read_text(encoding="utf-8")
            for name in ("sdd-explore", "sdd-verify", "sdd-apply")
        )
        for marker in PHASE_MARKERS:
            with self.subTest(marker=marker):
                self.assertIn(marker, sdd)

    def test_no_specialist_carries_a_phase_envelope(self):
        for name in SPECIALISTS:
            for marker in PHASE_MARKERS:
                with self.subTest(agent=name, marker=marker):
                    self.assertNotIn(marker, whole(name))

    def test_no_specialist_assumes_the_artifact_chain(self):
        for name in SPECIALISTS:
            with self.subTest(agent=name):
                text = whole(name)
                self.assertNotIn("persistence-contract.md", text)
                self.assertNotIn("artifact store", text.lower())


class CraftIsPointedAtNotRestatedTest(unittest.TestCase):
    def test_each_specialist_points_at_its_craft_file(self):
        for name, reference in CRAFT.items():
            with self.subTest(agent=name):
                self.assertIn(f"{{{{skills_root}}}}/{reference}", body(name))

    def test_no_craft_instruction_lives_in_two_places(self):
        for reference, needle in CRAFT_NEEDLE.items():
            with self.subTest(craft=reference):
                self.assertEqual(occurrences(needle), [SKILLS / reference])

    def test_each_specialist_body_stays_small_enough_to_be_a_pointer(self):
        """The lazy-load contract as a measurable fact: a body that inlined the
        craft it points at cannot fit in this."""
        for name in SPECIALISTS:
            with self.subTest(agent=name):
                lines = len(body(name).splitlines())
                self.assertLessEqual(lines, BODY_LINE_CEILING, f"{name}.md grew past its budget")

    def test_the_craft_pointer_fails_open(self):
        """A craft reference is a lazy-loaded reference, not a required gate:
        an unreadable one costs judgement, never the assignment.

        Presence is asserted on the prose -- that is where the agent is told
        what to do -- and absence on the whole file, because a fail-closed word
        would be just as wrong on a `description:` line."""
        for name in SPECIALISTS:
            with self.subTest(agent=name):
                self.assertIn("missing or unreadable", body(name))
                self.assertNotIn("blocked", whole(name))
                self.assertNotIn("STOP", whole(name))


class WhatEachOneReturnsTest(unittest.TestCase):
    """The single contract that separates a specialist from its SDD namesake."""

    def test_the_verifier_returns_evidence_and_says_it_declares_nothing_ready(self):
        self.assertIn("I do not declare anything ready", body("pegasus-verifier"))
        self.assertIn("evidence", body("pegasus-verifier").lower())

    def test_the_verifier_makes_no_readiness_authority_claim(self):
        self.assertIsNone(AUTHORITY_CLAIM.search(whole("pegasus-verifier")))

    def test_sdd_verify_still_makes_the_claim_the_specialist_refuses(self):
        """The contrast is the point: if the claim vanished from `sdd-verify`,
        the assertion above would be measuring an empty distinction."""
        self.assertIsNotNone(AUTHORITY_CLAIM.search(whole("sdd-verify")))

    def test_the_explorer_returns_a_finding_and_the_implementer_what_changed(self):
        self.assertIn("finding", body("pegasus-explorer").lower())
        self.assertIn("what changed", body("pegasus-implementer").lower())

    def test_each_contract_is_advertised_where_a_caller_reads_it_too(self):
        """The one place a contract legitimately lives twice.

        A caller picking an agent sees the `description:`, never the prose, so
        what each one returns has to be stated there as well. Asserted on
        purpose rather than inherited from a helper that happened to read the
        whole file -- that accident is what let the prose lose the contract
        while every guard stayed green."""
        for name, promise in (
            ("pegasus-explorer", "finding"),
            ("pegasus-verifier", "evidence"),
            ("pegasus-implementer", "what changed"),
        ):
            with self.subTest(agent=name):
                self.assertIn(promise, description(name).lower())


class HelperReadsTheBodyTest(unittest.TestCase):
    """The split itself, held against the leak it once had.

    `body()` returned the whole file, so every PRESENCE check in this module was
    satisfiable by a word on the `description:` line. These pin the contract so
    the split cannot quietly collapse back. Asserted against a literal fixture
    rather than a file written into the shipped content tree -- the functions
    under test take text, so there is nothing to stage on disk.
    """

    FIXTURE = (
        "---\n"
        "name: probe\n"
        "description: returns a finding about the thing\n"
        "mode: subagent\n"
        "---\n"
        "\n"
        "# Probe\n"
        "\n"
        "Prose that says something else entirely.\n"
    )

    def test_the_body_excludes_the_front_matter(self):
        text = prose_of(self.FIXTURE)
        self.assertIn("Prose that says something else entirely.", text)
        self.assertNotIn("description:", text)
        self.assertNotIn("returns a finding", text)

    def test_the_description_is_read_on_its_own(self):
        self.assertEqual(description_of(self.FIXTURE), "returns a finding about the thing")

    def test_every_shipped_specialist_actually_has_both_halves(self):
        """Guards against a parse that silently returns "" for everything."""
        for name in SPECIALISTS:
            with self.subTest(agent=name):
                self.assertTrue(body(name).strip())
                self.assertTrue(description(name).strip())
                self.assertNotIn("description:", body(name))


if __name__ == "__main__":
    unittest.main()
