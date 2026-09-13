"""Guard: a disposable home built for a real `PosixFileSystem` must be
carved out of the shared scratch root -- there is exactly one way to build
one, not two that can drift apart.

The defect this guard exists to catch already happened once, in this exact
repository: `test_installation.py`'s `setUp` was a near-literal copy of
`RealHomeTestCase`'s (`tests/real_home.py`) -- down to the root-user check --
missing only the one thing that made the original fast, `dir=_scratch_root()`.
Nothing noticed. Measured in isolation: an `fsync` call takes a median of
6302 microseconds on ext4 against 1.2 microseconds on tmpfs -- roughly five
thousand times slower -- and `write_atomic` calls it twice per write. 226
writes at that ext4 median account for the entire 1.42s-per-test cost the
copied setUp carried; the fsync is not part of the cost, it is the cost.
That number happens to be large for `test_installation.py` specifically and
small for a test that writes a handful of files, but the *shape* of the
defect -- a second way to build a disposable `PosixFileSystem` home that
forgot to route through the scratch root -- is exactly as easy to reintroduce
either way, and the next test to fall into it will not always be a cheap one.

So the rule this guard holds the tree to is not "keep it fast today", it is
"one way to build this, ever": every test that constructs a real
`PosixFileSystem` and a disposable temporary directory to be its home routes
that directory through the shared place -- either by inheriting (directly, or
through a local subclass -- the pattern most real-home test files in this
suite already use) from `RealHomeTestCase`, or, where inheriting does not fit
(see `test_filesystem.py`'s own reason below), by passing
`dir=_scratch_root()` to `tempfile.TemporaryDirectory()` explicitly.

A class trips this guard when it constructs a `PosixFileSystem` and also
builds a `tempfile.TemporaryDirectory()` whose `dir=` keyword is missing
entirely, or is present but not a call to something named `_scratch_root` --
matched by the called name, same as this repository's other AST guards
(`test_tools_have_coverage.py`), not by which module defined it, so a local
`_scratch_root()` (as `test_tui_pty.py` already has its own copy of) counts
exactly like the one imported from `real_home.py`. A name reaching the module
through `from module import Name as Alias` is resolved back to `Name` before
that comparison, so `from tempfile import TemporaryDirectory as TD` and a
later `TD()` is seen for what it is; `import tempfile as tf` needed no such
resolution to begin with; because the call is `tf.TemporaryDirectory()`, the
attribute actually being read off is already `TemporaryDirectory`, alias or
not.

Two scopes are checked, not one, because a construction that never appears
in a class's own lexical body -- e.g. a module-level `_make_fs()` /
`_make_dir()` helper that a `setUp` merely calls -- is invisible to a
class-scoped walk no matter how carefully that walk is written:

  1. Class-scoped: does this specific class's own body construct a real
     `PosixFileSystem` and an unrouted `TemporaryDirectory()`? This is what
     names the offending class in the failure message, and it is what runs
     first.
  2. Module-scoped fallback: only for a file where the class-scoped pass
     found nothing and no class in the file inherits `RealHomeTestCase` --
     does the *module as a whole* (every function and class in it) contain
     both a real `PosixFileSystem` construction and an unrouted
     `TemporaryDirectory()`? If a class-scoped hit already exists, or some
     class in the file already routes through `RealHomeTestCase`, the
     module-level pass does not run, on the theory that a file that already
     demonstrates the shared form is not the shape this fallback exists to
     catch. This is coarser on purpose -- it cannot say which construction
     paired with which, only that the file as a whole holds both shapes
     unguarded -- which is why it reports the pseudo-name `<module>` instead
     of a class, and why a hit here is more likely than a class-scoped hit to
     need a reasoned exception in `NOT_ROUTED_THROUGH_SCRATCH_ROOT` rather
     than a code fix.

THE LIMIT, STATED PLAINLY: this is a static, syntactic check over one file's
AST. It follows a call to a name (bare or import-aliased) and, for a class,
to base classes defined in the same file. It follows nothing else. Concretely,
it cannot and does not see:

  - A factory in a *different* module -- `from helpers import make_home; ...;
    self.fs = make_home()` -- where `make_home` builds the `PosixFileSystem`
    and the `TemporaryDirectory()` somewhere this guard never parses.
  - Construction reached through `getattr`, a dict/registry of callables, a
    decorator, `functools.partial`, or any other indirection where the name
    actually called is not a literal identifier or attribute access at the
    call site.
  - A base class defined outside this file (e.g. imported from a different
    test module) -- `_inherits_real_home` only walks classes it can see in
    the same source tree, so inheriting from an out-of-file base that itself
    inherits `RealHomeTestCase` is invisible to it.

If the construction is one hop away in the same file through a plain name or
a plain attribute, this guard sees it. If it is behind a second module, a
runtime lookup, or anything else that is not a literal name, it does not, and
no amount of extending this particular walk will change that -- catching it
would need either running the code or a much heavier whole-repository
call-graph analysis, not a deeper version of this same AST walk.

One more assumption, unrelated to the above and worth naming for what it is:
this guard discovers files with a non-recursive `tests/test_*.py` glob,
matching how this suite's own discovery finds its tests today (`unittest
discover -s tests`, which also does not descend into subdirectories of
`tests/` for this repository's layout). If that discovery ever starts
recursing into subdirectories, this glob would need to as well -- it is not
exploitable today only because nothing this suite runs recurses either.

Why `RealHomeTestCase` is not mandatory everywhere: `test_filesystem.py`
tests the filesystem port's own behaviour, including per-test
`@unittest.skipIf(os.geteuid() == 0, ...)` decorators on only *some* of its
70 tests -- inheriting `RealHomeTestCase` would move that skip into `setUp`
and silently skip the whole class under a root-running test process, losing
real coverage of every test that does not depend on permission bits. Every
one of its 70 tests was run against both `/tmp` and `/dev/shm` before this
guard was written and passed identically either way (tmpfs on Linux supports
the same permission bits, symlinks, and atomic rename this port relies on),
so it now spells the same rule out explicitly with `dir=_scratch_root()`
instead.

Any other legitimate exception -- a test that genuinely needs a disk-backed
home tmpfs cannot stand in for, or a module-level false positive from the
coarser fallback pass -- belongs in `NOT_ROUTED_THROUGH_SCRATCH_ROOT` below,
with a comment explaining why, keyed by the *full relative path* of the file
plus the class name (or the pseudo-name `<module>` for a module-scoped hit),
never by filename alone: comparing exclusions by filename instead of full
path is the exact mistake this repository made twice already, and checked
against the real file at that exact path so a stale entry cannot silently
stop guarding anything.
"""
from __future__ import annotations

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = ROOT / "tests"

