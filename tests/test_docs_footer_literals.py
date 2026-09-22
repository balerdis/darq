"""`docs/arquitectura/arquitectura.md` quotes two TUI screen footers verbatim,
inside fenced code blocks meant to show what a person actually sees. Nothing
checked that those quotes still match `src/darq/tui/view.py` once the real
footer changed -- a stale description of the models screen's own footer was
found by hand, not by a failing test (see the models screen's own history).

This derives both footer literals from `view.py`'s own AST -- never a second
hand-typed copy of them -- and asserts the doc's quote is exactly, not
approximately, the same string. That is what makes this bidirectional: if
`view.py`'s literal changes, the derived expectation changes with it and the
old quote in the doc stops matching; if the doc's quote is typed wrong, or
changed to something else, it stops matching the real literal. A guard that
only checked "does 'esc:' appear somewhere nearby" would pass on either kind
of drift; this compares the whole string.

Only two footers are checked because only two are actually quoted in the
doc -- `view.py` has others (`enter/esc: back`, the two MCP/directory
selection footers, the provider/model/effort footers), but the doc never
quotes them verbatim, so there is nothing here for a guard to hold them
against without inventing a claim the doc itself does not make.

Reads `view.py`'s source text and parses it with `ast` -- no subprocess, no
execution of the module's own rendering.
"""
from __future__ import annotations

import ast
import unittest
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
VIEW = REPOSITORY / "src" / "darq" / "tui" / "view.py"
ARQUITECTURA = REPOSITORY / "docs" / "arquitectura" / "arquitectura.md"


def _function(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{name!r} was not found in {VIEW}")


def _footer_constant(function: ast.FunctionDef, *, containing: str) -> str:
    """The one string constant inside `function` that names both `enter`
    and `esc:` and contains `containing` -- the shape every footer in this
    file has, whether it is a plain literal or (for the install-plan screen)
    the constant parts of an f-string. `_render_models` alone draws four
    different footers, one per step of its wizard, so `containing` is what
    picks the one this test is actually about; every other caller in this
    module names a function with only one footer to begin with, where it
    does no narrowing at all. Raises if the result is not exactly one, so
    this guard fails loudly on a shape it was not written against instead of
    silently picking the wrong string.
    """
    candidates = []
    for node in ast.walk(function):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if "enter" in node.value and "esc:" in node.value:
                candidates.append(node.value)
        if isinstance(node, ast.JoinedStr):
            # `{}` stands in for each interpolated hole (`{screen.command}`,
            # say) -- keeping its position matters for
            # `InstallPlanScreenFooterTest`, which fills that hole back in
            # rather than only checking the surrounding text is present.
            text = "".join(
                part.value if isinstance(part, ast.Constant) and isinstance(part.value, str) else "{}"
                for part in node.values
            )
            if "enter" in text and "esc:" in text:
                candidates.append(text)
    candidates = [text for text in candidates if containing in text]
    assert len(candidates) == 1, f"expected exactly one footer literal in {function.name}, found {candidates!r}"
    return candidates[0]


class ModelsScreenFooterTest(unittest.TestCase):
    """`_render_models`'s footer is a plain string literal -- no f-string
    interpolation -- so the constant extracted from its AST is exactly what
    a person sees, and exactly what the doc must quote."""

    @classmethod
    def setUpClass(cls):
        tree = ast.parse(VIEW.read_text(encoding="utf-8"), filename=str(VIEW))
        cls.footer = _footer_constant(_function(tree, "_render_models"), containing="discards staged changes")
        cls.arquitectura = ARQUITECTURA.read_text(encoding="utf-8")

    def test_the_footer_is_derived_and_shaped_as_expected(self):
        # Pinned so a change to this literal is a deliberate edit to this
        # test too, not a silent pass on whatever `view.py` happens to say.
        self.assertIn("enter: configure, or confirm to apply", self.footer)
        self.assertIn("esc: back, discards staged changes", self.footer)

    def test_the_document_quotes_the_real_footer_verbatim(self):
        self.assertIn(self.footer, self.arquitectura)


class InstallPlanScreenFooterTest(unittest.TestCase):
    """`_render_install_plan`'s footer is an f-string parametrized by
    `screen.command`; the doc quotes only the `install` instantiation, so
    this reconstructs that one instantiation from the f-string's own
    constant parts rather than the whole template.
    """

    @classmethod
    def setUpClass(cls):
        tree = ast.parse(VIEW.read_text(encoding="utf-8"), filename=str(VIEW))
        cls.footer_template = _footer_constant(_function(tree, "_render_install_plan"), containing="nothing written")
        cls.arquitectura = ARQUITECTURA.read_text(encoding="utf-8")

    def test_the_template_has_exactly_one_hole_for_the_command(self):
        # A single `{}` from `.format`, not a second hand-typed template --
        # `_footer_constant` already joined the f-string's literal parts
        # across the interpolation, so a lone `{}` is what a one-hole
        # template looks like once joined this way.
        self.assertEqual(self.footer_template.count("{}"), 1)

    def test_the_document_quotes_the_install_instantiation_verbatim(self):
        expected = self.footer_template.format("install")
        self.assertIn(expected, self.arquitectura)
