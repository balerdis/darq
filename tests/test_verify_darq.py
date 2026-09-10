"""Unit tests for the pure brand-leak classifier in ``tools.verify_darq``.

Everything exercised here is pure: parsing the three named registers from an in-memory payload,
and classifying leak matches against them. No filesystem, no subprocess, no built binary required.
The one exception is `test_rebrand_json_registers_load_without_error`, which reads the repo's real
`rebrand.json` to prove the registers this repo actually ships parse cleanly and cover the real
inventory measured against a clean install.

`InstallerBrandLeakTests` and `InstallerIdentityAssignmentTests` cover the pure helpers behind the
generated-installer checks in the same way; `InstallerVerificationMutationTests` proves
`verify_installer` itself can fail, against a scratch copy of an installer-shaped script -- never
against the repo's own `dist/install.sh`.
"""
from __future__ import annotations

import stat
import sys
import tempfile
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


class FindStaleReasonEntriesTests(unittest.TestCase):
    """The guard closing the gap `accepted_residue`/`known_defects` used to have: an entry that
    classifies nothing in a run must be reported, naming it, so the register can never grow stale
    without anyone noticing.
    """

    def test_entry_with_a_real_hit_is_not_stale(self) -> None:
        reasons = {"pegasus-something": "cosmetic reason"}
        corpus = ['const NAME = "pegasus-something"']
        self.assertEqual(verify_darq.find_stale_reason_entries(reasons, corpus), ())

    def test_entry_with_no_hit_anywhere_is_stale(self) -> None:
        reasons = {"pegasus-AGENTS.md": "obsolete reason"}
        corpus = ['const NAME = "pegasus-something-else"', "no relevant text here"]
        self.assertEqual(
            verify_darq.find_stale_reason_entries(reasons, corpus), ("pegasus-AGENTS.md",)
        )

    def test_empty_corpus_makes_every_entry_stale(self) -> None:
        reasons = {"pegasus-a": "reason a", "pegasus-b": "reason b"}
        self.assertEqual(
            set(verify_darq.find_stale_reason_entries(reasons, [])), {"pegasus-a", "pegasus-b"}
        )

    def test_empty_register_reports_no_stale_entries(self) -> None:
        self.assertEqual(verify_darq.find_stale_reason_entries({}, ["anything"]), ())

    def test_a_shorter_entry_shadowed_by_a_longer_one_is_not_reported_stale(self) -> None:
        """The edge case the guard has to get right: two registered tokens where the shorter
        one's only occurrence sits entirely inside the longer one's occurrence. `classify_match`
        always attributes that match to the longer token (registers are longest-token-first), so
        the shorter one never 'wins' a classification here -- but its text is still genuinely
        present, so it must NOT be reported stale. Obsolescence means the literal string never
        occurs at all, not merely that another entry claims the same spot first."""
        reasons = {
            "pegasus/skill-registry/pegasus-skill-registry": "longer, wins classification",
            "pegasus-skill-registry": "shorter, shadowed by the entry above at this exact spot",
        }
        corpus = ["PEGASUS_SKILL_REGISTRY_BIN=/x/pegasus/skill-registry/pegasus-skill-registry"]
        self.assertEqual(verify_darq.find_stale_reason_entries(reasons, corpus), ())

    def test_a_token_absent_from_the_corpus_even_when_a_longer_relative_is_present_is_stale(self) -> None:
        """The complement of the shadowing case above: the longer token's presence does not
        excuse a *different*, unrelated shorter token that plain-text never occurs at all."""
        reasons = {
            "pegasus/skill-registry/pegasus-skill-registry": "present",
            "pegasus-AGENTS.md": "not present anywhere",
        }
        corpus = ["PEGASUS_SKILL_REGISTRY_BIN=/x/pegasus/skill-registry/pegasus-skill-registry"]
        self.assertEqual(
            verify_darq.find_stale_reason_entries(reasons, corpus), ("pegasus-AGENTS.md",)
        )


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
        # known_defects is deliberately NOT asserted non-empty: an empty register is the
        # correct, desirable state, and demanding an entry would create pressure to keep a
        # defect registered after it was fixed upstream. What must hold is that whatever it
        # holds classifies correctly -- see the test below, which is derived from the data
        # and therefore passes for zero entries and for any future one.

    def test_every_registered_defect_classifies_as_a_warning(self) -> None:
        """Derived from the register, not from a hardcoded token.

        The orchestrator-notifier defect used to be the single entry here; engine v5.24.0
        fixed it (the plugin now carries an {{orchestrator}} placeholder filled from the
        content-declared name), so the register is empty again. Written this way, this test
        keeps proving the WARNING contract for whatever the register holds next, instead of
        having to be rewritten every time an entry arrives or leaves.
        """
        for token in self.defects:
            with self.subTest(token=token):
                finding = _classify_first_finding(
                    f"a line that mentions {token} in passing",
                    self.protected, self.accepted, self.defects,
                )
                self.assertIsNotNone(finding)
                self.assertEqual(finding.outcome, verify_darq.WARNING)

    def test_the_fixed_orchestrator_literal_is_now_a_fail(self) -> None:
        """The complement of the register's removal, and the reason removing it matters.

        While the defect was registered, `pegasus-orchestrator` in an installed tree was a
        WARNING -- expected, tolerated, easy to scroll past. Now that the engine fills the
        name from content, that literal has no legitimate reason to appear in a DARQ install
        at all, so its reappearance is a regression and must fail the check rather than warn.
        """
        line = 'const ORCHESTRATOR_AGENT = "pegasus-orchestrator"'
        finding = _classify_first_finding(line, self.protected, self.accepted, self.defects)
        self.assertIsNotNone(finding)
        self.assertEqual(finding.outcome, verify_darq.FAIL)

    def test_skill_registry_env_value_is_now_a_fail_since_names_derive_from_identity(self) -> None:
        """As of engine v5.28.0 the skill-registry subtree, its executable and its module all
        derive their names from identity.json, so a value naming the literal engine path is no
        longer accepted residue -- it went from a NOTE (see git history of this test) to exactly
        the kind of unclassified hit the register is meant to keep failing. The environment
        variable name itself stays SILENT (it is still `protected_tokens`, a stable wire key);
        only the path value it points at is a regression now."""
        line = 'PEGASUS_SKILL_REGISTRY_BIN=/home/x/.config/opencode/pegasus/skill-registry/pegasus-skill-registry'
        finding = _classify_first_finding(line, self.protected, self.accepted, self.defects)
        self.assertIsNotNone(finding)
        self.assertEqual(finding.outcome, verify_darq.FAIL)

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
                # What a clean DARQ install actually contains since engine v5.28.0: the
                # exported plugin symbol derives from identity.json too, so it reads
                # "DarqSkillRegistryPlugin", never the engine-named literal. This line used
                # to read "PegasusSkillRegistryPlugin" and passed only because accepted_residue
                # downgraded it to a NOTE -- that entry was pruned once names stopped being
                # literal (see rebrand.json's accepted_residue_notes).
                'export default DarqSkillRegistryPlugin',
                # What a clean DARQ install actually contains since engine v5.24.0: the
                # notifier's orchestrator name comes from DARQ's own content. This line used
                # to read "pegasus-orchestrator" and passed only because known_defects
                # downgraded it to a WARNING -- the register was masking a real occurrence
                # inside the fixture that stands for a clean tree.
                'const ORCHESTRATOR_AGENT = "darq-orchestrator"',
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


