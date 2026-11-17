# Persistence Contract

Where SDD artifacts are kept under each artifact store mode, who reads and who writes them, and what
an orchestrator writes into a launch so that a sub-agent persists the right thing.

## Choosing the mode

The orchestrator passes the `Artifact store mode`, with one of the values
`engram | openspec | hybrid | none`. The orchestrator ASKS the user which one they want during SDD
Session Preflight, which runs on the first SDD command of a session or on a natural-language request
that amounts to one, and keeps the answer for the rest of the session. When preflight runs, what
else it settles and which mode is the default are all defined in `_shared/sdd-session-preflight.md`;
do not restate the default here.

## The four modes

- **`engram`** is the memory that carries work from one session to the next. Reads and writes go to
  Engram and it never creates project files. It recovers in a new session and survives compaction, but it lives in a
  local DB the team cannot share, and it keeps no iteration history: Engram upserts by `topic_key`,
  so running a phase again for the same change replaces the earlier version, with no revision kept.
  Its audit trail is partial, because archiving stores a summary report rather than the full
  artifact folder. Choose `openspec` or `hybrid` when you need every iteration kept, or a team
  working together.
- **`openspec`** is the source of truth. Reads and writes go to the filesystem and it does create
  project files: committed files the team can share, git history holding every iteration, and the
  full folder as audit trail once archived. It does not survive compaction, and it recovers in a new
  session only through git.
- **`hybrid`** is both at once: files for the team, Engram for recovery. It reads Engram first, with
  the filesystem as fallback, writes both, creates project files, recovers across sessions,
  survives compaction, shares through its files, keeps iterations in files plus git, and archives
  both. It costs more tokens.
- **`none`** is ephemeral. It reads only the orchestrator's prompt context, writes nothing, creates
  no project file, recovers nothing, shares nothing and leaves no audit trail: it is lost when the
  conversation ends.

How `hybrid` writes: every artifact goes to Engram, following `_shared/mcp/engram-convention.md`
(recovery across sessions, survival through compaction, deterministic search), and at the same time
to the filesystem, following `_shared/openspec-convention.md` (human-readable files that can go
under version control). An operation counts as complete only once BOTH writes have succeeded. A read
tries Engram first and turns to the filesystem when Engram comes back empty. Each operation costs
MORE tokens than with a single store, so choose `hybrid` only when you need cross-session
persistence and local file artifacts together.

## Orchestrator state

After every phase transition the orchestrator saves the DAG state, so an SDD run can be picked up
again after a compaction:

- `engram`: saved with `mem_save(topic_key: "sdd/{change-name}/state", capture_prompt: false*)`;
  found again with `mem_search("sdd/*/state")` followed by `mem_get_observation(id)`.
- `openspec`: written to, and read back from, `openspec/changes/{change-name}/state.yaml`.
- `hybrid`: both the `mem_save` and the `state.yaml` file; recovery tries Engram before the file.
- `none`: neither saving nor recovering is possible, so warn the user.

\* State is an automated artifact. Pass `capture_prompt: false` whenever the Engram tool schema
offers the field; when an older schema rejects it or does not expose it, leave it out instead of
failing.

## Rules every phase follows

- `none`: create or modify no project file at all; the results go back inline only.
- `engram`: write no project file; persist to Engram and hand back the observation IDs.
- `openspec`: write files only at the paths `_shared/openspec-convention.md` defines.
- `hybrid`: persist to Engram and to the filesystem alike, following both conventions.
- Never force an `openspec/` folder into existence: it is created only when the orchestrator passed `openspec` or `hybrid` explicitly.
- No mode passed at all: persist nothing, return the results inline, and do not choose a mode yourself.

## Who reads and who writes

A sub-agent starts from a fresh context: it has NO view of what the orchestrator was instructed, nor
of its memory protocol.

Under the ambient memory-scope rule (`_shared/mcp/engram-convention.md`), a sub-agent makes no
memory write unless its brief asks for one. The `Artifact store mode` line of an SDD launch, when it
says `engram` or `hybrid`, IS the brief asking for that phase's own artifact write — nothing else.
An SDD phase agent therefore saves its designated artifact and only that: discovery saves of its own
accord and `mem_session_summary` are outside its brief unless a specific instruction adds them.

