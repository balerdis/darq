---
name: engram
description: Persistent memory that survives across sessions and compactions
distribution: download
endpoint: https://github.com/balerdis/engram/releases/download/v1.24.0/engram_1.24.0_linux_amd64.tar.gz
version: 1.24.0
checksum: sha256:02ce8e5647509d8beccc4a342ded73622a230028c8d1c296bd1fb13dd9ba4b3d
archive_members: [CHANGELOG.md, LICENSE, README.md, engram]
archive_executable: engram
argv: [mcp, --tools=agent]
reaches: [arquitecto-darq, darq-explorer, darq-general, darq-implementer, darq-orchestrator, darq-verifier, sdd-apply, sdd-archive, sdd-design, sdd-explore, sdd-init, sdd-onboard, sdd-propose, sdd-spec, sdd-tasks, sdd-verify]
---

# Engram Convention (persistent memory)

Engram gives you memory that outlives both the session and any compaction. You reach it
through the `mem_*` tools: `mem_save`, `mem_search`, `mem_context` and the rest of that
family. Whenever those tools are in your session, everything below applies at all times. It
is mandatory, not something you switch on when it seems useful.

## Memory Scope (who writes, and when)

If you were launched by another agent, you make no memory writes — no `mem_save`,
`mem_update`, `mem_session_summary`, nor the `mem_judge` that follows a save — unless
your brief asks for one. You may still read: `mem_search`, `mem_context`,
`mem_get_observation`. What deserves keeping goes in your reply; whoever launched you
decides what to save.

The agent talking with the person works the other way round: any write it wants from an
agent it launches has to be asked for in that agent's brief, and a durable finding that comes
back in the reply is the launcher's own to save.

## Sub-Agent Findings (`## Key Learnings`)

When engram is selected, a passive capture runs on the way back from a launched
agent — the platform's own plugin on the sub-agent tool's output, or its hook on the
sub-agent's last message, whichever the platform provides. A sub-agent can therefore
have specific findings saved for it without ever calling a memory tool: when its
brief asks for this, it ends its reply with a `## Key Learnings` section, and that
section is saved automatically once the reply returns.

The exact format of that section:

- Always write the heading exactly as `## Key Learnings`, on its own line. As
  compatibility forms only, engram v1.20.0's extractor (`ExtractLearnings`,
  `internal/store/store.go`) also recognizes `### Key Learnings`, `## Learnings`
  and `### Learnings` — never a heading with a single `#`: the extractor's
  heading pattern is anchored to two or three `#` (`^#{2,3}`), so one `#` is
  not recognized and nothing under it is saved.
- Items are numbered (`1.`, `2.`, ...), one durable finding per item, each a
  self-contained sentence on its own line. A bulleted list is used only as a
  fallback when there are no numbered items.
- Each item needs 20 or more characters and 4 or more words after stripping bold,
  italic and inline-code markup — a fragment shorter than that is dropped, not
  saved short.
- If the reply has more than one such section, only the **last** one that yields
  valid items is used; an earlier one is discarded, not merged.
- Saved items are deduplicated by a normalized hash within the project — the same
  finding written twice does not produce two observations.
- Each item lands as its own observation, type `passive`, scope project, linked to
  the **launcher's** session — the passive capture runs in the launching agent's
  hook, not the sub-agent's.

This save runs on every platform whenever engram is selected. The agent that
launched the sub-agent leaves its `## Key Learnings` items to that capture: it
does not save them again and never searches memory just to confirm they landed.
Anything else durable in the reply is still its to save.

## When to Save (if you are the agent talking with the person)

Each of these events calls for a `mem_save` once it has happened:

- **Decisions**: an architecture or design decision; a tool or library chosen, with its
  tradeoffs; a change of workflow that was agreed on.
- **Conventions**: a team convention documented or established; a pattern settled on, be it
  naming, structure or convention.
- **Work done**: a bug fix completed (save its root cause with it); a feature built through a
  non-obvious approach; a Notion, Jira or GitHub artifact created or updated with significant
  content; a configuration change or an environment set up.
- **Things learned**: a non-obvious discovery about the codebase; a gotcha, an edge case or
  some unexpected behavior; a preference or constraint of the user's.

If nothing durable came out of the work (a check that merely confirmed, an attempt that got
blocked, a delegation with nothing new in it), save nothing. And if the topic is already in
memory, update it under its existing topic key instead of saving it a second time.

## Save Format

A `mem_save` call carries these fields:

| Field | What goes in it |
|---|---|
| **title** | a verb plus its object, short and easy to search for, e.g. "Fixed N+1 query in UserList" |
| **type** | one of `bugfix`, `decision`, `architecture`, `discovery`, `pattern`, `config`, `preference` |
| **scope** | `project` by default, or `personal` |
| **topic_key** | recommended whenever a topic will evolve: a stable key such as `architecture/auth-model` |
| **content** | four labelled parts: **What** (one sentence on what was done), **Why** (what prompted it: a user request, a bug, performance and so on), **Where** (the files or paths affected), **Learned** (gotchas, edge cases, surprises; leave it out when there were none) |

