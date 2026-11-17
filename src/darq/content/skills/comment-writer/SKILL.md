---
name: comment-writer
description: "Write warm, direct collaboration comments. Trigger: PR feedback, issue replies, reviews, Slack messages, or GitHub comments."
license: Apache-2.0
metadata:
  version: "1.0"
---

# Comment Writer

A comment is read by a person who has other work waiting. This skill makes each comment worth that person's time: it says what matters first, gives the reason when one is needed, and ends with what to do.

## When it applies

Whenever you write a comment another person will read, among them:

- comments on a GitHub pull request or issue;
- review feedback, including a request for changes;
- replies written as a maintainer;
- project updates sent in Slack, Discord or another asynchronous channel.

## Building a comment

Assemble it from three parts, in this order, and leave out the middle one when the reason is already obvious:

1. What you observed, or what you are asking for, stated plainly.
2. Why it matters.
3. The concrete step that should happen next.

## Tone and length

- Put the point someone can act on in the opening sentence. Do not retell the pull request before reaching your feedback.
- Write the way a considerate colleague talks: friendly and plain, never in the voice of a corporate announcement.
- Stay brief: one to three short paragraphs, or a compact list.
- Every request for a change carries its technical reason.
- Raise the issue that matters most, and let minor preferences go instead of stacking them up.
- Use no em dashes; a comma, a period or parentheses do the same job.

## Which language to write in

By default the comment takes the language of the place where it is posted:

- In an issue or thread written in Spanish, write in Spanish; in one written in English, write in English.
- When a thread mixes languages, use the language of the message your comment is aimed at.
- If the person explicitly asks for a particular language or tone, that request takes precedence.
- A Spanish comment is in neutral, professional Spanish, unless the person or the thread clearly calls for a regional tone.

## Sample comments

Asking for a change:

```text
The retry loop in `syncOrders` has no upper bound, so a server that keeps answering 503 holds the worker forever.

Please cap it at five attempts with a growing delay, and log the last failure.
```

Approving with a remark:

```text
Looks good to merge: it fixes the timeout and nothing beyond it.

Not blocking: this is one link of a chain, so the next PR should link this one and the one after it, which keeps the chain easy to walk.
```

Asking for a split:

```text
This one is over our 400-line review budget. Please break it up, or explain why it has to land whole so we can agree on a `size:exception`.

A cut that would review well: the data model and its tests first, then the API built on it, then the docs. Each review then has a clear beginning and end.
```

## Before commenting on a PR

Read its title, description and size first:

`gh pr view <PR_NUMBER> --json title,body,additions,deletions,changedFiles`
