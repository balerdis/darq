"""The Claude Code adapter.

Implements exactly the capabilities its manifest declares, and nothing else: a
render method for an undeclared capability is a phantom capability and the
registry rejects it.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from pegasus.adapters.claudecode import layout as layout_module
from pegasus.adapters.claudecode import manifest as manifest_module
from pegasus.adapters.claudecode import render
from pegasus.core.content import Agent, Command, Mcp, Skill, SystemPrompt
from pegasus.core.identity import Identity
from pegasus.core.types import (
    Artifact,
    CapabilityManifest,
    ConfigKeyArtifact,
    Detection,
    Environment,
    Layout,
    ModelAssignment,
    SupportTier,
)

BINARY = "claude"


class Adapter:
    """Everything Pegasus needs to know about Claude Code."""

    id = manifest_module.CLI_ID
    display_name = manifest_module.DISPLAY_NAME

    def tier(self) -> SupportTier:
        return SupportTier.PARTIAL

    def capabilities(self) -> CapabilityManifest:
        return manifest_module.MANIFEST

    def activation_steps(self) -> tuple[str, ...]:
        """Tell the user to restart, because the alternative is a claim we
        cannot back up either way.

        `settings.json` and skills are documented as hot-reloaded, but
        whether an already-running session picks up a newly written agent or
        command file is not documented, and could not be measured: a probe
        using `claude -p --continue` starts a fresh process each time, which
        proves nothing about a live one. Telling the user to restart is true
        whichever way that turns out to be -- an empty tuple here would claim
        a certainty this adapter does not have.
        """
        return (
            "Restart your Claude Code session. Whether an already-running "
            "session picks up a newly written agent or slash command file "
            "is not documented, so restarting is the only way to be sure "
            "the change has taken effect.",
        )

    # --- Detection: PATH and the filesystem only, never execution ---

    def detect(self, environment: Environment) -> Detection:
        binary = shutil.which(BINARY, path=environment.variables.get("PATH"))
        config = layout_module.config_dir(environment)
        return Detection(
            installed=binary is not None,
            binary_path=Path(binary) if binary else None,
            config_dir=config,
            config_found=config.is_dir(),
        )

    # --- Where ---

    def layout(self, environment: Environment) -> Layout:
        return layout_module.build(environment)

    # --- How ---

    def render_skill(self, layout: Layout, skill: Skill) -> list[Artifact]:
        return render.skill(layout, skill)

    def render_agent(
        self,
        layout: Layout,
        agent: Agent,
        assignment: ModelAssignment | None = None,
        *,
        mcp: tuple[Mcp, ...],
    ) -> list[Artifact]:
        return render.agent(layout, agent, assignment, mcp)

    def render_mcp(self, layout: Layout, mcp: Mcp) -> list[Artifact]:
        return render.mcp(layout, mcp)

    def writes_mcp_config_key(self) -> bool:
        """Never: see `render.mcp`'s own docstring. Claude Code keeps a
        server's definition inside each granted agent's own `mcpServers:`
        frontmatter, not in one global settings key, so this adapter never
        writes a `/mcp/<id>` pointer for any server -- bound or not."""
        return False

    def render_command(self, layout: Layout, command: Command, orchestrator_name: str) -> list[Artifact]:
        return render.command(layout, command, orchestrator_name)

    def render_system_prompt(
        self, layout: Layout, system_prompt: SystemPrompt, identity: Identity
    ) -> list[Artifact]:
        return render.system_prompt(layout, system_prompt, identity)

    # --- What this adapter ships on its own ---

    def own_artifacts(
        self,
        layout: Layout,
        orchestrator_name: str,
        identity: Identity,
        delegation_targets: tuple[Any, ...],
    ) -> list[Artifact]:
        """One artifact: the `agent` key in `settings.json`.

        Pegasus's orchestrator is an ordinary `mode: primary` agent in the
        content core; Claude Code's main session is not a file at all. This
        one key is the whole bridge between the two: `settings.json`'s
        top-level `agent` field is documented as "start every session as a
        named subagent with its prompt, tools, and model" -- so the
        orchestrator renders as an ordinary agent file, exactly like every
        other agent (see `render.agent`'s own docstring for why no special
        file shape exists for `mode: primary`), and this single key is what
        makes a fresh session adopt it, carrying its prompt, tools and model
        along with it.

        `orchestrator_name` is the same content-declared name `render_
        command` receives for `RunsAs.ORCHESTRATOR` (see `Content.
        SESSION_STARTS_IN`) -- never a literal this adapter invents -- which
        is exactly why it is written here as a value, not baked in as a key.

        `identity` is unused: this adapter ships no bundled asset that needs
        to name the running distribution, unlike OpenCode's plugins. It is
        still accepted, because the port's signature requires every adapter
        to take it.

        `delegation_targets`, unlike `identity`, IS used: it is what
        `render.delegation_capabilities` turns into the generated reference
        every delegating agent's body already points at
        (`{{skills_root}}/_shared/delegation-capabilities.md`, six agent
        bodies -- see `content.delegation_capabilities_path`). Before this,
        this adapter accepted the parameter but never wrote the file it
        describes, leaving that pointer dangling in every real Claude Code
        install: the instruction survives on its own stated fallback ("if
        this reference is missing or unreadable, do not assume the
        capability"), but the whole capability-table feature was silently
        absent for this CLI. See `render.delegation_capabilities`'s own
        docstring for why its table is not a copy of OpenCode's -- it must
        speak this CLI's own tool and MCP-denial vocabulary, not the other
        adapter's, or it would lie about what a target can actually run.
        """
        return [
            ConfigKeyArtifact(
                id="own:orchestrator-agent",
                path=layout.settings_file,
                pointer="/agent",
                value=orchestrator_name,
            ),
            *render.delegation_capabilities(layout, delegation_targets),
        ]
