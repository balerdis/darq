"""Unit tests for the pure rebrand transform in ``rebrand.transform``.

No filesystem is touched except through ``apply_to_tree``'s own tests, which build a throwaway
tree under a temporary directory. Everything else exercises the pure string functions directly.
"""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from rebrand.transform import (
    RebrandMap,
    RebrandPathError,
    apply_to_tree,
    is_excluded,
    mask,
    parse_map,
    rename_relative_path,
    should_substitute_body,
    substitute_body,
    unmask,
)

ROOT = Path(__file__).resolve().parents[1]
REBRAND_JSON = ROOT / "rebrand.json"
ENGINE_CONTENT_ROOT = ROOT / "build" / "work" / "extracted" / "pegasus" / "content"


class RebrandTransformTests(unittest.TestCase):
    """Tests that share the module-scoped ``rebrand_map`` fixture (parsed once for the class)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.rebrand_map: RebrandMap = parse_map(json.loads(REBRAND_JSON.read_text(encoding="utf-8")))

    def test_rebrand_json_declares_only_the_semantic_renames_that_derivation_cannot_produce(self) -> None:
        """``renames`` now holds only the two deliberate re-namings (king-pegasus's persona name
        does not textually derive from the brand substitution map); the purely mechanical
        pegasus-orchestrator renames were removed once verified byte-identical to what
        ``rename_relative_path`` derives on its own -- see
        ``test_derivation_reproduces_the_removed_pegasus_orchestrator_renames_byte_for_byte``."""
        rebrand_map = self.rebrand_map
        self.assertEqual(
            set(rebrand_map.rename_map),
            {
                "agents/king-pegasus.md",
                "agents/mcp/cbm@king-pegasus.md",
            },
        )
        self.assertEqual(rebrand_map.rename_map["agents/king-pegasus.md"], "agents/arquitecto-darq.md")
        self.assertEqual(
            rebrand_map.rename_map["agents/mcp/cbm@king-pegasus.md"],
            "agents/mcp/cbm@arquitecto-darq.md",
        )

    def test_derivation_reproduces_the_removed_pegasus_orchestrator_renames_byte_for_byte(self) -> None:
        """The two entries removed from ``renames`` must be exactly reproducible by mechanical
        derivation -- this is the byte-for-byte proof the brief requires before removing them."""
        rebrand_map = self.rebrand_map
        self.assertEqual(
            substitute_body("agents/pegasus-orchestrator.md", rebrand_map),
            "agents/darq-orchestrator.md",
        )
        self.assertEqual(
            substitute_body("agents/mcp/cbm@pegasus-orchestrator.md", rebrand_map),
            "agents/mcp/cbm@darq-orchestrator.md",
        )

    def test_king_pegasus_never_degrades_into_king_darq(self) -> None:
        """The whole reason substitution order is correctness-critical: 'king-pegasus' must become
        'arquitecto-darq' as a single unit, not 'king-' + ('pegasus' -> 'darq') = 'king-darq'."""
        result = substitute_body("Ask king-pegasus for help.", self.rebrand_map)
        self.assertIn("arquitecto-darq", result)
        self.assertNotIn("king-darq", result)
        self.assertTrue("pegasus" not in result.lower() or "arquitecto-darq" in result)

    def test_pegasus_orchestrator_replaced_before_bare_pegasus(self) -> None:
        result = substitute_body("Delegate to pegasus-orchestrator now.", self.rebrand_map)
        self.assertEqual(result, "Delegate to darq-orchestrator now.")

    def test_case_variants_all_covered(self) -> None:
        rebrand_map = self.rebrand_map
        self.assertEqual(substitute_body("Pegasus Harness", rebrand_map), "DARQ")
        self.assertEqual(substitute_body("pegasus-harness", rebrand_map), "darq")
        self.assertEqual(substitute_body("Pegasus", rebrand_map), "DARQ")
        self.assertEqual(substitute_body("PEGASUS", rebrand_map), "DARQ")
        self.assertEqual(substitute_body("pegasus", rebrand_map), "darq")

    def test_ordering_matches_declared_longest_match_first(self) -> None:
        patterns = [old for old, _ in self.rebrand_map.substitutions]
        self.assertLess(patterns.index("king-pegasus"), patterns.index("pegasus"))
        self.assertLess(patterns.index("pegasus-orchestrator"), patterns.index("pegasus"))
        self.assertLess(patterns.index("Pegasus Harness"), patterns.index("Pegasus"))
        self.assertLess(patterns.index("pegasus-harness"), patterns.index("pegasus"))

    def test_protected_tokens_survive_the_transform_unchanged(self) -> None:
        tokens = [
            "PEGASUS_SKILL_ROOTS",
            "PEGASUS_SKILL_REGISTRY_BIN",
            "PEGASUS_NO_UPDATE_CHECK",
            "PEGASUS_INSTALL_BASE_URL",
            "pegasus/capability-manifest/v1",
            "pegasus/model-assignment/v1",
            "pegasus/artifact-catalog/v4",
            "pegasus/cli-report/v1",
            "pegasus-harness/journal/v4",
            "pegasus_version",
            "pegasus_installed",
            "pegasus-doctor",
            "/pegasus/catalog-build",
            ".pegasus-data",
        ]
        for token in tokens:
            with self.subTest(token=token):
                body = f"Set {token} before running the CLI. Also mind Pegasus Harness conventions here."
                result = substitute_body(body, self.rebrand_map)
                self.assertIn(token, result, f"{token!r} must survive verbatim, got: {result!r}")
                # And the surrounding prose still got rebranded normally.
                self.assertIn("DARQ", result)
                self.assertNotIn("Pegasus Harness", result)

    def test_pegasus_skill_roots_specifically_survives_body_containing_it(self) -> None:
        """The exact scenario called out in the brief: a body mentioning the skill-registry env var
        must come out with that env var byte-identical, even though it contains 'PEGASUS' as a
        substring the case-insensitive-looking substitution rules would otherwise happily rewrite."""
        body = "Export PEGASUS_SKILL_ROOTS to point at your local skills checkout."
        result = substitute_body(body, self.rebrand_map)
        self.assertEqual(result, body)

    def test_dot_pegasus_dash_prefix_masked_before_the_longer_dot_pegasus_data_token(self) -> None:
        """Masking must walk protected tokens longest-first: masking '.pegasus-' before the longer
        '.pegasus-data' would clip 'data' off, leaving it unmasked and then rewritten to 'darqdata'."""
        payload = {
            "renames": [],
            "substitutions": [["pegasus", "darq"]],
            "protected_tokens": [".pegasus-", ".pegasus-data"],
            "excluded_paths": [],
        }
        rebrand_map = parse_map(payload)
        self.assertEqual(rebrand_map.protected_tokens[0], ".pegasus-data")  # sorted longest-first
        result = substitute_body("keep .pegasus-data intact", rebrand_map)
        self.assertIn(".pegasus-data", result)
        self.assertNotIn("darqdata", result)

    def test_mask_unmask_round_trip_is_identity(self) -> None:
        tokens = (".pegasus-data", ".pegasus-", "PEGASUS_SKILL_ROOTS")
        text = "a .pegasus-data b .pegasus-c PEGASUS_SKILL_ROOTS d"
        self.assertEqual(unmask(mask(text, tokens), tokens), text)

    def test_json_files_are_never_substituted(self) -> None:
        rebrand_map = self.rebrand_map
        self.assertFalse(should_substitute_body("mcp/playwright-package-lock.json", rebrand_map))
        self.assertTrue(should_substitute_body("agents/pegasus-orchestrator.md", rebrand_map))
        self.assertTrue(should_substitute_body("session-start.txt", rebrand_map))

    def test_excluded_paths_are_never_substituted(self) -> None:
        payload = json.loads(REBRAND_JSON.read_text(encoding="utf-8"))
        payload["substitution_extensions"] = [".md", ".txt", ".py"]
        excluded_map = RebrandMap(
            renames=tuple((e["from"], e["to"]) for e in payload["renames"]),
            substitutions=tuple(tuple(p) for p in payload["substitutions"]),
            protected_tokens=tuple(sorted(payload["protected_tokens"], key=len, reverse=True)),
            excluded_paths=("__init__.py",),
        )
        self.assertTrue(is_excluded("__init__.py", excluded_map))
        self.assertFalse(should_substitute_body("__init__.py", excluded_map))

    def test_rename_relative_path_prefers_the_explicit_semantic_rename_over_derivation(self) -> None:
        rebrand_map = self.rebrand_map
        self.assertEqual(
            rename_relative_path("agents/king-pegasus.md", rebrand_map), "agents/arquitecto-darq.md"
        )
        self.assertEqual(rename_relative_path("agents/sdd-apply.md", rebrand_map), "agents/sdd-apply.md")

    def test_rename_relative_path_derives_a_mechanical_rename_with_no_rebrand_json_entry(self) -> None:
        """The whole point of the fix: a brand-new content filename the engine ships (like
        ``pegasus-general.md`` in v5.25.0) is renamed correctly with zero ``rebrand.json`` changes,
        because the path goes through the same substitution map applied to file bodies."""
        rebrand_map = self.rebrand_map
        self.assertNotIn("agents/pegasus-whatever.md", rebrand_map.rename_map)
        self.assertEqual(
            rename_relative_path("agents/pegasus-whatever.md", rebrand_map),
            "agents/darq-whatever.md",
        )
        self.assertNotIn("agents/pegasus-general.md", rebrand_map.rename_map)
        self.assertEqual(
            rename_relative_path("agents/pegasus-general.md", rebrand_map),
            "agents/darq-general.md",
        )

    def test_rename_relative_path_leaves_a_protected_token_in_a_path_untouched(self) -> None:
        """Path-level substitution must go through the same masking as body substitution, or a
        path containing a protected wire token would get clobbered by the bare 'pegasus' rule."""
        payload = json.loads(REBRAND_JSON.read_text(encoding="utf-8"))
        payload["renames"] = []
        rebrand_map = parse_map(payload)
        result = rename_relative_path("mcp/pegasus/cli-report/v1.md", rebrand_map)
        self.assertIn("pegasus/cli-report/v1", result)
        self.assertEqual(result, "mcp/pegasus/cli-report/v1.md")

    def test_accepted_residue_paths_are_out_of_scope_for_rename_relative_path(self) -> None:
        """``apply_to_tree`` (the only caller of ``rename_relative_path``) is invoked with
        ``package / "content"`` as its content root (see tools/build_darq.py). The
        ``accepted_residue`` entries that name a path (e.g. the notifier/skill-registry plugin
        assets) live under ``adapters/opencode/assets/`` in the extracted engine package, entirely
        outside that content root, so ``rename_relative_path`` never sees them -- no exemption
        code is needed. This is verified against the real extracted engine tree, not assumed."""
        if not ENGINE_CONTENT_ROOT.is_dir():
            self.skipTest(f"{ENGINE_CONTENT_ROOT} not present; run tools/build_darq.py once first")
        payload = json.loads(REBRAND_JSON.read_text(encoding="utf-8"))
        residue_paths = [
            entry["token"] for entry in payload["accepted_residue"] if "/" in entry["token"]
        ]
        self.assertTrue(residue_paths, "expected at least one path-shaped accepted_residue entry")
        content_files = {
            p.relative_to(ENGINE_CONTENT_ROOT).as_posix()
            for p in ENGINE_CONTENT_ROOT.rglob("*")
            if p.is_file()
        }
        for residue_path in residue_paths:
            with self.subTest(residue_path=residue_path):
                self.assertNotIn(
                    residue_path,
                    content_files,
                    f"{residue_path!r} unexpectedly lives under the content root apply_to_tree "
                    "governs; it would need an explicit exemption after all",
                )
                matches = [f for f in content_files if residue_path in f]
                self.assertEqual(
                    matches,
                    [],
                    f"{residue_path!r} unexpectedly appears under the content root: {matches!r}",
                )

    def test_mirror_check_fires_when_an_explicit_rename_still_leaves_the_brand_in_the_output(self) -> None:
        """The transform-time mirror must catch a path neither the explicit list nor derivation
        actually resolves -- here, a (deliberately broken) explicit entry whose own target still
        carries the brand. The error names the offending path."""
        payload = json.loads(REBRAND_JSON.read_text(encoding="utf-8"))
        payload["renames"] = [{"from": "agents/broken.md", "to": "agents/still-pegasus-branded.md"}]
        rebrand_map = parse_map(payload)
        with self.assertRaises(RebrandPathError) as ctx:
            rename_relative_path("agents/broken.md", rebrand_map)
        self.assertIn("agents/still-pegasus-branded.md", str(ctx.exception))

    def test_mirror_check_does_not_fire_on_the_real_pinned_engine_content_tree(self) -> None:
        """The clean build stays clean: run the mirror-guarded rename over the actual pinned
        engine content tree (already extracted into build/work by a prior real build) and confirm
        it does not raise."""
        if not ENGINE_CONTENT_ROOT.is_dir():
            self.skipTest(f"{ENGINE_CONTENT_ROOT} not present; run tools/build_darq.py once first")
        rebrand_map = self.rebrand_map
        for path in sorted(p for p in ENGINE_CONTENT_ROOT.rglob("*") if p.is_file()):
            relative_posix = path.relative_to(ENGINE_CONTENT_ROOT).as_posix()
            if is_excluded(relative_posix, rebrand_map):
                continue
            rename_relative_path(relative_posix, rebrand_map)  # must not raise

    def test_no_output_filename_stem_carries_a_banned_brand_fragment_after_a_real_transform(self) -> None:
        """Complement of the whole change: transform a fresh copy of the real pinned engine content
        tree and confirm no resulting filename stem contains any brand fragment declared in
        rebrand.json's own substitutions -- the banned-fragment list is never hand-written here."""
        if not ENGINE_CONTENT_ROOT.is_dir():
            self.skipTest(f"{ENGINE_CONTENT_ROOT} not present; run tools/build_darq.py once first")
        rebrand_map = self.rebrand_map
        work_root = Path(tempfile.mkdtemp(prefix="darq-rebrand-test-"))
        self.addCleanup(shutil.rmtree, work_root, ignore_errors=True)
        content_copy = work_root / "content"
        shutil.copytree(ENGINE_CONTENT_ROOT, content_copy)

        apply_to_tree(content_copy, rebrand_map)

        banned_fragments = tuple(old for old, _ in rebrand_map.substitutions)
        for path in sorted(p for p in content_copy.rglob("*") if p.is_file()):
            for fragment in banned_fragments:
                self.assertNotIn(
                    fragment,
                    path.stem,
                    f"{path.relative_to(content_copy)} still carries brand fragment {fragment!r}",
                )

    def test_apply_to_tree_renames_and_substitutes_on_disk(self) -> None:
        rebrand_map = self.rebrand_map
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        tmp_path = Path(tmp_dir.name)

        agents_dir = tmp_path / "agents"
        mcp_dir = agents_dir / "mcp"
        mcp_dir.mkdir(parents=True)
        (agents_dir / "king-pegasus.md").write_text(
            "---\nname: king-pegasus\n---\n# King Pegasus\nDelegate to pegasus-orchestrator.\n",
            encoding="utf-8",
        )
        (agents_dir / "pegasus-orchestrator.md").write_text(
            "---\nname: pegasus-orchestrator\n---\n# Pegasus Harness Orchestrator\n", encoding="utf-8"
        )
        (mcp_dir / "cbm@king-pegasus.md").write_text("cbm section for king-pegasus\n", encoding="utf-8")
        (mcp_dir / "cbm@pegasus-orchestrator.md").write_text(
            "cbm section for pegasus-orchestrator\n", encoding="utf-8"
        )
        (tmp_path / "session-start.txt").write_text("pegasus-orchestrator", encoding="utf-8")
        (tmp_path / "__init__.py").write_text("# pegasus content package marker\n", encoding="utf-8")
        lockfile = tmp_path / "playwright-package-lock.json"
        lockfile.write_text('{"packages": {"": {"name": "pegasus-playwright-mcp"}}}\n', encoding="utf-8")

        apply_to_tree(tmp_path, rebrand_map)

        self.assertFalse((agents_dir / "king-pegasus.md").exists())
        self.assertFalse((agents_dir / "pegasus-orchestrator.md").exists())
        self.assertFalse((mcp_dir / "cbm@king-pegasus.md").exists())
        self.assertFalse((mcp_dir / "cbm@pegasus-orchestrator.md").exists())

        renamed = (agents_dir / "arquitecto-darq.md").read_text(encoding="utf-8")
        self.assertIn("name: arquitecto-darq", renamed)
        self.assertIn("Arquitecto DARQ", renamed)
        self.assertIn("darq-orchestrator", renamed)

        orchestrator = (agents_dir / "darq-orchestrator.md").read_text(encoding="utf-8")
        self.assertIn("name: darq-orchestrator", orchestrator)
        self.assertIn("DARQ Orchestrator", orchestrator)

        self.assertEqual(
            (mcp_dir / "cbm@arquitecto-darq.md").read_text(encoding="utf-8"),
            "cbm section for arquitecto-darq\n",
        )
        self.assertEqual(
            (mcp_dir / "cbm@darq-orchestrator.md").read_text(encoding="utf-8"),
            "cbm section for darq-orchestrator\n",
        )

        self.assertEqual((tmp_path / "session-start.txt").read_text(encoding="utf-8"), "darq-orchestrator")

        # __init__.py is never touched, even though it mentions 'pegasus'.
        self.assertEqual(
            (tmp_path / "__init__.py").read_text(encoding="utf-8"),
            "# pegasus content package marker\n",
        )

        # The JSON lockfile residue is left completely alone.
        self.assertEqual(
            lockfile.read_text(encoding="utf-8"),
            '{"packages": {"": {"name": "pegasus-playwright-mcp"}}}\n',
        )


if __name__ == "__main__":
    unittest.main()
