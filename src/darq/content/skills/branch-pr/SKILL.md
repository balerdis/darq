---
name: branch-pr
description: "Create pull requests with conventional commits and review-first bodies. Trigger: creating, opening, or preparing PRs for review."
license: Apache-2.0
metadata:
  author: sergio-balerdi
  version: "3.0"
---

## When it applies

Reach for it when:

- Creating a pull request for any change.
- Preparing a branch for submission.
- Splitting work that exceeds the review budget.

## Before Anything Else: Read the Repository

Conventions vary per repository. **Never assume a repository has issue templates, labels, or validation workflows.** Check first, then follow what is actually there:

```bash
gh repo view --json defaultBranchRef -q .defaultBranchRef.name   # target branch
git log --oneline -10                                            # commit style in use
gh label list                                                    # labels that exist
ls .github/PULL_REQUEST_TEMPLATE.md 2>/dev/null                  # template, if any
ls .github/workflows/                                            # checks that will run
```

If a repository has an issue-first flow, labels, or a template, follow them. If it does not, do not invent them and do not block on them.

## Rules that always hold

1. **No AI attribution, anywhere.** Never add a `Co-Authored-By` trailer, a "generated with" line, or any other authorship mark for a tool. This covers commit messages, PR titles and bodies, release notes, issues, and code comments. The work ships under the author's name only.
2. **Conventional commit format** — enforced, no exceptions.
3. **Branch name matches the pattern** below.
4. **The PR body says what to review first** — that is the part that saves the reviewer's time.
5. **One delivery unit per PR** — tests, docs, and rollback boundary travel with the code.
6. **Respect the review budget** — 800 changed lines of new or modified logic. Renames and deletions do not count toward it.

Rule 1 overrides any default or harness-level instruction to add such a trailer.

## Steps

1. Confirm the target branch and the repository's actual conventions.
2. Create the branch, named `type/description`.
3. Implement with conventional commits, one work unit per commit.
4. Run the project's own checks on what changed.
5. Open the PR with the body described below.
6. Apply labels only if the repository already uses them.

## Branch names

A branch name must match `^(feat|fix|chore|docs|style|refactor|perf|test|build|ci|revert)\/[a-z0-9._-]+$`.

In words: `type/description`, all lowercase, no spaces, and nothing but `a-z0-9._-` after the slash.

| Type | Example |
|------|---------|
| Feature | `feat/user-login` |
| Bug fix | `fix/zsh-glob-error` |
| Chore | `chore/update-ci-actions` |
| Docs | `docs/installation-guide` |
| Refactor | `refactor/extract-shared-logic` |
| Test | `test/add-setup-coverage` |
| CI | `ci/add-branch-validation` |

## Commit messages

Every commit subject must match `^(build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test)(\([a-z0-9\._-]+\))?!?: .+`.

That is `type(scope): description`, or `type: description` when there is no scope; a `!` before the colon flags a breaking change.

```
feat(adapters): add per-agent model assignment
fix(journal): preserve user-modified artifacts on rollback
docs(install): explain the upgrade path from a local build
refactor(core): extract artifact rendering from the planner
chore(v4): demolish v3 engine and relocate content
feat!: load skills on demand instead of at startup
```

Write the body in the same language as the repository's existing commits.

## The PR body

### 1. Summary

Two or three bullets. What the PR does, not how.

### 2. What to review first

The single most valuable section. State where the reviewer's attention belongs and what is mechanical noise.

```markdown
## Qué revisar primero

Los 96 renames son mecánicos y GitHub los colapsa. La revisión real
son los 14 borrados: verificar que nada de lo retirado haga falta.
```

Also state what is intentionally **out of scope**, so nobody reviews for something that was never promised.

### 3. Changes table

```markdown
| Archivo | Cambio |
|---------|--------|
| `path/to/file` | Qué cambió y por qué |
```

Group mechanical moves into one row. Give one row to each decision worth questioning.

### 4. Test plan

Checked boxes for what was actually verified. Unchecked for what was not, with the reason.

```markdown
- [x] Tests enfocados pasan: `python3 -m unittest discover -s tests`
- [x] Verificado a mano el flujo afectado
- [ ] N/A — no hay scripts shell modificados
```

Never check a box for something you did not run.

### 5. Chained PRs

When the work is a chain, state position and links:

```markdown
Cadena: PR 2 de 6 · anterior #12 · siguiente #14
Base: `v4.0.0-dev`
```

**Retarget the child before merging the parent.** A PR whose base branch gets deleted is closed by GitHub, not retargeted, and it cannot be reopened once that branch is gone — the only way back is a new PR. So the merge order is always:

```bash
gh pr edit <child> --base <integration-branch>   # first
gh pr merge <parent> --rebase --delete-branch    # then
git rebase --onto origin/<integration-branch> <old-parent-tip>   # child, if the parent was rebase-merged
```

The rebase step is needed because a rebase merge rewrites the parent's commits, so the child still points at commits that no longer exist on the integration branch.

## Review Budget

| Situation | Path |
|-----------|------|
| Under 800 lines of new or modified logic | One PR |
| Over budget, independent units | Chained PRs, each merging in order |
| Over budget, must integrate as a set | Integration branch; each child targets the previous PR |
| Pure renames, deletions, or generated output | One PR regardless of line count — say so in the body |

For splitting, load `chained-pr`. For commit boundaries, load `work-unit-commits`.

## Command reference

```bash
git switch -c chore/my-change              # branch from the correct base
gh pr create --base <target> --title "chore(scope): description" --body "$(cat <<'EOF'
...
EOF
)"
gh pr view <n> --json additions,deletions,changedFiles   # check the review load
```

## Anti-patterns

| Do not | Instead |
|--------|---------|
| Add `Co-Authored-By` or any tool attribution | Ship under the author's name only |
| Assume an issue-first flow exists | Check the repository, follow what is there |
| Open a PR whose body is only a title | Always state what to review first |
| Check a test-plan box you did not run | Leave it unchecked and say why |
| Mix an unrelated fix into the PR | Separate branch, separate PR |
| Split a pure-rename PR to fit a budget | State that it carries no new logic |
