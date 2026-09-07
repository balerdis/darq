"""Unit tests for the pure helpers in ``tools.build_darq``.

`format_checksum_sidecar` is the only pure logic this module adds beyond what already existed:
everything else new here (`run_build_installer`, the extended `fetch_pinned_assets` asset list)
is I/O -- downloading, invoking `build_installer.py`, writing files -- and is exercised instead by
`tools/check.sh` actually building and verifying `dist/install.sh` end to end.
"""
from __future__ import annotations

import sys
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


if __name__ == "__main__":
    unittest.main()
