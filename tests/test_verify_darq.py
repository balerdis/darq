"""Unit tests for the pure brand-leak classifier in ``tools.verify_darq``.

Everything exercised here is pure: parsing the three named registers from an in-memory payload,
and classifying leak matches against them. No filesystem, no subprocess, no built binary required.
The one exception is `test_rebrand_json_registers_load_without_error`, which reads the repo's real
`rebrand.json` to prove the registers this repo actually ships parse cleanly and cover the real
inventory measured against a clean install.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import verify_darq  # noqa: E402


def _classify_first_finding(text: str, protected, accepted, defects) -> verify_darq.Finding | None:
    findings = verify_darq.scan_text_for_findings(text, protected, accepted, defects)
    return findings[0] if findings else None


class ClassifyMatchTests(unittest.TestCase):
    """The four-way classifier, tested directly against synthetic registers."""

    def setUp(self) -> None:
        self.protected = ("pegasus/cli-report/v1",)
        self.accepted = {"pegasus-cosmetic-thing": "cosmetic reason"}
        self.defects = {"pegasus-known-bug": "functional defect reason"}

    def test_protected_token_is_silent(self) -> None:
        text = 'schema: "pegasus/cli-report/v1"'
        findings = verify_darq.scan_text_for_findings(text, self.protected, self.accepted, self.defects)
        self.assertEqual(findings, [])

    def test_accepted_residue_is_a_note(self) -> None:
        text = "name: pegasus-cosmetic-thing"
        finding = _classify_first_finding(text, self.protected, self.accepted, self.defects)
        self.assertIsNotNone(finding)
        self.assertEqual(finding.outcome, verify_darq.NOTE)
        self.assertEqual(finding.token, "pegasus-cosmetic-thing")

    def test_known_defect_is_a_warning(self) -> None:
        text = "const AGENT = pegasus-known-bug"
        finding = _classify_first_finding(text, self.protected, self.accepted, self.defects)
        self.assertIsNotNone(finding)
        self.assertEqual(finding.outcome, verify_darq.WARNING)
        self.assertEqual(finding.token, "pegasus-known-bug")

    def test_unclassified_hit_is_a_fail(self) -> None:
        text = "a brand new pegasus-regression nobody declared anywhere"
        finding = _classify_first_finding(text, self.protected, self.accepted, self.defects)
        self.assertIsNotNone(finding)
        self.assertEqual(finding.outcome, verify_darq.FAIL)
        self.assertIsNone(finding.token)

    def test_classify_match_returns_the_same_four_outcomes_directly(self) -> None:
        line = "pegasus/cli-report/v1 pegasus-cosmetic-thing pegasus-known-bug pegasus-mystery"
        outcomes = []
        for match in verify_darq._LEAK_PATTERN.finditer(line):
            outcome, _token = verify_darq.classify_match(
                line, match.start(), match.end(), self.protected, self.accepted, self.defects
            )
            outcomes.append(outcome)
        self.assertEqual(
            outcomes,
            [verify_darq.SILENT, verify_darq.NOTE, verify_darq.WARNING, verify_darq.FAIL],
        )


class LeakPatternTests(unittest.TestCase):
    """'harness' must never trigger a scan on its own -- see the comment on _LEAK_PATTERN."""

    def test_bare_harness_is_not_a_leak(self) -> None:
        text = "Runtime harness command/scenario and exact result"
        findings = verify_darq.scan_text_for_findings(text, (), {}, {})
        self.assertEqual(findings, [])

    def test_pegasus_harness_is_still_caught(self) -> None:
        text = "installed under pegasus-harness by mistake"
        findings = verify_darq.scan_text_for_findings(text, (), {}, {})
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].outcome, verify_darq.FAIL)


class ParseReasonRegisterTests(unittest.TestCase):
    """Every accepted_residue/known_defects entry must carry a token and a non-empty reason."""

    def test_entry_missing_reason_is_rejected(self) -> None:
        payload = {"accepted_residue": [{"token": "pegasus-something"}]}
        with self.assertRaises(verify_darq.VerificationFailure):
            verify_darq.parse_reason_register("accepted_residue", payload)

    def test_entry_missing_token_is_rejected(self) -> None:
        payload = {"known_defects": [{"reason": "some reason"}]}
        with self.assertRaises(verify_darq.VerificationFailure):
            verify_darq.parse_reason_register("known_defects", payload)

    def test_entry_with_blank_reason_is_rejected(self) -> None:
        payload = {"accepted_residue": [{"token": "pegasus-something", "reason": "   "}]}
        with self.assertRaises(verify_darq.VerificationFailure):
            verify_darq.parse_reason_register("accepted_residue", payload)

    def test_well_formed_entries_parse_into_a_token_to_reason_mapping(self) -> None:
        payload = {
            "accepted_residue": [
                {"token": "pegasus-short", "reason": "reason A"},
                {"token": "pegasus-much-longer-token", "reason": "reason B"},
            ]
        }
        parsed = verify_darq.parse_reason_register("accepted_residue", payload)
        self.assertEqual(parsed["pegasus-short"], "reason A")
        self.assertEqual(parsed["pegasus-much-longer-token"], "reason B")
        # Longest-first ordering, same rationale as protected_tokens.
        self.assertEqual(list(parsed)[0], "pegasus-much-longer-token")


class RebrandJsonRegistersTests(unittest.TestCase):
    """The registers this repo actually ships must load without error and classify the real,
    measured residue correctly -- proof by mutation that the check can still fail follows in
    VerifyMutationTests below, against a fabricated installed tree.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = verify_darq.load_rebrand_config()
        cls.protected = verify_darq.parse_protected_tokens(cls.payload)
        cls.accepted = verify_darq.parse_reason_register("accepted_residue", cls.payload)
        cls.defects = verify_darq.parse_reason_register("known_defects", cls.payload)

    def test_rebrand_json_registers_load_without_error(self) -> None:
        self.assertIn("pegasus/cli-report/v1", self.protected)
        self.assertGreater(len(self.accepted), 0)
        self.assertGreater(len(self.defects), 0)

    def test_known_orchestrator_notifier_defect_is_a_warning(self) -> None:
        line = 'const ORCHESTRATOR_AGENT = "pegasus-orchestrator"'
        finding = _classify_first_finding(line, self.protected, self.accepted, self.defects)
        self.assertIsNotNone(finding)
        self.assertEqual(finding.outcome, verify_darq.WARNING)

    def test_skill_registry_subtree_residue_is_a_note(self) -> None:
        line = 'PEGASUS_SKILL_REGISTRY_BIN=/home/x/.config/opencode/pegasus/skill-registry/pegasus-skill-registry'
        finding = _classify_first_finding(line, self.protected, self.accepted, self.defects)
        self.assertIsNotNone(finding)
        self.assertEqual(finding.outcome, verify_darq.NOTE)

    def test_new_registry_assets_schema_is_protected_and_silent(self) -> None:
        line = '"schema": "pegasus-registry-assets/v3",'
        findings = verify_darq.scan_text_for_findings(line, self.protected, self.accepted, self.defects)
        self.assertEqual(findings, [])

    def test_zellij_debug_env_var_is_protected_and_silent(self) -> None:
        line = 'return process.env.PEGASUS_ZELLIJ_STATE_DEBUG === "1"'
        findings = verify_darq.scan_text_for_findings(line, self.protected, self.accepted, self.defects)
        self.assertEqual(findings, [])

    def test_a_brand_new_unclassified_leak_still_fails(self) -> None:
        line = "totally new pegasus-drift-nobody-declared appears here"
        finding = _classify_first_finding(line, self.protected, self.accepted, self.defects)
        self.assertIsNotNone(finding)
        self.assertEqual(finding.outcome, verify_darq.FAIL)


