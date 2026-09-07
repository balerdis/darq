"""Unit tests for the pure rebrand transform in ``rebrand.transform``.

No filesystem is touched except through ``apply_to_tree``'s own tests, which build a throwaway
tree under a temporary directory. Everything else exercises the pure string functions directly.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from rebrand.transform import (
    RebrandMap,
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


class RebrandTransformTests(unittest.TestCase):
    """Tests that share the module-scoped ``rebrand_map`` fixture (parsed once for the class)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.rebrand_map: RebrandMap = parse_map(json.loads(REBRAND_JSON.read_text(encoding="utf-8")))

    def test_rebrand_json_parses_and_has_the_four_declared_renames(self) -> None:
        rebrand_map = self.rebrand_map
        self.assertEqual(
            set(rebrand_map.rename_map),
            {
                "agents/pegasus-orchestrator.md",
                "agents/mcp/cbm@pegasus-orchestrator.md",
                "agents/king-pegasus.md",
                "agents/mcp/cbm@king-pegasus.md",
            },
        )
        self.assertEqual(rebrand_map.rename_map["agents/king-pegasus.md"], "agents/arquitecto-darq.md")
        self.assertEqual(
            rebrand_map.rename_map["agents/mcp/cbm@king-pegasus.md"],
            "agents/mcp/cbm@arquitecto-darq.md",
        )
        self.assertEqual(
            rebrand_map.rename_map["agents/pegasus-orchestrator.md"],
            "agents/darq-orchestrator.md",
        )
        self.assertEqual(
            rebrand_map.rename_map["agents/mcp/cbm@pegasus-orchestrator.md"],
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

    def test_rename_relative_path_is_a_lookup_not_a_heuristic(self) -> None:
        rebrand_map = self.rebrand_map
        self.assertEqual(
            rename_relative_path("agents/king-pegasus.md", rebrand_map), "agents/arquitecto-darq.md"
        )
        self.assertEqual(rename_relative_path("agents/sdd-apply.md", rebrand_map), "agents/sdd-apply.md")

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
