---
name: skill-creator
description: "Trigger: new skills, agent instructions, documenting AI usage patterns. Create LLM-first skills with valid frontmatter."
license: Apache-2.0
metadata:
  version: "1.0"
---

## Activation Contract

A skill earns its place when a decision tree would help the AI choose well, when a complex
workflow needs its steps spelled out in order, when this project's conventions part ways with
generic best practice, or when the AI meets the same pattern again and again and needs
direction on it. Anything trivial or one-off, or better served by plain documentation, gets
no skill.

## Hard Rules

- Style authority, highest first. Inside this repo, `docs/skill-style-guide.md` is normative:
  read and follow it before you create or change any skill. For installed global skills where
  that file cannot be found, its bundled local copy,
  `skill-creator/references/skill-style-guide.md`, takes its place. When neither can be read,
  the inline rules at the end of this list are what you go by.
- The thing you are writing is a runtime instruction contract for an LLM; it is never
  documentation for people.
- Keep trigger words inside `description`. Never add a `Keywords` section.
- References lead to local files and nowhere else.
- Body length in tokens: 180 to 450 targeted, 700 at most by recommendation, 1000 at most
  without exception.
- Inline rules, the fallback when no guide is readable:
  - `description` MUST fit on one physical line, quoted and YAML-safe, with the essential
    trigger words leading. It SHOULD stay within 160 characters and MUST stay within 250.
  - The frontmatter MUST carry `name`, `description`, `license`, `metadata.author` and
    `metadata.version`.
  - Instructions are imperative; tutorials and background prose stay out.
  - Supporting material goes to `assets/` or `references/`, never the main body.
  - Right: `description: "Trigger: Jira task, ticket, issue, task creation. Create Jira tasks in the team format."`
  - Wrong: a folded `description: >` spread over several lines, or a separate
    `Keywords: jira, task` line.

## Decision Gates

| When you have | Do this |
|---|---|
| more than one meaningful path | add a compact decision table |
| a long explanation sitting in `SKILL.md` | move it into a supporting file |
| conceptual detail, edge cases, docs that already exist | link them locally from `references/` |
| code templates, schemas, fixtures or generated examples | put them in `assets/` |

## Execution Steps

1. Check for `docs/skill-style-guide.md`. Where it exists it governs, ahead of both the
   bundled copy and the inline rules.
2. Without that repo guide, read `skill-creator/references/skill-style-guide.md` and let it
   govern ahead of the inline rules.
3. Make sure no such skill exists yet and that the pattern is genuinely reusable.
4. In the target skill root, project-level or user-level, create or update
   `{skill-name}/SKILL.md`. Its directory holds `SKILL.md` (required, the main skill file),
   optionally `assets/` (templates, schemas, examples such as `template.py` or
   `schema.json`), and optionally `references/` (links to local docs, e.g. a `<concern>.md`
   that points to `docs/developer-guide/*.mdx`).
5. Give it frontmatter of this shape: `name: {skill-name}`;
   `description: "Trigger: {essential trigger words users or agents will say}. {What this skill does}."`;
   `license: Apache-2.0`; and a `metadata` map holding `author: "{your-github-username}"`
   and `version: "1.0"`.
6. Lay the body out as Activation Contract, Hard Rules, Decision Gates, Execution Steps,
   Output Contract, References, in that order.
7. A project skill also gets registered in `AGENTS.md`.

## Output Contract

Report back with:
- every file you created or modified;
- which rules you followed: the repo style guide, or the inline fallback rules;
- any change to the `AGENTS.md` registration;
- each supporting file you added under `assets/` or `references/`.

## References

- `docs/skill-style-guide.md`: the repo's normative style guide for LLM-first skills.
- `skill-creator/references/skill-style-guide.md`: its bundled local copy, for installed
  global skills when the repo doc is unavailable.
