---
name: issue-creation
description: "Create GitHub issues with issue-first checks. Trigger: creating GitHub issues, bug reports, or feature requests."
license: Apache-2.0
metadata:
  version: "1.0"
---

# Filing a GitHub issue

An issue is filed in the repository you are working in, never in another one, and under that repository's own setup: its templates, its labels, its approval gate and its Discussions, each of which you read before writing anything.

## Situations this covers

- Opening an issue, whether it reports a bug or asks for a feature.
- Helping a contributor put an issue together.
- Triaging issues, or approving them, as a maintainer.

## What always holds

- **The setup is read first**, from the repository being worked in (see "Reading the setup").
- **A repository with issue templates gets one of them.** When it has blank issues turned off, using a template is mandatory.
- **An approval label gates PRs.** If the repository uses one (`status:approved`, for instance), no PR may be opened until a maintainer has added it.
- **Questions belong in Discussions** when the repository has them turned on, not in an issue.

## Reading the setup

Run these from the repository being worked in; when the working directory is some other repository, add `--repo OWNER/REPO`.

- `gh repo view --json nameWithOwner,url,isBlankIssuesEnabled,hasDiscussionsEnabled,issueTemplates` reports the templates, whether blank issues are allowed, whether Discussions are on, and the repository URL.
- `gh label list` reports the labels the repository defines.

How to read the answer:

- Every entry of `issueTemplates` has a `name`, and that `name` is the value `gh issue create --template` expects.
- With `hasDiscussionsEnabled` true, Discussions live at the repository's `url` plus `/discussions`.
- Labels come only from what `gh label list` returned. A status label the repository does not define is never made up.

## From check to submission

1. Read the setup: templates, blank issues, Discussions, labels.
2. Look through the existing issues for a duplicate.
3. Pick the template that matches: bug report, feature request, or the repository's own equivalent.
4. Answer every required field the template declares, all of them.
5. Tick the pre-flight checkboxes, when the template has any.
6. Submit. The labels the template declares, such as `status:needs-review`, are added automatically.
7. If the repository uses an approval label, wait until a maintainer adds it.
8. Only after that, open the PR that links this issue.

## What templates usually look like

The two shapes below are common, nothing more. The repository's own templates, read during setup, always win: fill in the fields they declare and pass the template names they carry.

### A bug report

It usually lives at `.github/ISSUE_TEMPLATE/bug_report.yml`, and whatever labels it declares are applied on creation (often `bug` and `status:needs-review`).

#### Fields

Its required fields are typically **Pre-flight Checks** (checkboxes: no duplicate exists, the approval workflow is understood), **Bug Description**, **Steps to Reproduce** (numbered), **Expected Behavior**, **Actual Behavior** (errors and logs included), and dropdowns describing the environment: **Operating System** (for example macOS, Linux variants, Windows, WSL), the agent or client in use (as many options as the template lists, plus Other), and **Shell** (for example bash, zsh, fish, Other). A dropdown is answered with one of the options it lists. **Relevant Logs** (rendered as a code block) and **Additional Context** (screenshots, workarounds, anything else) are usually optional.

Filed from the command line, the body repeats the template's field labels as headings:

```bash
gh issue create --template "<bug report template name>" \
  --title "fix(export): CSV export drops rows with an empty date" \
  --body "
### Pre-flight Checks
- [x] No open or closed issue already reports this
- [x] I know a PR can only follow once this issue has status:approved

### Bug Description
Exporting a report to CSV leaves out every row whose date field is empty.

### Steps to Reproduce
1. Create a report with one row that has no date
2. Export it to CSV
3. Open the file: that row is missing

### Expected Behavior
Every row is exported, with an empty date cell where there is no date.

### Actual Behavior
Rows without a date are silently skipped.

### Operating System
Linux
"
```

### A feature request

It usually lives at `.github/ISSUE_TEMPLATE/feature_request.yml`, with its declared labels (often `enhancement` and `status:needs-review`) applied on creation.

#### Fields

Besides the same **Pre-flight Checks**, its required fields are typically **Problem Description** (the pain the feature removes), **Proposed Solution** (how it should work from the user's side) and **Affected Area** (a dropdown of the parts of the project, as the repository names them). **Alternatives Considered** and **Additional Context** (mockups, examples, references) are usually optional. It is filed the same way as a bug report: `gh issue create --template "<feature request template name>" --title "feat(scope): description" --body "..."`, with one `### <field label>` heading per field in the body.

## Labels

Labels exist only as the repository defines them (`gh label list`). In a frequent arrangement:

- The templates add a type label and a review label when the issue is created: `bug` or `enhancement`, together with `status:needs-review`.
- Maintainers add `status:approved` once an issue is accepted for implementation, which is what allows PRs to be opened.
- Maintainers also set a priority: `priority:high` for a critical bug or urgent feature, `priority:medium` for something important that blocks nothing, `priority:low` for a nice-to-have.

## Approving issues as a maintainer

Where the repository uses an approval label:

1. A new issue arrives labelled `status:needs-review`.
2. The maintainer judges it: is it valid, clearly described, and within scope?
3. If so, they add `status:approved`.
4. If not, they reply with the reason and close it when that is warranted.
5. The contributor may then open a PR that links the issue.

## Choosing where something goes

| It is | It goes to |
|---|---|
| a bug | the bug report template |
| a new feature or an improvement | the feature request template |
| a question | the repository's Discussions, when enabled, not an issue |
| a duplicate | a link to the existing issue, then closed |

## Command reference

- Read the setup: `gh repo view --json nameWithOwner,url,isBlankIssuesEnabled,hasDiscussionsEnabled,issueTemplates` and `gh label list`
- Look for duplicates before filing: `gh issue list --search "keyword"`
- File a bug report: `gh issue create --template "<bug report template name>" --title "fix(scope): description"`
- File a feature request: `gh issue create --template "<feature request template name>" --title "feat(scope): description"`
- As a maintainer, approve an issue: `gh issue edit <number> --add-label "status:approved"`
- As a maintainer, set a priority: `gh issue edit <number> --add-label "priority:high"`
