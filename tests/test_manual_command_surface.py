"""`MANUAL.md` describes what the commands do. Three of those descriptions
were describing something else.

This file is `test_manual_mcp_screens.py`'s sibling for the flags rather than
the screens, and it follows the same discipline: every fact it holds the
document to is DERIVED -- from the parser, from an identity, or from running
the command against a real home and looking at what landed on disk. Nothing
here is a literal typed twice, and the Spanish prose around those facts is
deliberately not pattern-matched: a regex over a sentence somebody may
legitimately reword proves nothing and breaks for the wrong reasons.

The three claims, and how each was wrong:

* "Los tres reaplican la configuración renderizada al terminar" said `pegasus
  mcp list` rewrites `opencode.json`. It does not -- it loads the journal and
  reads the settings, and writes nothing at all. Two of the three write; the
  sentence counted all three.
* "Este permiso se renderiza como `"ask"` ... cada vez que un agente lo
  necesite, OpenCode va a preguntar" said a directory you grant still prompts.
  It does not: `render._permission` writes `f"{path}/*": "allow"` for every
  granted directory, *after* the `"*": "ask"` baseline, and the runtime keeps
  the last matching rule. `"ask"` is what a directory you did NOT grant gets.
  Read as written, the paragraph promised a prompt that will never come, on a
  permission whose whole point is that it stops coming.
* "la ausencia del flag ya es la decisión de no instalarlo" was true when it
  was written and is now true only for a first install. A bare `install` over
  an installation that already has a recorded selection is refused outright,
  precisely so that silence cannot retire it -- and `--mcp none` is the
  spelling that revokes it on purpose.

And one gap, the same surface read the other way round: `pegasus upgrade`
shipped and the manual never learned it existed. The last class here derives
the whole top-level surface from the parser, so the next command cannot go
missing the way that one did -- see its own docstring for what a coverage
check can and cannot prove.

Each corrected paragraph is found by the name of the guard that measures it,
which is the convention `tests/test_manual_figures.py` already established: a
machine-shaped token somebody has to edit on purpose, and the same sentence
that tells a reader where the fact was checked. The coverage class is the
exception and names itself nowhere in the document: it holds no single claim
a sentence could point at.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import re
from pathlib import Path

from pegasus import cli
from pegasus.adapters import available
from pegasus.core import journal as journal_module
from pegasus.core.types import Environment
from real_home import RealHomeTestCase as _RealHomeTestCase

REPOSITORY = Path(__file__).resolve().parents[1]
MANUAL = REPOSITORY / "MANUAL.md"

#: This module, derived rather than retyped, so renaming it fails here and
#: names the document that has to follow.
GUARD_MODULE = Path(__file__).relative_to(REPOSITORY).as_posix()

AT = "2026-08-14T00:00:00+00:00"
CLI = available().ids()[0]
NO_BINARY = {"PATH": ""}

#: A server this release ships that needs nothing fetched and no Node on the
#: PATH, so an install can record a real selection without the suite reaching
#: for a network it refuses to have.
REMOTE_SERVER = "context7"

#: A key Pegasus never heard of, standing in for a server the person
#: administers themselves -- the same stand-in `tests/test_cli_mcp.py` uses,
#: and pinned below for the same reason: the day it becomes a shipped server,
#: `mcp grant` starts refusing it and every measurement here silently stops
#: measuring what it says it does.
OWN_KEY = "figma"


def paragraph_naming(guard: str) -> str:
    """The one line of the manual that names ``guard``.

    Empty when there is not exactly one, so every assertion built on it fails
    loudly instead of proving something about nothing.
    """
    lines = [line for line in MANUAL.read_text(encoding="utf-8").splitlines() if f"`{guard}`" in line]
    return lines[0] if len(lines) == 1 else ""


def subcommands_under(dest: str) -> frozenset[str]:
    """Every subcommand the real parser offers under ``dest``.

    Read off `cli._parser` rather than listed here, so a subcommand added or
    removed reaches this file instead of going unnoticed by it.
    """
    found: set[str] = set()

    def walk(parser: argparse.ArgumentParser) -> None:
        for action in parser._actions:
            if not isinstance(action, argparse._SubParsersAction):
                continue
            if action.dest == dest:
                found.update(action.choices)
            for child in action.choices.values():
                walk(child)

    walk(cli._parser(cli.default_identity()))
    return frozenset(found)


class RealHomeTestCase(_RealHomeTestCase):
    """The same throwaway-home harness `tests/test_cli_mcp.py` runs on: real
    disk, real journal, the commands driven through `cli.main` exactly as a
    person would type them."""

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

    def rendered(self) -> bytes:
        return self.layout().settings_file.read_bytes()

    def whole_home(self) -> dict[Path, bytes]:
        return {path: path.read_bytes() for path in self.home.rglob("*") if path.is_file()}

    def installed(self):
        return journal_module.install_for(cli.journal_store(self.runtime()).load(), CLI)

    def declare_own_mcp_server(self, key: str) -> None:
        """What a person administering their own MCP server leaves in the
        CLI's own configuration: a key under `/mcp` Pegasus never wrote."""
        settings = self.layout().settings_file
        document = json.loads(settings.read_text(encoding="utf-8"))
        document.setdefault("mcp", {})[key] = {"type": "local", "command": [f"{key}-server"]}
        settings.write_text(json.dumps(document, indent=2), encoding="utf-8")