| Launch | Who reads the context | Who writes |
|---|---|---|
| Non-SDD task | engram is searched by the orchestrator, which passes a summary in the prompt | the orchestrator, keeping what is worth it from the durable findings the sub-agent returns in its reply |
| SDD phase with dependencies | the sub-agent, straight from the backend | the sub-agent, its own artifact |
| SDD phase without dependencies, such as explore | nobody | the sub-agent, its own artifact |

Why the work is split this way:
- Non-SDD work: the orchestrator knows which context is relevant, and a sub-agent running its own searches burns tokens on results that are not.
- SDD reads: the artifacts are large, and pasting them into the orchestrator's prompt would take up its whole context window, so the phase reads them itself.
- SDD phases write their own artifact: the `Artifact store mode` line in their launch asks for exactly that write, and the detail is theirs to persist directly. A non-SDD sub-agent hands its findings back instead, and the launcher decides what is durable enough to keep.

## Orchestrator Prompt Instructions for Sub-Agents

Each template below contains lines that read from or write to memory. Include those lines only when
the artifact store mode is `engram` or `hybrid`; under `openspec` or `none`, leave out the retrieval
and persistence lines and keep the rest of the template. Telling a sub-agent that the pipeline breaks
unless it calls a tool it does not have is worse than telling it nothing.

**Non-SDD launch:**

```
Return durable findings in your reply — decisions, discoveries, bug fixes, conventions
worth keeping. You make no memory write; the launcher decides what to save from what
you return.
```

Only when the launcher wants this sub-agent's findings saved automatically, rather than handed back
for the launcher to save, add:
```
PERSISTENCE: End your reply with a `## Key Learnings` section — numbered, one durable finding per item, each a self-contained sentence on one line. Call no memory tool for it; it is saved automatically when your reply returns.
```

**SDD phase launch.** The three read lines, from "Before you start" down, go only to a phase that
depends on earlier artifacts; for a phase with no dependencies, drop them and send the rest as it
stands.
```
Artifact store mode: {engram|openspec|hybrid|none}
Before you start, read each of these artifacts in full; a search alone gives a truncated preview:
  mem_search(query: "sdd/{change-name}/{type}") → its ID
  mem_get_observation(id: {id}) → its full content (REQUIRED)

PERSISTENCE IS MANDATORY — do not skip it:
When your work is done you MUST call
  mem_save(title: "sdd/{change-name}/{artifact-type}", topic_key: "sdd/{change-name}/{artifact-type}", type: "architecture", capture_prompt: false, content: "{your full artifact markdown}")
Return without that call and the phase after you will NOT find your artifact: the pipeline BREAKS.
```

Every SDD artifact save spells out `capture_prompt: false`, and it is mandatory wherever the Engram
tool schema supports the field. By default Engram v1.15.3 turns `capture_prompt` on (true), which is
right for an ordinary human or proactive save; an automated pipeline artifact, though, must keep the
user's prompt out of it. Do not decide it from `type`: a genuine architecture decision made by a
person carries `architecture` too, just like every SDD artifact. When an older schema rejects
`capture_prompt` or does not expose it, omit it instead of failing.

## The last output is text

A sub-agent that persists something, by `mem_save` or by writing a file, makes that call BEFORE its
final text response, and the very last thing it outputs is text, never a tool call. It must NOT
call `mem_session_summary` either; only top-level agents call that.

**Why**: the Task tool hands the parent only what the sub-agent outputs last. When that output is
a tool call, the parent gets nothing but the tool's result (`"Observation saved"`, for example), and
the analysis the sub-agent wrote never arrives. The order is always: the work, then the save, then
the text envelope.

## Skills for the sub-agent

Before the launch, the orchestrator looks the skill paths up in the skill registry and puts them
into the launch prompt as a `## Skills to load before work` block; the sub-agent reads exactly those
`SKILL.md` files before any task-specific work. Without that block, a `SKILL: Load` instruction is the fallback. With neither,
the sub-agent goes on without skills, and that is not an error. Running the `skill-registry` skill
or `sdd-init` generates or refreshes the registry.

## Verbosity

A launch may come with `detail_level` set to `concise | standard | deep`. It sets how much the
output says and never what is persisted: the full artifact is always saved.