#: {"tests/test_some_file.py::ClassName": "reason"} -- see the module
#: docstring for why this is keyed by full path, never by class name alone.
#: A module-scoped hit (see the module docstring's "two scopes") is keyed by
#: the pseudo-name `<module>` instead of a class name.
NOT_ROUTED_THROUGH_SCRATCH_ROOT: dict[str, str] = {
    # No class or module needs a full disk-backed home today. Add an entry
    # here, with a reason, if one ever genuinely does -- e.g. a test that
    # specifically exercises `write_atomic`'s device wait against a real
    # block device rather than tmpfs, or a module-level false positive from
    # the coarser module-scoped fallback pass.
}


def _base_name(base: ast.expr) -> str | None:
    if isinstance(base, ast.Name):
        return base.id
    if isinstance(base, ast.Attribute):
        return base.attr
    return None


def _inherits_real_home(node: ast.ClassDef, classes_by_name: dict[str, ast.ClassDef], seen: set[str]) -> bool:
    for base in node.bases:
        name = _base_name(base)
        if name is None:
            continue
        if name.endswith("RealHomeTestCase"):
            return True
        if name in seen:
            continue
        parent = classes_by_name.get(name)
        if parent is not None:
            seen.add(name)
            if _inherits_real_home(parent, classes_by_name, seen):
                return True
    return False


def _import_aliases(tree: ast.Module) -> dict[str, str]:
    """Map a name imported under an alias back to what it was imported as --
    `from tempfile import TemporaryDirectory as TD` maps `"TD"` to
    `"TemporaryDirectory"` -- so a call site using the alias is judged by
    what it actually calls, not by the local name it happens to be spelled
    with."""
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.asname:
                    aliases[alias.asname] = alias.name
    return aliases


def _called_name(call: ast.Call, aliases: dict[str, str]) -> str | None:
    func = call.func
    if isinstance(func, ast.Name):
        return aliases.get(func.id, func.id)
    if isinstance(func, ast.Attribute):
        # `module.Name(...)` -- the attribute is already the real name
        # regardless of what the module itself was imported as
        # (`import tempfile as tf; tf.TemporaryDirectory()`), so no alias
        # resolution is needed on this branch.
        return func.attr
    return None


def _constructs_posix_filesystem(node: ast.AST, aliases: dict[str, str]) -> bool:
    return any(
        isinstance(call, ast.Call) and _called_name(call, aliases) == "PosixFileSystem" for call in ast.walk(node)
    )


