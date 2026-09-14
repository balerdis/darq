"""`pegasus repair`: journal hazards `doctor` can only name.

Step 1: a `granted_directories` entry a hand edit put in the journal that
`content.validate_granted_directory` refuses gets quarantined at load time
(`journal._granted_directories_from_dict`) rather than blocking the whole
journal. `repair` is the command that removes a quarantined entry, the same
way `directory revoke` removes a legitimate one -- except quarantine cannot
be reached through `directory revoke`, because it is never in
`granted_directories` to begin with.

Real disk, a throwaway home, the same discipline `test_cli_directory.py`
already follows.
"""
from __future__ import annotations

import io
import json

from pegasus import cli
from pegasus.adapters import available
from pegasus.core import journal as journal_module
from pegasus.core.types import Environment
from real_home import RealHomeTestCase as _RealHomeTestCase

AT = "2026-08-14T00:00:00+00:00"
CLI = available().ids()[0]
NO_BINARY = {"PATH": ""}


class RealHomeTestCase(_RealHomeTestCase):
    def runtime(self) -> cli.Runtime:
        return cli.Runtime(
            filesystem=self.filesystem, home=self.home, now=AT, out=io.StringIO(), variables=NO_BINARY
        )

    def layout(self):
        return available().get(CLI).layout(Environment(home=self.home))

    def present(self) -> None:
        self.layout().config_dir.mkdir(parents=True, exist_ok=True)

    def store(self):
        return cli.journal_store(self.runtime())

    def run_cli(self, *argv) -> tuple[int, dict]:
        context = self.runtime()
        code = cli.main([*argv, "--json"], runtime=context)
        return code, json.loads(context.out.getvalue())

    def run_prose(self, *argv) -> tuple[int, str]:
        context = self.runtime()
        code = cli.main(list(argv), runtime=context)
        return code, context.out.getvalue()

    def installed(self):
        return journal_module.install_for(self.store().load(), CLI)

    def install(self) -> None:
        self.present()
        code, _ = self.run_cli("install", "--cli", CLI)
        self.assertEqual(code, 0)

    def settings(self) -> dict:
        return json.loads(self.layout().settings_file.read_bytes())

    def own_directory(self) -> str:
        target = self.home / "worktrees" / "extra"
        target.mkdir(parents=True, exist_ok=True)
        return str(target)

    def plant_quarantined_entry(self, entry="/") -> None:
        """Hand-edit the journal the way a person editing it by hand, or a
        corrupted write, would -- an entry `content.validate_granted_directory`
        refuses, spliced directly into `granted_directories`."""
        path = self.store().path
        payload = json.loads(path.read_bytes())
        install_payload = next(item for item in payload["installs"] if item["cli"] == CLI)
        install_payload.setdefault("granted_directories", []).append(entry)
        path.write_bytes(json.dumps(payload).encode("utf-8"))


class QuarantineLoadTest(RealHomeTestCase):
    """1a/1b: loading no longer dies, and the bad entry never reaches what an
    agent is granted."""

    def test_a_quarantined_entry_does_not_block_loading_the_journal(self):
        self.install()
        self.plant_quarantined_entry("/")
        journal = self.store().load()  # must not raise
        install = journal_module.install_for(journal, CLI)
        self.assertEqual(install.granted_directories, ())
        self.assertEqual(install.quarantined_directories, ("/",))

    def test_a_quarantined_entry_never_reaches_the_rendered_permission(self):
        """The containment guard: run the real path that decides what an
        agent is granted (a plain reinstall, which reapplies
        `installed.granted_directories`) and assert the rendered permission
        carries only the legitimate grant -- comparing the actual set, not a
        count or a substring."""
        self.install()
        legitimate = self.own_directory()
        code, _ = self.run_cli("directory", "grant", "--cli", CLI, legitimate)
        self.assertEqual(code, 0)
        dangerous = str(self.layout().config_dir)
        self.plant_quarantined_entry(dangerous)
        # A plain reinstall reapplies `installed.granted_directories` --
        # exactly the path a person would hit next, with no idea a
        # quarantined entry even exists.
        code, report = self.run_cli("install", "--cli", CLI)
        self.assertEqual(code, 0, report)
        settings = self.settings()
        agents = settings.get("agent", {})
        self.assertTrue(agents, "expected at least one rendered agent")
        granted_keys = {
            key
            for entry in agents.values()
            for key in entry.get("permission", {}).get("external_directory", {})
        }
        self.assertIn(f"{legitimate}/*", granted_keys)
        # The fact, not a proxy: the quarantined entry never earns its own
        # `f"{path}/*": allow"` rule -- the one shape `render.py` writes for
        # every entry in `Agent.granted_directories`. (The skills subtree
        # beneath the config directory is a separate, legitimate baseline
        # exception and is deliberately not asserted against here.)
        self.assertNotIn(f"{dangerous}/*", granted_keys)

    def test_directories_granted_excludes_the_quarantined_entry(self):
        self.install()
        self.plant_quarantined_entry("/")
        install = self.installed()
        self.assertEqual(install.granted_directories, ())

    def test_a_plain_reinstall_carries_the_quarantine_forward_instead_of_silently_dropping_it(self):
        """`_merged` rebuilds the `Install` on every run; nothing in the
        install/update path re-derives quarantine, so a reinstall that
        forgot to carry it forward would silently delete it -- the same
        silent-loss shape "tolerate as empty" was rejected for
        `granted_directories` itself."""
        self.install()
        self.plant_quarantined_entry("/")
        self.assertEqual(self.installed().quarantined_directories, ("/",))
        code, _ = self.run_cli("install", "--cli", CLI)
        self.assertEqual(code, 0)
        self.assertEqual(self.installed().quarantined_directories, ("/",))


