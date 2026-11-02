# Architecture review — 2026-10-28 — rule 5, "no process launch at import" (backlog #382)

**Convened by THRASHING** (`docs/dev-process.md`): rounds 2 and 3 of `wrap-every-selftest` both carry findings caused by
the previous round's own fix, in one component — rule 5 of `scripts/check-fixture-git-isolation.py`. Round 2's escapes
(annotated assignment, walrus, unpacking, aliased `import_module`, assignment targets) came from round 1's static
extension; round 3's (a context-conditional launch, `sitecustomize`/`.pth` before the hook, native `system()` through
`ctypes`/CFFI) came from round 2's audit-hook redesign.

## The wall, named once

This is the third subject in two days to hit it (`architecture-review-2026-10-27-fixture-guard.md`, `…-em-guard.md`):
**a guard that tries to PROVE A NEGATIVE about arbitrary code — "this never launches", "this always renders readable",
"this never writes another repository" — from inside the language, by syntax or by in-process observation, has an
outside.** Syntax has more spellings than any deny-list; an in-process hook has startup code before it, native calls
beside it, and only the one context it samples. Each round's fix moved the outside rather than closing it.

## What is stable, and therefore ships

The subject of #382 itself — measured, and held in every round: **every one of the 79 `--self-test` scripts runs inside
`fixture_git.isolated()`** (from 16), with the entry shape checked statically (closed: one item, argument-free,
undecorated, synchronous, module-level), 711 falsifier runs over nine variable families with 0 victim changes, and
0 real scripts launching at import in the observed context.

## Decision (owner's standing AFK rule — not critical)

**SPLIT.** Rule 5 ships as an OBSERVATION with a bounded claim: the child starts with `-I -S` (closing the startup-hook
escape for free — Codex measured all 84 real files still pass), a cheap static backstop refuses a DIRECT launcher call
anywhere at module level including inside a module-level `if` (closing the context-conditional shape seen in round 3),
and the docs say exactly what is observed — one import, one context, in-process audit events — and list what is not:
native calls, launches only taken in another context through non-literal code, daemon threads that outlive the check.
**Enforcement OUTSIDE the interpreter** (a sandbox profile around the child — `sandbox-exec` on macOS, seccomp/landlock
on Linux CI — that denies process creation at import) is backlog #380's subject, which is precisely "in-process isolation
cannot stop code that escapes it", and is recorded there.

⚠ **Falsifier for this decision:** if a real script's import ever launches a process that this rule did not report,
the observation was taken as a guarantee — #380 is then overdue, not optional.
