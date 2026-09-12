"""Unit tests for ``tools.build_darq.overlay_content``.

Two properties are under test:

1. A collision -- an overlay file whose relative path already exists in the rebranded engine
   tree -- is a hard build failure, never a silent overwrite.
2. Every overlay file is mirrored against the engine's brand, the same way
   ``rebrand.transform.rename_relative_path`` mirrors a *derived* path: to REJECT the file if the
   brand survives, never to rewrite it. DARQ's own content must never carry the engine's brand in
   its name or its body.

``build/work/extracted-raw/content`` (a previous real build's raw, unrebranded engine content
copy -- see ``tests/test_rebrand.py``'s own ``ENGINE_CONTENT_ROOT``) is reused here only to
confirm real repo content never collides with it; the mutation tests below build small synthetic
package/overlay trees under ``tempfile.mkdtemp`` so they never depend on that copy existing.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))

import build_darq  # noqa: E402
from rebrand.transform import parse_map  # noqa: E402

REBRAND_MAP = parse_map(__import__("json").loads((ROOT / "rebrand.json").read_text(encoding="utf-8")))
REAL_CONTENT_OVERLAY = ROOT / "content"
ENGINE_CONTENT_ROOT = ROOT / "build" / "work" / "extracted-raw" / "content"


class OverlayContentFixture(unittest.TestCase):
    def setUp(self) -> None:
        self.work_root = Path(tempfile.mkdtemp(prefix="darq-overlay-test-"))
        self.addCleanup(shutil.rmtree, self.work_root, ignore_errors=True)
        self.package = self.work_root / "package"
        self.overlay_root = self.work_root / "overlay"
        (self.package / "content").mkdir(parents=True)
        self.overlay_root.mkdir(parents=True)

    def _write_engine_file(self, relative: str, text: str = "engine content\n") -> Path:
        path = self.package / "content" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def _write_overlay_file(self, relative: str, text: str = "overlay content\n") -> Path:
        path = self.overlay_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path


class OverlayCollisionTests(OverlayContentFixture):
    def test_overlay_file_colliding_with_engine_path_is_a_hard_failure(self) -> None:
        self._write_engine_file("skills/already-here.md", "engine's own content\n")
        self._write_overlay_file("skills/already-here.md", "darq content trying to land here\n")

        with self.assertRaises(build_darq.OverlayCollisionError) as ctx:
            build_darq.overlay_content(self.package, self.overlay_root, REBRAND_MAP)
        self.assertIn("skills/already-here.md", str(ctx.exception))

        # The engine's own file must survive untouched -- the collision must be caught before
        # any overwrite, not after.
        self.assertEqual(
            (self.package / "content" / "skills" / "already-here.md").read_text(encoding="utf-8"),
            "engine's own content\n",
        )

    def test_non_colliding_overlay_file_is_added_and_reported(self) -> None:
        self._write_engine_file("skills/existing.md")
        self._write_overlay_file("skills/new.md", "brand new\n")

        build_darq.overlay_content(self.package, self.overlay_root, REBRAND_MAP)

        self.assertEqual(
            (self.package / "content" / "skills" / "new.md").read_text(encoding="utf-8"),
            "brand new\n",
        )

    def test_engine_file_blocking_a_needed_overlay_directory_is_a_hard_failure(self) -> None:
        # The escape an adversarial review reproduced: the engine tree has a *file* at a path the
        # overlay needs as an intermediate *directory*. The leaf destination
        # (content/skillsdir/inner.md) does not exist yet, so a leaf-only exists() check never
        # fires, and the collision used to surface later as a bare `pathlib.FileExistsError` out
        # of `Path.mkdir` -- no path, no explanation. It must instead raise
        # `OverlayCollisionError`, naming the blocking path, same as any other collision.
        self._write_engine_file("skillsdir", "engine file, not a dir\n")
        self._write_overlay_file("skillsdir/inner.md", "overlay content\n")

        with self.assertRaises(build_darq.OverlayCollisionError) as ctx:
            build_darq.overlay_content(self.package, self.overlay_root, REBRAND_MAP)
        self.assertIn("skillsdir", str(ctx.exception))

        # The engine's own file must survive untouched -- the collision must be caught before
        # any attempt to turn it into a directory.
        engine_path = self.package / "content" / "skillsdir"
        self.assertTrue(engine_path.is_file())
        self.assertEqual(engine_path.read_text(encoding="utf-8"), "engine file, not a dir\n")

    def test_engine_directory_blocking_an_overlay_file_is_a_hard_failure(self) -> None:
        # The reverse direction: the engine tree has a *directory* at a path the overlay wants to
        # place a *file*. This is reachable (an overlay file's own path can coincide with an
        # engine directory), and the existing leaf check already covers it: `Path.exists()` is
        # true for a directory just as it is for a file, so the same `OverlayCollisionError` path
        # fires without any extra code.
        self._write_engine_file("skillsdir/inner.md", "engine content\n")
        self._write_overlay_file("skillsdir", "overlay file, not a dir\n")

        with self.assertRaises(build_darq.OverlayCollisionError) as ctx:
            build_darq.overlay_content(self.package, self.overlay_root, REBRAND_MAP)
        self.assertIn("skillsdir", str(ctx.exception))

        # The engine's own directory must survive untouched.
        engine_dir = self.package / "content" / "skillsdir"
        self.assertTrue(engine_dir.is_dir())
        self.assertEqual(
            (engine_dir / "inner.md").read_text(encoding="utf-8"), "engine content\n"
        )


class OverlayBrandLeakTests(OverlayContentFixture):
    def test_overlay_file_named_with_the_brand_is_rejected(self) -> None:
        self._write_overlay_file("skills/pegasus-thing.md", "clean body\n")

        with self.assertRaises(build_darq.OverlayBrandLeakError) as ctx:
            build_darq.overlay_content(self.package, self.overlay_root, REBRAND_MAP)
        self.assertIn("pegasus-thing.md", str(ctx.exception))
        self.assertFalse((self.package / "content" / "skills" / "pegasus-thing.md").exists())

    def test_overlay_file_body_carrying_the_brand_is_rejected(self) -> None:
        self._write_overlay_file("skills/clean-name.md", "This mentions Pegasus in the body.\n")

        with self.assertRaises(build_darq.OverlayBrandLeakError) as ctx:
            build_darq.overlay_content(self.package, self.overlay_root, REBRAND_MAP)
        self.assertIn("clean-name.md", str(ctx.exception))
        self.assertFalse((self.package / "content" / "skills" / "clean-name.md").exists())

    def test_overlay_file_body_carrying_a_protected_token_passes(self) -> None:
        # `.pegasus-data` is a protected wire identifier, not a brand leak: it must never be
        # rejected just because it contains the substring "pegasus".
        self._write_overlay_file(
            "skills/wire-id.md", "State lives under `.pegasus-data` on disk.\n"
        )

        build_darq.overlay_content(self.package, self.overlay_root, REBRAND_MAP)

        self.assertEqual(
            (self.package / "content" / "skills" / "wire-id.md").read_text(encoding="utf-8"),
            "State lives under `.pegasus-data` on disk.\n",
        )


class RealContentOverlayTests(unittest.TestCase):
    """The real ``content/`` tree this repo ships must always pass the overlay unchanged."""

    def setUp(self) -> None:
        self.work_root = Path(tempfile.mkdtemp(prefix="darq-overlay-real-test-"))
        self.addCleanup(shutil.rmtree, self.work_root, ignore_errors=True)
        self.package = self.work_root / "package"
        (self.package / "content").mkdir(parents=True)

    def test_the_five_real_overlay_files_pass_without_change(self) -> None:
        overlay_files = sorted(
            p for p in REAL_CONTENT_OVERLAY.rglob("*") if p.is_file() and p.name != ".gitkeep"
        )
        self.assertEqual(len(overlay_files), 5, "expected exactly the 5 known content/ files")

        build_darq.overlay_content(self.package, REAL_CONTENT_OVERLAY, REBRAND_MAP)

        for source in overlay_files:
            relative = source.relative_to(REAL_CONTENT_OVERLAY)
            destination = self.package / "content" / relative
            self.assertEqual(destination.read_bytes(), source.read_bytes())

    @unittest.skipUnless(
        ENGINE_CONTENT_ROOT.is_dir(), "no persisted raw engine content copy from a real build yet"
    )
    def test_the_five_real_overlay_files_do_not_collide_with_a_real_engine_tree(self) -> None:
        shutil.copytree(ENGINE_CONTENT_ROOT, self.package / "content", dirs_exist_ok=True)
        build_darq.overlay_content(self.package, REAL_CONTENT_OVERLAY, REBRAND_MAP)


if __name__ == "__main__":
    unittest.main()
