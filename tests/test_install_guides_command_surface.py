"""Both installation guides described a retirement the product stopped doing.

`INSTALL.md` said a bare `install`, with no `--mcp`, **retires** the servers
already bound, and gave that as the reason `update` exists.
`INSTALL_BY_AGENT.md` said the same thing to an agent, in the imperative:
"un servidor no nombrado se retira -- eso te comería en silencio cualquier
atadura de MCP que la instalación ya tuviera."

Neither is true since the guard in `cli.install`. A bare `install` over an
installation whose selection is already recorded is REFUSED before anything
is written -- precisely so that silence cannot retire it -- `--mcp none` is
the spelling that revokes on purpose, and `update` is the way to bring the
installation up to date without touching the selection. `MANUAL.md` was
brought to that truth already; these two were not, so the same product had
three documents and two accounts of it.

The two guides frame it differently on purpose and keep doing so: one is
explaining to a person why `update` exists, the other is telling an agent
which command not to run. What they share is the fact, so one guard holds it
and both paragraphs name that guard. All three halves are run against a real
installation rather than read: the refusal, that it wrote nothing, and that
`update` leaves the recorded selection exactly as it was.

The finder here works on paragraphs and not on lines, which is the one place
this file departs from `tests/test_manual_command_surface.py`: `MANUAL.md`
keeps a paragraph on one line and these two guides hard-wrap, so a
line-based finder would hold each claim to whichever fragment of a sentence
happened to carry the guard's name.
"""
from __future__ import annotations

import io
import json
from pathlib import Path

from pegasus import cli
from pegasus.adapters import available
from pegasus.core import journal as journal_module
from pegasus.core.types import Environment
from real_home import RealHomeTestCase as _RealHomeTestCase

REPOSITORY = Path(__file__).resolve().parents[1]
GUIDES = (REPOSITORY / "INSTALL.md", REPOSITORY / "INSTALL_BY_AGENT.md")

#: This module, derived rather than retyped, so renaming it fails here and
#: names the documents that have to follow.
GUARD_MODULE = Path(__file__).relative_to(REPOSITORY).as_posix()

AT = "2026-08-14T00:00:00+00:00"
CLI = available().ids()[0]
NO_BINARY = {"PATH": ""}

#: A server this release ships that needs nothing fetched and no Node on the
#: PATH, so an install can record a real selection without the suite reaching
#: for a network it refuses to have.
REMOTE_SERVER = "context7"


def paragraph_naming(document: Path, guard: str) -> str:
    """The one paragraph of ``document`` that names ``guard``.

    Paragraphs, not lines: both guides hard-wrap their prose, so the sentence
    that names the guard and the sentence that states the claim are usually
    not the same line. Empty when there is not exactly one, so every
    assertion built on it fails loudly instead of proving something about
    nothing.
    """
    blocks = [
        " ".join(block.split())
        for block in document.read_text(encoding="utf-8").split("\n\n")
        if f"`{guard}`" in block
    ]
    return blocks[0] if len(blocks) == 1 else ""


class InstallGuidesSayABareInstallIsRefusedTest(_RealHomeTestCase):
    """What a bare `install` does to a selection that is already recorded.

    Run three ways, because three separate facts are in those paragraphs and
    a reader acts on each: it is refused, the refusal writes nothing, and
    `update` brings the installation up to date while leaving the selection
    exactly where it was. The recorded selection is reconstructed the one way
    the engine reconstructs it rather than read off a field that does not
    exist.
    """

    def setUp(self):
        super().setUp()
        self.present()
        self.run_cli("install", "--cli", CLI, "--mcp", REMOTE_SERVER)

    def runtime(self) -> cli.Runtime:
        return cli.Runtime(
            filesystem=self.filesystem, home=self.home, now=AT, out=io.StringIO(), variables=NO_BINARY
        )

    def layout(self):
        return available().get(CLI).layout(Environment(home=self.home))

    def present(self) -> None:
        self.layout().config_dir.mkdir(parents=True, exist_ok=True)

    def run_cli(self, *argv) -> tuple[int, dict]:
        context = self.runtime()
        code = cli.main([*argv, "--json"], runtime=context)
        return code, json.loads(context.out.getvalue())

    def whole_home(self) -> dict[Path, bytes]:
        return {path: path.read_bytes() for path in self.home.rglob("*") if path.is_file()}

    def installed(self):
        return journal_module.install_for(cli.journal_store(self.runtime()).load(), CLI)

    def recorded_selection(self) -> tuple[str, ...]:
        selection, unresolved = cli._mcp_update_selection(
            self.installed(), display_name=cli.default_identity().display_name
        )
        self.assertEqual(unresolved, [])
        return tuple(selection)

    def test_the_example_server_is_one_this_release_ships(self):
        from pegasus.core import content as content_module

        self.assertIn(REMOTE_SERVER, {item.name for item in content_module.load().mcp})

    def test_there_is_a_recorded_selection_to_lose(self):
        """Or every run below would be firing over nothing."""
        self.assertEqual(self.recorded_selection(), (REMOTE_SERVER,))

    def test_a_bare_install_is_refused_and_writes_nothing(self):
        """The defect itself. Both guides said this retires the selection; it
        does not get far enough to retire anything."""
        before = self.whole_home()
        code, report = self.run_cli("install", "--cli", CLI)
        self.assertNotEqual(code, 0)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(self.whole_home(), before)
        self.assertEqual(self.recorded_selection(), (REMOTE_SERVER,))

    def test_the_deliberate_spelling_empties_the_recorded_selection(self):
        """What a person who really does want it gone types instead."""
        code, _ = self.run_cli("install", "--cli", CLI, "--mcp", cli._MCP_NONE)
        self.assertEqual(code, 0)
        self.assertEqual(self.recorded_selection(), ())

    def test_update_brings_the_installation_up_to_date_and_keeps_the_selection(self):
        """The reason both guides point at `update`, measured rather than
        asserted."""
        code, _ = self.run_cli("update", "--cli", CLI)
        self.assertEqual(code, 0)
        self.assertEqual(self.recorded_selection(), (REMOTE_SERVER,))

    def test_each_guide_holds_exactly_one_paragraph_naming_this(self):
        """Everything below reads those paragraphs; two of them in one
        document, or none, proves nothing."""
        for guide in GUIDES:
            with self.subTest(document=guide.name):
                self.assertTrue(
                    paragraph_naming(guide, type(self).__name__),
                    f"no single paragraph of {guide.name} names {type(self).__name__}",
                )

    def test_each_guide_names_the_deliberate_spelling(self):
        """Derived from the flag value the CLI actually understands, so a
        rename of it fails here and names the documents that have to follow.
        Neither guide had it at all: they described the silent retirement and
        never the way to ask for one."""
        for guide in GUIDES:
            with self.subTest(document=guide.name):
                self.assertIn(
                    f"`--mcp {cli._MCP_NONE}`", paragraph_naming(guide, type(self).__name__)
                )

    def test_each_guide_names_the_command_that_keeps_the_selection(self):
        for guide in GUIDES:
            with self.subTest(document=guide.name):
                self.assertIn("`update`", paragraph_naming(guide, type(self).__name__))

    def test_each_guide_says_where_this_was_measured(self):
        for guide in GUIDES:
            with self.subTest(document=guide.name):
                self.assertIn(f"`{GUARD_MODULE}`", paragraph_naming(guide, type(self).__name__))


if __name__ == "__main__":  # pragma: no cover
    import unittest

    unittest.main()
