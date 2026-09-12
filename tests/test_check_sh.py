"""Tests for `tools/check.sh`'s own argument-parsing logic: `--offline`, `--no-build`, and that an
unknown argument exits 2. Exercised by actually running the script and reading its exit code --
there is no other way to test bash argument parsing.

Recursion guard: `tools/check.sh`'s own "unit tests" step runs `python3 -m unittest discover -s
tests`, which picks up this very file. A test here that shells out to `check.sh` would otherwise
launch check.sh -> discover -> this file -> check.sh -> ... forever. `DARQ_CHECK_SH_TEST_NESTED`
breaks that: any test that invokes `check.sh` sets it in the child's environment, and every test in
this file skips immediately if it is already set in its own environment -- so a real invocation
runs check.sh exactly once, one level deep.
"""
from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK_SH = ROOT / "tools" / "check.sh"
_NESTED_GUARD = "DARQ_CHECK_SH_TEST_NESTED"

DIST_DARQ = ROOT / "dist" / "darq"

#: The four assets `tools.build_darq.PINNED_ASSETS` fetches (or, under `--offline`, reuses) into
#: `build/cache/`. Kept as a literal tuple rather than imported from `build_darq` so this module
#: has no import-time dependency on it -- this list is deliberately duplicated, not derived, to
#: keep the "did we check the cache before touching --offline" logic below trivially auditable.
_REQUIRED_CACHED_ASSETS = ("pegasus", "build_zipapp.py", "build_installer.py", "install.sh")
BUILD_CACHE = ROOT / "build" / "cache"


def _missing_cached_assets() -> list[str]:
    return [name for name in _REQUIRED_CACHED_ASSETS if not (BUILD_CACHE / name).is_file()]


def _run_check_sh(*args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env[_NESTED_GUARD] = "1"
    return subprocess.run(
        ["bash", str(CHECK_SH), *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )


@unittest.skipIf(os.environ.get(_NESTED_GUARD), "nested invocation from check.sh itself; see module docstring")
class CheckShArgumentParsingTests(unittest.TestCase):
    def test_an_unknown_argument_exits_2_without_running_anything_else(self) -> None:
        result = _run_check_sh("--not-a-real-flag")

        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown argument: --not-a-real-flag", result.stderr)
        # It exits before the "== unit tests ==" banner ever prints.
        self.assertNotIn("unit tests", result.stdout)

    def test_no_build_skips_the_build_step_and_still_verifies_the_existing_dist(self) -> None:
        if not DIST_DARQ.is_file():
            self.skipTest(
                f"{DIST_DARQ} does not exist; run tools/build_darq.py first to produce it "
                "(this test only verifies an existing dist/, it never builds one)"
            )

        result = _run_check_sh("--offline", "--no-build")

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("== unit tests ==", result.stdout)
        self.assertIn("== check_no_engine_code.py ==", result.stdout)
        self.assertNotIn("== build_darq.py ==", result.stdout)
        self.assertIn("== verify_darq.py ==", result.stdout)
        self.assertIn("All checks passed.", result.stdout)

    def test_offline_alone_runs_the_build_step_too(self) -> None:
        # `--offline` alone (no `--no-build`) runs `build_darq.py --offline`, which reaches
        # `fetch_pinned_assets(..., offline=True)`. Since the fix documented in
        # tests/test_fetch_pinned_assets.py, that function hard-refuses (raising `BuildError`,
        # never touching the network) for any asset not already in `build/cache/`, instead of the
        # old silent fall-back to a real download. The guard below is still worth keeping: it turns
        # what would now be a hard build failure on an unpopulated cache into an honest skip that
        # names what to populate, rather than making this test itself fail on a machine that simply
        # hasn't run a build yet.
        missing = _missing_cached_assets()
        if missing:
            self.skipTest(
                f"build/cache/ is missing {missing}; populate build/cache/ with all of "
                f"{list(_REQUIRED_CACHED_ASSETS)} first (e.g. run tools/build_darq.py once "
                "with network access) -- otherwise --offline would now hard-refuse instead of "
                "building, for the missing asset(s)"
            )

        result = _run_check_sh("--offline")

        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("== build_darq.py ==", result.stdout)
        self.assertIn("OFFLINE: reusing cached", result.stdout)
        self.assertIn("All checks passed.", result.stdout)


if __name__ == "__main__":
    unittest.main()
