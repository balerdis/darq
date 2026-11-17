# What Every SDD Phase Shares

The protocol the SDD phase skills have in common. Every phase sub-agent MUST load it together with the `SKILL.md` of its own phase.

Who does the work: whoever runs an SDD phase EXECUTES it and never orchestrates. Unless told otherwise the phase's work is yours to do, and you hand work back only when your phase skill says, in so many words, to halt with a blocker report. Giving the whole phase to another agent is a hand-off, not delegation, and is forbidden outright. When your own work divides into genuinely independent parts, read `_shared/sub-delegation-criterion.md` (resolved against the skills root, per Section F below) before you fan any of it out to `darq-general`, which is today the only target your own descriptor permits; that file owns the criterion, the shape of the fan-out and the merge rule, for every agent that applies it and not only for this one. If it is missing or unreadable, work through the parts yourself one after another and say so in your report: an unreadable criterion stops delegation, never the phase.

## A. Skill Loading

Use the first of these sources that is there:

1. In the prompt that launched you, the orchestrator's `## Skills to load before work` block. Read precisely the `SKILL.md` files it lists before you start on the task itself. This source wins: while it is present, IGNORE every `SKILL: Load` instruction that repeats it.
2. A `SKILL: Load` instruction: load precisely the skill files it names.
3. The skill registry, looked up with `mem_search(query: "skill-registry")` and read whole through `mem_get_observation(id)` on the hit, or else the `.atl/skill-registry.md` file at the root of the project when one exists. Hold the triggers of its index against what you were asked to do, and for each match read the `SKILL.md` it lists, path exactly as written.
4. Nothing at all: go ahead with only your phase skill.

Source 1 is the preferred route; 2 and 3 stand in when it is absent. A registry lookup is SKILL LOADING; it is not delegation.

## B. Artifact Retrieval (Engram Mode)

What `mem_search` hands back is a 300-char PREVIEW, never the whole artifact, so you MUST call `mem_get_observation(id)` for EVERY artifact: **build on a preview and the output is wrong.** Run two parallel rounds instead of a sequence of single calls:

1. All searches together, noting each ID: `mem_search(query: "sdd/{change-name}/{artifact-type}")`.
2. All retrievals together, for the complete content (REQUIRED): `mem_get_observation(id: {saved_id})`.

Nothing you produce may rest on a preview.

## C. Artifact Persistence

Persisting the artifact your phase produced is a MUST. Leave it out and the pipeline BREAKS, because the phases downstream will look for it in vain. This is the one memory write your launch brief asks for, per the ambient memory-scope rule: the `Artifact store mode` your launch passed is that request, and it reaches your own artifact only, never a session summary or a discovery saved on its own.

| Mode | Your step |
|---|---|
| `engram` | the `mem_save` call below |
| `openspec` | none: the main step of the phase already wrote the file |
| `hybrid` | both: the file on disk AND the `mem_save` call below |
| `none` | inline result only, no file written, no `mem_save` |

```
mem_save(title: "sdd/{change-name}/{artifact-type}", topic_key: "sdd/{change-name}/{artifact-type}", type: "architecture", capture_prompt: false, content: "{your full artifact markdown}")
```

Because of `topic_key`, saving a second time updates the observation rather than adding a duplicate. One exception: the Strict TDD evidence record `sdd/{change-name}/apply-evidence/{n}`, where each apply batch takes a fresh key, writes it once and never saves to it again. An SDD artifact is pipeline output made by a machine, not a memory a person or a proactive save creates, hence the flag is required. When the schema of the Engram tool offers it, include `capture_prompt: false`; when the schema is older and refuses the field or lacks it, drop it instead of failing.

## D. Return Envelope

> **CRITICAL: text comes last.** The envelope you return, as text, is the very end of your output; NEVER finish on a tool call, and make any `mem_save` before it. `mem_session_summary` is not yours to call; only a top-level agent calls it. **Why**: if a tool call is the last thing a sub-agent does, its parent only ever sees that tool's return value, and the analysis in your text never arrives.

Each phase MUST give the orchestrator an envelope with this structure:

| Field | Contents |
|---|---|
| `status` | `success`, `partial` or `blocked` |
| `executive_summary` | between one and three sentences on the work done |
| `detailed_report` | optional; everything the phase produced, unless it is inline anyway |
| `artifacts` | the key or the path of each artifact you wrote |
| `next_recommended` | which SDD phase comes next, or "none" |
| `risks` | any risk you came across, or "None" |
| `skill_resolution` | where your skills came from: `paths-injected` when the orchestrator sent exact paths, `fallback-registry` when you took the paths out of the registry yourself, `fallback-path` when they came through SKILL: Load, `none` when you loaded no skill |

Report observations, not actions: never "added test X", always "test X: ran `<command>` → 30 tests". When you sub-delegated, say so, and keep what you checked with your own eyes separate from what you merely relay. A report written as a list of actions describes an intention, and each level of delegation buries the evidence one summary deeper.

An example, from a design phase:

```markdown
**Status**: success
**Summary**: Design of `{change-name}` saved: architecture decisions plus the file changes they imply.
**Artifacts**: `openspec/changes/{change-name}/design.md` | Engram `sdd/{change-name}/design`
**Next**: sdd-tasks
**Risks**: None
**Skill Resolution**: fallback-registry — 2 skills (go-testing, typescript)
(other possible values: `none — no registry found`, `paths-injected`, `fallback-path`)
```

## E. Review Workload Guard

Producing tasks is not enough: SDD also guards how much a reviewer has to take in. The guard keeps reviewers from burning out and delivery safe, so do not treat it as optional process noise.

- Execution mode: interactive|auto

**Budget.** By default a PR's review budget is **400 changed lines**, counted as `additions + deletions`. Only authored text counts, additions plus deletions; generated goldens are left out of the authored risk count while remaining part of complete snapshot identity.

**Orchestrator.** When the session starts, a delivery strategy MUST be cached by it, with the values and the default that come from `_shared/sdd-session-preflight.md`. It MUST give `sdd-tasks` the `Delivery strategy`, and give `sdd-apply` the decision that strategy resolved to.

**`sdd-tasks`.** Its forecast MUST say whether the planned work could break the budget, and each guard line below MUST appear in that forecast as exact plain text:
- `Decision needed before apply: Yes|No`
- `Chained PRs recommended: Yes|No`
- `400-line budget risk: Low|Medium|High`

On a high forecast, the recommendation it MUST make is chained or stacked PRs, split into deliverable work units.

**`sdd-apply`.** Unless the delivery strategy lands on chained/stacked PR slices, or on a `size:exception` that somebody accepted explicitly, it MUST NOT take on oversized work.

**Slices.** Every slice of a chain MUST start and end clearly, own a scope that stands alone, carry its own verification and be reasonably easy to roll back. Inside a Feature Branch Chain the first PR, PR #1, has the feature/tracker branch as its target, and each later child PR targets the branch of the PR right before it; if GitHub's diff for a child still shows earlier slices, retarget or rebase it until only that slice is left in the diff.

## F. Path Resolution

A reference to any file in the skills tree is written relative to the skills root, so `_shared/sdd-phase-common.md` or `sdd-apply/references/cbm-index-coherence.md` names the same file whichever skill wrote it.
