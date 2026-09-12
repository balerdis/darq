"""Tests for `tools.build_darq.fetch_pinned_assets`: the sha256 trust boundary between DARQ and
the pinned pegasus release, and the download step feeding it.

`download()` uses `urllib.request.urlopen`, which accepts `file://` URLs. That is exploited here
to exercise real download + hash verification against local files, with no network at all: every
asset in a synthetic `engine.pin`-shaped dict resolves to a `file://` URL pointing at a temp file
this test controls.
"""
from __future__ import annotations

import hashlib
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_darq  # noqa: E402


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_url(path: Path) -> str:
    return path.resolve().as_uri()


def _pin_for(assets: dict[str, tuple[Path, str]]) -> dict:
    """Build a minimal `engine.pin`-shaped dict. `assets` maps asset name to (source_path,
    expected_sha256) -- `expected_sha256` is deliberately a parameter so a test can pass a wrong
    one on purpose."""
    return {
        "tag": "vTEST",
        "assets": {
            name: {"url_template": _file_url(source_path), "sha256": expected}
            for name, (source_path, expected) in assets.items()
        },
    }


class FetchPinnedAssetsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.work_root = Path(tempfile.mkdtemp(prefix="darq-fetch-test-"))
        self.addCleanup(shutil.rmtree, self.work_root, ignore_errors=True)
        self.source_dir = self.work_root / "source"
        self.source_dir.mkdir()
        self.cache_dir = self.work_root / "cache"

        # Every entry in build_darq.PINNED_ASSETS must be present in the pin dict, or
        # fetch_pinned_assets raises a KeyError before it ever gets to hashing -- give each a
        # distinct, valid source file so tests can then corrupt exactly one asset's expectation.
        self.sources: dict[str, Path] = {}
        for asset_name in build_darq.PINNED_ASSETS:
            path = self.source_dir / asset_name.replace("/", "_")
            path.write_bytes(f"content of {asset_name}\n".encode("utf-8"))
            self.sources[asset_name] = path

    def _pin_with_correct_hashes(self) -> dict:
        return _pin_for(
            {name: (path, _sha256(path.read_bytes())) for name, path in self.sources.items()}
        )

    def test_a_matching_hash_is_accepted_and_the_asset_is_downloaded(self) -> None:
        pin = self._pin_with_correct_hashes()

        paths = build_darq.fetch_pinned_assets(pin, self.cache_dir, offline=False)

        for asset_name, source_path in self.sources.items():
            downloaded = paths[asset_name]
            self.assertTrue(downloaded.is_file())
            self.assertEqual(downloaded.read_bytes(), source_path.read_bytes())

    def test_a_mismatched_hash_is_a_hard_refusal_naming_the_asset(self) -> None:
        pin = self._pin_with_correct_hashes()
        tampered_asset = "pegasus"
        pin["assets"][tampered_asset]["sha256"] = "0" * 64

        with self.assertRaises(build_darq.BuildError) as ctx:
            build_darq.fetch_pinned_assets(pin, self.cache_dir, offline=False)

        message = str(ctx.exception)
        self.assertIn(tampered_asset, message)
        self.assertIn("REFUSED", message)
        self.assertIn("0" * 64, message)

    def test_a_mismatched_hash_still_refuses_even_if_it_is_the_last_asset_checked(self) -> None:
        """`fetch_pinned_assets` downloads every asset before verifying any of them -- confirm the
        mismatch is still caught even when it is not the first asset in `PINNED_ASSETS`."""
        pin = self._pin_with_correct_hashes()
        tampered_asset = build_darq.PINNED_ASSETS[-1]
        pin["assets"][tampered_asset]["sha256"] = "f" * 64

        with self.assertRaises(build_darq.BuildError) as ctx:
            build_darq.fetch_pinned_assets(pin, self.cache_dir, offline=False)

        self.assertIn(tampered_asset, str(ctx.exception))

    def test_no_partial_asset_is_treated_as_verified_when_one_asset_mismatches(self) -> None:
        """A hard refusal must stop the build before anything downstream can use a supposedly
        verified asset -- confirm the exception actually propagates rather than being caught and
        turned into a warning anywhere in fetch_pinned_assets."""
        pin = self._pin_with_correct_hashes()
        pin["assets"]["pegasus"]["sha256"] = "1" * 64
        try:
            build_darq.fetch_pinned_assets(pin, self.cache_dir, offline=False)
            self.fail("expected BuildError to propagate")
        except build_darq.BuildError:
            pass

    def test_a_source_url_that_does_not_resolve_raises_rather_than_silently_skipping(self) -> None:
        pin = self._pin_with_correct_hashes()
        missing = self.work_root / "does-not-exist"
        pin["assets"]["pegasus"]["url_template"] = _file_url(missing)

        with self.assertRaises(Exception) as ctx:
            build_darq.fetch_pinned_assets(pin, self.cache_dir, offline=False)
        # urllib surfaces this as a URLError; the important behaviour is that it is never
        # swallowed, not the exact exception class.
        self.assertNotIsInstance(ctx.exception, build_darq.BuildError)

    def test_offline_with_no_cached_file_falls_back_to_downloading_it(self) -> None:
        """Documents actual behaviour, which is looser than `--offline`'s own docstring/CLI help
        promise ("reuse whatever is already in the cache dir"): `fetch_pinned_assets` only *skips*
        the download when `offline` is set AND the file is already cached; if it is not cached, it
        silently falls back to fetching from `url_template` regardless of `offline`. This is a
        real discrepancy worth flagging (not a DARQ security boundary -- verification still runs
        unconditionally either way -- but the flag does not do what its own docs claim), reported
        rather than fixed here since D8's scope is testing, not changing `--offline`'s semantics."""
        pin = self._pin_with_correct_hashes()

        paths = build_darq.fetch_pinned_assets(pin, self.cache_dir, offline=True)

        self.assertTrue(paths["pegasus"].is_file())

    def test_offline_with_no_cached_file_and_no_resolvable_source_still_raises(self) -> None:
        """The one case `--offline` truly cannot paper over: cache empty and the URL does not
        resolve either. This still raises (see `test_a_source_url_that_does_not_resolve_raises`
        for the same behaviour with `offline=False`) -- `offline` is never a way to make a
        genuinely absent asset look like success."""
        pin = self._pin_with_correct_hashes()
        pin["assets"]["pegasus"]["url_template"] = _file_url(self.work_root / "does-not-exist")

        with self.assertRaises(Exception) as ctx:
            build_darq.fetch_pinned_assets(pin, self.cache_dir, offline=True)
        self.assertNotIsInstance(ctx.exception, build_darq.BuildError)


if __name__ == "__main__":
    unittest.main()
