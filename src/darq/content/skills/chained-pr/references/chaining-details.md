# How a chain is put together

## Two strategies, side by side

Stacked PRs to main fit a change whose every slice is worth shipping by itself. The slices land on `main` one after another, so a slice ships as soon as its turn comes, and a bad slice is undone by reverting that single PR on `main`. The cost: `main` may hold part of a behavior for a while. Keeping the chain current is the lighter routine of retargeting and rebasing.

A Feature Branch Chain suits a change that must not reach `main` half finished. No slice reaches `main` before the last child is in and the tracker merges, so users get the feature in one piece, and undoing it means reverting or holding the whole feature branch. The cost: an extra PR, the tracker, and disciplined diffs, since each child may show its own slice and no other.

## Stacking onto main

Use it when each slice can reach `main` in its turn. Three slices look like this:

```text
PR 1  targets main            the groundwork
PR 2  targets PR 1's branch   a feature slice on top of it
PR 3  targets PR 2's branch   the tests and docs that follow
```

Once a parent has merged, rebase or retarget the next PR so that GitHub shows that PR's own slice only.

## Chaining through a feature branch

Children are reviewed one narrow slice at a time while the integrated result builds up on the tracker branch. A tracker branch `feat/invoices` with three children:

```text
branch                   created from              its PR targets
feat/invoices            main                      main (the tracker, draft, merged last)
feat/invoices-1-schema   feat/invoices             feat/invoices
feat/invoices-2-api      feat/invoices-1-schema    feat/invoices-1-schema
feat/invoices-3-ui       feat/invoices-2-api       feat/invoices-2-api
```

Setting it up:

1. Branch the tracker off `main`.
2. Open the tracker's PR against `main` and mark it as a draft that must not be merged.
3. Branch the first child off the tracker and open PR #1 with the tracker branch as its base.
4. Branch each later child off the branch of the PR before it, and open its PR with that parent branch as base.
5. Integrate the children in order. The tracker is merged only once the chain is complete.

## The section every chained PR body carries

Its title is `## Chain Context`. Add it to the PR body the repository's template produces; whatever issue link or checklist the template requires stays in place, and this section comes on top. Fill in every placeholder:

````markdown
## Chain Context

- Chain: <name of the feature or stack>
- Tracker PR: <#NNN, or "Not needed" for stacked PRs>
- Position: <N> of <total>
- Base: `<branch this PR targets>`
- Depends on: <earlier PR, issue or link, or "None">
- Follow-up: <the PR that comes next, or "None">
- Review budget: <changed lines> / 400
- Starts at: <the branch, PR or state this work builds on>
- Ends with: <the self-contained result this PR leaves behind>

### Chain Overview

```text
main
 └── #NNN earlier PR
      └── 📍 #NNN this PR
           └── #NNN later PR
```

### Scope

- Includes: <the one unit this PR delivers>
- Excludes: <work deferred to later PRs>

### Autonomy

- [ ] its branch should go green in CI
- [ ] it delivers one thing only
- [ ] reverting it takes nothing outside it along
- [ ] its unit is verified by tests, docs or a manual check
````

## The `gh` side

Write the body to a file first, `pr-body.md` in these examples, and pass it with `--body-file`.

- Size and title of an existing PR, to check its load: `gh pr view <PR_NUMBER> --json additions,deletions,changedFiles,title,url`
- First child, opened against the tracker: `gh pr create --base feat/invoices --title "feat(invoices): add the invoice schema" --body-file pr-body.md`
- Second child, opened against the first: `gh pr create --base feat/invoices-1-schema --title "feat(invoices): expose the invoice API" --body-file pr-body.md`

## When you review a chain

- Send back for splitting any PR over the 400-line budget that has no accepted `size:exception`.
- When the work has to be integrated before it reaches `main`, recommend a Feature Branch Chain; when each slice can be merged on its own, recommend Stacked PRs to main.
- Compare each child with its immediate parent branch: the branch right above it in the chain, which is `main` itself for the first PR of a stack or for a child already retargeted there. When a child's diff contains another link's work, that is a branching bug; fix it before reviewing further.