class DoctorReportsQuarantineTest(RealHomeTestCase):
    def test_doctor_names_the_quarantined_entry(self):
        self.install()
        self.plant_quarantined_entry("/")
        _, report = self.run_cli("doctor")
        entry = next(item for item in report["clis"] if item["cli"] == CLI)
        self.assertIn(repr("/"), entry["directories_quarantined"])

    def test_doctor_says_nothing_when_there_is_nothing_quarantined(self):
        self.install()
        _, report = self.run_cli("doctor")
        entry = next(item for item in report["clis"] if item["cli"] == CLI)
        self.assertNotIn("directories_quarantined", entry)

    def test_doctor_prose_names_the_repair_command(self):
        self.install()
        self.plant_quarantined_entry("/")
        _, printed = self.run_prose("doctor")
        self.assertIn("repair", printed)
        self.assertIn("grant nothing", printed)

    def test_doctor_prose_says_nothing_about_quarantine_when_there_is_none(self):
        self.install()
        _, printed = self.run_prose("doctor")
        self.assertNotIn("quarantin", printed)


class RepairCommandTest(RealHomeTestCase):
    def test_repair_removes_the_quarantined_entry(self):
        self.install()
        self.plant_quarantined_entry("/")
        code, report = self.run_cli("repair", "--cli", CLI)
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "repaired")
        self.assertIn(repr("/"), report["removed_quarantined_directories"])
        self.assertEqual(self.installed().quarantined_directories, ())

    def test_repair_names_each_entry_it_removed(self):
        self.install()
        self.plant_quarantined_entry("/")
        self.plant_quarantined_entry("relative/one")
        _, report = self.run_cli("repair", "--cli", CLI)
        self.assertIn(repr("/"), report["removed_quarantined_directories"])
        self.assertIn(repr("relative/one"), report["removed_quarantined_directories"])

    def test_repair_removes_nothing_else(self):
        """It performs no other write: the legitimate grant, and every other
        journal fact, survive untouched."""
        self.install()
        legitimate = self.own_directory()
        self.run_cli("directory", "grant", "--cli", CLI, legitimate)
        self.plant_quarantined_entry("/")
        self.run_cli("repair", "--cli", CLI)
        self.assertEqual(self.installed().granted_directories, (legitimate,))

    def test_repair_with_nothing_to_repair_writes_nothing_and_exits_ok(self):
        self.install()
        before = self.store().path.stat().st_mtime_ns
        before_bytes = self.store().path.read_bytes()
        code, report = self.run_cli("repair", "--cli", CLI)
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "nothing-to-repair")
        self.assertEqual(self.store().path.stat().st_mtime_ns, before)
        self.assertEqual(self.store().path.read_bytes(), before_bytes)

    def test_dry_run_reports_without_writing(self):
        self.install()
        self.plant_quarantined_entry("/")
        before_bytes = self.store().path.read_bytes()
        before_mtime = self.store().path.stat().st_mtime_ns
        code, report = self.run_cli("repair", "--cli", CLI, "--dry-run")
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "planned")
        self.assertIn(repr("/"), report["removed_quarantined_directories"])
        self.assertEqual(self.store().path.read_bytes(), before_bytes)
        self.assertEqual(self.store().path.stat().st_mtime_ns, before_mtime)
        self.assertEqual(self.installed().quarantined_directories, ("/",))

    def test_repair_takes_a_snapshot_restore_can_undo(self):
        self.install()
        self.plant_quarantined_entry("/")
        code, report = self.run_cli("repair", "--cli", CLI)
        self.assertEqual(code, 0)
        code, restore_report = self.run_cli("restore")
        self.assertEqual(code, 0)
        self.assertEqual(self.installed().quarantined_directories, ("/",))

    def test_repair_without_an_installation_is_refused(self):
        self.present()
        code, report = self.run_cli("repair", "--cli", CLI)
        self.assertNotEqual(code, 0)
        self.assertEqual(report["status"], "failed")

    def test_repair_with_an_unknown_cli_is_refused(self):
        code, report = self.run_cli("repair", "--cli", "nonesuch")
        self.assertNotEqual(code, 0)
        self.assertEqual(report["status"], "failed")

    def test_repair_against_malformed_json_fails_with_the_same_message_every_command_gives(self):
        self.install()
        self.store().path.write_bytes(b"{ not json")
        code, report = self.run_cli("repair", "--cli", CLI)
        self.assertNotEqual(code, 0)
        self.assertEqual(report["status"], "failed")
        self.assertIn("not readable JSON", report["error"])

    def test_repair_against_a_granted_directories_shape_quarantine_does_not_cover_fails_and_names_restore(self):
        """`granted_directories` not being a list at all is a different
        corruption quarantine does not cover -- `repair` fails with the same
        "malformed" message every other command gives, which names
        `restore` as the way back."""
        self.install()
        path = self.store().path
        payload = json.loads(path.read_bytes())
        install_payload = next(item for item in payload["installs"] if item["cli"] == CLI)
        install_payload["granted_directories"] = "not-a-list"
        path.write_bytes(json.dumps(payload).encode("utf-8"))
        code, report = self.run_cli("repair", "--cli", CLI)
        self.assertNotEqual(code, 0)
        self.assertEqual(report["status"], "failed")
        self.assertIn("malformed", report["error"])
        self.assertIn("restore", report["error"])

    def test_repair_prose_names_what_it_removed(self):
        self.install()
        self.plant_quarantined_entry("/")
        _, printed = self.run_prose("repair", "--cli", CLI)
        self.assertIn("Removed", printed)
        self.assertIn(repr("/"), printed)

    def test_repair_prose_with_nothing_to_repair(self):
        self.install()
        _, printed = self.run_prose("repair", "--cli", CLI)
        self.assertIn("nothing to repair", printed)


