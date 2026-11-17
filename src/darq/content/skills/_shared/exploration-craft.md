# Exploration Craft

## Scope

Owns how to explore a codebase or an idea well — the investigation method, the way to compare
approaches, and the report discipline — independent of any change-lifecycle machinery. An agent
with no SDD context can follow this file on its own; it says nothing about artifact stores, phase
envelopes, or what happens after the report is handed back.

## Authority

This file is the canonical owner of the exploration method: how to understand a request, how to
investigate real code instead of guessing, how to compare competing approaches, and the shape of a
concise exploration report. A calling skill states when exploration runs and what to do with the
result; it does not restate how to explore.

## Pin down the question first

Before you open a single file, work out what is really being asked. Is it a new feature, a bug fix
or a refactor, and which domain does it reach into?

## Look at the code itself

The point of reading is to learn four things: the architecture and patterns in place today, which
files and modules the request would touch, what the code already does that bears on it, and where
constraints or risks may lie. Cover all of it:

```
INVESTIGATE:
- entry points and the files that matter most: read them
- functionality related to the request: search for it
- existing tests, if there are any: check them
- patterns the code already follows: look for them
- dependencies and coupling: identify them
```

## Weigh the options

When there is more than one way to do it, set the candidates next to each other, each with its pros,
its cons and its complexity (Low, Med or High):

| Option | Pros | Cons | Complexity |
|---|---|---|---|
| A | … | … | Low, Med or High |
| B | … | … | Low, Med or High |

## Report Shape

A concise exploration report carries these sections, in order:

- **Current State** — how the system works today, as it relates to this topic.
- **Affected Areas** — one line per file or module, each naming why it is affected.
- **Approaches** — each with a name, a one-line description, its pros, its cons, and an effort of
  Low, Medium or High.
- **Recommendation** — the approach you would take, and why.
- **Risks** — what could go wrong, one line each.

The heading these sections are returned under is not this file's to choose. A phase skill names the
envelope its phase must emit; an agent with no phase returns the same sections under whatever its own
result identity defines. A caller that wraps this report in a larger contract (a phase envelope, a
next-step field, a persistence rule) appends to this shape; it does not need to replace it.

## Exploration Rules

- Exploring changes nothing: no existing code or file is modified; you investigate and you report
- Base every claim on code you actually read; never guess what the codebase does
- Be brief: the reader wants a summary, not a long account
- When the information you can find is not enough, say so plainly
- When the request is too vague to explore, name the clarification you need
