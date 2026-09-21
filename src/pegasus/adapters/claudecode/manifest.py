"""What this adapter delivers for Claude Code.

The manifest is not Claude Code's feature list: it is the list of capabilities
this adapter actually implements today. The registry refuses to register an
adapter that claims more than it implements, so a capability stays False until
its render and the content it needs both exist.
"""
from __future__ import annotations

from pegasus.core.types import CapabilityManifest

CLI_ID = "claudecode"
DISPLAY_NAME = "Claude Code"

MANIFEST = CapabilityManifest(
    cli_id=CLI_ID,
    skills=True,
    system_prompt=True,
    slash_commands=True,
    sub_agents=True,
    # Claude Code puts an agent's prompt in the body of the agent's own .md
    # file: one artifact, not two. So no `prompts_dir` in the layout and no
    # `render_prompt` method -- the registry rejects both if this capability
    # is not declared.
    prompts=False,
    # Claude Code has no documented location inside ~/.claude/ for a
    # session-wide MCP server definition: user scope lives in ~/.claude.json,
    # a SIBLING of that directory, and core.catalog._entries() hard-fails on
    # any artifact outside layout.config_dir. The in-tree alternative --
    # `mcpServers:` inside each agent's own frontmatter -- would need
    # `render_agent` to receive `Mcp` descriptors it is never handed, or
    # would stash them between `render_mcp` and `render_agent` calls, which
    # would give this adapter per-machine state the port forbids. This is an
    # open architectural decision the user is deciding separately; declare
    # `mcp=False` and let the registry enforce it until it is resolved.
    mcp=False,
    # Claude Code resolves models live or from env vars -- "no local cached
    # models.json file" (code.claude.com/docs/en/model-config.md) -- and its
    # `model:` field takes aliases (sonnet, opus, haiku, fable, inherit) or
    # full ids, while `ModelAssignment` is provider/model shaped. There is no
    # honest on-disk source to read a catalog from, so no `model_catalog`
    # method.
    per_agent_model=False,
)