Write the title and the content in normal prose, with a space between words and every word spelled out whole. Memory search matches whole words, so a fused word like `credentialchanges` is never found by a search for `credential`. This holds however long the session has run.

## Topic Update Rules

- Two different topics MUST NOT overwrite one another.
- While one topic evolves, keep reusing its `topic_key`, so each save upserts.
- Not sure which key fits? Ask `mem_suggest_topic_key` before saving.
- To correct a specific observation whose ID you know, use `mem_update`.

## Searching Memory

Whenever the user says any variation of "remember", "recall", "what did we do" or "how did
we solve", or otherwise points at past work, in whatever language they write, look it up in
this order:

1. `mem_context`: recent session history, fast and cheap.
2. Nothing there? `mem_search` with keywords that fit.
3. A hit? `mem_get_observation` returns its full, untruncated content.

Search on your own initiative as well: before starting work that may already have been done;
when the user brings up a topic you have no context on; and when the user's FIRST message
touches the project, a feature or a problem. In that last case run `mem_search` with
keywords taken from the message, to check for earlier work before you answer.

## Session Close Protocol (if you are the agent talking with the person)

Only the agent talking with the person calls `mem_session_summary`, and only at a
real close: the person says the session is ending, or asks for it (or the
equivalent in the user's language). Finishing a task, getting a delegation back, or
delivering a reply is not a close, and neither is saying "done" / "listo" / "that's
it". At a real close, call `mem_session_summary` with this shape:

```markdown
## Goal
[What this session was working on]

## Instructions
[Preferences or constraints of the user found along the way; skip if none]

## Discoveries
- [Technical findings, gotchas, non-obvious learnings]

## Accomplished
- [Items completed, with their key details]

## Next Steps
- [What is left to do, for the next session]

## Relevant Files
- path/to/file — [what it does or what changed]
```

Skipping this is not an option: without it, the next session begins knowing nothing of this
one.

## After Compaction (if you are the agent talking with the person)

If you are the agent talking with the person and you see a compaction message or
"FIRST ACTION REQUIRED":
1. IMMEDIATELY call `mem_session_summary` with the compacted summary content —
   this persists what was done before compaction
2. Call `mem_context` to recover additional context from previous sessions
3. Only THEN continue working

Do not skip step 1. Without it, everything done before compaction is lost from
memory. A sub-agent that hits compaction follows the Memory Scope rule above
instead: no `mem_session_summary` unless its brief asks for one.

## SDD Artifact Naming Convention

NOTE: each skill's SKILL.md already carries the engram calls it depends on (`mem_search`, `mem_save`, `mem_get_observation`). What follows is reference material only; a sub-agent does NOT have to read it to do its work.

For an SDD phase sub-agent, the `Artifact store mode` line in your launch — `engram` or `hybrid` — is the brief asking for exactly this artifact write; it is not a license to save anything else. Ad-hoc discovery saves and `mem_session_summary` stay the launching agent's job, not yours, per the Memory Scope rule above.

### How Every SDD Artifact Is Keyed

Every SDD artifact persisted to Engram MUST be named the same deterministic way:

| Field | Value |
|---|---|
| `title` | `sdd/{change-name}/{artifact-type}` |
| `topic_key` | `sdd/{change-name}/{artifact-type}`, identical to the title |
| `type` | `architecture` |
| `scope` | `project` |
| `capture_prompt` | `false` |

For SDD artifacts, `capture_prompt: false` is REQUIRED whenever the Engram tool schema
supports the field. Engram v1.15.3 records the user's prompt by default on human or
proactive saves, and SDD artifacts are automated pipeline output, not saves of that kind.
Their `type` cannot tell the two apart, because human architecture decisions use
`architecture` as well, so never infer the flag from it. On an older schema that rejects the
field or does not expose it, leave it out rather than letting the call fail.

### The Artifacts

| Producer | `{artifact-type}` | What it holds |
|---|---|---|
| orchestrator | `state` | the DAG state, used to recover after a compaction |
| sdd-explore | `explore` | the exploration analysis |
| sdd-propose | `proposal` | the change proposal |
| sdd-spec | `spec` | the delta specifications, every domain concatenated into one |
| sdd-design | `design` | the technical design |
| sdd-tasks | `tasks` | the task breakdown |
| sdd-apply | `apply-progress` | implementation progress: one single artifact, upserted on every batch; under Strict TDD it carries the TDD Evidence Ledger |
| sdd-apply | `apply-evidence/{n}` | Strict TDD only: the TDD Cycle Evidence of batch `{n}`, under topic key `sdd/{change-name}/apply-evidence/{n}`; written once, never updated |
| sdd-verify | `verify-report` | the verification report |
| sdd-archive | `archive-report` | the archive closure, lineage included |

### Saving and Updating

An ordinary write is a single call of this form:

```
mem_save(title: "sdd/{change-name}/{artifact-type}", topic_key: "sdd/{change-name}/{artifact-type}", type: "architecture", capture_prompt: false, content: "{full markdown content}")
```

Saving the proposal of a change called `add-dark-mode`, for instance, reads
`mem_save(title: "sdd/add-dark-mode/proposal", topic_key: "sdd/add-dark-mode/proposal", type: "architecture", project: "my-app", capture_prompt: false, content: "## Proposal\n\nAdd dark mode toggle...")`.

The `state` artifact uses the same call with `title` and `topic_key` both set to
`sdd/{change-name}/state`, `type: "architecture"` and `capture_prompt: false`. Its `content`
is YAML of this shape:

```yaml
change: {change-name}
phase: {last-phase}
artifact_store: engram
artifacts:
  proposal: true
  specs: true
  design: false
  tasks: false
tasks_progress:
  completed: []
  pending: []
last_updated: {ISO date}
```

To bring that state back: `mem_search("sdd/{change-name}/state")`, then
`mem_get_observation(id)`, then parse the YAML and restore the state from it.

To replace an artifact whose observation ID you hold, call
`mem_update(id: {observation-id}, content: "{updated full content}")`. The rule of thumb:
the exact ID in hand means `mem_update`; otherwise upsert, with `mem_save` under the same
`topic_key`.

### Finding and Reading Artifacts

A search only ever returns a truncated preview plus the observation ID, so reading an
artifact always takes two calls:

1. `mem_search(query: "sdd/{change-name}/{artifact-type}")` for the ID;
2. `mem_get_observation(id: {observation-id})` for the complete content.

Needing several artifacts, run every search first and keep only the IDs (say
`mem_search(query: "sdd/{change-name}/proposal", ...)`, then the same for `spec` and
`design`). Only then fetch each one in full, e.g. `mem_get_observation(id: {proposal_id})`,
`mem_get_observation(id: {spec_id})`, `mem_get_observation(id: {design_id})`. That second,
full-content pass is mandatory.

`mem_search(query: "sdd/{change-name}/")` lists every artifact of one change. The project
context comes back through `mem_search(query: "sdd-init/{project}")` for its ID, and then
`mem_get_observation(id)` for the whole of it.

### Stale Memories

Where Engram exposes lifecycle metadata or tooling:

- At the start of a session, and before architecture-sensitive work, list the current
  project's memories with `mem_review` (action `list`), if that tool is available.
- If it is not, the task carries on regardless: use `mem_context`/`mem_search` as usual, and
  still honor lifecycle metadata on any observation that comes back with it.
- An `active` memory can be used as usual. A `needs_review` memory is stale context, not a
  trusted fact: bring it up, and check it against current evidence before you lean on it.
- Never mark anything reviewed on your own. `mem_review` with action `mark_reviewed` runs
  only after the user has explicitly confirmed it, or inside a dedicated memory maintenance
  command.

### Project Name Resolution (engram v1.11.0+)

**Leave `project` out: engram already knows it.** At MCP startup it works the project out a
single time, from the git remote of the tree it was launched in, and every call that omits
the argument lands there. The `--project` flag and the `ENGRAM_PROJECT` environment variable
can override that choice, and every name, however it arrives, is lowercased and trimmed.

Pass the argument only to reach a project other than the current one, and only
when you know that project already exists — `mem_save` refuses a name it does
not recognise rather than creating it, and the error is `unknown_project`. A
refused save is a memory lost with the turn, so the argument is the riskiest
field in the call: omitted it is always right, supplied it can only be wrong.
`mem_search` refuses the same way, and its error lists the projects that do
exist, which is the cheapest way to find the real name of one.

**A project name from another server is not a project name here.** Codebase
Memory derives its names from the filesystem path; engram derives its own from
the git remote. The same checkout is `home-serg-work-thing` to one and
`thing-api` to the other, and neither can resolve the other's spelling. Never
carry a name across from a tool that just handed you one.

Saving under a name that matches none of the existing observations makes engram warn of
possible name drift. Variants are merged with the `mem_merge_projects` MCP tool, or with
`engram projects consolidate` on the command line.

### Upsert Behavior

A save that matches an existing observation on `topic_key`, `project` and `scope` together
UPDATEs it in place, an overwrite and never an INSERT. The earlier content is gone:
`revision_count` goes up, but the old text is NOT kept. That is deliberate, since engram is
working memory rather than an audit trail; iteration history or team collaboration call for
`openspec` or `hybrid` mode instead. The Strict TDD evidence records are the exception by
construction: each batch saves under a new key (`sdd/{change-name}/apply-evidence/{n}`), so
nothing is overwritten and no earlier record is ever saved again.

### Why It Is Built This Way

Titles are deterministic so that recovery can match them exactly. The `topic_key` is what
lets upserts happen without duplicates. The `sdd/` prefix gives every SDD artifact a
namespace of its own. Recovery takes two steps because search previews are always truncated,
and `mem_get_observation` is the only route to the full content. Finally, the archive-report
lists every observation ID involved, which keeps the lineage completely traceable.
