"""A rendered agent body must never point at a file its own adapter never writes.

The incident: a real install put Claude Code's agents on disk, and six of them
carry a lazy-load pointer at `{{skills_root}}/_shared/delegation-capabilities.md`
(see `content.delegation_capabilities_path` and the six agent bodies that read
it -- `king-pegasus`, `pegasus-general`, `pegasus-implementer`,
`pegasus-orchestrator`, `sdd-explore`, `sdd-verify`). OpenCode's `own_artifacts`
writes that file (`opencode.render.delegation_capabilities`); Claude Code's did
not. The instruction survives because it carries its own fallback ("if this
reference is missing or unreadable, do not assume the capability"), but the
whole capability-table feature was silently absent for that CLI, and nothing
caught it: `test_skill_references.py` checks the *source* content tree against
itself, never what a given adapter actually puts on disk, and `own_artifacts`
is deliberately per-adapter, so nothing forced parity between adapters.

This module makes that class of gap structurally impossible to ship again: for
every adapter this release registers, every skills-root path a rendered agent
body names must resolve to an artifact that very adapter emits. A third
adapter is covered the day it registers in `pegasus.adapters.available()`,
with nothing here to edit.

Home: not `test_skill_references.py` (that file is a static-source guard over
`content/skills/*.md` alone, and never renders anything through an adapter),
and not `test_delegation_capabilities.py` (that file is about one specific
generated artifact). This is its own module because the invariant it proves --
"an adapter's own rendered output is internally consistent" -- is a property
of the render pipeline as a whole, cutting across every adapter and every kind
of skills-root reference (a shared reference, a per-phase `SKILL.md`, an MCP
convention), not of any one artifact or any one adapter.
"""
from __future__ import annotations

import re
import unittest
from collections import defaultdict
from pathlib import Path

from pegasus import cli
from pegasus.adapters import available
from pegasus.core import catalog as catalog_module
from pegasus.core import content as content_module
from pegasus.core.types import Environment, FileArtifact

HOME = Path("/home/probe")
ENVIRONMENT = Environment(home=HOME, data_dir=HOME / ".local" / "share" / "pegasus-harness")
IDENTITY = cli.default_identity()

#: An artifact carrying an agent's own prose is identified by its id, not by a
#: hardcoded adapter name: `claudecode.render.agent` embeds the body directly
#: into one file (`id=f"agent:{name}"`), while `opencode.render.agent`/
#: `.prompt` split definition and prose into two files, the prose keyed
#: `id=f"prompt:{name}"`. Both prefixes already exist in the two shipped
#: adapters -- a third adapter renders its agent prose under one of these two
#: established shapes, per the same `CliAdapter` port every adapter implements,
#: so no adapter id is named here.
AGENT_BODY_ID_PREFIXES = ("agent:", "prompt:")

#: Matches a skills-root reference once the `{{skills_root}}` placeholder has
#: already been substituted with this layout's real, absolute directory --
#: i.e. against RENDERED output, never against the content source's own
#: `{{skills_root}}/...` literal. Captures the path relative to the skills
#: root, the same shape `layout.skills_dir / <captured>` would reconstruct.
def _reference_pattern(skills_root: Path) -> re.Pattern[str]:
    return re.compile(re.escape(str(skills_root)) + r"/([\w./-]+\.md)")


def _emitted_relative_paths(file_artifacts, skills_root: Path) -> set[str]:
    return {
        str(artifact.path.relative_to(skills_root))
        for artifact in file_artifacts
        if artifact.path.is_relative_to(skills_root)
    }


def _dangling_references_by_adapter() -> dict[str, list[str]]:
    """Render the real shipped content through every registered adapter and
    report, per adapter, every skills-root reference an agent body makes that
    does not resolve to a path that same adapter's own render actually wrote.

    `catalog_module.render` (not `catalog_module.build`) is used because it
    hands back the real `Artifact` objects -- `FileArtifact.path` already
    resolved against a real `Environment` -- rather than `build`'s portable,
    address-only `Catalog.entries`; the reference check needs to read each
    agent body's actual bytes, which only `render`'s artifacts carry.

    Content is loaded once, unpruned (`content_module.load()`, no
    `select_mcp`): every shipped MCP server's convention file is written
    unconditionally in that shape (see `core.catalog.render`'s `SOURCES` loop
    over `content.mcp`), which is exactly what proves an agent's own
    convention pointer resolves -- a pruned selection would make some of
    those references vanish along with the servers instead of being checked.
    """
    content = content_module.load()
    registry = available()
    findings: dict[str, list[str]] = defaultdict(list)

    for cli_id in registry.ids():
        adapter = registry.get(cli_id)
        layout = adapter.layout(ENVIRONMENT)
        if layout.skills_dir is None:
            continue  # nothing to resolve against; this adapter ships no skills tree

        artifacts = catalog_module.render(content, adapter, ENVIRONMENT, IDENTITY)
        file_artifacts = [item for item in artifacts if isinstance(item, FileArtifact)]
        emitted = _emitted_relative_paths(file_artifacts, layout.skills_dir)
        pattern = _reference_pattern(layout.skills_dir)

        for artifact in file_artifacts:
            if not artifact.id.startswith(AGENT_BODY_ID_PREFIXES):
                continue
            text = artifact.content.decode("utf-8", errors="ignore")
            for reference in sorted(set(pattern.findall(text))):
                if reference not in emitted:
                    findings[cli_id].append(f"{artifact.id} -> {{{{skills_root}}}}/{reference}")

    return dict(findings)


class EveryAdapterIsScannedTest(unittest.TestCase):
    def test_at_least_two_adapters_are_registered(self):
        """Without this, the guard below could pass by scanning nothing."""
        self.assertGreaterEqual(len(available().ids()), 2)


class NoDanglingSkillsRootReferenceTest(unittest.TestCase):
    def test_every_agent_body_reference_resolves_to_an_artifact_its_own_adapter_emits(self):
        findings = _dangling_references_by_adapter()
        if not findings:
            return
        report = "\n".join(
            f"{cli_id}:\n" + "\n".join(f"  {line}" for line in sorted(lines))
            for cli_id, lines in sorted(findings.items())
        )
        self.fail(
            "dangling skills-root reference(s) -- a rendered agent body points at a "
            "file its own adapter never writes:\n" + report
        )


if __name__ == "__main__":
    unittest.main()
