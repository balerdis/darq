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

## Understand the Request

Before touching the codebase, parse what is actually being asked:

- Is this a new feature? A bug fix? A refactor?
- What domain does it touch?

## Investigate the Codebase

Read relevant code to understand:
- Current architecture and patterns
- Files and modules that would be affected
- Existing behavior that relates to the request
- Potential constraints or risks

```
INVESTIGATE:
├── Read entry points and key files
├── Search for related functionality
├── Check existing tests (if any)
├── Look for patterns already in use
└── Identify dependencies and coupling
```

## Analyze Options

If there are multiple approaches, compare them:

| Approach | Pros | Cons | Complexity |
|----------|------|------|------------|
| Option A | ... | ... | Low/Med/High |
| Option B | ... | ... | Low/Med/High |

## Report Shape

A concise exploration report carries these sections, in order:

```markdown
## Exploration: {topic}

### Current State
{How the system works today relevant to this topic}

### Affected Areas
- `path/to/file.ext` — {why it's affected}
- `path/to/other.ext` — {why it's affected}

### Approaches
1. **{Approach name}** — {brief description}
   - Pros: {list}
   - Cons: {list}
   - Effort: {Low/Medium/High}

2. **{Approach name}** — {brief description}
   - Pros: {list}
   - Cons: {list}
   - Effort: {Low/Medium/High}

### Recommendation
{Your recommended approach and why}

### Risks
- {Risk 1}
- {Risk 2}
```

A caller that wraps this report in a larger contract (a phase envelope, a next-step field, a
persistence rule) appends to this shape; it does not need to replace it.

## Rules

- Do not modify any existing code or files while exploring — exploration only investigates and reports
- Always read real code, never guess about the codebase
- Keep your analysis concise — the reader needs a summary, not a novel
- If you can't find enough information, say so clearly
- If the request is too vague to explore, say what clarification is needed