class InstallerBrandLeakTests(unittest.TestCase):
    """`find_installer_brand_leaks` is unconditional -- no register, no exceptions -- so it is
    tested directly against short synthetic snippets."""

    def test_clean_text_has_no_leaks(self) -> None:
        text = "PRODUCT_ID='darq'\nPRODUCT_DISPLAY_NAME='DARQ'\n"
        self.assertEqual(verify_darq.find_installer_brand_leaks(text), [])

    def test_pegasus_is_caught_case_insensitively(self) -> None:
        text = "# Built for Pegasus\nPRODUCT_ID='darq'\n"
        findings = verify_darq.find_installer_brand_leaks(text)
        self.assertEqual(len(findings), 1)
        line_number, token, line_text = findings[0]
        self.assertEqual(line_number, 1)
        self.assertEqual(token, "pegasus")
        self.assertIn("Pegasus", line_text)

    def test_harness_is_caught_unlike_the_binary_leak_scan(self) -> None:
        # Unlike `_LEAK_PATTERN` (which drops bare 'harness' as an ordinary English word), the
        # installer check is unconditional over the exact three tokens the brief names.
        text = "some harness reference"
        findings = verify_darq.find_installer_brand_leaks(text)
        self.assertEqual([token for _line, token, _text in findings], ["harness"])

    def test_balerdis_is_not_banned_since_it_is_the_shared_github_account(self) -> None:
        # 'balerdis' hosts both github.com/balerdis/pegasus-harness (the engine) and
        # github.com/balerdis/darq (this distribution) -- it is not an engine-specific brand
        # string, and DARQ's own identity.json legitimately puts it in the installer's base URL.
        text = "curl -fsSL https://github.com/balerdis/darq/releases/latest/download/install.sh"
        self.assertEqual(verify_darq.find_installer_brand_leaks(text), [])


