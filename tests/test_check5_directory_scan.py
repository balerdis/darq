"""Unit tests for the widened check-5 corpus in ``tools.verify_darq``.

These exercise ``_scan_corpus_files`` and ``run_brand_leak_directory_scan`` directly against a
synthetic scratch ``home`` built under ``tempfile.mkdtemp`` -- never the real ``$HOME``, and never
a real built ``darq`` binary (that end-to-end path is covered by ``tools/check.sh`` itself). This
lets the three closed gaps of check 5's former "Known limitations" section be proven without a
subprocess:

  - the data dir (``<home>/.local/share/darq``) is now part of the scanned corpus;
  - a file's own *name*, not just its content, is classified;
  - a file that fails to decode as UTF-8 produces a report line instead of vanishing silently.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import verify_darq  # noqa: E402


class ScanCorpusFilesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp(prefix="darq-check5-test-"))
        self.addCleanup(shutil.rmtree, self.home, ignore_errors=True)

    def test_files_under_config_opencode_are_included(self) -> None:
        config_file = self.home / ".config" / "opencode" / "a.json"
        config_file.parent.mkdir(parents=True)
        config_file.write_text("{}", encoding="utf-8")

        files = verify_darq._scan_corpus_files(self.home)

        self.assertIn(config_file, files)

    def test_files_under_data_dir_are_now_included(self) -> None:
        data_file = self.home / ".local" / "share" / "darq" / "journal" / "v4" / "entry.json"
        data_file.parent.mkdir(parents=True)
        data_file.write_text("{}", encoding="utf-8")

        files = verify_darq._scan_corpus_files(self.home)

        self.assertIn(data_file, files)

    def test_missing_directories_yield_no_files_rather_than_erroring(self) -> None:
        files = verify_darq._scan_corpus_files(self.home)
        self.assertEqual(files, [])


class RunBrandLeakDirectoryScanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp(prefix="darq-check5-test-"))
        self.addCleanup(shutil.rmtree, self.home, ignore_errors=True)
        self.protected_tokens = verify_darq.parse_protected_tokens(verify_darq.load_rebrand_config())
        self.accepted_residue = verify_darq.parse_reason_register(
            "accepted_residue", verify_darq.load_rebrand_config()
        )
        self.known_defects = verify_darq.parse_reason_register(
            "known_defects", verify_darq.load_rebrand_config()
        )

    def _write(self, relative: str, data: bytes) -> Path:
        path = self.home / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def _scan(self) -> tuple[verify_darq.Report, list[str]]:
        report = verify_darq.Report()
        corpus = verify_darq.run_brand_leak_directory_scan(
            self.home, report, self.protected_tokens, self.accepted_residue, self.known_defects
        )
        return report, corpus

    def test_brand_in_a_file_name_under_the_scanned_tree_is_reported_as_a_leak(self) -> None:
        self._write(".config/opencode/pegasus-notes.txt", b"nothing branded in the body\n")

        report, _ = self._scan()

        self.assertTrue(
            any("pegasus-notes.txt" in failure for failure in report.failures),
            report.failures,
        )

    def test_brand_in_the_data_dir_content_is_reported(self) -> None:
        self._write(
            ".local/share/darq/journal/notes.txt",
            b"this journal entry was written by pegasus itself\n",
        )

        report, _ = self._scan()

        self.assertTrue(
            any("notes.txt" in failure and "pegasus itself" in failure for failure in report.failures),
            report.failures,
        )

    def test_a_file_that_does_not_decode_as_utf8_produces_a_warning_line_naming_it(self) -> None:
        self._write(".config/opencode/binary.bin", b"\xff\xfe\x00\x01\x02\xff")

        report, corpus = self._scan()

        self.assertEqual(report.failures, [])
        self.assertTrue(
            any("binary.bin" in warning for warning in report.warnings),
            report.warnings,
        )
        # Its content is never appended to the corpus (it was never read), but it must not
        # silently disappear from the report the way the old bare `continue` made it disappear.
        self.assertFalse(any("\xff" in text for text in corpus))

    def test_protected_token_in_the_data_dir_is_still_silent(self) -> None:
        self._write(
            ".local/share/darq/journal/v4/entry.json",
            b'{"schema": "pegasus-harness/journal/v4", "pegasus_version": "5.34.0"}',
        )

        report, _ = self._scan()

        self.assertEqual(report.failures, [])

    def test_clean_tree_produces_no_findings(self) -> None:
        self._write(".config/opencode/config.json", b'{"cli": "opencode"}')
        self._write(".local/share/darq/journal/v4/entry.json", b'{"ok": true}')

        report, _ = self._scan()

        self.assertEqual(report.failures, [])
        self.assertEqual(report.warnings, [])


if __name__ == "__main__":
    unittest.main()
