"""`sdd-verify`'s readiness-authority claim is scoped to the SDD archive gate.

`sdd-verify` used to describe itself as Pegasus's "sole readiness authority for
executable and configuration changes" -- wording broad enough to read as
authority over every change anywhere, which forced anyone who only wanted a
verification run to enter the whole SDD flow to reach it. What the claim
actually gates is narrower: `sdd-archive` may run only on a current
verify-report with no critical findings. The claim is rewritten to say that
scope out loud, and this guard keeps a future agent body from re-widening it
by making the same broad claim again.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

AGENTS = Path(__file__).resolve().parents[1] / "src" / "pegasus" / "content" / "agents"

#: A self-declared "I am THE authority" claim, worded loosely enough to catch a
#: future agent phrasing it differently while still claiming the same thing:
#: "sole" (or "the one") within a short distance of "authority".
AUTHORITY_CLAIM = re.compile(r"\bsole\b.{0,60}\bauthority\b", re.IGNORECASE | re.DOTALL)


def matches_by_file() -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for path in sorted(AGENTS.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        hits = [m.group(0) for m in AUTHORITY_CLAIM.finditer(text)]
        if hits:
            found[path.name] = hits
    return found


class ReadinessAuthorityScopeTest(unittest.TestCase):
    def test_the_claim_is_scoped_to_archiving_an_sdd_change(self):
        """The rewritten wording must name the archive gate, not "every change"."""
        text = (AGENTS / "sdd-verify.md").read_text(encoding="utf-8")
        self.assertIn("archive", text.lower())
        self.assertNotIn("executable and configuration changes", text)

    def test_the_orchestrator_pointer_is_scoped_the_same_way(self):
        text = (AGENTS / "pegasus-orchestrator.md").read_text(encoding="utf-8")
        self.assertIn("archive", text.lower())

    def test_only_sdd_verify_and_the_orchestrator_make_the_claim(self):
        found = matches_by_file()
        self.assertEqual(
            set(found),
            {"sdd-verify.md", "pegasus-orchestrator.md"},
            f"a readiness-authority claim was found outside its owner: {found}",
        )


if __name__ == "__main__":
    unittest.main()
