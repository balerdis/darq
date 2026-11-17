---
name: work-unit-commits
description: "Plan commits as reviewable work units. Trigger: implementation, commit splitting, chained PRs, or keeping tests and docs with code."
license: Apache-2.0
metadata:
  version: "1.0"
---

# Work-unit commits

A work unit is the smallest part of a change that delivers something by itself: a behavior, a fix, a migration, or a piece of documentation. With this skill each commit holds exactly one such unit. Every commit can then be reviewed, tested and reverted on its own, and a branch that grows too large can be divided into pull requests along boundaries that already exist.

## Use it when

You are deciding what goes into each commit or pull request, in particular when you:

- divide a feature into pieces a reviewer can follow;
- prepare the commits of a branch before its pull request is opened;
- need a big change to become a chain or a stack of pull requests;
- want to keep down how much a reviewer has to hold in mind at once;
- apply SDD tasks and must not end up with a pull request above 400 changed lines.

## Where to cut

- Do not cut by file type or layer when none of the resulting pieces works alone. Data models in one commit, services in the next and tests in a third give the reviewer three pieces, none of which works alone; put the model, the service code and the tests that together deliver one behavior in a single commit instead.
- A test travels in the same commit as the behavior it checks.
- Documentation travels with the user-visible change or workflow it describes.
- Read in order, the commits tell the story of the change: from each diff and its message, a reviewer can see why that commit exists.
- Treat every commit as a pull request in waiting. If the change outgrows the budget, one commit, or a small group of them, becomes one link of a chain without being reworked.
- When SDD tasks forecast a change above 400 lines, group the planned commits into chained pull request slices before implementation starts, not after the work is done.

## An example

A reports page gains a CSV export. Divided by layer, the history reads `add models`, then `add services`, then `add tests`, then `update docs`. No commit in it produces a working export, and the tests arrive after the code they were meant to check. Divided by work unit:

- `feat(reports): turn a report into CSV rows, with unit tests`
- `feat(reports): serve the CSV download from the reports endpoint, with its integration test`
- `feat(reports): add the export button and describe it in the user guide`

Each of these builds and passes its own tests, each message names what changed for the user or the system, and each one is a natural place to end a pull request.

## Before each commit

Confirm that:

1. the commit has a single purpose you can state in one sentence;
2. the repository still makes sense with this commit applied and nothing after it;
3. the tests or documentation this unit needs are part of it, where the unit needs any;
4. reverting it would not force reverting unrelated work;
5. the message says what the commit achieves, not which files it touches.

Then record the unit's evidence:

- the focused test command, with its exact result;
- the runtime harness command or scenario, with its exact result, or an explicit `N/A` together with the reason no runtime boundary exists;
- the rollback boundary: the exact files or behavior that can be taken out without taking out unrelated work.

## From commits to pull requests

A chain of pull requests is built out of work-unit commits. The loop is: build the smallest unit that stands alone, add the verification for it, commit it with a Conventional Commit message, and repeat. Once a pull request gets close to 400 changed lines, lift one commit, or a run of them, out into its own link of a chain.

## Inside SDD

The risk level in the Review Workload Forecast that `sdd-tasks` writes decides the handling:

| Forecast risk | What to do |
|---|---|
| Low | Keep the work-unit commits together in one pull request. |
| Medium | Still commit by work unit, and watch the changed-line count before the pull request is created. |
| High | Do what the SDD `Delivery strategy` says: on `ask-on-risk`, ask; on `auto-chain`, slice automatically; on `single-pr` over the budget, require a `size:exception`; on `exception-ok`, record the accepted `size:exception`. |

For the `>400` threshold, count what was authored: lines added plus lines deleted. Generated goldens do not count toward it, but each generated file is still part of the unit's complete snapshot identity.

Each SDD work unit should line up with one commit or one pull request, having a known starting state, a known finished state, verification inside the same unit, and a rollback that takes nothing unrelated with it. As implementation evidence it MUST carry the three items listed under "Before each commit": the focused test command and its exact result, the runtime harness command or scenario and its exact result (or `N/A` and why there is no runtime boundary), and the rollback boundary. The rollback boundary is stated independently of whether a commit was created: a unit still sitting uncommitted in the working tree owes it all the same.

## Commands worth running

Before committing, read the story the diff tells: `git diff --stat` summarizes what is not yet staged, and `git diff --cached --stat` what is. To match the commit style the history already uses, look at the last few subjects with `git log --oneline -5`.
