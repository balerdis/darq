# Skill Authoring Guide

Skills in this repo are written for a model, not for people. Each one is a runtime contract
the LLM reads to find out when it applies, what may never be broken, how to choose between
paths, what to do, and what to give back. Follow this guide to write a new skill here or to
rework an old one.

## How a Skill Is Found and Read

Indexing is done by `external registry refresh`, which neither summarizes nor rewrites
anything. Per skill it stores four facts: its `name`, the trigger text in `description`, its
scope, and the exact path of its `SKILL.md`. A delegator passes the matching paths on to its
subagents, and every subagent reads the entire skill before doing any work. Because the whole
file is always what gets read, and it is the source of truth, no `## Compact Rules` section is
required. Auditing or refactoring an existing skill against this guide is the job of
`skill-improver`.

## Frontmatter

Discovery works from the frontmatter alone, so a `Keywords` section must NOT be added. Fill
in `name`, `description` and `license`, plus `author` and `version` under `metadata`. The
`description`:
- is quoted, YAML-safe, and written on one physical line;
- opens with its trigger words, as in `"Trigger: ... . {What the skill does}."`;
- SHOULD stay at or under 160 characters and MUST stay at or under 250.

## Length

The body has a budget in tokens: 180 to 450 is the goal, 700 the recommended ceiling, 1000
the absolute one. Whatever does not fit (examples, schemas, background) moves out. Templates,
schemas, fixtures and generated examples go to `assets/`; local documents that explain a
concept or an edge case go to `references/`. Keep reference paths stable, and relative to the
skill directory where you can.

## Body Layout

Every `SKILL.md` MUST follow this order, leaving a part out only when it is truly irrelevant:

1. Frontmatter: all the metadata discovery needs.
2. Activation Contract: exactly which situations load the skill.
3. Hard Rules: what the LLM MUST NOT violate.
4. Decision Gates: a short table or bullet list for each fork.
5. Execution Steps: the workflow, step by step.
6. Output Contract: the final format, or the artifacts expected back.
7. References: local files only; detail lives there, not in the skill.

## Phrasing

| Write | Not |
|---|---|
| imperative runtime instructions ("Load X", "Check Y", "Return Z") | history, motivation, or tutorial background |
| the activation trigger and hard constraints at the top | a critical rule hidden beneath examples |
| decision gates as compact tables | generic advice the LLM has no way to execute |
| the smallest example that still runs | long docs pasted into the skill |
| links to local supporting files for the detail | external URLs as the primary references |

## Before It Ships

Each of these holds:
- the frontmatter is complete, with a quoted single-line `description` and its trigger words intact;
- all required sections are present, in the order given above;
- every hard rule can be tested or observed;
- decision gates appear only where a fork matters;
- the output contract says exactly what the LLM returns;
- references go to local files only.

## When Reworking a Skill

- [ ] Move explanatory prose out into local references.
- [ ] Fold repeated rules into one hard rule.
- [ ] Turn branches described in prose into a decision table.
- [ ] Shrink each example to the smallest useful case.
- [ ] Re-check the description's length and its trigger words.
