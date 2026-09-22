# SDD Applicability

## Scope

Owns one question and only that one: **is this request SDD work at all?** Everything downstream of a
"yes" already has an owner — `_shared/sdd-session-preflight.md` owns what preflight is and when it
runs, `_shared/sdd-phase-common.md` owns what a phase does once it is launched. Nothing owned the
question above them, so in practice every request was treated as a "yes" and a person who wanted one
thing looked at was asked to initialise a change first.

## Authority

Canonical owner of the SDD/not-SDD decision: the signals on each side, the ambiguous cases, and what
to do when work that started loose grows until it deserves the full cycle. Whatever governs a given
caller — an orchestrator body, a command file — owns only the compact IF, the clear cases that
resolve without reading anything, and points here for the rest.

This file never softens a gate. Once the answer is SDD, preflight and the init guard apply in full,
exactly as their own owners define them.

## It is not SDD when

- One question is being asked about the codebase, and an answer ends it.
- One check is being asked for — run this, does it still pass, what does it print.
- One change is already decided, scoped and small, and nobody is arguing about the approach.
- Someone is mid-conversation and wants a fact, not a cycle.
- The person said explicitly that they do not want the flow.

## It is SDD when

- The change needs a shape agreed before code: requirements, an approach worth arguing, trade-offs.
- It spans several work units that have to land in order, or across several sessions.
- A written record has to survive the session — specs to verify against, a task list someone else
  will pick up, an archive someone will read next quarter.
- Someone asked for it by name, by command or in their own words.
- The work will be reviewed against a contract rather than against a diff.

## Ambiguous cases

These are the ones that actually come up. Resolve them by asking what the OUTPUT has to be, never by
size alone:

- **A small change to a contract everyone depends on.** Two lines can still need a spec. If the
  output is an agreement, it is SDD; if the output is the two lines, it is not.
- **A bug fix with an unclear cause.** Investigate first as ordinary work. If the cause turns out to
  be a design decision that has to change, that is the moment it becomes SDD, not before.
- **"Refactor X".** Not SDD when the behaviour is fixed and the tests already state it. SDD when the
  refactor is really a redesign wearing a smaller word.
- **A request with a deadline attached.** Urgency changes nothing here; the flow is chosen by what
  the work needs, and saying so plainly beats skipping a cycle the work will need anyway.
- **Genuinely undecidable.** Ask, in one line, naming both options and what each costs. Do not
  silently pick the heavier one because it is the safer thing to be wrong about — a cycle nobody
  wanted is a real cost paid by a real person.

## When work grows into SDD mid-flight

Work that started as one question and turned into a change worth specifying is the common case, not a
mistake. Do not retrofit: the loose work already done is not wasted, it is the exploration.
Name the moment out loud, propose the switch, and resolve preflight then — the gates apply from
that point forward, never retroactively to work already delivered. If the person declines, keep going as
ordinary work and say what will be missing without the cycle.

## Fail-open

This file decides a route, never whether work happens. If it is missing or unreadable, judge from the
clear cases you already carry, say which way you judged and why, and proceed — a router nobody can
read is not a reason to refuse the request, and it is not licence to skip a gate that does apply once
the answer is SDD.
