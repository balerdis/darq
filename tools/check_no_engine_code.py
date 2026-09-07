#!/usr/bin/env python3
"""The no-fork guard: DARQ's repo tree must contain zero engine code and zero copies of engine
content. This is the mechanism that keeps DARQ a *distribution*, never a fork -- if the engine
ever needs a change, the answer is upstream, release, bump `engine.pin`, never "just edit it here".

    python3 tools/check_no_engine_code.py

Deliberately a real check that can fail, not a comment expressing an intention -- see
`tests/test_check_no_engine_code.py`, which creates a genuine violation, runs this guard against
it, and asserts it fails, before removing the violation again.

Three independent checks, because each one alone has a blind spot the next closes: a directory
named like an engine layer, a file named like a known engine content artifact, and a Python file
that imports the engine package. The third is the one that catches a single `content.py` copied
to the repo root, where no directory name and no content filename would give it away.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: Directories that exist only inside the hexagonal engine layout (`src/pegasus/{core,ports,
#: infra,adapters,tui}`). DARQ never has a `src/pegasus` tree at all -- finding any of these
#: in the repo means engine code was copied in.
_ENGINE_LAYER_DIRS = frozenset({"core", "ports", "adapters", "tui", "infra"})

#: Content artifacts the engine itself ships (a distinctive sample, deliberately not exhaustive --
#: `_ENGINE_IMPORT` below is what catches the general case). A copy landing in this repo is
#: exactly the fork DARQ's whole design exists to prevent.
_ENGINE_CONTENT_MARKERS = (
    "king-pegasus.md",
    "pegasus-orchestrator.md",
    "session-start.txt",
)

#: An import of the engine package. DARQ's own tooling transforms and packages engine files as
#: *data* and never imports the engine, so any Python file here that imports `pegasus` is a copy
#: of engine source, whatever it happens to be named or wherever it happens to sit.
_ENGINE_IMPORT = re.compile(r"^\s*(?:from\s+pegasus[.\s]|import\s+pegasus\b)", re.MULTILINE)


class NoEngineCodeViolation(RuntimeError):
    """The repo tree contains something only the engine itself should own."""


def repo_paths(root: Path = ROOT) -> list[Path]:
    """Every path git considers part of this repo: tracked files, plus untracked ones that
    `.gitignore` does not exclude.

    Scope comes from git rather than from a hardcoded list of directory names to skip, so
    `.gitignore` stays the single source of truth for what the build owns and this guard
    ignores. A second, parallel list would be free to disagree with it -- and a guard that
    keeps skipping a directory `.gitignore` no longer excludes is a guard that reports PASS
    while engine code sits committed beside it. Untracked-but-not-ignored files are in scope
    on purpose: the violation this guard exists to catch should be caught *before* it is
    committed, not after.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            capture_output=True, text=True, check=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        # Never degrade to "scan everything" or "scan nothing": both would let this guard report
        # something it did not actually verify.
        raise NoEngineCodeViolation(
            f"cannot determine the repo's file scope from git at {root}: {error}"
        ) from error
    return [root / name for name in result.stdout.split("\0") if name]


def find_engine_layer_dirs(paths: list[Path], root: Path) -> list[Path]:
    """Every directory named exactly like one of the engine's hexagonal layers."""
    found = set()
    for path in paths:
        for parent in path.relative_to(root).parents:
            if parent.name in _ENGINE_LAYER_DIRS:
                found.add(root / parent)
    return sorted(found)


def find_engine_content_copies(paths: list[Path], root: Path) -> list[Path]:
    """Every file whose name exactly matches a known engine content artifact."""
    return sorted(path for path in paths if path.name in _ENGINE_CONTENT_MARKERS)


def find_engine_python_copies(paths: list[Path], root: Path) -> list[Path]:
    """Every Python file that imports the engine package -- i.e. every copy of engine source."""
    found = []
    for path in paths:
        if path.suffix != ".py" or not path.is_file():
            continue
        try:
            body = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if _ENGINE_IMPORT.search(body):
            found.append(path)
    return sorted(found)


def check(root: Path = ROOT) -> list[str]:
    """Every violation found, as human-readable messages. Empty means the tree is clean."""
    paths = repo_paths(root)
    violations = []
    for path in find_engine_layer_dirs(paths, root):
        violations.append(
            f"{path.relative_to(root)}: directory name matches an engine hexagonal layer "
            f"({'/'.join(sorted(_ENGINE_LAYER_DIRS))}); DARQ must never contain engine source"
        )
    for path in find_engine_content_copies(paths, root):
        violations.append(
            f"{path.relative_to(root)}: filename matches a known engine content artifact; "
            f"DARQ must consume this from the pinned release, never commit a copy"
        )
    for path in find_engine_python_copies(paths, root):
        violations.append(
            f"{path.relative_to(root)}: imports the engine package; DARQ's own tooling treats "
            f"engine files as data and never imports them, so this is a copy of engine source"
        )
    return violations


def main() -> int:
    try:
        violations = check()
    except NoEngineCodeViolation as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    if not violations:
        print("PASS: no engine code or content copies found in the DARQ repo tree")
        return 0
    print(f"FAIL: {len(violations)} violation(s):", file=sys.stderr)
    for violation in violations:
        print(f"  - {violation}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