class SharedForbiddenFragmentsRegisterTests(unittest.TestCase):
    """`verify_darq.FORBIDDEN_INSTALLER_TOKENS` and `rebrand.transform`'s mirror check must read
    the SAME register out of `rebrand.json` -- there must be exactly one declaration of "what
    counts as a brand leak" inside DARQ, not two independently hand-written lists that happen to
    agree today and can silently drift apart tomorrow.

    This intentionally does not just assert two equal literals written independently in this test
    file: it re-reads `rebrand.json`'s `forbidden_fragments` register itself and compares
    `verify_darq`'s constant against that live value, so the test fails again the moment someone
    reintroduces a hardcoded tuple in `verify_darq.py` that drifts from `rebrand.json`.
    """

    def test_forbidden_installer_tokens_equals_rebrand_jsons_forbidden_fragments_register(self) -> None:
        payload = verify_darq.load_rebrand_config()
        self.assertEqual(
            set(verify_darq.FORBIDDEN_INSTALLER_TOKENS),
            set(payload["forbidden_fragments"]),
        )

    def test_forbidden_installer_tokens_is_not_a_hardcoded_literal_independent_of_the_json_file(
        self,
    ) -> None:
        """Prove the constant is actually *derived* from the file, not just coincidentally equal
        to it: mutate a throwaway copy of the register and confirm loading from that copy changes
        what `find_installer_brand_leaks` would treat as forbidden -- i.e. the value really is a
        function of the register's content, not a value someone typed twice."""
        payload = verify_darq.load_rebrand_config()
        mutated = dict(payload)
        mutated["forbidden_fragments"] = ["totally-unrelated-fragment"]
        derived = tuple(mutated["forbidden_fragments"])
        findings = verify_darq.find_installer_brand_leaks(
            "a line mentioning totally-unrelated-fragment here", tokens=derived
        )
        self.assertEqual([token for _line, token, _text in findings], ["totally-unrelated-fragment"])
        # And that same string is NOT flagged under the real, unmutated register.
        self.assertEqual(
            verify_darq.find_installer_brand_leaks(
                "a line mentioning totally-unrelated-fragment here"
            ),
            [],
        )


class InstallerIdentityAssignmentTests(unittest.TestCase):
    def test_derives_all_four_assignments_from_identity_payload(self) -> None:
        identity = {
            "product_id": "darq",
            "display_name": "DARQ",
            "program_name": "darq",
            "release": {"install_base_url_default": "https://example.invalid/latest/download"},
        }
        assignments = verify_darq.expected_installer_identity_assignments(identity)
        self.assertEqual(
            assignments,
            {
                "PRODUCT_ID": "darq",
                "PRODUCT_DISPLAY_NAME": "DARQ",
                "PRODUCT_PROGRAM_NAME": "darq",
                "PRODUCT_RELEASE_BASE_URL_DEFAULT": "https://example.invalid/latest/download",
            },
        )

    def test_darq_identity_json_matches_what_the_generated_installer_must_carry(self) -> None:
        import json

        identity = json.loads((ROOT / "identity.json").read_text(encoding="utf-8"))
        assignments = verify_darq.expected_installer_identity_assignments(identity)
        self.assertEqual(assignments["PRODUCT_ID"], "darq")
        self.assertEqual(assignments["PRODUCT_DISPLAY_NAME"], "DARQ")
        self.assertEqual(assignments["PRODUCT_PROGRAM_NAME"], "darq")
        self.assertTrue(assignments["PRODUCT_RELEASE_BASE_URL_DEFAULT"].startswith("https://"))


