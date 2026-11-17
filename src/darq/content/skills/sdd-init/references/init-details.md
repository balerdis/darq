# Detection and Payload Details for sdd-init

What the sdd-init skill leaves to this file. First the core of the phase: where testing capabilities show up
and how they are recorded, the openspec bootstrap and the Engram saves, and what the reply has to cover.
Then the skills: what makes a skill LLM-first, and how the skill registry is put together.

## Finding testing capabilities

- The runner: the scripts and dependencies in `package.json`; then `pyproject.toml`, `pytest.ini`, `go.mod`
  and `Cargo.toml`; and the `Makefile`.
- The layers: the runner itself reveals unit tests. Integration shows through libraries like
  `testing-library`, `httpx`, `httptest` or `WebApplicationFactory`, and E2E through tools like `playwright`,
  `cypress`, `selenium` or `chromedp`.
- Coverage, through any of: `vitest --coverage`, `jest --coverage`, `c8`, `pytest-cov`, `go test -cover`, `coverlet`.
- Code quality: the commands behind the linter, the type checker and the formatter.

## Shape of the testing capabilities

```markdown
## Testing Capabilities

**Strict TDD Mode**: {enabled/disabled}
**Detected**: {the date of this detection}

### Test Runner

- Command: `{the command that runs the tests}`
- Framework: {framework name}

### Test Layers

| Layer       | Available | Tool        |
| ----------- | --------- | ----------- |
| Unit        | ✅ / ❌   | {the tool, or — when there is none} |
| Integration | ✅ / ❌   | {the tool, or — when there is none} |
| E2E         | ✅ / ❌   | {the tool, or — when there is none} |

### Coverage

- Available: ✅ / ❌
- Command: `{the coverage command, or —}`

### Quality Tools

| Tool         | Available | Command        |
| ------------ | --------- | -------------- |
| Linter       | ✅ / ❌   | {its command, or — when there is none} |
| Type checker | ✅ / ❌   | {its command, or — when there is none} |
| Formatter    | ✅ / ❌   | {its command, or — when there is none} |
```

## OpenSpec bootstrap

```text
openspec/
├── config.yaml
├── specs/
└── changes/
    └── archive/
```

`config.yaml` should include concise context, `strict_tdd`, the testing capabilities, and a set of rules for
each phase: proposal, spec, design, tasks, apply, verify and archive. Its `context:` is kept below 10 lines.

## The three Engram saves

```text
mem_save title/topic_key: sdd-init/{project}
type: architecture
content: the project context that was detected, as markdown
capture_prompt: false, if the tool accepts it

mem_save title/topic_key: sdd/{project}/testing-capabilities
type: config
content: the testing capabilities, as markdown
capture_prompt: false, if the tool accepts it

mem_save title/topic_key: skill-registry
type: config
content: the registry, as markdown
capture_prompt: false, if the tool accepts it
```

## What the reply covers

Whatever the mode, the reply names the project and its stack, the persistence in use, Strict TDD Mode, the
Testing Capabilities table, the artifacts created or saved, any limitations that apply, and the next steps.
In engram mode it has to point out that this memory is local and cannot be shared; in none mode it has to
recommend turning persistence on.

## What makes a skill LLM-first

A skill is a contract of instructions the model runs on, not documentation for human readers. One that
qualifies has:

- this structure: frontmatter, Activation Contract, Hard Rules, Decision Gates, Execution Steps, Output
  Contract, References;
- a `description` that is quoted, fits on a single physical line, leads with its trigger, and stays within
  250 characters;
- a body aimed at 180-450 tokens, with examples, schemas, edge cases and background moved out to local
  `references/` or `assets/`;
- references to local files, stable relative to the skill's own directory wherever that can be done;
- quality gates it passes: every hard rule can be observed, the decision gates cover forks that really
  occur, the output contract says exactly what is returned, and each reference resolves locally.

## Building the skill registry

Skills are looked for in two sets of directories.

- User level: `~/.pi/agent/skills/`, `~/.config/agents/skills/`, `~/.agents/skills/`, `~/.kimi/skills/`, `~/.config/opencode/skills/`, `~/.config/kilo/skills/`, `~/.claude/skills/`, `~/.gemini/skills/`, `~/.gemini/antigravity/skills/`, `~/.cursor/skills/`, `~/.copilot/skills/`, `~/.codex/skills/`, `~/.codeium/windsurf/skills/`, `~/.qwen/skills/`, `~/.kiro/skills/`, and `~/.openclaw/skills/`.
- Project level: `{project-root}/skills/`, `{project-root}/.opencode/skills/`, `{project-root}/.claude/skills/`, `{project-root}/.gemini/skills/`, `{project-root}/.cursor/skills/`, `{project-root}/.github/skills/`, `{project-root}/.codex/skills/`, `{project-root}/.qwen/skills/`, `{project-root}/.kiro/skills/`, `{project-root}/.openclaw/skills/`, `{project-root}/.pi/skills/`, `{project-root}/.agent/skills/`, `{project-root}/.agents/skills/`, and `{project-root}/.atl/skills/`.

Of what turns up, `sdd-*`, `_shared` and `skill-registry` are dropped. Each skill name gets one entry, and a
name found at both levels goes to the project-level skill rather than the user-level one. Read as much of
every selected `SKILL.md` frontmatter as you need, and record per skill its `name`, the trigger text from its
`description`, the full path to its `SKILL.md`, and its scope. What results is an index, never a generated
summary: subagents receive exact paths and read the whole skill, which remains the source of truth.

The project's convention files are scanned as well: `agents.md`, `AGENTS.md`, a project-level `CLAUDE.md`,
`.cursorrules`, `GEMINI.md` and `copilot-instructions.md`. When one of them is an index, `AGENTS.md` for
example, pull out the file paths it references, and enter the index together with each of those files in the
registry.