def _unrouted_temporary_directory_calls(node: ast.AST, aliases: dict[str, str]) -> list[ast.Call]:
    """Every `tempfile.TemporaryDirectory(...)` call in `node` whose `dir=`
    keyword is either absent or not a call to something named
    `_scratch_root` -- the one shape that actually reaches tmpfs."""
    offenders = []
    for call in ast.walk(node):
        if not isinstance(call, ast.Call) or _called_name(call, aliases) != "TemporaryDirectory":
            continue
        dir_value = next((keyword.value for keyword in call.keywords if keyword.arg == "dir"), None)
        if (
            dir_value is not None
            and isinstance(dir_value, ast.Call)
            and _called_name(dir_value, aliases) == "_scratch_root"
        ):
            continue
        offenders.append(call)
    return offenders


def _offending_classes(tree: ast.Module, aliases: dict[str, str]) -> list[str]:
    classes_by_name = {node.name: node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}

    offenders = []
    for node in classes_by_name.values():
        if _inherits_real_home(node, classes_by_name, {node.name}):
            continue
        if not _constructs_posix_filesystem(node, aliases):
            continue
        if not _unrouted_temporary_directory_calls(node, aliases):
            continue
        offenders.append(node.name)
    return sorted(offenders)


def _any_class_routes_through_real_home(tree: ast.Module) -> bool:
    classes_by_name = {node.name: node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}
    return any(_inherits_real_home(node, classes_by_name, {node.name}) for node in classes_by_name.values())


def _offenders_in_file(path: Path) -> list[str]:
    """Class-scoped offenders first; only when that pass finds nothing and
    no class in the file already routes through `RealHomeTestCase` does the
    coarser module-scoped fallback run -- see the module docstring's "two
    scopes" section for why, and for what each pass can and cannot see."""
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    aliases = _import_aliases(tree)

    class_offenders = _offending_classes(tree, aliases)
    if class_offenders:
        return class_offenders
    if _any_class_routes_through_real_home(tree):
        return []
    if _constructs_posix_filesystem(tree, aliases) and _unrouted_temporary_directory_calls(tree, aliases):
        return ["<module>"]
    return []


def _stale_exceptions(exceptions: dict[str, str]) -> list[str]:
    """Every qualifier in `exceptions` whose file half does not exist at that
    exact path -- pulled out of the test method so the logic can be
    exercised against a dict that is not the (empty) production one."""
    stale = []
    for qualifier in exceptions:
        relative_path = qualifier.split("::", 1)[0]
        if not (ROOT / relative_path).is_file():
            stale.append(qualifier)
    return stale


class RealHomesUseTheSharedScratchRootTest(unittest.TestCase):
    def test_scratch_root_exceptions_name_files_that_exist(self):
        """A stale exception that outlived the file it named would silently
        stop guarding anything -- checked by full relative path, never by
        filename alone."""
        stale = _stale_exceptions(NOT_ROUTED_THROUGH_SCRATCH_ROOT)
        self.assertEqual(
            stale,
            [],
            f"NOT_ROUTED_THROUGH_SCRATCH_ROOT names {stale!r}, whose file half does not exist "
            "at that exact path -- update or remove the exception.",
        )

    def test_stale_exception_check_actually_fails_on_a_missing_path(self):
        """`test_scratch_root_exceptions_name_files_that_exist` proves nothing
        while `NOT_ROUTED_THROUGH_SCRATCH_ROOT` is empty -- an empty dict
        vacuously passes regardless of whether the checking logic works. This
        exercises that logic directly, against a dict built here rather than
        the production one, so the assertion is not resting on production
        data staying empty."""
        fake_exceptions = {
            "tests/test_this_file_does_not_exist_anywhere.py::SomeClass": "made up for this test",
        }
        stale = _stale_exceptions(fake_exceptions)
        self.assertEqual(stale, list(fake_exceptions))

    def test_no_real_posix_home_bypasses_the_shared_scratch_root(self):
        offenders = []
        for path in sorted(TESTS_DIR.glob("test_*.py")):
            if path.name == "test_real_home_shared_root.py":
                continue  # this guard's own probes construct the shapes it looks for
            relative = path.relative_to(ROOT).as_posix()
            for class_name in _offenders_in_file(path):
                qualifier = f"{relative}::{class_name}"
                if qualifier in NOT_ROUTED_THROUGH_SCRATCH_ROOT:
                    continue
                offenders.append(qualifier)

        self.assertEqual(
            offenders,
            [],
            "these construct a real PosixFileSystem over a tempfile.TemporaryDirectory() "
            "that is not routed through the shared scratch root: "
            f"{offenders} -- either inherit RealHomeTestCase (tests/real_home.py), pass "
            "dir=_scratch_root() explicitly, or add a reasoned exception to "
            "NOT_ROUTED_THROUGH_SCRATCH_ROOT.",
        )


if __name__ == "__main__":
    unittest.main()
