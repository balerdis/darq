"""Hand-typed figures and enumerations that a guard can derive without a subprocess.

Five prose figures were found with no guard at all. Four get one here; the
fifth does not, on purpose.

1. MANUAL.md's "## Qué hacen los cinco MCPs opcionales" heading and its
   table, checked against `content.load().mcp` -- the real parser for
   `src/darq/content/mcp/`, which already knows to ignore
   `playwright-package-lock.json` because that file has no `.md` descriptor
   shape to load.

2. MANUAL.md's "con cinco generaciones de historial y no más", checked
   against `darq.cli.RETAIN_GENERATIONS`.

3. MANUAL.md's "El menú principal agrupa sus ocho entradas por intención"
   and the enumeration that follows it, checked against
   `darq.tui.navigator.main_menu()` -- both the count and, in the exact
   order the prose claims is deliberate, the entries themselves. This is the
   figure that was once right while the list beneath it silently dropped
   `Grant MCP servers`; the list is what this guards, not just the number.

4. MANUAL.md's "de una instalación anterior a 5.28.0 que la poda automática
   nunca puede alcanzar" gets NO guard here. `5.28.0` is a historical fact
   about when `Install.created_dirs`/`created` started being recorded
   (`src/darq/core/journal.py`, `src/darq/core/planner.py`) -- it
   exists only as prose in docstrings and as a git tag (`v5.28.0`), never as
   a runtime constant, schema-version field, or migration marker. A git tag
   is not read by the installed product and reading one here would mean
   shelling out to `git`, which this file exists to avoid; a docstring
   literal would just be the same hand-typed number copied to a second
   place, not derived from anything. There is nothing in the tree that
   *computes* this value, so a guard for it would only ever compare one
   retyping against another -- the exact proxy-approval failure mode this
   project has been bitten by before. Left unguarded, honestly, rather than
   faked.

5. MANUAL.md's "Los comandos distribuidos son ..." enumeration of the
   OpenCode slash commands Pegasus ships, checked against
   `content.load().commands` -- the real `src/darq/content/commands/`
   tree. This is a different command surface than
   `ManualDocumentsEveryTopLevelCommandTest`
   (`tests/test_manual_command_surface.py`), which checks the `pegasus`
   CLI's own argparse subcommands (`install`, `update`, ...); nothing
   existing already covered this enumeration, so it gets a new guard rather
   than a duplicate of one that does.

Everything here reads files already on disk and imports already-loaded
Python modules -- no subprocess, no built CLI, no zipapp -- so the whole
file is meant to cost close to nothing.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from darq import cli as cli_module
from darq.core import content as content_module
from darq.tui import navigator

REPOSITORY = Path(__file__).resolve().parents[1]
MANUAL = REPOSITORY / "MANUAL.md"

#: Spanish words for the small counts these guards may need to state. Extend
#: this, rather than hand-typing a word past it, if a count this file checks
#: ever grows into double digits.
SPANISH_ONES = {
    1: "uno",
    2: "dos",
    3: "tres",
    4: "cuatro",
    5: "cinco",
    6: "seis",
    7: "siete",
    8: "ocho",
    9: "nueve",
    10: "diez",
    20: "veinte",
}


def _spanish(count: int) -> str:
    word = SPANISH_ONES.get(count)
    if word is None:
        raise AssertionError(f"no Spanish word on file for {count}; extend SPANISH_ONES")
    return word


def _section(text: str, heading: str) -> str:
    """The text from `heading` up to (not including) the next `## ` heading."""
    start = text.index(heading)
    rest = text[start + len(heading) :]
    end = re.search(r"\n## ", rest)
    return rest[: end.start()] if end else rest


class OptionalMcpTableTest(unittest.TestCase):
    """MANUAL.md's "## Qué hacen los cinco MCPs opcionales" heading and table."""

    HEADING = "## Qué hacen los cinco MCPs opcionales"

    @classmethod
    def setUpClass(cls):
        cls.manual = MANUAL.read_text(encoding="utf-8")
        cls.mcp = content_module.load().mcp

    def test_the_heading_is_found_exactly_once(self):
        self.assertEqual(self.manual.count(self.HEADING), 1)

    def test_the_heading_names_the_real_count(self):
        expected = f"## Qué hacen los {_spanish(len(self.mcp))} MCPs opcionales"
        self.assertIn(expected, self.manual)

    def _table_row_ids(self) -> list[str]:
        section = _section(self.manual, self.HEADING)
        lines = [line for line in section.splitlines() if line.startswith("|")]
        # First line is the header (`| MCP | ... |`), second is the `| --- |` rule.
        data_rows = lines[2:]
        ids = []
        for row in data_rows:
            first_cell = row.split("|")[1].strip()
            head = re.split(r"[\s(]", first_cell, maxsplit=1)[0]
            ids.append(head.lower())
        return ids

    def test_the_table_has_exactly_one_row_per_shipped_mcp_and_names_it(self):
        """Bidirectional: the row set must equal the shipped set, not just cover it."""
        row_ids = self._table_row_ids()
        shipped_ids = [server.name for server in self.mcp]
        self.assertEqual(sorted(row_ids), sorted(shipped_ids))


