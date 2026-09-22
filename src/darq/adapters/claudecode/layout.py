"""Where Claude Code keeps each kind of artifact.

Pure path arithmetic. The registry builds this against a home directory that
does not exist, so touching the filesystem here would make registration
depend on the state of the machine.
"""
from __future__ import annotations

from pathlib import Path

from darq.core.types import Environment, Layout

SETTINGS = "settings.json"

#: The layout's own fixed anchor for the system prompt file. This can only be
#: a fixed name, never the identity-derived one `render.system_prompt`
#: actually writes: `layout()` is called from many places that carry no
#: `Identity` at all (see `adapter.layout`'s own callers), so there is no way
#: to smuggle a distribution's real `program_name` in here. Mirrors exactly
#: how OpenCode's own `SYSTEM_PROMPT` constant works, for the same reason.
SYSTEM_PROMPT = "pegasus.md"


def config_dir(environment: Environment) -> Path:
    """Claude Code's configuration root.

    Honours `CLAUDE_CONFIG_DIR` when it is set to an absolute path. Claude
    Code does NOT honour `XDG_CONFIG_HOME` -- verified against Claude Code's
    own documentation -- so, unlike OpenCode's `config_dir`, this function
    never looks at it.
    """
    configured = environment.variables.get("CLAUDE_CONFIG_DIR", "").strip()
    if configured and Path(configured).is_absolute():
        return Path(configured)
    return environment.home / ".claude"


def build(environment: Environment) -> Layout:
    root = config_dir(environment)
    return Layout(
        config_dir=root,
        settings_file=root / SETTINGS,
        skills_dir=root / "skills",
        # A real anchor, unlike OpenCode: Claude Code reads each subagent
        # from its own file under this directory rather than from a key
        # inside the settings file.
        agents_dir=root / "agents",
        commands_dir=root / "commands",
        # `prompts=False`: Claude Code keeps an agent's prompt in the body of
        # its own file, so there is no second artifact and no directory for it.
        prompts_dir=None,
        plugins_dir=None,
        system_prompt_file=root / "rules" / SYSTEM_PROMPT,
        # Pegasus's own directory, not Claude Code's -- `None` when this frame
        # has no answer for it, the same as every other environment-derived
        # fact. Where a `download`- or `npm`-distributed server's fetched
        # tree lands; `render.py`'s `_download_command`/`_npm_command` point
        # a granted agent's inline `mcpServers:` entry at a path inside it.
        dependencies_dir=(environment.data_dir / "mcp") if environment.data_dir is not None else None,
    )
