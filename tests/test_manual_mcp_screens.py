"""`MANUAL.md` documents the TUI's two MCP screens, against the real surface.

The manual described the `Grant MCP servers` screen at length and never
mentioned the *install* screen's MCP step at all -- the checklist that decides
which servers this release ships end up part of the installation. Its behaviour
is not obvious (a bound server is granted but never installed, so it used to
open unchecked and a Continue that touched nothing retired it -- commit
`a190720`), and a real installation nearly lost its bound servers to that.
Something undocumented cannot be relied on, and something documented from
memory goes stale the first time a label changes.

So every string this file requires the manual to carry is DERIVED from the
product: the heading comes out of `view.render` on a real screen object, the
bound-row prefix out of the row the same renderer draws, the preview's
retirement label out of `cli.prose_for` on a real planned report, and the menu
entries out of `navigator.main_menu`. Nothing here is a literal typed twice, so
renaming any of them fails here and names the document that has to follow.

What is deliberately NOT asserted is the Spanish prose around those strings. A
regex over a sentence somebody may legitimately reword proves nothing and
breaks for the wrong reasons; what is checkable is that the manual quotes the
words a person actually sees on screen, and that it quotes them in the section
about the screen they belong to.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from darq import cli  # noqa: F401  (imported first: `tui.view` imports it back)
from darq.tui import navigator, view
from darq.tui.navigator import CliOption, McpOption, McpSelectionScreen

MANUAL = Path(__file__).resolve().parents[1] / "MANUAL.md"

CLI_OPTION = CliOption(
    id="opencode", display_name="OpenCode", config_dir=Path("/probe"), tier="supported"
)
BOUND_KEY = "a-key-of-your-own"


def rendered_selection_screen() -> tuple[str, ...]:
    """The install step's MCP checklist, drawn by the real renderer."""
    screen = McpSelectionScreen(
        cli=CLI_OPTION,
        options=(
            McpOption(id="probe-bound", description="A server you already run", bound_to=BOUND_KEY),
            McpOption(id="probe-own", description="A server Pegasus obtains"),
        ),
        chosen=("probe-bound", "probe-own"),
    )
    return tuple(
        "".join(span.text for span in line.spans)
        for line in view.render(screen, cursor=0)
    )


def screen_heading_tail() -> str:
    """What the heading says after the CLI's name -- the part that is the
    screen's own identity rather than this machine's."""
    return rendered_selection_screen()[0].split(" · ")[-1]


def bound_row_prefix() -> str:
    """How a row says it is bound, with the key itself taken back out.

    Read off the helper the renderer calls, then checked against a real
    rendered row below, so it is the screen's own wording and not this file's
    idea of it.
    """
    detail = view._mcp_row_detail(McpOption(id="probe", description="D", bound_to=BOUND_KEY))
    return detail.split(BOUND_KEY)[0]


def retirement_label() -> str:
    """The preview line that tells a person what a Continue would take away."""
    report = {
        "status": "planned",
        "command": "install",
        "cli": CLI_OPTION.id,
        "created": [],
        "updated": [],
        "unchanged": [],
        "skipped": [],
        "retired": [{"id": "mcp:probe", "target": "/probe/target"}],
    }
    return next(
        line for line in cli.prose_for(report).splitlines() if line.endswith(":")
    )


def menu_labels() -> dict[str, str]:
    """The main menu's own entry labels, by the word this file knows them by."""
    menu = navigator.main_menu(
        detections=(), installed=(), display_name="Probe", version="0.0.0"
    )
    labels = [entry.label for entry in menu.entries]
    return {
        "install": next(label for label in labels if label == "Install"),
        "grant": next(label for label in labels if label.startswith("Grant ")),
    }


class ManualDocumentsTheInstallMcpScreenTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manual = MANUAL.read_text(encoding="utf-8")

    def test_the_derivations_are_not_vacuous(self):
        """Each helper must return something specific; an empty string would
        make every assertion below pass against any document at all."""
        self.assertIn("mcp", screen_heading_tail())
        self.assertIn("bound", bound_row_prefix())
        self.assertNotIn(BOUND_KEY, bound_row_prefix())
        rendered = next(line for line in rendered_selection_screen() if BOUND_KEY in line)
        self.assertIn(
            bound_row_prefix() + BOUND_KEY,
            rendered,
            "the prefix this file reads is not the one the screen draws",
        )
        self.assertTrue(retirement_label().endswith(":"))
        self.assertEqual(menu_labels()["grant"], "Grant MCP servers")

    def test_the_manual_quotes_the_screens_own_heading(self):
        """A person on that screen has to be able to tell it is this one."""
        self.assertIn(
            screen_heading_tail(),
            self.manual,
            "MANUAL.md never names the install step's MCP screen",
        )

    def test_the_manual_says_how_a_bound_row_announces_itself(self):
        """The whole hazard: a bound row and an ordinary one are the same
        checkbox meaning different things, and only this prefix tells them
        apart on screen."""
        self.assertIn(
            f"`{bound_row_prefix()}",
            self.manual,
            "MANUAL.md never quotes how a bound server labels itself",
        )

    def test_the_manual_quotes_the_previews_retirement_section(self):
        """What saves somebody who did touch a row: the preview names, before
        anything is written, exactly what a Continue would take away."""
        self.assertIn(
            retirement_label(),
            self.manual,
            "MANUAL.md never quotes the preview's retirement section",
        )

    def test_the_manual_reaches_the_screen_through_the_menu_entry_that_leads_there(self):
        """Both screens are documented, and neither is reachable by guessing:
        the manual has to name the menu entry each one is behind."""
        for label in menu_labels().values():
            self.assertIn(f"`{label}`", self.manual, f"MANUAL.md never names the `{label}` entry")

    def test_the_two_screens_are_documented_apart(self):
        """Converting a server between bound and Pegasus-administered is the
        grant screen's job, not this one's. Both headings must be present, so
        the manual cannot be read as describing a single MCP screen."""
        self.assertIn(screen_heading_tail(), self.manual)
        self.assertIn(f"`{menu_labels()['grant']}`", self.manual)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