class VerifyEndToEndMutationTests(unittest.TestCase):
    """Prove the check can still fail: inject a synthetic, unclassified brand string into an
    installed-tree-shaped text blob and confirm it produces a FAIL finding; then confirm the same
    file, scanned before mutation, produces no FAIL finding at all.
    """

    @classmethod
    def setUpClass(cls) -> None:
        payload = verify_darq.load_rebrand_config()
        cls.protected = verify_darq.parse_protected_tokens(payload)
        cls.accepted = verify_darq.parse_reason_register("accepted_residue", payload)
        cls.defects = verify_darq.parse_reason_register("known_defects", payload)

    def _fail_count(self, text: str) -> int:
        findings = verify_darq.scan_text_for_findings(text, self.protected, self.accepted, self.defects)
        return sum(1 for finding in findings if finding.outcome == verify_darq.FAIL)

    def test_clean_installed_looking_text_has_no_fail(self) -> None:
        clean_text = "\n".join(
            [
                '"schema": "pegasus/cli-report/v1"',
                'PEGASUS_SKILL_ROOTS=/some/path',
                'export default PegasusSkillRegistryPlugin',
                'const ORCHESTRATOR_AGENT = "pegasus-orchestrator"',
            ]
        )
        self.assertEqual(self._fail_count(clean_text), 0)

    def test_injected_regression_produces_a_fail(self) -> None:
        mutated_text = "\n".join(
            [
                '"schema": "pegasus/cli-report/v1"',
                'PEGASUS_SKILL_ROOTS=/some/path',
                # A brand-new, never-declared brand leak injected into an otherwise clean file --
                # this is what a real regression looks like: nothing in any register mentions it.
                'const NEW_LEAK = "pegasus-totally-unreviewed-regression"',
            ]
        )
        self.assertEqual(self._fail_count(mutated_text), 1)


if __name__ == "__main__":
    unittest.main()