class OrphanedDirectoryRepairTest(RealHomeTestCase):
    """2a: `doctor` already names an empty directory `created_dirs` never
    recorded, under `unprunable_empty_directories` -- P5. `repair` is what
    actually removes exactly that set, and nothing else, reusing
    `planner.empty_directories_never_pruned` for discovery so the two can
    never name different directories."""

    def plant_untracked_empty_directory(self, name: str = "leftover-from-an-old-install") -> Path:
        directory = self.layout().config_dir / name
        directory.mkdir()
        return directory

    def test_repair_removes_an_orphaned_empty_directory(self):
        self.install()
        directory = self.plant_untracked_empty_directory()
        code, report = self.run_cli("repair", "--cli", CLI)
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "repaired")
        self.assertIn(str(directory), report["removed_orphaned_directories"])
        self.assertFalse(directory.exists())

    def test_repair_leaves_a_directory_still_reachable_from_created_dirs_alone(self):
        self.install()
        tracked = next(iter(self.installed().created_dirs))
        self.run_cli("repair", "--cli", CLI)
        self.assertTrue(tracked.exists())

    def test_repair_leaves_a_nonempty_directory_alone(self):
        self.install()
        directory = self.plant_untracked_empty_directory()
        (directory / "keepme.txt").write_bytes(b"mine")
        code, report = self.run_cli("repair", "--cli", CLI)
        self.assertEqual(code, 0)
        self.assertEqual(report["removed_orphaned_directories"], [])
        self.assertTrue(directory.exists())
        self.assertTrue((directory / "keepme.txt").exists())

    def test_a_file_planted_between_discovery_and_removal_saves_the_directory(self):
        """The whole point of re-checking emptiness at removal time rather
        than trusting the discovery pass: `remove_empty_dir` is `os.rmdir`,
        which fails atomically against a directory that is not actually
        empty. Discover first (the directory is genuinely empty then), plant
        a file into it -- simulating a write landing in the same window a
        stale discovery result would have missed -- and only then run the
        removal `repair` performs; the directory must survive."""
        self.install()
        directory = self.plant_untracked_empty_directory()
        from pegasus.core import planner as planner_module

        scan = planner_module.empty_directories_never_pruned(
            self.filesystem, self.installed().config_dir, self.installed().created_dirs
        )
        self.assertIn(str(directory), scan.found)
        (directory / "raced-in.txt").write_bytes(b"landed after discovery")
        removed = planner_module.remove_orphaned_empty_directories(
            self.filesystem, self.installed().config_dir, scan.found
        )
        self.assertNotIn(str(directory), removed)
        self.assertTrue(directory.exists())
        self.assertTrue((directory / "raced-in.txt").exists())

    def test_repair_ascends_into_a_parent_that_becomes_empty_in_the_same_run(self):
        """A parent that was not itself empty at discovery time -- it still
        held the child directory -- but becomes empty once that child is
        removed must be taken in the same run, not left standing."""
        self.install()
        parent = self.layout().config_dir / "leftover-parent"
        child = parent / "leftover-child"
        child.mkdir(parents=True)
        code, report = self.run_cli("repair", "--cli", CLI)
        self.assertEqual(code, 0)
        self.assertFalse(parent.exists())
        self.assertIn(str(child), report["removed_orphaned_directories"])
        self.assertIn(str(parent), report["removed_orphaned_directories"])

    def test_repair_never_ascends_past_config_dir(self):
        self.install()
        self.plant_untracked_empty_directory()
        self.run_cli("repair", "--cli", CLI)
        self.assertTrue(self.layout().config_dir.exists())

    def test_dry_run_names_the_orphaned_directory_without_removing_it(self):
        self.install()
        directory = self.plant_untracked_empty_directory()
        code, report = self.run_cli("repair", "--cli", CLI, "--dry-run")
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "planned")
        self.assertIn(str(directory), report["removed_orphaned_directories"])
        self.assertTrue(directory.exists())

    def test_repair_prose_names_the_orphaned_directory_distinctly_from_quarantine(self):
        self.install()
        directory = self.plant_untracked_empty_directory()
        self.plant_quarantined_entry("/")
        _, printed = self.run_prose("repair", "--cli", CLI)
        self.assertIn("orphaned empty director", printed)
        self.assertIn(str(directory), printed)
        self.assertIn("quarantined granted-directory", printed)


