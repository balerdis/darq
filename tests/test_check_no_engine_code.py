"""Proves the no-fork guard actually catches a violation -- not just that it stays quiet on a
clean tree, which a guard that never checks anything would do too.
"""
from __future__ import annotations

import unittest

from tools.check_no_engine_code import ROOT, check


class CheckNoEngineCodeTests(unittest.TestCase):
    def test_the_real_darq_tree_is_clean(self) -> None:
        self.assertEqual(check(), [])

    def test_guard_catches_an_engine_layer_directory_violation(self) -> None:
        violation_dir = ROOT / "core"
        self.assertFalse(violation_dir.exists(), "test setup assumption: no core/ dir already present")

        # Registered first so it runs last (addCleanup is LIFO): the final "quiet again" check
        # only makes sense once every cleanup below it has actually removed the violation.
        self.addCleanup(lambda: self.assertEqual(check(), []))

        violation_dir.mkdir()
        self.addCleanup(violation_dir.rmdir)
        violation_file = violation_dir / "content.py"
        violation_file.write_text("# copied engine module\n", encoding="utf-8")
        self.addCleanup(violation_file.unlink)

        violations = check()
        self.assertTrue(violations, "the guard must fail once a core/ directory exists")
        self.assertTrue(any("core" in message for message in violations))

    def test_guard_catches_a_copied_engine_content_artifact(self) -> None:
        violation_file = ROOT / "content" / "king-pegasus.md"
        self.assertFalse(violation_file.exists(), "test setup assumption: no copy already present")

        self.addCleanup(lambda: self.assertEqual(check(), []))

        violation_file.write_text("---\nname: king-pegasus\n---\ncopied content\n", encoding="utf-8")
        self.addCleanup(violation_file.unlink)

        violations = check()
        self.assertTrue(violations)
        self.assertTrue(any("king-pegasus.md" in message for message in violations))

    def test_guard_catches_a_python_file_that_imports_the_engine(self) -> None:
        """The check that closes the other two's blind spot: a single engine module copied to the
        repo root, named nothing in particular, sitting in no engine-shaped directory.
        """
        violation_file = ROOT / "helper.py"
        self.assertFalse(violation_file.exists(), "test setup assumption: no helper.py already present")

        self.addCleanup(lambda: self.assertEqual(check(), []))

        violation_file.write_text("from pegasus.core import content\n", encoding="utf-8")
        self.addCleanup(violation_file.unlink)

        violations = check()
        self.assertTrue(violations, "the guard must fail on a Python file importing the engine")
        self.assertTrue(any("helper.py" in message for message in violations))

    def test_the_guard_takes_its_scope_from_gitignore_not_from_its_own_list(self) -> None:
        """The build's scratch extraction holds the whole engine tree, and must stay exempt -- but
        the exemption has to come from `.gitignore`, the one place that already declares it.

        A hardcoded list of directory names to skip would be a second source of truth, free to
        disagree with `.gitignore`: the day a directory stopped being ignored, the guard would keep
        skipping it and report PASS with engine code committed inside. Asserting the same violation
        is exempt under an ignored path and caught outside it is what pins the scope to git.
        """
        ignored = ROOT / "build" / "guard-scope-probe"
        tracked = ROOT / "guard-scope-probe.py"
        body = "from pegasus.core import content\n"

        self.addCleanup(lambda: self.assertEqual(check(), []))

        ignored.mkdir(parents=True, exist_ok=True)
        self.addCleanup(ignored.rmdir)
        leak_file = ignored / "leak.py"
        leak_file.write_text(body, encoding="utf-8")
        self.addCleanup(lambda: leak_file.unlink(missing_ok=True))

        self.assertEqual(check(), [], "a violation under an ignored path must not trip the guard")

        tracked.write_text(body, encoding="utf-8")
        self.addCleanup(lambda: tracked.unlink(missing_ok=True))
        self.assertTrue(check(), "the identical file outside an ignored path must trip it")


if __name__ == "__main__":
    unittest.main()
