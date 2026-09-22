"""The snapshot generation manifest: pure structure, no filesystem."""
from __future__ import annotations

import unittest
from pathlib import Path

from darq.core import snapshot as snapshot_module
from darq.core.snapshot import Entry, Manifest, SnapshotError

AT = "2026-08-14T00:00:00+00:00"


def entry(**overrides) -> Entry:
    fields = dict(path=Path("/home/probe/.config/some-cli/settings.json"), existed=True, mode="0644", blob="0001.blob")
    fields.update(overrides)
    return Entry(**fields)


class EntryConstructionTest(unittest.TestCase):
    def test_an_existing_entry_needs_a_mode_and_a_blob(self):
        entry(existed=True, mode="0644", blob="0001.blob")

    def test_an_absent_entry_needs_neither(self):
        entry(existed=False, mode=None, blob=None)

    def test_an_absent_entry_cannot_carry_a_blob(self):
        with self.assertRaises(SnapshotError):
            entry(existed=False, mode=None, blob="0001.blob")

    def test_an_absent_entry_cannot_carry_a_mode(self):
        with self.assertRaises(SnapshotError):
            entry(existed=False, mode="0644", blob=None)

    def test_an_existing_entry_needs_a_blob(self):
        with self.assertRaises(SnapshotError):
            entry(existed=True, mode="0644", blob=None)

    def test_an_existing_entry_needs_a_mode(self):
        with self.assertRaises(SnapshotError):
            entry(existed=True, mode=None, blob="0001.blob")


class ManifestRoundTripTest(unittest.TestCase):
    def setUp(self):
        self.manifest = Manifest(
            taken_at=AT,
            entries=(
                entry(),
                entry(path=Path("/home/probe/.config/some-cli/other.json"), existed=False, mode=None, blob=None),
            ),
        )

    def test_survives_serialization(self):
        payload = snapshot_module.to_dict(self.manifest)
        self.assertEqual(snapshot_module.from_dict(payload), self.manifest)

    def test_fields_that_do_not_apply_are_omitted(self):
        payload = snapshot_module.to_dict(self.manifest)
        absent_entry = payload["entries"][1]
        self.assertNotIn("mode", absent_entry)
        self.assertNotIn("blob", absent_entry)

    def test_an_empty_manifest_round_trips(self):
        empty = Manifest(taken_at=AT)
        self.assertEqual(snapshot_module.from_dict(snapshot_module.to_dict(empty)), empty)


class ManifestLabelTest(unittest.TestCase):
    """`Manifest.label` names the intention that produced a generation --
    `"install"`, `"mcp grant"`, and so on. It must be optional in both
    directions: absent by default, and a manifest written before this field
    existed must go on reading fine rather than become unreadable.
    """

    def test_a_manifest_with_no_label_defaults_to_none(self):
        self.assertIsNone(Manifest(taken_at=AT).label)

    def test_a_label_survives_serialization(self):
        manifest = Manifest(taken_at=AT, label="mcp grant")
        payload = snapshot_module.to_dict(manifest)
        self.assertEqual(payload["label"], "mcp grant")
        self.assertEqual(snapshot_module.from_dict(payload), manifest)

    def test_an_absent_label_is_omitted_from_the_serialized_payload(self):
        """Mirrors `Entry.is_directory`'s own omission: a manifest this
        version writes for an unlabelled generation must read back
        identically to one a version that predates this field would have
        produced -- there is no reason for the two to differ on a fact
        neither of them is describing.
        """
        payload = snapshot_module.to_dict(Manifest(taken_at=AT))
        self.assertNotIn("label", payload)

    def test_a_manifest_written_before_this_field_existed_still_reads(self):
        """The constraint most likely to be broken silently: a real manifest
        already on disk, written by a version of this product that never
        heard of `label`, carries only `taken_at` and `entries` -- exactly
        the bytes a real file on a real machine looks like today. Reading it
        back must succeed, with `label` simply absent, not raise.
        """
        payload = {"taken_at": AT, "entries": []}
        manifest = snapshot_module.from_dict(payload)
        self.assertIsNone(manifest.label)
        self.assertEqual(manifest.taken_at, AT)

    def test_a_non_string_label_is_rejected(self):
        with self.assertRaises(SnapshotError):
            snapshot_module.from_dict({"taken_at": AT, "entries": [], "label": 42})


class FromDictValidationTest(unittest.TestCase):
    def test_rejects_a_non_object_payload(self):
        with self.assertRaises(SnapshotError):
            snapshot_module.from_dict([])

    def test_rejects_a_missing_taken_at(self):
        with self.assertRaises(SnapshotError):
            snapshot_module.from_dict({"entries": []})

    def test_rejects_a_blank_taken_at(self):
        with self.assertRaises(SnapshotError):
            snapshot_module.from_dict({"taken_at": "", "entries": []})

    def test_rejects_entries_that_are_not_a_list(self):
        with self.assertRaises(SnapshotError):
            snapshot_module.from_dict({"taken_at": AT, "entries": "nope"})

    def test_rejects_an_entry_that_is_not_an_object(self):
        with self.assertRaises(SnapshotError):
            snapshot_module.from_dict({"taken_at": AT, "entries": ["nope"]})

    def test_rejects_an_entry_missing_a_path(self):
        with self.assertRaises(SnapshotError):
            snapshot_module.from_dict({"taken_at": AT, "entries": [{"existed": False}]})

    def test_rejects_an_entry_missing_existed(self):
        with self.assertRaises(SnapshotError):
            snapshot_module.from_dict({"taken_at": AT, "entries": [{"path": "/a"}]})

    def test_rejects_an_entry_with_a_non_boolean_existed(self):
        with self.assertRaises(SnapshotError):
            snapshot_module.from_dict({"taken_at": AT, "entries": [{"path": "/a", "existed": "yes"}]})

    def test_rejects_an_entry_with_a_non_string_mode(self):
        with self.assertRaises(SnapshotError):
            snapshot_module.from_dict(
                {"taken_at": AT, "entries": [{"path": "/a", "existed": True, "mode": 644, "blob": "0001.blob"}]}
            )

    def test_rejects_an_entry_with_a_non_string_blob(self):
        with self.assertRaises(SnapshotError):
            snapshot_module.from_dict(
                {"taken_at": AT, "entries": [{"path": "/a", "existed": True, "mode": "0644", "blob": 1}]}
            )

    def test_rejects_an_existing_entry_that_still_lacks_a_blob(self):
        """The construction guard fires even when the payload reached from_dict."""
        with self.assertRaises(SnapshotError):
            snapshot_module.from_dict({"taken_at": AT, "entries": [{"path": "/a", "existed": True, "mode": "0644"}]})


if __name__ == "__main__":
    unittest.main()
