"""`MANUAL.md` told the reader to go get OpenCode. This project had already
got it for them.

The paragraph said you need OpenCode installed outside Pegasus and that
"Pegasus no lo instala, actualiza ni desinstala". That is true of the
`pegasus` binary and false of the project: the repository root ships
`install.sh`, the very asset the documented one-line `curl ... | bash`
downloads, and that script installs nvm, Node and OpenCode before it ever
gets to the binary. A person following the documented path had OpenCode
already, and this paragraph sent them off to install it again.

So the claim is narrowed to the binary, and both halves are RUN rather than
read, which is the discipline `tests/test_manual_command_surface.py` holds
every claim it measures to:

* the binary's half, by asking a real `install` for a machine with no
  OpenCode on it and looking at what came back -- a refusal that writes
  nothing, which is what "sólo se integra con una instalación existente"
  means when a machine is put to it;
* the installer's half, by running the real `install.sh` in `--verify` mode
  against a throwaway home with nothing present, and reading the plan the
  script itself prints. What the manual has to name is derived from that
  plan, so a component the installer stops bringing -- or starts bringing --
  reaches this file instead of going unnoticed by it.

What this does NOT hold is the negative in the middle of the sentence: that
the binary never *updates* or *uninstalls* OpenCode either. Proving the
absence of a behaviour nothing implements would mean asserting over the
shape of the source, and `tests/test_manual_command_surface.py`'s coverage
class already derives the whole top-level surface from the parser for the
one thing a check like that can honestly prove. The half that was false is
the half measured here.
"""
from __future__ import annotations

import io
import json
import shutil
import stat
import subprocess
import sys
from pathlib import Path

from pegasus import cli
from pegasus.adapters import available
from real_home import RealHomeTestCase as _RealHomeTestCase

REPOSITORY = Path(__file__).resolve().parents[1]
MANUAL = REPOSITORY / "MANUAL.md"
INSTALL_GUIDE = REPOSITORY / "INSTALL.md"
INSTALLER = REPOSITORY / "install.sh"

sys.path.insert(0, str(REPOSITORY / "tools"))

import check_docs_links as checker  # noqa: E402

#: This module, derived rather than retyped, so renaming it fails here and
#: names the document that has to follow.
GUARD_MODULE = Path(__file__).relative_to(REPOSITORY).as_posix()

AT = "2026-08-14T00:00:00+00:00"
CLI = available().ids()[0]

#: The host CLI, spelled the way its own adapter spells it -- which is how
#: the plan below names it too, so the manual is held to the product's word
#: for it and not to one typed here.
HOST = available().get(CLI).display_name

#: Resolved from this process's own PATH and always invoked by absolute path:
#: the runs below hand the script a deliberately shrunk PATH, which would
#: otherwise make `bash` itself unresolvable. Same workaround, and same
#: reason, as `tests/test_install_script.py`.
BASH = shutil.which("bash") or "/bin/bash"

#: The narrow set of system directories the script's own plumbing needs
#: (`sed`, `cat`, `uname`, ...). Kept this short on purpose: a wider PATH
#: would let a `node` or an `opencode` from this machine answer the script's
#: detection, and the plan would then be a plan for somebody else's computer.
SYSTEM_PATH = "/usr/bin:/bin"

#: The heading the script prints over its plan. Retyped, because it is prose
#: the script emits and there is nothing in the tree to derive it from; the
#: block is asserted to have been found at all, so a rename fails loudly here
#: rather than leaving this measuring an empty list.
PLAN_HEADING = "Se instalará"

#: A `python3` that answers the two questions the script asks it: its version,
#: and whether that version is new enough. Present and valid, so the run below
#: is about Node and OpenCode and not about a blocked preflight.
PYTHON_STUB = 'case "$2" in\n  *sys.exit*) exit 0 ;;\n  *) echo "3.12.4" ;;\nesac'

#: A `curl` that succeeds and writes the file it was handed with `-o`, the way
#: the real one does. `--verify` downloads nothing, but the script's own
#: preflight still wants curl to exist.
CURL_STUB = 'dest=""\nwhile [ $# -gt 0 ]; do\n  if [ "$1" = "-o" ]; then dest="$2"; shift; fi\n  shift\ndone\nif [ -n "$dest" ]; then : > "$dest"; fi\nexit 0'


def paragraph_naming(guard: str) -> str:
    """The one line of the manual that names ``guard``.

    Empty when there is not exactly one, so every assertion built on it fails
    loudly instead of proving something about nothing.
    """
    lines = [line for line in MANUAL.read_text(encoding="utf-8").splitlines() if f"`{guard}`" in line]
    return lines[0] if len(lines) == 1 else ""


def installer_section_link() -> str:
    """The link into the guide's own section about `install.sh`.

    Its anchor is slugged by the repository's own link checker from the
    guide's own first numbered heading, so renaming that heading fails here
    and names the document that has to follow it.
    """
    headings = [
        line[3:].strip()
        for line in INSTALL_GUIDE.read_text(encoding="utf-8").splitlines()
        if line.startswith("## 1.")
    ]
    if len(headings) != 1:
        return ""
    return f"({INSTALL_GUIDE.name}#{checker.slug(headings[0])})"


def _stub(directory: Path, name: str, body: str) -> None:
    path = directory / name
    path.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


