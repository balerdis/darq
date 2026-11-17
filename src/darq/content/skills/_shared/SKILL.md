---
name: _shared
description: "Shared SDD references for installed skills. Not invokable."
disable-model-invocation: true
user-invocable: false
license: MIT
metadata:
  version: "1.0"
---

## What lives here

Reference files the SDD skills read while they run, `_shared/sdd-phase-common.md` and
`_shared/persistence-contract.md` among them. One of them, `_shared/sdd-session-preflight.md`,
is where SDD Session Preflight is defined: each SDD command insists on it, yet no command spells
it out itself.

## Never load as a skill

This folder only supports other skills. Nothing should invoke `_shared` as one.
