---
name: cognitive-doc-design
description: "Design docs that reduce cognitive load. Trigger: writing guides, READMEs, RFCs, onboarding, architecture, or review-facing docs."
license: Apache-2.0
metadata:
  version: "1.0"
---

# Cognitive Doc Design

Every document asks its reader to hold something in mind. This skill keeps that demand small: the reader finds the point at once, can act on it, and can come back later without starting again from the top.

## Use it for

Creating or editing documentation that someone needs to grasp fast, keep in memory, or rely on while reviewing. In particular:

- a pull request description, or notes left for the people reviewing it;
- a guide for contributors or for maintainers;
- a write-up of an architecture, a workflow, or the first steps on the project;
- any existing document that has grown long or dense, or that resists skimming.

## How to write it

1. **Open with the conclusion.** The first lines carry the outcome, the decision, or what the reader must do. Background comes after them.
2. **Layer the depth (progressive disclosure).** Cover the ordinary path first; details, edge cases and pointers to further material follow it.
3. **Cut it into chunks.** Each short section holds one group of related facts, and flat lists stay short.
4. **Put up signposts.** Headings, labels, callouts and brief summaries show the reader where they stand.
5. **Favor recognition over recall.** What the reader can look up in a table, a checklist, an example or a template beats prose they must carry in their head.
6. **Spare the reviewer.** Someone reviewing the work should be able to confirm its intent without piecing its history back together.

## A starting skeleton

When the repository has no template of its own that serves the reader better, begin from this one:

```markdown
# <What the reader gets, stated as a result>

<A single paragraph: what is different now, who gains from it, and why that matters.>

## Start here

1. <The first thing to do>
2. <The thing after it>
3. <How to tell it worked: a check or the result to expect>

## Decisions

| Topic | Decision |
| --- | --- |
| <area> | <a line or two on what was decided and why> |

## Confirm

- [ ] <A point the reader can confirm>
- [ ] <Another point>

## Then

<The link or the action that carries the work forward.>
```

## Pull request descriptions and review notes

Reviewers tire fast when they must find their own way through a change, so lay the way out for them:

- Point to where the review should begin.
- Name what the change deliberately leaves out.
- When the PR is one link of a chain, link the PR before it and the PR after it.
- Give each section a single decision or a single unit of work.
- Turn acceptance criteria and verification steps into checklists.

## Commands that help

- `git diff --name-only -- '*.md'` lists the Markdown files in the working tree whose changes are not staged yet.
- `gh pr view <PR_NUMBER> --json additions,deletions,changedFiles` gives the size of a PR in changed lines, a rough gauge of how much it asks of its reviewers.