class ManualSaysWhichMcpSubcommandsRewriteTheConfigurationTest(RealHomeTestCase):
    """Which of `pegasus mcp`'s subcommands write, measured by running them.

    The partition is produced here rather than read out of the source: each
    subcommand is run against a real installation and the rendered
    `opencode.json` is compared byte for byte across the call. A source-level
    check for "this one calls `install`" would approve by a proxy and would
    keep passing the day the call is added somewhere it should not be.

    `list` is also checked against the *whole* home and not just the settings
    file: "no escribe nada" is a claim about the machine, and a command that
    left a snapshot generation or a journal write behind would satisfy a
    narrower check while making the sentence false.
    """

    def setUp(self):
        super().setUp()
        self.present()
        self.run_cli("install", "--cli", CLI, "--mcp", cli._MCP_NONE)
        self.declare_own_mcp_server(OWN_KEY)
        self.offered = subcommands_under("mcp_command")
        self.writes: set[str] = set()
        self.reads: set[str] = set()
        self._measure("list")
        self._measure("grant", OWN_KEY)
        self._measure("revoke", OWN_KEY)

    def _measure(self, name: str, *arguments: str) -> None:
        before_home = self.whole_home()
        before = self.rendered()
        code, _ = self.run_cli("mcp", name, "--cli", CLI, *arguments)
        self.assertEqual(code, 0, f"`mcp {name}` failed, so nothing here measured anything")
        if self.rendered() != before:
            self.writes.add(name)
        else:
            self.reads.add(name)
            self.assertEqual(
                self.whole_home(), before_home, f"`mcp {name}` wrote somewhere outside the rendered configuration"
            )

    def test_the_stand_in_key_is_not_a_shipped_server(self):
        """Or `grant` would refuse it and the measurement above would be of a
        failure, not of a write."""
        from pegasus.core import content as content_module

        self.assertNotIn(OWN_KEY, {item.name for item in content_module.load().mcp})

    def test_every_subcommand_the_parser_offers_was_measured(self):
        """A fourth subcommand must reach this file rather than slip past the
        sentence it would also belong in."""
        self.assertEqual(self.writes | self.reads, self.offered)

    def test_some_rewrite_and_some_do_not(self):
        """Both halves have to be non-empty, or the two assertions below are
        each satisfied by an empty set and prove nothing."""
        self.assertTrue(self.writes)
        self.assertTrue(self.reads)

    def test_the_paragraph_is_found_exactly_once(self):
        self.assertTrue(
            paragraph_naming(type(self).__name__),
            f"no single line of {MANUAL.name} names {type(self).__name__}",
        )

    def test_the_paragraph_names_every_subcommand_that_rewrites(self):
        paragraph = paragraph_naming(type(self).__name__)
        program = cli.default_identity().program_name
        for name in sorted(self.writes):
            self.assertIn(f"`{program} mcp {name}`", paragraph)

    def test_the_paragraph_claims_nothing_for_the_ones_that_do_not(self):
        """The defect itself: `list` was inside the claim, so a reader was
        told a read-only command rewrites their configuration."""
        paragraph = paragraph_naming(type(self).__name__)
        program = cli.default_identity().program_name
        for name in sorted(self.reads):
            self.assertNotIn(f"`{program} mcp {name}`", paragraph)
            self.assertNotIn(f"`{name}`", paragraph)

    def test_the_paragraph_says_where_this_was_measured(self):
        self.assertIn(f"`{GUARD_MODULE}`", paragraph_naming(type(self).__name__))


