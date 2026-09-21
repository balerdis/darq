"""How Claude Code spells what the content core means.

Every table in this module is a translation from an agnostic concept to a
Claude Code name. This is the only place those names are allowed to appear.
"""
from __future__ import annotations

import json
from typing import Any

from pegasus.core import placeholders
from pegasus.core.content import Agent, Command, Skill, SystemPrompt
from pegasus.core.identity import Identity
from pegasus.core.types import Artifact, FileArtifact, Layout, ModelAssignment

#: Claude Code's exact, case-sensitive tool names. This is the entire native
#: tool vocabulary in shipped content: the union of `requires_tools` and
#: `optional_tools` across every agent this repository ships (verified by
#: reading all sixteen). A name outside this table is not "close enough" --
#: Claude Code matches tool names literally -- so `_tools_field` raises
#: rather than let an unmapped name pass through unnoticed.
TOOL_NAME: dict[str, str] = {
    "read": "Read",
    "write": "Write",
    "edit": "Edit",
    "bash": "Bash",
    "grep": "Grep",
    "glob": "Glob",
    "ask": "AskUserQuestion",
    "skill": "Skill",
}


class RenderError(ValueError):
    """The content asks for something this CLI has no name for."""


def skill(layout: Layout, item: Skill) -> list[Artifact]:
    """Skills travel verbatim: Claude Code reads the same SKILL.md format."""
    return [
        FileArtifact(
            id=f"skill:{item.name}:{asset.relative_path}",
            path=layout.skills_dir / item.name / asset.relative_path,
            content=asset.content,
            executable=False,
        )
        for asset in item.assets
    ]


def agent(layout: Layout, item: Agent, assignment: ModelAssignment | None = None) -> list[Artifact]:
    """One file per agent, `agents_dir / <name>.md`, frontmatter over the body.

    Every agent renders here the same way regardless of `item.mode`: Claude
    Code has one session identity, not a `primary`/`subagent` split at the
    file level. `content.py` keeps declaring `mode: primary` for the two
    agents that carry it because that is the fact about them; how that fact
    is spelled for one particular CLI is this adapter's job, never the
    content core's. For Claude Code the answer lives in `adapter.own_
    artifacts`, not here: the session-starting agent
    (`content.SESSION_STARTS_IN`) becomes the CLI's single session identity
    through `settings.json`'s `agent` key, and any other `primary` agent (the
    content core ships exactly one: `king-pegasus`) is demoted to an ordinary
    delegation target with no special file shape of its own -- it renders
    through this same function, indistinguishable on disk from a subagent.
    That demotion happens in the adapter, never in the content core, because
    it is a fact about how *this* CLI expresses "the session runs as", not
    about what `king-pegasus` *is*.

    `assignment`, when given, names a model at the one field Claude Code's
    schema has for it. `assignment.model_id` is written, not `assignment.
    full_id`: Claude Code's `model:` field takes a bare alias (`sonnet`,
    `opus`, `haiku`, `fable`, `inherit`) or a bare model id, never a
    provider-qualified one -- `ModelAssignment` carries `provider_id`
    separately because a *machine's* resolved preference needs it (to tell
    two providers' same-named models apart), but that provider qualifier has
    nowhere to land in this CLI's own vocabulary. Dead code today:
    `per_agent_model=False` means the engine always calls this with `None`,
    so `assignment` is kept, per the port's signature, and handled without
    inventing a default for the day this capability might exist.
    """
    fields: dict[str, Any] = {"name": item.name, "description": item.description}
    fields["tools"] = _tools_field(item)
    if assignment is not None:
        fields["model"] = assignment.model_id
    return [
        FileArtifact(
            id=f"agent:{item.name}",
            path=layout.agents_dir / f"{item.name}.md",
            content=(_frontmatter(fields) + "\n" + _agent_body(layout, item)).encode("utf-8"),
            executable=False,
        )
    ]


def _tools_field(item: Agent) -> str:
    """A comma-separated tool list, plus an `Agent(...)` entry for delegation.

    `Agent(name-a, name-b)` is Claude Code's purpose-built construct for
    restricting which subagent types may be spawned -- it lives inside this
    same `tools` list, not in a field of its own. An agent whose `may_
    delegate_to` is empty gets no `Agent(...)` entry at all: that omission is
    how "may delegate to nobody" is spelled, not a special case to guard.
    """
    names = (*item.requires_tools, *item.optional_tools)
    unknown = [name for name in names if name not in TOOL_NAME]
    if unknown:
        raise RenderError(f"{item.name}: no Claude Code name for tools {', '.join(sorted(unknown))}")
    entries = sorted({TOOL_NAME[name] for name in names})
    if item.may_delegate_to:
        entries.append(f"Agent({', '.join(item.may_delegate_to)})")
    return ", ".join(entries)


