"""No file in this fork may name the upstream engine's module path.

This fork's package was renamed from `pegasus` to `darq`, so `pegasus.core`,
`pegasus.cli` and their siblings name modules that do not exist here. A
reference to one is a dead pointer: a reader following it finds nothing, and
so does anyone grepping for the module a docstring claims to explain.

The rename itself was mechanical and complete. What keeps re-introducing
these is transport: a fix authored upstream and brought over with
`git cherry-pick` carries upstream's own prose, and upstream correctly names
its modules `pegasus.*`. The cherry-pick applies cleanly -- git tracks the
directory rename -- and the stale pointer rides in with it, unflagged,
because the brand guardians in `test_architecture.py` scan bundled adapter
assets rather than engine source prose. The first transport after the fork
introduced exactly one, in `cli.py`'s `_NUMERIC_VERSION` docstring.

Deliberately narrow: this matches a dotted module path only. The wire
identifiers that must keep saying `pegasus` forever -- the journal and report
schemas, the `pegasus_version` and `pegasus_installed` keys, the `PEGASUS_*`
environment variables, `.pegasus-` temporary files -- use an underscore, a
slash or a hyphen, never a dot followed by a package name, so none of them
match here and none needs an exemption. Prose that merely names the upstream
product does not match either; that is a separate concern and this gate does
not judge it.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: A dotted path into the upstream package: `pegasus.` followed by anything
#: that can start a Python identifier.
#:
#: This deliberately does not enumerate the modules. It did at first --
#: `(core|adapters|infra|ports|tui|cli|content)` -- and an adversarial review
#: found the hole immediately: the list left out `__main__`, a real module
#: upstream that upstream's own `test_version_guard.py` imports by name, so a
#: transported reference to it would have ridden in unflagged. An enumeration
#: of what exists is a list somebody has to remember to widen, and the whole
#: reason this gate exists is that nobody remembers.
#:
#: Matching on the dot is what keeps it safe. Every identifier that must keep
#: saying `pegasus` forever separates the word with an underscore, a slash or
#: a hyphen -- `pegasus_version`, `pegasus/cli-report/v1`,
#: `pegasus-harness/journal/v4`, `PEGASUS_SKILL_ROOTS`, `.pegasus-`,
#: `pegasus-doctor` -- and never with a dot followed by a letter, so none of
#: them can match here no matter how the engine grows.
#: Spellings where `pegasus.` IS followed by a letter and must survive anyway,
#: with the reason each one is here. Today there is one: `pegasus.md`, the
#: identity-blind default filename `Layout` carries for the Claude Code system
#: prompt -- a wire spelling this engine keeps deliberately, documented in
#: `adapters/claudecode/layout.py` and in `test_architecture.py`'s own
#: allowlist. It is a filename, not a module path, and the dot in front of a
#: file extension is indistinguishable from the dot in front of a package.
#:
#: Enumerating the exceptions is the opposite bet from enumerating the
#: modules, and it is the right one for a gate. A missing module fails OPEN --
#: the defect ships unseen, which is exactly how `__main__` slipped past the
#: first version of this pattern. A missing exception fails CLOSED -- a benign
#: spelling gets flagged, somebody reads it, and it lands here with its reason
#: written down. A guardian should be wrong in the direction that gets looked at.
PROTECTED_DOTTED_SPELLINGS = ("md",)

UPSTREAM_MODULE_PATH = re.compile(
    r"\bpegasus\.(?!(?:" + "|".join(PROTECTED_DOTTED_SPELLINGS) + r")\b)[A-Za-z_]"
)

SCANNED_DIRS = ("src/darq", "tests", "tools")

#: The one file whose `pegasus.*` paths are deliberate, with the reason it is
#: exempt rather than fixed: `test_architecture.py` builds throwaway packages
#: named `pegasus` on purpose, because the layering rule under test keys off
#: `source.name` and the probe has to reproduce that exact name to exercise
#: it. Those strings are the probe's input, not a pointer at a real module.
#: Listed as one exact path so a second file can never join it in silence.
EXEMPT = frozenset({"tests/test_architecture.py"})

#: This file is excluded from its own scan. Its docstring explains the shape
#: it forbids and one of its tests feeds that shape to the pattern on purpose,
#: so scanning itself would report its own prose as the defect -- the failure
#: mode where a detector measures something it brought along itself.
SELF = "tests/test_upstream_module_paths.py"


def _python_files() -> list[Path]:
    return sorted(
        path
        for directory in SCANNED_DIRS
        for path in (ROOT / directory).rglob("*.py")
        if "__pycache__" not in path.parts
        and str(path.relative_to(ROOT)) not in EXEMPT
        and str(path.relative_to(ROOT)) != SELF
    )


class NoUpstreamModulePathTest(unittest.TestCase):
    def test_there_are_files_to_scan(self):
        self.assertTrue(_python_files(), "no Python files found -- the scan target drifted")

    def test_no_file_names_an_upstream_module(self):
        offenders = {}
        for path in _python_files():
            hits = [
                f"{index}: {line.strip()}"
                for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
                if UPSTREAM_MODULE_PATH.search(line)
            ]
            if hits:
                offenders[str(path.relative_to(ROOT))] = hits
        self.assertEqual(
            offenders,
            {},
            "a file names a module path from the upstream engine, which does not exist in this fork -- "
            f"this is what a transported commit brings in with it; rename it to `darq.*`: {offenders}",
        )

    def test_a_transported_pointer_would_be_flagged(self):
        """The gate catches the exact shape the first transport introduced,
        and the dunder modules an enumerated pattern left out."""
        for prose in (
            "`SAFE_VERSION` (`pegasus.core.identity`) is wider",
            "from pegasus.__main__ import guard",
            "see `pegasus.__init__`",
            "a module added upstream tomorrow: pegasus.whatever",
        ):
            with self.subTest(prose=prose):
                self.assertTrue(UPSTREAM_MODULE_PATH.search(prose))

    def test_the_protected_filename_is_not_flagged(self):
        """`pegasus.md` is a filename this engine keeps on purpose, not a
        pointer at a module, and it has to survive the widened pattern."""
        self.assertIsNone(UPSTREAM_MODULE_PATH.search('SYSTEM_PROMPT = "pegasus.md"'))

    def test_every_protected_spelling_still_appears_in_the_tree(self):
        """An exception may not outlive its reason: each protected spelling
        must still be somewhere in the engine source, or it is dead weight
        widening the hole for whatever lands on that spelling next."""
        sources = "\n".join(
            path.read_text(encoding="utf-8") for path in (ROOT / "src/darq").rglob("*.py")
        )
        for suffix in PROTECTED_DOTTED_SPELLINGS:
            with self.subTest(suffix=suffix):
                self.assertIn(f"pegasus.{suffix}", sources, f"pegasus.{suffix} is no longer in the tree")

    def test_the_exemption_still_names_a_file_that_needs_it(self):
        """The exemption may not outlive its reason. Each exempt path must
        exist and must still build the scratch package the exemption is for --
        the day `test_architecture.py` stops doing that, the exemption is dead
        weight hiding whatever lands there next."""
        for relative in sorted(EXEMPT):
            path = ROOT / relative
            with self.subTest(path=relative):
                self.assertTrue(path.is_file(), f"{relative} does not exist")
                self.assertIn(
                    "_write_scratch_pegasus",
                    path.read_text(encoding="utf-8"),
                    f"{relative} no longer builds the scratch package its exemption was written for",
                )

    def test_a_wire_identifier_is_not_flagged(self):
        """Every identifier that must keep saying `pegasus` forever survives."""
        for identifier in (
            'SCHEMA = "pegasus-harness/journal/v4"',
            '"pegasus/cli-report/v1"',
            '"pegasus_version": runtime.identity.version,',
            'entry["pegasus_installed"]',
            'PEGASUS_SKILL_REGISTRY_BIN',
            'TEMPORARY_PREFIX = ".pegasus-"',
            'CLIENT_NAME = "pegasus-doctor"',
        ):
            with self.subTest(identifier=identifier):
                self.assertIsNone(UPSTREAM_MODULE_PATH.search(identifier))


if __name__ == "__main__":
    unittest.main()
