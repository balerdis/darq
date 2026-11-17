# Skills for Delegated Work

This protocol binds (MUST) whoever delegates: it is how a delegating agent works out which of the
project's skills a sub-agent's job needs, and how it gets them to the sub-agent without loss.

The reason: a freshly launched sub-agent has no idea which of the project's skills exist. Its remedy is the
registry, a cheap catalogue of them for the delegator, and using it never requires anyone to rewrite or
summarize a skill.

Apply it ahead of each launch whose job touches the artifacts of the project in any way: to read them, write,
review or test them, document them, or create them. Only a command that is mechanical through and
through goes without.

## 1. Locate the registry

**Index, not rulebook**: per skill, the registry holds a name, its triggers, its scope and the exact
location of its `SKILL.md`, and no compacted rules at all. Stop at the first of these that answers:

1. a copy cached earlier in this session;
2. Engram: `mem_search(query: "skill-registry")`, then `mem_get_observation(id)` on the hit to read
   all of it;
3. the file `.atl/skill-registry.md` at the root of the project. When creating `.atl/` in a git
   repository falls to you, list `.atl/` in `.git/info/exclude` (never in `.gitignore`), except when
   a line already ignores it;
4. none of them: carry on without the project's skills, and warn that the user needs to run
   `external registry refresh`.

## 2. Choose

Compare each registry entry's trigger or description with two aspects of the job:

| Aspect | A match names |
|---|---|
| Code and files | the framework, language or tool in play, or the paths involved |
| Task and action | the kind of work, with actions such as tests, docs, a PR, Jira, a release, comments or a review |

Send the fewest skills that still help. Above five matches, cut down to the top five by relevance,
and when ranking them, the code side beats the context of the task.

## 3. Send paths

Paths go to the sub-agent; summaries never do. Its launch prompt carries a block shaped like this one.

```markdown
## Skills to load before work

Every file below comes first: do not read, write, review, test or create an artifact until you have read them.

- /absolute/path/to/skills/react-19/SKILL.md
- (one line per selected skill)
```

Reading the listed files comes first, ahead of anything specific to the task, and is a MUST for the
sub-agent: `SKILL.md` itself is what it runs under, and the authority on what the skill says.

## 4. Ask how it went

`skill_resolution` is a MUST in every sub-agent's report, with one of four values:

| Value | Meaning |
|---|---|
| `paths-injected` | the delegating agent sent the precise skill paths, and they were loaded |
| `fallback-registry` | nothing was sent, so the sub-agent looked registry paths up by itself |
| `fallback-path` | a fallback path given explicitly, not one in the registry, was loaded |
| `none` | no skill was loaded |

Any value besides `paths-injected` obliges the orchestrator to go back over the registry, re-reading
it before it delegates again.

## Surviving compaction

`.atl/skill-registry.md` and Engram both keep the registry, so after a compaction a delegator
recovers the paths it chose by consulting it once more. Since sub-agents get the precise files rather
than generated digests, nothing a skill means is lost along the way.

## Where it is applied

| Delegator | Applies it |
|---|---|
| ATL Orchestrator | to every delegation, SDD or not |
| judgment-day | ahead of Judge A, Judge B and the Fix Agent |
| pr-review, and any delegator added later | whenever it starts sub-agents |