class ManualSaysHowAGrantedDirectoryIsRenderedTest(RealHomeTestCase):
    """What `pegasus directory grant` actually writes into `opencode.json`.

    The example path is not chosen here: it is read out of the manual's own
    fenced `directory grant` command, whose first two words come from this
    binary's identity. So the directory this grants is the directory the
    reader was told to grant, and the entry asserted below is the entry that
    reader would find on their own machine.

    Run end to end, against real disk, because the claim is about what lands
    in the configuration file -- not about what `render._permission` returns
    on the way there.
    """

    def setUp(self):
        super().setUp()
        self.path = self.example_path()
        self.present()
        self.run_cli("install", "--cli", CLI, "--mcp", cli._MCP_NONE)
        code, _ = self.run_cli("directory", "grant", "--cli", CLI, self.path)
        self.assertEqual(code, 0, "the manual's own example grant failed")
        self.maps = [
            agent["permission"]["external_directory"]
            for agent in json.loads(self.rendered())["agent"].values()
            if "external_directory" in agent.get("permission", {})
        ]

    @staticmethod
    def example_path() -> str:
        """The directory the manual's own fenced command grants."""
        program = cli.default_identity().program_name
        fenced = re.compile(rf"^{re.escape(program)} directory grant --cli \S+ (\S+)$", re.MULTILINE)
        found = fenced.findall(MANUAL.read_text(encoding="utf-8"))
        return found[0] if len(set(found)) == 1 else ""

    def test_the_manual_shows_a_single_example_directory(self):
        """Everything below grants it; two different ones, or none, would
        leave this measuring a path nobody was shown."""
        self.assertTrue(self.example_path(), f"{MANUAL.name} has no single fenced directory grant to read")

    def test_every_agent_carries_the_granted_directory(self):
        """The manual's other claim about this: a grant reaches every agent,
        primary and sub-agent alike."""
        self.assertTrue(self.maps)
        self.assertEqual(len(self.maps), len(json.loads(self.rendered())["agent"]))
        for entry in self.maps:
            self.assertIn(f"{self.path}/*", entry)

    def test_a_grant_is_not_a_prompt(self):
        """The whole defect. The paragraph said a granted directory renders as
        `"ask"`, which is the value of the baseline it is written after -- if
        the two were ever the same value, granting a directory would change
        nothing at all."""
        for entry in self.maps:
            self.assertNotEqual(entry[f"{self.path}/*"], entry["*"])

    def test_the_paragraph_quotes_the_entry_a_grant_actually_writes(self):
        """Both halves, each attached to what it belongs to, because the value
        alone is what went wrong: `"ask"` was in the old sentence too."""
        paragraph = paragraph_naming(type(self).__name__)
        entry = self.maps[0]
        granted = json.dumps({f"{self.path}/*": entry[f"{self.path}/*"]})[1:-1]
        baseline = json.dumps({"*": entry["*"]})[1:-1]
        self.assertIn(granted, paragraph)
        self.assertIn(baseline, paragraph)

    def test_the_paragraph_is_found_exactly_once(self):
        self.assertTrue(
            paragraph_naming(type(self).__name__),
            f"no single line of {MANUAL.name} names {type(self).__name__}",
        )

    def test_the_paragraph_says_where_this_was_measured(self):
        self.assertIn(f"`{GUARD_MODULE}`", paragraph_naming(type(self).__name__))