class SymlinkedConfigDirTest(RealHomeTestCase):
    """2b: a symlinked config_dir, or a symlinked subdirectory reached mid
    walk, used to produce a silently empty report -- `visit` returns as soon
    as it sees a symlink, so nothing under it was ever inspected, and
    nothing said so. Real symlinks, real disk, per the house rule against
    faking filesystem semantics."""

    def test_doctor_names_a_symlinked_config_dir_it_could_not_walk(self):
        self.present()
        real_config_dir = self.layout().config_dir
        elsewhere = self.home / "dotfiles-config"
        real_config_dir.rename(elsewhere) if real_config_dir.exists() else elsewhere.mkdir(parents=True)
        import os as _os

        _os.symlink(elsewhere, real_config_dir)
        code, _ = self.run_cli("install", "--cli", CLI)
        self.assertEqual(code, 0)
        _, report = self.run_cli("doctor")
        entry = next(item for item in report["clis"] if item["cli"] == CLI)
        self.assertIn(str(real_config_dir), entry.get("directories_not_walked", []))
        self.assertNotIn("unprunable_empty_directories", entry)

    def test_doctor_names_a_symlinked_subdirectory_reached_mid_walk(self):
        self.install()
        real_subdir = self.layout().config_dir / "linked-subtree"
        elsewhere = self.home / "elsewhere-subtree"
        elsewhere.mkdir(parents=True)
        (elsewhere / "empty-inside").mkdir()
        import os as _os

        _os.symlink(elsewhere, real_subdir)
        _, report = self.run_cli("doctor")
        entry = next(item for item in report["clis"] if item["cli"] == CLI)
        self.assertIn(str(real_subdir), entry.get("directories_not_walked", []))
        # What is behind the symlink was never inspected -- it must not be
        # named as an orphaned empty directory it never actually walked.
        self.assertNotIn(
            str(elsewhere / "empty-inside"), entry.get("unprunable_empty_directories", [])
        )

    def test_repair_does_not_silently_claim_success_over_an_unwalked_subtree(self):
        self.install()
        real_subdir = self.layout().config_dir / "linked-subtree"
        elsewhere = self.home / "elsewhere-subtree-2"
        elsewhere.mkdir(parents=True)
        import os as _os

        _os.symlink(elsewhere, real_subdir)
        code, report = self.run_cli("repair", "--cli", CLI)
        self.assertEqual(code, 0)
        self.assertIn(str(real_subdir), report.get("directories_not_walked", []))
        _, printed = self.run_prose("repair", "--cli", CLI)
        self.assertIn(str(real_subdir), printed)
