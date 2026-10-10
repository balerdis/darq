"""Strict TDD evidence is append-only: one record per apply batch, plus a ledger.

apply-progress is one artifact rewritten by every batch. In a real change it
was rewritten 15 times; each rewrite demoted the previous batch's evidence
tables into compressed "historical" sections until the exact RED commands of
the first tasks were gone, verify flagged them CRITICAL, and archive refused.
A rule that only says "copy rows verbatim" does not survive a long rewrite, so
the evidence moved out of the rewritten artifact: each batch writes its own
record once, and apply-progress keeps only a short ledger of them.
"""
from __future__ import annotations

import unittest
from pathlib import Path

CONTENT = Path(__file__).resolve().parents[1] / "src" / "darq" / "content"
APPLY = (CONTENT / "skills" / "sdd-apply" / "SKILL.md").read_text(encoding="utf-8")
STRICT_APPLY = (CONTENT / "skills" / "sdd-apply" / "strict-tdd.md").read_text(encoding="utf-8")
VERIFY = (CONTENT / "skills" / "sdd-verify" / "strict-tdd-verify.md").read_text(encoding="utf-8")
ENGRAM = (CONTENT / "mcp" / "engram.md").read_text(encoding="utf-8")
OPENSPEC = (CONTENT / "skills" / "_shared" / "openspec-convention.md").read_text(encoding="utf-8")
ARCHIVE = (CONTENT / "skills" / "sdd-archive" / "SKILL.md").read_text(encoding="utf-8")

KEY = "sdd/{change-name}/apply-evidence/{n}"


def flat(text: str) -> str:
    return " ".join(text.replace("│", " ").split())


class ApplyWritesOneRecordPerBatch(unittest.TestCase):
    def test_engram_key_pattern_and_numbering(self) -> None:
        text = flat(APPLY)
        self.assertIn(f"`topic_key: {KEY}`", text)
        self.assertIn("1 for the first batch", text)
        self.assertIn("one more than the highest batch number in the apply-progress `## TDD Evidence Ledger`", text)

    def test_record_is_saved_before_apply_progress(self) -> None:
        text = flat(APPLY)
        self.assertIn("as its OWN artifact BEFORE writing apply-progress", text)

    def test_record_is_write_once(self) -> None:
        text = flat(APPLY)
        self.assertIn("never `mem_update` it", text)
        self.assertIn("never save again under its key", text)
        self.assertIn("A correction to an earlier record goes into THIS batch's own record, stated as a correction", text)
        self.assertIn("earlier records stay untouched", text)

    def test_openspec_hybrid_none(self) -> None:
        text = flat(APPLY)
        self.assertIn("`openspec/changes/{change-name}/apply-evidence/{n}.md`", text)
        self.assertIn("**hybrid**: both", text)
        self.assertIn("**none**: nothing persisted", text)

    def test_return_summary_keeps_the_table(self) -> None:
        self.assertIn("### TDD Cycle Evidence", STRICT_APPLY)
        self.assertIn("apply-evidence/{n}", STRICT_APPLY)


class ApplyProgressKeepsALedger(unittest.TestCase):
    def test_ledger_section_and_line_content(self) -> None:
        text = flat(APPLY)
        self.assertIn("`## TDD Evidence Ledger`", text)
        self.assertIn("one line per batch in a fixed format", text)

    def test_ledger_lines_are_copied_exactly(self) -> None:
        text = flat(APPLY)
        self.assertIn("Copy every existing ledger line exactly, never dropping, merging, reordering or rewording one, and append this batch's line", text)

    def test_reopened_task_rule(self) -> None:
        text = flat(APPLY)
        self.assertIn("A task re-opened after it was complete gets new rows in the re-opening batch's own record, marked as re-opened", text)
        self.assertIn("Its earlier rows stay in their earlier records", text)


class VerifyReadsTheRecords(unittest.TestCase):
    def test_reads_every_record_in_ledger_order(self) -> None:
        text = flat(VERIFY)
        self.assertIn('If it has a "## TDD Evidence Ledger": retrieve EVERY listed record', text)
        self.assertIn("mem_get_observation by the recorded id under engram", text)
        self.assertIn("in ledger order", text)
        self.assertIn("cross-checked against the current test run", text)

    def test_unavailable_record_is_its_own_critical(self) -> None:
        text = flat(VERIFY)
        self.assertIn("cannot be retrieved is CRITICAL", text)
        self.assertIn("evidence record unavailable: {key}", text)
        self.assertIn('a different finding from "RED has no command"', text)

    def test_no_ledger_falls_back_to_the_table(self) -> None:
        text = flat(VERIFY)
        self.assertIn("started before the ledger existed", text)
        self.assertIn('"TDD Cycle Evidence" tables inside apply-progress', text)

    def test_no_override_or_waiver(self) -> None:
        self.assertIn("No override, no waiver", flat(VERIFY))


class ConventionsListTheRecord(unittest.TestCase):
    def test_engram_convention(self) -> None:
        text = flat(ENGRAM)
        self.assertIn(f"`{KEY}`", text)
        self.assertIn("written once, never updated", text)
        self.assertNotIn("(one per batch)", text)
        self.assertIn("each batch saves under a new key", text)

    def test_openspec_convention(self) -> None:
        text = flat(OPENSPEC)
        self.assertIn("apply-evidence/", text)
        self.assertIn("`openspec/changes/{change-name}/apply-evidence/{n}.md`", text)

    def test_archive_reads_the_records_without_touching_the_gate(self) -> None:
        text = flat(ARCHIVE)
        self.assertIn("`sdd/{change-name}/apply-evidence/{n}` records", text)
        self.assertIn("Do not accept an override for CRITICAL verification issues", text)



class ReviewFixes(unittest.TestCase):
    def test_legacy_tables_kept_and_ledger_starts_at_one(self) -> None:
        text = flat(APPLY)
        self.assertIn("evidence tables from before the ledger existed", text)
        self.assertIn("keep those tables exactly as they are", text)
        self.assertIn("start the ledger at n=1", text)

    def test_verify_judges_legacy_and_ledger_together(self) -> None:
        text = flat(VERIFY)
        self.assertIn("With BOTH legacy tables and a ledger, judge the legacy tables AND every ledger record", text)

    def test_ledger_line_format(self) -> None:
        self.assertIn("`{n} | {key} | {observation id or file path} | {task ids} | {date}`", flat(APPLY))

    def test_key_existence_check_and_orphan_rule(self) -> None:
        text = flat(APPLY)
        self.assertIn("Never reuse a key", text)
        self.assertIn("compare titles exactly", text)
        self.assertIn("the file does not exist", text)
        self.assertIn("is not in the ledger", text)
        self.assertIn("add its ledger line too, and take the next free number", text)
        self.assertIn("If the ledger cannot be read, stop and report", text)
        self.assertIn("strictly sequential", text)

    def test_superseding_rows(self) -> None:
        text = flat(VERIFY)
        self.assertIn("supersedes the earlier rows for that task ONLY if it carries its own RED command and observed failure", text)
        self.assertIn("the earlier rows still stand", text)
        self.assertIn("effective latest row", text)

    def test_reopened_task_not_skipped_and_craft_wording(self) -> None:
        self.assertIn("except a task the orchestrator re-opened", flat(APPLY))
        craft = flat((CONTENT / "skills" / "_shared" / "implementation-craft.md").read_text(encoding="utf-8"))
        self.assertIn("in your return summary and in the batch's evidence record", craft)


if __name__ == "__main__":
    unittest.main()
