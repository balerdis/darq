---
name: skill-registry
description: "Trigger: update skills, skill registry, actualizar skills, after skill changes. Index available skills by trigger and path."
license: MIT
metadata:
  version: "1.0"
---

## Activation Contract

Run this whenever the set of skills changes (one was installed, removed, created, moved or
renamed) and whenever delegation calls for an up-to-date index of them.

## Hard Rules

- Leave out `sdd-*`, `_shared` and `skill-registry` entirely. When two skills share a name,
  keep one: the project-level skill beats the user-level one.
- Whatever the SDD persistence mode, the registry file `.atl/skill-registry.md` gets written,
  every time.
- With Engram available, the registry is stored there too, using the fields of step 4 (its
  topic key is `skill-registry`, and prompt capture is turned off).
- Unless that has been explicitly disabled, put `.atl/` in `.gitignore` where you can.
- What you build is an index. It compiles nothing and summarizes nothing; each skill's
  `SKILL.md` stays the source of truth.
- By default no compact rules are generated or injected. Author intent survives because
  subagents receive the exact skill paths.

## Decision Gates

| Case | Outcome |
|---|---|
| A delegation is about to happen | Pick the registry rows that match and pass on their `SKILL.md` paths |
| The scan finds nothing | Write the registry anyway, empty, so that agents quit hunting for skills that are not there |
| One name sits in several global locations | The source scanned first wins |
| One name exists both globally and in the project | The project-level skill wins |

## Execution Steps

1. Walk every known skill directory, user-level and project-level, collecting each
   `*/SKILL.md`.
2. Read only as much of each frontmatter as it takes to get the `name` and the trigger text
   in `description`.
3. Write the registry file: which sources were scanned, the contract the registry follows,
   and one row per skill with its name, its trigger (the `description` text), its scope and
   its exact path.
4. Where Engram is available, persist the same content as a memory whose `title` and
   `topic_key` are both `skill-registry`, with `type: config` and `capture_prompt: false`.
5. Finish by returning the registry path, how many skills it holds, the cache status, and
   whether Engram got updated.

## Output Contract

Reply with:
- the project name, and where the registry file lives;
- how many skills were indexed;
- cache status: hit, or regenerated;
- the skills that were skipped or turned out duplicated, when there are any.

## References

- `_shared/skill-resolver.md`: how delegators put the index to use.
- `docs/skill-style-guide.md`: how a skill should be written before it is indexed.
