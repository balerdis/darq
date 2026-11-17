---
name: sdd-init
description: "Trigger: sdd init, iniciar sdd, openspec init. Initialize SDD context, testing capabilities, registry, and persistence."
disable-model-invocation: true
user-invocable: false
license: MIT
metadata:
  author: darq-balerdis
  version: "3.0"
  delegate_only: true
---

> **ORCHESTRATOR GATE.** Whoever opens this file with the `skill()` tool is the orchestrator, and must not
> run the phase inline: halt here and launch the `sdd-init` sub-agent through the platform's delegation
> primitive (`task(...)`, sub-agent invocation, and so on). What follows is for executors only.

## For the sdd-init sub-agent

That gate is for the orchestrator, not for you. Do the phase yourself, delegating NONE of it and never
invoking the Skill tool: executing is your job, so execute.

## Activation Contract

Trigger: a request, from the orchestrator or from the user, that a project be made ready for SDD. As the
phase executor you do this work in person: nothing is delegated, and you never take on the orchestrator's
role.

## Hard Rules

- Detect, and never guess: the project's real architecture, its stack and the conventions it keeps, the
  persistence mode, the tools it tests with.
- Should `openspec/` exist already, say what is in it, and ask before you update it.
- Testing capabilities ALWAYS get a record of their own, kept apart from the rest: the Engram observation
  `sdd/{project}/testing-capabilities`, or the `testing:` key of `openspec/config.yaml`.
- `.atl/skill-registry.md` is built EVERY time; when Engram is reachable, `skill-registry` goes there as well.
- Automated SDD and config saves pass `capture_prompt: false` where the tool takes that field, and leave it
  out if the tool's schema has no such field.
- English is the default for every technical artifact you generate. Neither the conversation's language nor
  the persona's regional voice enters an SDD artifact, except when the user explicitly wants that language for
  the artifact or the conventions of the project call for it. Another language the user explicitly asked for
  gets a neutral, professional register, unless the user explicitly names a different tone or a regional
  variant.
- Comments addressed to the public or to a particular context use that context's language by default. An
  explicit instruction from the user on language or tone wins; without one they stay neutral and
  professional, unless the context clearly demands a different tone or a regional variant.

## Decision Gates

| Input | Action |
|---|---|
| Store mode `engram` | Engram, and nothing else, receives both the testing capabilities and the project context; `openspec/` is never created. |
| Store mode `openspec` | Nothing but the files that bootstrap openspec gets created or updated, written as file artifacts by the rules of `_shared/openspec-convention.md`. |
| Store mode `hybrid` | Persist both ways at once: the openspec files and the Engram observations. |
| Store mode `none` | Hand back what you detected, and write no SDD artifact at all, with one exception: the registry, whenever it is needed. |
| Strict TDD Mode | Resolve it with "Resolving Strict TDD Mode" in `_shared/implementation-craft.md`, then persist the result as `strict_tdd`. |

## Execution Steps

1. Read the project's own files, then summarize what stack it runs on and which conventions it keeps:
   manifests such as `pyproject.toml`, `go.mod` or `package.json`, the CI setup, and whatever configures
   linting and tests.
2. Find the test runner and the test layers, then coverage, then the formatter, the linter and the type
   checker.
3. Resolve Strict TDD Mode with "Resolving Strict TDD Mode" in `_shared/implementation-craft.md`, using the runner step 2 found.
4. Bring up the persistence that the chosen store mode requires.
5. Write `.atl/skill-registry.md` by the scan rules in "Building the skill registry" of
   `sdd-init/references/init-details.md`. In a git repository, list `.atl/` in `.git/info/exclude` too,
   unless a line already ignores it; never use `.gitignore` for this.
6. Store what was found: the project context, and with it the testing capabilities.
7. Reply with the envelope described under Output Contract.

## Output Contract

The envelope you answer with has five fields:

- `status`
- `executive_summary`
- `artifacts`
- `next_recommended`
- `risks`

Include project, stack, persistence mode, Strict TDD status, testing capability table, saved observation IDs/paths, registry path, and next `/sdd-explore` or `/sdd-new` step.

## References

- `sdd-init/references/init-details.md`: what to detect and where, what each Engram save carries, the
  skeleton of the openspec config, and the templates for the reply.
- `_shared/mcp/engram-convention.md`: the naming of what Engram stores; it exists only when the `engram`
  server was chosen.
- `_shared/openspec-convention.md`: the layout of openspec and the rules it keeps.
