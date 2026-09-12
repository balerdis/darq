"""Unit tests for the pure helpers in ``tools.build_darq``.

`format_checksum_sidecar` is the only pure logic this module adds beyond what already existed:
everything else new here (`run_build_installer`, the extended `fetch_pinned_assets` asset list)
is I/O -- downloading, invoking `build_installer.py`, writing files -- and is exercised instead by
`tools/check.sh` actually building and verifying `dist/install.sh` end to end.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_darq  # noqa: E402


class FormatChecksumSidecarTests(unittest.TestCase):
    def test_matches_the_format_build_zipapp_already_writes(self) -> None:
        text = build_darq.format_checksum_sidecar("abc123", "install.sh")
        self.assertEqual(text, "abc123  install.sh\n")

    def test_single_trailing_newline_only(self) -> None:
        text = build_darq.format_checksum_sidecar("deadbeef", "darq")
        self.assertEqual(text.count("\n"), 1)
        self.assertTrue(text.endswith("\n"))


class PinnedAssetsTests(unittest.TestCase):
    def test_pinned_assets_include_the_installer_pair(self) -> None:
        self.assertIn("build_installer.py", build_darq.PINNED_ASSETS)
        self.assertIn("install.sh", build_darq.PINNED_ASSETS)
        self.assertIn("pegasus", build_darq.PINNED_ASSETS)
        self.assertIn("build_zipapp.py", build_darq.PINNED_ASSETS)

    def test_engine_pin_declares_every_pinned_asset(self) -> None:
        pin = build_darq.load_pin()
        for asset_name in build_darq.PINNED_ASSETS:
            self.assertIn(asset_name, pin["assets"], f"engine.pin is missing {asset_name!r}")
            self.assertIn("sha256", pin["assets"][asset_name])
            self.assertIn("url_template", pin["assets"][asset_name])


class RawContentCopyTests(unittest.TestCase):
    """`persist_raw_content_copy` is the fix for D1: a real, unrebranded copy of the engine's
    content tree, kept outside anything `run_build_zipapp`/`run_build_installer` packages."""

    def setUp(self) -> None:
        self.work_root = Path(tempfile.mkdtemp(prefix="darq-build-test-"))
        self.addCleanup(shutil.rmtree, self.work_root, ignore_errors=True)

    def test_copies_every_file_byte_for_byte_without_touching_the_source(self) -> None:
        content_root = self.work_root / "extracted" / "pegasus" / "content"
        (content_root / "agents").mkdir(parents=True)
        (content_root / "agents" / "pegasus-orchestrator.md").write_text(
            "pegasus-orchestrator body\n", encoding="utf-8"
        )
        raw_dir = self.work_root / "extracted-raw" / "content"

        build_darq.persist_raw_content_copy(content_root, raw_dir)

        self.assertEqual(
            (raw_dir / "agents" / "pegasus-orchestrator.md").read_text(encoding="utf-8"),
            "pegasus-orchestrator body\n",
        )
        # The source is untouched -- this runs *before* apply_to_tree, not instead of it.
        self.assertEqual(
            (content_root / "agents" / "pegasus-orchestrator.md").read_text(encoding="utf-8"),
            "pegasus-orchestrator body\n",
        )

    def test_a_stale_raw_copy_from_a_previous_build_is_replaced_not_merged(self) -> None:
        content_root = self.work_root / "extracted" / "pegasus" / "content"
        content_root.mkdir(parents=True)
        (content_root / "fresh.md").write_text("fresh\n", encoding="utf-8")
        raw_dir = self.work_root / "extracted-raw" / "content"
        raw_dir.mkdir(parents=True)
        (raw_dir / "stale.md").write_text("stale\n", encoding="utf-8")

        build_darq.persist_raw_content_copy(content_root, raw_dir)

        self.assertTrue((raw_dir / "fresh.md").is_file())
        self.assertFalse((raw_dir / "stale.md").exists())

    def test_default_raw_content_dir_sits_outside_the_extracted_package_tree_that_gets_packaged(
        self,
    ) -> None:
        """`run_build_zipapp`/`run_build_installer` are invoked with `package` (i.e.
        `<work_dir>/extracted/pegasus`) as their source. `DEFAULT_RAW_CONTENT_DIR` must not be a
        descendant of that tree, or a real build would ship it inside `dist/darq`."""
        package_tree = build_darq.DEFAULT_WORK_DIR / "extracted" / "pegasus"
        self.assertNotIn(package_tree, build_darq.DEFAULT_RAW_CONTENT_DIR.parents)
        self.assertNotEqual(package_tree, build_darq.DEFAULT_RAW_CONTENT_DIR)

    def test_raw_content_dir_for_derives_from_the_given_work_dir(self) -> None:
        """Two builds run with different `--work-dir` values must not collide on the same raw
        content copy location. `raw_content_dir_for` must place the copy as a sibling of
        `<work_dir>/extracted`, inside `work_dir` itself -- never at a fixed path."""
        custom_work_dir = self.work_root / "somewhere-else" / "work"

        result = build_darq.raw_content_dir_for(custom_work_dir)

        self.assertEqual(result, custom_work_dir / "extracted-raw" / "content")
        self.assertNotEqual(result, build_darq.DEFAULT_RAW_CONTENT_DIR)

    def test_raw_content_dir_for_preserves_todays_default_path_for_the_default_work_dir(self) -> None:
        """The current default behavior (no `--work-dir` passed) must not change."""
        self.assertEqual(
            build_darq.raw_content_dir_for(build_darq.DEFAULT_WORK_DIR),
            build_darq.DEFAULT_RAW_CONTENT_DIR,
        )


if __name__ == "__main__":
    unittest.main()
