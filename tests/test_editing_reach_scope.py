"""The baseline's editing-reach section tells a denied TOOL from a denied FILE.

On a real machine an agent was asked to add a line to `/etc/hosts`. Passwordless
`sudo` was configured, the agent had `bash` with no restriction on it, and it had
already written the correct `sudo tee` command out for the person. Its patch tool
returned `PermissionDenied: FileSystem.writeFile (/etc/hosts)` -- an ordinary
filesystem error -- and the agent quoted this product's own baseline back at the
user ("If the runtime denies a tool, that denial stands") and stopped. Our own
text closed a path nobody had closed.

Two different things share the word "denied", and the section now has to name
which one it is talking about:

* The runtime DENYING an agent a tool is a decision about the AGENT. The person
  or the configuration said this agent may not use that tool, so every other
  route to the same end is closed too. That is the denial that stands.
* A `PermissionDenied` / `EACCES` / "Permission denied" RETURNED BY a tool is a
  fact about the FILE. That tool writes as the user this session runs as, and
  the file belongs to somebody else. It says nothing about what another tool can
  reach.

The section already reasons correctly about the remote case ("for a remote edit
the shell is not a way around them: it is the only way there"). A local file this
session's user cannot write is out of the editing tools' reach for exactly the
same reason, so it gets the same treatment, under the same condition the SSH
paragraph uses: correct when the person asked for that change.

And because "where you can get to" is not "what you may change" -- `{program}`
ships a verifier that holds `bash` precisely to run tests and is told not to fix
anything -- the section has to scope itself the way `## Persona Scope` does.

HOW THIS GUARD IS WRITTEN. Every check below locates the SENTENCE that makes a
claim and asserts that sentence carries it. None of them asks whether a word
appears somewhere in the file. That exact proxy is a confirmed defect in this
tree: a guard that checked `"archive" in text.lower()` was defeated by appending
an unrelated parenthetical containing the word, and `GuardIsNotAWordBagTest`
below runs the equivalent attack against these helpers so the weakening cannot
come back in silence.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

BASELINE = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "darq"
    / "content"
    / "system-prompt"
    / "AGENTS.md"
)

#: The section is found by what it is about, not by one spelling of its title:
#: the heading may be reworded, but there is exactly one `##` about editing.
SECTION_HEADING = re.compile(r"^##\s+Editing\b.*$", re.MULTILINE)
NEXT_HEADING = re.compile(r"^##\s+", re.MULTILINE)

#: A run with no sentence-ending period in it: one sentence, so a match cannot
#: be assembled out of clauses that live in two different claims.
SENTENCE = r"[^.]*"

#: Locates the surviving restrictive sentence -- the one that misfired.
DENIAL_STANDS = re.compile(r"\bdenial stands\b", re.IGNORECASE)

#: "A tool the runtime DENIES you is a decision about this agent."
TOOL_DENIAL_IS_ABOUT_THE_AGENT = re.compile(
    rf"\bden(?:y|ies|ied|ying)\b{SENTENCE}\bis a decision about\b{SENTENCE}\bagent\b",
    re.IGNORECASE,
)

#: ...and therefore closes every other route to the same end.
CLOSES_EVERY_ROUTE = re.compile(
    rf"\b(?:every|all|any)\b{SENTENCE}\b(?:route|path|way)s?\b{SENTENCE}\bclosed\b",
    re.IGNORECASE,
)

#: "A `PermissionDenied` ... returned BY a tool is a fact about the FILE."
RETURNED_ERROR_IS_ABOUT_THE_FILE = re.compile(
    rf"(?:`PermissionDenied`|`EACCES`){SENTENCE}\bis a fact about\b{SENTENCE}\bfile\b",
    re.IGNORECASE,
)

#: ...and so proves nothing about the other tools.
SAYS_NOTHING_ABOUT_OTHER_TOOLS = re.compile(
    r"\bsays nothing about what (?:another|any other) tool can reach\b", re.IGNORECASE
)

#: An order to stop. It belongs to the denied-tool claim and must not be hung on
#: the sentence about a filesystem error, which is the misfire this file exists for.
AN_ORDER_TO_STOP = re.compile(r"\b(?:stop|stands)\b", re.IGNORECASE)

#: "Editing a privileged local file with `bash` and `sudo` is correct on the same
#: condition: when the person asked for that change." The condition has to live in
#: the same sentence as the authorisation, not merely somewhere in the section --
#: the remote bullet already carries those words.
PRIVILEGED_LOCAL_IS_CORRECT = re.compile(
    rf"\bsudo\b{SENTENCE}\bis correct\b{SENTENCE}\bperson asked for that change\b",
    re.IGNORECASE,
)

#: Elevating is the person's call, and an error is not a request for it.
ELEVATION_IS_THE_PERSONS_DECISION = re.compile(
    rf"\belevat\w+\b{SENTENCE}\bis the person(?:'|’)s decision\b", re.IGNORECASE
)
NOT_A_REQUEST_TO_ELEVATE = re.compile(
    rf"`PermissionDenied`{SENTENCE}\bis not a request to elevate\b", re.IGNORECASE
)

#: The same care the SSH sentence already demands, and the announcement before
#: running an elevated command.
SAY_BEFORE_RUNNING = re.compile(
    rf"\bsay what you\b{SENTENCE}\brun\b{SENTENCE}\bbefore\b", re.IGNORECASE
)
READ_IT_BACK = re.compile(r"\bread it back to confirm\b", re.IGNORECASE)
READ_THE_CURRENT_VALUE = re.compile(r"\bread the current value first\b", re.IGNORECASE)
ONLY_WHAT_WAS_AUTHORIZED = re.compile(
    r"\bchange only what was authori[sz]ed\b", re.IGNORECASE
)

#: Modelled on `## Persona Scope`'s own self-scoping ("govern ONLY your reply
#: text"): this section says where you can get to, never what you may change,
#: and it never widens the contract of the agent reading it.
SCOPES_ITSELF_TO_REACH = re.compile(
    rf"\bgoverns ONLY\b{SENTENCE}\bwhere you can get to\b{SENTENCE}"
    rf"\bnever widens what your own agent(?:'|’)s contract permits\b"
)

#: Correct today and load-bearing for the symmetry the privileged-local case is
#: built on. If this goes, the new bullet is reasoning from something absent.
REMOTE_IS_THE_ONLY_WAY_THERE = re.compile(
    r"\bthe shell is not a way around\b[^.]*\bit is the only way there\b", re.IGNORECASE
)


def section_of(text: str) -> str:
    """The editing-reach section's body, heading excluded."""
    opening = SECTION_HEADING.search(text)
    if opening is None:
        return ""
    rest = text[opening.end() :]
    closing = NEXT_HEADING.search(rest)
    return rest if closing is None else rest[: closing.start()]


