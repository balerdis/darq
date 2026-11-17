---
name: chained-pr
description: "Trigger: PRs over 400 lines, stacked PRs, review slices. Split oversized changes into chained PRs that protect review focus."
license: Apache-2.0
metadata:
  version: "1.0"
---

A chain swaps one oversized pull request for a sequence of small ones, reviewed in order. Every link carries a single work unit, declares where it starts and where it stops, and shows the reviewer its own diff and nothing else.

## Activation Contract

Pull this skill in for any of these:

- the PR being planned looks set to pass **400 changed lines**;
- a forecast from SDD reads `400-line budget risk: High` or `Chained PRs recommended: Yes`;
- the person wants chained or stacked PRs, wants the work cut into review slices, or wants the reviewer's load kept down.

## Hard Rules

- Once the person picks a strategy, the whole chain uses it, from the first branch to the last PR. Switching part way, or mixing the two, is not allowed.
- A diff that shows commits belonging to another unit points to a wrong base. Treat it as a bug: rebase or retarget until nothing but the current unit is left.
- Feature Branch Chain: the tracker PR stays a draft that is never merged on its own; child 1 is based on the tracker branch, and every later child on the branch of the child just before it.
- A child PR's body always holds a diagram of the chain's dependencies, with `📍` on the PR you are looking at.
- Every PR body in the chain says where the work starts, where it ends, which earlier PRs it needs, what follow-up comes next, and what it leaves out on purpose.
- One work unit per PR, with the tests and docs that prove that unit travelling alongside it.
- Size each PR so a reviewer gets through it in an hour at most (**≤60 minutes**).
- Past 400 changed lines, split, unless a maintainer has said yes to `size:exception` for that PR in so many words.

## Decision Gates

Count the lines that change and name the work units first. Then:

- SDD artifacts that already state a `Delivery strategy`: follow it, and do so before apply begins and before any PR exists.
- At most 400 lines and a single topic: keep one PR, no chain.
- Above 400, with slices that are each worth landing on their own: Stacked PRs to main.
- Above 400, with a feature that must come together before any of it reaches `main`: Feature Branch Chain, tracker PR included.
- Generated output, vendored code or a migration that cannot be cut cleanly: do not split; request `size:exception` from a maintainer.

## Execution Steps

1. Work out the size of the change and which parts of it stand alone.
2. Decide the strategy. If the size is over budget and nothing has been chosen or cached, put the question to the person; never decide it for them.
3. Open exactly the branches and PRs that strategy calls for.
4. Start each PR body from the repository's own template and append the Chain Context section; whatever the template requires stays where it is.
5. Verify every PR by itself: CI, tests, docs or a manual check, a rollback confined to its unit, and a diff with nothing foreign in it.
6. Leave the tracker as an unmerged draft until all of its children are reviewed and in.

## Output Contract

Hand back: the strategy; the PR sequence; the boundary of the PR at hand; the dependency diagram; the verification plan for each PR; the review budget counted as `additions + deletions`; and, for any `size:exception`, why it is justified.

## References

`chained-pr/references/chaining-details.md`: how the two strategies compare, their branch layouts and setup, the Chain Context section, the `gh` commands, and what reviewers check.
