---
name: skill-improver
description: "Trigger: improve skills, audit skills, refactor skills, skill quality. Audit and upgrade existing LLM-first skills."
license: Apache-2.0
metadata:
  version: "1.0"
---

## Activation Contract

`SKILL.md` files that already exist, and that someone wants audited, refactored, normalized
or improved, are this skill's territory. A brand-new skill drawn out of a pattern worth
reusing is not: that belongs to `skill-creator`.

## Hard Rules

- Audit only, by default. Change files only once the user explicitly asks for the
  improvements to be applied.
- Nothing meaningful disappears without a word: long explanations, examples, templates and
  schemas move into local `references/` or `assets/` instead of being cut.
- Never make up triggers, policies or domain rules. Flag anything ambiguous for a human to
  review.
- The skill's own `SKILL.md` is the source of truth. What its author meant, its critical
  rules, how it activates and what it must output all survive your edits.
- `.atl/skill-registry.md` lists each skill's name, trigger, scope and exact path, and that
  is all it is. Do not expect summaries generated from the skills in it.
- Style contract: `docs/skill-style-guide.md` is normative wherever it exists. For installed
  global skills without it, the bundled local copy,
  `skill-improver/references/skill-style-guide.md`, takes its place.

## Decision Gates

| Finding | Response |
|---|---|
| Rules contradict each other, or the intent is unclear | Report it and leave that rule as it is; no automatic rewrite |
| Branching logic buried in prose | Turn it into a compact decision table |
| Body over budget | Keep every rule; move examples and background into supporting files |
| Reads like tutorial documentation | Recast it as runtime instructions, with background moved to `references/` |
| Frontmatter missing or invalid | Repair it: `name`, `license`, `metadata`, and a `description` that is quoted and on one line |

## Execution Steps

1. Load the style contract: `docs/skill-style-guide.md`, or failing that
   `skill-improver/references/skill-style-guide.md`. Should neither exist, hold every skill
   to the core LLM-first structure instead, which is frontmatter followed by Activation
   Contract, Hard Rules, Decision Gates, Execution Steps, Output Contract and References.
2. Pick the skills to review from the paths `.atl/skill-registry.md` lists. No registry
   file? Then look through the known skill directories for any `*/SKILL.md`.
3. Go over each chosen skill: its metadata and how clearly its trigger reads; whether its
   sections come in order and its body fits the budget; whether it is actionable, with sound
   decision gates and an output contract; and whether every reference is local.
4. Report per skill, giving each finding a severity and the exact change you propose.
5. Only in apply mode: fix the safe issues and nothing else, keep the content intact, add
   supporting files where they are needed, then rerun `external registry refresh` or ask for
   it to be run.

## Output Contract

Hand back:
- which skills you audited, and the paths you used for them;
- the issues, sorted into severity groups;
- the files you changed, if you were asked to apply changes;
- a suggestion to refresh the registry whenever a skill's metadata or path changed;
- anything ambiguous, left for a human to review.

## References

- `skill-improver/references/skill-style-guide.md`: the bundled local copy of the style
  guide, for installed global skills when the repo has no such doc.
- `docs/skill-style-guide.md`: the repo's own normative style guide for LLM-first skills.