class ManualSaysWhoInstallsOpenCodeTest(_RealHomeTestCase):
    """Who brings OpenCode to a machine: not the binary, and yes the script
    the documented one-liner runs."""

    def setUp(self):
        super().setUp()
        self.stubs = self.home / "stubs"
        self.stubs.mkdir()
        _stub(self.stubs, "python3", PYTHON_STUB)
        _stub(self.stubs, "curl", CURL_STUB)
        self.paragraph = paragraph_naming(type(self).__name__)

    def runtime(self) -> cli.Runtime:
        return cli.Runtime(
            filesystem=self.filesystem, home=self.home, now=AT, out=io.StringIO(), variables={"PATH": ""}
        )

    def run_cli(self, *argv) -> tuple[int, dict]:
        context = self.runtime()
        code = cli.main([*argv, "--json"], runtime=context)
        return code, json.loads(context.out.getvalue())

    def whole_home(self) -> dict[Path, bytes]:
        return {path: path.read_bytes() for path in self.home.rglob("*") if path.is_file()}

    def verify(self) -> subprocess.CompletedProcess:
        """The real installer, asked what it would do and told to do nothing.

        `--verify` writes nothing at all -- asserted below against the whole
        throwaway home, because a plan-printing run that left a directory
        behind would make this a test that installs things.
        """
        return subprocess.run(
            [BASH, str(INSTALLER), "--verify"],
            env={"HOME": str(self.home), "PATH": f"{self.stubs}:{SYSTEM_PATH}"},
            cwd=str(REPOSITORY),
            text=True,
            capture_output=True,
            timeout=60,
            stdin=subprocess.DEVNULL,
        )

    def planned(self, printed: str) -> list[str]:
        """What the script's own plan says a real run would install.

        The product's own binary is dropped: this paragraph is about what a
        person needs before that binary is any use, and the binary installing
        itself is the one line of the plan that says nothing about that.
        """
        lines = printed.splitlines()
        heads = [index for index, line in enumerate(lines) if PLAN_HEADING in line and line.startswith("===")]
        if len(heads) != 1:
            return []
        items = []
        for line in lines[heads[0] + 1:]:
            if line.startswith("==="):
                break
            item = line.strip()
            if item and cli.default_identity().program_name not in item and str(self.home) not in item:
                items.append(item)
        return items

    def test_the_paragraph_is_found_exactly_once(self):
        """Everything below reads this paragraph; two of them, or none, proves
        nothing."""
        self.assertTrue(
            self.paragraph, f"no single line of {MANUAL.name} names {type(self).__name__}"
        )

    def test_the_binary_refuses_a_machine_that_has_no_host_cli_on_it(self):
        """The half that stays true, run rather than asserted. `install` on a
        machine without OpenCode does not fetch one: it stops, says why, and
        leaves the home exactly as it found it."""
        before = self.whole_home()
        code, report = self.run_cli("install", "--cli", CLI, "--mcp", cli._MCP_NONE)
        self.assertNotEqual(code, 0)
        self.assertEqual(report["status"], "failed")
        self.assertIn(HOST, report["error"])
        self.assertEqual(self.whole_home(), before)

    def test_the_installer_this_project_ships_is_at_the_root_and_executable(self):
        """The asset the documented one-liner downloads and pipes into a
        shell. If it is not here, the paragraph is pointing at nothing."""
        self.assertTrue(INSTALLER.is_file(), f"{INSTALLER.name} is not at the repository root")
        self.assertTrue(INSTALLER.stat().st_mode & stat.S_IXUSR)

    def test_the_plan_the_installer_prints_brings_the_host_cli(self):
        """The half that was false. Nothing is present on this throwaway
        machine, so what the script says it would install is the whole list of
        what it brings -- and the host CLI, named by its own adapter, has to
        be on it or the paragraph's new claim is the old one's mirror image.
        """
        printed = self.verify()
        self.assertEqual(printed.returncode, 0, printed.stderr)
        items = self.planned(printed.stdout)
        self.assertTrue(items, f"no plan block under {PLAN_HEADING!r}:\n\n{printed.stdout}")
        self.assertTrue(
            any(item.startswith(HOST) for item in items),
            f"the installer no longer plans to bring {HOST}: {items}",
        )

    def test_verify_leaves_the_home_it_was_pointed_at_untouched(self):
        """Or the run above would be an installation, and this file would be
        the thing it is measuring."""
        before = self.whole_home()
        self.verify()
        self.assertEqual(self.whole_home(), before)

    def test_the_paragraph_names_everything_the_installer_brings(self):
        """The defect itself, in the only direction that matters to a reader:
        the paragraph tells them the one-liner already handled this, so it has
        to name what the one-liner handled. Each item is taken by its first
        word -- the component -- because the rest of the line is a pinned
        version this paragraph has no business repeating."""
        printed = self.verify()
        self.assertEqual(printed.returncode, 0, printed.stderr)
        for item in self.planned(printed.stdout):
            component = item.split()[0].rstrip(",")
            self.assertIn(
                component,
                self.paragraph,
                f"{MANUAL.name} does not say the installer brings {component}",
            )

    def test_the_paragraph_names_the_installer_and_points_at_the_guide(self):
        """A reader who wants the detail has to be able to get to it, and the
        detail lives in one section of one document. Both the file name and
        the link are derived, never typed twice."""
        self.assertIn(f"`{INSTALLER.name}`", self.paragraph)
        link = installer_section_link()
        self.assertTrue(link, f"{INSTALL_GUIDE.name} has no single first numbered section to link to")
        self.assertIn(link, self.paragraph)

    def test_the_paragraph_says_where_this_was_measured(self):
        """A claim without its measurement is the state this paragraph was
        already in. Both names come from this module, never from a literal
        typed twice."""
        self.assertIn(f"`{type(self).__name__}`", self.paragraph)
        self.assertIn(f"`{GUARD_MODULE}`", self.paragraph)


if __name__ == "__main__":  # pragma: no cover
    import unittest

    unittest.main()
