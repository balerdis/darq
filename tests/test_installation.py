"""Installing the real content into a real directory, and taking it back out.

Everything else in this suite proves a decision. This proves the decisions
compose: the content core, an adapter, the planner, the POSIX filesystem and
the journal, run end to end against a temporary home with nothing faked.

It is the first test that would notice if the catalog and the journal disagreed
about a fingerprint, if an append were installed twice, or if uninstalling left
a home dirtier than it found it.
"""
from __future__ import annotations

import unittest
from dataclasses import replace
from pathlib import Path

from pegasus import cli
from pegasus.adapters import available
from pegasus.core import catalog as catalog_module
from pegasus.core import content as content_module
from pegasus.core import journal as journal_module
from pegasus.core import ownership
from pegasus.core import planner
from pegasus.core.types import Environment, FileArtifact
from pegasus.infra.journal_store_file import FileJournalStore
from real_home import RealHomeTestCase as _RealHomeTestCase

AT = "2026-08-14T00:00:00+00:00"
VERSION = "4.0.0"


class InstallAndRetireTest(_RealHomeTestCase):
    def setUp(self):
        super().setUp()
        self.fs = self.filesystem
        self.registry = available()
        # Pinned to OpenCode, not "whichever adapter registers first": this
        # suite's own end-to-end assertions (subagent_depth, the apply_patch
        # scoping plugin, ...) exercise OpenCode-specific artifacts that
        # Claude Code's adapter never renders. "ids()[0]" now resolves
        # alphabetically to "claudecode" instead, which cannot support them.
        self.cli = "opencode"
        self.adapter = self.registry.get(self.cli)
        self.environment = Environment(home=self.home, data_dir=self.fs.data_dir(self.home))
        self.layout = self.adapter.layout(self.environment)
        self.artifacts = catalog_module.render(
            content_module.load(), self.adapter, self.environment, cli.default_identity()
        )

    def install(self) -> planner.Applied:
        plan = planner.plan(self.fs, cli=self.cli, artifacts=self.artifacts)
        return planner.apply(self.fs, plan, at=AT)

    def files_under(self, root: Path) -> list[Path]:
        return sorted(path for path in root.rglob("*") if path.is_file())

    # --- Installing ---

    def test_an_empty_home_receives_every_artifact(self):
        plan = planner.plan(self.fs, cli=self.cli, artifacts=self.artifacts)
        self.assertEqual(len(plan.collisions), 0)
        self.assertEqual(len(plan.creations), len(self.artifacts))

    def test_installing_puts_the_files_on_disk(self):
        applied = self.install()
        self.assertEqual(len(applied.records), len(self.artifacts))
        self.assertTrue(self.files_under(self.layout.config_dir))

    def test_every_record_is_a_journal_the_core_accepts(self):
        applied = self.install()
        install = journal_module.Install(
            cli=self.cli,
            installed_at=AT,
            config_dir=self.layout.config_dir,
            release={"version": VERSION},
            entries=applied.records,
        )
        stored = journal_module.with_install(journal_module.empty(VERSION), install)
        store = FileJournalStore(self.fs, home=self.home, pegasus_version=VERSION)
        store.save(stored)
        self.assertEqual(store.load(), stored)

    def test_the_fingerprints_recorded_are_taken_the_way_the_catalog_takes_them(self):
        """One fingerprint function, or no uninstall ever recognises its own work.

        Equality entry by entry is the wrong invariant to hold on to. The catalog
        is release identity and is built in a canonical frame, while the journal
        records what this machine actually received, and a body that asks the
        installer for a path is deliberately different once filled. What must
        never diverge is *how* the fingerprint is taken and *what* it covers:
        every id the catalog publishes is an id the journal records, and every
        recorded digest is the digest of the artifact this run rendered.
        """
        applied = self.install()
        catalog = catalog_module.build(content_module.load(), self.adapter, cli.default_identity())
        rendered = catalog_module.render(
            content_module.load(), self.adapter, self.environment, cli.default_identity()
        )

        recorded = {record.id: record.after_digest for record in applied.records}
        self.assertEqual(set(recorded), {entry.id for entry in catalog.entries})
        self.assertEqual(recorded, {item.id: ownership.digest(item) for item in rendered})

    def test_the_apply_patch_scope_plugin_lands_on_disk_and_is_claimed(self):
        """A bundled plugin is only shipped if the journal admits to it.

        Named here rather than left to the counts above because the failure it
        guards against is silent in both directions: an asset the journal never
        records is an asset `uninstall` leaves behind forever, and an asset that
        never reaches disk is a plugin the runtime simply does not load. The
        artifact is found by its suffix, not by a spelled-out filename -- the
        installed name is derived from this distribution's identity.
        """
        matches = [
            item
            for item in self.artifacts
            if isinstance(item, FileArtifact) and item.path.name.endswith("-apply-patch-scope.ts")
        ]
        self.assertEqual(len(matches), 1, "the apply_patch scoping plugin is not among the artifacts")
        plugin = matches[0]

        applied = self.install()
        self.assertTrue(plugin.path.is_file(), plugin.path)
        self.assertIn(plugin.id, {record.id for record in applied.records})

    def test_subagent_depth_is_ten_and_claimed(self):
        """OpenCode refuses `task` from a sub-agent unless `subagent_depth` is
        raised above its default of 1. Pegasus owns this top-level key at 10,
        a circuit breaker rather than a policy value, and the key must be
        claimed in the journal the same as any other owned key or `uninstall`
        would leave it behind forever.
        """
        import json

        applied = self.install()
        settings = self.layout.settings_file
        self.assertIsNotNone(settings)
        document = json.loads(settings.read_text(encoding="utf-8"))
        self.assertEqual(document["subagent_depth"], 10)
        self.assertIn("own:subagent-depth", {record.id for record in applied.records})

    def test_installing_twice_changes_nothing_the_second_time(self):
        """Every artifact is a collision the second time, including the appends."""
        self.install()
        before = {path: path.read_bytes() for path in self.files_under(self.layout.config_dir)}
        second = planner.plan(self.fs, cli=self.cli, artifacts=self.artifacts)
        self.assertEqual(len(second.creations), 0)
        applied = planner.apply(self.fs, second, at=AT)
        self.assertEqual(applied.records, ())
        self.assertEqual({path: path.read_bytes() for path in self.files_under(self.layout.config_dir)}, before)

    # --- Reinstalling ---

    def installed_record(self, applied: planner.Applied) -> journal_module.Install:
        return journal_module.Install(
            cli=self.cli, installed_at=AT, config_dir=self.layout.config_dir, release={}, entries=applied.records
        )

    def replan(self, applied: planner.Applied, artifacts=None) -> planner.Plan:
        return planner.plan(
            self.fs,
            cli=self.cli,
            artifacts=artifacts if artifacts is not None else self.artifacts,
            installed=self.installed_record(applied),
        )

    def test_a_second_run_over_our_own_work_has_nothing_to_collide_with(self):
        """The payload is not a collision with itself once the journal is consulted."""
        second = self.replan(self.install())
        self.assertEqual(len(second.collisions), 0)
        self.assertEqual(len(second.unchanged), len(self.artifacts))

    def test_a_second_run_with_identical_content_writes_nothing(self):
        applied = self.install()
        before = {path: path.read_bytes() for path in self.files_under(self.layout.config_dir)}
        second = planner.apply(self.fs, self.replan(applied), at=AT)
        self.assertEqual(second.records, ())
        self.assertEqual({path: path.read_bytes() for path in self.files_under(self.layout.config_dir)}, before)

    def test_a_shipped_file_that_changed_is_rewritten(self):
        """The whole point of the unit: a new version of the payload lands."""
        applied = self.install()
        target = next(item for item in self.artifacts if isinstance(item, FileArtifact))
        newer = [
            replace(item, content=b"a newer shipped version\n") if item is target else item
            for item in self.artifacts
        ]
        plan = self.replan(applied, newer)
        self.assertEqual([step.artifact.id for step in plan.updates], [target.id])
        planner.apply(self.fs, plan, at=AT)
        self.assertEqual(target.path.read_bytes(), b"a newer shipped version\n")

    def test_a_file_the_user_edited_is_overwritten_by_a_reinstall(self):
        applied = self.install()
        target = next(item for item in self.artifacts if isinstance(item, FileArtifact))
        target.path.write_bytes(b"the user's own words\n")
        newer = [
            replace(item, content=b"a newer shipped version\n") if item is target else item
            for item in self.artifacts
        ]
        plan = self.replan(applied, newer)
        self.assertEqual([step.artifact.id for step in plan.updates], [target.id])
        planner.apply(self.fs, plan, at=AT)
        self.assertEqual(target.path.read_bytes(), b"a newer shipped version\n")

    # --- Retiring ---

    def test_retiring_takes_back_everything_it_installed(self):
        applied = self.install()
        install = journal_module.Install(
            cli=self.cli, installed_at=AT, config_dir=self.layout.config_dir, release={}, entries=applied.records
        )
        retired = planner.retire(self.fs, install)
        self.assertEqual(len(retired.removed), len(applied.records))

    def test_a_home_that_was_installed_and_retired_holds_nothing_of_ours(self):
        applied = self.install()
        install = journal_module.Install(
            cli=self.cli, installed_at=AT, config_dir=self.layout.config_dir, release={}, entries=applied.records
        )
        planner.retire(self.fs, install)
        leftovers = [path for path in self.files_under(self.layout.config_dir) if path.stat().st_size > 0]
        settings = self.layout.settings_file
        if settings is not None and settings.exists():
            leftovers = [path for path in leftovers if path != settings]
            self.assertEqual(settings.read_text(encoding="utf-8").strip(), "{}")
        self.assertEqual(leftovers, [])

    def test_a_file_the_user_edited_is_removed_by_the_uninstall_too(self):
        """The snapshot is what keeps the edit recoverable, not this check."""
        applied = self.install()
        edited = next(record for record in applied.records if record.kind == "file")
        edited.target.write_bytes(b"the user rewrote this")
        install = journal_module.Install(
            cli=self.cli, installed_at=AT, config_dir=self.layout.config_dir, release={}, entries=applied.records
        )
        retired = planner.retire(self.fs, install)
        self.assertIn(edited.id, retired.removed)
        self.assertFalse(edited.target.exists())

    def test_a_key_the_user_added_survives_the_uninstall(self):
        settings = self.layout.settings_file
        if settings is None:
            self.skipTest("this adapter has no settings file")
        applied = self.install()
        document = settings.read_text(encoding="utf-8")
        settings.write_text(document.replace("{", '{\n  "theirs": "keep me",', 1), encoding="utf-8")
        install = journal_module.Install(
            cli=self.cli, installed_at=AT, config_dir=self.layout.config_dir, release={}, entries=applied.records
        )
        planner.retire(self.fs, install)
        self.assertIn("keep me", settings.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