class RestoreGenerationsFigureTest(unittest.TestCase):
    """MANUAL.md's "con cinco generaciones de historial y no más"."""

    ANCHOR = "generaciones de historial y no más"

    @classmethod
    def setUpClass(cls):
        cls.manual = MANUAL.read_text(encoding="utf-8")

    def test_the_anchor_is_found_exactly_once(self):
        self.assertEqual(self.manual.count(self.ANCHOR), 1)

    def test_the_figure_matches_retain_generations(self):
        expected = f"con {_spanish(cli_module.RETAIN_GENERATIONS)} {self.ANCHOR}"
        self.assertIn(expected, self.manual)


class MainMenuEntriesTest(unittest.TestCase):
    """MANUAL.md's "El menú principal agrupa sus ocho entradas por intención"
    and the enumeration that follows it -- count AND list, in order.
    """

    ANCHOR = "agrupa sus"
    PARAGRAPH_END = "accidente."

    @classmethod
    def setUpClass(cls):
        cls.install = MANUAL.read_text(encoding="utf-8")
        cls.entries = [entry.label for entry in navigator.main_menu().entries]

    def _paragraph(self) -> str:
        start = self.install.index(self.ANCHOR)
        end = self.install.index(self.PARAGRAPH_END, start) + len(self.PARAGRAPH_END)
        return self.install[start:end]

    def test_the_anchor_is_found_exactly_once(self):
        self.assertEqual(self.install.count(self.ANCHOR), 1)

    def test_the_paragraph_states_the_real_entry_count(self):
        paragraph = self._paragraph()
        expected = f"agrupa sus {_spanish(len(self.entries))} entradas"
        self.assertIn(expected, paragraph)

    def test_the_paragraph_names_every_entry_in_the_real_order(self):
        """The regression this guards: the count stayed right while the list
        beneath it silently dropped `Grant MCP servers`."""
        paragraph = self._paragraph()
        named = re.findall(r"`([^`]+)`", paragraph)
        self.assertEqual(named, self.entries)


class DistributedCommandsEnumerationTest(unittest.TestCase):
    """MANUAL.md's "Los comandos distribuidos son ..." enumeration of the
    OpenCode slash commands under `src/darq/content/commands/`.

    A different surface than `ManualDocumentsEveryTopLevelCommandTest`
    (`tests/test_manual_command_surface.py`), which checks the `pegasus`
    CLI's own argparse subcommands. Nothing already covers this
    enumeration.
    """

    START = "Los comandos distribuidos son "
    END = ". Podés leer su contenido"

    @classmethod
    def setUpClass(cls):
        cls.manual = MANUAL.read_text(encoding="utf-8")
        cls.commands = content_module.load().commands

    def test_the_anchor_is_found_exactly_once(self):
        self.assertEqual(self.manual.count(self.START), 1)

    def _named(self) -> set[str]:
        start = self.manual.index(self.START) + len(self.START)
        end = self.manual.index(self.END, start)
        sentence = self.manual[start:end]
        return set(re.findall(r"`([^`]+)`", sentence))

    def test_the_enumeration_names_exactly_the_shipped_commands(self):
        """Bidirectional: every shipped command is named, and nothing named
        is not shipped."""
        named = self._named()
        shipped = {command.name for command in self.commands}
        self.assertEqual(named, shipped)


if __name__ == "__main__":
    unittest.main()
