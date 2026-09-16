"""`pegasus directory grant` on a path the deny floor shadows reports success
and is a permanent no-op.

`EXTERNAL_DIRECTORY_DENY_FLOOR` (`render.py`) is written last into every
agent's rendered `external_directory` map, so the runtime's last-match
resolution always lands on it for the five directory names it names. A
person can still run `pegasus directory grant --cli opencode /home/me/.ssh`:
`content.validate_granted_directory` accepts it (it names no glob
metacharacter, is absolute, is not the filesystem root, the CLI's own
configuration directory, or Pegasus's own data directory), and it is written
and reported as granted -- but it can never take effect, because the floor
always wins the match regardless of where a grant was written.

`render.deny_floor_shadows` is the predicate that answers this ahead of time,
so `pegasus directory grant` can warn instead of silently doing nothing. It
must match the runtime's own semantics -- `packages/core/src/util/wildcard.ts`
-- not a path-component proxy (`".ssh" in Path(p).parts`), which would flag a
directory merely named `sshfoo` or miss the pattern's real shape.
"""
from __future__ import annotations

import unittest

from pegasus.adapters.opencode import render as render_module


class DenyFloorShadowsCanonicalNamesTest(unittest.TestCase):
    """A grant naming one of the floor's five directories, anywhere in the
    path, must be reported as shadowed -- this is the case the bug missed."""

    def test_ssh_at_top_level(self):
        self.assertTrue(render_module.deny_floor_shadows("/home/me/.ssh"))

    def test_ssh_nested(self):
        self.assertTrue(render_module.deny_floor_shadows("/home/me/projects/x/.ssh"))

    def test_aws(self):
        self.assertTrue(render_module.deny_floor_shadows("/home/me/.aws"))

    def test_credentials(self):
        self.assertTrue(render_module.deny_floor_shadows("/home/me/.credentials"))

    def test_secrets(self):
        self.assertTrue(render_module.deny_floor_shadows("/srv/app/secrets"))

    def test_config_gh(self):
        self.assertTrue(render_module.deny_floor_shadows("/home/me/.config/gh"))

    def test_a_directory_inside_a_shadowed_directory_is_also_shadowed(self):
        """The floor's own pattern (`*/.ssh/*`) matches anything beneath the
        named directory too, not only the directory itself."""
        self.assertTrue(render_module.deny_floor_shadows("/home/me/.ssh/keys"))


class DenyFloorDoesNotShadowLookalikesTest(unittest.TestCase):
    """A proxy check (substring, or path-component-name check done wrong)
    would flag these. The real match must not."""

    def test_directory_merely_named_sshfoo(self):
        self.assertFalse(render_module.deny_floor_shadows("/home/me/sshfoo"))

    def test_ssh_as_a_trailing_filename_fragment_not_a_directory_component(self):
        self.assertFalse(render_module.deny_floor_shadows("/home/me/config.ssh"))

    def test_secrets_as_a_prefix_of_a_longer_name(self):
        self.assertFalse(render_module.deny_floor_shadows("/srv/app/secretsvault"))

    def test_an_unrelated_directory(self):
        self.assertFalse(render_module.deny_floor_shadows("/home/me/worktrees/otro-repo"))

    def test_gh_config_without_the_dot_config_parent(self):
        """`*/.config/gh/*` requires the literal `.config/gh` path segment
        sequence -- a directory just named `gh` elsewhere must not match."""
        self.assertFalse(render_module.deny_floor_shadows("/home/me/tools/gh"))


class DenyFloorShadowMatchesTheRuntimeWildcardSemanticsTest(unittest.TestCase):
    """`_wildcard_match` is a direct port of the runtime's own
    `Wildcard.match`: escape regex metacharacters, `*` -> `.*`, `?` -> `.`,
    anchor both ends. This pins that port against the floor's own patterns
    rather than against the public predicate alone, so a regression in the
    port itself (not just in `deny_floor_shadows`'s wiring) is caught here."""

    def test_star_crosses_slash(self):
        self.assertTrue(render_module._wildcard_match("/a/b/.ssh/c/d/*", "*/.ssh/*"))

    def test_anchored_at_both_ends(self):
        """A pattern with no wildcard at all must match the whole candidate,
        not merely appear as a substring of it -- `re.search` would wrongly
        pass this, `re.fullmatch` (what the runtime's own `^...$` anchoring
        means) correctly does not."""
        self.assertTrue(render_module._wildcard_match("abc", "abc"))
        self.assertFalse(render_module._wildcard_match("xabcx", "abc"))

    def test_literal_dot_is_escaped_not_a_wildcard(self):
        """If `.` in the pattern were left as a regex metacharacter instead of
        being escaped, `X.ssh` would wrongly match `*/.ssh/*`'s translated
        form for the wrong reason -- this pins that it is escaped."""
        self.assertFalse(render_module._wildcard_match("/a/Xsshb/*", "*/.ssh/*"))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
