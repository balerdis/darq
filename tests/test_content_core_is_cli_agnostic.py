"""The content core renders into every CLI adapter identically -- so it must
name none of them.

`src/darq/content/` is the half of DARQ every adapter renders; a file in
there that says "OpenCode" is prose leaking a fact the architecture already
promises not to depend on. The forbidden names are derived from the adapter
registry itself (`darq.adapters.available()`), not hardcoded, so this guard
starts covering a future Claude Code adapter the moment it registers, with no
edit here.

## Why phrases, not words

An adapter contributes two names: `id` (e.g. `"opencode"`) and `display_name`
(e.g. `"OpenCode"`). Both are matched as whole phrases, case-insensitively, on
word boundaries -- never split into their individual words. This matters once
a "Claude Code" adapter exists: its `display_name` is two words. Matching each
word separately would flag every legitimate mention of the Claude *model*
("Claude Sonnet", "Ask Claude") or of Anthropic in this project's own prose,
none of which name the CLI. Matching "Claude Code" as one phrase avoids that:
content is free to say "Claude" or "Anthropic" on their own, and only trips
the guard when it names the CLI adapter specifically. The same reasoning is
why `id` and `display_name` are each matched as their own phrase rather than
tokenized and unioned.

Note also that `id="opencode"` and `display_name="OpenCode"` reduce to the
same token once case is folded -- matching both is deliberately redundant,
not a bug: nothing here assumes an adapter's `id` and `display_name` always
coincide that way, and a future adapter is free to have them differ.

## Why the whole file, not one line at a time

The gap between the two words of a phrase is matched as `_WORD_GAP`, and the
scan runs over the file as a single string rather than line by line. Both
halves of that are the same point: this project hand-wraps its prose, so a
two-word display name is one line break away from being invisible to a guard
that only ever sees one line at a time. A name split across a wrap is the
same leak as one written inline, and must read as one.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from darq.adapters import available

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "src" / "darq" / "content"

#: What may sit between the words of a multi-word CLI name and still count as
#: that name. See "Why the whole file, not one line at a time" above.
_WORD_GAP = r"\s+"

#: Paths (relative to `CONTENT`) where naming CLIs is the legitimate point of
#: the file, not a leak. Each entry says why. Exactly these three -- no
#: others -- so the allowlist itself cannot quietly grow into a place where
#: real leaks hide.
ALLOWED_TO_NAME_CLIS = {
    # Scans skill directories across roughly 16 agent CLIs; naming them is
    # the content of the reference, not an aside.
    "skills/sdd-init/references/init-details.md",
    # An issue form's client dropdown, plus a note on which CLIs a setup
    # script configures.
    "skills/issue-creation/SKILL.md",
    # A `.git/info/exclude` list of per-CLI artifact directories.
    "skills/project-agents-bootstrap/SKILL.md",
}


def _pattern_for(name: str) -> re.Pattern[str]:
    """One case-insensitive, word-boundary pattern for a single CLI name."""
    joined = _WORD_GAP.join(re.escape(word) for word in name.split())
    return re.compile(rf"\b{joined}\b", re.IGNORECASE)


def _forbidden_patterns() -> list[re.Pattern[str]]:
    """One pattern per adapter name, derived from the live registry rather
    than hardcoded -- see module docstring."""
    registry = available()
    names: set[str] = set()
    for cli_id in registry.ids():
        adapter = registry.get(cli_id)
        names.add(adapter.id)
        names.add(adapter.display_name)
    return [_pattern_for(name) for name in names if name.strip()]


def _offenses(text: str, patterns: list[re.Pattern[str]], label: str) -> list[str]:
    """Every place in `text` that names a CLI, as ``label:line: <line>``.

    Scanned as one string, not line by line, so a name broken across a wrap is
    still found; the line number is recovered from the match's offset. A line
    is reported once however many patterns hit it -- an adapter's `id` and
    `display_name` often reduce to the same token, and one leak is one leak.
    """
    lines = text.splitlines()
    found: dict[int, str] = {}
    for pattern in patterns:
        for match in pattern.finditer(text):
            lineno = text.count("\n", 0, match.start()) + 1
            if lineno not in found:
                found[lineno] = lines[lineno - 1].strip() if lineno <= len(lines) else ""
    return [f"{label}:{lineno}: {found[lineno]!r}" for lineno in sorted(found)]


class ContentCoreIsCliAgnosticTest(unittest.TestCase):
    def test_no_content_file_names_a_registered_cli(self):
        patterns = _forbidden_patterns()
        self.assertTrue(patterns, "no adapters registered -- nothing to guard against")

        offenses: list[str] = []
        for path in sorted(CONTENT.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(CONTENT).as_posix()
            if relative in ALLOWED_TO_NAME_CLIS:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            offenses.extend(_offenses(text, patterns, relative))

        self.assertFalse(
            offenses,
            "content core names a registered CLI (add to ALLOWED_TO_NAME_CLIS only if "
            "legitimate, otherwise reword):\n" + "\n".join(offenses),
        )

    def test_a_multi_word_cli_name_survives_a_line_break(self):
        """A two-word display name wrapped across two lines is the same leak.

        This is not hypothetical: the next adapter's `display_name` is "Claude
        Code", and this project wraps its prose by hand near 100 columns, so
        the wrap falls between two words often. A guard that reads one line at
        a time, or that demands a literal space, would pass a file that names
        the CLI outright.
        """
        pattern = _pattern_for("Claude Code")
        wrapped = "the brief goes to the Claude\nCode adapter, which renders it.\n"
        self.assertEqual(
            _offenses(wrapped, [pattern], "doc.md"),
            ["doc.md:1: 'the brief goes to the Claude'"],
        )

    def test_one_line_is_reported_once_however_many_patterns_hit_it(self):
        """`id` and `display_name` usually fold to the same token; a line that
        names a CLI once is one offense, not one per pattern."""
        patterns = [_pattern_for("opencode"), _pattern_for("OpenCode")]
        self.assertEqual(
            _offenses("nothing here\nsays OpenCode out loud\n", patterns, "doc.md"),
            ["doc.md:2: 'says OpenCode out loud'"],
        )

    def test_allowlist_entries_all_exist(self):
        """A stale allowlist entry (renamed or deleted file) would silently
        stop covering anything -- catch that instead of trusting the list."""
        missing = [entry for entry in ALLOWED_TO_NAME_CLIS if not (CONTENT / entry).is_file()]
        self.assertFalse(missing, f"allowlist entries with no matching file: {missing}")


if __name__ == "__main__":
    unittest.main()