class ManualSaysHowAnMcpSelectionIsRevokedOnPurposeTest(RealHomeTestCase):
    """Silence about `--mcp` stopped meaning "install nothing" for a repeat
    install, and the manual still said it did.

    A first install with no `--mcp` selects nothing, which is what the
    sentence was written for and still true. A *second* one, over an
    installation whose selection is already recorded, is refused before
    anything is written -- a bare reinstall run for an unrelated reason would
    otherwise retire every server, convention and binding it had, and report
    success. `--mcp none` is the one spelling that asks for that retirement on
    purpose.

    All three are run here rather than read: the refusal, the fact that it
    wrote nothing, and that the deliberate spelling really does empty the
    recorded selection.
    """

    def setUp(self):
        super().setUp()
        self.present()
        self.run_cli("install", "--cli", CLI, "--mcp", REMOTE_SERVER)

    def test_the_example_server_is_one_this_release_ships(self):
        from pegasus.core import content as content_module

        self.assertIn(REMOTE_SERVER, {item.name for item in content_module.load().mcp})

    def test_a_bare_reinstall_over_a_recorded_selection_is_refused(self):
        before = self.whole_home()
        code, report = self.run_cli("install", "--cli", CLI)
        self.assertNotEqual(code, 0)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(self.whole_home(), before)

    def recorded_selection(self) -> tuple[str, ...]:
        """What a later `update` would replay -- the installation's own
        recorded selection, reconstructed the one way the engine reconstructs
        it rather than read off a field that does not exist."""
        selection, unresolved = cli._mcp_update_selection(
            self.installed(), display_name=cli.default_identity().display_name
        )
        self.assertEqual(unresolved, [])
        return tuple(selection)

    def test_the_recorded_selection_is_what_the_refusal_is_protecting(self):
        """Or the refusal above would be firing over nothing."""
        self.assertEqual(self.recorded_selection(), (REMOTE_SERVER,))

    def test_the_deliberate_spelling_empties_the_recorded_selection(self):
        code, _ = self.run_cli("install", "--cli", CLI, "--mcp", cli._MCP_NONE)
        self.assertEqual(code, 0)
        self.assertEqual(self.recorded_selection(), ())
        # And with nothing recorded, silence is harmless again: the refusal is
        # about losing a selection, not about the flag being absent.
        self.assertEqual(self.run_cli("install", "--cli", CLI)[0], 0)

    def test_the_paragraph_is_found_exactly_once(self):
        self.assertTrue(
            paragraph_naming(type(self).__name__),
            f"no single line of {MANUAL.name} names {type(self).__name__}",
        )

    def test_the_paragraph_names_the_deliberate_spelling(self):
        """Derived from the flag value the CLI actually understands, so a
        rename of it fails here and names the document that has to follow."""
        self.assertIn(f"`--mcp {cli._MCP_NONE}`", paragraph_naming(type(self).__name__))

    def test_the_paragraph_says_where_this_was_measured(self):
        self.assertIn(f"`{GUARD_MODULE}`", paragraph_naming(type(self).__name__))