def bullets_of(section: str) -> list[str]:
    """Every top-level bullet, one string each."""
    return [line.strip() for line in section.splitlines() if line.lstrip().startswith("- ")]


def the_bullet_that(pattern: re.Pattern[str], section: str) -> str:
    """The single bullet a locator matches, or "" when it is not exactly one."""
    found = [bullet for bullet in bullets_of(section) if pattern.search(bullet)]
    return found[0] if len(found) == 1 else ""


def tells_the_two_denials_apart(section: str) -> bool:
    """Does the bullet carrying "that denial stands" say which denial it means,
    and does it name the other one as a fact about the file?"""
    bullet = the_bullet_that(DENIAL_STANDS, section)
    if not bullet:
        return False
    return bool(
        TOOL_DENIAL_IS_ABOUT_THE_AGENT.search(bullet)
        and CLOSES_EVERY_ROUTE.search(bullet)
        and RETURNED_ERROR_IS_ABOUT_THE_FILE.search(bullet)
        and SAYS_NOTHING_ABOUT_OTHER_TOOLS.search(bullet)
    )


def authorises_the_privileged_local_path(section: str) -> bool:
    """Is there a bullet that authorises the elevated local edit on the same
    condition the SSH bullet uses, with the same read-first/read-back care?"""
    bullet = the_bullet_that(PRIVILEGED_LOCAL_IS_CORRECT, section)
    if not bullet:
        return False
    return all(
        pattern.search(bullet)
        for pattern in (
            SAY_BEFORE_RUNNING,
            READ_THE_CURRENT_VALUE,
            ONLY_WHAT_WAS_AUTHORIZED,
            READ_IT_BACK,
            ELEVATION_IS_THE_PERSONS_DECISION,
            NOT_A_REQUEST_TO_ELEVATE,
        )
    )


def scopes_itself_to_reach(section: str) -> bool:
    """Does one sentence say the section is about reach and widens no contract?"""
    return bool(SCOPES_ITSELF_TO_REACH.search(section))


class EditingReachSectionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = BASELINE.read_text(encoding="utf-8")
        cls.section = section_of(cls.text)

    def test_the_section_is_found_at_all(self):
        """Everything below reads this section; an empty one would pass vacuously."""
        self.assertTrue(self.section.strip(), "no `## Editing ...` section in the baseline")
        self.assertGreaterEqual(len(bullets_of(self.section)), 5)

    def test_the_restrictive_sentence_says_which_denial_it_is_about(self):
        """"That denial stands" is true of a tool the runtime withheld from this
        agent and false of a filesystem error, and the sentence has to say so."""
        bullet = the_bullet_that(DENIAL_STANDS, self.section)
        self.assertTrue(bullet, "no single bullet carries the `denial stands` rule")
        self.assertRegex(bullet, TOOL_DENIAL_IS_ABOUT_THE_AGENT)
        self.assertRegex(bullet, CLOSES_EVERY_ROUTE)

    def test_a_permission_error_returned_by_a_tool_is_named_a_fact_about_the_file(self):
        bullet = the_bullet_that(DENIAL_STANDS, self.section)
        self.assertTrue(bullet, "no single bullet carries the `denial stands` rule")
        self.assertRegex(bullet, RETURNED_ERROR_IS_ABOUT_THE_FILE)
        self.assertRegex(bullet, SAYS_NOTHING_ABOUT_OTHER_TOOLS)

    def test_the_two_denials_are_told_apart(self):
        self.assertTrue(tells_the_two_denials_apart(self.section))

    def test_the_sentence_about_a_returned_error_does_not_order_a_stop(self):
        """The misfire itself: an agent read an `EACCES` as an order to stop. The
        sentence that describes a returned permission error must not carry one."""
        bullet = the_bullet_that(DENIAL_STANDS, self.section)
        self.assertTrue(bullet, "no single bullet carries the `denial stands` rule")
        claim = RETURNED_ERROR_IS_ABOUT_THE_FILE.search(bullet)
        self.assertIsNotNone(claim)
        self.assertNotRegex(
            claim.group(0),
            AN_ORDER_TO_STOP,
            "the filesystem-error sentence has been made to order a stop again",
        )

    def test_the_privileged_local_edit_is_authorised_on_the_persons_request(self):
        """Symmetric with the remote bullet, and conditioned the same way."""
        bullet = the_bullet_that(PRIVILEGED_LOCAL_IS_CORRECT, self.section)
        self.assertTrue(
            bullet,
            "no bullet authorises an elevated local edit when the person asked for it",
        )
        self.assertRegex(bullet, SAY_BEFORE_RUNNING)
        self.assertRegex(bullet, READ_THE_CURRENT_VALUE)
        self.assertRegex(bullet, ONLY_WHAT_WAS_AUTHORIZED)
        self.assertRegex(bullet, READ_IT_BACK)

    def test_elevating_is_the_persons_call_and_an_error_is_not_a_request_for_it(self):
        bullet = the_bullet_that(PRIVILEGED_LOCAL_IS_CORRECT, self.section)
        self.assertTrue(bullet, "no bullet authorises an elevated local edit")
        self.assertRegex(bullet, ELEVATION_IS_THE_PERSONS_DECISION)
        self.assertRegex(bullet, NOT_A_REQUEST_TO_ELEVATE)

    def test_the_whole_privileged_local_path_is_present(self):
        self.assertTrue(authorises_the_privileged_local_path(self.section))

    def test_the_section_scopes_itself_to_reach_and_widens_no_contract(self):
        """`darq-verifier` holds `bash` to run tests and is told not to fix
        anything. Nothing here may be read as permission to start fixing."""
        self.assertTrue(
            scopes_itself_to_reach(self.section),
            "the section does not say it governs reach only and widens no contract",
        )

    def test_the_remote_reasoning_the_local_case_mirrors_is_still_there(self):
        self.assertRegex(self.section, REMOTE_IS_THE_ONLY_WAY_THERE)


class GuardIsNotAWordBagTest(unittest.TestCase):
    """The attack that defeated this tree's last prose guard, run against this one.

    Each doctored section below contains every WORD the real one does -- the
    locators would all hit if they searched the file rather than the sentence --
    while the claim the section exists to make has been taken out. Every helper
    must answer False.
    """

    WORD_SALAD = "\n".join(
        (
            "- Denied, denial stands, decision, agent, tool, file, closed, every route.",
            "- `PermissionDenied`, `EACCES`, Permission denied, fact, reach, another tool.",
            "- sudo, bash, is correct, the person asked for that change, elevate, elevating.",
            "- governs ONLY, where you can get to, never widens, contract permits, agent's.",
        )
    )

    def test_the_two_denials_are_not_told_apart_by_a_word_bag(self):
        self.assertFalse(tells_the_two_denials_apart(self.WORD_SALAD))

    def test_the_privileged_path_is_not_authorised_by_a_word_bag(self):
        self.assertFalse(authorises_the_privileged_local_path(self.WORD_SALAD))

    def test_the_section_is_not_scoped_by_a_word_bag(self):
        self.assertFalse(scopes_itself_to_reach(self.WORD_SALAD))

    def test_a_claim_split_across_two_bullets_does_not_count(self):
        """Half the claim in one bullet and half in another is not the claim."""
        split = "\n".join(
            (
                "- If the runtime denies a tool, that denial stands: say which tool and stop.",
                "- Denying a tool is a decision about this agent and every route is closed.",
                "- A `PermissionDenied` is a fact about the file.",
                "- It says nothing about what another tool can reach.",
            )
        )
        self.assertFalse(tells_the_two_denials_apart(split))

    def test_the_condition_in_a_neighbouring_sentence_does_not_count(self):
        """The authorisation and its condition have to be the same sentence; the
        remote bullet already says "the person asked for that change" nearby."""
        neighbour = "\n".join(
            (
                "- Editing a privileged local file with `bash` and `sudo` is correct. "
                "Do it when the person asked for that change. "
                "Say what you will run before you run it, read the current value first, "
                "change only what was authorized, and read it back to confirm. "
                "Elevating is the person's decision, and a `PermissionDenied` is not a "
                "request to elevate.",
            )
        )
        self.assertFalse(authorises_the_privileged_local_path(neighbour))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
