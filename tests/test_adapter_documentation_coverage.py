"""Guard: a registered adapter cannot go undocumented, or misdocumented.

DARQ shipped a second CLI (Claude Code) alongside the original one
(OpenCode) without updating any of the four user-facing documents -- 89
mentions of OpenCode and zero of Claude Code, `README.md` stating outright
that OpenCode was the only client. Nothing caught that because nothing
compared the documented surface against `darq.adapters.available()`. This
file is that comparison, derived from the registry -- never a hardcoded list
of adapter ids -- so a third adapter that registers tomorrow fails this test
the day it registers, instead of going silently undocumented like the second
one did.

Two things are checked, both explicitly requested by the brief that fixed
this gap:

1. Every adapter's display name appears in each document that is supposed to
   introduce a reader to every CLI DARQ supports.
2. A capability comparison table in `README.md` -- parsed, not eyeballed --
   agrees, cell for cell, with each adapter's own `CapabilityManifest` and
   `tier()`.

Which documents must name every adapter, and which do not, is a deliberate
choice, not an oversight:

* `README.md`, `INSTALL.md` and `INSTALL_BY_AGENT.md` are entry points: a
  reader (human or agent) lands on one of these first and must be told which
  CLIs exist before choosing one. All three must name every adapter.
* `MANUAL.md` is deliberately excluded. Its own title scopes it --
  "Manual de uso: DARQ + OpenCode" -- and its prose is pinned,
  fact for fact, against a live OpenCode installation by five other guard
  suites (`test_manual_command_surface.py` and its four siblings). Turning it
  into a manual for every CLI would mean either fighting those pins or
  duplicating the entire day-to-day manual per adapter; the document whose
  job is to route a reader to the right CLI already does that job elsewhere
  (`README.md`, `INSTALL_BY_AGENT.md`), and `MANUAL.md` says so of itself. A
  guard that forced every document to name every CLI would be noise; a guard
  that named none would be silence -- this file draws the line at the
  entry points, where a reader could otherwise be steered wrong.

Every failure found is collected and reported together, in one assertion, so
a single run of this file names everything wrong instead of one thing at a
time.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from darq.adapters import available
from darq.core.types import Capability

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Entry-point documents a reader (human or agent) meets before choosing a
#: CLI. Every adapter's display name must appear in each of these. See the
#: module docstring for why `MANUAL.md` is not in this tuple.
DOCS_NAMING_EVERY_ADAPTER = ("README.md", "INSTALL.md", "INSTALL_BY_AGENT.md")

#: Where the machine-checkable capability table lives.
CAPABILITY_TABLE_DOC = "README.md"

#: Column order the capability table is expected to use: the manifest's own
#: boolean fields, in the order `Capability` declares them, plus the two
#: adapter-level facts that are not part of the manifest itself.
TABLE_COLUMNS = tuple(capability.value for capability in Capability) + ("tier",)


def _read(doc_name: str) -> str:
    path = REPO_ROOT / doc_name
    return path.read_text(encoding="utf-8")


def _find_capability_table(text: str) -> dict[str, str]:
    """Return {column_name: raw_header_cell} for the header row of the table
    whose first column is "CLI" and whose remaining columns are exactly
    `TABLE_COLUMNS`, in order. Raises AssertionError (caught by the caller as
    a missing-table failure) if no such table exists.
    """
    lines = text.splitlines()
    for index, line in enumerate(lines):
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not cells or cells[0] != "CLI":
            continue
        if tuple(cells[1:]) == TABLE_COLUMNS:
            return {"header_index": index, "lines": lines}
    raise LookupError(
        f"no capability table found in {CAPABILITY_TABLE_DOC} with header "
        f"'CLI | {' | '.join(TABLE_COLUMNS)}'"
    )


def _table_rows(text: str) -> dict[str, list[str]]:
    """{display_name: [cell, ...]} for every data row of the capability table,
    keyed by the row's first column (expected to be a display name).
    """
    found = _find_capability_table(text)
    lines = found["lines"]
    header_index = found["header_index"]
    rows: dict[str, list[str]] = {}
    # Row after the header is the "---" separator; data rows follow until a
    # line that is no longer a table row.
    for line in lines[header_index + 2 :]:
        stripped = line.strip()
        if not stripped.startswith("|"):
            break
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) != len(TABLE_COLUMNS) + 1:
            break
        rows[cells[0]] = cells[1:]
    return rows


def _bool_cell(value: bool) -> str:
    return "sí" if value else "no"


class EveryRegisteredAdapterIsDocumentedTest(unittest.TestCase):
    """Names every adapter `darq.adapters.available()` registers, and
    checks it against the docs -- never the other way around. The registry
    is the source of truth; a document is either in agreement with it or it
    is wrong.
    """

    def test_every_adapter_is_named_in_every_entry_point_document(self) -> None:
        registry = available()
        failures: list[str] = []
        for doc_name in DOCS_NAMING_EVERY_ADAPTER:
            text = _read(doc_name)
            for cli_id in registry.ids():
                adapter = registry.get(cli_id)
                display_name = adapter.display_name
                if display_name not in text:
                    failures.append(
                        f"{doc_name}: does not mention {display_name!r} "
                        f"(adapter id {cli_id!r}, registered in "
                        f"darq.adapters.available())"
                    )
        self.assertFalse(failures, "\n" + "\n".join(failures))

    def test_capability_table_agrees_with_every_manifest(self) -> None:
        registry = available()
        text = _read(CAPABILITY_TABLE_DOC)
        failures: list[str] = []

        try:
            rows = _table_rows(text)
        except LookupError as error:
            self.fail(str(error))

        for cli_id in registry.ids():
            adapter = registry.get(cli_id)
            manifest = registry.manifest(cli_id)
            display_name = adapter.display_name
            row = rows.get(display_name)
            if row is None:
                failures.append(
                    f"{CAPABILITY_TABLE_DOC}: capability table has no row for "
                    f"{display_name!r} (adapter id {cli_id!r})"
                )
                continue

            expected = tuple(
                _bool_cell(manifest.declares(capability)) for capability in Capability
            ) + (adapter.tier().value,)
            for column_name, expected_cell, actual_cell in zip(TABLE_COLUMNS, expected, row):
                if actual_cell != expected_cell:
                    failures.append(
                        f"{CAPABILITY_TABLE_DOC}: row {display_name!r}, column "
                        f"{column_name!r} says {actual_cell!r}, manifest says "
                        f"{expected_cell!r}"
                    )

        # A row for a CLI the registry no longer knows would be stale prose,
        # not a registry gap -- named separately so it never masquerades as
        # a missing-adapter failure.
        documented_display_names = set(rows)
        registered_display_names = {registry.get(cli_id).display_name for cli_id in registry.ids()}
        stale = documented_display_names - registered_display_names
        for name in sorted(stale):
            failures.append(
                f"{CAPABILITY_TABLE_DOC}: capability table has a row for "
                f"{name!r}, which is not a registered adapter"
            )

        self.assertFalse(failures, "\n" + "\n".join(failures))


if __name__ == "__main__":
    unittest.main()