class ManualDocumentsEveryTopLevelCommandTest(RealHomeTestCase):
    """Every subcommand the flags offer is reachable from this manual.

    `pegasus upgrade` shipped and the manual never learned it existed: the
    document covered `install`, `update`, `uninstall`, `repair`, `doctor`,
    `restore`, `models`, `mcp` and `directory`, and simply stopped there. A
    reader looking for how to replace the binary found nothing, and nothing
    anywhere said the list had gone short.

    What this proves and what it does not, plainly: it proves each command is
    named in the document as something a person can type, derived from the
    real parser so the tenth command cannot slip past the way the ninth did.
    It does not prove that what the manual then says about a command is true
    -- that is held, one claim at a time, by the guards above and by
    `tests/test_manual_figures.py`, and no coverage check can stand in for
    them.

    The version flag is here rather than in a class of its own because it is
    the same gap in the same surface: a way to ask this binary what it is,
    answered by the parser alone, that a person reads about in the same
    breath as replacing it.
    """

    def setUp(self):
        super().setUp()
        self.manual = MANUAL.read_text(encoding="utf-8")
        self.program = cli.default_identity().program_name

    def test_the_parser_offers_a_surface_to_check_against(self):
        """Or every assertion below would pass over an empty set."""
        self.assertGreater(len(subcommands_under("command")), 1)

    def test_every_subcommand_is_named_as_something_a_person_can_type(self):
        for name in sorted(subcommands_under("command")):
            self.assertIn(
                f"{self.program} {name}",
                self.manual,
                f"{MANUAL.name} never names `{self.program} {name}`",
            )

    def version_flags(self) -> list[str]:
        return [
            option
            for action in cli._parser(cli.default_identity())._actions
            if action.dest == "version"
            for option in action.option_strings
        ]

    def test_the_version_flag_is_named_in_the_spelling_the_parser_accepts(self):
        """Both spellings come off the parser's own action, never retyped."""
        flags = self.version_flags()
        self.assertTrue(flags, "the parser no longer offers a version flag")
        for flag in flags:
            self.assertIn(f"`{self.program} {flag}`", self.manual)

    def test_the_manual_names_no_bare_flag_the_parser_would_reject(self):
        """The other direction, which the check above cannot see.

        Dropping a spelling from the parser leaves every remaining one still
        documented, so that check stays green while the manual points at a
        flag that no longer exists. This reads the bare-flag invocations out
        of the document and requires the parser to know each one -- so a
        spelling can be removed or renamed, but not silently left behind
        here.
        """
        named = set(re.findall(rf"`{re.escape(self.program)} (-{{1,2}}[a-zA-Z][\w-]*)`", self.manual))
        self.assertTrue(named, f"{MANUAL.name} names no bare flag at all, so this proves nothing")
        accepted = {
            option
            for action in cli._parser(cli.default_identity())._actions
            for option in action.option_strings
        }
        self.assertEqual(named - accepted, set())

    def test_the_version_flag_answers_with_this_binarys_own_version(self):
        """Run, not read: the manual's reason for naming it is that it answers
        without opening a home or reading a journal, which is exactly when a
        person needs it."""
        printed = io.StringIO()
        # argparse's version action writes straight to `sys.stdout` and exits,
        # never through the runtime's own stream, so this is captured here
        # rather than read off `runtime.out` -- and captured at all so the
        # suite's own output stays the suite's.
        with contextlib.redirect_stdout(printed), self.assertRaises(SystemExit) as raised:
            cli.main(["--version"], runtime=self.runtime())
        self.assertEqual(raised.exception.code, 0)
        self.assertIn(cli.default_identity().version, printed.getvalue())

    def test_the_menu_entry_that_leads_to_the_upgrade_is_quoted_as_drawn(self):
        """The TUI half, derived from the menu itself the same way
        `tests/test_manual_mcp_screens.py` derives the two it documents."""
        from pegasus.tui import navigator

        labels = [entry.label for entry in navigator.main_menu().entries]
        upgrade = [label for label in labels if label.lower() == "upgrade"]
        self.assertEqual(len(upgrade), 1, f"the main menu no longer offers one Upgrade entry: {labels}")
        self.assertIn(f"`{upgrade[0]}`", self.manual)


if __name__ == "__main__":  # pragma: no cover
    import unittest

    unittest.main()