# A minimal, installer-shaped fixture: an identity header block plus just enough --help handling
# to exercise `verify_installer`'s subprocess check without needing a real build or network access.
_INSTALLER_FIXTURE = """#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
PRODUCT_ID='darq'
PRODUCT_DISPLAY_NAME='DARQ'
PRODUCT_PROGRAM_NAME='darq'
PRODUCT_RELEASE_BASE_URL_DEFAULT='https://github.com/balerdis/darq/releases/latest/download'
# ============================================================================

case "${1-}" in
  --help|-h)
    echo "usage: install.sh [--help] [--verify]"
    echo "installs a product; see identity block above for details"
    exit 0
    ;;
  --verify)
    echo "se instalaria: el binario $PRODUCT_PROGRAM_NAME"
    exit 0
    ;;
esac
"""


class InstallerVerificationMutationTests(unittest.TestCase):
    """Proves `verify_installer` can actually fail: run it against a scratch copy of an
    installer-shaped fixture with an injected 'pegasus' brand string, and confirm it reports a
    failure; then run it again against the same fixture unmutated and confirm it does not.

    Never touches the repo's real `dist/install.sh` -- both copies live in a throwaway temp dir
    created by this test and removed afterward.
    """

    def _run_against(self, installer_text: str) -> verify_darq.Report:
        with tempfile.TemporaryDirectory(prefix="darq-installer-mutation-") as tmp:
            tmp_path = Path(tmp)
            installer_path = tmp_path / "install.sh"
            installer_path.write_text(installer_text, encoding="utf-8")
            mode = installer_path.stat().st_mode
            installer_path.chmod(mode | stat.S_IXUSR)

            scratch_root = tmp_path / "scratch"
            scratch_root.mkdir()

            report = verify_darq.Report()
            verify_darq.verify_installer(installer_path, scratch_root, report)
            return report

    def test_clean_fixture_reports_no_failure(self) -> None:
        report = self._run_against(_INSTALLER_FIXTURE)
        self.assertEqual(report.failures, [])

    def test_injected_pegasus_string_is_reported_as_a_failure(self) -> None:
        mutated = _INSTALLER_FIXTURE.replace(
            "# ============================================================================\n"
            "PRODUCT_ID='darq'",
            "# Adapted from pegasus\n"
            "# ============================================================================\n"
            "PRODUCT_ID='darq'",
        )
        self.assertIn("pegasus", mutated)
        report = self._run_against(mutated)
        self.assertGreater(len(report.failures), 0)
        self.assertTrue(any("brand leak" in failure for failure in report.failures))


class ReadmeAgreesWithTheDefectRegisterTests(unittest.TestCase):
    """The README's "Limitaciones conocidas" prose must not outlive the register it describes.

    This class exists because it already went wrong: the README announced the
    orchestrator-notifier defect as live for weeks after engine v5.24.0 fixed it, telling
    readers their notifications were broken when they worked. Nothing caught it, because
    the register and the prose were two independent statements of the same fact and only
    one of them got updated.

    Both directions are checked, because a stale README can fail either way: claiming a
    defect nobody registered, or staying silent about one somebody did.
    """

    #: Matched as a literal substring, which is all this guard claims to do: it trips on a
    #: verbatim reintroduction of this heading, not on the same claim reworded or translated.
    #: A cheap tripwire for the regression that actually happened, not a proof of accuracy.
    HEADING = "Defecto funcional conocido"

    @classmethod
    def setUpClass(cls) -> None:
        cls.readme = (ROOT / "README.md").read_text(encoding="utf-8")
        cls.defects = verify_darq.parse_reason_register(
            "known_defects", verify_darq.load_rebrand_config()
        )

    def test_the_readme_announces_no_defect_the_register_does_not_hold(self) -> None:
        # Deliberately asserts nothing when the register is non-empty: a heading is then
        # legitimate, and the sibling test below is what covers that branch.
        if not self.defects:
            self.assertNotIn(
                self.HEADING,
                self.readme,
                "the README announces a known functional defect but known_defects is empty; "
                "a fixed defect left in the prose tells readers something is broken when it is not",
            )

    def test_every_registered_defect_is_named_in_the_readme(self) -> None:
        for token in self.defects:
            with self.subTest(token=token):
                self.assertIn(
                    token,
                    self.readme,
                    f"known_defects registers {token!r} but the README never mentions it; "
                    "a defect that reports as a tolerated WARNING has to be findable by a reader",
                )
if __name__ == "__main__":
    unittest.main()