def command(layout: Layout, item: Command, orchestrator_name: str) -> list[Artifact]:
    """A markdown file, Claude Code's own command frontmatter over the body.

    `orchestrator_name` is accepted because the port's signature requires
    every adapter to take it, not because this function has anywhere to put
    it. Claude Code's command frontmatter (`description`, `argument-hint`,
    `allowed-tools`, `model`, `disable-model-invocation`, `user-invocable`)
    has no `agent:` field -- unlike OpenCode, which spells `RunsAs.
    ORCHESTRATOR` by naming an agent there. There is nothing honest to write
    for it here: this function renders the same frontmatter for every
    `RunsAs` member, and `orchestrator_name` never appears in the output.
    """
    fields: dict[str, Any] = {"description": item.description}
    return [
        FileArtifact(
            id=f"command:{item.name}",
            path=layout.commands_dir / f"{item.name}.md",
            content=(_frontmatter(fields) + "\n" + _body(layout, item.body, item.name)).encode("utf-8"),
            executable=False,
        )
    ]


def system_prompt(layout: Layout, item: SystemPrompt, identity: Identity) -> list[Artifact]:
    """One file, `rules/<program_name>.md`, and nothing else to wire in.

    `~/.claude/rules/*.md` is a first-class, auto-loaded location -- Claude
    Code documents it in the same "what loads at startup" bullet as CLAUDE.md,
    reaching the main session AND every sub-agent (only the built-in Explore
    and Plan agents skip it). That means this one file, shipped once, reaches
    all sixteen agents with no per-agent duplication and no settings key
    pointing at it -- unlike OpenCode's own `system_prompt`, which has to
    append an entry to an `instructions` list for the runtime to notice the
    file at all. There is deliberately no `ConfigKeyArtifact` here.

    The filename comes from `identity`, not from `layout.system_prompt_file`:
    `layout` is built with no `Identity` in reach (see `adapter.layout`,
    called from many places that never carry one), so its own anchor stays
    the fixed, identity-unaware default -- correct only for the packaged
    distribution, and never consulted for what this function actually writes.

    This adapter never writes into the user's own `~/.claude/CLAUDE.md`; that
    file is theirs.
    """
    path = layout.config_dir / "rules" / f"{identity.program_name}.md"
    return [
        FileArtifact(
            id=f"system-prompt:{path.name}",
            path=path,
            content=_system_prompt_body(layout, item).encode("utf-8"),
            executable=False,
        )
    ]


def _system_prompt_body(layout: Layout, item: SystemPrompt) -> str:
    """The base prompt, then one section per server the user chose."""
    return _with_mcp_sections(layout, item.body, item.mcp_sections, "system-prompt")


def _agent_body(layout: Layout, item: Agent) -> str:
    """The agent's own prose, then one section per server it was granted.

    Composed exactly the way `_system_prompt_body` composes the base prompt.
    In practice `item.mcp_sections` is always empty for this adapter today --
    `mcp=False` means nothing is ever selected for it to carry -- but the
    composition is written generically because `Agent` is the same dataclass
    every adapter renders from, and a future `mcp=True` here must not require
    rewriting this function.
    """
    return _with_mcp_sections(layout, item.body, item.mcp_sections, item.name)


def _with_mcp_sections(layout: Layout, body: str, sections: tuple[Any, ...], owner: str) -> str:
    parts = [_body(layout, body, owner)]
    parts += [_body(layout, section.body, str(section.source)) for section in sections]
    return "\n\n".join(part.strip("\n") for part in parts) + "\n"


def _body(layout: Layout, body: str, owner: str) -> str:
    """Answer the placeholders a body left for its installer.

    A body names facts, not paths, so that one text installs under every CLI.
    This is where those facts become this layout's directories.
    """
    try:
        return placeholders.fill(body, facts(layout))
    except placeholders.Unanswered as missing:
        raise RenderError(
            f"{owner}: this layout has no {missing.name}, so the body cannot be filled"
        ) from None


def facts(layout: Layout) -> dict[str, str]:
    """What this layout can answer. An absent anchor answers nothing, never a blank."""
    result: dict[str, str] = {}
    if layout.skills_dir is not None:
        result["skills_root"] = str(layout.skills_dir)
    return result


def _frontmatter(fields: dict[str, Any]) -> str:
    lines = ["---"]
    lines += [f"{key}: {_scalar(value)}" for key, value in fields.items()]
    lines.append("---")
    return "\n".join(lines) + "\n"


def _scalar(value: Any) -> str:
    """JSON is a subset of YAML, so this quotes exactly when quoting is needed."""
    if isinstance(value, bool):
        return "true" if value else "false"
    return json.dumps(value, ensure_ascii=False)
